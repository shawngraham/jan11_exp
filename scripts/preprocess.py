#!/usr/bin/env python3
"""
Preprocess PDFs with OpenCV Assertion safeguards.
- Prevents 'empty source' errors in cvtColor.
- Shaves gutters safely.
- Discards fragments under 250KB.
"""

import os
import json
import cv2
import numpy as np
from pdf2image import convert_from_path
import argparse
from pathlib import Path

def detect_vertical_columns(image_array, expected_columns=5):
    # SAFETY: Check if image is valid
    if image_array is None or image_array.size == 0:
        return [0]
        
    h, w = image_array.shape[:2]
    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)

    roi = binary[int(h*0.1):int(h*0.9), :]
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 150))
    v_lines = cv2.morphologyEx(roi, cv2.MORPH_OPEN, v_kernel)
    v_proj = np.sum(v_lines, axis=0)
    
    v_norm = v_proj / (np.max(v_proj) + 1e-6)
    peaks = [x for x in range(1, len(v_norm)-1) if v_norm[x] > 0.1 and v_norm[x] > v_norm[x-1] and v_norm[x] > v_norm[x+1]]
    
    clean_peaks = []
    min_col_w = w // (expected_columns + 2)
    if peaks:
        clean_peaks.append(peaks[0])
        for p in peaks[1:]:
            if p > clean_peaks[-1] + min_col_w: clean_peaks.append(p)
            
    # Remove duplicates and sort
    bounds = sorted(list(set([0] + clean_peaks + [w])))
    return bounds

def detect_horizontal_rules(column_img, debug_name=None):
    """
    Robust horizontal rule detection.
    Optimized for slightly tilted or faint 19th-century printing rules.
    """
    if column_img is None or column_img.size == 0:
        return [0]
    
    h, w = column_img.shape[:2]
    if h < 100: return [0, h]

    # 1. Shave margins (essential to remove vertical edge noise)
    shave = max(1, int(w * 0.05))
    clean_col = column_img[:, shave:w-shave]
    cw = clean_col.shape[1]

    # 2. Pre-process
    gray = cv2.cvtColor(clean_col, cv2.COLOR_BGR2GRAY)
    
    # Use a very sensitive threshold to catch faint lines
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)

    # 3. Morphology: The "Line Finder"
    # We use a shorter kernel (35% width) to account for slight page tilt.
    # We then 'Close' it to bridge the tapered ends.
    kernel_w = max(1, int(cw * 0.15)) 
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
    
    # Remove text
    detected = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    # Bridge the rule segments
    detected = cv2.morphologyEx(detected, cv2.MORPH_CLOSE, h_kernel, iterations=3)

    # 4. Vertical Projection
    y_proj = np.sum(detected, axis=1)
    
    # Calculate threshold: 25% of the column width is ink-heavy enough for a rule
    # This is much more forgiving than 40-50%
    peak_thresh = 255 * cw * 0.15
    
    dividers = []
    y = 10
    while y < h - 10:
        if y_proj[y] > peak_thresh:
            # We found a candidate. Check if it's a rule (thin) or a text block (thick)
            start_y = y
            while y < h and y_proj[y] > (peak_thresh * 0.5):
                y += 1
            end_y = y
            
            # RULE CHECK: If the 'blob' is more than 15 pixels tall, 
            # it's likely a line of bold text, not a rule. Skip it.
            if (end_y - start_y) < 15:
                dividers.append(int((start_y + end_y) / 2))
        y += 1

    # 5. Clean and Filter
    min_snip_h = 80 # Min height of an ad/article
    clean_dividers = []
    if dividers:
        dividers = sorted(list(set(dividers)))
        clean_dividers.append(dividers[0])
        for d in dividers[1:]:
            if d > clean_dividers[-1] + min_snip_h:
                clean_dividers.append(d)

    # --- DEBUG VISUALIZATION ---
    # If this isn't working, uncomment these lines to see the 'detected' lines
    # cv2.imwrite(f"debug_lines_{debug_name}.png", detected)

    return sorted(list(set([0] + clean_dividers + [h])))

def preprocess_pdf(pdf_path, output_dir, dpi=150):
    pdf_name = Path(pdf_path).stem
    images = convert_from_path(pdf_path, dpi=dpi)
    pdf_output_dir = Path(output_dir) / pdf_name
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    pdf_metadata = {'source_pdf': pdf_name, 'dpi': dpi, 'pages': []}
    MIN_KB = 250 

    for page_num, image in enumerate(images, start=1):
        print(f"  Page {page_num}/{len(images)}...")
        img_arr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        v_bounds = detect_vertical_columns(img_arr)
        page_snippets = []

        for col_idx in range(len(v_bounds)-1):
            x1, x2 = v_bounds[col_idx], v_bounds[col_idx+1]
            # SAFETY: Skip zero-width columns
            if x2 <= x1: continue
            
            column_strip = img_arr[:, x1:x2]
            h_bounds = detect_horizontal_rules(column_strip)
            
            for snip_idx in range(len(h_bounds)-1):
                y1, y2 = h_bounds[snip_idx], h_bounds[snip_idx+1]
                # SAFETY: Skip zero-height snippets
                if y2 <= y1: continue
                
                snippet = column_strip[y1:y2, :]
                
                # FINAL SAFETY: Ensure snippet exists before cvtColor
                if snippet is None or snippet.size == 0: continue
                
                snippet_gray = cv2.cvtColor(snippet, cv2.COLOR_BGR2GRAY)
                
                snip_fn = f"p{page_num:02d}_c{col_idx:02d}_s{snip_idx:03d}.jpg"
                snip_path = pdf_output_dir / snip_fn
                cv2.imwrite(str(snip_path), snippet_gray, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

                if os.path.getsize(snip_path) / 1024 < MIN_KB:
                    os.remove(snip_path)
                    continue

                page_snippets.append({
                    'path': str(snip_path),
                    'x_offset': int(x1),
                    'y_offset': int(y1),
                    'column': int(col_idx)
                })

        pdf_metadata['pages'].append({'page_num': page_num, 'snippets': page_snippets})
    
    return pdf_metadata

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', default='pdfs')
    parser.add_argument('--output-dir', default='data/preprocessed')
    parser.add_argument('--dpi', type=int, default=150)
    args = parser.parse_args()

    input_dir, output_dir = Path(args.input_dir), Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_files = sorted(input_dir.glob('*.pdf'))
    all_metadata = []

    for pdf in pdf_files:
        try:
            metadata = preprocess_pdf(pdf, output_dir, args.dpi)
            all_metadata.append(metadata)
        except Exception as e:
            print(f"  Error processing {pdf.name}: {e}")
            import traceback
            traceback.print_exc()

    with open(output_dir / 'all_metadata.json', 'w') as f:
        json.dump(all_metadata, f, indent=2)
    print("\n✓ Preprocessing complete and safely hardened.")

if __name__ == '__main__':
    main()