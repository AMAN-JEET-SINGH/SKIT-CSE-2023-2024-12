"""
FastAPI application for multimodal mental health analysis pipeline
Combines video emotion detection, audio analysis, transcription, and text analysis
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import uvicorn
from pathlib import Path
import json
import uuid
from datetime import datetime
import shutil
import asyncio
from enum import Enum
import sys
from multiprocessing import freeze_support
import os
import subprocess

sys.path.insert(0, str(Path(__file__).parent))

from parallel_pipeline import (
    MultimodalAnalysisPipeline,
    PrivacyMode,
    MultimodalAnalysisResult
)
from emotional_support_chatbot import EmotionalSupportChatbot
from audio.text_analysis_pii_removal import remove_pii, analyze_text_emotion as analyze_text_llm
from audio.text_classification import analyze_text_emotion as analyze_emotion_local
from audio.depression_text import analyze_text_depression
from models.user import UserCreate, UserLogin, Token, UserResponse, verify_password, get_password_hash
from database import Database, get_users_collection
from auth import create_access_token, get_current_active_user
from datetime import datetime
from bson import ObjectId
from services.journal_service import JournalService
from models.journal import JournalType
from text_chunking_analyzer import ChunkedTextAnalyzer

class PrivacyModeRequest(str, Enum):
    FULL_PRIVACY = "full_privacy"
    ANONYMIZED = "anonymized"


class UploadResponse(BaseModel):
    task_id: str
    message: str
    status: str
    video_path: str
    privacy_mode: str


class StatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str
    stage: Optional[str] = None


class AnalysisResultResponse(BaseModel):
    task_id: str
    mental_health_score: int
    depression_score: int  # NEW
    anxiety_score: int     # NEW
    stress_score: int      # NEW
    risk_level: str
    confidence: float
    video_emotion: str
    audio_emotion: str
    text_emotion: str
    depression_level: str
    key_indicators: List[str]
    recommendations: List[str]
    areas_of_concern: List[str]
    positive_indicators: List[str]


class TextJournalRequest(BaseModel):
    text: str
    privacy_mode: PrivacyModeRequest
    session_id: Optional[str] = None


class TextJournalResponse(BaseModel):
    success: bool
    journal_id: str
    mental_health_score: int
    depression_score: int  # NEW
    anxiety_score: int     # NEW
    stress_score: int      # NEW
    risk_level: str
    confidence: float
    dominant_emotion: str
    depression_level: str
    key_indicators: List[str]
    recommendations: List[str]
    analysis_summary: Dict[str, Any]


class FileManager:
    """Manages file operations for the application"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.uploads_dir = self.base_dir / "uploads"
        self.results_dir = self.base_dir / "results"
        self.status_dir = self.base_dir / "status"
    
    def setup_directories(self):
        """Create necessary directories if they don't exist"""
        self.uploads_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        self.status_dir.mkdir(exist_ok=True)
        print(f"Directories initialized:")
        print(f"  - Uploads: {self.uploads_dir}")
        print(f"  - Results: {self.results_dir}")
        print(f"  - Status: {self.status_dir}")
    
    def generate_task_id(self) -> str:
        """Generate a unique task ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"
    
    def get_upload_path(self, task_id: str, filename: str) -> Path:
        """Get the path for uploaded video"""
        ext = Path(filename).suffix
        return self.uploads_dir / f"{task_id}{ext}"
    
    def get_result_path(self, task_id: str) -> Path:
        """Get the path for result JSON"""
        return self.results_dir / f"{task_id}_result.json"
    
    def get_status_path(self, task_id: str) -> Path:
        """Get the path for status JSON"""
        return self.status_dir / f"{task_id}_status.json"
    
    def save_result(self, task_id: str, result_data: dict):
        """Save analysis result to JSON file"""
        result_path = self.get_result_path(task_id)
        with open(result_path, 'w') as f:
            json.dump(result_data, f, indent=2)
        print(f"Result saved: {result_path}")
    
    def load_result(self, task_id: str) -> dict:
        """Load analysis result from JSON file"""
        result_path = self.get_result_path(task_id)
        if not result_path.exists():
            raise FileNotFoundError(f"Result not found for task {task_id}")
        with open(result_path, 'r') as f:
            return json.load(f)
    
    def save_status(self, task_id: str, status_data: dict):
        """Save task status to JSON file"""
        status_path = self.get_status_path(task_id)
        status_data['last_updated'] = datetime.utcnow().isoformat()
        with open(status_path, 'w') as f:
            json.dump(status_data, f, indent=2)
    
    def load_status(self, task_id: str) -> dict:
        """Load task status from JSON file"""
        status_path = self.get_status_path(task_id)
        if not status_path.exists():
            raise FileNotFoundError(f"Status not found for task {task_id}")
        with open(status_path, 'r') as f:
            return json.load(f)
    
    def get_video_path(self, task_id: str) -> Path:
        """Find the video file for a given task_id"""
        for file in self.uploads_dir.glob(f"{task_id}.*"):
            return file
        raise FileNotFoundError(f"Video not found for task {task_id}")
    
    def cleanup_task(self, task_id: str, keep_video: bool = True):
        """Delete files associated with a task"""
        if not keep_video:
            for file in self.uploads_dir.glob(f"{task_id}.*"):
                file.unlink()
                print(f"Deleted upload: {file}")
        
        result_path = self.get_result_path(task_id)
        if result_path.exists():
            result_path.unlink()
        
        status_path = self.get_status_path(task_id)
        if status_path.exists():
            status_path.unlink()
        
        print(f"Task {task_id} cleaned up (video kept: {keep_video})")


class MultimodalAnalysisService:
    """Service for managing multimodal analysis pipeline"""
    
    def __init__(self):
        self.pipeline = None
        self._pipeline_loaded = False
    
    def _load_pipeline(self):
        """Lazy load the multimodal analysis pipeline"""
        if not self._pipeline_loaded:
            print("Loading multimodal analysis pipeline...")
            self.pipeline = MultimodalAnalysisPipeline()
            self._pipeline_loaded = True
            print("Pipeline loaded successfully")
    
    async def analyze_video(
        self,
        video_path: Path,
        task_id: str,
        file_manager: FileManager,
        privacy_mode: PrivacyMode,
        interval_seconds: int = 5,
        frame_skip: int = 2
    ) -> dict:
        """
        Perform complete multimodal analysis on video
        
        Args:
            video_path: Path to video file
            task_id: Unique task identifier
            file_manager: File management instance
            privacy_mode: Privacy mode for text analysis
            interval_seconds: Seconds per analysis interval
            frame_skip: Process every Nth frame
        """
        try:
            self._load_pipeline()
            
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'processing',
                'progress': 10.0,
                'stage': 'initialization',
                'message': 'Starting multimodal analysis'
            })
            
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'processing',
                'progress': 30.0,
                'stage': 'video_analysis',
                'message': 'Analyzing video emotions'
            })
            
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'processing',
                'progress': 50.0,
                'stage': 'audio_analysis',
                'message': 'Processing audio and transcription'
            })
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_analysis_sync,
                video_path,
                privacy_mode,
                interval_seconds,
                frame_skip
            )
            
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'processing',
                'progress': 80.0,
                'stage': 'llm_assessment',
                'message': 'Generating final assessment'
            })
            
            result_dict = self._result_to_dict(result)
            
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'completed',
                'progress': 100.0,
                'stage': 'completed',
                'message': 'Multimodal analysis completed'
            })
            
            return result_dict
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'failed',
                'progress': 0.0,
                'stage': 'error',
                'message': f'Analysis failed: {str(e)}'
            })
            raise
    
    def _run_analysis_sync(
        self,
        video_path: Path,
        privacy_mode: PrivacyMode,
        interval_seconds: int,
        frame_skip: int
    ) -> MultimodalAnalysisResult:
        """Synchronous wrapper for pipeline analysis"""
        return self.pipeline.analyze_video(
            video_path=str(video_path),
            privacy_mode=privacy_mode,
            interval_seconds=interval_seconds,
            frame_skip=frame_skip,
            cleanup=True
        )
    
    def _result_to_dict(self, result: MultimodalAnalysisResult) -> dict:
        """Convert MultimodalAnalysisResult to dictionary"""
        from dataclasses import asdict
        return asdict(result)


class VideoService:
    """Service for managing video processing workflow"""
    
    def __init__(self, file_manager: FileManager, analysis_service: MultimodalAnalysisService):
        self.file_manager = file_manager
        self.analysis_service = analysis_service
    
    async def process_upload(
        self,
        file: UploadFile,
        privacy_mode: PrivacyMode,
        interval_seconds: int,
        frame_skip: int,
        background_tasks: BackgroundTasks
    ) -> tuple[str, str, str]:
        """Handle video upload and initiate analysis"""
        task_id = self.file_manager.generate_task_id()
        upload_path = self.file_manager.get_upload_path(task_id, file.filename)
        
        try:
            with open(upload_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            print(f"Video uploaded: {upload_path}")
        finally:
            await file.close()
        
        self.file_manager.save_status(task_id, {
            'task_id': task_id,
            'status': 'queued',
            'progress': 0.0,
            'stage': 'queued',
            'message': 'Video uploaded. Analysis queued.'
        })
        
        background_tasks.add_task(
            self._analyze_and_save,
            task_id=task_id,
            video_path=upload_path,
            privacy_mode=privacy_mode,
            interval_seconds=interval_seconds,
            frame_skip=frame_skip
        )
        
        return task_id, str(upload_path), privacy_mode.value
    
    async def _analyze_and_save(
        self,
        task_id: str,
        video_path: Path,
        privacy_mode: PrivacyMode,
        interval_seconds: int,
        frame_skip: int
    ):
        """Background task: Analyze video and save results"""
        try:
            print(f"Starting multimodal analysis for task: {task_id}")
            
            results = await self.analysis_service.analyze_video(
                video_path=video_path,
                task_id=task_id,
                file_manager=self.file_manager,
                privacy_mode=privacy_mode,
                interval_seconds=interval_seconds,
                frame_skip=frame_skip
            )
            
            self.file_manager.save_result(task_id, results)
            
            print(f"Multimodal analysis completed for task: {task_id}")
            print(f"Video kept at: {video_path}")
            
        except Exception as e:
            print(f"Analysis failed for task {task_id}: {str(e)}")
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the current status of an analysis task"""
        try:
            status = self.file_manager.load_status(task_id)
            return status
        except FileNotFoundError:
            return {
                'task_id': task_id,
                'status': 'not_found',
                'progress': 0.0,
                'stage': 'not_found',
                'message': 'Task not found'
            }
    
    async def get_analysis_result(self, task_id: str) -> Dict[str, Any]:
        """Get the complete analysis result"""
        status = await self.get_task_status(task_id)
        
        if status['status'] != 'completed':
            raise Exception(
                f"Analysis not ready. Current status: {status['status']}"
            )
        
        return self.file_manager.load_result(task_id)
    
    async def get_video_path(self, task_id: str) -> Path:
        """Get the path to the uploaded video"""
        return self.file_manager.get_video_path(task_id)
    
    async def cleanup_task(self, task_id: str, delete_video: bool = False):
        """Cleanup task files"""
        self.file_manager.cleanup_task(task_id, keep_video=not delete_video)


# Add after other service initializations
chatbot_service = EmotionalSupportChatbot(sessions_dir="chat_sessions")

# Pydantic models for chatbot
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500
    remove_pii: bool = True  # Default to True for privacy

class ChatResponse(BaseModel):
    success: bool
    session_id: str
    assistant_message: Optional[str] = None
    error: Optional[str] = None
    session_info: Optional[Dict] = None


app = FastAPI(
    title="Multimodal Mental Health Analysis API",
    description="Comprehensive mental health analysis combining video emotion detection, audio analysis, transcription, and text analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add this for large file uploads
# Set max upload size to 500MB (adjust as needed)
os.environ["FASTAPI_MAX_BODY_SIZE"] = "524288000"

file_manager = FileManager()
analysis_service = MultimodalAnalysisService()
video_service = VideoService(file_manager, analysis_service)

# Initialize chunked analyzer globally
chunked_text_analyzer = ChunkedTextAnalyzer()


@app.on_event("startup")
async def startup_event():
    """Initialize required directories on startup"""
    file_manager.setup_directories()
    await Database.connect_db()
    print("Application started successfully")
    print("Multimodal mental health analysis pipeline ready")
    print("Privacy modes: FULL_PRIVACY and ANONYMIZED available")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await Database.close_db()
    print("Shutting down application")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multimodal Mental Health Analysis API",
        "version": "1.0.0",
        "features": [
            "Video emotion detection with frame sampling",
            "Audio emotion analysis",
            "Speech-to-text transcription",
            "Text sentiment and depression analysis",
            "Privacy-preserving modes",
            "LLM-powered comprehensive assessment"
        ],
        "endpoints": {
            "upload": "/api/upload-video",
            "status": "/api/status/{task_id}",
            "result": "/api/result/{task_id}",
            "summary": "/api/summary/{task_id}",
            "download": "/api/download-result/{task_id}",
            "video": "/api/video/{task_id}",
            "cleanup": "/api/cleanup/{task_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "pipeline_loaded": analysis_service._pipeline_loaded
    }


@app.post("/api/upload-video", response_model=AnalysisResultResponse)
async def upload_video(
    file: UploadFile = File(...),
    privacy_mode: PrivacyModeRequest = Form(PrivacyModeRequest.ANONYMIZED),
    interval_seconds: int = Form(5),
    frame_skip: int = Form(2),
    current_user = Depends(get_current_active_user)
):
    """
    Upload a video for comprehensive multimodal mental health analysis
    SYNCHRONOUS - Returns complete analysis result after processing
    """
    task_id = None
    upload_path = None
    
    print("\n--- New Upload Request Received ---")
    print(f"User ID: {current_user.id}")
    
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        print(f"Processing file: {file.filename}")
        
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate task ID and save video
        task_id = file_manager.generate_task_id()
        upload_path = file_manager.get_upload_path(task_id, file.filename)
        
        print(f"Task ID: {task_id}")
        print(f"Saving to: {upload_path}")

        # === START OF CRITICAL CHANGE (Streaming) ===
        # Replaced await file.read() with robust streaming
        try:
            with open(upload_path, "wb") as buffer:
                # file.file is the underlying SpooledTemporaryFile
                # This streams the file directly to disk, avoiding memory issues
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            print(f"Error writing file to disk: {e}")
            raise Exception(f"Could not write file to disk: {e}")
        # === END OF CRITICAL CHANGE ===
            
        print(f"Video saved to disk: {upload_path}")
        
        # Verify file was written correctly
        if not upload_path.exists():
            raise Exception("File was not saved properly (path does not exist)")
        
        actual_size = upload_path.stat().st_size
        if actual_size == 0:
            raise Exception("Uploaded file is empty (size 0 bytes)")
        
        print(f"File size on disk: {actual_size} bytes")
        
        # Give the filesystem a moment to settle
        await asyncio.sleep(0.5)
        
        # === START OF CRITICAL CHANGE (FFmpeg Guard) ===
        # Hardened check to FAIL on corrupt video
        try:
            print("Verifying video file with FFmpeg...")
            result = subprocess.run(
                [
                    'ffmpeg',
                    '-v', 'error',  # Only print errors
                    '-i', str(upload_path), # Input file
                    '-f', 'null',  # Don't create an output file
                    '-'            # Output to stdout (which is ignored)
                ],
                capture_output=True,
                text=True, # Decode stderr as text
                timeout=10
            )
            
            # If returncode is not 0, FFmpeg failed
            if result.returncode != 0:
                error_message = f"FFmpeg verification failed. File is corrupt or unreadable. Error: {result.stderr}"
                print(f"!!! {error_message}")
                # This exception will be caught by the outer try/except
                raise Exception(error_message)
            
            print("FFmpeg verification successful.")

        except Exception as e:
            # Re-raise the exception (either from timeout or from the check)
            raise e
        # === END OF CRITICAL CHANGE ===
            
    except Exception as e:
        print(f"File upload error: {e}")
        if upload_path and upload_path.exists():
            print(f"Cleaning up failed upload: {upload_path}")
            upload_path.unlink() # Clean up the corrupt/failed file
        # Return a 500 error with the specific failure reason
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    finally:
        # This is important! It closes the SpooledTemporaryFile
        await file.close()
    
    # --- Start Analysis (only if upload succeeded) ---
    
    # Save initial status
    file_manager.save_status(task_id, {
        'task_id': task_id,
        'status': 'processing',
        'progress': 0.0,
        'stage': 'starting',
        'message': 'Video uploaded. Starting analysis...'
    })
    
    # Convert privacy mode
    privacy_enum = PrivacyMode(privacy_mode.value)
    
    # SYNCHRONOUS ANALYSIS
    print(f"Starting synchronous analysis for task: {task_id}")
    
    try:
        result_dict = await analysis_service.analyze_video(
            video_path=upload_path,
            task_id=task_id,
            file_manager=file_manager,
            privacy_mode=privacy_enum,
            interval_seconds=interval_seconds,
            frame_skip=frame_skip
        )
    except Exception as e:
        # Handle errors during the analysis step
        print(f"Analysis pipeline error: {e}")
        file_manager.save_status(task_id, {'message': f'Analysis failed: {e}'})
        # Note: You might want to delete the `upload_path` file here too
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Save complete results
    file_manager.save_result(task_id, result_dict)
    
    # Save to MongoDB
    journal_data = {
        "user_id": current_user.id,
        "journal_type": "video",
        "privacy_mode": privacy_mode.value,
        "video_path": str(upload_path)
    }
    
    db_journal_id = await JournalService.create_journal_entry(
        user_id=current_user.id,
        journal_data=journal_data,
        analysis_result=result_dict
    )
    
    print(f"Video journal saved to database with ID: {db_journal_id}")
    print(f"Analysis completed for task: {task_id}")
    
    # Extract summary for response
    summary = result_dict.get('summary', {})
    llm_assessment = result_dict.get('llm_final_assessment', {})
    
    # Return complete analysis result
    return AnalysisResultResponse(
        task_id=task_id,
        mental_health_score=summary.get('mental_health_score', 0),
        depression_score=summary.get('depression_score', 0),
        anxiety_score=summary.get('anxiety_score', 0),
        stress_score=summary.get('stress_score', 0),
        risk_level=summary.get('risk_level', 'unknown'),
        confidence=summary.get('confidence', 0.0),
        video_emotion=summary.get('video_emotion', 'neutral'),
        audio_emotion=summary.get('audio_emotion', 'neutral'),
        text_emotion=summary.get('text_emotion', 'neutral'),
        depression_level=summary.get('depression_level', 'unknown'),
        key_indicators=llm_assessment.get('key_indicators', []),
        recommendations=llm_assessment.get('recommendations', []),
        areas_of_concern=llm_assessment.get('areas_of_concern', []),
        positive_indicators=llm_assessment.get('positive_indicators', [])
    )


@app.get("/api/status/{task_id}", response_model=StatusResponse)
async def get_analysis_status(task_id: str):
    """
    Get the status of a multimodal analysis task
    
    Parameters:
    - task_id: Task identifier from upload
    
    Returns:
    - status: queued|processing|completed|failed|not_found
    - progress: Progress percentage (0-100)
    - stage: Current processing stage
    - message: Status message
    """
    try:
        status_info = await video_service.get_task_status(task_id)
        return StatusResponse(**status_info)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/result/{task_id}")
async def get_analysis_result(task_id: str):
    """
    Get the complete multimodal analysis result
    
    Parameters:
    - task_id: Task identifier
    
    Returns:
    - Complete JSON with all analysis components
    """
    try:
        result = await video_service.get_analysis_result(task_id)
        return JSONResponse(content=result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Result not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/summary/{task_id}", response_model=AnalysisResultResponse)
async def get_analysis_summary(task_id: str):
    """
    Get a simplified summary of the analysis result
    
    Parameters:
    - task_id: Task identifier
    
    Returns:
    - Structured summary with key metrics and recommendations
    """
    try:
        result = await video_service.get_analysis_result(task_id)
        
        summary = result.get('summary', {})
        llm_assessment = result.get('llm_final_assessment', {})
        
        return AnalysisResultResponse(
            task_id=task_id,
            mental_health_score=summary.get('mental_health_score', 0),
            depression_score=summary.get('depression_score', 0),  # NEW
            anxiety_score=summary.get('anxiety_score', 0),        # NEW
            stress_score=summary.get('stress_score', 0),          # NEW
            risk_level=summary.get('risk_level', 'unknown'),
            confidence=summary.get('confidence', 0.0),
            video_emotion=summary.get('video_emotion', 'neutral'),
            audio_emotion=summary.get('audio_emotion', 'neutral'),
            text_emotion=summary.get('text_emotion', 'neutral'),
            depression_level=summary.get('depression_level', 'unknown'),
            key_indicators=llm_assessment.get('key_indicators', []),
            recommendations=llm_assessment.get('recommendations', []),
            areas_of_concern=llm_assessment.get('areas_of_concern', []),
            positive_indicators=llm_assessment.get('positive_indicators', [])
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Result not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-result/{task_id}")
async def download_result(task_id: str):
    """
    Download the complete analysis result as a JSON file
    
    Parameters:
    - task_id: Task identifier
    
    Returns:
    - JSON file download
    """
    try:
        result_path = file_manager.get_result_path(task_id)
        
        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Result file not found")
        
        return FileResponse(
            path=result_path,
            media_type="application/json",
            filename=f"multimodal_analysis_{task_id}.json"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/{task_id}")
async def get_video(task_id: str):
    """
    Get information about the uploaded video file
    
    Parameters:
    - task_id: Task identifier
    
    Returns:
    - Video file path and metadata
    """
    try:
        video_path = await video_service.get_video_path(task_id)
        return {
            "task_id": task_id,
            "video_path": str(video_path),
            "exists": video_path.exists(),
            "size_mb": round(video_path.stat().st_size / (1024 * 1024), 2) if video_path.exists() else 0
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cleanup/{task_id}")
async def cleanup_task(task_id: str, delete_video: bool = False):
    """
    Cleanup a task's files
    
    Parameters:
    - task_id: Task identifier
    - delete_video: Whether to delete the video file (default: False)
    
    Returns:
    - Cleanup status
    """
    try:
        await video_service.cleanup_task(task_id, delete_video=delete_video)
        return {
            "message": f"Task {task_id} cleaned up successfully",
            "video_deleted": delete_video
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Chatbot routes
@app.post("/api/chat/new-session")
async def create_chat_session():
    """Create a new chat session"""
    session_id = chatbot_service.create_session()
    return {
        "success": True,
        "session_id": session_id,
        "message": "New chat session created"
    }

@app.post("/api/chat/message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """
    Send a message to the emotional support chatbot with optional PII removal
    NO AUTHENTICATION REQUIRED - Anonymous mental health support
    """
    try:
        session_id = request.session_id
        if not session_id:
            session_id = chatbot_service.create_session()
        
        # Conditionally remove PII based on user preference
        message_to_send = request.message
        if request.remove_pii:
            print(f"[Chat] Applying PII removal")
            message_to_send = remove_pii(request.message)
        else:
            print(f"[Chat] PII removal disabled by user")
        
        # No mental health context since no user authentication
        mental_health_context = None
        
        response = chatbot_service.chat(
            session_id=session_id,
            user_message=message_to_send,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            mental_health_context=mental_health_context
        )
        
        if response['success']:
            return ChatResponse(
                success=True,
                session_id=response['session_id'],
                assistant_message=response['assistant_message'],
                session_info=response['session_info']
            )
        else:
            return ChatResponse(
                success=False,
                session_id=session_id,
                error=response['error']
            )
    
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    history = chatbot_service.get_chat_history(session_id)
    if history['success']:
        return history
    else:
        raise HTTPException(status_code=404, detail=history['error'])

@app.delete("/api/chat/clear/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session"""
    result = chatbot_service.clear_session(session_id)
    return result

@app.delete("/api/chat/session/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session"""
    result = chatbot_service.delete_session(session_id)
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=404, detail=result['error'])

@app.get("/api/chat/sessions")
async def list_chat_sessions():
    """List all active chat sessions"""
    sessions = chatbot_service.list_sessions()
    return {
        "success": True,
        "count": len(sessions),
        "sessions": sessions
    }


@app.post("/api/analyze-text-journal", response_model=TextJournalResponse)
async def analyze_text_journal(
    request: TextJournalRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Analyze text journal entry with privacy options and save to database
    NOW SENDS ALL CHUNK DISTRIBUTIONS TO LLM
    """
    try:
        journal_id = file_manager.generate_task_id()
        
        print(f"\n--- Text Journal Analysis Started ---")
        print(f"User ID: {current_user.id}")
        print(f"Journal ID: {journal_id}")
        print(f"Privacy Mode: {request.privacy_mode.value}")
        print(f"Text Length: {len(request.text)} characters")
        
        # Run chunked classifiers (handles long text automatically)
        print("Running emotion analysis (chunked if needed)...")
        emotion_result = chunked_text_analyzer.analyze_emotion_chunked(request.text)
        
        print("Running depression analysis (chunked if needed)...")
        depression_result = chunked_text_analyzer.analyze_depression_chunked(request.text)
        
        # Log chunking info
        if emotion_result.get('chunking_applied'):
            print(f"✓ Emotion analysis: {emotion_result['chunks_analyzed']} chunks, {emotion_result['total_tokens']} tokens")
        else:
            print(f"✓ Emotion analysis: Single pass, {emotion_result['total_tokens']} tokens")
        
        if depression_result.get('chunking_applied'):
            print(f"✓ Depression analysis: {depression_result['chunks_analyzed']} chunks, {depression_result['total_tokens']} tokens")
        else:
            print(f"✓ Depression analysis: Single pass, {depression_result['total_tokens']} tokens")
        
        if request.privacy_mode == PrivacyModeRequest.FULL_PRIVACY:
            # FULL PRIVACY: Only distributions to LLM (ALL CHUNKS)
            print("Mode: Full Privacy - Using only classifier distributions")
            
            # Build chunk-by-chunk emotion analysis
            emotion_chunks_str = ""
            if emotion_result.get('chunking_applied'):
                emotion_chunks_str = "\n**EMOTION ANALYSIS BY CHUNK:**\n"
                for chunk_dist in emotion_result['chunk_distributions']:
                    emotion_chunks_str += f"\nChunk {chunk_dist['chunk_index']}:\n"
                    emotion_chunks_str += f"  Preview: {chunk_dist['chunk_preview']}\n"
                    emotion_chunks_str += f"  Distribution: {json.dumps(chunk_dist['distribution'], indent=4)}\n"
                    emotion_chunks_str += f"  Dominant: {chunk_dist['dominant']}\n"
            
            # Build chunk-by-chunk depression analysis
            depression_chunks_str = ""
            if depression_result.get('chunking_applied'):
                depression_chunks_str = "\n**DEPRESSION ANALYSIS BY CHUNK:**\n"
                for chunk_dist in depression_result['chunk_distributions']:
                    depression_chunks_str += f"\nChunk {chunk_dist['chunk_index']}:\n"
                    depression_chunks_str += f"  Preview: {chunk_dist['chunk_preview']}\n"
                    depression_chunks_str += f"  Distribution: {json.dumps(chunk_dist['distribution'], indent=4)}\n"
                    depression_chunks_str += f"  Level: {chunk_dist['dominant']}\n"
            
            llm_prompt = f"""Analyze this mental health assessment data with CHUNK-LEVEL GRANULARITY:

EMOTION ANALYSIS SUMMARY:
- Total chunks: {emotion_result.get('chunks_analyzed', 1)}
- Aggregated distribution: {json.dumps(emotion_result['all_emotions'], indent=2)}
- Overall dominant: {emotion_result['dominant_emotion']} ({emotion_result['confidence']:.2f})

{emotion_chunks_str}

DEPRESSION ANALYSIS SUMMARY:
- Total chunks: {depression_result.get('chunks_analyzed', 1)}
- Aggregated distribution: {json.dumps(depression_result['all_scores'], indent=2)}
- Overall level: {depression_result['depression_level']} (severity: {depression_result['severity']}/10)

{depression_chunks_str}

**CRITICAL**: You have MULTIPLE softmax distributions from different parts of the text.
Analyze:
1. **Emotional progression**: How emotions change across chunks
2. **Mixed states**: Conflicting emotions in different sections
3. **Severity patterns**: Increasing/decreasing depression indicators
4. **Context clues**: Chunk previews show content transitions

NO TEXT PROVIDED (Full Privacy Mode) - Use distributions + chunk previews only.

Provide assessment as JSON with specific scores and DIRECT recommendations:
{{
    "mental_health_score": 0-100,
    "depression_score": 0-100,
    "anxiety_score": 0-100,
    "stress_score": 0-100,
    "risk_level": "low/moderate/high/critical",
    "confidence": 0.0-1.0,
    "key_indicators": ["indicator1", "indicator2"],
    "recommendations": ["You should...", "Consider..."],
    "emotional_trajectory": "Description of how emotions evolved across chunks"
}}

IMPORTANT: Write recommendations in SECOND PERSON (address as 'you')."""

        else:
            # ANONYMIZED: Remove PII, send to LLM WITH CHUNK CONTEXT
            print("Mode: Anonymized - Removing PII and sending to LLM with chunk analysis")
            
            anonymized_text = remove_pii(request.text)
            
            # Truncate if very long
            if len(anonymized_text) > 4000:
                anonymized_text = anonymized_text[:4000] + "\n[... text truncated for LLM analysis ...]"
                print(f"⚠️ Truncated anonymized text to 4000 chars for LLM")
            
            # Build chunk-level analysis strings (same as above)
            emotion_chunks_str = ""
            if emotion_result.get('chunking_applied'):
                emotion_chunks_str = "\n**EMOTION PROGRESSION ACROSS CHUNKS:**\n"
                for chunk_dist in emotion_result['chunk_distributions']:
                    emotion_chunks_str += f"\nChunk {chunk_dist['chunk_index']}: {chunk_dist['dominant']}\n"
                    emotion_chunks_str += f"  Distribution: {json.dumps(chunk_dist['distribution'], indent=4)}\n"
            
            depression_chunks_str = ""
            if depression_result.get('chunking_applied'):
                depression_chunks_str = "\n**DEPRESSION INDICATORS BY SECTION:**\n"
                for chunk_dist in depression_result['chunk_distributions']:
                    depression_chunks_str += f"\nChunk {chunk_dist['chunk_index']}: {chunk_dist['dominant']}\n"
                    depression_chunks_str += f"  Distribution: {json.dumps(chunk_dist['distribution'], indent=4)}\n"
            
            llm_prompt = f"""Analyze this mental health journal entry with CHUNK-LEVEL EMOTION TRACKING:

ANONYMIZED TEXT:
"{anonymized_text}"

EMOTION ANALYSIS (Chunked - {emotion_result.get('chunks_analyzed', 1)} sections):
Overall: {emotion_result['dominant_emotion']} ({emotion_result['confidence']:.2f})
{emotion_chunks_str}

DEPRESSION ANALYSIS (Chunked - {depression_result.get('chunks_analyzed', 1)} sections):
Overall: {depression_result['depression_level']} (severity: {depression_result['severity']}/10)
{depression_chunks_str}

**LEVERAGE CHUNK-LEVEL DATA**:
- Identify emotional shifts throughout the journal
- Detect conflicting feelings in different sections
- Assess if depression indicators worsen or improve across text
- Provide context-aware recommendations based on emotional trajectory

Provide comprehensive assessment as JSON:
{{
    "mental_health_score": 0-100,
    "depression_score": 0-100,
    "anxiety_score": 0-100,
    "stress_score": 0-100,
    "risk_level": "low/moderate/high/critical",
    "confidence": 0.0-1.0,
    "key_indicators": ["indicator1", "indicator2"],
    "recommendations": ["You should...", "Consider..."],
    "emotional_journey": "Description of how their emotional state evolved throughout the entry"
}}

IMPORTANT: Write recommendations in SECOND PERSON (address as 'you')."""

        # Get LLM assessment
        from groq import Groq
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a mental health assessment expert. Provide comprehensive analysis in JSON format."},
                {"role": "user", "content": llm_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        llm_assessment = json.loads(response.choices[0].message.content)
        
        # Save complete results to file
        complete_result = {
            "journal_id": journal_id,
            "timestamp": datetime.utcnow().isoformat(),
            "privacy_mode": request.privacy_mode.value,
            "text_length": len(request.text),
            "text_statistics": {
                "total_tokens_emotion": emotion_result.get('total_tokens'),
                "chunks_emotion": emotion_result.get('chunks_analyzed'),
                "chunks_depression": depression_result.get('chunks_analyzed'),
                "chunking_applied": emotion_result.get('chunking_applied') or depression_result.get('chunking_applied')
            },
            "emotion_analysis": emotion_result,
            "depression_analysis": depression_result,
            "llm_assessment": llm_assessment
        }
        
        journal_path = file_manager.results_dir / f"{journal_id}_text_journal.json"
        with open(journal_path, 'w') as f:
            json.dump(complete_result, f, indent=2)
        
        # Save to MongoDB
        journal_data = {
            "user_id": current_user.id,
            "journal_type": "text",
            "privacy_mode": request.privacy_mode.value,
            "content": request.text if request.privacy_mode.value == "anonymized" else None,
            "text_length": len(request.text),
            "chunking_applied": emotion_result.get('chunking_applied') or depression_result.get('chunking_applied')
        }
        
        db_journal_id = await JournalService.create_journal_entry(
            user_id=current_user.id,
            journal_data=journal_data,
            analysis_result=complete_result
        )
        
        print(f"Text journal saved to database with ID: {db_journal_id}")
        print(f"Text journal analysis completed: {journal_id}")
        
        return TextJournalResponse(
            success=True,
            journal_id=journal_id,
            mental_health_score=llm_assessment['mental_health_score'],
            depression_score=llm_assessment['depression_score'],
            anxiety_score=llm_assessment['anxiety_score'],
            stress_score=llm_assessment['stress_score'],
            risk_level=llm_assessment['risk_level'],
            confidence=llm_assessment['confidence'],
            dominant_emotion=emotion_result['dominant_emotion'],
            depression_level=depression_result['depression_level'],
            key_indicators=llm_assessment['key_indicators'],
            recommendations=llm_assessment['recommendations'],
            analysis_summary={
                "emotion_scores": emotion_result['all_emotions'],
                "depression_severity": depression_result['severity'],
                "privacy_mode": request.privacy_mode.value,
                "db_journal_id": db_journal_id,
                "chunking_info": {
                    "applied": emotion_result.get('chunking_applied') or depression_result.get('chunking_applied'),
                    "emotion_chunks": emotion_result.get('chunks_analyzed', 1),
                    "depression_chunks": depression_result.get('chunks_analyzed', 1),
                    "total_tokens": emotion_result.get('total_tokens')
                }
            }
        )
        
    except Exception as e:
        print(f"Text journal analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# Authentication routes
@app.post("/api/auth/register", response_model=Token)
async def register(user: UserCreate):
    """Register a new user"""
    try:
        users_collection = await get_users_collection()
        
        # Check if user already exists
        existing_user = await users_collection.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Validate password length
        if len(user.password) > 72:
            raise HTTPException(
                status_code=400,
                detail="Password cannot be longer than 72 characters"
            )
        
        if len(user.password) < 8:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters"
            )
        
        # Create user document
        try:
            hashed_password = get_password_hash(user.password)
        except Exception as e:
            print(f"Password hashing error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process password"
            )
        
        user_dict = {
            "email": user.email,
            "full_name": user.full_name,
            "hashed_password": hashed_password,
            "date_created": datetime.utcnow(),
            "is_active": True
        }
        
        result = await users_collection.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email})
        
        # Prepare user response
        user_response = UserResponse(
            id=user_dict["_id"],
            email=user_dict["email"],
            full_name=user_dict["full_name"],
            date_created=user_dict["date_created"],
            is_active=user_dict["is_active"]
        )
        
        return Token(
            access_token=access_token,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Login user"""
    try:
        users_collection = await get_users_collection()
        
        # Find user by email
        user = await users_collection.find_one({"email": user_credentials.email})
        
        if not user or not verify_password(user_credentials.password, user["hashed_password"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        if not user.get("is_active", True):
            raise HTTPException(status_code=400, detail="Inactive user")
        
        # Create access token
        access_token = create_access_token(data={"sub": user["email"]})
        
        # Prepare user response
        user_response = UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user["full_name"],
            date_created=user["date_created"],
            is_active=user.get("is_active", True)
        )
        
        return Token(
            access_token=access_token,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        date_created=current_user.date_created,
        is_active=current_user.is_active
    )


@app.get("/api/journals/my-journals")
async def get_my_journals(
    limit: int = 50,
    journal_type: Optional[str] = None,
    current_user = Depends(get_current_active_user)
):
    """Get current user's journal entries"""
    try:
        journals_collection = await JournalService.get_journals_collection()
        
        query = {
            "user_id": current_user.id,
            "is_deleted": False
        }
        
        if journal_type:
            query["journal_type"] = journal_type
        
        journals = await journals_collection.find(query).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        # Convert ObjectId and datetime to string
        for journal in journals:
            journal["_id"] = str(journal["_id"])
            # Handle date field (could be datetime or date)
            if "date" in journal:
                if isinstance(journal["date"], datetime):
                    journal["date"] = journal["date"].date().isoformat()
                else:
                    journal["date"] = journal["date"].isoformat() if hasattr(journal["date"], "isoformat") else str(journal["date"])
            
            if "timestamp" in journal:
                journal["timestamp"] = journal["timestamp"].isoformat() if hasattr(journal["timestamp"], "isoformat") else str(journal["timestamp"])
        
        return {
            "success": True,
            "count": len(journals),
            "journals": journals
        }
        
    except Exception as e:
        print(f"Error fetching journals: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/journals/heatmap/{year}")
async def get_journal_heatmap(
    year: int,
    current_user = Depends(get_current_active_user)
):
    """Get heatmap data for journal entries (like GitHub contributions)"""
    try:
        heatmap_data = await JournalService.get_heatmap_data(
            user_id=current_user.id,
            year=year
        )
        
        # Convert dates to strings
        heatmap_dict = {
            "user_id": heatmap_data.user_id,
            "year": heatmap_data.year,
            "current_streak": heatmap_data.current_streak,
            "longest_streak": heatmap_data.longest_streak,
            "total_entries": heatmap_data.total_entries,
            "data": [
                {
                    "date": point.date.isoformat(),
                    "value": point.value,
                    "mental_health_score": point.mental_health_score,
                    "total_entries": point.total_entries,
                    "tooltip": point.tooltip
                }
                for point in heatmap_data.data
            ]
        }
        
        return heatmap_dict
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/journals/stats")
async def get_journal_stats(
    current_user = Depends(get_current_active_user)
):
    """Get journal statistics for current user"""
    try:
        journals_collection = await JournalService.get_journals_collection()
        streaks_collection = await JournalService.get_streaks_collection()
        
        # Get total counts
        total_entries = await journals_collection.count_documents({
            "user_id": current_user.id,
            "is_deleted": False
        })
        
        text_entries = await journals_collection.count_documents({
            "user_id": current_user.id,
            "journal_type": "text",
            "is_deleted": False
        })
        
        video_entries = await journals_collection.count_documents({
            "user_id": current_user.id,
            "journal_type": "video",
            "is_deleted": False
        })
        
        # Get streak info
        streak_doc = await streaks_collection.find_one({"user_id": current_user.id})
        
        current_streak = streak_doc["current_streak"] if streak_doc else 0
        longest_streak = streak_doc["longest_streak"] if streak_doc else 0
        
        # Handle last_entry_date - could be datetime or date
        last_entry_date = None
        if streak_doc and streak_doc.get("last_entry_date"):
            led = streak_doc["last_entry_date"]
            if isinstance(led, datetime):
                last_entry_date = led.date().isoformat()
            else:
                last_entry_date = led.isoformat() if hasattr(led, "isoformat") else None
        
        return {
            "success": True,
            "stats": {
                "total_entries": total_entries,
                "text_entries": text_entries,
                "video_entries": video_entries,
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "last_entry_date": last_entry_date
            }
        }
        
    except Exception as e:
        print(f"Error fetching journal stats: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/journals/recent-scores")
async def get_recent_scores(
    days: int = 5,
    current_user = Depends(get_current_active_user)
):
    """Get recent mental health scores for chatbot context"""
    try:
        journals_collection = await JournalService.get_journals_collection()
        
        # Get journals from last N days
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        journals = await journals_collection.find({
            "user_id": current_user.id,
            "is_deleted": False,
            "timestamp": {"$gte": cutoff_date}
        }).sort("timestamp", -1).to_list(length=100)
        
        # Extract scores by day
        daily_scores = {}
        for journal in journals:
            date_key = journal["timestamp"].date().isoformat()
            
            if date_key not in daily_scores:
                daily_scores[date_key] = {
                    "date": date_key,
                    "depression_scores": [],
                    "anxiety_scores": [],
                    "stress_scores": [],
                    "mental_health_scores": []
                }
            
            llm = journal.get("llm_assessment", {})
            daily_scores[date_key]["depression_scores"].append(llm.get("depression_score", 0))
            daily_scores[date_key]["anxiety_scores"].append(llm.get("anxiety_score", 0))
            daily_scores[date_key]["stress_scores"].append(llm.get("stress_score", 0))
            daily_scores[date_key]["mental_health_scores"].append(llm.get("mental_health_score", 0))
        
        # Calculate daily averages
        summary = []
        for date_key in sorted(daily_scores.keys(), reverse=True):
            day_data = daily_scores[date_key]
            summary.append({
                "date": day_data["date"],
                "avg_depression": round(sum(day_data["depression_scores"]) / len(day_data["depression_scores"])),
                "avg_anxiety": round(sum(day_data["anxiety_scores"]) / len(day_data["anxiety_scores"])),
                "avg_stress": round(sum(day_data["stress_scores"]) / len(day_data["stress_scores"])),
                "avg_mental_health": round(sum(day_data["mental_health_scores"]) / len(day_data["mental_health_scores"])),
                "entries_count": len(day_data["depression_scores"])
            })
        
        return {
            "success": True,
            "days": days,
            "data": summary[:days]  # Return only requested number of days
        }
        
    except Exception as e:
        print(f"Error fetching recent scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    freeze_support()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )