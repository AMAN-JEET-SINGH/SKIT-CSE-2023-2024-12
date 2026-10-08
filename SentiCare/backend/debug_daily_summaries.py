"""
Debug script to examine daily_summaries collection
"""
import asyncio
from datetime import datetime
from database import Database
import json

async def examine_daily_summaries():
    """Examine daily_summaries collection"""
    
    summaries = Database.get_collection("daily_summaries")
    
    print("=" * 80)
    print("EXAMINING DAILY_SUMMARIES COLLECTION")
    print("=" * 80)
    
    # Count total summaries
    total_count = await summaries.count_documents({})
    print(f"\nTotal daily summaries in database: {total_count}")
    
    if total_count == 0:
        print("\nNo daily summaries found!")
        print("This is why the heatmap is not showing data properly!")
        print("\nThe issue: daily_summaries are not being created when journals are added.")
        return
    
    # Get all summaries
    cursor = summaries.find({}).sort("date", -1)
    summaries_list = await cursor.to_list(length=None)
    
    print(f"\n🔍 Found {len(summaries_list)} daily summaries:\n")
    
    for summary in summaries_list:
        date = summary.get('date')
        user_id = summary.get('user_id', 'N/A')
        total_entries = summary.get('total_entries', 0)
        text_entries = summary.get('text_entries', 0)
        video_entries = summary.get('video_entries', 0)
        avg_mh_score = summary.get('avg_mental_health_score', 0)
        dominant_emotion = summary.get('dominant_emotion', 'N/A')
        
        print(f"📅 Date: {date}")
        print(f"   User: {user_id[:12]}...")
        print(f"   Total entries: {total_entries} (text: {text_entries}, video: {video_entries})")
        print(f"   Avg MH Score: {avg_mh_score:.1f}")
        print(f"   Dominant Emotion: {dominant_emotion}")
        print()

async def main():
    try:
        await Database.connect_db()
        await examine_daily_summaries()
    finally:
        await Database.close_db()

if __name__ == "__main__":
    asyncio.run(main())
