#!/usr/bin/env python3
"""
Automated Article Tagging Script
Classifies articles based on keyword matching and content analysis.
Fixes field name mismatches and adds word-boundary protection.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Tag definitions
TAG_KEYWORDS = {
    "whitechapel_ripper": {
        "keywords": [
            "whitechapel", "jack the ripper", "ripper", "leather apron", 
            "spitalfields", "hanbury", "mitre square", "buck's row",
            "mary kelly", "annie chapman", "elizabeth stride", "catherine eddowes",
            "mary nichols", "polly nichols", "london monster", "whitechapel fiend"
        ],
        "weight": 15
    },
    "crime_general": {
        "keywords": [
            "murder", "slain", "crime", "criminal", "police", "constable",
            "arrest", "trial", "prisoner", "jail", "gaol", "detective", 
            "suspect", "accused", "guilty", "theft", "robbery", "burglar", "hanged"
        ],
        "weight": 5
    },
    "local_shawville": {
        "keywords": [
            "shawville", "pontiac", "clarendon", "bristol", "fort coulonge", 
            "campbell's bay", "aylmer", "chapeau", "quyon", "bryson", "ottawa valley"
        ],
        "weight": 10
    },
    "british_empire": {
        "keywords": [
            "london", "england", "british", "victoria", "westminster", 
            "scotland yard", "metropolitan police", "thames", "liverpool", 
            "glasgow", "empire", "colonial", "imperial"
        ],
        "weight": 6
    },
    "advertisement": {
        "keywords": [
            "for sale", "wanted", "notice", "bargain", "price", "cents",
            "dollar", "cheap", "advertisement", "classified", "apply to", "inquire"
        ],
        "weight": 3
    }
}

def calculate_tag_scores(text, headline):
    """Calculate scores using word boundaries for accuracy."""
    combined = (headline + " " + text).lower()
    scores = defaultdict(float)

    for tag, config in TAG_KEYWORDS.items():
        score = 0
        for kw in config["keywords"]:
            # Use regex to find whole words only (\b)
            # This prevents "ripper" matching "stripper"
            pattern = rf'\b{re.escape(kw.lower())}\b'
            matches = len(re.findall(pattern, combined))
            
            if matches > 0:
                # Check if keyword is in headline (worth 3x)
                in_headline = len(re.findall(pattern, headline.lower()))
                score += (in_headline * 3) + (matches - in_headline)
        
        scores[tag] = score * config["weight"]
    
    return scores

def main():
    # 1. Path Setup
    script_dir = Path(__file__).parent
    project_root = script_dir if (script_dir / "data").exists() else script_dir.parent
    
    input_file = project_root / "data" / "processed" / "articles.json"
    output_file = project_root / "data" / "processed" / "tagged_articles.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run segment_articles.py first.")
        return

    # 2. Load Data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    print(f"Tagging {len(articles)} articles...")

    # 3. Process
    for art in articles:
        # Note: we use art["text"] because that's what segment_articles.py outputs
        scores = calculate_tag_scores(art.get("text", ""), art.get("headline", ""))
        
        # Sort and filter tags
        assigned = []
        for tag, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            if score > 0:
                assigned.append({
                    "tag": tag,
                    "score": round(score, 2)
                })
        
        art["tags"] = assigned
        art["primary_tag"] = assigned[0]["tag"] if assigned else "general"
        art["is_whitechapel"] = any(t["tag"] == "whitechapel_ripper" for t in assigned)

    # 4. Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"articles": articles}, f, indent=2, ensure_ascii=False)

    # 5. Summary
    ripper_count = sum(1 for a in articles if a["is_whitechapel"])
    print("=" * 60)
    print(f"Tagging Complete!")
    print(f"  Total articles: {len(articles)}")
    print(f"  Whitechapel-related: {ripper_count}")
    print(f"  Results saved to: {output_file}")

if __name__ == "__main__":
    main()