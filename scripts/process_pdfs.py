#!/usr/bin/env python3
"""
Step 2: OCR Processing
- Uses metadata from Preprocessing.
- Maps text back to PubID and Date.
"""

import json
import cv2
import numpy as np
from pathlib import Path
from paddleocr import PaddleOCR

def main():
    # Setup paths relative to the scripts folder
    project_root = Path(__file__).resolve().parent.parent
    preprocessed_dir = project_root / "data" / "preprocessed"
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize OCR
    ocr = PaddleOCR(lang='en', use_angle_cls=False)

    metadata_path = preprocessed_dir / "all_metadata.json"
    if not metadata_path.exists(): return

    with open(metadata_path, 'r') as f:
        all_metadata = json.load(f)

    final_output = []

    for pdf_meta in all_metadata:
        pdf_entry = {
            "pub_id": pdf_meta.get('pub_id'),
            "date": pdf_meta.get('pub_date'),
            "source": pdf_meta.get('source_pdf'),
            "pages": []
        }

        for page_meta in pdf_meta.get('pages', []):
            page_blocks = []
            print(f"OCR: {pdf_entry['source']} - Page {page_meta['page_num']}")

            for snip in page_meta.get('snippets', []):
                img = cv2.imread(snip['path'])
                if img is None: continue
                
                # Result call as requested
                result = ocr.predict(img)
                
                if not result or result[0] is None: continue

                for line in result[0]:
                    coords = line[0]
                    text, conf = line[1]

                    # Global Coordinate Mapping
                    x_off, y_off = snip['x_offset'], snip['y_offset']
                    real_x = min(p[0] for p in coords) + x_off
                    real_y = min(p[1] for p in coords) + y_off

                    page_blocks.append({
                        "text": text,
                        "conf": round(float(conf), 3),
                        "column": snip['column'],
                        "bbox": [int(real_x), int(real_y)]
                    })

            pdf_entry["pages"].append({
                "page": page_meta['page_num'],
                "blocks": page_blocks
            })

        final_output.append(pdf_entry)

    with open(output_dir / "ocr_results.json", "w") as f:
        json.dump(final_output, f, indent=2)

if __name__ == "__main__":
    main()