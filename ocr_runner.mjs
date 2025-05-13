import { ocr } from "llama-ocr";
import fs from "fs";
import dotenv from "dotenv";

dotenv.config();

const filePath = process.argv[2];
const outputPath = process.argv[3];

if (!filePath) {
  console.error("Error: No input file path provided");
  console.log("Usage: node ocr_runner.mjs <image_path> <output_path>");
  process.exit(1);
}

if (!outputPath) {
  console.error("Error: No output file path provided");
  console.log("Usage: node ocr_runner.mjs <image_path> <output_path>");
  process.exit(1);
}

const apiKey = process.env.TOGETHER_API_KEY;
if (!apiKey) {
  console.error("Error: TOGETHER_API_KEY not found in environment variables");
  console.error("Please add your Together API key to the .env file");
  process.exit(1);
}

if (!fs.existsSync(filePath)) {
  console.error(`Error: Input file does not exist: ${filePath}`);
  process.exit(1);
}

console.log(`Processing image: ${filePath}`);
console.log(`Output will be saved to: ${outputPath}`);

try {
  const markdown = await ocr({
    filePath,
    apiKey: process.env.TOGETHER_API_KEY,
  });

  fs.writeFileSync(outputPath, markdown);
  console.log("OCR result written to:", outputPath);
  console.log(`Extracted ${markdown.length} characters`);
} catch (err) {
  console.error("Error running llama-ocr:", err);
  process.exit(1);
}