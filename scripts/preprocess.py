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


def smooth_projection(projection, window_size=15):
    """
    Smooth projection profile using moving average.
    Reduces noise while preserving valley/peak structure.
    """
    kernel = np.ones(window_size) / window_size
    return np.convolve(projection, kernel, mode='same')


def find_valleys(projection, expected_columns=5, min_valley_depth=0.1):
    """
    Find valleys in projection profile that represent column gaps.

    Args:
        projection: 1D array of vertical projection values
        expected_columns: Expected number of columns
        min_valley_depth: Minimum depth of valley relative to peak (0-1)

    Returns:
        List of x-coordinates for valley centers (column boundaries)
    """
    # Invert projection so valleys become peaks
    inverted = -projection

    # Normalize to 0-1 range
    if inverted.max() > inverted.min():
        inverted = (inverted - inverted.min()) / (inverted.max() - inverted.min())

    # Find local maxima in inverted projection (= valleys in original)
    valleys = []

    # Simple peak detection: find points higher than neighbors
    for i in range(1, len(inverted) - 1):
        if inverted[i] > inverted[i-1] and inverted[i] > inverted[i+1]:
            # Check if valley is deep enough
            if inverted[i] > min_valley_depth:
                valleys.append(i)

    # If we found reasonable number of valleys, return them
    # We expect (expected_columns - 1) gaps between columns
    expected_gaps = expected_columns - 1

    if len(valleys) >= expected_gaps - 1:  # Allow 1 missing
        # Sort by depth and take the deepest ones
        valley_depths = [(v, inverted[v]) for v in valleys]
        valley_depths.sort(key=lambda x: x[1], reverse=True)

        # Take top expected_gaps valleys
        top_valleys = [v[0] for v in valley_depths[:expected_gaps]]
        top_valleys.sort()

        return top_valleys

    return None


def detect_column_boundaries(image_array, expected_columns=5, debug=False, debug_path=None):
    """
    Detect vertical column boundaries using projection profile method.

    This method:
    1. Binarizes the image
    2. Creates vertical projection profile (sum of dark pixels per column)
    3. Smooths the profile to reduce noise
    4. Finds valleys (column gaps) in the profile

    Args:
        image_array: Input image (BGR or grayscale)
        expected_columns: Expected number of columns
        debug: If True, save visualization
        debug_path: Path to save debug image

    Returns:
        List of x-coordinates for column boundaries [0, x1, x2, ..., width]
    """
    height, width = image_array.shape[:2]

    # Convert to grayscale if needed
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_array

    # Binarize using Otsu's method
    # This makes text/lines black (0) and background white (255)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Create vertical projection profile
    # Sum each column - higher values = more dark pixels (text/lines)
    projection = np.sum(binary, axis=0)

    # Smooth to reduce noise
    smoothed = smooth_projection(projection, window_size=int(width / 100))

    # Find valleys (column gaps)
    valleys = find_valleys(smoothed, expected_columns=expected_columns)

    # Debug visualization
    if debug and debug_path:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8))

        # Plot projection profile
        ax1.plot(projection, label='Raw projection', alpha=0.3)
        ax1.plot(smoothed, label='Smoothed projection', linewidth=2)
        if valleys:
            ax1.scatter(valleys, smoothed[valleys], color='red', s=100,
                       zorder=5, label='Detected gaps')
        ax1.set_xlabel('X Position (pixels)')
        ax1.set_ylabel('Darkness (sum of pixels)')
        ax1.set_title('Vertical Projection Profile')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Show image with detected boundaries
        display_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        if valleys:
            for v in valleys:
                cv2.line(display_img, (v, 0), (v, height), (0, 0, 255), 2)
        ax2.imshow(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB))
        ax2.set_title('Detected Column Boundaries')
        ax2.axis('off')

        plt.tight_layout()
        plt.savefig(debug_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"      Debug visualization saved to {debug_path}")

    # Convert valleys to boundaries
    if valleys and len(valleys) >= expected_columns - 2:  # Allow some tolerance
        boundaries = [0] + valleys + [width]
        boundaries = sorted(list(set(boundaries)))
        print(f"    Detected {len(boundaries)-1} columns using projection profile")
        return boundaries

    # Fallback: divide evenly
    print(f"    Could not detect columns reliably, using even division")
    boundaries = [int(width * i / expected_columns) for i in range(expected_columns + 1)]
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


def preprocess_pdf(pdf_path, output_dir, dpi=None, debug=False):
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

    # Create debug directory if needed
    if debug:
        debug_dir = pdf_output_dir / 'debug'
        debug_dir.mkdir(exist_ok=True)

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

        # Detect columns with optional debug visualization
        debug_path = None
        if debug:
            debug_path = pdf_output_dir / 'debug' / f'page_{page_num:03d}_detection.png'

        boundaries = detect_column_boundaries(
            image_array,
            expected_columns=5,
            debug=debug,
            debug_path=debug_path
        )

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
    parser.add_argument('--debug', action='store_true',
                        help='Save debug visualizations showing column detection')
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
    if args.debug:
        print("Debug mode enabled - will save column detection visualizations")

    # Process each PDF
    all_metadata = []
    for pdf_path in pdf_files:
        try:
            metadata = preprocess_pdf(pdf_path, output_dir, args.dpi, debug=args.debug)
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
