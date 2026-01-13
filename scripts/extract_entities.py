#!/usr/bin/env python3
"""
Extract named entities (people, places) from articles using spaCy NER.
Outputs entity data for use in network visualization.
"""

import json
import spacy
from collections import defaultdict
from pathlib import Path

def load_articles():
    """Load tagged articles from JSON."""
    with open('data/processed/tagged_articles.json', 'r') as f:
        data = json.load(f)
    return data['articles']

def extract_entities_from_articles(articles, sample_size=None):
    """
    Extract named entities from articles using spaCy.

    Args:
        articles: List of article dictionaries
        sample_size: If set, only process first N articles (for testing)

    Returns:
        dict with entity information and article-entity mappings
    """
    # Load spaCy English model
    print("Loading spaCy model...")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("Downloading spaCy English model...")
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
        nlp = spacy.load("en_core_web_sm")

    # Entity counts
    people = defaultdict(int)
    places = defaultdict(int)
    organizations = defaultdict(int)

    # Article-entity mappings
    article_entities = []

    # Process articles
    articles_to_process = articles[:sample_size] if sample_size else articles
    total = len(articles_to_process)

    print(f"Processing {total} articles...")

    for i, article in enumerate(articles_to_process):
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{total} articles...")

        article_id = article['article_id']
        text = article.get('full_text', '')
        headline = article.get('headline', '')
        combined_text = f"{headline}. {text}"

        # Skip if no text
        if not combined_text.strip():
            continue

        # Process with spaCy (limit to first 1000000 chars for performance)
        doc = nlp(combined_text[:1000000])

        # Extract entities
        article_people = set()
        article_places = set()
        article_orgs = set()

        for ent in doc.ents:
            # Clean entity text
            entity_text = ent.text.strip()

            # Skip single-character or very short entities
            if len(entity_text) <= 2:
                continue

            # Skip entities that are all uppercase (likely acronyms or OCR errors)
            if entity_text.isupper() and len(entity_text) > 1:
                continue

            if ent.label_ == 'PERSON':
                people[entity_text] += 1
                article_people.add(entity_text)
            elif ent.label_ in ['GPE', 'LOC']:  # Geopolitical entity or location
                places[entity_text] += 1
                article_places.add(entity_text)
            elif ent.label_ == 'ORG':
                organizations[entity_text] += 1
                article_orgs.add(entity_text)

        # Store article-entity mapping
        if article_people or article_places:
            article_entities.append({
                'article_id': article_id,
                'date': article.get('date'),
                'is_whitechapel': article.get('is_whitechapel', False),
                'is_ripper_related': article.get('is_ripper_related', False),
                'people': list(article_people),
                'places': list(article_places),
                'organizations': list(article_orgs)
            })

    print(f"Extracted {len(people)} unique people, {len(places)} unique places, {len(organizations)} organizations")

    return {
        'people': dict(people),
        'places': dict(places),
        'organizations': dict(organizations),
        'article_entities': article_entities
    }

def filter_entities(entities_data, min_mentions=2):
    """Filter entities to only include those mentioned at least min_mentions times."""

    # Filter each entity type
    filtered_people = {k: v for k, v in entities_data['people'].items() if v >= min_mentions}
    filtered_places = {k: v for k, v in entities_data['places'].items() if v >= min_mentions}
    filtered_orgs = {k: v for k, v in entities_data['organizations'].items() if v >= min_mentions}

    # Filter article entities to only include filtered entities
    filtered_entities = set(filtered_people.keys()) | set(filtered_places.keys()) | set(filtered_orgs.keys())

    filtered_article_entities = []
    for article in entities_data['article_entities']:
        filtered_article = {
            **article,
            'people': [p for p in article['people'] if p in filtered_people],
            'places': [p for p in article['places'] if p in filtered_places],
            'organizations': [o for o in article['organizations'] if o in filtered_orgs]
        }

        # Only include if article has at least one filtered entity
        if filtered_article['people'] or filtered_article['places'] or filtered_article['organizations']:
            filtered_article_entities.append(filtered_article)

    print(f"After filtering (min {min_mentions} mentions):")
    print(f"  People: {len(filtered_people)}")
    print(f"  Places: {len(filtered_places)}")
    print(f"  Organizations: {len(filtered_orgs)}")
    print(f"  Articles with entities: {len(filtered_article_entities)}")

    return {
        'people': filtered_people,
        'places': filtered_places,
        'organizations': filtered_orgs,
        'article_entities': filtered_article_entities
    }

def main():
    """Main execution."""
    print("Loading articles...")
    articles = load_articles()
    print(f"Loaded {len(articles)} articles")

    # Extract entities (use sample_size=100 for quick testing)
    entities_data = extract_entities_from_articles(articles, sample_size=None)

    # Filter to entities mentioned at least twice
    filtered_data = filter_entities(entities_data, min_mentions=2)

    # Save to file
    output_path = Path('data/processed/entities.json')
    with open(output_path, 'w') as f:
        json.dump(filtered_data, f, indent=2)

    print(f"\nSaved entity data to {output_path}")

    # Print top entities
    print("\nTop 20 people:")
    top_people = sorted(filtered_data['people'].items(), key=lambda x: x[1], reverse=True)[:20]
    for name, count in top_people:
        print(f"  {name}: {count} mentions")

    print("\nTop 20 places:")
    top_places = sorted(filtered_data['places'].items(), key=lambda x: x[1], reverse=True)[:20]
    for name, count in top_places:
        print(f"  {name}: {count} mentions")

if __name__ == '__main__':
    main()
