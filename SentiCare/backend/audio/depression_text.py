from transformers import pipeline
from typing import Dict

classifier = pipeline(
    "text-classification",
    model="rafalposwiata/deproberta-large-depression"
)

def analyze_text_depression(text: str) -> Dict:
    result = classifier(text)[0]
    
    # Maps to: not depression, moderate, severe
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