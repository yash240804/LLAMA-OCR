import os
import subprocess
from pathlib import Path

def process_image(image_path):
    """Process an image using llama-ocr and return the extracted text."""
    # Create a temporary output file
    temp_output = Path("temp_ocr_output.md")
    
    try:
        # Run the Node.js OCR script
        print(f"Running OCR on {image_path}")
        result = subprocess.run(
            ["node", "ocr_runner.mjs", str(image_path), str(temp_output)],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Print command output for debugging
        if result.stdout:
            print(f"OCR stdout: {result.stdout}")
        if result.stderr:
            print(f"OCR stderr: {result.stderr}")
        
        # Check if the output file exists
        if not temp_output.exists():
            print(f"OCR output file not created: {temp_output}")
            return None
            
        # Read the extracted text
        with open(temp_output, "r", encoding="utf-8") as f:
            extracted_text = f.read()
            
        if extracted_text:
            print(f"Successfully extracted {len(extracted_text)} characters")
            # Print a preview of the text
            print(f"Text preview: {extracted_text[:100]}...")
        else:
            print("Warning: Empty text extracted")
            
        return extracted_text
        
    except subprocess.CalledProcessError as e:
        print("Error running llama-ocr:", e)
        print(f"Return code: {e.returncode}")
        if e.output:
            print(f"Output: {e.output}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        print(f"Unexpected error in OCR processing: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temporary file
        if temp_output.exists():
            temp_output.unlink()