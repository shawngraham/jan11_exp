#!/usr/bin/env python3
"""
Test Script: Run PaddleOCR against a single snippet and visualize results.
Use this to debug coordinate mapping and text quality.
"""

import sys
import cv2
import json
import numpy as np
from pathlib import Path
from paddleocr import PaddleOCR

# 1. Initialize OCR
print("Initializing PaddleOCR V3/V4...")
# use_angle_cls=False is better for standard vertical newsprint
ocr = PaddleOCR(lang='en', use_angle_cls=False)

def test_single_image(image_path):
    img_path = Path(image_path)
    if not img_path.exists():
        print(f"Error: File not found at {image_path}")
        return

    # Load image
    img = cv2.imread(str(img_path))
    if img is None:
        print("Error: Could not decode image.")
        return

    print(f"Processing: {img_path.name} ({img.shape[1]}x{img.shape[0]})")

    # 2. Run OCR
    # We use .ocr() as it's the most stable method across versions
    try:
        result = ocr.predict(img)
    except Exception as e:
        print(f"OCR failed: {e}")
        return

    if not result or not result[0]:
        print("Done: No text detected in this image.")
        return

    # 3. Process and Visualize
    display_img = img.copy()
    print("\nDetected Text:")
    print("-" * 30)

    # Paddle returns a list of lines in the first index
    lines = result[0]
    
    for i, line in enumerate(lines):
        # line structure: [ [[x1,y1], [x2,y2], [x3,y3], [x4,y4]], (text, confidence) ]
        bbox = line[0]
        text, confidence = line[1]

        print(f"[{i+1}] Conf: {confidence:.2f} | Text: {text}")

        # Draw bounding box for visual confirmation
        pts = np.array(bbox, np.int32).reshape((-1, 1, 2))
        cv2.polylines(display_img, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
        # Draw text label
        cv2.putText(display_img, f"{i+1}", (int(bbox[0][0]), int(bbox[0][1] - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 4. Save visualization
    output_path = img_path.parent / f"debug_{img_path.stem}.jpg"
    cv2.imwrite(str(output_path), display_img)
    
    print("-" * 30)
    print(f"Done! Visualization saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ocr.py <path_to_image_snippet>")
    else:
        test_single_image(sys.argv[1])