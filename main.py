import os
import zipfile
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import json
import re
from tqdm import tqdm
from whatsapp_parser import WhatsAppChatParser
from typing import List

# Load environment variables
load_dotenv()

class MaintenancePaymentProcessor:
    def __init__(self):
        self.temp_dir = Path("temp_screenshots")
        self.temp_dir.mkdir(exist_ok=True)
        self.whatsapp_parser = WhatsAppChatParser()
        
    def extract_zip(self, zip_path):
        """Extract WhatsApp chat zip file and return list of image paths"""
        print(f"Extracting WhatsApp chat zip file: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
        
        # Get all image files
        image_files = list(self.temp_dir.glob("**/*.jpg")) + list(self.temp_dir.glob("**/*.png"))
        print(f"Found {len(image_files)} image files")
        return image_files
    
    def get_current_month_filter(self):
        """Get current month in YYYY-MM format"""
        now = datetime.now()
        return now.strftime("%Y-%m")
        
    def extract_date_from_filename(self, filename):
        """Extract date from filename patterns like PHOTO-2025-04-27"""
        date_match = re.search(r'PHOTO-(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            date_str = date_match.group(1)
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                return date_obj.strftime("%d %b %Y")  # Format as "27 Apr 2025"
            except ValueError:
                pass
        return None
    
    def normalize_date(self, date_str):
        """Convert various date formats to YYYY-MM format for comparison"""
        if not date_str:
            return None
            
        try:
            # Try different date format patterns
            formats = [
                "%d/%m/%y, %H:%M:%S",  # WhatsApp chat format: 27/04/25, 12:44:30
                "%d/%m/%y, %H:%M",     # WhatsApp chat format: 27/04/25, 12:44
                "%d %b %Y",            # 26 Apr 2025
                "%d %B %Y",            # 26 April 2025
                "%d-%m-%Y",            # 26-04-2025
                "%d/%m/%Y",            # 26/04/2025
                "%Y-%m-%d",            # 2025-04-26
                "%B %d, %Y",           # April 26, 2025
                "%b %d, %Y",           # Apr 26, 2025
                "%d %b %Y, %H:%M %p"   # 27 Apr 2025, 11:35 am
            ]
            
            # Try each format
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime("%Y-%m")  # Convert to YYYY-MM
                except ValueError:
                    continue
                    
            print(f"Could not parse date: {date_str}")
            return None
            
        except Exception as e:
            print(f"Error parsing date '{date_str}': {str(e)}")
            return None
    
    def filter_images_by_month(self, image_files: List[str], month: str) -> List[str]:
        """Filter images by month based on filename date."""
        filtered_files = []
        target_year, target_month = month.split('-')
        
        for image_file in image_files:
            # Extract date from filename
            filename = os.path.basename(image_file)
            date_match = re.search(r'(\d{4})-(\d{2})-\d{2}', filename)
            
            if date_match:
                file_year, file_month = date_match.groups()
                if file_year == target_year and file_month == target_month:
                    print(f"Including {image_file} (filename date: {file_year}-{file_month})")
                    filtered_files.append(image_file)
                else:
                    print(f"Excluding {image_file} (filename date: {file_year}-{file_month})")
            else:
                # If no date in filename, use file modification date
                mod_time = os.path.getmtime(image_file)
                mod_date = datetime.fromtimestamp(mod_time)
                if mod_date.year == int(target_year) and mod_date.month == int(target_month):
                    print(f"Including {image_file} (modification date: {mod_date.year}-{mod_date.month:02d})")
                    filtered_files.append(image_file)
                else:
                    print(f"Excluding {image_file} (modification date: {mod_date.year}-{mod_date.month:02d})")
        
        print(f"Filtered {len(filtered_files)} out of {len(image_files)} images for month {month}")
        return filtered_files
    
    def process_image(self, image_path):
        """Process a single image to extract payment information"""
        from ocr_runner import process_image
        from payment_extractor import PaymentExtractor
        
        print(f"Processing image: {image_path}")
        
        # Extract text using OCR
        extracted_text = process_image(str(image_path))
        
        if not extracted_text:
            print(f"No text extracted from {image_path}")
            return None
        
        # Extract payment information
        extractor = PaymentExtractor()
        payment_info = extractor.extract_payment_info(extracted_text)
        
        return payment_info
    
    def process_payments(self, zip_path, month_filter=None, output_file="payments.xlsx"):
        """
        Main processing function
        
        Args:
            zip_path: Path to WhatsApp chat zip export
            month_filter: YYYY-MM format to filter by month (default: current month)
            output_file: Path to output Excel file
        """
        # If no month filter provided, use current month
        if not month_filter:
            month_filter = self.get_current_month_filter()
            print(f"Using current month filter: {month_filter}")
        
        # Extract the zip file
        image_files = self.extract_zip(zip_path)
        
        # Process the WhatsApp chat to get contact mappings
        contact_mapping = self.whatsapp_parser.process_chat_export(self.temp_dir)
        
        # Show the contact mapping for debugging
        print("\nContact mapping:")
        for key, value in list(contact_mapping.items())[:5]:  # Show first 5 entries
            print(f"  {key}: {value}")
        print(f"  ... ({len(contact_mapping)} total mappings)")
        
        # Filter images by month
        filtered_images = self.filter_images_by_month(image_files, month_filter)
        
        # Process each image
        results = []
        for img_path in tqdm(filtered_images, desc="Processing images"):
            try:
                # Process the image to extract payment info
                payment_info = self.process_image(img_path)
                
                if payment_info:
                    # Get the filename for mapping
                    img_filename = os.path.basename(img_path)
                    
                    # Add image file reference
                    payment_info['image_file'] = str(img_path)
                    
                    # Add contact information from the mapping
                    contact_info = contact_mapping.get(img_filename, {})
                    
                    if contact_info:
                        payment_info['contact_name'] = contact_info.get('name', contact_info.get('phone'))
                        payment_info['contact_phone'] = contact_info.get('phone')
                        payment_info['sent_date'] = contact_info.get('sent_date')
                        
                        # Convert sent_date to a readable format
                        if payment_info['sent_date']:
                            try:
                                # Handle different WhatsApp date formats
                                if '/' in payment_info['sent_date']:
                                    date_obj = datetime.strptime(payment_info['sent_date'], "%d/%m/%y, %H:%M:%S")
                                else:
                                    date_obj = datetime.strptime(payment_info['sent_date'], "%d-%m-%Y, %H:%M:%S")
                                payment_info['sent_date'] = date_obj.strftime("%d %b %Y, %I:%M %p")
                            except Exception as e:
                                print(f"Error formatting sent date: {e}")
                    else:
                        payment_info['contact_name'] = None
                        payment_info['contact_phone'] = None
                        payment_info['sent_date'] = None
                    
                    # Debug output to show mapping
                    print(f"\nMapping for {img_filename}:")
                    print(f"  Contact: {payment_info.get('contact_name')}")
                    print(f"  Phone: {payment_info.get('contact_phone')}")
                    print(f"  Sent date: {payment_info.get('sent_date')}")
                    
                    # If date is missing, try to extract from filename
                    if not payment_info.get('date'):
                        filename_date = self.extract_date_from_filename(str(img_path))
                        if filename_date:
                            payment_info['date'] = filename_date
                    
                    results.append(payment_info)
                    print(f"Added payment info: {payment_info}")
                else:
                    print(f"No payment info extracted from {img_path}")
            except Exception as e:
                print(f"Error processing {img_path}: {str(e)}")
        
        # Save results to Excel
        self.save_to_excel(results, output_file)
        
        return results
    
    def save_to_excel(self, results, output_file):
        """Save results to Excel file with specified column order"""
        if not results:
            print("No results to save!")
            # Create empty Excel with headers
            df = pd.DataFrame(columns=["contact_name", "contact_phone", "sent_date", 
                                       "transaction_id", "amount", "payment_method", "date"])
            df.to_excel(output_file, index=False)
            print(f"Empty Excel file created at {output_file}")
            return
            
        try:
            # Convert results to DataFrame
            df = pd.DataFrame(results)
            
            # Ensure required columns exist
            for col in ["contact_name", "contact_phone", "sent_date", "transaction_id", "amount", "payment_method", "date"]:
                if col not in df.columns:
                    df[col] = None
            
            # Reorder columns according to requirements
            column_order = [
                "contact_name",       # Sender name
                "contact_phone",      # Contact number
                "sent_date",          # Date message was sent
                "transaction_id",     # Transaction ID  
                "amount",             # Amount
                "payment_method",     # Payment method
                "date",               # Transaction date (from screenshot)
                "image_file"          # Source image file
            ]
            
            df = df.reindex(columns=[c for c in column_order if c in df.columns] + 
                          [c for c in df.columns if c not in column_order])
            
            print("DataFrame created with columns:", df.columns.tolist())
            print("Preview:")
            print(df.head())
            
            # Save to Excel
            df.to_excel(output_file, index=False)
            print(f"✅ Results saved to {output_file}")
            
            # Also save as CSV for backup
            csv_file = output_file.replace('.xlsx', '.csv')
            df.to_csv(csv_file, index=False)
            print(f"✅ Also saved as CSV: {csv_file}")
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            import traceback
            traceback.print_exc()
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
        print("Temporary files cleaned up")

def main():
    processor = MaintenancePaymentProcessor()
    
    # Get input from user
    zip_path = input("Enter the path to WhatsApp chat zip file: ")
    
    # Default to current month, but allow user to specify a different month
    current_month = processor.get_current_month_filter()
    month_input = input(f"Enter the month to process (format: YYYY-MM): ")
    month = month_input if month_input else current_month
    
    output_file = input("Enter the output Excel file name (default: maintenance_payments.xlsx): ")
    if not output_file:
        output_file = "maintenance_payments.xlsx"
    
    try:
        # Process the payments
        results = processor.process_payments(zip_path, month, output_file)
        
        print(f"Processing complete. Found {len(results)} payment records.")
        
    finally:
        # Ask user if they want to clean up temp files
        cleanup = input("Clean up temporary files? (y/n): ")
        if cleanup.lower() == 'y':
            processor.cleanup()
        else:
            print(f"Temporary files kept at: {processor.temp_dir}")

if __name__ == "__main__":
    main()