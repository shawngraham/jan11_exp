#!/usr/bin/env python3
"""
Fix timeline.json to match the structure expected by timeline.js
"""
import json
import sys

def main():
    timeline_path = 'data/processed/timeline.json'

    # Load the timeline file
    with open(timeline_path, 'r') as f:
        data = json.load(f)

    # Rename top-level keys
    if 'london_canonical_events' in data:
        data['london_events'] = data.pop('london_canonical_events')

    if 'canadian_reports' in data:
        data['shawville_events'] = data.pop('canadian_reports')

    # Add descriptions to London events
    london_descriptions = {
        'lon_01': "First canonical victim found in Buck's Row",
        'lon_02': "Second canonical victim found in Hanbury Street",
        'lon_03': "Famous letter signed 'Jack the Ripper' received",
        'lon_04': "Two murders in one night: Elizabeth Stride and Catherine Eddowes",
        'lon_05': "Postcard received claiming credit for the 'double event'",
        'lon_06': "Letter with preserved kidney sent to George Lusk",
        'lon_07': "Final canonical victim, found in Miller's Court"
    }

    for event in data.get('london_events', []):
        event_id = event.get('id')
        if event_id in london_descriptions and 'description' not in event:
            event['description'] = london_descriptions[event_id]

    # Update Shawville events structure
    for event in data.get('shawville_events', []):
        # Add title field (copy from headline)
        if 'headline' in event:
            event['title'] = event['headline']

        # Add time_lag_days field (copy from days_since_event)
        if 'days_since_event' in event:
            event['time_lag_days'] = event['days_since_event']

        # Add description field (combine snippet truncation and historical_context)
        snippet = event.get('snippet', '')
        # Truncate snippet to first 100 chars
        snippet_preview = snippet[:100] + '...' if len(snippet) > 100 else snippet
        context = event.get('historical_context', '')
        event['description'] = f"{snippet_preview} {context}".strip()

        # Add related_london_event for timeline connections
        # Map correlated events to london event IDs
        correlated = event.get('correlated_event', '')
        event_map = {
            'Mary Ann Nichols': 'lon_01',
            'Annie Chapman': 'lon_02',
            'Double Event (Stride/Eddowes)': 'lon_04',
            'Mary Jane Kelly': 'lon_07'
        }
        event['related_london_event'] = event_map.get(correlated, 'lon_07')

    # Save the updated file
    with open(timeline_path, 'w') as f:
        json.dump(data, f, indent=2)

    print("✓ Timeline file updated successfully!")
    print(f"  - London events: {len(data.get('london_events', []))}")
    print(f"  - Shawville events: {len(data.get('shawville_events', []))}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
