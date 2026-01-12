#!/usr/bin/env python3
"""
OCR Processing Script - Sliced PaddleOCR (Robust Edition)
Tuned for M1 Macs and 19th-century newspaper density.
"""

import json
import sys
import gc
import cv2
import numpy as np
from pathlib import Path
from paddleocr import PaddleOCR

# --- INITIALIZATION ---
print("Initializing PaddleOCR V3/V4 Engine...")
try:
    # use_angle_cls=False is safer for column-based historical text
    ocr = PaddleOCR(lang='en', use_angle_cls=False) 
except Exception as e:
    print(f"Error during initialization: {e}")
    sys.exit(1)

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int64, np.int32, np.float32, np.float64)):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def process_column_with_slicing(image_path, col_meta, slice_h=1000, overlap=150):
    """
    Slices a tall column into chunks to prevent memory issues and improve accuracy.
    """
    img = cv2.imread(str(image_path))
    if img is None: return []
    
    # Image Enhancement
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    h_img, w_img = enhanced.shape[:2]
    
    all_text_blocks = []
    x_offset = col_meta['x_offset']

    # Slicing Loop
    for y_start in range(0, h_img, slice_h - overlap):
        y_end = min(y_start + slice_h, h_img)
        chunk = enhanced[y_start:y_end, :]
        
        # Paddle expects BGR images
        chunk_bgr = cv2.cvtColor(chunk, cv2.COLOR_GRAY2BGR)

        # Run OCR
        result = ocr.ocr(chunk_bgr)
        
        if not result or not result[0]:
            continue

        for line in result[0]:
            try:
                # --- ROBUST UNPACKING LOGIC ---
                # Expected: [ [[x,y],...], (text, confidence) ]
                if not line or len(line) < 2:
                    continue

                coords = line[0]
                content = line[1]

                # Check if content is a tuple (text, conf) or just a string
                if isinstance(content, (list, tuple)) and len(content) >= 2:
                    text_val = content[0]
                    conf_val = float(content[1])
                else:
                    # Fallback if only text is returned
                    text_val = str(content)
                    conf_val = 0.99

                if not text_val or conf_val < 0.4:
                    continue

                # Map coordinates back to the full broadsheet
                x_coords = [p[0] for p in coords]
                y_coords = [p[1] for p in coords]
                
                real_y = min(y_coords) + y_start
                real_x = min(x_coords) + x_offset
                real_w = max(x_coords) - min(x_coords)
                real_h = max(y_coords) - min(y_coords)

                # DEDUPLICATION: Avoid double-counting lines in the overlap
                center_y = real_y + (real_h / 2)
                if any(abs(center_y - (b['bbox']['y'] + b['bbox']['height']/2)) < 10 for b in all_text_blocks):
                    continue

                all_text_blocks.append({
                    "text": text_val,
                    "confidence": conf_val,
                    "bbox": {
                        "x": float(real_x),
                        "y": float(real_y),
                        "width": float(real_w),
                        "height": float(real_h)
                    },
                    "column": int(col_meta['column_index'])
                })
            except (IndexError, TypeError, ValueError) as e:
                # Skip malformed lines rather than crashing the whole page
                continue
            
        del chunk_bgr
        del chunk
        gc.collect()

    return all_text_blocks

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir if (script_dir / "data").exists() else script_dir.parent
    
    preprocessed_dir = project_root / "data" / "preprocessed"
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = preprocessed_dir / "all_metadata.json"
    if not metadata_path.exists():
        print(f"Error: run preprocess.py first.")
        return

    with open(metadata_path, 'r') as f:
        all_metadata = json.load(f)

    all_results = []
    print(f"Starting Robust OCR on {len(all_metadata)} documents...")

    for pdf_metadata in all_metadata:
        pdf_name = pdf_metadata['source_pdf']
        print(f"\nProcessing: {pdf_name}")
        pdf_entry = {"filename": pdf_name, "pages": []}

        for page_meta in pdf_metadata['pages']:
            print(f"  Page {page_meta['page_num']}...", end="", flush=True)
            page_text = []
            
            for col_meta in page_meta['columns']:
                blocks = process_column_with_slicing(col_meta['path'], col_meta)
                page_text.extend(blocks)
                print(".", end="", flush=True)
            
            pdf_entry["pages"].append({
                "page_number": int(page_meta['page_num']),
                "text_blocks": page_text,
                "total_blocks": len(page_text)
            })
            print(f" Done ({len(page_text)} lines)")
            gc.collect() 

        all_results.append(pdf_entry)

    # Save output
    output_file = output_dir / "ocr_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"pdfs": all_results}, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

    print(f"\n✓ OCR complete. Results saved to {output_file}")

if __name__ == "__main__":
    main()