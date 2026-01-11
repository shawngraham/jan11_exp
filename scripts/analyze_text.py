#!/usr/bin/env python3
"""
Text Analysis Script
Analyzes language, word frequency, and patterns in Whitechapel articles
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict

# Common stop words to exclude from analysis
STOP_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
    'was', 'were', 'been', 'has', 'had', 'are', 'is', 'am', 'can', 'could',
    'about', 'into', 'than', 'them', 'these', 'so', 'some', 'what', 'which',
    'when', 'where', 'who', 'whom', 'whose', 'why', 'how', 'more', 'most',
    'other', 'such', 'no', 'nor', 'only', 'own', 'same', 'then', 'very',
    'too', 'also', 'just', 'being', 'over', 'both', 'through', 'during',
    'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'again',
    'further', 'once', 'here', 'any', 'each', 'few', 'because', 'until',
    'while', 'since'
}

def clean_word(word):
    """Clean and normalize a word"""
    # Remove punctuation, convert to lowercase
    word = re.sub(r'[^\w\s-]', '', word.lower())
    return word.strip()

def extract_words(text):
    """Extract cleaned words from text"""
    words = text.split()
    cleaned = [clean_word(w) for w in words]
    # Filter out stop words and short words
    return [w for w in cleaned if w and len(w) > 2 and w not in STOP_WORDS]

def analyze_word_frequency(articles):
    """Analyze word frequency across articles"""
    word_freq = Counter()
    bigram_freq = Counter()

    for article in articles:
        words = extract_words(article.get("full_text", ""))
        word_freq.update(words)

        # Extract bigrams (two-word phrases)
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            bigram_freq.update([bigram])

    return word_freq, bigram_freq

def extract_sensational_language(articles):
    """Identify sensational or dramatic language"""
    sensational_words = {
        'horror', 'horrible', 'terrible', 'shocking', 'brutal', 'savage',
        'fiend', 'monster', 'ghastly', 'dreadful', 'frightful', 'atrocious',
        'heinous', 'gruesome', 'grisly', 'macabre', 'sinister', 'diabolical',
        'mysterious', 'terror', 'panic', 'fear', 'blood', 'mutilated'
    }

    sensational_usage = defaultdict(list)

    for article in articles:
        text_lower = article.get("full_text", "").lower()

        for word in sensational_words:
            if word in text_lower:
                # Count occurrences
                count = text_lower.count(word)
                sensational_usage[word].append({
                    "article_id": article["global_article_id"],
                    "count": count
                })

    # Summarize
    summary = {
        word: {
            "total_uses": sum(item["count"] for item in uses),
            "articles_using": len(uses)
        }
        for word, uses in sensational_usage.items()
        if uses
    }

    return summary

def analyze_sentence_patterns(articles):
    """Analyze sentence structure and patterns"""
    sentence_lengths = []
    question_count = 0
    exclamation_count = 0

    for article in articles:
        text = article.get("full_text", "")

        # Split into sentences (rough approximation)
        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            words = extract_words(sentence)
            if words:
                sentence_lengths.append(len(words))

        question_count += text.count('?')
        exclamation_count += text.count('!')

    avg_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0

    return {
        "average_sentence_length": avg_length,
        "total_questions": question_count,
        "total_exclamations": exclamation_count,
        "sentences_analyzed": len(sentence_lengths)
    }

def compare_whitechapel_vs_other(whitechapel_articles, other_crime_articles):
    """Compare language in Whitechapel articles vs other crime articles"""
    wc_word_freq, wc_bigram_freq = analyze_word_frequency(whitechapel_articles)
    other_word_freq, other_bigram_freq = analyze_word_frequency(other_crime_articles)

    # Find distinctive words (used more in Whitechapel)
    wc_total = sum(wc_word_freq.values())
    other_total = sum(other_word_freq.values())

    distinctive_wc = []

    for word, count in wc_word_freq.most_common(100):
        wc_ratio = count / wc_total if wc_total > 0 else 0
        other_ratio = other_word_freq.get(word, 0) / other_total if other_total > 0 else 0

        if wc_ratio > other_ratio * 2:  # Used at least 2x more in Whitechapel
            distinctive_wc.append({
                "word": word,
                "whitechapel_count": count,
                "other_count": other_word_freq.get(word, 0),
                "ratio": wc_ratio / other_ratio if other_ratio > 0 else float('inf')
            })

    return distinctive_wc[:20]  # Top 20

def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / "data" / "processed" / "tagged_articles.json"
    output_file = base_dir / "data" / "processed" / "text_analysis.json"

    # Check if input exists
    if not input_file.exists():
        print(f"Error: Tagged articles not found at {input_file}")
        print("Please run tag_articles.py first.")
        return

    # Load articles
    print(f"Loading articles from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = data["articles"]

    # Separate Whitechapel and other crime articles
    whitechapel_articles = [a for a in articles if a.get("is_whitechapel", False)]
    other_crime_articles = [
        a for a in articles
        if not a.get("is_whitechapel", False) and
        any(tag["tag"] == "crime_general" for tag in a.get("tags", []))
    ]

    print(f"Analyzing {len(whitechapel_articles)} Whitechapel articles...")
    print(f"Comparing with {len(other_crime_articles)} other crime articles...")

    # Analyze Whitechapel articles
    wc_word_freq, wc_bigram_freq = analyze_word_frequency(whitechapel_articles)
    sensational = extract_sensational_language(whitechapel_articles)
    sentence_patterns = analyze_sentence_patterns(whitechapel_articles)

    # Compare with other articles
    distinctive_words = []
    if other_crime_articles:
        distinctive_words = compare_whitechapel_vs_other(
            whitechapel_articles,
            other_crime_articles
        )

    # Prepare word cloud data (top 100 words with counts)
    word_cloud_data = [
        {"text": word, "size": count}
        for word, count in wc_word_freq.most_common(100)
    ]

    # Create output
    analysis_data = {
        "whitechapel_articles_analyzed": len(whitechapel_articles),
        "total_words": sum(wc_word_freq.values()),
        "unique_words": len(wc_word_freq),
        "word_frequency": {
            "top_words": [
                {"word": word, "count": count}
                for word, count in wc_word_freq.most_common(50)
            ],
            "top_phrases": [
                {"phrase": phrase, "count": count}
                for phrase, count in wc_bigram_freq.most_common(30)
            ]
        },
        "word_cloud_data": word_cloud_data,
        "sensational_language": sensational,
        "sentence_patterns": sentence_patterns,
        "distinctive_whitechapel_words": distinctive_words
    }

    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"Text analysis complete!")
    print(f"Results saved to {output_file}")
    print(f"\nSummary:")
    print(f"  Total words analyzed: {analysis_data['total_words']}")
    print(f"  Unique words: {analysis_data['unique_words']}")
    print(f"  Avg sentence length: {sentence_patterns['average_sentence_length']:.1f} words")

    print(f"\nTop 10 words:")
    for item in analysis_data["word_frequency"]["top_words"][:10]:
        print(f"    {item['word']}: {item['count']}")

    print(f"\nTop sensational words:")
    sorted_sensational = sorted(
        sensational.items(),
        key=lambda x: x[1]['total_uses'],
        reverse=True
    )
    for word, stats in sorted_sensational[:10]:
        print(f"    {word}: {stats['total_uses']} uses in {stats['articles_using']} articles")

if __name__ == "__main__":
    main()
