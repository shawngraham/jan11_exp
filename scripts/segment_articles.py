#!/usr/bin/env python3
"""
Article Segmentation Script
Analyzes OCR output to detect columns and segment individual articles
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def detect_columns(text_blocks, page_width, num_columns_hint=3):
    """
    Detect column boundaries based on text block positions

    Args:
        text_blocks: List of text blocks with bbox info
        page_width: Width of the page
        num_columns_hint: Expected number of columns

    Returns:
        List of column boundaries [(start_x, end_x), ...]
    """
    if not text_blocks:
        return []

    # Collect x-positions of block centers
    x_positions = []
    for block in text_blocks:
        x_center = block["bbox"]["x"] + block["bbox"]["width"] / 2
        x_positions.append(x_center)

    # Sort and create histogram
    x_positions.sort()

    # Simple column detection: divide page into equal columns
    # More sophisticated: cluster x-positions
    column_width = page_width / num_columns_hint
    columns = []

    for i in range(num_columns_hint):
        start_x = i * column_width
        end_x = (i + 1) * column_width
        columns.append((start_x, end_x))

    return columns

def assign_to_column(block, columns):
    """Assign a text block to a column"""
    x_center = block["bbox"]["x"] + block["bbox"]["width"] / 2

    for col_idx, (start_x, end_x) in enumerate(columns):
        if start_x <= x_center < end_x:
            return col_idx

    # Default to last column if outside bounds
    return len(columns) - 1

def is_likely_headline(block, surrounding_blocks):
    """
    Determine if a text block is likely a headline

    Heuristics:
    - Larger height than average
    - Shorter text (headlines are concise)
    - All caps or title case
    """
    text = block["text"]
    height = block["bbox"]["height"]

    # Calculate average height of surrounding blocks
    if surrounding_blocks:
        avg_height = sum(b["bbox"]["height"] for b in surrounding_blocks) / len(surrounding_blocks)
    else:
        avg_height = height

    # Check if significantly taller
    is_tall = height > avg_height * 1.3

    # Check if short text (headlines typically < 100 chars)
    is_short = len(text) < 100

    # Check if title case or all caps
    is_title_case = text.istitle() or text.isupper()

    # Check for common headline patterns
    has_headline_words = any(word in text.lower() for word in ['murder', 'arrested', 'found', 'death', 'trial', 'police'])

    score = sum([is_tall, is_short, is_title_case, has_headline_words])

    return score >= 2

def group_into_articles(text_blocks, page_width, page_height):
    """
    Group text blocks into articles

    Returns:
        List of articles with metadata
    """
    if not text_blocks:
        return []

    # Detect columns
    columns = detect_columns(text_blocks, page_width)

    # Assign blocks to columns
    for block in text_blocks:
        block["column"] = assign_to_column(block, columns)

    # Sort blocks by column, then by y-position
    sorted_blocks = sorted(text_blocks, key=lambda b: (b["column"], b["bbox"]["y"]))

    # Group blocks into articles
    articles = []
    current_article = None
    article_id = 1

    for i, block in enumerate(sorted_blocks):
        # Start new article if:
        # 1. First block
        # 2. Large vertical gap from previous block
        # 3. Column change

        start_new = False

        if current_article is None:
            start_new = True
        else:
            prev_block = sorted_blocks[i - 1]

            # Check vertical gap
            gap = block["bbox"]["y"] - (prev_block["bbox"]["y"] + prev_block["bbox"]["height"])
            avg_height = (block["bbox"]["height"] + prev_block["bbox"]["height"]) / 2

            # Large gap suggests new article
            if gap > avg_height * 2:
                start_new = True

            # Column change
            if block["column"] != prev_block["column"]:
                start_new = True

        if start_new:
            if current_article:
                articles.append(current_article)

            # Check if this block is a headline
            surrounding = sorted_blocks[max(0, i-2):min(len(sorted_blocks), i+3)]
            is_headline = is_likely_headline(block, surrounding)

            current_article = {
                "article_id": f"article_{article_id}",
                "headline": block["text"] if is_headline else "",
                "blocks": [block],
                "column": block["column"],
                "start_y": block["bbox"]["y"],
                "end_y": block["bbox"]["y"] + block["bbox"]["height"]
            }
            article_id += 1
        else:
            # Add to current article
            current_article["blocks"].append(block)
            current_article["end_y"] = block["bbox"]["y"] + block["bbox"]["height"]

            # Update headline if this looks more like one
            if not current_article["headline"] and is_likely_headline(block, current_article["blocks"]):
                current_article["headline"] = block["text"]

    # Add last article
    if current_article:
        articles.append(current_article)

    # Post-process articles
    for article in articles:
        # Combine text from all blocks
        article["full_text"] = " ".join(block["text"] for block in article["blocks"])

        # Calculate bounding box for entire article
        all_x = [b["bbox"]["x"] for b in article["blocks"]]
        all_y = [b["bbox"]["y"] for b in article["blocks"]]
        all_x_end = [b["bbox"]["x"] + b["bbox"]["width"] for b in article["blocks"]]
        all_y_end = [b["bbox"]["y"] + b["bbox"]["height"] for b in article["blocks"]]

        article["bbox"] = {
            "x": min(all_x),
            "y": min(all_y),
            "width": max(all_x_end) - min(all_x),
            "height": max(all_y_end) - min(all_y)
        }

        # Word count
        article["word_count"] = len(article["full_text"].split())

        # Remove individual blocks from output (keep positions but not redundant text)
        article["num_blocks"] = len(article["blocks"])
        del article["blocks"]

    return articles

def extract_date_from_text(text):
    """
    Attempt to extract date from article text or headline
    Common patterns: "September 15, 1888", "Sept. 15, 1888", etc.
    """
    # Common date patterns
    patterns = [
        r'([A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})',  # September 15, 1888
        r'(\d{1,2}\s+[A-Z][a-z]+\.?\s+\d{4})',      # 15 September 1888
        r'(\d{1,2}/\d{1,2}/\d{4})',                  # 09/15/1888
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return None

def process_page(page_data):
    """Process a single page and extract articles"""
    if "error" in page_data:
        return []

    text_blocks = page_data.get("text_blocks", [])
    page_width = page_data.get("image_width", 2000)
    page_height = page_data.get("image_height", 3000)

    articles = group_into_articles(text_blocks, page_width, page_height)

    # Add page metadata to each article
    for article in articles:
        article["page_number"] = page_data["page_number"]
        article["image_path"] = page_data.get("image_path", "")

        # Try to extract date
        date = extract_date_from_text(article["headline"] + " " + article["full_text"][:200])
        article["extracted_date"] = date

    return articles

def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / "data" / "raw" / "ocr_output.json"
    output_file = base_dir / "data" / "processed" / "articles.json"

    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if input exists
    if not input_file.exists():
        print(f"Error: OCR output not found at {input_file}")
        print("Please run process_pdfs.py first.")
        return

    # Load OCR data
    print(f"Loading OCR data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)

    # Process all PDFs and pages
    all_articles = []
    article_counter = 1

    for pdf_idx, pdf_data in enumerate(ocr_data["pdfs"]):
        pdf_name = pdf_data["filename"]
        print(f"Processing {pdf_name} ({pdf_idx + 1}/{len(ocr_data['pdfs'])})")

        for page_data in pdf_data["pages"]:
            articles = process_page(page_data)

            # Add PDF metadata and unique IDs
            for article in articles:
                article["source_pdf"] = pdf_name
                article["global_article_id"] = f"article_{article_counter:03d}"
                article_counter += 1
                all_articles.append(article)

            print(f"  Page {page_data['page_number']}: {len(articles)} articles")

    # Save results
    output_data = {
        "total_articles": len(all_articles),
        "articles": all_articles
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"Segmentation complete!")
    print(f"Results saved to {output_file}")
    print(f"\nSummary:")
    print(f"  Total articles extracted: {len(all_articles)}")

    # Statistics
    total_words = sum(a["word_count"] for a in all_articles)
    articles_with_headlines = sum(1 for a in all_articles if a["headline"])
    articles_with_dates = sum(1 for a in all_articles if a["extracted_date"])

    print(f"  Total words: {total_words}")
    print(f"  Articles with headlines: {articles_with_headlines}")
    print(f"  Articles with extracted dates: {articles_with_dates}")

if __name__ == "__main__":
    main()
