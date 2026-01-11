#!/usr/bin/env python3
"""
OCR Processing Script for Shawville Equity Newspapers
Column-based approach: Detects vertical lines, splits into columns, processes separately
This manages memory by processing one column at a time
"""

import os
import json
import sys
from pathlib import Path
from pdf2image import convert_from_path
import numpy as np
import cv2
from PIL import Image

# Increase PIL's decompression bomb limit for large newspaper scans
Image.MAX_IMAGE_PIXELS = 500000000

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


def detect_column_boundaries(image_array, expected_columns=5):
    """
    Detect vertical column boundaries using line detection

    Args:
        image_array: numpy array of image (grayscale)
        expected_columns: expected number of columns (default 5)

    Returns:
        List of x-coordinates representing column boundaries
    """
    print(f"    Detecting {expected_columns} column boundaries...")

    height, width = image_array.shape[:2]

    # Convert to grayscale if needed
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_array

    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detect vertical lines using Hough Line Transform
    # We're looking for long vertical lines
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=int(height * 0.3),  # Line must span at least 30% of height
        minLineLength=int(height * 0.5),  # At least 50% of page height
        maxLineGap=int(height * 0.1)  # Allow 10% gaps
    )

    # Extract vertical line x-coordinates
    vertical_lines = []

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Check if line is mostly vertical (angle within 10 degrees of vertical)
            if abs(x2 - x1) < 20:  # Nearly vertical
                x_avg = (x1 + x2) // 2
                vertical_lines.append(x_avg)

    # Cluster nearby lines (within 50 pixels)
    if vertical_lines:
        vertical_lines.sort()
        clustered_lines = []
        current_cluster = [vertical_lines[0]]

        for x in vertical_lines[1:]:
            if x - current_cluster[-1] < 50:
                current_cluster.append(x)
            else:
                # Take median of cluster
                clustered_lines.append(int(np.median(current_cluster)))
                current_cluster = [x]

        # Don't forget last cluster
        clustered_lines.append(int(np.median(current_cluster)))

        print(f"      Found {len(clustered_lines)} vertical dividers at x={clustered_lines}")

        # If we found lines, use them
        if len(clustered_lines) >= expected_columns - 1:
            # Add page boundaries
            boundaries = [0] + clustered_lines + [width]
            return sorted(set(boundaries))

    # Fallback: divide page evenly into expected columns
    print(f"      Fallback: dividing page evenly into {expected_columns} columns")
    column_width = width // expected_columns
    boundaries = [i * column_width for i in range(expected_columns + 1)]
    boundaries[-1] = width  # Ensure last boundary is exactly page width

    return boundaries


def split_into_columns(image_array, boundaries):
    """
    Split image into columns based on boundaries

    Args:
        image_array: numpy array of full page image
        boundaries: list of x-coordinates for column divisions

    Returns:
        List of (column_image, x_offset) tuples
    """
    columns = []

    for i in range(len(boundaries) - 1):
        x_start = boundaries[i]
        x_end = boundaries[i + 1]

        # Extract column with small margins to avoid cutting text
        margin = 10
        x_start_with_margin = max(0, x_start - margin)
        x_end_with_margin = min(image_array.shape[1], x_end + margin)

        column_img = image_array[:, x_start_with_margin:x_end_with_margin]

        columns.append({
            'image': column_img,
            'x_offset': x_start_with_margin,
            'column_index': i,
            'width': x_end_with_margin - x_start_with_margin
        })

    return columns


def process_column_ocr(column_data):
    """
    Run OCR on a single column

    Args:
        column_data: dict with 'image', 'x_offset', 'column_index'

    Returns:
        List of text blocks with adjusted coordinates
    """
    column_img = column_data['image']
    x_offset = column_data['x_offset']

    # Run OCR on column
    try:
        result = ocr.ocr(column_img, cls=True)
    except:
        # Try without cls parameter if it fails
        try:
            result = ocr.predict(column_img)
        except:
            result = ocr.ocr(column_img)

    text_blocks = []

    if result and result[0]:
        for line in result[0]:
            bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = line[1][0]  # text content
            confidence = line[1][1]  # confidence score

            # Adjust x-coordinates to full page coordinates
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
                "column": column_data['column_index']
            })

    return text_blocks


def process_pdf(pdf_path, output_dir):
    """
    Process a single PDF file using column-based approach

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save processed images

    Returns:
        Dictionary with OCR results for all pages
    """
    pdf_name = Path(pdf_path).stem
    print(f"Processing {pdf_name}...")

    # Convert PDF to images at 150 DPI (manageable for columns)
    try:
        images = convert_from_path(pdf_path, dpi=150)
        print(f"  Converted {len(images)} pages at 150 DPI")
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

        # Save full page image
        img_path = os.path.join(output_dir, f"{pdf_name}_page_{page_num}.jpg")
        image.save(img_path, 'JPEG')

        # Convert to numpy array
        img_array = np.array(image)

        # Detect column boundaries
        boundaries = detect_column_boundaries(img_array, expected_columns=5)

        # Split into columns
        columns = split_into_columns(img_array, boundaries)
        print(f"      Split into {len(columns)} columns")

        # Process each column separately (memory efficient)
        all_text_blocks = []

        for col_idx, column_data in enumerate(columns):
            print(f"      Processing column {col_idx + 1}/{len(columns)}...", end=" ")

            # OCR this column
            column_blocks = process_column_ocr(column_data)
            all_text_blocks.extend(column_blocks)

            print(f"{len(column_blocks)} blocks")

            # Free memory
            del column_data['image']

        # Store page results
        page_results = {
            "page_number": page_num,
            "image_path": img_path,
            "image_width": image.width,
            "image_height": image.height,
            "num_columns": len(columns),
            "column_boundaries": boundaries,
            "text_blocks": all_text_blocks,
            "total_blocks": len(all_text_blocks)
        }

        pdf_results["pages"].append(page_results)
        print(f"    Total: {len(all_text_blocks)} text blocks from {len(columns)} columns")

        # Free memory
        del img_array
        del columns

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

        # Force garbage collection between PDFs
        import gc
        gc.collect()

    # Save consolidated results
    output_file = output_dir / "ocr_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_pdfs": len(all_results),
            "processing_method": "column-based with vertical line detection",
            "dpi": 150,
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
    )

    print(f"\nSummary:")
    print(f"  PDFs processed: {len(all_results)}")
    print(f"  Total pages: {total_pages}")
    print(f"  Total text blocks: {total_blocks}")
    print(f"  Average blocks per page: {total_blocks / total_pages:.1f}")


if __name__ == "__main__":
    main()
