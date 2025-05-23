import os
import subprocess
import pandas as pd
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from tqdm import tqdm
import json
from langchain_core.output_parsers import JsonOutputParser
import sys
import traceback

load_dotenv()

class PaymentExtractor:
    def __init__(self):
        self.extraction_chain = self.setup_groq_extraction()
    
    def setup_groq_extraction(self):
        """Configure the LangChain + Groq LLM pipeline for structured payment data extraction."""
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
            
        parser = JsonOutputParser()
        
        llm = ChatGroq(
            api_key=groq_api_key,
            model_name="llama3-70b-8192"
        )
        
        prompt_template = """
        You are a financial data extraction expert. Extract payment information from the following text that was obtained from a screenshot of a payment receipt.

        Text from screenshot:
        {ocr_text}

        Extract the following information:
        1. Transaction ID/Reference Number
        2. Date of transaction
        3. Amount paid
        4. Payment app/method used (e.g., Google Pay, PhonePe, bank transfer, NEFT, Net Banking, RTGS, IMPS)

        Format your response as a valid JSON object with these exact keys:
        - transaction_id: The transaction ID or reference number (string)
        - date: The date of the payment (string)
        - amount: The amount paid (string, numeric value without currency symbol)
        - payment_method: The payment app or method used (string)
        
        For any field where information is not available, use null as the value.
        
        ONLY RETURN THE JSON OBJECT. Do not include explanations or additional text.
        """
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | llm | parser
        
        return chain

    def extract_payment_info(self, ocr_text):
        """Run the structured extraction on OCR output using the Groq-powered LLM."""
        try:
            result = self.extraction_chain.invoke({"ocr_text": ocr_text})

            print("\n=== Extracted Payment Info ===")
            print(f"Result type: {type(result)}")
            print(result)
            print("============================\n")

            if isinstance(result, dict):
                return result
            elif hasattr(result, "__dict__"):
                return vars(result)
            else:
                try:
                    if isinstance(result, str):
                        return json.loads(result)
                except:
                    pass
                    
            print("WARNING: Could not convert result to dictionary")
            return None
                
        except Exception as e:
            print(f"Error extracting info: {e}")
            traceback.print_exc()
            return None

def run_llama_ocr(image_path, output_path="ocr_output.md"):
    """Use llama-ocr (Node.js) to perform OCR on an image and return extracted markdown text."""
    try:
        subprocess.run(
            ["node", "ocr_runner.mjs", image_path, output_path],
            check=True
        )

        if not os.path.exists(output_path):
            print(f"OCR output file not created: {output_path}")
            return None
            
        with open(output_path, "r", encoding="utf-8") as f:
            return f.read()
    except subprocess.CalledProcessError as e:
        print("Error running llama-ocr:", e)
        return None
    except Exception as e:
        print(f"Unexpected error in OCR processing: {e}")
        return None

def process_payment_screenshots(image_directory, output_file="payment_records.xlsx", contact_mapping=None):
    """Process all payment screenshots in a directory and save structured results to Excel."""
    extractor = PaymentExtractor()

    if not os.path.exists(image_directory):
        print(f"Creating directory: {image_directory}")
        os.makedirs(image_directory)
    
    image_files = [f for f in os.listdir(image_directory)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        print(f"No image files found in {image_directory}")
        return []
    
    results = []
    print(f"Processing {len(image_files)} screenshots...")

    for img_file in tqdm(image_files):
        img_path = os.path.join(image_directory, img_file)
        temp_output = f"temp_ocr_{img_file}.md"

        print(f"\nProcessing image: {img_path}")
        ocr_text = run_llama_ocr(img_path, temp_output)
        
        if not ocr_text:
            print(f"Failed to extract text from {img_file}")
            continue
            
        print(f"OCR text extracted ({len(ocr_text)} chars)")
        print(f"OCR Preview: {ocr_text[:100]}...")

        payment_info = extractor.extract_payment_info(ocr_text)
        
        if payment_info:

            if contact_mapping and img_file in contact_mapping:
                contact = contact_mapping[img_file]
                payment_info["contact_name"] = contact.get("name")
                payment_info["contact_phone"] = contact.get("phone")
                payment_info["sent_date"] = contact.get("sent_date")
            else:
                payment_info["contact_name"] = None
                payment_info["contact_phone"] = None
                payment_info["sent_date"] = None
                
            results.append(payment_info)
            print(f"✅ Successfully extracted data from {img_file}")
            if payment_info.get("contact_name"):
                print(f"Contact: {payment_info['contact_name']} ({payment_info.get('contact_phone', 'No phone')})")
            print(f"Data: {payment_info}")
        else:
            print(f"❌ Failed to extract payment information from {img_file}")

        if os.path.exists(temp_output):
            os.remove(temp_output)

    print(f"\nTotal results collected: {len(results)}")
    if results:
        try:

            df = pd.DataFrame(results)
            print("DataFrame created with columns:", df.columns.tolist())
            print("DataFrame shape:", df.shape)
            print("Preview:")
            print(df.head())
            
            # Save to Excel
            df.to_excel(output_file, index=False)
            print(f"✅ Saved to {output_file}")

            csv_file = output_file.replace('.xlsx', '.csv')
            df.to_csv(csv_file, index=False)
            print(f"✅ Also saved as CSV: {csv_file}")
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            traceback.print_exc()

            print("Data that couldn't be saved:")
            for i, item in enumerate(results):
                print(f"Item {i}: {type(item)} - {item}")

            try:
                json_file = output_file.replace('.xlsx', '.json')
                with open(json_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"✅ Saved as JSON instead: {json_file}")
            except Exception as json_e:
                print(f"❌ Error saving JSON: {json_e}")
    else:
        print("No payment information extracted.")
    
    return results

def process_single_image(image_path, contact_info=None):
    """Process a single image for testing purposes."""
    print(f"Processing single image: {image_path}")

    temp_output = f"temp_ocr_test.md"

    ocr_text = run_llama_ocr(image_path, temp_output)
    if not ocr_text:
        print("Failed to extract text from image")
        return None
        
    print(f"OCR text extracted ({len(ocr_text)} chars)")
    print("OCR text:")
    print(ocr_text)

    extractor = PaymentExtractor()
    payment_info = extractor.extract_payment_info(ocr_text)

    if payment_info and contact_info:
        payment_info["contact_name"] = contact_info.get("name")
        payment_info["contact_phone"] = contact_info.get("phone")
        payment_info["sent_date"] = contact_info.get("sent_date")

    if os.path.exists(temp_output):
        os.remove(temp_output)
        
    if payment_info:
        print("✅ Successfully extracted payment info:")
        print(json.dumps(payment_info, indent=2))
        return payment_info
    else:
        print("❌ Failed to extract payment information")
        return None

if __name__ == "__main__":

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):

        process_single_image(sys.argv[1])
    else:

        image_directory = "payment_screenshots"
        output_file = "payment_records.xlsx"
        
        print("Starting payment screenshot processing pipeline...")
        print(f"Looking for images in: {os.path.abspath(image_directory)}")
        print(f"Output will be saved to: {os.path.abspath(output_file)}")
        
        try:
            results = process_payment_screenshots(image_directory, output_file)
            print(f"Processing complete. Found {len(results)} payment records.")
        except Exception as e:
            print(f"Error in processing pipeline: {e}")
            traceback.print_exc()