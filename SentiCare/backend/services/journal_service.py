from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from database import Database
from models.journal import (
    JournalEntryInDB,
    DailySummary,
    UserStreak,
    HeatmapDataPoint,
    HeatmapResponse,
    MonthlyStats
)
from bson import ObjectId

class JournalService:
    """Service for managing journal entries and analytics"""
    
    @staticmethod
    async def get_journals_collection():
        return Database.get_collection("journal_entries")
    
    @staticmethod
    async def get_daily_summaries_collection():
        return Database.get_collection("daily_summaries")
    
    @staticmethod
    async def get_streaks_collection():
        return Database.get_collection("user_streaks")
    
    @staticmethod
    async def create_journal_entry(
        user_id: str,
        journal_data: Dict,
        analysis_result: Dict
    ) -> str:
        """Create a new journal entry"""
        journals = await JournalService.get_journals_collection()
        
        # Base entry structure
        entry = {
            "user_id": user_id,
            "journal_type": journal_data["journal_type"],
            "date": datetime.combine(date.today(), datetime.min.time()),
            "timestamp": datetime.utcnow(),
            "privacy_mode": journal_data["privacy_mode"],
            "is_deleted": False
        }
        
        # Handle different journal types
        if journal_data["journal_type"] == "text":
            # Text journal structure
            entry.update({
                "content": journal_data.get("content", ""),
                "text_length": len(journal_data.get("content", "")),
                "emotion_analysis": analysis_result["emotion_analysis"],
                "depression_analysis": analysis_result["depression_analysis"],
                "llm_assessment": analysis_result["llm_assessment"],
                "analysis_id": analysis_result.get("journal_id")
            })
        else:  # video journal
            # Extract from video analysis result structure
            summary = analysis_result.get("summary", {})
            llm_assessment = analysis_result.get("llm_final_assessment", {})
            
            # Build emotion analysis from video/audio/text
            emotion_analysis = {
                "video_emotion": summary.get("video_emotion", "neutral"),
                "audio_emotion": summary.get("audio_emotion", "neutral"),
                "text_emotion": summary.get("text_emotion", "neutral"),
                "dominant_emotion": summary.get("text_emotion", "neutral")  # Use text as primary
            }
            
            # Build depression analysis from summary
            depression_analysis = {
                "depression_level": summary.get("depression_level", "unknown"),
                "confidence": summary.get("confidence", 0.0),
                "severity": 5 if summary.get("depression_level") == "moderate" else 0
            }
            
            entry.update({
                "video_path": journal_data.get("video_path"),
                "video_analysis": analysis_result.get("video_emotion"),
                "audio_analysis": analysis_result.get("audio_emotion"),
                "transcript": analysis_result.get("transcript"),
                "emotion_analysis": emotion_analysis,
                "depression_analysis": depression_analysis,
                "llm_assessment": llm_assessment,
                "analysis_id": analysis_result.get("video_path")
            })
        
        result = await journals.insert_one(entry)
        
        # Update daily summary and streak
        await JournalService.update_daily_summary(user_id, date.today())
        await JournalService.update_user_streak(user_id, date.today())
        
        return str(result.inserted_id)
    
    @staticmethod
    async def update_daily_summary(user_id: str, entry_date: date):
        """Update or create daily summary for a date"""
        journals = await JournalService.get_journals_collection()
        summaries = await JournalService.get_daily_summaries_collection()
        
        # Convert date to datetime range for querying
        start_datetime = datetime.combine(entry_date, datetime.min.time())
        end_datetime = datetime.combine(entry_date, datetime.max.time())
        
        # Get all entries for this day
        entries = await journals.find({
            "user_id": user_id,
            "date": {"$gte": start_datetime, "$lte": end_datetime},
            "is_deleted": False
        }).to_list(length=100)
        
        if not entries:
            return
        
        # Calculate aggregated stats
        total_entries = len(entries)
        text_entries = sum(1 for e in entries if e["journal_type"] == "text")
        video_entries = sum(1 for e in entries if e["journal_type"] == "video")
        
        # Extract scores - handle both field names
        mental_health_scores = []
        depression_scores = []
        anxiety_scores = []
        stress_scores = []
        
        for e in entries:
            llm = e.get("llm_assessment", {})
            # Handle both "mental_health_score" (text) and "overall_mental_health_score" (video)
            mh_score = llm.get("mental_health_score") or llm.get("overall_mental_health_score", 50)
            mental_health_scores.append(mh_score)
            depression_scores.append(llm.get("depression_score", 0))
            anxiety_scores.append(llm.get("anxiety_score", 0))
            stress_scores.append(llm.get("stress_score", 0))
        
        # Aggregate emotions
        emotion_counts = {}
        for entry in entries:
            emotion = entry["emotion_analysis"]["dominant_emotion"]
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        emotion_distribution = {
            k: v / total_entries for k, v in emotion_counts.items()
        }
        
        # Create summary
        summary = {
            "user_id": user_id,
            "date": start_datetime,
            "total_entries": total_entries,
            "text_entries": text_entries,
            "video_entries": video_entries,
            "avg_mental_health_score": sum(mental_health_scores) / total_entries,
            "avg_depression_score": sum(depression_scores) / total_entries,
            "avg_anxiety_score": sum(anxiety_scores) / total_entries,
            "avg_stress_score": sum(stress_scores) / total_entries,
            "dominant_emotion": dominant_emotion,
            "emotion_distribution": emotion_distribution,
            "has_entry": True,
            "first_entry_time": min(e["timestamp"] for e in entries),
            "last_entry_time": max(e["timestamp"] for e in entries)
        }
        
        # Upsert summary
        await summaries.update_one(
            {"user_id": user_id, "date": start_datetime},
            {"$set": summary},
            upsert=True
        )
    
    @staticmethod
    async def update_user_streak(user_id: str, entry_date: date):
        """Update user's streak data"""
        streaks = await JournalService.get_streaks_collection()
        
        streak_doc = await streaks.find_one({"user_id": user_id})
        
        # Convert date to datetime for MongoDB storage
        entry_datetime = datetime.combine(entry_date, datetime.min.time())
        
        if not streak_doc:
            # Create new streak
            streak_doc = {
                "user_id": user_id,
                "current_streak": 1,
                "longest_streak": 1,
                "total_entries": 1,
                "last_entry_date": entry_datetime,
                "streak_start_date": entry_datetime,
                "milestones_achieved": [],
                "updated_at": datetime.utcnow()
            }
            await streaks.insert_one(streak_doc)
            return
        
        last_date = streak_doc.get("last_entry_date")
        if last_date:
            last_date = last_date.date() if isinstance(last_date, datetime) else last_date
        
        if last_date == entry_date:
            # Already logged today, just increment total
            await streaks.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"total_entries": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return
        
        # Check if streak continues
        yesterday = entry_date - timedelta(days=1)
        
        if last_date == yesterday:
            # Streak continues
            new_streak = streak_doc["current_streak"] + 1
            longest = max(new_streak, streak_doc["longest_streak"])
            
            # Check milestones
            milestones = [7, 30, 60, 100, 180, 365]
            achieved = streak_doc.get("milestones_achieved", [])
            for milestone in milestones:
                if new_streak >= milestone and milestone not in achieved:
                    achieved.append(milestone)
            
            await streaks.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "current_streak": new_streak,
                        "longest_streak": longest,
                        "last_entry_date": entry_datetime,
                        "milestones_achieved": achieved,
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {"total_entries": 1}
                }
            )
        else:
            # Streak broken, start new
            await streaks.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "current_streak": 1,
                        "last_entry_date": entry_datetime,
                        "streak_start_date": entry_datetime,
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {"total_entries": 1}
                }
            )
    
    @staticmethod
    async def get_heatmap_data(
        user_id: str,
        year: int
    ) -> HeatmapResponse:
        """Get heatmap data for a year (like GitHub contributions) - reading directly from journal_entries"""
        journals = await JournalService.get_journals_collection()
        streaks = await JournalService.get_streaks_collection()
        
        # Get all journal entries for the year directly from journal_entries collection
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        
        entries_cursor = journals.find({
            "user_id": user_id,
            "date": {"$gte": start_date, "$lte": end_date},
            "is_deleted": False
        })
        
        entries_list = await entries_cursor.to_list(length=1000)
        
        # Group entries by date and calculate daily stats
        daily_stats = {}
        for entry in entries_list:
            entry_date = entry["date"].date() if isinstance(entry["date"], datetime) else entry["date"]
            date_str = str(entry_date)
            
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    "count": 0,
                    "mental_health_scores": [],
                    "emotions": []
                }
            
            daily_stats[date_str]["count"] += 1
            
            # Extract mental health score
            llm = entry.get("llm_assessment", {})
            mh_score = llm.get("mental_health_score") or llm.get("overall_mental_health_score", 50)
            daily_stats[date_str]["mental_health_scores"].append(mh_score)
            
            # Extract emotion
            emotion = entry.get("emotion_analysis", {}).get("dominant_emotion", "neutral")
            daily_stats[date_str]["emotions"].append(emotion)
        
        # Create heatmap data for every day of the year
        heatmap_data = []
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end:
            date_str = str(current_date)
            
            if date_str in daily_stats:
                stats = daily_stats[date_str]
                entry_count = stats["count"]
                
                # Calculate intensity based on number of entries (0-4 scale like GitHub)
                if entry_count >= 5:
                    intensity = 4  # 5+ entries = darkest green
                elif entry_count >= 4:
                    intensity = 3  # 4 entries = dark green
                elif entry_count >= 3:
                    intensity = 2  # 3 entries = medium green
                elif entry_count >= 2:
                    intensity = 1  # 2 entries = light green
                else:
                    intensity = 1  # 1 entry = light green
                
                # Calculate average mental health score
                avg_score = sum(stats["mental_health_scores"]) / len(stats["mental_health_scores"])
                
                # Find most common emotion
                emotion_counts = {}
                for emotion in stats["emotions"]:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                dominant_emotion = max(emotion_counts, key=emotion_counts.get)
                
                tooltip = f"{entry_count} entries • Score: {avg_score:.0f} • {dominant_emotion}"
                
                heatmap_data.append(HeatmapDataPoint(
                    date=current_date,
                    value=intensity,
                    mental_health_score=int(avg_score),
                    total_entries=entry_count,
                    tooltip=tooltip
                ))
            else:
                heatmap_data.append(HeatmapDataPoint(
                    date=current_date,
                    value=0,
                    total_entries=0,
                    tooltip="No entries"
                ))
            
            current_date += timedelta(days=1)
        
        # Get streak info
        streak_doc = await streaks.find_one({"user_id": user_id})
        current_streak = streak_doc["current_streak"] if streak_doc else 0
        longest_streak = streak_doc["longest_streak"] if streak_doc else 0
        total_entries = len(entries_list)
        
        return HeatmapResponse(
            user_id=user_id,
            year=year,
            data=heatmap_data,
            current_streak=current_streak,
            longest_streak=longest_streak,
            total_entries=total_entries
        )
    
    @staticmethod
    async def get_monthly_stats(
        user_id: str,
        year: int,
        month: int
    ) -> MonthlyStats:
        """Get detailed stats for a month"""
        summaries = await JournalService.get_daily_summaries_collection()
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        summaries_cursor = summaries.find({
            "user_id": user_id,
            "date": {"$gte": start_date, "$lte": end_date}
        })
        
        summaries_list = await summaries_cursor.to_list(length=31)
        
        if not summaries_list:
            return None
        
        # Calculate stats
        total_entries = sum(s["total_entries"] for s in summaries_list)
        text_entries = sum(s["text_entries"] for s in summaries_list)
        video_entries = sum(s["video_entries"] for s in summaries_list)
        
        avg_mental_health = sum(s["avg_mental_health_score"] for s in summaries_list) / len(summaries_list)
        avg_depression = sum(s["avg_depression_score"] for s in summaries_list) / len(summaries_list)
        avg_anxiety = sum(s["avg_anxiety_score"] for s in summaries_list) / len(summaries_list)
        avg_stress = sum(s["avg_stress_score"] for s in summaries_list) / len(summaries_list)
        
        # Emotion distribution
        emotion_counts = {}
        for summary in summaries_list:
            emotion = summary["dominant_emotion"]
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Find best and challenging days
        best_day = max(summaries_list, key=lambda x: x["avg_mental_health_score"])
        challenging_day = min(summaries_list, key=lambda x: x["avg_mental_health_score"])
        
        return MonthlyStats(
            user_id=user_id,
            year=year,
            month=month,
            total_entries=total_entries,
            text_entries=text_entries,
            video_entries=video_entries,
            avg_mental_health_score=avg_mental_health,
            avg_depression_score=avg_depression,
            avg_anxiety_score=avg_anxiety,
            avg_stress_score=avg_stress,
            emotion_distribution=emotion_counts,
            risk_level_distribution={},  # Can be calculated from journals
            best_day=best_day["date"],
            challenging_day=challenging_day["date"],
            streak_days=len(summaries_list)
        )
