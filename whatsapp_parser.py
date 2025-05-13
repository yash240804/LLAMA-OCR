import re
import os
from pathlib import Path
from datetime import datetime
import json

class WhatsAppChatParser:
    def __init__(self):
        self.contacts = {}  # Dictionary to store contact info: {name: {name, phone}}
        self.image_contact_mapping = {}  # Map image filenames to contact info
        self.message_timestamps = {}  # Store timestamps for each image
    
    def parse_chat_file(self, chat_file_path):
        """
        Parse WhatsApp chat.txt file to extract contact information
        and map images to contacts based on timestamps
        """
        print(f"Parsing WhatsApp chat file: {chat_file_path}")
        
        if not os.path.exists(chat_file_path):
            print(f"Chat file not found: {chat_file_path}")
            return {}
            
        # Regular expression to match WhatsApp chat entries
        # Updated to handle zero-width spaces and other special characters
        chat_pattern = re.compile(r'^[‎\s]*\[(\d{2}/\d{2}/\d{2},\s\d{2}:\d{2}:\d{2})\]\s(.+?):\s(.+)$')
        
        # Pattern to match image attachments
        image_pattern = re.compile(r'<attached:\s*(\d{8}-PHOTO-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.jpg)>')
        
        image_entries = []
        current_timestamp = None
        current_sender = None
        
        with open(chat_file_path, 'r', encoding='utf-8', errors='ignore') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                
                # Debug print
                print(f"Processing line: {line}")
                    
                match = chat_pattern.match(line)
                if match:
                    timestamp_str, contact_name, message = match.groups()
                    current_timestamp = timestamp_str
                    current_sender = contact_name
                    
                    # Store the contact information
                    if contact_name not in self.contacts:
                        self.contacts[contact_name] = {
                            'name': contact_name,
                            'phone': self.extract_phone_number(contact_name, message)
                        }
                    
                    # Check if this message contains an image attachment
                    img_match = image_pattern.search(message)
                    if img_match:
                        image_filename = img_match.group(1)
                        # Store the timestamp for this image
                        self.message_timestamps[image_filename] = timestamp_str
                        
                        entry = {
                            'timestamp': timestamp_str,
                            'contact_name': contact_name,
                            'contact_info': self.contacts[contact_name],
                            'sent_date': timestamp_str,
                            'image_filename': image_filename
                        }
                        image_entries.append(entry)
                        print(f"Found image: {image_filename} from {contact_name} at {timestamp_str}")
        
        print(f"Found {len(self.contacts)} contacts and {len(image_entries)} image entries")
        return image_entries
    
    def extract_phone_number(self, sender_name, message):
        """Extract phone number from sender name or message"""
        # Check if sender name is a phone number
        if re.match(r'^\+\d+\s\d+$', sender_name):
            return sender_name
            
        # Look for phone numbers in the message
        phone_match = re.search(r'(\+\d{1,3}\s?\d{10}|\d{10})', message)
        if phone_match:
            return phone_match.group(1)
            
        return None
    
    def map_images_to_contacts(self, image_files, image_entries):
        """
        Match image files to contacts based on filenames and timestamps from chat
        """
        print(f"Mapping {len(image_files)} images to contacts...")
        
        # Create mapping of filenames to contact info
        filename_mapping = {}
        
        # First, create mappings using the full filenames from chat
        for entry in image_entries:
            if entry.get('image_filename'):
                filename = entry['image_filename']
                filename_mapping[filename] = {
                    'name': entry['contact_name'],
                    'phone': entry['contact_info'].get('phone'),
                    'sent_date': entry['sent_date']
                }
                print(f"Added mapping for {filename} -> {entry['contact_name']}")
        
        # Process each image file
        mapped_count = 0
        for img_path in image_files:
            img_filename = os.path.basename(img_path)
            print(f"\nTrying to match image: '{img_filename}'")
            
            # Try exact match first
            if img_filename in filename_mapping:
                self.image_contact_mapping[img_filename] = filename_mapping[img_filename]
                print(f"Exact match: {img_filename} -> {filename_mapping[img_filename]['name']}")
                mapped_count += 1
                continue
            
            # Try to match using number portion at the beginning
            img_number_match = re.match(r'^(\d+)', img_filename)
            if img_number_match:
                img_number = img_number_match.group(1)
                
                # Try matching with zero-padded and non-zero-padded versions
                for filename, contact_info in filename_mapping.items():
                    file_number_match = re.match(r'^(\d+)', filename)
                    if file_number_match:
                        file_number = file_number_match.group(1)
                        
                        # Try both with and without leading zeros
                        if file_number.lstrip('0') == img_number.lstrip('0'):
                            self.image_contact_mapping[img_filename] = contact_info
                            print(f"Number match: {img_filename} -> {contact_info['name']}")
                            mapped_count += 1
                            break
            
            # If no match found, try to find the closest timestamp match
            if img_filename not in self.image_contact_mapping:
                # Extract date from filename if present
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', img_filename)
                if date_match:
                    img_date = date_match.group(1)
                    
                    # Find the closest timestamp match
                    closest_entry = None
                    min_time_diff = float('inf')
                    
                    for entry in image_entries:
                        entry_date = self.extract_date_from_timestamp(entry['timestamp'])
                        if entry_date:
                            time_diff = abs((datetime.strptime(img_date, "%Y-%m-%d") - 
                                          datetime.strptime(entry_date, "%Y-%m-%d")).days)
                            if time_diff < min_time_diff:
                                min_time_diff = time_diff
                                closest_entry = entry
                    
                    if closest_entry and min_time_diff <= 1:  # Allow 1 day difference
                        self.image_contact_mapping[img_filename] = {
                            'name': closest_entry['contact_name'],
                            'phone': closest_entry['contact_info'].get('phone'),
                            'sent_date': closest_entry['sent_date']
                        }
                        print(f"Timestamp match: {img_filename} -> {closest_entry['contact_name']}")
                        mapped_count += 1
                    else:
                        # If no match found, create an entry with None values
                        self.image_contact_mapping[img_filename] = {
                            'name': None,
                            'phone': None,
                            'sent_date': None
                        }
                        print(f"No match found for {img_filename}")
        
        print(f"\nSuccessfully mapped {mapped_count} out of {len(image_files)} images")
        return self.image_contact_mapping
    
    def extract_date_from_timestamp(self, timestamp_str):
        """Extract date from WhatsApp timestamp string"""
        try:
            # Handle different timestamp formats
            if '/' in timestamp_str:
                date_obj = datetime.strptime(timestamp_str, "%d/%m/%y, %H:%M:%S")
            else:
                date_obj = datetime.strptime(timestamp_str, "%d-%m-%Y, %H:%M:%S")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return None
    
    def process_chat_export(self, chat_dir):
        """Process WhatsApp chat export directory to extract contacts and map images"""
        # Find the chat file (_chat.txt or similar)
        chat_files = list(Path(chat_dir).glob("*_chat.txt"))
        if not chat_files:
            # Try alternative chat file names
            chat_files = list(Path(chat_dir).glob("*.txt"))
            
        if not chat_files:
            print("No chat text file found in the extracted WhatsApp data")
            return {}
            
        chat_file = chat_files[0]
        print(f"Found chat file: {chat_file}")
        
        # Get all image files
        image_files = list(Path(chat_dir).glob("**/*.jpg")) + list(Path(chat_dir).glob("**/*.png"))
        print(f"Found {len(image_files)} image files")
        
        # Parse the chat file and get image entries
        image_entries = self.parse_chat_file(str(chat_file))
        
        # Map images to contacts
        contact_mapping = self.map_images_to_contacts(image_files, image_entries)
        
        # Save mapping to a file for debugging
        try:
            mapping_file = Path(chat_dir) / "contact_mapping.json"
            with open(mapping_file, "w", encoding="utf-8") as f:
                json.dump(contact_mapping, f, indent=2, ensure_ascii=False)
                print(f"Saved contact mapping to {mapping_file}")
        except Exception as e:
            print(f"Error saving contact mapping: {e}")
        
        return contact_mapping