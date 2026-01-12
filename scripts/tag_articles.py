#!/usr/bin/env python3
"""
Step 4: Automated Article Tagging
- Classifies 1880s articles based on historically relevant keywords.
- Optimized with pre-compiled regex for speed.
- Aligns with Step 3 field names (pub, page, col, text, headline).
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Tag definitions with weights
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

# Pre-compile regex for every keyword to maximize speed
for tag in TAG_KEYWORDS:
    TAG_KEYWORDS[tag]["compiled"] = [
        re.compile(rf'\b{re.escape(kw.lower())}\b') 
        for kw in TAG_KEYWORDS[tag]["keywords"]
    ]

def calculate_tag_scores(text, headline):
    combined = (headline + " " + text).lower()
    headline_lower = headline.lower()
    scores = defaultdict(float)

    for tag, config in TAG_KEYWORDS.items():
        score = 0
        for pattern in config["compiled"]:
            # Count occurrences in full text
            matches = len(pattern.findall(combined))
            
            if matches > 0:
                # Check if keyword is specifically in the headline (bonus weight)
                in_headline = len(pattern.findall(headline_lower))
                # Headline matches are worth significantly more
                score += (in_headline * 5) + (matches - in_headline)
        
        if score > 0:
            scores[tag] = score * config["weight"]
    
    return scores

def main():
    # Setup paths
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    input_file = project_root / "data" / "processed" / "articles.json"
    output_file = project_root / "data" / "processed" / "tagged_articles.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run the segmenter first.")
        return

    # Load articles
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    print(f"Tagging {len(articles)} articles...")

    for art in articles:
        # Calculate scores based on the text and headline generated in Step 3
        # Use 'full_text' field (new) or fall back to 'text' (old)
        text = art.get("full_text", art.get("text", ""))
        scores = calculate_tag_scores(text, art.get("headline", ""))

        # Sort tags by score
        assigned = []
        for tag, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            assigned.append({
                "tag": tag,
                "score": round(score, 2)
            })

        # Determine metadata
        art["tags"] = assigned
        art["primary_tag"] = assigned[0]["tag"] if assigned else "general"

        # Specific flag for Whitechapel murders (using the field name the JS expects)
        art["is_whitechapel"] = any(t["tag"] == "whitechapel_ripper" for t in assigned)
        # Also keep old name for backward compatibility
        art["is_ripper_related"] = art["is_whitechapel"]

    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"articles": articles}, f, indent=2, ensure_ascii=False)

    # Summary Stats
    ripper_news = sum(1 for a in articles if a["is_whitechapel"])
    print("-" * 30)
    print(f"Tagging Complete!")
    print(f"Total articles processed: {len(articles)}")
    print(f"Whitechapel/Ripper detections: {ripper_news}")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()