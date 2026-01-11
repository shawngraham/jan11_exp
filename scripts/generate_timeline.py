#!/usr/bin/env python3
"""
Timeline Generation Script
Creates dual timeline data: London Whitechapel murders vs Shawville publications
"""

import json
from datetime import datetime
from pathlib import Path

# Canonical Whitechapel murders (the "canonical five")
LONDON_EVENTS = [
    {
        "id": "london_01",
        "date": "1888-08-31",
        "date_display": "August 31, 1888",
        "title": "Mary Ann Nichols",
        "description": "First canonical victim found in Buck's Row, Whitechapel",
        "location": "Buck's Row, Whitechapel",
        "type": "murder",
        "category": "london"
    },
    {
        "id": "london_02",
        "date": "1888-09-08",
        "date_display": "September 8, 1888",
        "title": "Annie Chapman",
        "description": "Second victim found in backyard of 29 Hanbury Street",
        "location": "Hanbury Street, Spitalfields",
        "type": "murder",
        "category": "london"
    },
    {
        "id": "london_03",
        "date": "1888-09-30",
        "date_display": "September 30, 1888",
        "title": "Elizabeth Stride",
        "description": "Third victim found in Dutfield's Yard (Double Event night)",
        "location": "Dutfield's Yard, Whitechapel",
        "type": "murder",
        "category": "london"
    },
    {
        "id": "london_04",
        "date": "1888-09-30",
        "date_display": "September 30, 1888",
        "title": "Catherine Eddowes",
        "description": "Fourth victim found in Mitre Square (Double Event night)",
        "location": "Mitre Square, City of London",
        "type": "murder",
        "category": "london"
    },
    {
        "id": "london_05",
        "date": "1888-11-09",
        "date_display": "November 9, 1888",
        "title": "Mary Jane Kelly",
        "description": "Fifth and final canonical victim found in her room",
        "location": "13 Miller's Court, Spitalfields",
        "type": "murder",
        "category": "london"
    },
    # Additional notable events
    {
        "id": "london_06",
        "date": "1888-09-27",
        "date_display": "September 27, 1888",
        "title": "'Dear Boss' Letter",
        "description": "Letter signed 'Jack the Ripper' received by Central News Agency",
        "location": "London",
        "type": "event",
        "category": "london"
    },
    {
        "id": "london_07",
        "date": "1888-10-01",
        "date_display": "October 1, 1888",
        "title": "'Saucy Jacky' Postcard",
        "description": "Postcard referencing the 'double event' murders",
        "location": "London",
        "type": "event",
        "category": "london"
    }
]

def parse_date(date_string):
    """
    Parse various date formats to ISO format

    Common patterns in 1880s newspapers:
    - "September 15, 1888"
    - "Sept. 15, 1888"
    - "15 September 1888"
    """
    if not date_string:
        return None

    # Month name mapping
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sept': 9, 'sep': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }

    date_lower = date_string.lower().replace('.', '').replace(',', '')
    parts = date_lower.split()

    try:
        # Try pattern: "September 15 1888"
        if len(parts) >= 3:
            month_str = parts[0]
            day = parts[1]
            year = parts[2]

            if month_str in months:
                return f"{year}-{months[month_str]:02d}-{int(day):02d}"

        # Try pattern: "15 September 1888"
        if len(parts) >= 3 and parts[0].isdigit():
            day = parts[0]
            month_str = parts[1]
            year = parts[2]

            if month_str in months:
                return f"{year}-{months[month_str]:02d}-{int(day):02d}"

    except (ValueError, IndexError):
        pass

    return None

def extract_publication_date_from_pdf_name(pdf_name):
    """
    Extract date from PDF filename if it follows a pattern
    e.g., "equity_1888_09_15.pdf" or "1888-09-15.pdf"
    """
    import re

    # Pattern: YYYY-MM-DD or YYYY_MM_DD
    pattern = r'(\d{4})[-_](\d{2})[-_](\d{2})'
    match = re.search(pattern, pdf_name)

    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"

    # Pattern: YYYYMMDD
    pattern = r'(\d{4})(\d{2})(\d{2})'
    match = re.search(pattern, pdf_name)

    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"

    return None

def calculate_time_lag(london_date, shawville_date):
    """Calculate days between London event and Shawville publication"""
    try:
        london = datetime.fromisoformat(london_date)
        shawville = datetime.fromisoformat(shawville_date)
        delta = (shawville - london).days
        return delta
    except:
        return None

def create_shawville_events(articles):
    """Create timeline events from Shawville articles"""
    shawville_events = []

    # Filter for Whitechapel articles
    whitechapel_articles = [a for a in articles if a.get("is_whitechapel", False)]

    print(f"Found {len(whitechapel_articles)} Whitechapel articles")

    for article in whitechapel_articles:
        # Try to get date from article or PDF name
        date_iso = None
        date_display = None

        if article.get("extracted_date"):
            date_iso = parse_date(article["extracted_date"])
            date_display = article["extracted_date"]

        # Fallback: try PDF name
        if not date_iso:
            date_iso = extract_publication_date_from_pdf_name(article.get("source_pdf", ""))

        # Create display date if we have ISO
        if date_iso and not date_display:
            try:
                dt = datetime.fromisoformat(date_iso)
                date_display = dt.strftime("%B %d, %Y")
            except:
                date_display = date_iso

        # Create event
        event = {
            "id": article["global_article_id"],
            "date": date_iso,
            "date_display": date_display or "Date unknown",
            "title": article.get("headline") or "Whitechapel Article",
            "description": article["full_text"][:200] + "..." if len(article["full_text"]) > 200 else article["full_text"],
            "source_pdf": article.get("source_pdf", ""),
            "page_number": article.get("page_number", ""),
            "article_id": article["global_article_id"],
            "type": "publication",
            "category": "shawville"
        }

        # Calculate lag if possible
        if date_iso:
            # Find closest preceding London murder
            preceding_murders = [
                e for e in LONDON_EVENTS
                if e["type"] == "murder" and e["date"] <= date_iso
            ]
            if preceding_murders:
                closest_murder = max(preceding_murders, key=lambda e: e["date"])
                lag = calculate_time_lag(closest_murder["date"], date_iso)
                if lag:
                    event["time_lag_days"] = lag
                    event["related_london_event"] = closest_murder["id"]

        shawville_events.append(event)

    return shawville_events

def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / "data" / "processed" / "tagged_articles.json"
    output_file = base_dir / "data" / "processed" / "timeline.json"

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

    # Create Shawville events
    print("Generating Shawville timeline events...")
    shawville_events = create_shawville_events(articles)

    # Sort events by date
    london_sorted = sorted(LONDON_EVENTS, key=lambda e: e["date"])
    shawville_sorted = sorted(
        [e for e in shawville_events if e["date"]],
        key=lambda e: e["date"]
    )
    shawville_no_date = [e for e in shawville_events if not e["date"]]

    # Calculate date range
    all_dates = [e["date"] for e in london_sorted + shawville_sorted]
    date_range = {
        "start": min(all_dates) if all_dates else "1888-08-01",
        "end": max(all_dates) if all_dates else "1895-12-31"
    }

    # Create output
    timeline_data = {
        "date_range": date_range,
        "london_events": london_sorted,
        "shawville_events": shawville_sorted + shawville_no_date,
        "statistics": {
            "total_london_events": len(london_sorted),
            "total_shawville_publications": len(shawville_events),
            "shawville_with_dates": len(shawville_sorted),
            "shawville_without_dates": len(shawville_no_date),
            "average_time_lag_days": None
        }
    }

    # Calculate average lag
    lags = [e["time_lag_days"] for e in shawville_sorted if "time_lag_days" in e]
    if lags:
        timeline_data["statistics"]["average_time_lag_days"] = sum(lags) / len(lags)

    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(timeline_data, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"Timeline generation complete!")
    print(f"Results saved to {output_file}")
    print(f"\nSummary:")
    print(f"  London events: {len(london_sorted)}")
    print(f"  Shawville publications: {len(shawville_events)}")
    print(f"    - With dates: {len(shawville_sorted)}")
    print(f"    - Without dates: {len(shawville_no_date)}")

    if lags:
        print(f"  Average time lag: {sum(lags) / len(lags):.1f} days")
        print(f"  Min lag: {min(lags)} days")
        print(f"  Max lag: {max(lags)} days")

if __name__ == "__main__":
    main()
