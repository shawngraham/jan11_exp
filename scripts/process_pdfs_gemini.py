#!/usr/bin/env python3
"""
OCR Processing Script - Gemini Vision Edition
Optimized for Google Gemini Pro Vision API.
"""

import json
import gc
import cv2
import numpy as np
from pathlib import Path
import google.generativeai as genai
from PIL import Image
import os
import time

# --- Gemini API Configuration ---
# IMPORTANT: Set your Gemini API key as an environment variable:
#   export GEMINI_API_KEY="your-api-key-here"
# Or pass it directly (not recommended for production):
#   API_KEY = "your-api-key-here"

API_KEY = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY')

if API_KEY == 'YOUR_API_KEY' or not API_KEY:
    print("ERROR: Gemini API key is not set.")
    print("Please set the GEMINI_API_KEY environment variable:")
    print("  export GEMINI_API_KEY='your-api-key-here'")
    exit(1)

# Initialize Gemini
print("Initializing Gemini Pro Vision OCR Engine...")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')  # Using Flash for faster, cheaper inference

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int64, np.int32, np.float32, np.float64)):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def gemini_ocr(image_path, max_retries=3):
    """
    Extract text and bounding boxes from an image using Gemini Vision API.

    Args:
        image_path: Path to the image file
        max_retries: Number of retry attempts for API calls

    Returns:
        List of text blocks with bounding boxes and confidence scores
    """
    img_pil = Image.open(image_path).convert("RGB")
    w, h = img_pil.size

    # Prompt engineering for structured output
    prompt = (
        "Extract all text from this newspaper image. "
        "For each text block, provide the text content and its bounding box coordinates. "
        "Return ONLY a JSON array with this exact format:\n"
        '[\n'
        '  {"text": "example text", "x": 10, "y": 20, "width": 100, "height": 15},\n'
        '  {"text": "more text", "x": 10, "y": 40, "width": 95, "height": 15}\n'
        ']\n'
        "Coordinates should be in pixels. Include all text, even small fragments."
    )

    for attempt in range(max_retries):
        try:
            response = model.generate_content([prompt, img_pil])

            # Extract text from response
            response_text = response.text.strip()

            # Try to parse as JSON
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                # Extract content between ``` blocks
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            text_blocks = json.loads(response_text)

            # Validate structure
            if not isinstance(text_blocks, list):
                raise ValueError("Response is not a JSON array")

            # Add confidence scores (Gemini doesn't provide them, so we use a default)
            for block in text_blocks:
                if not all(key in block for key in ['text', 'x', 'y', 'width', 'height']):
                    raise ValueError(f"Block missing required fields: {block}")
                block['confidence'] = 0.90  # Default confidence for Gemini

            return text_blocks

        except json.JSONDecodeError as e:
            print(f"\n    Warning: JSON parse error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                # Final fallback: simple text extraction without bounding boxes
                print("    Falling back to simple text extraction...")
                return fallback_text_extraction(img_pil, w, h)
            time.sleep(1)  # Brief delay before retry

        except Exception as e:
            print(f"\n    Warning: Gemini API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return fallback_text_extraction(img_pil, w, h)
            time.sleep(2 ** attempt)  # Exponential backoff

    return []

def fallback_text_extraction(img_pil, width, height):
    """
    Fallback method when structured extraction fails.
    Returns text with a single bounding box covering the whole image.
    """
    try:
        simple_prompt = "Extract all text from this image. Return only the text, nothing else."
        response = model.generate_content([simple_prompt, img_pil])

        extracted_text = ""
        for part in response.parts:
            if hasattr(part, 'text'):
                extracted_text += part.text + "\n"

        if extracted_text.strip():
            # Return as a single block covering the whole image
            return [{
                "text": extracted_text.strip(),
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "confidence": 0.85
            }]
    except Exception as e:
        print(f"    Fallback extraction also failed: {e}")

    return []

def main():
    # 1. Setup Project Paths
    script_dir = Path(__file__).parent
    project_root = script_dir if (script_dir / "data").exists() else script_dir.parent
    preprocessed_dir = project_root / "data" / "preprocessed"
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = preprocessed_dir / "all_metadata.json"
    if not metadata_path.exists():
        print(f"Error: Run preprocess.py first. Missing: {metadata_path}")
        return

    with open(metadata_path, 'r') as f:
        all_metadata = json.load(f)

    all_results = []

    # 2. Process each PDF found in metadata
    for pdf_meta in all_metadata:
        pdf_name = pdf_meta['source_pdf']
        print(f"\nOCRing Snippets for: {pdf_name}")
        pdf_entry = {"filename": pdf_name, "pages": []}

        for page_meta in pdf_meta['pages']:
            print(f"  Page {page_meta['page_num']}...", end="", flush=True)
            page_blocks = []

            # Process each snippet (article) individually
            for snip in page_meta['snippets']:
                snippet_image_path = snip['path']

                # Check if image exists
                if not Path(snippet_image_path).exists():
                    print(f"\n    Warning: Image not found: {snippet_image_path}")
                    continue

                # Run OCR using Gemini Pro Vision
                gemini_output = gemini_ocr(snippet_image_path)

                if not gemini_output:
                    continue

                for block in gemini_output:
                    try:
                        # Map snippet relative coords -> Full Broadsheet Pixels
                        real_x = float(block['x']) + snip['x_offset']
                        real_y = float(block['y']) + snip['y_offset']
                        real_w = float(block['width'])
                        real_h = float(block['height'])

                        page_blocks.append({
                            "text": block['text'],
                            "confidence": block.get('confidence', 0.90),
                            "bbox": {
                                "x": real_x,
                                "y": real_y,
                                "width": real_w,
                                "height": real_h
                            },
                            "column": snip.get('col_idx', snip.get('column', 0))
                        })
                    except (KeyError, TypeError, ValueError) as e:
                        print(f"\n    Error processing block: {e}")
                        continue

                # Memory cleanup after each snippet
                gc.collect()

                # Rate limiting to avoid API quota issues
                time.sleep(0.5)  # 500ms delay between requests

            pdf_entry["pages"].append({
                "page_number": page_meta['page_num'],
                "text_blocks": page_blocks,
                "total_blocks": len(page_blocks)
            })
            print(f" Done ({len(page_blocks)} blocks)")

        all_results.append(pdf_entry)

    # 4. Save consolidated results
    output_file = output_dir / "ocr_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"pdfs": all_results}, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

    print(f"\n✓ OCR Success. Output saved to: {output_file}")

if __name__ == "__main__":
    main()
