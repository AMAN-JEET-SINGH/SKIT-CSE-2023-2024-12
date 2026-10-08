import spacy
import re
from groq import Groq
from typing import Dict
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Load once at startup
nlp = spacy.load("en_core_web_sm")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def remove_pii(text: str) -> str:
    """Remove personally identifiable information"""
    doc = nlp(text)
    anonymized = text
    
    # Remove names, orgs, locations
    for ent in reversed(doc.ents):
        if ent.label_ in ["PERSON", "ORG", "GPE", "FAC", "LOC"]:
            anonymized = (
                anonymized[:ent.start_char] + 
                "[REDACTED]" + 
                anonymized[ent.end_char:]
            )
    
    # Remove phone/email
    anonymized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', anonymized)
    anonymized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', anonymized)
    
    return anonymized


def analyze_text_emotion(transcript: str) -> Dict:
    """
    Analyze text for emotions and mental health indicators
    """
    try:
        # Anonymize
        safe_text = remove_pii(transcript)
        
        # Analyze with Groq
        prompt = f"""Analyze this text for mental health indicators:

Text: "{safe_text}"

Respond ONLY with valid JSON in this exact format:
{{
    "emotions": ["primary", "secondary"],
    "sentiment": "positive",
    "key_phrases": ["phrase1", "phrase2"],
    "severity": 5
}}

Focus on depression/anxiety indicators like: fatigue, sleep issues, hopelessness, worry, overwhelm."""

        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a JSON API. Respond only with valid JSON, no other text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            "original_text": transcript,
            "anonymized_text": safe_text,
            "emotions": result.get("emotions", []),
            "sentiment": result.get("sentiment", "neutral"),
            "key_phrases": result.get("key_phrases", []),
            "severity": result.get("severity", 5)
        }
        
    except Exception as e:
        raise Exception(f"Text analysis failed: {str(e)}")


if __name__ == "__main__":
    # Example usage
    example_text = """
    I've been feeling so tired lately. It's hard to get out of bed in the morning,
    and I can't sleep properly at night. Work at Acme Corp has been stressful,
    and I just feel like I'm losing control.
    """

    print("Analyzing example text...\n")
    result = analyze_text_emotion(example_text)
    print(json.dumps(result, indent=4))