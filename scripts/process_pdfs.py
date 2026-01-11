#!/usr/bin/env python3
"""
OCR Processing Script for Preprocessed Column Images

This script reads preprocessed column images and runs OCR on them.
It expects columns to already be split by preprocess.py.
"""

import os
import json
import sys
from pathlib import Path
import cv2
import numpy as np
import gc

# Import PaddleOCR with version detection
import paddleocr
print(f"PaddleOCR version: {paddleocr.__version__}")

version = paddleocr.__version__
major_version = int(version.split('.')[0])

if major_version >= 3:
    print("Using PaddleOCR 3.x")
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang='en')
else:
    print("Using PaddleOCR 2.x")
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang='en', use_angle_cls=True)


def process_column_image(image_path, column_metadata):
    """
    Run OCR on a single preprocessed column image.

    Args:
        image_path: Path to column image file
        column_metadata: Metadata dict with x_offset and other info

    Returns:
        List of text blocks with full-page coordinates
    """
    # Load image
    column_img = cv2.imread(str(image_path))

    if column_img is None:
        print(f"      Warning: Could not load {image_path}")
        return []

    x_offset = column_metadata['x_offset']

    # Run OCR
    try:
        result = ocr.ocr(column_img, cls=True)
    except:
        # Try without cls parameter if it fails
        try:
            result = ocr.ocr(column_img)
        except:
            print(f"      OCR failed for {image_path}")
            return []

    text_blocks = []

    if result and result[0]:
        for line in result[0]:
            bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = line[1][0]  # text content
            confidence = line[1][1]  # confidence score

            # Adjust x-coordinates back to full page coordinates
            adjusted_bbox = [[x + x_offset, y] for x, y in bbox]

            x_coords = [point[0] for point in adjusted_bbox]
            y_coords = [point[1] for point in adjusted_bbox]

            text_blocks.append({
                "text": text,
                "confidence": float(confidence),
                "bbox": {
                    "x": min(x_coords),
                    "y": min(y_coords),
                    "width": max(x_coords) - min(x_coords),
                    "height": max(y_coords) - min(y_coords)
                },
                "polygon": [[float(p[0]), float(p[1])] for p in adjusted_bbox],
                "column": column_metadata['column_index']
            })

    return text_blocks


def process_preprocessed_pdf(pdf_metadata, preprocessed_dir):
    """
    Process all columns from a preprocessed PDF.

    Args:
        pdf_metadata: Metadata dict from preprocessing
        preprocessed_dir: Base directory with preprocessed data

    Returns:
        Dictionary with OCR results
    """
    pdf_name = pdf_metadata['source_pdf']
    print(f"\nProcessing: {pdf_name}")
    print(f"  {pdf_metadata['num_pages']} pages at {pdf_metadata['dpi']} DPI")

    pdf_results = {
        "filename": pdf_name,
        "num_pages": pdf_metadata['num_pages'],
        "dpi": pdf_metadata['dpi'],
        "pages": []
    }

    # Process each page
    for page_meta in pdf_metadata['pages']:
        page_num = page_meta['page_num']
        print(f"  Page {page_num}/{pdf_metadata['num_pages']}...")

        all_text_blocks = []

        # Process each column
        for col_meta in page_meta['columns']:
            col_idx = col_meta['column_index']
            col_path = Path(col_meta['path'])

            print(f"    Column {col_idx + 1}/{len(page_meta['columns'])}...", end=" ", flush=True)

            # Run OCR on column
            column_blocks = process_column_image(col_path, col_meta)
            all_text_blocks.extend(column_blocks)

            print(f"{len(column_blocks)} blocks")

            # Memory cleanup after each column
            gc.collect()

        # Store page results
        page_results = {
            "page_number": page_num,
            "num_columns": len(page_meta['columns']),
            "column_boundaries": page_meta['boundaries'],
            "text_blocks": all_text_blocks,
            "total_blocks": len(all_text_blocks)
        }

        pdf_results["pages"].append(page_results)
        print(f"    Total: {len(all_text_blocks)} text blocks")

    return pdf_results


def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    preprocessed_dir = base_dir / "data" / "preprocessed"
    output_dir = base_dir / "data" / "raw"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if preprocessed data exists
    if not preprocessed_dir.exists():
        print(f"Error: Preprocessed directory not found at {preprocessed_dir}")
        print("Please run preprocess.py first to prepare the PDFs.")
        sys.exit(1)

    # Load combined metadata
    metadata_path = preprocessed_dir / "all_metadata.json"
    if not metadata_path.exists():
        print(f"Error: Metadata file not found at {metadata_path}")
        print("Please run preprocess.py first.")
        sys.exit(1)

    with open(metadata_path, 'r') as f:
        all_metadata = json.load(f)

    print(f"Found metadata for {len(all_metadata)} PDFs")
    print("=" * 60)

    # Process all PDFs
    all_results = []

    for pdf_metadata in all_metadata:
        result = process_preprocessed_pdf(pdf_metadata, preprocessed_dir)
        if result:
            all_results.append(result)

        # Force garbage collection between PDFs
        gc.collect()

    # Save consolidated results
    output_file = output_dir / "ocr_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_pdfs": len(all_results),
            "processing_method": "preprocessed column-based OCR",
            "pdfs": all_results
        }, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"Processing complete!")
    print(f"Results saved to {output_file}")

    # Print summary
    total_pages = sum(pdf["num_pages"] for pdf in all_results)
    total_blocks = sum(
        page["total_blocks"]
        for pdf in all_results
        for page in pdf["pages"]
    )

    print(f"\nSummary:")
    print(f"  PDFs processed: {len(all_results)}")
    print(f"  Total pages: {total_pages}")
    print(f"  Total text blocks: {total_blocks}")
    if total_pages > 0:
        print(f"  Average blocks per page: {total_blocks / total_pages:.1f}")


if __name__ == "__main__":
    main()
