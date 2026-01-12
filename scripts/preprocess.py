#!/usr/bin/env python3
"""
Preprocess PDFs: Resize, detect columns, and split into manageable chunks.

Enhanced version with:
1. Adaptive ROI (Masthead skipping on Page 1)
2. Hybrid Gutter + Line detection
3. Scipy-based robust peak detection
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
from scipy.signal import find_peaks

def calculate_optimal_dpi(pdf_path, target_mb=4):
    """Calculate DPI that results in images around target size."""
    try:
        test_images = convert_from_path(pdf_path, dpi=100, first_page=1, last_page=1)
        test_img = test_images[0]
        width, height = test_img.size
        pixels = width * height
        bytes_per_pixel = 3
        estimated_mb = (pixels * bytes_per_pixel) / (1024 * 1024)

        if estimated_mb > 0:
            scale_factor = math.sqrt(target_mb / estimated_mb)
            optimal_dpi = int(100 * scale_factor)
            optimal_dpi = max(75, min(200, optimal_dpi))
        else:
            optimal_dpi = 100

        print(f"  Calculated optimal DPI: {optimal_dpi}")
        return optimal_dpi
    except Exception as e:
        print(f"  Warning: Could not calculate optimal DPI: {e}")
        return 100

def detect_column_boundaries(image_array, page_num=1, expected_columns=5, debug=False, debug_path=None):
    """
    Detect vertical column boundaries using a hybrid of vertical lines and whitespace gutters.
    """
    height, width = image_array.shape[:2]

    # 1. Preprocessing
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_array

    # Binarize: Text/Lines become 255 (white), Background becomes 0 (black)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 2. Adaptive ROI
    # Page 1 usually has a large masthead (title). We skip the top ~18%.
    # Interior pages only need a small margin skip to avoid headers.
    roi_top = int(height * 0.18) if page_num == 1 else int(height * 0.05)
    roi_bottom = int(height * 0.98)
    roi = binary[roi_top:roi_bottom, :]

    # 3. Signal A: Vertical Line Detection (Morphology)
    # Extracts physical black divider lines
    line_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 100))
    line_mask = cv2.morphologyEx(roi, cv2.MORPH_OPEN, line_kernel)
    line_signal = np.sum(line_mask, axis=0)
    
    # 4. Signal B: Gutter Detection (Whitespace)
    # Smears text horizontally; vertical gaps with 0 pixels are the gutters
    gutter_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    smeared = cv2.dilate(roi, gutter_kernel, iterations=1)
    gutter_signal = np.sum(smeared, axis=0)

    # 5. Hybrid Scoring
    # Normalize signals to 0.0 - 1.0
    line_norm = line_signal / (np.max(line_signal) + 1e-6)
    # Invert gutter signal (low density = high boundary score)
    gutter_norm = 1.0 - (gutter_signal / (np.max(gutter_signal) + 1e-6))
    
    # Combined score: 70% physical lines, 30% whitespace gutters
    combined_score = (line_norm * 0.7) + (gutter_norm * 0.3)

    # 6. Peak Detection
    # distance: Prevents detecting peaks too close together
    # prominence: Ensures the peak stands out from local noise
    min_col_width = width // (expected_columns + 2)
    peaks, _ = find_peaks(combined_score, distance=min_col_width, height=0.1, prominence=0.05)

    # Convert peaks to full-page boundaries
    boundaries = [0] + sorted(peaks.tolist()) + [width]

    # Debug visualization
    if debug and debug_path:
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Profile plot
        ax1.plot(combined_score, label='Hybrid Score', color='purple')
        ax1.scatter(peaks, combined_score[peaks], color='red', label='Detected Dividers')
        ax1.set_title(f'Column Detection Profile (Page {page_num})')
        ax1.legend()

        # Result Overlay
        display_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        for p in peaks:
            cv2.line(display_img, (p, 0), (p, height), (0, 0, 255), 3)
        ax2.imshow(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB))
        ax2.set_title('Detected Boundaries')
        ax2.axis('off')

        plt.tight_layout()
        plt.savefig(debug_path, dpi=150)
        plt.close()

    print(f"    Detected {len(boundaries)-1} columns on page {page_num}")
    return boundaries

def split_into_columns(image_array, boundaries, margin=10):
    """Split image into columns based on detected boundaries."""
    columns = []
    height, width = image_array.shape[:2]

    for i in range(len(boundaries) - 1):
        x_start = max(0, boundaries[i] - margin)
        x_end = min(width, boundaries[i + 1] + margin)
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
    """Preprocess a single PDF: convert, detect, split, save."""
    pdf_name = Path(pdf_path).stem
    if dpi is None:
        dpi = calculate_optimal_dpi(pdf_path)

    images = convert_from_path(pdf_path, dpi=dpi)
    pdf_output_dir = Path(output_dir) / pdf_name
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    if debug:
        (pdf_output_dir / 'debug').mkdir(exist_ok=True)

    pdf_metadata = {'source_pdf': pdf_name, 'dpi': dpi, 'num_pages': len(images), 'pages': []}

    for page_num, image in enumerate(images, start=1):
        print(f"  Page {page_num}/{len(images)}...")
        image_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        debug_path = pdf_output_dir / 'debug' / f'p{page_num:03d}_detect.png' if debug else None
        
        # Pass page_num to trigger Adaptive ROI
        boundaries = detect_column_boundaries(
            image_array, 
            page_num=page_num, 
            expected_columns=5, 
            debug=debug, 
            debug_path=debug_path
        )

        columns = split_into_columns(image_array, boundaries)
        page_metadata = {'page_num': page_num, 'boundaries': boundaries, 'columns': []}

        for column_img, col_meta in columns:
            col_filename = f"{pdf_name}_p{page_num:03d}_c{col_meta['column_index']:02d}.png"
            col_path = pdf_output_dir / col_filename
            cv2.imwrite(str(col_path), column_img)
            col_meta['filename'] = col_filename
            col_meta['path'] = str(col_path)
            page_metadata['columns'].append(col_meta)

        pdf_metadata['pages'].append(page_metadata)

    with open(pdf_output_dir / 'metadata.json', 'w') as f:
        json.dump(pdf_metadata, f, indent=2)
    return pdf_metadata

def main():
    parser = argparse.ArgumentParser(description='Preprocess PDFs for OCR')
    parser.add_argument('--input-dir', default='pdfs')
    parser.add_argument('--output-dir', default='data/preprocessed')
    parser.add_argument('--dpi', type=int, default=None)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    input_dir, output_dir = Path(args.input_dir), Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(input_dir.glob('*.pdf'))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return

    # This list will store metadata for every PDF processed
    all_metadata = []

    for pdf_path in pdf_files:
        try:
            # We capture the returned metadata dictionary
            metadata = preprocess_pdf(pdf_path, output_dir, args.dpi, debug=args.debug)
            all_metadata.append(metadata)
        except Exception as e:
            print(f"  Error processing {pdf_path.name}: {e}")

    # CRITICAL: Save the master metadata file that Step 2 (OCR) expects
    combined_metadata_path = output_dir / 'all_metadata.json'
    with open(combined_metadata_path, 'w') as f:
        json.dump(all_metadata, f, indent=2)

    print(f"\nPreprocessing complete!")
    print(f"  Processed {len(all_metadata)} PDFs")
    print(f"  Master metadata saved to: {combined_metadata_path}")

if __name__ == '__main__':
    main()