#!/usr/bin/env python3
"""
Pipeline Runner Script
Executes all data processing scripts in sequence
"""

import sys
import subprocess
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
    print("=" * 60)
    print("WHITECHAPEL IN SHAWVILLE - DATA PROCESSING PIPELINE")
    print("=" * 60)

    scripts = [
        "process_pdfs.py",
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
