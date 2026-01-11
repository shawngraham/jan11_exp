#!/usr/bin/env python3
"""
Automated Article Tagging Script
Classifies articles based on keyword matching and content analysis
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Tag definitions with keywords
TAG_KEYWORDS = {
    "whitechapel_ripper": {
        "keywords": [
            "whitechapel", "jack the ripper", "ripper", "east end murders",
            "leather apron", "spitalfields", "commercial road", "dorset street",
            "mary kelly", "annie chapman", "elizabeth stride", "catherine eddowes",
            "mary nichols", "polly nichols"
        ],
        "patterns": [
            r"whitechapel.*murder",
            r"ripper.*case",
            r"east\s+end.*horror"
        ],
        "weight": 10  # High priority tag
    },
    "crime_general": {
        "keywords": [
            "murder", "murdered", "crime", "criminal", "police", "constable",
            "arrest", "arrested", "trial", "prisoner", "jail", "gaol",
            "detective", "investigation", "suspect", "accused", "guilty",
            "victim", "killing", "theft", "robbery", "burglar"
        ],
        "patterns": [
            r"charge[d]?\s+with",
            r"found\s+guilty",
            r"sentenced\s+to"
        ],
        "weight": 5
    },
    "british_empire": {
        "keywords": [
            "london", "england", "britain", "british", "queen victoria",
            "westminster", "downing street", "house of commons", "house of lords",
            "scotland yard", "metropolitan police", "thames",
            "manchester", "liverpool", "birmingham", "glasgow",
            "india", "colonial office", "empire", "colony", "imperial"
        ],
        "patterns": [
            r"london.*news",
            r"from\s+london",
            r"english\s+.*affairs"
        ],
        "weight": 6,
        # Exclude parliament-only references (handled separately)
        "exclude_if_only": ["parliament", "parliamentary"]
    },
    "local_shawville": {
        "keywords": [
            "shawville", "pontiac", "ottawa valley", "clarendon",
            "bristol", "fort coulonge", "campbell's bay", "aylmer",
            "chapeau", "quyon", "bryson"
        ],
        "patterns": [
            r"local\s+news",
            r"our\s+town",
            r"in\s+this\s+vicinity"
        ],
        "weight": 8
    },
    "international": {
        "keywords": [
            "france", "germany", "russia", "italy", "spain", "austria",
            "america", "united states", "washington", "new york",
            "china", "japan", "africa", "australia", "mexico",
            "paris", "berlin", "moscow", "rome", "vienna"
        ],
        "patterns": [
            r"foreign\s+news",
            r"from\s+abroad",
            r"cable\s+dispatch"
        ],
        "weight": 5
    },
    "canadian": {
        "keywords": [
            "canada", "canadian", "ottawa", "montreal", "toronto", "quebec",
            "dominion", "ontario", "macdonald", "laurier", "governor general"
        ],
        "patterns": [
            r"canadian\s+.*news",
            r"dominion\s+.*affairs"
        ],
        "weight": 7
    },
    "advertisement": {
        "keywords": [
            "for sale", "wanted", "notice", "bargain", "price", "cents",
            "dollar", "cheap", "advertisement", "classified",
            "buy now", "special offer", "discount"
        ],
        "patterns": [
            r"\$\d+\.\d+",
            r"apply\s+to",
            r"inquire\s+at"
        ],
        "weight": 3
    },
    "social_cultural": {
        "keywords": [
            "church", "sermon", "marriage", "wedding", "funeral", "death",
            "social", "entertainment", "concert", "lecture", "meeting",
            "society", "club", "association", "agricultural", "fair"
        ],
        "patterns": [
            r"social\s+event",
            r"will\s+be\s+held",
            r"passed\s+away"
        ],
        "weight": 4
    }
}

def normalize_text(text):
    """Normalize text for matching"""
    return text.lower().strip()

def calculate_tag_scores(article_text, headline=""):
    """
    Calculate confidence scores for each tag

    Returns:
        Dictionary of tag -> score
    """
    combined_text = normalize_text(headline + " " + article_text)
    scores = defaultdict(float)

    for tag, config in TAG_KEYWORDS.items():
        score = 0

        # Check keywords
        for keyword in config["keywords"]:
            keyword_lower = keyword.lower()
            # Count occurrences, weight by importance
            count = combined_text.count(keyword_lower)
            if count > 0:
                # More weight to headline matches
                headline_matches = normalize_text(headline).count(keyword_lower)
                body_matches = count - headline_matches
                score += (headline_matches * 2) + body_matches

        # Check regex patterns
        for pattern in config.get("patterns", []):
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            score += len(matches) * 2  # Patterns worth more

        # Apply tag weight
        score *= config["weight"]

        # Check exclusions
        if "exclude_if_only" in config:
            # Only exclude if ONLY those keywords match and nothing else
            exclude_words = config["exclude_if_only"]
            has_only_exclude = all(
                word.lower() in combined_text for word in exclude_words
            )
            has_other_keywords = any(
                kw.lower() in combined_text
                for kw in config["keywords"]
                if kw.lower() not in [w.lower() for w in exclude_words]
            )

            if has_only_exclude and not has_other_keywords:
                score = 0

        scores[tag] = score

    return scores

def assign_tags(article):
    """
    Assign tags to an article based on content

    Returns:
        Updated article with tags and confidence scores
    """
    text = article.get("full_text", "")
    headline = article.get("headline", "")

    # Calculate scores
    scores = calculate_tag_scores(text, headline)

    # Determine primary tags (score > threshold)
    threshold = 5
    assigned_tags = []

    for tag, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        if score > threshold:
            assigned_tags.append({
                "tag": tag,
                "confidence": min(1.0, score / 50)  # Normalize to 0-1
            })

    # Always assign at least one tag (highest scoring)
    if not assigned_tags and scores:
        best_tag = max(scores.items(), key=lambda x: x[1])
        assigned_tags.append({
            "tag": best_tag[0],
            "confidence": 0.3  # Low confidence
        })

    # Special handling: mark Whitechapel articles prominently
    is_whitechapel = any(tag["tag"] == "whitechapel_ripper" for tag in assigned_tags)

    article["tags"] = assigned_tags
    article["is_whitechapel"] = is_whitechapel
    article["primary_tag"] = assigned_tags[0]["tag"] if assigned_tags else "unknown"

    return article

def generate_statistics(articles):
    """Generate statistics about tagged articles"""
    stats = {
        "total_articles": len(articles),
        "tag_distribution": defaultdict(int),
        "whitechapel_articles": 0,
        "average_tags_per_article": 0,
        "articles_by_primary_tag": defaultdict(list)
    }

    total_tags = 0

    for article in articles:
        # Count tags
        for tag_info in article.get("tags", []):
            stats["tag_distribution"][tag_info["tag"]] += 1
            total_tags += 1

        # Count Whitechapel
        if article.get("is_whitechapel"):
            stats["whitechapel_articles"] += 1

        # Group by primary tag
        primary = article.get("primary_tag", "unknown")
        stats["articles_by_primary_tag"][primary].append(article["global_article_id"])

    stats["average_tags_per_article"] = total_tags / len(articles) if articles else 0

    return stats

def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / "data" / "processed" / "articles.json"
    output_file = base_dir / "data" / "processed" / "tagged_articles.json"
    stats_file = base_dir / "data" / "processed" / "tagging_stats.json"

    # Check if input exists
    if not input_file.exists():
        print(f"Error: Articles file not found at {input_file}")
        print("Please run segment_articles.py first.")
        return

    # Load articles
    print(f"Loading articles from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = data["articles"]
    print(f"Processing {len(articles)} articles...")

    # Tag each article
    for i, article in enumerate(articles, 1):
        assign_tags(article)
        if i % 50 == 0:
            print(f"  Tagged {i}/{len(articles)} articles...")

    # Generate statistics
    stats = generate_statistics(articles)

    # Save results
    output_data = {
        "total_articles": len(articles),
        "articles": articles
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(dict(stats), f, indent=2, default=list)

    print("=" * 60)
    print(f"Tagging complete!")
    print(f"Results saved to {output_file}")
    print(f"Statistics saved to {stats_file}")
    print(f"\nSummary:")
    print(f"  Total articles: {stats['total_articles']}")
    print(f"  Whitechapel articles: {stats['whitechapel_articles']}")
    print(f"  Average tags per article: {stats['average_tags_per_article']:.2f}")
    print(f"\nTag distribution:")
    for tag, count in sorted(stats['tag_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"    {tag}: {count}")

if __name__ == "__main__":
    main()
