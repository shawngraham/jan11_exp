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


def find_peaks(projection, expected_columns=5, min_peak_height=0.2):
    """
    Find peaks in projection profile that represent vertical black divider lines.

    Args:
        projection: 1D array of vertical projection values
        expected_columns: Expected number of columns
        min_peak_height: Minimum height of peak relative to max (0-1)

    Returns:
        List of x-coordinates for peak centers (column divider lines)
    """
    # Normalize to 0-1 range
    if projection.max() > projection.min():
        normalized = (projection - projection.min()) / (projection.max() - projection.min())
    else:
        return None

    # Find local maxima (peaks = black vertical lines)
    peaks = []

    # Simple peak detection: find points higher than neighbors
    for i in range(1, len(normalized) - 1):
        if normalized[i] > normalized[i-1] and normalized[i] > normalized[i+1]:
            # Check if peak is tall enough
            if normalized[i] > min_peak_height:
                peaks.append(i)

    # We expect (expected_columns - 1) divider lines between columns
    expected_dividers = expected_columns - 1

    if len(peaks) >= expected_dividers - 1:  # Allow 1 missing
        # Sort by height and take the tallest ones (most prominent black lines)
        peak_heights = [(p, normalized[p]) for p in peaks]
        peak_heights.sort(key=lambda x: x[1], reverse=True)

        # Take top expected_dividers peaks
        top_peaks = [p[0] for p in peak_heights[:expected_dividers]]
        top_peaks.sort()

        return top_peaks

    return None


def detect_column_boundaries(image_array, expected_columns=5, debug=False, debug_path=None):
    """
    Detect vertical column boundaries by finding black vertical divider lines.

    This method:
    1. Binarizes the image
    2. Uses morphological operations to enhance vertical lines
    3. Creates projection profile from vertical lines only
    4. Finds peaks (black divider lines) in the profile

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
    # This makes text/lines black (255) and background white (0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological operation to enhance VERTICAL lines specifically
    # Create a vertical kernel (1 pixel wide, tall height)
    # This will only match vertical structures like column dividers
    vertical_kernel_height = max(height // 20, 50)  # At least 50 pixels tall
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_kernel_height))

    # Apply morphological opening to extract vertical lines
    # This removes horizontal lines and text, keeping only vertical structures
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

    # Additionally, use closing to connect broken vertical lines
    vertical_lines = cv2.morphologyEx(vertical_lines, cv2.MORPH_CLOSE, vertical_kernel)

    # Create vertical projection profile from ONLY the vertical lines
    # Sum each column - higher values = more vertical line pixels
    projection = np.sum(vertical_lines, axis=0)

    # Smooth to reduce noise
    smoothed = smooth_projection(projection, window_size=int(width / 100))

    # Find peaks (black divider lines)
    peaks = find_peaks(smoothed, expected_columns=expected_columns, min_peak_height=0.2)

    # Debug visualization
    if debug and debug_path:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # Original image
        ax1.imshow(cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB))
        ax1.set_title('Original Image')
        ax1.axis('off')

        # Enhanced vertical lines
        ax2.imshow(vertical_lines, cmap='gray')
        ax2.set_title('Enhanced Vertical Lines (Morphological)')
        ax2.axis('off')

        # Plot projection profile
        ax3.plot(projection, label='Raw projection', alpha=0.3)
        ax3.plot(smoothed, label='Smoothed projection', linewidth=2)
        if peaks:
            ax3.scatter(peaks, smoothed[peaks], color='red', s=100,
                       zorder=5, label='Detected divider lines')
        ax3.set_xlabel('X Position (pixels)')
        ax3.set_ylabel('Darkness (vertical line pixels)')
        ax3.set_title('Vertical Line Projection Profile')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Show image with detected boundaries
        display_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        if peaks:
            for p in peaks:
                cv2.line(display_img, (p, 0), (p, height), (0, 0, 255), 3)
        ax4.imshow(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB))
        ax4.set_title('Detected Column Dividers')
        ax4.axis('off')

        plt.tight_layout()
        plt.savefig(debug_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"      Debug visualization saved to {debug_path}")

    # Convert peaks (divider lines) to boundaries
    if peaks and len(peaks) >= expected_columns - 2:  # Allow some tolerance
        boundaries = [0] + peaks + [width]
        boundaries = sorted(list(set(boundaries)))
        print(f"    Detected {len(boundaries)-1} columns using vertical line detection")
        return boundaries

    # Fallback: divide evenly
    print(f"    Could not detect column dividers reliably, using even division")
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
