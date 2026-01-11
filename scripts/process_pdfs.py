#!/usr/bin/env python3
"""
OCR Processing Script for Shawville Equity Newspapers
Converts PDFs to images and extracts text with bounding boxes using PaddleOCR
Now uses PPStructure for automatic newspaper layout analysis
"""

import os
import json
import sys
from pathlib import Path
from pdf2image import convert_from_path
import numpy as np
import paddleocr
from PIL import Image
import gc
from pdf2image import pdfinfo_from_path, convert_from_path

# Increase PIL's decompression bomb limit for large newspaper scans
# Default is ~178 MP, we're increasing to 500 MP to handle high-res PDFs
Image.MAX_IMAGE_PIXELS = 500000000

print(f"PaddleOCR version: {paddleocr.__version__}")

# Detect version and use appropriate OCR engine
version = paddleocr.__version__
major_version = int(version.split('.')[0])

if major_version >= 3:
    # PaddleOCR 3.x - use PPStructureV3 with newspaper layout model
    print("Using PaddleOCR 3.x with PPStructureV3 (newspaper layout analysis)")
    from paddleocr import PPStructureV3

    try:
        # Try newspaper-specific layout model first
        ocr = PPStructureV3(
            layout_model='picodet_lcnet_x1_0_layout_newspaper',
            lang='en',
            max_side_limit=8000, # Increase this from default 4000
            limit_type='max'    # Ensure it uses the max side
        )
        print("✓ Loaded newspaper layout model")
    except Exception as e:
        print(f"Note: Newspaper model not available, using default layout model")
        print(f"  Error: {e}")
        ocr = PPStructureV3(
            lang='en'
        )
    USE_STRUCTURE = True
else:
    # PaddleOCR 2.x - use standard OCR (no structure analysis)
    print("Using PaddleOCR 2.x (standard OCR, no layout analysis)")
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(
        lang='en',
        use_angle_cls=True
    )
    USE_STRUCTURE = False

def process_structure_result(result):
    """
    Process PPStructure result (PaddleOCR 3.x with layout analysis)

    PPStructure returns: [
        {
            'type': 'text',  # or 'title', 'figure', 'table'
            'bbox': [x1, y1, x2, y2],
            'res': [  # OCR results for this region
                {'text': '...', 'confidence': 0.95, ...}
            ]
        },
        ...
    ]
    """
    text_blocks = []

    for region in result:
        region_type = region.get('type', 'unknown')
        bbox = region.get('bbox', [0, 0, 0, 0])

        # Get OCR results from this region
        res = region.get('res', [])

        for item in res:
            if isinstance(item, dict) and 'text' in item:
                # Extract text and coordinates
                text = item.get('text', '')
                confidence = item.get('confidence', 0.0)

                # Get text-level bounding box if available
                text_bbox = item.get('text_region', bbox)

                if isinstance(text_bbox, list) and len(text_bbox) >= 4:
                    if isinstance(text_bbox[0], list):
                        # Polygon format: [[x1,y1], [x2,y2], ...]
                        x_coords = [p[0] for p in text_bbox]
                        y_coords = [p[1] for p in text_bbox]
                        x, y = min(x_coords), min(y_coords)
                        width = max(x_coords) - x
                        height = max(y_coords) - y
                        polygon = [[float(p[0]), float(p[1])] for p in text_bbox]
                    else:
                        # Box format: [x1, y1, x2, y2]
                        x, y, x2, y2 = text_bbox
                        width = x2 - x
                        height = y2 - y
                        polygon = [[x, y], [x2, y], [x2, y2], [x, y2]]
                else:
                    # Fallback to region bbox
                    x, y, x2, y2 = bbox
                    width = x2 - x
                    height = y2 - y
                    polygon = [[x, y], [x2, y], [x2, y2], [x, y2]]

                text_blocks.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": {
                        "x": float(x),
                        "y": float(y),
                        "width": float(width),
                        "height": float(height)
                    },
                    "polygon": polygon,
                    "region_type": region_type  # text, title, figure, etc.
                })

    return text_blocks

def extract_layout_info(result):
    """Extract layout region information from PPStructure result"""
    layout_regions = []

    for idx, region in enumerate(result):
        region_type = region.get('type', 'unknown')
        bbox = region.get('bbox', [0, 0, 0, 0])

        if len(bbox) >= 4:
            layout_regions.append({
                "region_id": idx,
                "type": region_type,
                "bbox": {
                    "x": float(bbox[0]),
                    "y": float(bbox[1]),
                    "width": float(bbox[2] - bbox[0]),
                    "height": float(bbox[3] - bbox[1])
                }
            })

    return layout_regions

def process_standard_result(result):
    """
    Process standard OCR result (PaddleOCR 2.x)

    Standard format: [
        [
            [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],  # bbox
            ('text', confidence)  # text and score
        ],
        ...
    ]
    """
    text_blocks = []

    if result and result[0]:
        for line in result[0]:
            bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = line[1][0]  # text content
            confidence = line[1][1]  # confidence score

            # Calculate bounding box dimensions
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]

            text_blocks.append({
                "text": text,
                "confidence": float(confidence),
                "bbox": {
                    "x": min(x_coords),
                    "y": min(y_coords),
                    "width": max(x_coords) - min(x_coords),
                    "height": max(y_coords) - min(y_coords)
                },
                "polygon": [[float(p[0]), float(p[1])] for p in bbox],
                "region_type": "text"  # Default for standard OCR
            })

    return text_blocks

def process_pdf(pdf_path, output_dir):
    """
    M1 Silicon Optimized PDF Processor
    """
    pdf_name = Path(pdf_path).stem
    print(f"Processing {pdf_name}...")

    # 1. Get page count without loading images (Saves RAM)
    try:
        info = pdfinfo_from_path(pdf_path)
        num_pages = info["Pages"]
    except Exception as e:
        print(f"Poppler error: {e}. Try 'brew install poppler'")
        return None

    # 150 DPI is the 'sweet spot' for newspapers on M1 (16GB RAM)
    # If you have an 8GB Mac Mini, consider dropping this to 130
    dpi = 150 if USE_STRUCTURE else 130

    pdf_results = {
        "filename": pdf_name,
        "source_pdf": pdf_path,
        "num_pages": num_pages,
        "pages": []
    }

    for page_num in range(1, num_pages + 1):
        print(f"  Page {page_num}/{num_pages}...")

        try:
            # 2. Convert ONLY the current page
            page_images = convert_from_path(
                pdf_path, 
                dpi=dpi, 
                first_page=page_num, 
                last_page=page_num,
                thread_count=1 # M1 is fast; 1 thread keeps memory stable
            )
            
            if not page_images: continue
            image = page_images[0]
            
            # 3. Save and prepare
            img_path = os.path.join(output_dir, f"{pdf_name}_page_{page_num}.jpg")
            image.save(img_path, 'JPEG')
            img_array = np.array(image)

            # 4. OCR Step (Fixed for PaddleOCR 3.0)
            if USE_STRUCTURE:
                # Use .predict() for V3
                # Add 'slice' if you still get memory crashes on specific large pages
                result = ocr.predict(img_array)
                text_blocks = process_structure_result(result)
                layout_info = extract_layout_info(result)
            else:
                result = ocr.ocr(img_array, cls=True)
                text_blocks = process_standard_result(result)
                layout_info = None

            pdf_results["pages"].append({
                "page_number": page_num,
                "image_path": img_path,
                "image_width": image.width,
                "image_height": image.height,
                "text_blocks": text_blocks,
                "total_blocks": len(text_blocks),
                "layout_regions": layout_info
            })

            # 5. AGGRESSIVE CLEANUP (Required for M1 Unified Memory)
            del img_array
            del image
            del page_images
            gc.collect() 

        except Exception as e:
            print(f"  ! Error on page {page_num}: {e}")
            pdf_results["pages"].append({"page_number": page_num, "error": str(e)})

    return pdf_results

def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    pdf_dir = base_dir / "pdfs"
    output_dir = base_dir / "data" / "raw"
    images_dir = output_dir / "images"

    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Check if PDF directory exists
    if not pdf_dir.exists():
        print(f"Error: PDF directory not found at {pdf_dir}")
        print("Please create the 'pdfs' folder and add your PDF files.")
        sys.exit(1)

    # Find all PDFs
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF files")
    print("=" * 60)

    # Process all PDFs
    all_results = []

    for pdf_file in sorted(pdf_files):
        result = process_pdf(str(pdf_file), str(images_dir))
        if result:
            all_results.append(result)

    # Save consolidated results
    output_file = output_dir / "ocr_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_pdfs": len(all_results),
            "processed_date": None,  # Can add timestamp if needed
            "pdfs": all_results
        }, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"Processing complete!")
    print(f"Results saved to {output_file}")
    print(f"Images saved to {images_dir}")

    # Print summary
    total_pages = sum(pdf["num_pages"] for pdf in all_results)
    total_blocks = sum(
        page["total_blocks"]
        for pdf in all_results
        for page in pdf["pages"]
        if "total_blocks" in page
    )

    print(f"\nSummary:")
    print(f"  PDFs processed: {len(all_results)}")
    print(f"  Total pages: {total_pages}")
    print(f"  Total text blocks: {total_blocks}")

if __name__ == "__main__":
    main()
