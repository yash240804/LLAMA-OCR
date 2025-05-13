import os
from pathlib import Path
import json
import sys
from whatsapp_parser import WhatsAppChatParser

def test_parser_mapping(zip_dir):
    """
    Test the improved WhatsApp parser's mapping functionality directly
    
    Args:
        zip_dir: Path to extracted WhatsApp zip directory
    """
    parser = WhatsAppChatParser()

    chat_files = list(Path(zip_dir).glob("*_chat.txt"))
    if not chat_files:
        chat_files = list(Path(zip_dir).glob("*.txt"))
        
    if not chat_files:
        print("No chat text file found in the directory")
        return
        
    chat_file = chat_files[0]
    print(f"Found chat file: {chat_file}")

    image_files = list(Path(zip_dir).glob("**/*.jpg")) + list(Path(zip_dir).glob("**/*.png"))
    print(f"Found {len(image_files)} image files")

    print("\nImage files found:")
    for img in image_files:
        print(f"  {os.path.basename(img)}")

    image_entries = parser.parse_chat_file(chat_file)
    
    print("\nImage entries from chat file:")
    for entry in image_entries:
        print(f"  {entry['image_filename']} from {entry['contact_name']} at {entry['sent_date']}")

    contact_mapping = parser.map_images_to_contacts(image_files, image_entries)
    
    print("\nMapping results:")
    successful = 0
    for filename, info in contact_mapping.items():
        status = "✅ Mapped" if info.get('name') else "❌ No match"
        if info.get('name'):
            successful += 1
        print(f"  {status} {filename} -> {info.get('name')} ({info.get('sent_date')})")
    
    print(f"\nSummary: Successfully mapped {successful} out of {len(image_files)} images ({successful/len(image_files)*100:.1f}%)")

    with open(os.path.join(zip_dir, "improved_mapping.json"), "w", encoding="utf-8") as f:
        json.dump(contact_mapping, f, indent=2, ensure_ascii=False)
        print(f"Saved detailed mapping to {os.path.join(zip_dir, 'improved_mapping.json')}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        zip_dir = sys.argv[1]
    else:
        zip_dir = input("Enter the path to extracted WhatsApp directory: ")
        
    if os.path.exists(zip_dir):
        test_parser_mapping(zip_dir)
    else:
        print(f"Directory not found: {zip_dir}")