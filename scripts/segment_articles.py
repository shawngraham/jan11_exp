#!/usr/bin/env python3
"""
Article Segmentation Script
Analyzes OCR output to group text blocks into individual articles.
Optimized for 19th-century newspapers like "The Equity".
"""

import json
import re
from pathlib import Path

def is_likely_headline(block, surrounding_blocks):
    """
    Determine if a text block is likely a headline or sub-head.
    19th-century headlines are often All-Caps, centered, or slightly larger.
    """
    text = block["text"].strip()
    if len(text) < 3 or len(text) > 150: 
        return False

    height = block["bbox"]["height"]
    avg_height = sum(b["bbox"]["height"] for b in surrounding_blocks) / len(surrounding_blocks)

    # Heuristic 1: Significantly taller than surrounding text
    is_tall = height > avg_height * 1.25
    
    # Heuristic 2: Short and All Caps (e.g., "LOCAL NEWS", "DIED")
    is_caps_short = text.isupper() and len(text) < 60
    
    # Heuristic 3: Title Case and short (not ending in sentence punctuation)
    is_title_short = text.istitle() and not text.endswith(('.', '!', '?')) and len(text) < 80

    score = 0
    if is_tall: score += 2
    if is_caps_short: score += 1
    if is_title_short: score += 1
    
    return score >= 2

def group_into_articles(text_blocks):
    """
    Group text blocks into articles using column and vertical positioning.
    """
    if not text_blocks:
        return []

    # Trust the 'column' index from preprocess.py, then sort by Y position
    sorted_blocks = sorted(text_blocks, key=lambda b: (b.get("column", 0), b["bbox"]["y"]))

    articles = []
    current_article = None
    article_id_counter = 1

    for i, block in enumerate(sorted_blocks):
        # Gather surrounding blocks for height context
        surrounding = sorted_blocks[max(0, i-3):min(len(sorted_blocks), i+4)]
        is_headline = is_likely_headline(block, surrounding)

        start_new = False
        if current_article is None:
            start_new = True
        else:
            prev_block = sorted_blocks[i - 1]
            
            # RULE 1: Forced break on a detected headline
            if is_headline:
                start_new = True
            
            # RULE 2: Break on column change
            elif block.get("column") != prev_block.get("column"):
                start_new = True
                
            # RULE 3: Significant Vertical Gap (approx 2.5x line height)
            else:
                gap = block["bbox"]["y"] - (prev_block["bbox"]["y"] + prev_block["bbox"]["height"])
                if gap > (block["bbox"]["height"] * 2.5):
                    start_new = True

        if start_new:
            if current_article:
                articles.append(current_article)

            current_article = {
                "article_id": article_id_counter,
                "headline": block["text"] if is_headline else "Untitled Snippet",
                "blocks": [block],
                "column": block.get("column"),
                "start_y": block["bbox"]["y"]
            }
            article_id_counter += 1
        else:
            current_article["blocks"].append(block)

    if current_article:
        articles.append(current_article)
        
    return articles

def parse_metadata_from_filename(filename):
    """
    Extract Pub ID and Date from filename format: 83471_1888-10-25.pdf
    """
    # Pattern to match: 5 digits, underscore, YYYY-MM-DD
    match = re.search(r'(\d{5})_(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return {
            "pub_id": match.group(1),
            "date": match.group(2)
        }
    return {"pub_id": "unknown", "date": "unknown"}

def main():
    # Setup paths relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir if (script_dir / "data").exists() else script_dir.parent
    
    input_file = project_root / "data" / "raw" / "ocr_output.json"
    output_file = project_root / "data" / "processed" / "articles.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        print(f"Error: OCR output not found at {input_file}")
        return

    print(f"Loading OCR data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)

    all_articles = []
    
    for pdf_data in ocr_data.get("pdfs", []):
        pdf_filename = pdf_data["filename"]
        meta = parse_metadata_from_filename(pdf_filename)
        
        print(f"Segmenting: {pdf_filename} (Date: {meta['date']})")

        for page_data in pdf_data.get("pages", []):
            page_num = page_data["page_number"]
            articles = group_into_articles(page_data.get("text_blocks", []))

            for art in articles:
                # Combine block text into full article text
                full_text = " ".join(b["text"] for b in art["blocks"]).strip()
                
                # Calculate aggregate bounding box
                all_x = [b["bbox"]["x"] for b in art["blocks"]]
                all_y = [b["bbox"]["y"] for b in art["blocks"]]
                all_w = [b["bbox"]["x"] + b["bbox"]["width"] for b in art["blocks"]]
                all_h = [b["bbox"]["y"] + b["bbox"]["height"] for b in art["blocks"]]

                article_entry = {
                    "article_id": f"{meta['pub_id']}_{meta['date']}_p{page_num}_{art['article_id']}",
                    "pub_id": meta["pub_id"],
                    "date": meta["date"],
                    "page": page_num,
                    "column": art["column"],
                    "headline": art["headline"],
                    "text": full_text,
                    "word_count": len(full_text.split()),
                    "bbox": {
                        "x": min(all_x),
                        "y": min(all_y),
                        "width": max(all_w) - min(all_x),
                        "height": max(all_h) - min(all_y)
                    }
                }
                all_articles.append(article_entry)

    # Save processed data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_articles": len(all_articles),
            "articles": all_articles
        }, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"SUCCESS: Extracted {len(all_articles)} articles.")
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    main()