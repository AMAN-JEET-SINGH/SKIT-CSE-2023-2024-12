"""
FastAPI application for video emotion analysis - Optimized with Frame Sampling
No Grad-CAM in API | Videos kept in uploads folder
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
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

from emotion_detector import EmotionDetector

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UploadResponse(BaseModel):
    task_id: str
    message: str
    status: str
    video_path: str

class StatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str
    current_interval: Optional[int] = None
    total_intervals: Optional[int] = None


# ============================================================================
# FILE MANAGER
# ============================================================================

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
        print(f"📁 Directories initialized:")
        print(f"   - Uploads: {self.uploads_dir}")
        print(f"   - Results: {self.results_dir}")
        print(f"   - Status: {self.status_dir}")
    
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
        print(f"💾 Result saved: {result_path}")
    
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
    
    def delete_result(self, task_id: str):
        """Delete result file"""
        result_path = self.get_result_path(task_id)
        if result_path.exists():
            result_path.unlink()
            print(f"🗑️  Deleted result: {result_path}")
    
    def delete_status(self, task_id: str):
        """Delete status file"""
        status_path = self.get_status_path(task_id)
        if status_path.exists():
            status_path.unlink()
            print(f"🗑️  Deleted status: {status_path}")
    
    def delete_upload(self, task_id: str):
        """Delete uploaded video file"""
        for file in self.uploads_dir.glob(f"{task_id}.*"):
            file.unlink()
            print(f"🗑️  Deleted upload: {file}")
    
    def cleanup_task(self, task_id: str, keep_video: bool = True):
        """Delete files associated with a task"""
        if not keep_video:
            self.delete_upload(task_id)
        self.delete_result(task_id)
        self.delete_status(task_id)
        print(f"✅ Task {task_id} cleaned up (video kept: {keep_video})")
    
    def get_video_path(self, task_id: str) -> Path:
        """Find the video file for a given task_id"""
        for file in self.uploads_dir.glob(f"{task_id}.*"):
            return file
        raise FileNotFoundError(f"Video not found for task {task_id}")


# ============================================================================
# PROGRESS TRACKER
# ============================================================================

class ProgressTracker:
    """Track analysis progress and update status"""
    
    def __init__(self, task_id: str, file_manager: FileManager):
        self.task_id = task_id
        self.file_manager = file_manager
        self.current_interval = 0
        self.total_intervals = 0
    
    async def update(self, current: int, total: int):
        """Update progress status"""
        self.current_interval = current
        self.total_intervals = total
        progress = (current / total * 100) if total > 0 else 0
        
        status_data = {
            'task_id': self.task_id,
            'status': 'processing',
            'progress': round(progress, 2),
            'current_interval': current,
            'total_intervals': total,
            'message': f'Processing interval {current}/{total}'
        }
        
        self.file_manager.save_status(self.task_id, status_data)


# ============================================================================
# ANALYSIS SERVICE WITH FRAME SAMPLING
# ============================================================================

class AnalysisService:
    """Service for managing emotion detection analysis with optimizations"""
    
    def __init__(self):
        self.detector = None
        self._model_loaded = False
    
    def _load_model(self):
        """Lazy load the emotion detector model"""
        if not self._model_loaded:
            print("🔄 Loading emotion detection model...")
            self.detector = EmotionDetector()
            self._model_loaded = True
            print("✅ Model loaded successfully")
    
    async def analyze_video(
        self,
        video_path: Path,
        task_id: str,
        file_manager: FileManager,
        interval_seconds: int = 5,
        frame_skip: int = 2
    ) -> dict:
        """
        Analyze video with frame sampling optimization
        
        Args:
            video_path: Path to video file
            task_id: Unique task identifier
            file_manager: File management instance
            interval_seconds: Seconds per analysis interval
            frame_skip: Process every Nth frame (2 = process 1 out of 2 frames)
        """
        try:
            self._load_model()
            progress_tracker = ProgressTracker(task_id, file_manager)
            
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'processing',
                'progress': 0.0,
                'message': 'Starting analysis with frame sampling...'
            })
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._run_analysis_sync,
                video_path,
                interval_seconds,
                frame_skip,
                progress_tracker
            )
            
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'completed',
                'progress': 100.0,
                'message': 'Analysis completed successfully'
            })
            
            return results
            
        except Exception as e:
            file_manager.save_status(task_id, {
                'task_id': task_id,
                'status': 'failed',
                'progress': 0.0,
                'message': f'Analysis failed: {str(e)}'
            })
            raise
    
    def _run_analysis_sync(
        self,
        video_path: Path,
        interval_seconds: int,
        frame_skip: int,
        progress_tracker: ProgressTracker
    ) -> dict:
        """
        Synchronous wrapper - calls optimized analysis method
        NO GRAD-CAM in API analysis
        """
        return self.detector.analyze_video_by_intervals_optimized(
            video_path=str(video_path),
            interval_seconds=interval_seconds,
            frame_skip=frame_skip,
            progress_tracker=progress_tracker
        )


# ============================================================================
# VIDEO SERVICE
# ============================================================================

class VideoService:
    """Service for managing video processing workflow"""
    
    def __init__(self, file_manager: FileManager, analysis_service: AnalysisService):
        self.file_manager = file_manager
        self.analysis_service = analysis_service
    
    async def process_upload(
        self,
        file: UploadFile,
        interval_seconds: int,
        frame_skip: int,
        background_tasks: BackgroundTasks
    ) -> tuple[str, str]:
        """Handle video upload and initiate analysis"""
        task_id = self.file_manager.generate_task_id()
        upload_path = self.file_manager.get_upload_path(task_id, file.filename)
        
        try:
            with open(upload_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            print(f"📤 Video uploaded: {upload_path}")
        finally:
            await file.close()
        
        self.file_manager.save_status(task_id, {
            'task_id': task_id,
            'status': 'queued',
            'progress': 0.0,
            'message': 'Video uploaded. Analysis queued.'
        })
        
        background_tasks.add_task(
            self._analyze_and_save,
            task_id=task_id,
            video_path=upload_path,
            interval_seconds=interval_seconds,
            frame_skip=frame_skip
        )
        
        return task_id, str(upload_path)
    
    async def _analyze_and_save(
        self,
        task_id: str,
        video_path: Path,
        interval_seconds: int,
        frame_skip: int
    ):
        """Background task: Analyze video and save results (video kept)"""
        try:
            print(f"🎬 Starting analysis for task: {task_id}")
            
            results = await self.analysis_service.analyze_video(
                video_path=video_path,
                task_id=task_id,
                file_manager=self.file_manager,
                interval_seconds=interval_seconds,
                frame_skip=frame_skip
            )
            
            self.file_manager.save_result(task_id, results)
            
            print(f"✅ Analysis completed for task: {task_id}")
            print(f"📹 Video kept at: {video_path}")
            
        except Exception as e:
            print(f"❌ Analysis failed for task {task_id}: {str(e)}")
    
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
        """Cleanup task files (video kept by default)"""
        self.file_manager.cleanup_task(task_id, keep_video=not delete_video)


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Video Emotion Analysis API - Optimized",
    description="Fast emotion analysis with frame sampling. Videos stored for Grad-CAM.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
file_manager = FileManager()
analysis_service = AnalysisService()
video_service = VideoService(file_manager, analysis_service)


@app.on_event("startup")
async def startup_event():
    """Initialize required directories on startup"""
    file_manager.setup_directories()
    print("✅ Application started successfully")
    print("⚡ Frame sampling enabled for faster processing")
    print("📹 Videos will be kept in uploads/ folder")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🔄 Shutting down application...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Video Emotion Analysis API - Optimized",
        "version": "2.0.0",
        "features": [
            "Frame sampling for 2-3x faster processing",
            "Videos stored in uploads/ for Grad-CAM",
            "No Grad-CAM computation in main API"
        ],
        "endpoints": {
            "upload": "/api/upload-video",
            "status": "/api/status/{task_id}",
            "result": "/api/result/{task_id}",
            "download": "/api/download-result/{task_id}",
            "video": "/api/video/{task_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/upload-video", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    interval_seconds: int = 5,
    frame_skip: int = 2
):
    """
    Upload a video for emotion analysis (Optimized with frame sampling)
    
    Parameters:
    - file: Video file (mp4, avi, mov, etc.)
    - interval_seconds: Analysis interval duration (default: 5)
    - frame_skip: Process every Nth frame (default: 2, means 2x faster)
      * 1 = process all frames (slowest, most accurate)
      * 2 = process every 2nd frame (2x faster, recommended)
      * 3 = process every 3rd frame (3x faster)
    
    Returns:
    - task_id: Unique identifier for tracking analysis
    - video_path: Path where video is stored
    - message: Status message
    
    Note: Video is kept in uploads/ for later Grad-CAM visualization
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        if frame_skip < 1:
            raise HTTPException(
                status_code=400,
                detail="frame_skip must be >= 1"
            )
        
        task_id, video_path = await video_service.process_upload(
            file=file,
            interval_seconds=interval_seconds,
            frame_skip=frame_skip,
            background_tasks=background_tasks
        )
        
        return UploadResponse(
            task_id=task_id,
            message=f"Video uploaded. Analysis started with frame_skip={frame_skip}.",
            status="processing",
            video_path=video_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/status/{task_id}", response_model=StatusResponse)
async def get_analysis_status(task_id: str):
    """
    Get the status of a video analysis task
    
    Parameters:
    - task_id: Task identifier from upload
    
    Returns:
    - status: processing|completed|failed|not_found
    - progress: Progress percentage (0-100)
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
    Get the complete analysis result
    
    Parameters:
    - task_id: Task identifier
    
    Returns:
    - Complete JSON with interval scores and summary
    """
    try:
        result = await video_service.get_analysis_result(task_id)
        return JSONResponse(content=result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Result not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-result/{task_id}")
async def download_result(task_id: str):
    """
    Download the analysis result as a JSON file
    
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
            filename=f"emotion_analysis_{task_id}.json"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/{task_id}")
async def get_video(task_id: str):
    """
    Get the uploaded video file (for Grad-CAM visualization)
    
    Parameters:
    - task_id: Task identifier
    
    Returns:
    - Video file path information
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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )