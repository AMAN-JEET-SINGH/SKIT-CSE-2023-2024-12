"""
Emotion Detector - Optimized with Frame Sampling (No Grad-CAM in API)
"""

import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import numpy as np
import cv2
import asyncio
from collections import defaultdict
from facenet_pytorch import MTCNN
import warnings

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

class EmotionDetector:
    def __init__(self, model_name="dima806/facial_emotions_image_detection"):
        """Initialize the emotion detection model"""
        print("Loading emotion model...")
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForImageClassification.from_pretrained(model_name)
        self.model.eval()
        
        # Get all emotion labels
        self.emotion_labels = list(self.model.config.id2label.values())
        print(f"Emotions that can be detected: {', '.join(self.emotion_labels)}")
        
        # Load MTCNN face detector
        print("Loading MTCNN face detector...")
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.mtcnn = MTCNN(
            keep_all=True,
            device=device,
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7],
            post_process=False
        )
        print(f"MTCNN loaded on {device}")
        print("All models loaded successfully!")
    
    def _detect_faces_mtcnn(self, frame):
        """Detect faces using MTCNN"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes, probs = self.mtcnn.detect(rgb_frame)
        
        faces = []
        if boxes is not None:
            for box, prob in zip(boxes, probs):
                if prob > 0.9:
                    x1, y1, x2, y2 = box
                    x, y = int(x1), int(y1)
                    w, h = int(x2 - x1), int(y2 - y1)
                    
                    x = max(0, x)
                    y = max(0, y)
                    w = min(w, frame.shape[1] - x)
                    h = min(h, frame.shape[0] - y)
                    
                    faces.append((x, y, w, h, prob))
        
        return faces
    
    def detect_emotion(self, frame):
        """Detect emotion from a frame (NO Grad-CAM)"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        
        inputs = self.processor(images=pil_image, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=1)[0]
        
        pred_id = logits.argmax(dim=1).item()
        pred_label = self.model.config.id2label[pred_id]
        
        all_probs = {self.model.config.id2label[i]: probs[i].item() 
                        for i in range(len(probs))}
        
        return pred_label, all_probs
    
    def analyze_video_by_intervals_optimized(
        self,
        video_path: str,
        interval_seconds: int = 5,
        frame_skip: int = 2,
        progress_tracker=None
    ):
        """
        OPTIMIZED: Analyze video with frame sampling for faster processing
        
        Args:
            video_path: Path to video file
            interval_seconds: Seconds per analysis interval
            frame_skip: Process every Nth frame (2 = 2x faster, 3 = 3x faster)
            progress_tracker: Progress tracking object
        
        Returns:
            Analysis results dictionary
        """
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video file {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / fps
        
        frames_per_interval = int(fps * interval_seconds)
        total_intervals = int(np.ceil(duration_seconds / interval_seconds))
        
        print(f"⚡ Frame sampling enabled: processing 1 out of every {frame_skip} frames")
        print(f"📊 Video: {total_frames} frames, {duration_seconds:.2f}s")
        print(f"🎯 Effective processing: ~{total_frames // frame_skip} frames")
        
        # Storage for interval data
        intervals_data = []
        current_interval = {
            'interval_number': 0,
            'start_time': 0.0,
            'end_time': interval_seconds,
            'detections': [],
            'frames_with_face': 0,
            'frames_processed': 0,
            'frames_sampled': 0
        }
        
        frame_count = 0
        interval_frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            interval_frame_count += 1
            
            # FRAME SAMPLING: Only process every Nth frame
            if frame_count % frame_skip != 0:
                current_interval['frames_processed'] += 1
                continue
            
            current_interval['frames_sampled'] += 1
            
            # Detect faces
            faces = self._detect_faces_mtcnn(frame)
            
            if len(faces) > 0:
                x, y, w, h, conf = max(faces, key=lambda f: f[2] * f[3])
                face_roi = frame[y:y+h, x:x+w]
                
                emotion, probabilities = self.detect_emotion(face_roi)
                
                current_interval['detections'].append({
                    'emotion': emotion,
                    'probabilities': probabilities
                })
                current_interval['frames_with_face'] += 1
            
            current_interval['frames_processed'] += 1
            
            # Check if interval is complete
            if interval_frame_count >= frames_per_interval or frame_count >= total_frames:
                interval_scores = self._calculate_interval_scores(current_interval)
                intervals_data.append(interval_scores)
                
                # Update progress via tracker
                if progress_tracker:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            progress_tracker.update(len(intervals_data), total_intervals)
                        )
                        loop.close()
                    except Exception as e:
                        print(f"Progress update error: {e}")
                
                # Start new interval
                interval_frame_count = 0
                current_interval = {
                    'interval_number': len(intervals_data),
                    'start_time': len(intervals_data) * interval_seconds,
                    'end_time': (len(intervals_data) + 1) * interval_seconds,
                    'detections': [],
                    'frames_with_face': 0,
                    'frames_processed': 0,
                    'frames_sampled': 0
                }
        
        cap.release()
        
        # Prepare results
        results = {
            'video_info': {
                'path': str(video_path),
                'fps': fps,
                'duration_seconds': duration_seconds,
                'total_frames': total_frames,
                'interval_seconds': interval_seconds,
                'frame_skip': frame_skip,
                'optimization': f"Processed 1/{frame_skip} frames for {frame_skip}x speedup"
            },
            'emotion_labels': self.emotion_labels,
            'intervals': intervals_data,
            'summary': self._calculate_overall_summary(intervals_data)
        }
        
        return results
    
    def _calculate_interval_scores(self, interval_data):
        """Calculate weighted emotion scores for an interval"""
        detections = interval_data['detections']
        
        if not detections:
            scores = {emotion: 0.0 for emotion in self.emotion_labels}
            return {
                'interval_number': interval_data['interval_number'] + 1,
                'start_time': interval_data['start_time'],
                'end_time': interval_data['end_time'],
                'frames_processed': interval_data['frames_processed'],
                'frames_sampled': interval_data.get('frames_sampled', 0),
                'frames_with_face': 0,
                'face_detection_rate': 0.0,
                'emotion_scores': scores,
                'dominant_emotion': 'none',
                'detections_count': 0
            }
        
        emotion_score_accumulator = defaultdict(float)
        
        for detection in detections:
            probs = detection['probabilities']
            for emotion, prob in probs.items():
                emotion_score_accumulator[emotion] += prob
        
        total_detections = len(detections)
        emotion_scores = {}
        for emotion in self.emotion_labels:
            avg_prob = emotion_score_accumulator[emotion] / total_detections
            detection_rate = interval_data['frames_with_face'] / max(interval_data['frames_sampled'], 1)
            emotion_scores[emotion] = round(avg_prob * detection_rate * 100, 2)
        
        dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
        
        return {
            'interval_number': interval_data['interval_number'] + 1,
            'start_time': round(interval_data['start_time'], 2),
            'end_time': round(interval_data['end_time'], 2),
            'frames_processed': interval_data['frames_processed'],
            'frames_sampled': interval_data.get('frames_sampled', 0),
            'frames_with_face': interval_data['frames_with_face'],
            'face_detection_rate': round(interval_data['frames_with_face'] / max(interval_data['frames_sampled'], 1), 3),
            'emotion_scores': emotion_scores,
            'dominant_emotion': dominant_emotion,
            'detections_count': total_detections
        }
    
    def _calculate_overall_summary(self, intervals_data):
        """Calculate overall video emotion summary"""
        if not intervals_data:
            return {}
        
        total_scores = defaultdict(float)
        total_intervals = len(intervals_data)
        
        for interval in intervals_data:
            for emotion, score in interval['emotion_scores'].items():
                total_scores[emotion] += score
        
        avg_scores = {emotion: round(score / total_intervals, 2) 
                        for emotion, score in total_scores.items()}
        
        dominant_emotion = max(avg_scores.items(), key=lambda x: x[1])[0]
        
        return {
            'total_intervals': total_intervals,
            'average_emotion_scores': avg_scores,
            'overall_dominant_emotion': dominant_emotion
        }