import os
import subprocess
import pandas as pd
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from tqdm import tqdm
import json

load_dotenv()

def run_llama_ocr(image_path, output_path="ocr_output.md"):
    """Use llama-ocr (Node.js) to perform OCR on an image and return extracted markdown text."""
    try:
        subprocess.run(
            ["node", "ocr_runner.mjs", image_path, output_path],
            check=True
        )
        with open(output_path, "r", encoding="utf-8") as f:
            return f.read()
    except subprocess.CalledProcessError as e:
        print("Error running llama-ocr:", e)
        return None

def setup_groq_extraction():
    """Configure the LangChain + Groq LLM pipeline for structured payment data extraction."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(
        api_key=groq_api_key,
        model_name="llama3-70b-8192"
    )
    prompt_template = """
    Extract payment information from the following text that was obtained from a screenshot of a payment receipt.

    Text from screenshot:
    {ocr_text}

    Extract the following information:
    1. Transaction ID/Reference Number
    2. Date of transaction
    3. Amount paid
    4. Payment app/method used (e.g., Google Pay, PhonePe, bank transfer, NEFT, Net Banking, RTGS, IMPS)

    The response should be valid JSON with these exact keys:
    - transaction_id: The transaction ID or reference number
    - date: The date of the payment
    - amount: The amount paid (numeric value without currency symbol)
    - payment_method: The payment app or method used
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    return prompt | llm


def extract_payment_info(extraction_chain, ocr_text):
    """Run the structured extraction on OCR output using the Groq-powered LLM."""
    try:
        result = extraction_chain.invoke({"ocr_text": ocr_text})
        
        # Extract content from the AIMessage object
        raw_output = result.content if hasattr(result, "content") else result

        # 🔍 Print response for debugging
        print("\n=== LLM Raw Output ===")
        print(raw_output)
        print("======================\n")

        return json.loads(raw_output)
    except Exception as e:
        print(f"Error extracting info: {e}")
        return None


def process_payment_screenshots(image_directory, output_file="payment_records.xlsx"):
    """Process all payment screenshots in a directory and save structured results to Excel."""
    extraction_chain = setup_groq_extraction()
    image_files = [f for f in os.listdir(image_directory)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    results = []
    print(f"Processing {len(image_files)} screenshots...")

    for img_file in tqdm(image_files):
        img_path = os.path.join(image_directory, img_file)
        temp_output = f"temp_ocr_{img_file}.md"

        ocr_text = run_llama_ocr(img_path, temp_output)
        
        if not ocr_text:
            print(f"Failed to extract text from {img_file}")
            continue

        payment_info = extract_payment_info(extraction_chain, ocr_text)
        
        if payment_info:
            payment_info["image_file"] = img_file
            results.append(payment_info)
        else:
            print(f"Failed to extract payment information from {img_file}")

        if os.path.exists(temp_output):
            os.remove(temp_output)

    if results:
        pd.DataFrame(results).to_excel(output_file, index=False)
        print(f"Saved {len(results)} payment records to {output_file}")
    else:
        print("No payment information extracted.")
    
    return results

if __name__ == "__main__":
    image_directory = "payment_screenshots"
    process_payment_screenshots(image_directory)
