#!/usr/bin/env python3
"""
OCR Processing Script for Preprocessed Column Images

This script reads preprocessed column images and runs OCR on them using EasyOCR.
It expects columns to already be split by preprocess.py.

Pipeline flow:
  preprocess.py -> column images in data/preprocessed/
  process_pdfs.py -> OCR results in data/raw/ocr_output.json
  segment_articles.py -> segmented articles in data/processed/articles.json
"""

import os
import json
import sys
from pathlib import Path
import gc

# EasyOCR for text recognition
import easyocr

# Initialize EasyOCR reader (once, globally)
print("Initializing EasyOCR...")
print("  Loading English language model...")

# Use CPU mode for M1 compatibility and memory efficiency
reader = easyocr.Reader(['en'], gpu=False, verbose=False)
print("  ✓ EasyOCR ready")


def process_column_image(image_path, column_metadata):
    """
    Run OCR on a single preprocessed column image.

    Args:
        image_path: Path to column image file
        column_metadata: Metadata dict with x_offset and other info

    Returns:
        List of text blocks with full-page coordinates
    """
    # Verify image exists
    if not Path(image_path).exists():
        print(f"      Warning: Image not found {image_path}")
        return []

    x_offset = column_metadata['x_offset']

    # Run OCR using EasyOCR
    try:
        # readtext returns: list of (bbox, text, confidence)
        # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        result = reader.readtext(str(image_path))
    except Exception as e:
        print(f"      OCR failed for {image_path}: {e}")
        return []

    text_blocks = []

    for detection in result:
        bbox, text, confidence = detection

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
        print("")
        print("Usage:")
        print("  python3 scripts/preprocess.py --input-dir pdfs --output-dir data/preprocessed")
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
        try:
            result = process_preprocessed_pdf(pdf_metadata, preprocessed_dir)
            if result:
                all_results.append(result)
        except Exception as e:
            print(f"  ✗ Error processing {pdf_metadata.get('source_pdf', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()

        # Force garbage collection between PDFs
        gc.collect()

    # Save consolidated results
    output_file = output_dir / "ocr_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_pdfs": len(all_results),
            "processing_method": "EasyOCR with preprocessed column-based approach",
            "ocr_engine": "EasyOCR",
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

    print(f"\nNext step:")
    print(f"  Run segment_articles.py to segment the OCR results into articles")


if __name__ == "__main__":
    main()
