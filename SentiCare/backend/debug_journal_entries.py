"""
Debug script to examine journal_entries collection structure and timestamps
"""
import asyncio
from datetime import datetime
from database import Database
import json

async def examine_journal_entries():
    """Examine all fields and timestamps in journal_entries collection"""
    
    # Get journal entries collection
    journals = Database.get_collection("journal_entries")
    
    print("=" * 80)
    print("EXAMINING JOURNAL_ENTRIES COLLECTION")
    print("=" * 80)
    
    # Count total entries
    total_count = await journals.count_documents({})
    print(f"\n📊 Total journal entries in database: {total_count}")
    
    if total_count == 0:
        print("\n⚠️  No journal entries found in database!")
        return
    
    # Get all entries
    cursor = journals.find({}).sort("timestamp", -1)  # Sort by timestamp descending
    entries = await cursor.to_list(length=None)
    
    print(f"\n🔍 Analyzing {len(entries)} journal entries...\n")
    
    # Analyze structure of first entry
    if entries:
        print("-" * 80)
        print("SAMPLE ENTRY STRUCTURE (First Entry):")
        print("-" * 80)
        first_entry = entries[0]
        
        # Print all fields
        for key, value in first_entry.items():
            if isinstance(value, datetime):
                print(f"  {key}: {value} (datetime) - ISO: {value.isoformat()}")
            elif isinstance(value, dict):
                print(f"  {key}: {json.dumps(value, indent=4, default=str)}")
            else:
                print(f"  {key}: {value} ({type(value).__name__})")
        
    # Group entries by date field
    print("\n" + "=" * 80)
    print("ENTRIES GROUPED BY DATE FIELD:")
    print("=" * 80)
    
    entries_by_date = {}
    entries_by_timestamp_date = {}
    
    for entry in entries:
        # Group by 'date' field
        entry_date = entry.get('date')
        if entry_date:
            date_key = entry_date.date() if isinstance(entry_date, datetime) else entry_date
            date_str = str(date_key)
            if date_str not in entries_by_date:
                entries_by_date[date_str] = []
            entries_by_date[date_str].append(entry)
        
        # Group by timestamp's date component
        timestamp = entry.get('timestamp')
        if timestamp:
            ts_date = timestamp.date() if isinstance(timestamp, datetime) else timestamp
            ts_str = str(ts_date)
            if ts_str not in entries_by_timestamp_date:
                entries_by_timestamp_date[ts_str] = []
            entries_by_timestamp_date[ts_str].append(entry)
    
    # Print grouped by 'date' field
    print("\n📅 GROUPED BY 'date' FIELD:")
    for date_str in sorted(entries_by_date.keys()):
        count = len(entries_by_date[date_str])
        print(f"  {date_str}: {count} entries")
        for entry in entries_by_date[date_str][:3]:  # Show first 3
            user_id = entry.get('user_id', 'N/A')
            journal_type = entry.get('journal_type', 'N/A')
            timestamp = entry.get('timestamp', 'N/A')
            print(f"    - Type: {journal_type}, User: {user_id[:8]}..., Timestamp: {timestamp}")
        if len(entries_by_date[date_str]) > 3:
            print(f"    ... and {len(entries_by_date[date_str]) - 3} more")
    
    # Print grouped by timestamp date
    print("\n⏰ GROUPED BY 'timestamp' DATE COMPONENT:")
    for date_str in sorted(entries_by_timestamp_date.keys()):
        count = len(entries_by_timestamp_date[date_str])
        print(f"  {date_str}: {count} entries")
    
    # Check for date/timestamp mismatches
    print("\n" + "=" * 80)
    print("CHECKING FOR DATE/TIMESTAMP MISMATCHES:")
    print("=" * 80)
    
    mismatches = []
    for entry in entries:
        date_field = entry.get('date')
        timestamp_field = entry.get('timestamp')
        
        if date_field and timestamp_field:
            date_part = date_field.date() if isinstance(date_field, datetime) else date_field
            timestamp_part = timestamp_field.date() if isinstance(timestamp_field, datetime) else timestamp_field
            
            if date_part != timestamp_part:
                mismatches.append({
                    'id': str(entry.get('_id')),
                    'date': date_part,
                    'timestamp': timestamp_part,
                    'type': entry.get('journal_type')
                })
    
    if mismatches:
        print(f"\n⚠️  Found {len(mismatches)} entries with date/timestamp mismatches:")
        for mismatch in mismatches[:5]:  # Show first 5
            print(f"  ID: {mismatch['id']}")
            print(f"    date field: {mismatch['date']}")
            print(f"    timestamp date: {mismatch['timestamp']}")
            print(f"    type: {mismatch['type']}")
    else:
        print("\n✅ All entries have matching date and timestamp date components")
    
    # Analyze emotion and score data
    print("\n" + "=" * 80)
    print("EMOTION AND SCORE ANALYSIS:")
    print("=" * 80)
    
    emotions = {}
    mental_health_scores = []
    
    for entry in entries:
        emotion_analysis = entry.get('emotion_analysis', {})
        dominant_emotion = emotion_analysis.get('dominant_emotion', 'unknown')
        emotions[dominant_emotion] = emotions.get(dominant_emotion, 0) + 1
        
        llm_assessment = entry.get('llm_assessment', {})
        mh_score = llm_assessment.get('mental_health_score') or llm_assessment.get('overall_mental_health_score')
        if mh_score:
            mental_health_scores.append(mh_score)
    
    print("\n🎭 Emotion Distribution:")
    for emotion, count in sorted(emotions.items(), key=lambda x: x[1], reverse=True):
        print(f"  {emotion}: {count} entries")
    
    if mental_health_scores:
        avg_score = sum(mental_health_scores) / len(mental_health_scores)
        print(f"\n📊 Mental Health Scores:")
        print(f"  Average: {avg_score:.1f}")
        print(f"  Min: {min(mental_health_scores)}")
        print(f"  Max: {max(mental_health_scores)}")
    
    # Analyze by user
    print("\n" + "=" * 80)
    print("ENTRIES BY USER:")
    print("=" * 80)
    
    users = {}
    for entry in entries:
        user_id = entry.get('user_id', 'unknown')
        if user_id not in users:
            users[user_id] = {
                'total': 0,
                'text': 0,
                'video': 0,
                'dates': set()
            }
        users[user_id]['total'] += 1
        
        journal_type = entry.get('journal_type', 'unknown')
        if journal_type == 'text':
            users[user_id]['text'] += 1
        elif journal_type == 'video':
            users[user_id]['video'] += 1
        
        date_field = entry.get('date')
        if date_field:
            date_key = date_field.date() if isinstance(date_field, datetime) else date_field
            users[user_id]['dates'].add(str(date_key))
    
    for user_id, stats in users.items():
        print(f"\n👤 User: {user_id[:12]}...")
        print(f"  Total entries: {stats['total']}")
        print(f"  Text entries: {stats['text']}")
        print(f"  Video entries: {stats['video']}")
        print(f"  Unique dates: {len(stats['dates'])}")
        print(f"  Dates: {', '.join(sorted(stats['dates']))}")
    
    print("\n" + "=" * 80)
    print("HEATMAP IMPLICATIONS:")
    print("=" * 80)
    
    print("\n💡 Key Findings:")
    print(f"  - Total entries: {total_count}")
    print(f"  - Unique dates (date field): {len(entries_by_date)}")
    print(f"  - Unique dates (timestamp): {len(entries_by_timestamp_date)}")
    print(f"  - Date/timestamp mismatches: {len(mismatches)}")
    print(f"\n  Dates with entries: {', '.join(sorted(entries_by_date.keys()))}")
    
    if len(entries_by_date) == 1:
        print("\n⚠️  WARNING: Only 1 unique date found!")
        print("  This explains why the heatmap shows only one day with activity.")
        print("  To populate the heatmap, create journal entries on different days.")

async def main():
    try:
        await Database.connect_db()
        await examine_journal_entries()
    finally:
        await Database.close_db()

if __name__ == "__main__":
    asyncio.run(main())
