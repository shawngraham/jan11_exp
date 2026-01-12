#!/usr/bin/env python3
"""
Text Analysis Script
Analyzes language across ALL articles and compares Whitechapel vs General reporting.
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict

# Common stop words to exclude from frequency analysis
STOP_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'for', 'not', 'on', 
    'with', 'he', 'as', 'it', 'was', 'his', 'by', 'from', 'at', 'this', 'but', 
    'had', 'are', 'which', 'or', 'an', 'been', 'were', 'their', 'there', 'one', 
    'all', 'would', 'said', 'they', 'who', 'will', 'has', 'about', 'can', 'if'
}

SENSATIONAL_WORDS = {
    'horror', 'horrible', 'terrible', 'shocking', 'brutal', 'savage',
    'fiend', 'monster', 'ghastly', 'dreadful', 'frightful', 'atrocious',
    'heinous', 'gruesome', 'grisly', 'macabre', 'sinister', 'diabolical',
    'mysterious', 'terror', 'panic', 'fear', 'blood', 'mutilated', 'outrage'
}

def clean_word(word):
    return re.sub(r'[^\w\s]', '', word.lower()).strip()

def get_words(text):
    words = [clean_word(w) for w in text.split()]
    return [w for w in words if w and len(w) > 2 and w not in STOP_WORDS]

def analyze_group(articles):
    """Generates counts and stats for a specific group of articles."""
    if not articles:
        return {}
    
    word_counts = Counter()
    bigram_counts = Counter()
    sensational_counts = Counter()
    total_excl = 0
    sentence_lengths = []

    for art in articles:
        text = art.get("text", "")
        clean_text = text.lower()
        
        # 1. Word/Bigram frequency
        words = get_words(text)
        word_counts.update(words)
        for i in range(len(words) - 1):
            bigram_counts.update([f"{words[i]} {words[i+1]}"])
        
        # 2. Sensationalism
        for word in SENSATIONAL_WORDS:
            matches = len(re.findall(rf'\b{word}\b', clean_text))
            sensational_counts[word] += matches
            
        # 3. Sentence/Punctuation patterns
        total_excl += text.count("!")
        sentences = re.split(r'[.!?]+', text)
        sentence_lengths.extend([len(s.split()) for s in sentences if len(s.split()) > 1])

    return {
        "article_count": len(articles),
        "total_words": sum(word_counts.values()),
        "avg_sentence_len": round(sum(sentence_lengths)/len(sentence_lengths), 1) if sentence_lengths else 0,
        "exclamation_rate": round(total_excl / len(articles), 2),
        "top_keywords": word_counts.most_common(50),
        "top_phrases": bigram_counts.most_common(20),
        "sensational_total": sum(sensational_counts.values())
    }

def main():
    # 1. Path Setup
    script_dir = Path(__file__).parent
    project_root = script_dir if (script_dir / "data").exists() else script_dir.parent
    input_file = project_root / "data" / "processed" / "tagged_articles.json"
    output_file = project_root / "data" / "processed" / "text_analysis.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    # 2. Load Data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_articles = data.get("articles", [])
    wc_articles = [a for a in all_articles if a.get("is_whitechapel")]
    other_articles = [a for a in all_articles if not a.get("is_whitechapel")]

    print(f"Analyzing {len(all_articles)} total articles...")

    # 3. Comparative Analysis
    stats_global = analyze_group(all_articles)
    stats_whitechapel = analyze_group(wc_articles)
    stats_general = analyze_group(other_articles)

    # 4. Final Report Structure
    analysis_data = {
        "newspaper_overview": {
            "articles_processed": stats_global["article_count"],
            "total_vocabulary_size": len(stats_global["top_keywords"]),
            "avg_sentence_length": stats_global["avg_sentence_len"],
            "top_words": [{"word": w, "count": c} for w, c in stats_global["top_keywords"][:50]]
        },
        "comparison": {
            "whitechapel": {
                "exclamation_intensity": stats_whitechapel.get("exclamation_rate", 0),
                "sensational_word_count": stats_whitechapel.get("sensational_total", 0),
                "top_phrases": [{"phrase": p, "count": c} for p, c in stats_whitechapel.get("top_phrases", [])]
            },
            "general_news": {
                "exclamation_intensity": stats_general.get("exclamation_rate", 0),
                "sensational_word_count": stats_general.get("sensational_total", 0),
                "top_phrases": [{"phrase": p, "count": c} for p, c in stats_general.get("top_phrases", [])]
            }
        }
    }

    # 5. Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("Full Text Analysis Complete!")
    print(f"  Total Articles: {len(all_articles)}")
    print(f"  Whitechapel Intensity: {stats_whitechapel.get('exclamation_rate', 0)} ! per article")
    print(f"  General Intensity: {stats_general.get('exclamation_rate', 0)} ! per article")
    print(f"  Saved to: {output_file}")

if __name__ == "__main__":
    main()