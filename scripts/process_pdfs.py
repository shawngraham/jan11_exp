##!/usr/bin/env python3
"""
OCR Processing Script - Snippet Edition
Simply loops through the article snippets and runs .predict()
"""

import json
import gc
import cv2
import numpy as np
from pathlib import Path
from paddleocr import PaddleOCR

print("Initializing PaddleOCR...")
ocr = PaddleOCR(lang='en', use_angle_cls=False)

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int64, np.int32, np.float32, np.float64)):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir if (script_dir / "data").exists() else script_dir.parent
    preprocessed_dir = project_root / "data" / "preprocessed"
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(preprocessed_dir / "all_metadata.json", 'r') as f:
        all_metadata = json.load(f)

    all_results = []
    for pdf_meta in all_metadata:
        pdf_name = pdf_meta['source_pdf']
        print(f"\nOCRing Snippets for: {pdf_name}")
        pdf_entry = {"filename": pdf_name, "pages": []}

        for page_meta in pdf_meta['pages']:
            print(f"  Page {page_meta['page_num']}...", end="", flush=True)
            page_blocks = []
            
            for snip in page_meta['snippets']:
                img = cv2.imread(snip['path'])
                if img is None: continue
                
                # Predict on the individual article/snippet
                result = ocr.predict(img)
                
                # Handle the Paddle predict format
                # Usually: [ {'res': [[bbox, (text, conf)], ...]} ]
                for region in result:
                    lines = region.get('res', []) if isinstance(region, dict) else region
                    for line in lines:
                        text = line[1][0]
                        conf = float(line[1][1])
                        
                        # Map snippet coords -> Page coords
                        coords = line[0]
                        real_x = min(p[0] for p in coords) + snip['x_offset']
                        real_y = min(p[1] for p in coords) + snip['y_offset']
                        real_w = max(p[0] for p in coords) - min(p[0] for p in coords)
                        real_h = max(p[1] for p in coords) - min(p[1] for p in coords)

                        page_blocks.append({
                            "text": text,
                            "bbox": {"x": real_x, "y": real_y, "width": real_w, "height": real_h},
                            "column": snip['col_idx']
                        })
                gc.collect()

            pdf_entry["pages"].append({
                "page_number": page_meta['page_num'],
                "text_blocks": page_blocks
            })
            print(f" Done ({len(page_blocks)} lines)")

        all_results.append(pdf_entry)

    with open(output_dir / "ocr_output.json", 'w') as f:
        json.dump({"pdfs": all_results}, f, indent=2, cls=NumpyEncoder)

if __name__ == "__main__":
    main()