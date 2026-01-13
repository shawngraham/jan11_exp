#!/usr/bin/env python3
"""
Pipeline Runner Script - Whitechapel in Shawville
Executes the full 6-step data processing sequence.
Defaults to Tesseract OCR for M1 stability.
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_script(script_name):
    """Run a Python script and handle errors"""
    script_path = Path(__file__).parent / script_name
    print(f"\n{'=' * 60}")
    print(f"Running: {script_name}")
    print('=' * 60)

    try:
        # We use capture_output=False so you can see the 
        # real-time progress prints from the OCR and Preprocessor
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✓ {script_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {script_name} failed with error")
        print(f"Error: {e}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Run the Whitechapel in Shawville data processing pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--ocr-engine',
        choices=['tesseract', 'paddleocr', 'gemini', 'surya'],
        default='tesseract',
        help='OCR engine to use: "tesseract" (default/stable), "paddleocr" (deep learning), or "gemini"'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("WHITECHAPEL IN SHAWVILLE - DATA PROCESSING PIPELINE")
    print("=" * 60)
    print(f"OCR Engine: {args.ocr_engine.upper()}")
    print("=" * 60)

    # Logic to select Step 2 script
    if args.ocr_engine == "gemini":
        ocr_script = "process_pdfs_gemini.py"
    elif args.ocr_engine == "paddleocr":
        ocr_script = "process_pdfs.py"
    elif args.ocr_engine == "surya":
        ocr_script = "process_images_surya_batch.py"
    else:
        ocr_script = "process_pdfs_tesseract.py"

    # The Canonical 6-Step Sequence
    scripts = [
        "preprocess.py",        # Step 1: 300DPI Snippets + Split at 2000px
        ocr_script,             # Step 2: The chosen OCR Engine (Default: Tesseract)
        "segment_articles.py",  # Step 3: JSONL -> Article Grouping
        "tag_articles.py",      # Step 4: Thematic/Ripper Classification
        "generate_timeline.py", # Step 5: Historical News Lag Analysis
        "analyze_text.py"       # Step 6: Linguistic Sensationalism Index
    ]

    success_count = 0

    for script in scripts:
        if run_script(script):
            success_count += 1
        else:
            print(f"\nPipeline stopped due to error in {script}")
            print("Troubleshooting: Check memory usage or file paths.")
            sys.exit(1)

    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETE!")
    print(f"Successfully completed {success_count}/{len(scripts)} steps")
    print("=" * 60)
    print("\nGenerated data files for visualization:")
    print("  - data/raw/ocr_output_tesseract.jsonl (Raw OCR)")
    print("  - data/processed/articles.json        (Segments)")
    print("  - data/processed/tagged_articles.json (Thematic Data)")
    print("  - data/processed/timeline.json        (Temporal/Lag Data)")
    print("  - data/processed/text_analysis.json   (Linguistic Stats)")
    print("\nReady to launch Whitechapel in Shawville interactive!")

if __name__ == "__main__":
    main()