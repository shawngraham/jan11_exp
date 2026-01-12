#!/usr/bin/env python3
"""
OCR Processing Script for Preprocessed Column Images
Includes NumpyEncoder to fix JSON serialization errors.
"""

import os
import json
import sys
import gc
from pathlib import Path
import numpy as np
import easyocr

# --- THE FIX: Custom Encoder for NumPy types ---
class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

# Initialize EasyOCR reader
print("Initializing EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False, verbose=False)

def process_column_image(image_path, column_metadata):
    """Run OCR and return blocks with full-page coordinates."""
    img_p = Path(image_path)
    if not img_p.exists():
        return []

    x_offset = column_metadata['x_offset']

    try:
        # Using paragraph=True for faster/cleaner newspaper OCR
        result = reader.readtext(str(img_p), paragraph=True)
    except Exception as e:
        print(f" OCR Error: {e}")
        return []

    text_blocks = []
    for detection in result:
        # EasyOCR with paragraph=True returns (bbox, text)
        bbox, text = detection
        
        # Explicitly convert to standard floats to avoid int64 issues
        adjusted_bbox = [[float(p[0] + x_offset), float(p[1])] for p in bbox]
        
        x_coords = [p[0] for p in adjusted_bbox]
        y_coords = [p[1] for p in adjusted_bbox]

        text_blocks.append({
            "text": text,
            "bbox": {
                "x": min(x_coords),
                "y": min(y_coords),
                "width": max(x_coords) - min(x_coords),
                "height": max(y_coords) - min(y_coords)
            },
            "polygon": adjusted_bbox,
            "column": int(column_metadata['column_index'])
        })
    return text_blocks

def main():
    # Setup paths
    script_dir = Path(__file__).parent
    project_root = script_dir if (script_dir / "data").exists() else script_dir.parent
    
    preprocessed_dir = project_root / "data" / "preprocessed"
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = preprocessed_dir / "all_metadata.json"
    if not metadata_path.exists():
        print(f"Error: Missing {metadata_path}")
        sys.exit(1)

    with open(metadata_path, 'r') as f:
        all_metadata = json.load(f)

    all_results = []
    for pdf_meta in all_metadata:
        pdf_name = pdf_meta['source_pdf']
        print(f"Processing OCR for: {pdf_name}")
        
        pdf_data = {"filename": pdf_name, "pages": []}

        for page_meta in pdf_meta['pages']:
            print(f"  Page {page_meta['page_num']}...", end="", flush=True)
            all_text_blocks = []
            
            for col_meta in page_meta['columns']:
                blocks = process_column_image(col_meta['path'], col_meta)
                all_text_blocks.extend(blocks)
                gc.collect()
            
            pdf_data["pages"].append({
                "page_number": int(page_meta['page_num']),
                "text_blocks": all_text_blocks,
                "total_blocks": len(all_text_blocks)
            })
            print(f" Done ({len(all_text_blocks)} blocks)")

        all_results.append(pdf_data)

    # Save with the custom encoder
    output_file = output_dir / "ocr_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "pdfs": all_results,
            "ocr_engine": "EasyOCR (Paragraph Mode)"
        }, f, indent=2, ensure_ascii=False, cls=NumpyEncoder) # <-- CLS IS KEY

    print(f"\n✓ OCR Output saved to {output_file}")

if __name__ == "__main__":
    main()