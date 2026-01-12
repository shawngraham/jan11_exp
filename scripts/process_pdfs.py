#!/usr/bin/env python3
"""
OCR Processing Script - Snippet Edition
Optimized for PaddleOCR results on M1 Macs.
"""

import json
import gc
import cv2
import numpy as np
from pathlib import Path
from paddleocr import PaddleOCR

# Initialization
print("Initializing PaddleOCR V3/V4 Engine...")
# use_angle_cls=False is faster and more stable for straight newsprint
ocr = PaddleOCR(lang='en', use_angle_cls=False)

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int64, np.int32, np.float32, np.float64)):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

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
                img = cv2.imread(snip['path'])
                if img is None: continue
                
                # Run OCR
                # Some versions require .predict(), some .ocr()
                # If .predict() gave you DeprecationWarnings before, use .ocr(img)
                try:
                    result = ocr.ocr(img)
                except Exception:
                    result = ocr.predict(img)
                
                if not result or not result[0]:
                    continue

                # 3. Robust Unpacking
                # Paddle results can be: [ [[bbox], (text, conf)], ... ]
                # OR nested: [ [ [[bbox], (text, conf)], ... ] ]
                lines = result[0] if isinstance(result[0], list) else result

                for line in lines:
                    try:
                        # Defensive check: ensure line has bbox and content
                        if not isinstance(line, (list, tuple)) or len(line) < 2:
                            continue
                            
                        coords = line[0]
                        content = line[1]
                        
                        text = content[0]
                        conf = float(content[1])

                        # Map snippet relative coords -> Full Broadhseet Pixels
                        real_x = min(p[0] for p in coords) + snip['x_offset']
                        real_y = min(p[1] for p in coords) + snip['y_offset']
                        real_w = max(p[0] for p in coords) - min(p[0] for p in coords)
                        real_h = max(p[1] for p in coords) - min(p[1] for p in coords)

                        page_blocks.append({
                            "text": text,
                            "confidence": conf,
                            "bbox": {
                                "x": float(real_x),
                                "y": float(real_y),
                                "width": float(real_w),
                                "height": float(real_h)
                            },
                            # Sync field name 'column' with segment_articles.py
                            "column": snip.get('col_idx', snip.get('column', 0))
                        })
                    except (IndexError, TypeError):
                        continue

                # Memory cleanup after each snippet
                del img
                gc.collect()

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