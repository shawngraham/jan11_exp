#!/usr/bin/env python3
"""
OCR Processing Script for Shawville Equity Newspapers
Converts PDFs to images and extracts text with bounding boxes using PaddleOCR
"""

import os
import json
import sys
from pathlib import Path
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import numpy as np

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)

def process_pdf(pdf_path, output_dir):
    """
    Process a single PDF file

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save processed images

    Returns:
        Dictionary with OCR results for all pages
    """
    pdf_name = Path(pdf_path).stem
    print(f"Processing {pdf_name}...")

    # Convert PDF to images
    try:
        images = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"Error converting PDF {pdf_name}: {e}")
        return None

    pdf_results = {
        "filename": pdf_name,
        "source_pdf": pdf_path,
        "num_pages": len(images),
        "pages": []
    }

    # Process each page
    for page_num, image in enumerate(images, 1):
        print(f"  Processing page {page_num}/{len(images)}...")

        # Save page image
        img_path = os.path.join(output_dir, f"{pdf_name}_page_{page_num}.jpg")
        image.save(img_path, 'JPEG')

        # Convert PIL image to numpy array for PaddleOCR
        img_array = np.array(image)

        # Run OCR
        try:
            result = ocr.ocr(img_array, cls=True)

            # Extract text blocks with bounding boxes
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
                        "polygon": [[float(p[0]), float(p[1])] for p in bbox]
                    })

            page_results = {
                "page_number": page_num,
                "image_path": img_path,
                "image_width": image.width,
                "image_height": image.height,
                "text_blocks": text_blocks,
                "total_blocks": len(text_blocks)
            }

            pdf_results["pages"].append(page_results)
            print(f"    Found {len(text_blocks)} text blocks")

        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            pdf_results["pages"].append({
                "page_number": page_num,
                "error": str(e)
            })

    return pdf_results

def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    pdf_dir = base_dir / "pdf"
    output_dir = base_dir / "data" / "raw"
    images_dir = output_dir / "images"

    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Check if PDF directory exists
    if not pdf_dir.exists():
        print(f"Error: PDF directory not found at {pdf_dir}")
        print("Please create the 'pdf' folder and add your PDF files.")
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
