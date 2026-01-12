#/usr/bin/env python3
"""
Timeline Generation Script
Creates dual timeline data: London Whitechapel murders vs Shawville publications.
Synced with the segment_articles.py and tag_articles.py data structure.
"""

import json
from datetime import datetime
from pathlib import Path

# Canonical Whitechapel murders (the "canonical five") plus key events
LONDON_EVENTS = [
    {"id": "lon_01", "date": "1888-08-31", "title": "Mary Ann Nichols", "location": "Buck's Row, Whitechapel", "type": "murder"},
    {"id": "lon_02", "date": "1888-09-08", "title": "Annie Chapman", "location": "Hanbury Street", "type": "murder"},
    {"id": "lon_03", "date": "1888-09-27", "title": "'Dear Boss' Letter", "location": "Central News Agency", "type": "event"},
    {"id": "lon_04", "date": "1888-09-30", "title": "Elizabeth Stride", "location": "Dutfield's Yard", "type": "murder"},
    {"id": "lon_05", "date": "1888-09-30", "title": "Catherine Eddowes", "location": "Mitre Square", "type": "murder"},
    {"id": "lon_06", "date": "1888-10-01", "title": "'Saucy Jacky' Postcard", "location": "London", "type": "event"},
    {"id": "lon_07", "date": "1888-11-09", "title": "Mary Jane Kelly", "location": "Miller's Court", "type": "murder"}
]

def calculate_time_lag(london_date_str, shawville_date_str):
    """Calculate days between a London event and a Shawville publication."""
    try:
        london = datetime.fromisoformat(london_date_str)
        shawville = datetime.fromisoformat(shawville_date_str)
        return (shawville - london).days
    except:
        return None

def main():
    # 1. Path Setup
    script_dir = Path(__file__).parent
    project_root = script_dir if (script_dir / "data").exists() else script_dir.parent
    
    input_file = project_root / "data" / "processed" / "tagged_articles.json"
    output_file = project_root / "data" / "processed" / "timeline.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run previous steps first.")
        return

    # 2. Load Data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    
    # Filter for Ripper-related articles
    whitechapel_articles = [a for a in articles if a.get("is_whitechapel")]
    print(f"Generating timeline for {len(whitechapel_articles)} Whitechapel articles...")

    shawville_events = []

    # 3. Process Articles into Timeline Events
    for art in whitechapel_articles:
        date_iso = art.get("date") # We already extracted this in Step 3!
        
        # Format a display date (e.g., Oct 25, 1888)
        date_display = date_iso
        try:
            dt = datetime.fromisoformat(date_iso)
            date_display = dt.strftime("%b %d, %Y")
        except:
            pass

        event = {
            "id": art["article_id"],
            "date": date_iso,
            "date_display": date_display,
            "title": art.get("headline", "Whitechapel Report"),
            # Create a short snippet for the timeline UI
            "snippet": art["text"][:150] + "..." if len(art["text"]) > 150 else art["text"],
            "page": art.get("page"),
            "column": art.get("column"),
            "type": "publication",
            "category": "shawville"
        }

        # Calculate Lag from the most recent London murder
        if date_iso:
            preceding_murders = [
                e for e in LONDON_EVENTS 
                if e["type"] == "murder" and e["date"] <= date_iso
            ]
            if preceding_murders:
                # Get the one closest to our publication date
                closest = max(preceding_murders, key=lambda e: e["date"])
                lag = calculate_time_lag(closest["date"], date_iso)
                event["time_lag_days"] = lag
                event["related_murder"] = closest["title"]

        shawville_events.append(event)

    # 4. Final Data Structure
    timeline_data = {
        "london_events": LONDON_EVENTS,
        "shawville_events": sorted(shawville_events, key=lambda x: x['date'] if x['date'] else ""),
        "statistics": {
            "total_articles": len(whitechapel_articles),
            "average_lag": 0
        }
    }

    # Calc Avg Lag
    lags = [e["time_lag_days"] for e in shawville_events if "time_lag_days" in e]
    if lags:
        timeline_data["statistics"]["average_lag"] = round(sum(lags) / len(lags), 1)

    # 5. Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(timeline_data, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"Timeline Complete!")
    print(f"  Average news lag: {timeline_data['statistics']['average_lag']} days")
    print(f"  Saved to: {output_file}")

if __name__ == "__main__":
    main()