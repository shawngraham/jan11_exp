#!/usr/bin/env python3
"""
Pipeline Runner Script
Executes all data processing scripts in sequence
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
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default PaddleOCR (local processing)
  python run_pipeline.py

  # Run with Gemini Vision API (cloud processing)
  python run_pipeline.py --ocr-engine gemini

  # Run with specific OCR engine
  python run_pipeline.py --ocr-engine paddleocr
        """
    )
    parser.add_argument(
        '--ocr-engine',
        choices=['paddleocr', 'gemini'],
        default='paddleocr',
        help='OCR engine to use: "paddleocr" for local processing (default), "gemini" for Gemini Vision API'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("WHITECHAPEL IN SHAWVILLE - DATA PROCESSING PIPELINE")
    print("=" * 60)
    print(f"OCR Engine: {args.ocr_engine.upper()}")
    print("=" * 60)

    # Choose OCR script based on engine selection
    ocr_script = "process_pdfs_gemini.py" if args.ocr_engine == "gemini" else "process_pdfs.py"

    scripts = [
        "preprocess.py",      # Step 1: Resize PDFs, detect columns, split into images
        ocr_script,           # Step 2: Run OCR on preprocessed columns (PaddleOCR or Gemini)
        "segment_articles.py",
        "tag_articles.py",
        "generate_timeline.py",
        "analyze_text.py"
    ]

    success_count = 0

    for script in scripts:
        if run_script(script):
            success_count += 1
        else:
            print(f"\nPipeline stopped due to error in {script}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETE!")
    print(f"Successfully completed {success_count}/{len(scripts)} steps")
    print("=" * 60)
    print("\nGenerated data files:")
    print("  - data/raw/ocr_output.json")
    print("  - data/processed/articles.json")
    print("  - data/processed/tagged_articles.json")
    print("  - data/processed/timeline.json")
    print("  - data/processed/text_analysis.json")
    print("\nReady to build website!")

if __name__ == "__main__":
    main()
