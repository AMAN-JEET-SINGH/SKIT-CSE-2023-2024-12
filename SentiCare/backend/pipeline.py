"""
Integrated Multimodal Analysis Pipeline
Combines video emotion detection with audio/text analysis
"""

import os
import json
import subprocess
import shutil
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import re

import torch
import torchaudio
import spacy
import httpx
from transformers import (
    AutoModelForAudioClassification,
    AutoFeatureExtractor,
    pipeline
)
from groq import Groq
from dotenv import load_dotenv

# Import video emotion detector
from emotion_detector import EmotionDetector

load_dotenv()


class PrivacyMode(Enum):
    FULL_PRIVACY = "full_privacy"
    ANONYMIZED = "anonymized"


@dataclass
class MultimodalAnalysisResult:
    """Complete multimodal analysis results"""
    video_path: str
    video_emotion: Dict  # From EmotionDetector
    transcript: Dict
    audio_emotion: Dict
    text_analysis: Dict
    privacy_mode: str
    llm_final_assessment: Dict
    summary: Dict



# AUDIO EXTRACTION
class AudioExtractor:
    @staticmethod
    def extract(video_path: str, output_audio: str = "temp_audio.wav") -> str:
        if not shutil.which("ffmpeg"):
            raise EnvironmentError("ffmpeg not found")
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            output_audio, '-y'
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_audio



# TRANSCRIPTION
class Transcriber:
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise EnvironmentError("Missing DEEPGRAM_API_KEY")
    
    def transcribe(self, audio_path: str) -> Dict:
        with open(audio_path, "rb") as audio:
            buffer_data = audio.read()
        
        response = httpx.post(
            "https://api.deepgram.com/v1/listen",
            params={
                "model": "nova-2",
                "smart_format": "true",
                "punctuate": "true",
            },
            headers={
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/wav"
            },
            content=buffer_data,
            timeout=60.0
        )
        response.raise_for_status()
        
        data = response.json()
        result = data["results"]["channels"][0]["alternatives"][0]
        words = [
            {"word": w["word"], "start": w["start"], "end": w["end"]}
            for w in result.get("words", [])
        ]
        
        return {
            "text": result.get("transcript", ""),
            "words": words,
            "duration": words[-1]["end"] if words else 0.0,
            "confidence": result.get("confidence", 0.0)
        }



# AUDIO EMOTION
class AudioEmotionAnalyzer:
    def __init__(self):
        print("Loading audio emotion model...")
        model_name = "superb/wav2vec2-base-superb-er"
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
        self.model = AutoModelForAudioClassification.from_pretrained(model_name)
        print("Audio model loaded!")
    
    def analyze(self, audio_path: str) -> Dict:
        waveform, sample_rate = torchaudio.load(audio_path)
        
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
        
        inputs = self.feature_extractor(
            waveform.squeeze().numpy(),
            sampling_rate=16000,
            return_tensors="pt"
        )
        
        with torch.no_grad():
            logits = self.model(**inputs).logits
        
        probs = torch.nn.functional.softmax(logits, dim=-1)[0]
        emotions = ['neutral', 'happy', 'sad', 'angry']
        predicted_idx = torch.argmax(probs).item()
        
        return {
            "emotion": emotions[predicted_idx],
            "confidence": float(probs[predicted_idx]),
            "all_emotions": {emotions[i]: float(probs[i]) for i in range(len(emotions))}
        }



# TEXT ANALYSIS
class TextAnalyzer:
    def __init__(self):
        print("Loading text analysis models...")
        self.nlp = spacy.load("en_core_web_sm")
        self.emotion_classifier = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            return_all_scores=True
        )
        self.depression_classifier = pipeline(
            "text-classification",
            model="rafalposwiata/deproberta-large-depression"
        )
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        print("Text models loaded!")
    
    def remove_pii(self, text: str) -> str:
        doc = self.nlp(text)
        anonymized = text
        
        for ent in reversed(doc.ents):
            if ent.label_ in ["PERSON", "ORG", "GPE", "FAC", "LOC"]:
                anonymized = (
                    anonymized[:ent.start_char] +
                    "[REDACTED]" +
                    anonymized[ent.end_char:]
                )
        
        anonymized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', anonymized)
        anonymized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', anonymized)
        return anonymized
    
    def analyze_emotion_local(self, text: str) -> Dict:
        results = self.emotion_classifier(text)[0]
        emotion_scores = {r['label']: r['score'] for r in results}
        dominant = max(results, key=lambda x: x['score'])
        
        return {
            "dominant_emotion": dominant['label'],
            "confidence": dominant['score'],
            "all_emotions": emotion_scores
        }
    
    def analyze_depression_local(self, text: str) -> Dict:
        result = self.depression_classifier(text)[0]
        severity_map = {"not depression": 0, "moderate": 5, "severe": 9}
        
        return {
            "depression_level": result['label'],
            "confidence": result['score'],
            "severity": severity_map.get(result['label'], 0)
        }
    
    def analyze_detailed_llm(self, text: str) -> Dict:
        prompt = f"""Analyze this text for mental health indicators:
                    Text: "{text}"
                    Respond ONLY with valid JSON:
                    {{
                        "emotions": ["primary", "secondary"],
                        "sentiment": "positive/negative/neutral",
                        "key_phrases": ["phrase1", "phrase2"],
                        "severity": 5
                    }}
                    Focus on: fatigue, sleep issues, hopelessness, worry, overwhelm.
                """
        
        response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a JSON API. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def analyze(self, text: str, privacy_mode: PrivacyMode) -> Tuple[Dict, Optional[str]]:
        emotion_result = self.analyze_emotion_local(text)
        depression_result = self.analyze_depression_local(text)
        
        if privacy_mode == PrivacyMode.FULL_PRIVACY:
            return {
                "emotion": emotion_result,
                "depression": depression_result,
                "llm_analysis": None,
                "anonymized_text": None
            }, None
        else:
            anonymized = self.remove_pii(text)
            llm_analysis = self.analyze_detailed_llm(anonymized)
            return {
                "emotion": emotion_result,
                "depression": depression_result,
                "llm_analysis": llm_analysis,
                "anonymized_text": anonymized
            }, anonymized



# VIDEO EMOTION ANALYSIS
class VideoEmotionAnalyzer:
    def __init__(self):
        print("Loading video emotion detector...")
        self.detector = EmotionDetector()
        print("Video emotion detector loaded!")
    
    def analyze(self, video_path: str, interval_seconds: int = 5, frame_skip: int = 2) -> Dict:
        """Analyze video emotions using optimized frame sampling"""
        return self.detector.analyze_video_by_intervals_optimized(
            video_path=video_path,
            interval_seconds=interval_seconds,
            frame_skip=frame_skip
        )



# MULTIMODAL PIPELINE
class MultimodalAnalysisPipeline:
    def __init__(self):
        print("\n" + "="*60)
        print("INITIALIZING MULTIMODAL ANALYSIS PIPELINE")
        print("="*60)
        
        self.audio_extractor = AudioExtractor()
        self.transcriber = Transcriber()
        self.audio_emotion = AudioEmotionAnalyzer()
        self.text_analyzer = TextAnalyzer()
        self.video_emotion = VideoEmotionAnalyzer()
        
        print("\nAll modules loaded!\n")
    
    def analyze_video(
        self,
        video_path: str,
        privacy_mode: PrivacyMode = PrivacyMode.ANONYMIZED,
        interval_seconds: int = 5,
        frame_skip: int = 2,
        cleanup: bool = True
    ) -> MultimodalAnalysisResult:
        """
        Run complete multimodal analysis
        
        Args:
            video_path: Path to video file
            privacy_mode: FULL_PRIVACY or ANONYMIZED
            interval_seconds: Video analysis interval
            frame_skip: Frame sampling rate (2 = 2x faster)
            cleanup: Remove temp audio file
        """
        print(f"\n{'='*60}")
        print(f"ANALYZING: {video_path}")
        print(f"Privacy: {privacy_mode.value} | Frame skip: {frame_skip}")
        print(f"{'='*60}\n")
        
        temp_audio = "temp_audio.wav"
        
        try:
            # 1. Video emotion analysis
            print("Analyzing video emotions...")
            video_emotion_result = self.video_emotion.analyze(
                video_path, interval_seconds, frame_skip
            )
            print(f"    Video analyzed ({len(video_emotion_result.get('intervals', []))} intervals)\n")
            
            # 2. Extract audio
            print("Extracting audio...")
            self.audio_extractor.extract(video_path, temp_audio)
            print("    Audio extracted\n")
            
            # 3. Transcribe
            print("Transcribing...")
            transcript = self.transcriber.transcribe(temp_audio)
            print(f"    Transcribed ({transcript['confidence']:.2%})\n")
            
            # 4. Audio emotion
            print("Analyzing audio emotion...")
            audio_emotion_result = self.audio_emotion.analyze(temp_audio)
            print(f"    {audio_emotion_result['emotion']}\n")
            
            # 5. Text analysis
            print("Analyzing text...")
            text_analysis, text_for_multimodal = self.text_analyzer.analyze(
                transcript['text'], privacy_mode
            )
            print(f"    Completed\n")
            
            # 6. Multimodal LLM assessment
            print("Getting multimodal LLM assessment...")
            llm_assessment = self._get_llm_assessment(
                video_emotion_result,
                audio_emotion_result,
                text_analysis,
                text_for_multimodal,
                privacy_mode
            )
            print("    Assessment complete\n")
            
            summary = self._generate_summary(
                video_emotion_result,
                audio_emotion_result,
                text_analysis,
                llm_assessment
            )
            
            result = MultimodalAnalysisResult(
                video_path=video_path,
                video_emotion=video_emotion_result,
                transcript=transcript,
                audio_emotion=audio_emotion_result,
                text_analysis=text_analysis,
                privacy_mode=privacy_mode.value,
                llm_final_assessment=llm_assessment,
                summary=summary
            )
            
            print(f"{'='*60}")
            print("ANALYSIS COMPLETE")
            print(f"{'='*60}\n")
            
            return result
            
        finally:
            if cleanup and os.path.exists(temp_audio):
                os.remove(temp_audio)
    
    def _get_llm_assessment(
        self,
        video_emotion: Dict,
        audio_emotion: Dict,
        text_analysis: Dict,
        text_for_multimodal: Optional[str],
        privacy_mode: PrivacyMode
    ) -> Dict:
        """Generate final multimodal assessment using LLM"""
        
        # Build text section based on privacy
        if privacy_mode == PrivacyMode.FULL_PRIVACY:
            text_info = f"""
TEXT ANALYSIS (Classifier Outputs Only):
- Emotion: {text_analysis['emotion']['dominant_emotion']} ({text_analysis['emotion']['confidence']:.2f})
- Depression: {text_analysis['depression']['depression_level']} ({text_analysis['depression']['confidence']:.2f})
- Severity: {text_analysis['depression']['severity']}/10
"""
        else:
            text_info = f"""
TEXT ANALYSIS:
- Transcript: "{text_for_multimodal}"
- Emotion: {text_analysis['emotion']['dominant_emotion']}
- Depression: {text_analysis['depression']['depression_level']}
- LLM Insights: {json.dumps(text_analysis['llm_analysis'], indent=2)}
"""
        
        # Extract dominant video emotion
        intervals = video_emotion.get('intervals', [])
        video_emotions = [i['dominant_emotion'] for i in intervals if 'dominant_emotion' in i]
        dominant_video_emotion = max(set(video_emotions), key=video_emotions.count) if video_emotions else "neutral"
        
        prompt = f"""Analyze this multimodal mental health data:
                    VIDEO ANALYSIS:
                    - Total Intervals: {len(intervals)}
                    - Dominant Emotion: {dominant_video_emotion}
                    - Summary: {json.dumps(video_emotion.get('summary', {}), indent=2)}

                    AUDIO ANALYSIS:
                    - Emotion: {audio_emotion['emotion']} ({audio_emotion['confidence']:.2f})
                    - All Emotions: {json.dumps(audio_emotion['all_emotions'], indent=2)}

                    {text_info}

                    Provide comprehensive assessment as JSON:
                    {{
                        "overall_mental_health_score": 0-100,
                        "risk_level": "low/moderate/high/critical",
                        "confidence": 0.0-1.0,
                        "key_indicators": ["indicator1", "indicator2"],
                        "recommendations": ["rec1", "rec2"],
                        "areas_of_concern": ["concern1", "concern2"],
                        "positive_indicators": ["positive1", "positive2"]
                    }}
                """
        try:
            response = self.text_analyzer.groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are a mental health assessment expert. Provide comprehensive analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Warning: LLM assessment failed: {e}")
            return {
                "overall_mental_health_score": 50,
                "risk_level": "moderate",
                "confidence": 0.5,
                "key_indicators": ["LLM unavailable"],
                "recommendations": ["Consult healthcare professional"],
                "areas_of_concern": ["Unable to complete full analysis"],
                "positive_indicators": []
            }
    
    def _generate_summary(
        self,
        video_emotion: Dict,
        audio_emotion: Dict,
        text_analysis: Dict,
        llm_assessment: Dict
    ) -> Dict:
        intervals = video_emotion.get('intervals', [])
        video_emotions = [i['dominant_emotion'] for i in intervals if 'dominant_emotion' in i]
        dominant_video = max(set(video_emotions), key=video_emotions.count) if video_emotions else "neutral"
        
        return {
            "mental_health_score": llm_assessment['overall_mental_health_score'],
            "risk_level": llm_assessment['risk_level'],
            "confidence": llm_assessment['confidence'],
            "video_emotion": dominant_video,
            "audio_emotion": audio_emotion['emotion'],
            "text_emotion": text_analysis['emotion']['dominant_emotion'],
            "depression_level": text_analysis['depression']['depression_level'],
            "total_intervals": len(intervals)
        }
    
    def save_results(self, result: MultimodalAnalysisResult, output_path: str = "multimodal_analysis.json"):
        with open(output_path, 'w') as f:
            json.dump(asdict(result), f, indent=2)
        print(f"Results saved to {output_path}")



# USAGE
def ask_privacy_preference() -> PrivacyMode:
    print("\n" + "="*60)
    print("PRIVACY SETTINGS")
    print("="*60)
    print("\n1. ANONYMIZED MODE (Recommended)")
    print("   - Removes PII, sends anonymized text")
    print("   - More accurate scoring\n")
    print("2. FULL PRIVACY MODE")
    print("   - Only sends classifier scores")
    print("   - Maximum privacy\n")
    
    while True:
        choice = input("Choose (1/2): ").strip()
        if choice == "1":
            print("\n ANONYMIZED mode\n")
            return PrivacyMode.ANONYMIZED
        elif choice == "2":
            print("\nFULL PRIVACY mode\n")
            return PrivacyMode.FULL_PRIVACY


if __name__ == "__main__":
    pipeline = MultimodalAnalysisPipeline()
    
    video_path = "D:\Coding\MentalApp\S20230010071_SE_VideoResume.mp4"
    
    if os.path.exists(video_path):
        privacy_mode = ask_privacy_preference()
        
        result = pipeline.analyze_video(
            video_path,
            privacy_mode=privacy_mode,
            interval_seconds=5,
            frame_skip=2
        )
        
        print("\nFINAL ASSESSMENT")
        print(f"Mental Health Score: {result.summary['mental_health_score']}/100")
        print(f"Risk Level: {result.summary['risk_level'].upper()}")
        print(f"Confidence: {result.summary['confidence']:.2%}")
        print(f"\nEmotions:")
        print(f"  Video: {result.summary['video_emotion']}")
        print(f"  Audio: {result.summary['audio_emotion']}")
        print(f"  Text: {result.summary['text_emotion']}")
        print(f"  Depression: {result.summary['depression_level']}")
        
        print(f"\nKey Indicators:")
        for ind in result.llm_final_assessment['key_indicators']:
            print(f"  • {ind}")
        
        print(f"\nRecommendations:")
        for rec in result.llm_final_assessment['recommendations']:
            print(f"  • {rec}")
        
        pipeline.save_results(result)
    else:
        print(f"Video not found: {video_path}")