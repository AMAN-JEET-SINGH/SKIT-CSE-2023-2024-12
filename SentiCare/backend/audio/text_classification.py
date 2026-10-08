from transformers import pipeline
from typing import Dict

# Load model locally
print("Loading emotion classifier...")
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=True
)
print("Model loaded!\n")

def analyze_text_emotion(text: str) -> Dict:
    """Analyze text emotions locally"""
    results = emotion_classifier(text)[0]
    
    # Convert to dict
    emotion_scores = {r['label']: r['score'] for r in results}
    
    # Get top emotions (score > 0.1)
    emotions = [r['label'] for r in results if r['score'] > 0.1]
    emotions.sort(key=lambda x: emotion_scores[x], reverse=True)
    
    return {
        "emotions": emotions,
        "emotion_scores": emotion_scores,
        "dominant_emotion": max(results, key=lambda x: x['score'])['label']
    }

# Test
if __name__ == "__main__":
    text = "I'm feeling happy and optimistic about my future"
    result = analyze_text_emotion(text)
    
    print(f"Dominant: {result['dominant_emotion']}\n")
    print("All scores:")
    for emotion, score in result['emotion_scores'].items():
        print(f"  {emotion:>10}: {score:.3f}")