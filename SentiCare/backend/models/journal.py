from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, date
from enum import Enum

class JournalType(str, Enum):
    TEXT = "text"
    VIDEO = "video"

class PrivacyMode(str, Enum):
    FULL_PRIVACY = "full_privacy"
    ANONYMIZED = "anonymized"

# Emotion Analysis Sub-model
class EmotionAnalysis(BaseModel):
    emotions: List[str]
    emotion_scores: Dict[str, float]
    dominant_emotion: str

# Depression Analysis Sub-model
class DepressionAnalysis(BaseModel):
    depression_level: str
    confidence: float
    severity: int

# LLM Assessment Sub-model
class LLMAssessment(BaseModel):
    mental_health_score: int
    depression_score: int
    anxiety_score: int
    stress_score: int
    risk_level: str
    confidence: float
    key_indicators: List[str]
    recommendations: List[str]

# Video Analysis Sub-models (for video journals)
class VideoEmotionInterval(BaseModel):
    start_time: float
    end_time: float
    dominant_emotion: str
    confidence: float

class VideoAnalysis(BaseModel):
    video_path: str
    intervals: List[VideoEmotionInterval]
    dominant_emotion: str
    duration: float

class AudioAnalysis(BaseModel):
    emotion: str
    confidence: float
    all_emotions: Dict[str, float]

class Transcript(BaseModel):
    text: str
    duration: float
    confidence: float
    word_count: int

# Main Journal Entry Model
class JournalEntryCreate(BaseModel):
    user_id: str
    journal_type: JournalType
    privacy_mode: PrivacyMode
    content: Optional[str] = None  # For text journals
    video_path: Optional[str] = None  # For video journals

class JournalEntryInDB(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    journal_type: JournalType
    date: date  # Journal date (for daily tracking)
    timestamp: datetime  # Exact creation time
    privacy_mode: PrivacyMode
    
    # Text journal fields
    content: Optional[str] = None
    text_length: Optional[int] = None
    
    # Video journal fields
    video_path: Optional[str] = None
    video_analysis: Optional[VideoAnalysis] = None
    audio_analysis: Optional[AudioAnalysis] = None
    transcript: Optional[Transcript] = None
    
    # Common analysis fields
    emotion_analysis: EmotionAnalysis
    depression_analysis: DepressionAnalysis
    llm_assessment: LLMAssessment
    
    # Metadata
    analysis_id: str  # Link to full analysis JSON
    is_deleted: bool = False
    
    class Config:
        populate_by_name = True

class JournalEntryResponse(BaseModel):
    id: str
    user_id: str
    journal_type: JournalType
    date: date
    timestamp: datetime
    
    # Scores for quick access
    mental_health_score: int
    depression_score: int
    anxiety_score: int
    stress_score: int
    risk_level: str
    dominant_emotion: str
    
    # Content preview
    content_preview: Optional[str] = None  # First 100 chars
    video_thumbnail: Optional[str] = None
    
    class Config:
        populate_by_name = True

# Daily Summary Model (for heatmap/streak tracking)
class DailySummary(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    date: date
    
    # Daily stats
    total_entries: int
    text_entries: int
    video_entries: int
    
    # Aggregated scores (average of all entries that day)
    avg_mental_health_score: float
    avg_depression_score: float
    avg_anxiety_score: float
    avg_stress_score: float
    
    # Dominant emotion of the day
    dominant_emotion: str
    emotion_distribution: Dict[str, float]
    
    # Streak tracking
    has_entry: bool = True
    
    # Timestamps
    first_entry_time: datetime
    last_entry_time: datetime
    
    class Config:
        populate_by_name = True

# Streak Model (for gamification)
class UserStreak(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    current_streak: int = 0
    longest_streak: int = 0
    total_entries: int = 0
    last_entry_date: Optional[date] = None
    streak_start_date: Optional[date] = None
    
    # Milestones
    milestones_achieved: List[int] = []  # [7, 30, 100, etc.]
    
    # Last updated
    updated_at: datetime
    
    class Config:
        populate_by_name = True

# Heatmap Data Model (for visualization)
class HeatmapDataPoint(BaseModel):
    date: date
    value: int  # 0 = no entry, 1-4 = intensity based on scores
    mental_health_score: Optional[int] = None
    total_entries: int
    tooltip: str  # Summary for hover

class HeatmapResponse(BaseModel):
    user_id: str
    year: int
    data: List[HeatmapDataPoint]
    current_streak: int
    longest_streak: int
    total_entries: int

# Monthly Stats Model
class MonthlyStats(BaseModel):
    user_id: str
    year: int
    month: int
    
    total_entries: int
    text_entries: int
    video_entries: int
    
    avg_mental_health_score: float
    avg_depression_score: float
    avg_anxiety_score: float
    avg_stress_score: float
    
    emotion_distribution: Dict[str, int]  # Count of each emotion
    risk_level_distribution: Dict[str, int]  # Count of each risk level
    
    best_day: Optional[date] = None  # Highest mental health score
    challenging_day: Optional[date] = None  # Lowest mental health score
    
    streak_days: int
