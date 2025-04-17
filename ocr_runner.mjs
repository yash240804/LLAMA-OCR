// ocr_runner.mjs
import { ocr } from "llama-ocr";
import fs from "fs";
import dotenv from "dotenv";

dotenv.config();

const filePath = process.argv[2];
const outputPath = process.argv[3];

try {
  const markdown = await ocr({
    filePath,
    apiKey: process.env.TOGETHER_API_KEY,
  });

  fs.writeFileSync(outputPath, markdown);
  console.log("OCR result written to:", outputPath);
} catch (err) {
  console.error("Error running llama-ocr:", err);
  process.exit(1);
}
