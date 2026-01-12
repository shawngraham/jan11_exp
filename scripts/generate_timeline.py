#!usr/bin/env python3
"""
Step 5: Timeline Generation
- Correlates London events with local Canadian reporting.
- Calculates news "lag" (Telegraphic vs. Printed delay).
- Uses the 'date' metadata extracted from filenames.
"""

import json
from datetime import datetime
from pathlib import Path

# Canonical Whitechapel murders and key media events
LONDON_EVENTS = [
    {"id": "lon_01", "date": "1888-08-31", "title": "Mary Ann Nichols", "location": "Buck's Row", "type": "murder"},
    {"id": "lon_02", "date": "1888-09-08", "title": "Annie Chapman", "location": "Hanbury Street", "type": "murder"},
    {"id": "lon_03", "date": "1888-09-27", "title": "'Dear Boss' Letter", "location": "London", "type": "event"},
    {"id": "lon_04", "date": "1888-09-30", "title": "Double Event (Stride/Eddowes)", "location": "Whitechapel", "type": "murder"},
    {"id": "lon_05", "date": "1888-10-01", "title": "'Saucy Jacky' Postcard", "location": "London", "type": "event"},
    {"id": "lon_06", "date": "1888-10-16", "title": "Lusk 'From Hell' Letter", "location": "London", "type": "event"},
    {"id": "lon_07", "date": "1888-11-09", "title": "Mary Jane Kelly", "location": "Miller's Court", "type": "murder"}
]

def calculate_time_lag(london_date_str, shawville_date_str):
    """Calculate days between London event and Canadian publication."""
    try:
        london = datetime.strptime(london_date_str, "%Y-%m-%d")
        shawville = datetime.strptime(shawville_date_str, "%Y-%m-%d")
        return (shawville - london).days
    except Exception:
        return None

def main():
    # Setup paths
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    input_file = project_root / "data" / "processed" / "tagged_articles.json"
    output_file = project_root / "data" / "processed" / "timeline.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run tagging first.")
        return

    # Load tagged articles
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    
    # FILTER: Aligning with the tag name used in Step 4
    # Note: We check for 'is_whitechapel' or 'is_ripper_related' 
    whitechapel_articles = [a for a in articles if a.get("is_whitechapel") or a.get("is_ripper_related")]
    
    print(f"Analyzing {len(whitechapel_articles)} articles for timeline correlation...")

    shawville_events = []

    for art in whitechapel_articles:
        date_iso = art.get("date") 
        if not date_iso: continue
        
        # Display formatting (e.g., Oct 25, 1888)
        try:
            dt = datetime.strptime(date_iso, "%Y-%m-%d")
            date_display = dt.strftime("%b %d, %Y")
        except:
            date_display = date_iso

        # Get the text using new or old field names
        text = art.get("full_text", art.get("text", ""))

        event = {
            "article_id": art["article_id"],
            "pub": art.get("source_pdf", art.get("pub")),
            "date": date_iso,
            "date_display": date_display,
            "headline": art.get("headline", "Untitled Report"),
            "snippet": text[:200] + "..." if len(text) > 200 else text,
            "page": art.get("page_number", art.get("page")),
            "column": art.get("column"),
            "type": "publication"
        }

        # CALCULATE LAG: Find the most recent London event preceding this newspaper date
        preceding_events = [
            e for e in LONDON_EVENTS 
            if e["date"] <= date_iso
        ]
        
        if preceding_events:
            # The "trigger" event is the one closest to the publication date
            trigger = sorted(preceding_events, key=lambda x: x["date"])[-1]
            lag = calculate_time_lag(trigger["date"], date_iso)
            
            event["correlated_event"] = trigger["title"]
            event["days_since_event"] = lag
            event["historical_context"] = f"Reported {lag} days after the {trigger['title']}."

        shawville_events.append(event)

    # Compile Final Timeline
    # We sort by date to ensure the "narrative" flows correctly
    timeline_data = {
        "london_canonical_events": LONDON_EVENTS,
        "canadian_reports": sorted(shawville_events, key=lambda x: x['date']),
        "statistics": {
            "total_matches": len(whitechapel_articles),
            "total_london_events": len(LONDON_EVENTS),
            "generated_at": datetime.now().isoformat()
        }
    }

    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(timeline_data, f, indent=2, ensure_ascii=False)

    # Analysis Summary
    print("-" * 30)
    print(f"Timeline Generated: {output_file}")
    if shawville_events:
        lags = [e["days_since_event"] for e in shawville_events if "days_since_event" in e]
        avg_lag = sum(lags) / len(lags) if lags else 0
        print(f"Average information lag: {avg_lag:.1f} days.")

if __name__ == "__main__":
    main()