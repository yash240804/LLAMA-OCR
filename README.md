# Society Maintenance Payment Processor

This tool helps process WhatsApp chat exports containing maintenance payment screenshots. It extracts payment information using OCR and LLM, then organizes it into an Excel file. It also extracts contact information from the chat to match with payment data.

## Features

- Process WhatsApp chat exports (zip files)
- Extract screenshots from the chat
- Extract contact information (name and phone number) from chat text
- Match payment screenshots with contact information using timestamps and filenames
- Use LLaMA OCR for text extraction from screenshots
- Extract structured payment information using LLM
- Save results to Excel file with contact details
- Filter by month
- Handle various WhatsApp chat formats and special characters

## Setup

1. Install Python dependencies:
```bash
pip install -r requirement.txt
```

2. Install Node.js dependencies:
```bash
npm install llama-ocr
```

3. Create a `.env` file with your API keys:
Website: https://groq.com
Website: https://together.ai
```
GROQ_API_KEY=your_groq_api_key
TOGETHER_API_KEY=your_together_api_key
```

## Usage

1. Export your WhatsApp chat with media (zip file)
2. Run the script:
```bash
python main.py
```

3. When prompted:
   - Enter the path to your WhatsApp chat zip file
   - Enter the month to process (format: YYYY-MM, e.g., 2024-03)
   - Enter the output Excel file name

The script will:
1. Extract the zip file
2. Parse the WhatsApp chat to extract contact information
3. Process all screenshots and match them with contacts
4. Extract payment information
5. Save results to Excel with contact details
6. Clean up temporary files

## Output Format

The Excel file will contain the following columns:
- contact_name: The name of the contact from the WhatsApp chat
- contact_phone: The phone number of the contact (if available)
- sent_date: The date and time when the payment screenshot was shared in the chat
- transaction_id: The transaction ID or reference number
- amount: The amount paid
- payment_method: The payment app or method used
- date: The date of the payment
- image_file: The source image file name

## How It Works

1. **WhatsApp Chat Parsing**: 
   - Extracts the _chat.txt file from the WhatsApp export
   - Parses chat messages to identify contacts and their messages
   - Handles special characters and various date formats
   - Tracks image attachments and their senders

2. **Contact-Image Mapping**: 
   - Maps screenshots to contacts using multiple strategies:
     - Exact filename matching
     - Numeric ID matching
     - Timestamp-based matching
   - Handles zero-width spaces and special characters in chat

3. **Payment Information Extraction**: 
   - Uses OCR to extract text from screenshots
   - Uses LLM to extract structured payment information
   - Handles various payment receipt formats

4. **Data Consolidation**: 
   - Combines payment information with contact details
   - Filters by month
   - Exports to Excel with proper formatting

## Requirements

- Python 3.8+
- Node.js 14+
- Groq API key
- Together API key

## Troubleshooting

If you encounter any issues:

1. **Missing Dependencies**:
   - Make sure all Python packages are installed: `pip install -r requirement.txt`
   - Ensure Node.js and llama-ocr are installed: `npm install llama-ocr`

2. **Chat Parsing Issues**:
   - Check if your WhatsApp export includes the _chat.txt file
   - Ensure the chat export includes media files
   - Verify the chat format matches the expected pattern

3. **Image Mapping Issues**:
   - Check the contact_mapping.json file in the temp directory
   - Verify that image filenames match the format in the chat
   - Ensure timestamps are in the correct format

4. **OCR/LLM Issues**:
   - Verify your API keys are correctly set in the .env file
   - Check if the screenshots are clear and readable
   - Ensure the payment receipts are in a supported format