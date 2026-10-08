from transformers import AutoModelForAudioClassification, AutoFeatureExtractor
import torch
import torchaudio
from typing import Dict

print("🔄 Loading model...")
model_name = "superb/wav2vec2-base-superb-er"
feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
model = AutoModelForAudioClassification.from_pretrained(model_name)
print("✅ Model loaded!\n")

def analyze_audio_emotion(audio_path: str) -> Dict:
    try:
        waveform, sample_rate = torchaudio.load(audio_path)
        
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
        
        inputs = feature_extractor(waveform.squeeze().numpy(), sampling_rate=16000, return_tensors="pt")
        
        with torch.no_grad():
            logits = model(**inputs).logits
        
        probs = torch.nn.functional.softmax(logits, dim=-1)[0]
        
        emotion_probs = {
            'neutral': float(probs[0]),
            'happy': float(probs[1]),
            'sad': float(probs[2]),
            'angry': float(probs[3])
        }
        
        emotions = ['neutral', 'happy', 'sad', 'angry']
        predicted_idx = torch.argmax(probs).item()
        
        return {
            "emotion": emotions[predicted_idx],
            "emotion_probs": emotion_probs,
            "confidence": float(probs[predicted_idx])
        }
    except Exception as e:
        raise Exception(f"Failed: {str(e)}")

if __name__ == "__main__":
    import os
    audio_path = "temp_audio.wav"
    
    if os.path.exists(audio_path):
        result = analyze_audio_emotion(audio_path)
        print(f"Emotion: {result['emotion']} ({result['confidence']:.3f})\n")
        for k, v in result["emotion_probs"].items():
            print(f"  {k:>8}: {v:.3f}")