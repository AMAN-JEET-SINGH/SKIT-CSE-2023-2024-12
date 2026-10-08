"""
Integrated Multimodal Analysis Pipeline with Multiprocessing
Process 1: Video emotion detection
Process 2: Audio extraction + transcription + audio emotion + text analysis
Final: LLM assessment combining both
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
from multiprocessing import Process, Queue
# from faster_whisper import WhisperModel
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
    video_emotion: Dict
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
    """
    Uses SpeechBrain's fine-tuned wav2vec2 model trained specifically on IEMOCAP
    Achieves 78.7% accuracy on IEMOCAP test set (vs 67% for SUPERB model)
    """
    def __init__(self):
        # Install SpeechBrain first: pip install speechbrain
        try:
            from speechbrain.inference.interfaces import foreign_class
            
            # Load the SpeechBrain wav2vec2 model for IEMOCAP
            self.classifier = foreign_class(
                source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
                pymodule_file="custom_interface.py",
                classname="CustomEncoderWav2vec2Classifier"
            )
            self.use_speechbrain = True
            self.emotions = ['neu', 'hap', 'sad', 'ang']  # IEMOCAP labels
            self.emotion_map = {
                'neu': 'neutral',
                'hap': 'happy',
                'sad': 'sad',
                'ang': 'angry'
            }
        except ImportError:
            print("⚠️ SpeechBrain not installed. Falling back to SUPERB model (67% accuracy)")
            print("For best performance, install: pip install speechbrain")
            self.use_speechbrain = False
            
            # Fallback to SUPERB model
            from transformers import AutoModelForAudioClassification, AutoFeatureExtractor
            model_name = "superb/wav2vec2-base-superb-er"
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
            self.model = AutoModelForAudioClassification.from_pretrained(model_name)
            self.emotions = ['neutral', 'happy', 'sad', 'angry']
    
    def analyze(self, audio_path: str) -> Dict:
        if self.use_speechbrain:
            # Use SpeechBrain model (78.7% accuracy)
            out_prob, score, index, text_lab = self.classifier.classify_file(audio_path)
            
            # Convert to probabilities dictionary
            emotion_label = text_lab[0]  # e.g., 'ang', 'hap', etc.
            mapped_emotion = self.emotion_map.get(emotion_label, emotion_label)
            
            return {
                "emotion": mapped_emotion,
                "confidence": float(score[0]),
                "all_emotions": {
                    self.emotion_map[self.emotions[i]]: float(out_prob[0][i])
                    for i in range(len(self.emotions))
                },
                "model_used": "speechbrain_wav2vec2_iemocap",
                "accuracy": "78.7%"
            }
        else:
            # Fallback to SUPERB model (67% accuracy)
            import torchaudio
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
            predicted_idx = torch.argmax(probs).item()
            
            return {
                "emotion": self.emotions[predicted_idx],
                "confidence": float(probs[predicted_idx]),
                "all_emotions": {self.emotions[i]: float(probs[i]) for i in range(len(self.emotions))},
                "model_used": "superb_wav2vec2_base",
                "accuracy": "~67%"
            }

# Load with GPU acceleration
# model = WhisperModel(model_size, device="cuda", compute_type="float16")

# t0 = time.time()
# segments, info = model.transcribe("your_audio.wav", beam_size=5, vad_filter=True)
# print(f"→ {info.duration:.1f}s audio in {time.time() - t0:.1f}s")

# for seg in segments:
#     print(f"[{seg.start:.2f}–{seg.end:.2f}] {seg.text}")

# TEXT ANALYSIS
class TextAnalyzer:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.emotion_classifier = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            return_all_scores=True
        )
        self.depression_classifier = pipeline(
            "text-classification",
            model="rafalposwiata/deproberta-large-depression",
            return_all_scores=True  # Get all scores instead of just top
        )
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
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
            "all_emotions": emotion_scores  # Full softmax distribution
        }
    
    def analyze_depression_local(self, text: str) -> Dict:
        results = self.depression_classifier(text)[0]
        depression_scores = {r['label']: r['score'] for r in results}
        dominant = max(results, key=lambda x: x['score'])
        
        severity_map = {"not depression": 0, "moderate": 5, "severe": 9}
        
        return {
            "depression_level": dominant['label'],
            "confidence": dominant['score'],
            "severity": severity_map.get(dominant['label'], 0),
            "all_scores": depression_scores  # Full softmax distribution
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



# PARALLEL PROCESSING FUNCTIONS
def process_video_emotions(video_path: str, interval_seconds: int, frame_skip: int, result_queue: Queue):
    """Process 1: Video emotion analysis"""
    try:
        print("[Process 1] Starting video emotion analysis...")
        detector = EmotionDetector()
        result = detector.analyze_video_by_intervals_optimized(
            video_path=video_path,
            interval_seconds=interval_seconds,
            frame_skip=frame_skip
        )
        print(f"[Process 1] Video analysis complete ({len(result.get('intervals', []))} intervals)")
        result_queue.put(("video", result))
    except Exception as e:
        print(f"[Process 1] Error: {e}")
        result_queue.put(("video", {"error": str(e)}))


def process_audio_text(video_path: str, privacy_mode: PrivacyMode, temp_audio: str, result_queue: Queue):
    """Process 2: Audio extraction + transcription + audio emotion + text analysis"""
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    text_analyzer = TextAnalyzer()
    text_analyzer.groq_client = groq_client
    try:
        print("[Process 2] Starting audio/text pipeline...")
        
        extractor = AudioExtractor()
        extractor.extract(video_path, temp_audio)
        
        print("[Process 2] Transcribing audio...")
        transcriber = Transcriber()
        transcript = transcriber.transcribe(temp_audio)
        print(f"[Process 2] Transcription completed with confidence {transcript['confidence']:.2%}")
        
        print("[Process 2] Running audio emotion analysis...")
        audio_analyzer = AudioEmotionAnalyzer()
        audio_emotion = audio_analyzer.analyze(temp_audio)
        print(f"[Process 2] Audio emotion detected: {audio_emotion['emotion']}")
        
        print("[Process 2] Running text analysis...")
        text_analyzer = TextAnalyzer()
        text_analysis, text_for_multimodal = text_analyzer.analyze(
            transcript['text'], privacy_mode
        )
        
        print("[Process 2] Audio/text analysis complete.")
        result_queue.put(("audio_text", {
            "transcript": transcript,
            "audio_emotion": audio_emotion,
            "text_analysis": text_analysis,
            "text_for_multimodal": text_for_multimodal
        }))
    except Exception as e:
        print(f"[Process 2] Error: {e}")
        result_queue.put(("audio_text", {"error": str(e)}))



# MULTIMODAL PIPELINE
class MultimodalAnalysisPipeline:
    def __init__(self):
        print("\n" + "="*60)
        print("INITIALIZING MULTIMODAL ANALYSIS PIPELINE (MULTIPROCESSING)")
        print("="*60)
        print("\nPipeline initialized successfully.\n")
    
    def analyze_video(
        self,
        video_path: str,
        privacy_mode: PrivacyMode = PrivacyMode.ANONYMIZED,
        interval_seconds: int = 5,
        frame_skip: int = 2,
        cleanup: bool = True
    ) -> MultimodalAnalysisResult:
        print(f"\n{'='*60}")
        print(f"ANALYZING VIDEO: {video_path}")
        print(f"Privacy Mode: {privacy_mode.value}")
        print(f"Frame Skip: {frame_skip} | Interval: {interval_seconds}s")
        print(f"Processing Mode: Parallel")
        print(f"{'='*60}\n")
        
        temp_audio = f"temp_audio_{os.getpid()}.wav"
        result_queue = Queue()
        
        try:
            p1 = Process(target=process_video_emotions, 
                        args=(video_path, interval_seconds, frame_skip, result_queue))
            p2 = Process(target=process_audio_text, 
                        args=(video_path, privacy_mode, temp_audio, result_queue))
            
            print("Starting parallel processing...")
            p1.start()
            p2.start()
            
            results = {}
            for _ in range(2):
                result_type, data = result_queue.get()
                results[result_type] = data
            
            p1.join()
            p2.join()
            
            print("\nBoth processes completed.\n")
            
            if "error" in results.get("video", {}):
                raise Exception(f"Video processing failed: {results['video']['error']}")
            if "error" in results.get("audio_text", {}):
                raise Exception(f"Audio/text processing failed: {results['audio_text']['error']}")
            
            video_emotion_result = results["video"]
            audio_text_results = results["audio_text"]
            transcript = audio_text_results["transcript"]
            audio_emotion_result = audio_text_results["audio_emotion"]
            text_analysis = audio_text_results["text_analysis"]
            text_for_multimodal = audio_text_results["text_for_multimodal"]
            
            print("Generating multimodal LLM assessment...")
            llm_assessment = self._get_llm_assessment(
                video_emotion_result,
                audio_emotion_result,
                text_analysis,
                text_for_multimodal,
                privacy_mode
            )
            print("Multimodal assessment complete.\n")
            
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
        """
        Generate LLM assessment with FULL SOFTMAX DISTRIBUTIONS for all modalities
        """
        
        # Extract video emotion distribution from intervals
        intervals = video_emotion.get('intervals', [])
        video_emotions = [i['dominant_emotion'] for i in intervals if 'dominant_emotion' in i]
        dominant_video_emotion = max(set(video_emotions), key=video_emotions.count) if video_emotions else "neutral"
        
        # Calculate average emotion distribution across video intervals
        video_emotion_distribution = {}
        if intervals:
            emotion_counts = {}
            for interval in intervals:
                if 'dominant_emotion' in interval:
                    emotion = interval['dominant_emotion']
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            total = len(intervals)
            video_emotion_distribution = {
                emotion: count / total for emotion, count in emotion_counts.items()
            }
        
        # Build text analysis section with full distributions
        if privacy_mode == PrivacyMode.FULL_PRIVACY:
            text_info = f"""
TEXT ANALYSIS (Full Classifier Distributions):
- Emotion Distribution (Softmax):
{json.dumps(text_analysis['emotion']['all_emotions'], indent=4)}
- Dominant Emotion: {text_analysis['emotion']['dominant_emotion']} ({text_analysis['emotion']['confidence']:.2f})

- Depression Distribution (Softmax):
{json.dumps(text_analysis['depression']['all_scores'], indent=4)}
- Depression Level: {text_analysis['depression']['depression_level']} ({text_analysis['depression']['confidence']:.2f})
- Severity Score: {text_analysis['depression']['severity']}/10
"""
        else:
            text_info = f"""
TEXT ANALYSIS (Full Classifier Distributions + Content):
- Transcript: "{text_for_multimodal}"

- Emotion Distribution (Softmax):
{json.dumps(text_analysis['emotion']['all_emotions'], indent=4)}
- Dominant Emotion: {text_analysis['emotion']['dominant_emotion']} ({text_analysis['emotion']['confidence']:.2f})

- Depression Distribution (Softmax):
{json.dumps(text_analysis['depression']['all_scores'], indent=4)}
- Depression Level: {text_analysis['depression']['depression_level']} ({text_analysis['depression']['confidence']:.2f})
- Severity Score: {text_analysis['depression']['severity']}/10

- LLM Detailed Analysis:
{json.dumps(text_analysis['llm_analysis'], indent=4)}
"""
        
        prompt = f"""Analyze this multimodal mental health data with FULL PROBABILITY DISTRIBUTIONS:

VIDEO ANALYSIS:
- Total Intervals Analyzed: {len(intervals)}
- Dominant Emotion: {dominant_video_emotion}
- Emotion Distribution Across Video:
{json.dumps(video_emotion_distribution, indent=4)}
- Detailed Summary: {json.dumps(video_emotion.get('summary', {}), indent=2)}

AUDIO ANALYSIS (Full Softmax Distribution):
- Audio Emotion Distribution:
{json.dumps(audio_emotion['all_emotions'], indent=4)}
- Dominant Audio Emotion: {audio_emotion['emotion']} ({audio_emotion['confidence']:.2f})

{text_info}

**IMPORTANT**: You have been provided with COMPLETE probability distributions (softmax outputs) from all classifiers.
Use these full distributions to:
1. Assess confidence and uncertainty in predictions
2. Identify mixed emotional states
3. Detect subtle patterns across modalities
4. Provide more nuanced risk assessment

Provide comprehensive assessment as JSON with SPECIFIC SCORES and DIRECT recommendations:
{{
    "overall_mental_health_score": 0-100,
    "depression_score": 0-100,
    "anxiety_score": 0-100,
    "stress_score": 0-100,
    "risk_level": "low/moderate/high/critical",
    "confidence": 0.0-1.0,
    "key_indicators": ["indicator1", "indicator2"],
    "recommendations": ["You should...", "Consider...", "Try..."],
    "areas_of_concern": ["concern1", "concern2"],
    "positive_indicators": ["positive1", "positive2"],
    "distribution_insights": "Analysis of probability distributions and mixed states"
}}

CRITICAL: Write ALL recommendations in SECOND PERSON (address the person directly as 'you', not 'they' or 'the user').
Examples:
- Good: "You should consider speaking with a therapist"
- Bad: "The user should consider speaking with a therapist"
"""
        
        try:
            groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are a mental health assessment expert with expertise in interpreting classifier probability distributions. Provide comprehensive analysis leveraging full softmax outputs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"LLM assessment failed: {e}")
            return {
                "overall_mental_health_score": 50,
                "risk_level": "moderate",
                "confidence": 0.5,
                "key_indicators": ["LLM unavailable"],
                "recommendations": ["Consult healthcare professional"],
                "areas_of_concern": ["Unable to complete full analysis"],
                "positive_indicators": [],
                "distribution_insights": "Full distribution analysis unavailable due to LLM error"
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
            "depression_score": llm_assessment.get('depression_score', 0),  # NEW
            "anxiety_score": llm_assessment.get('anxiety_score', 0),        # NEW
            "stress_score": llm_assessment.get('stress_score', 0),          # NEW
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
    print("   - Removes PII, sends anonymized text + full distributions")
    print("   - More accurate scoring\n")
    print("2. FULL PRIVACY MODE")
    print("   - Only sends classifier probability distributions")
    print("   - Maximum privacy\n")
    
    while True:
        choice = input("Choose (1/2): ").strip()
        if choice == "1":
            print("\nSelected: ANONYMIZED mode\n")
            return PrivacyMode.ANONYMIZED
        elif choice == "2":
            print("\nSelected: FULL PRIVACY mode\n")
            return PrivacyMode.FULL_PRIVACY


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    
    pipeline = MultimodalAnalysisPipeline()
    
    video_path = "D:\\Coding\\MentalApp\\rito.mp4"
    
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