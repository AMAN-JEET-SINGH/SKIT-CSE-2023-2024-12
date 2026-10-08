"""
Integrated Video Analysis Pipeline
Combines audio extraction, transcription, emotion recognition, and mental health analysis
with privacy controls for multimodal LLM scoring
"""

import os
import json
import subprocess
import shutil
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
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

load_dotenv()


# CONFIG
class PrivacyMode(Enum):
    """Privacy mode for text processing"""
    FULL_PRIVACY = "full_privacy"  # Only send classifier outputs to multimodal LLM
    ANONYMIZED = "anonymized"      # Send anonymized text to multimodal LLM


@dataclass
class AnalysisResult:
    """Complete analysis results"""
    video_path: str
    transcript: Dict
    audio_emotion: Dict
    text_analysis: Dict  # Contains both emotion and depression
    privacy_mode: str
    multimodal_input: Dict  # What gets sent to multimodal LLM
    summary: Dict


# MODULE 1: AUDIO EXTRACTION
class AudioExtractor:
    """Extract audio from video files using FFmpeg"""
    
    @staticmethod
    def check_ffmpeg():
        if not shutil.which("ffmpeg"):
            raise EnvironmentError("ffmpeg not found. Install and add to PATH.")
    
    @staticmethod
    def extract(video_path: str, output_audio: str = "temp_audio.wav") -> str:
        """Extract audio from video"""
        AudioExtractor.check_ffmpeg()
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            output_audio, '-y'
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_audio
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed: {e.stderr.decode()}")


# MODULE 2: TRANSCRIPTION
class Transcriber:
    """Transcribe audio using Deepgram API"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise EnvironmentError("Missing DEEPGRAM_API_KEY")
    
    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe audio file"""
        try:
            with open(audio_path, "rb") as audio:
                buffer_data = audio.read()
            
            url = "https://api.deepgram.com/v1/listen"
            params = {
                "model": "nova-2",
                "smart_format": "true",
                "punctuate": "true",
                "diarize": "false"
            }
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/wav"
            }
            
            response = httpx.post(
                url, params=params, headers=headers,
                content=buffer_data, timeout=60.0
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
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")


# MODULE 3: AUDIO EMOTION RECOGNITION
class AudioEmotionAnalyzer:
    """Analyze emotions from audio waveforms"""
    
    def __init__(self):
        print("Loading audio emotion model...")
        model_name = "superb/wav2vec2-base-superb-er"
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
        self.model = AutoModelForAudioClassification.from_pretrained(model_name)
        print("Audio model loaded!")
    
    def analyze(self, audio_path: str) -> Dict:
        """Analyze emotion from audio"""
        try:
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
                "all_emotions": {
                    emotions[i]: float(probs[i]) for i in range(len(emotions))
                }
            }
        except Exception as e:
            raise Exception(f"Audio emotion analysis failed: {str(e)}")


# MODULE 4: TEXT ANALYSIS (PRIVACY-AWARE)
class TextAnalyzer:
    """
    Unified text analysis with privacy controls
    Handles both local classifiers and LLM-based analysis
    """
    
    def __init__(self):
        print("Loading text analysis models...")
        
        # For PII removal
        self.nlp = spacy.load("en_core_web_sm")
        
        # Local emotion classifier
        self.emotion_classifier = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            return_all_scores=True
        )
        
        # Depression classifier
        self.depression_classifier = pipeline(
            "text-classification",
            model="rafalposwiata/deproberta-large-depression"
        )
        
        # Groq for detailed analysis (only if anonymized mode)
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        print("Text models loaded!")
    
    def remove_pii(self, text: str) -> str:
        """Remove personally identifiable information"""
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
        anonymized = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL]',
            anonymized
        )
        
        return anonymized
    
    def analyze_emotion_local(self, text: str) -> Dict:
        """Local emotion classification"""
        results = self.emotion_classifier(text)[0]
        emotion_scores = {r['label']: r['score'] for r in results}
        dominant = max(results, key=lambda x: x['score'])
        
        return {
            "dominant_emotion": dominant['label'],
            "confidence": dominant['score'],
            "all_emotions": emotion_scores
        }
    
    def analyze_depression_local(self, text: str) -> Dict:
        """Local depression classification"""
        result = self.depression_classifier(text)[0]
        
        severity_map = {
            "not depression": 0,
            "moderate": 5,
            "severe": 9
        }
        
        return {
            "depression_level": result['label'],
            "confidence": result['score'],
            "severity": severity_map.get(result['label'], 0)
        }
    
    def analyze_detailed_llm(self, text: str) -> Dict:
        """Detailed LLM analysis (only for anonymized text)"""
        try:
            prompt = f"""Analyze this text for mental health indicators:
                        Text: "{text}"
                        Respond ONLY with valid JSON:
                        {{
                            "emotions": ["primary", "secondary"],
                            "sentiment": "positive/negative/neutral",
                            "key_phrases": ["phrase1", "phrase2"],
                            "severity": 5
                        }}
                        Focus on: fatigue, sleep issues, hopelessness, worry, overwhelm."""
            
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
        except Exception as e:
            raise Exception(f"LLM analysis failed: {str(e)}")
    
    def analyze(self, text: str, privacy_mode: PrivacyMode) -> Tuple[Dict, str]:
        """
        Complete text analysis respecting privacy mode
        Returns: (analysis_dict, text_for_multimodal)
        """
        # Always run local classifiers
        emotion_result = self.analyze_emotion_local(text)
        depression_result = self.analyze_depression_local(text)
        
        if privacy_mode == PrivacyMode.FULL_PRIVACY:
            # Only send classifier outputs to multimodal LLM
            analysis = {
                "emotion": emotion_result,
                "depression": depression_result,
                "llm_analysis": None,
                "anonymized_text": None
            }
            text_for_multimodal = None  # No text sent
            
        else:  # ANONYMIZED mode
            # Send anonymized text to multimodal LLM
            anonymized = self.remove_pii(text)
            llm_analysis = self.analyze_detailed_llm(anonymized)
            
            analysis = {
                "emotion": emotion_result,
                "depression": depression_result,
                "llm_analysis": llm_analysis,
                "anonymized_text": anonymized
            }
            text_for_multimodal = anonymized
        
        return analysis, text_for_multimodal


# MAIN PIPELINE
class VideoAnalysisPipeline:
    """Complete video analysis pipeline with privacy controls"""
    
    def __init__(self):
        print("\n" + "="*60)
        print("INITIALIZING VIDEO ANALYSIS PIPELINE")
        print("="*60)
        
        self.audio_extractor = AudioExtractor()
        self.transcriber = Transcriber()
        self.audio_emotion = AudioEmotionAnalyzer()
        self.text_analyzer = TextAnalyzer()
        
        print("\nAll modules loaded successfully!\n")
    
    def analyze_video(
        self,
        video_path: str,
        privacy_mode: PrivacyMode = PrivacyMode.ANONYMIZED,
        cleanup: bool = True
    ) -> AnalysisResult:
        """
        Run complete analysis pipeline
        
        Args:
            video_path: Path to video file (your teammate provides this)
            privacy_mode: FULL_PRIVACY (only classifier outputs) or ANONYMIZED (masked text)
            cleanup: Remove temporary audio file
        
        Returns:
            AnalysisResult with all analysis data and multimodal inputs
        """
        print(f"\n{'='*60}")
        print(f"ANALYZING: {video_path}")
        print(f"Privacy Mode: {privacy_mode.value}")
        print(f"{'='*60}\n")
        
        temp_audio = "temp_audio.wav"
        
        try:
            # Step 1: Extract audio from video
            print("Extracting audio from video...")
            self.audio_extractor.extract(video_path, temp_audio)
            print("   Audio extracted\n")
            
            # Step 2: Transcribe audio
            print("Transcribing audio...")
            transcript = self.transcriber.transcribe(temp_audio)
            print(f"   Transcribed ({transcript['confidence']:.2%} confidence)\n")
            
            # Step 3: Audio emotion analysis
            print("Analyzing audio emotions...")
            audio_emotion_result = self.audio_emotion.analyze(temp_audio)
            print(f"   Detected: {audio_emotion_result['emotion']}\n")
            
            # Step 4: Text analysis (privacy-aware)
            print("Analyzing text (privacy-aware)...")
            text_analysis, text_for_multimodal = self.text_analyzer.analyze(
                transcript['text'],
                privacy_mode
            )
            
            if privacy_mode == PrivacyMode.FULL_PRIVACY:
                print("   Full privacy: Only classifier outputs will be sent\n")
            else:
                print("   Anonymized text will be sent to multimodal LLM\n")
            
            # Step 5: Prepare multimodal inputs
            print("Preparing multimodal LLM inputs...")
            multimodal_input = self._prepare_multimodal_input(
                video_path,
                temp_audio,
                audio_emotion_result,
                text_analysis,
                text_for_multimodal,
                privacy_mode
            )
            print("   Multimodal inputs prepared\n")
            
            # Generate summary
            summary = self._generate_summary(
                audio_emotion_result,
                text_analysis
            )
            
            result = AnalysisResult(
                video_path=video_path,
                transcript=transcript,
                audio_emotion=audio_emotion_result,
                text_analysis=text_analysis,
                privacy_mode=privacy_mode.value,
                multimodal_input=multimodal_input,
                summary=summary
            )
            
            print(f"{'='*60}")
            print("ANALYSIS COMPLETE")
            print(f"{'='*60}\n")
            
            return result
            
        finally:
            if cleanup and os.path.exists(temp_audio):
                os.remove(temp_audio)
    
    def _prepare_multimodal_input(
        self,
        video_path: str,
        audio_path: str,
        audio_emotion: Dict,
        text_analysis: Dict,
        text_for_multimodal: Optional[str],
        privacy_mode: PrivacyMode
    ) -> Dict:
        """
        Prepare inputs for multimodal LLM scoring
        Video analysis will be added by your teammate
        """
        multimodal_input = {
            "video_path": video_path,  # Your teammate's video analysis hooks in here
            "audio_path": audio_path,
            "audio_emotion": audio_emotion,
        }
        
        if privacy_mode == PrivacyMode.FULL_PRIVACY:
            # Only send classifier outputs
            multimodal_input["text_features"] = {
                "emotion": text_analysis["emotion"]["dominant_emotion"],
                "emotion_confidence": text_analysis["emotion"]["confidence"],
                "depression_level": text_analysis["depression"]["depression_level"],
                "depression_confidence": text_analysis["depression"]["confidence"],
                "depression_severity": text_analysis["depression"]["severity"]
            }
            multimodal_input["text_content"] = None
        else:
            # Send anonymized text + features
            multimodal_input["text_features"] = {
                "emotion": text_analysis["emotion"]["dominant_emotion"],
                "depression_level": text_analysis["depression"]["depression_level"],
                "llm_insights": text_analysis["llm_analysis"]
            }
            multimodal_input["text_content"] = text_for_multimodal
        
        return multimodal_input
    
    def _generate_summary(self, audio_emotion: Dict, text_analysis: Dict) -> Dict:
        """Generate analysis summary"""
        depression = text_analysis["depression"]
        emotion = text_analysis["emotion"]
        
        risk_factors = [
            depression['severity'],
            5 if emotion['dominant_emotion'] in ['sadness', 'fear', 'anger'] else 0,
            5 if audio_emotion['emotion'] in ['sad', 'angry'] else 0
        ]
        overall_risk = sum(risk_factors) / len(risk_factors)
        
        risk_level = "Low" if overall_risk < 3 else "Moderate" if overall_risk < 6 else "High"
        
        return {
            "overall_risk_score": round(overall_risk, 2),
            "risk_level": risk_level,
            "audio_emotion": audio_emotion['emotion'],
            "text_emotion": emotion['dominant_emotion'],
            "depression_level": depression['depression_level'],
        }
    
    def save_results(self, result: AnalysisResult, output_path: str = "analysis_results.json"):
        """Save results to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(asdict(result), f, indent=2)
        print(f"Results saved to {output_path}")


# USAGE EXAMPLE
def ask_privacy_preference() -> PrivacyMode:
    """Ask user about privacy preference"""
    print("\n" + "="*60)
    print("PRIVACY SETTINGS")
    print("="*60)
    print("\nYour transcript will be analyzed for mental health indicators.")
    print("\nWe can send data to our multimodal AI in two ways:\n")
    print("1. ANONYMIZED MODE (Recommended)")
    print("   - Removes names, locations, emails, phone numbers")
    print("   - Sends anonymized text to AI for detailed analysis")
    print("   - More accurate multimodal scoring\n")
    print("2. FULL PRIVACY MODE")
    print("   - NO text sent to multimodal AI")
    print("   - Only sends classifier scores (emotion, depression level)")
    print("   - Maximum privacy, slightly less accurate\n")
    
    while True:
        choice = input("Choose mode (1 for Anonymized, 2 for Full Privacy): ").strip()
        if choice == "1":
            print("\nUsing ANONYMIZED mode - PII will be removed\n")
            return PrivacyMode.ANONYMIZED
        elif choice == "2":
            print("\nUsing FULL PRIVACY mode - No text will be sent\n")
            return PrivacyMode.FULL_PRIVACY
        print("Invalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    # Initialize pipeline
    pipeline = VideoAnalysisPipeline()
    
    # Video provided by teammate
    video_path = "S20230010071_SE_VideoResume.mp4"
    
    if os.path.exists(video_path):
        # Ask user about privacy
        privacy_mode = ask_privacy_preference()
        
        # Run analysis
        result = pipeline.analyze_video(video_path, privacy_mode=privacy_mode)
        
        # Print summary
        print("\nSUMMARY")
        print(f"Risk Level: {result.summary['risk_level']}")
        print(f"Risk Score: {result.summary['overall_risk_score']}/10")
        print(f"Audio Emotion: {result.summary['audio_emotion']}")
        print(f"Text Emotion: {result.summary['text_emotion']}")
        print(f"Depression: {result.summary['depression_level']}")
        
        # Show what's being sent to multimodal LLM
        print(f"\nMultimodal LLM will receive:")
        print(f"   - Video features (from teammate's analysis)")
        print(f"   - Audio emotion: {result.audio_emotion['emotion']}")
        if result.multimodal_input['text_content']:
            print(f"   - Anonymized text: Yes")
        else:
            print(f"   - Text classifiers only (no transcript)")
        
        # Save results
        pipeline.save_results(result)
    else:
        print(f"Video file not found: {video_path}")