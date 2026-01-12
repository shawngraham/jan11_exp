#!/usr/bin/env python3
"""
Step 6: Text Analysis & Comparative Linguistics
- Fixed KeyError when a category has zero articles.
- Compares Ripper reporting vs. General News.
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict

# Common stop words
STOP_WORDS = {
    'the', 'and', 'that', 'with', 'for', 'was', 'his', 'had', 'they', 'from',
    'said', 'were', 'been', 'which', 'there', 'this', 'would', 'their', 'will',
    'upon', 'then', 'into', 'them', 'when', 'more', 'some', 'than'
}

SENSATIONAL_WORDS = {
    'horror', 'horrible', 'terrible', 'shocking', 'brutal', 'savage',
    'fiend', 'monster', 'ghastly', 'dreadful', 'frightful', 'atrocious',
    'heinous', 'gruesome', 'grisly', 'macabre', 'sinister', 'diabolical',
    'mysterious', 'terror', 'panic', 'fear', 'blood', 'mutilated', 'outrage'
}

def clean_word(word):
    return re.sub(r'[^\w]', '', word.lower())

def get_words(text):
    words = [clean_word(w) for w in text.split()]
    return [w for w in words if len(w) > 2 and w not in STOP_WORDS]

def analyze_group(articles):
    """Generates counts and stats. Returns default values if articles list is empty."""
    # Default structure to prevent KeyErrors downstream
    results = {
        "article_count": len(articles),
        "total_words": 0,
        "avg_sentence_len": 0,
        "exclamation_intensity": 0,
        "sensational_score": 0,
        "top_keywords": [],
        "top_phrases": [],
        "sensational_word_details": Counter()
    }

    if not articles:
        return results

    word_counts = Counter()
    bigram_counts = Counter()
    sensational_word_counter = Counter()
    total_excl = 0
    sentence_lengths = []

    for art in articles:
        text = art.get("full_text", "") or art.get("text", "")
        clean_text = text.lower()

        words = get_words(text)
        word_counts.update(words)

        for i in range(len(words) - 1):
            bigram_counts.update([f"{words[i]} {words[i+1]}"])

        for word in SENSATIONAL_WORDS:
            matches = len(re.findall(rf'\b{word}\b', clean_text))
            if matches > 0:
                sensational_word_counter[word] += matches

        total_excl += text.count("!")

        sentences = re.split(r'[.!?]+', text)
        lengths = [len(s.split()) for s in sentences if len(s.split()) > 2]
        if lengths:
            sentence_lengths.extend(lengths)

    # Update the results dictionary with actual data
    results["total_words"] = sum(word_counts.values())
    if sentence_lengths:
        results["avg_sentence_len"] = round(sum(sentence_lengths)/len(sentence_lengths), 1)

    results["exclamation_intensity"] = round(total_excl / len(articles), 2)
    results["sensational_score"] = round(sum(sensational_word_counter.values()) / len(articles), 2) if articles else 0
    results["top_keywords"] = word_counts.most_common(50)
    results["top_phrases"] = bigram_counts.most_common(20)
    results["sensational_word_details"] = sensational_word_counter

    return results

def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    input_file = project_root / "data" / "processed" / "tagged_articles.json"
    output_file = project_root / "data" / "processed" / "text_analysis.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_articles = data.get("articles", [])
    
    # Check for either naming convention of the tag
    wc_articles = [a for a in all_articles if a.get("is_whitechapel") or a.get("is_ripper_related")]
    other_articles = [a for a in all_articles if not (a.get("is_whitechapel") or a.get("is_ripper_related"))]

    print(f"Analyzing {len(all_articles)} total articles...")

    stats_whitechapel = analyze_group(wc_articles)
    stats_general = analyze_group(other_articles)

    # Generate word cloud data from top keywords
    word_cloud_data = [
        {"text": word, "size": count}
        for word, count in stats_whitechapel["top_keywords"][:50]
    ]

    # Generate sensational language data
    sensational_language = {
        word: {
            "total_uses": count,
            "contexts": []  # Could be expanded later
        }
        for word, count in stats_whitechapel["sensational_word_details"].items()
    }

    report = {
        "summary": {
            "total_articles": len(all_articles),
            "ripper_news_count": len(wc_articles)
        },
        "word_cloud_data": word_cloud_data,
        "sensational_language": sensational_language,
        "whitechapel_analysis": {
            "stats": {
                "avg_sentence_length": stats_whitechapel["avg_sentence_len"],
                "exclamations_per_article": stats_whitechapel["exclamation_intensity"],
                "sensational_words_per_article": stats_whitechapel["sensational_score"]
            },
            "top_keywords": [{"word": w, "count": c} for w, c in stats_whitechapel["top_keywords"][:20]],
            "top_phrases": [{"phrase": p, "count": c} for p, c in stats_whitechapel["top_phrases"][:20]]
        },
        "general_news_analysis": {
            "stats": {
                "avg_sentence_length": stats_general["avg_sentence_len"],
                "exclamations_per_article": stats_general["exclamation_intensity"],
                "sensational_words_per_article": stats_general["sensational_score"]
            },
            "top_keywords": [{"word": w, "count": c} for w, c in stats_general["top_keywords"][:20]],
            "top_phrases": [{"phrase": p, "count": c} for p, c in stats_general["top_phrases"][:20]]
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("-" * 30)
    print(f"Analysis Complete! Saved to {output_file}")
    print(f"Identified {len(wc_articles)} Ripper articles and {len(other_articles)} general articles.")

if __name__ == "__main__":
    main()