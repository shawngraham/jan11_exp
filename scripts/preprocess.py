#!/usr/bin/env python3
"""
Preprocess PDFs: Resize, detect columns, and split into manageable chunks.

This script:
1. Converts PDFs to images at optimal DPI
2. Detects vertical column boundaries
3. Splits each page into columns
4. Saves column images (~4MB target per page)
5. Outputs metadata for OCR processing
"""

import os
import json
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import argparse
from pathlib import Path
import math

def calculate_optimal_dpi(pdf_path, target_mb=4):
    """
    Calculate DPI that results in images around target size.
    Start with 100 DPI and adjust based on actual file size.
    """
    # Try 100 DPI first to get a baseline
    try:
        test_images = convert_from_path(pdf_path, dpi=100, first_page=1, last_page=1)
        test_img = test_images[0]

        # Estimate file size (rough approximation)
        width, height = test_img.size
        pixels = width * height
        bytes_per_pixel = 3  # RGB
        estimated_mb = (pixels * bytes_per_pixel) / (1024 * 1024)

        # Adjust DPI to hit target
        if estimated_mb > 0:
            scale_factor = math.sqrt(target_mb / estimated_mb)
            optimal_dpi = int(100 * scale_factor)
            # Clamp between 75 and 200 DPI
            optimal_dpi = max(75, min(200, optimal_dpi))
        else:
            optimal_dpi = 100

        print(f"  Calculated optimal DPI: {optimal_dpi} (estimated {estimated_mb:.2f}MB at 100 DPI)")
        return optimal_dpi

    except Exception as e:
        print(f"  Warning: Could not calculate optimal DPI: {e}")
        return 100


def detect_column_boundaries(image_array, expected_columns=5):
    """
    Detect vertical column boundaries using line detection.
    Returns list of x-coordinates for column boundaries.
    """
    height, width = image_array.shape[:2]
    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)

    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detect lines using Hough transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=int(height * 0.3),
        minLineLength=int(height * 0.5),
        maxLineGap=int(height * 0.1)
    )

    if lines is None:
        print(f"    No vertical lines detected, using even division")
        return [int(width * i / expected_columns) for i in range(expected_columns + 1)]

    # Extract vertical lines (near 90 degrees)
    vertical_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Check if line is mostly vertical
        if abs(x2 - x1) < 20:  # Allow small horizontal deviation
            x_avg = (x1 + x2) / 2
            vertical_lines.append(x_avg)

    if len(vertical_lines) < 2:
        print(f"    Insufficient vertical lines detected ({len(vertical_lines)}), using even division")
        return [int(width * i / expected_columns) for i in range(expected_columns + 1)]

    # Cluster lines that are close together (within 20 pixels)
    vertical_lines.sort()
    clustered = []
    current_cluster = [vertical_lines[0]]

    for x in vertical_lines[1:]:
        if x - current_cluster[-1] < 20:
            current_cluster.append(x)
        else:
            clustered.append(sum(current_cluster) / len(current_cluster))
            current_cluster = [x]
    clustered.append(sum(current_cluster) / len(current_cluster))

    # Ensure we have boundaries at 0 and width
    boundaries = [0] + [int(x) for x in clustered if 0 < x < width] + [width]
    boundaries = sorted(list(set(boundaries)))

    print(f"    Detected {len(boundaries)-1} columns from {len(vertical_lines)} vertical lines")
    return boundaries


def split_into_columns(image_array, boundaries, margin=10):
    """
    Split image into columns based on detected boundaries.
    Returns list of (column_image, metadata) tuples.
    """
    columns = []
    height, width = image_array.shape[:2]

    for i in range(len(boundaries) - 1):
        x_start = max(0, boundaries[i] - margin)
        x_end = min(width, boundaries[i + 1] + margin)

        # Extract column
        column_img = image_array[:, x_start:x_end]

        metadata = {
            'column_index': i,
            'x_offset': x_start,
            'x_start': boundaries[i],
            'x_end': boundaries[i + 1],
            'width': x_end - x_start,
            'height': height
        }

        columns.append((column_img, metadata))

    return columns


def preprocess_pdf(pdf_path, output_dir, dpi=None):
    """
    Preprocess a single PDF: convert to images, detect columns, split and save.
    """
    pdf_name = Path(pdf_path).stem
    print(f"\nProcessing: {pdf_name}")

    # Calculate optimal DPI if not specified
    if dpi is None:
        dpi = calculate_optimal_dpi(pdf_path)

    # Convert PDF to images
    print(f"  Converting PDF at {dpi} DPI...")
    images = convert_from_path(pdf_path, dpi=dpi)
    print(f"  Converted {len(images)} pages")

    # Create output directory for this PDF
    pdf_output_dir = Path(output_dir) / pdf_name
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    # Store metadata for all pages
    pdf_metadata = {
        'source_pdf': pdf_name,
        'dpi': dpi,
        'num_pages': len(images),
        'pages': []
    }

    # Process each page
    for page_num, image in enumerate(images, start=1):
        print(f"  Page {page_num}/{len(images)}...")

        # Convert PIL to numpy array
        image_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Detect columns
        boundaries = detect_column_boundaries(image_array)

        # Split into columns
        columns = split_into_columns(image_array, boundaries)

        # Save each column
        page_metadata = {
            'page_num': page_num,
            'boundaries': boundaries,
            'columns': []
        }

        for column_img, col_meta in columns:
            # Generate filename
            col_filename = f"{pdf_name}_p{page_num:03d}_c{col_meta['column_index']:02d}.png"
            col_path = pdf_output_dir / col_filename

            # Save column image
            cv2.imwrite(str(col_path), column_img)

            # Add to metadata
            col_meta['filename'] = col_filename
            col_meta['path'] = str(col_path)
            page_metadata['columns'].append(col_meta)

        pdf_metadata['pages'].append(page_metadata)
        print(f"    Saved {len(columns)} columns")

    # Save metadata
    metadata_path = pdf_output_dir / 'metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(pdf_metadata, f, indent=2)

    print(f"  ✓ Completed: {pdf_name} - {len(images)} pages, metadata saved")
    return pdf_metadata


def main():
    parser = argparse.ArgumentParser(description='Preprocess PDFs for OCR')
    parser.add_argument('--input-dir', default='pdfs',
                        help='Directory containing PDFs')
    parser.add_argument('--output-dir', default='data/preprocessed',
                        help='Directory for preprocessed column images')
    parser.add_argument('--dpi', type=int, default=None,
                        help='DPI for conversion (auto-calculated if not specified)')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all PDFs
    pdf_files = sorted(input_dir.glob('*.pdf'))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return

    print(f"Found {len(pdf_files)} PDFs to preprocess")

    # Process each PDF
    all_metadata = []
    for pdf_path in pdf_files:
        try:
            metadata = preprocess_pdf(pdf_path, output_dir, args.dpi)
            all_metadata.append(metadata)
        except Exception as e:
            print(f"  ✗ Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()

    # Save combined metadata
    combined_metadata_path = output_dir / 'all_metadata.json'
    with open(combined_metadata_path, 'w') as f:
        json.dump(all_metadata, f, indent=2)

    print(f"\n✓ Preprocessing complete!")
    print(f"  Processed {len(all_metadata)} PDFs")
    print(f"  Output directory: {output_dir}")
    print(f"  Combined metadata: {combined_metadata_path}")


if __name__ == '__main__':
    main()
