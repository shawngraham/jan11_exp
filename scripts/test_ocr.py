#!/usr/bin/env python3
"""
Test Script: Robust PaddleOCR debugging.
Handles cases where confidence scores are missing from the output.
"""

import sys
import cv2
import json
import numpy as np
from pathlib import Path
from paddleocr import PaddleOCR

# 1. Initialize OCR
print("Initializing PaddleOCR V3/V4...")
# We use minimal params for maximum compatibility
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
    try:
        # Some versions prefer .ocr(), some .predict()
        result = ocr.predict(img)
    except Exception as e:
        print(f"OCR failed: {e}")
        return

    if not result or not result[0]:
        print("Done: No text detected in this image.")
        return

    # 3. Process and Visualize
    display_img = img.copy()
    print("\nDetected Text Results:")
    print("-" * 50)

    # Paddle returns a list of lines in the first index
    lines = result[0]
    
    for i, line in enumerate(lines):
        try:
            # Expected format: [ [[x,y],...], (text, confidence) ]
            bbox = line[0]
            content = line[1]

            # --- ROBUST UNPACKING ---
            if isinstance(content, (list, tuple)) and len(content) >= 2:
                text = content[0]
                confidence = float(content[1])
            else:
                # If only a string is returned without confidence
                text = str(content)
                confidence = 1.0 # Default confidence

            print(f"[{i+1:02d}] {confidence:.2f} | {text}")

            # Draw bounding box
            pts = np.array(bbox, np.int32).reshape((-1, 1, 2))
            cv2.polylines(display_img, [pts], isClosed=True, color=(0, 0, 255), thickness=1)
            
            # Draw index number
            cv2.putText(display_img, f"{i+1}", (int(bbox[0][0]), int(bbox[0][1] - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        except Exception as e:
            print(f"Error parsing line {i}: {e}")
            continue

    # 4. Save visualization
    output_path = img_path.parent / f"debug_{img_path.stem}.jpg"
    cv2.imwrite(str(output_path), display_img)
    
    print("-" * 50)
    print(f"Done! Visualization saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ocr.py <path_to_image_snippet>")
    else:
        test_single_image(sys.argv[1])