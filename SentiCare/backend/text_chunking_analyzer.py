"""
Smart Text Chunking Analyzer for Long Inputs
Handles text longer than model token limits (512 tokens for DistilRoBERTa)
Provides chunk-wise analysis and intelligent aggregation
"""

from typing import Dict, List, Tuple
from transformers import AutoTokenizer, pipeline
import numpy as np


class ChunkedTextAnalyzer:
    """
    Analyzes long text by chunking and aggregating results
    Handles emotion and depression classification with token limits
    """
    
    def __init__(self):
        # Load tokenizer to count tokens accurately
        self.emotion_tokenizer = AutoTokenizer.from_pretrained(
            "j-hartmann/emotion-english-distilroberta-base"
        )
        self.depression_tokenizer = AutoTokenizer.from_pretrained(
            "rafalposwiata/deproberta-large-depression"
        )
        
        # Load classifiers
        self.emotion_classifier = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            return_all_scores=True
        )
        self.depression_classifier = pipeline(
            "text-classification",
            model="rafalposwiata/deproberta-large-depression",
            return_all_scores=True
        )
        
        # Token limits (with safety margin)
        self.emotion_max_tokens = 480  # 512 - 32 for special tokens
        self.depression_max_tokens = 480
        
        print("Chunked Text Analyzer initialized")
        print(f"Max tokens per chunk: {self.emotion_max_tokens}")
    
    def chunk_text_by_sentences(self, text: str, max_tokens: int, tokenizer) -> List[str]:
        """
        Split text into chunks at sentence boundaries while respecting token limits
        
        Args:
            text: Input text
            max_tokens: Maximum tokens per chunk
            tokenizer: Tokenizer to use for counting
        
        Returns:
            List of text chunks
        """
        import re
        
        # Split into sentences (handles ., !, ?, and newlines)
        sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            # Tokenize sentence
            sentence_tokens = tokenizer.encode(sentence, add_special_tokens=False)
            sentence_token_count = len(sentence_tokens)
            
            # If single sentence exceeds limit, split it further by words
            if sentence_token_count > max_tokens:
                # If current chunk has content, save it
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split long sentence by words
                words = sentence.split()
                word_chunk = []
                word_tokens = 0
                
                for word in words:
                    word_token_count = len(tokenizer.encode(word, add_special_tokens=False))
                    
                    if word_tokens + word_token_count > max_tokens:
                        if word_chunk:
                            chunks.append(' '.join(word_chunk))
                        word_chunk = [word]
                        word_tokens = word_token_count
                    else:
                        word_chunk.append(word)
                        word_tokens += word_token_count
                
                if word_chunk:
                    chunks.append(' '.join(word_chunk))
            
            # If adding sentence would exceed limit, start new chunk
            elif current_tokens + sentence_token_count > max_tokens:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_token_count
            
            # Otherwise, add to current chunk
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_token_count
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def analyze_emotion_chunked(self, text: str) -> Dict:
        """
        Analyze emotion with automatic chunking for long texts
        NOW PRESERVES ALL CHUNK DISTRIBUTIONS FOR LLM
        
        Returns:
            {
                'dominant_emotion': str,
                'confidence': float,
                'all_emotions': dict,  # Aggregated for compatibility
                'chunks_analyzed': int,
                'chunk_distributions': list,  # NEW: Individual chunk softmax outputs
                'chunk_details': list
            }
        """
        # Check if chunking is needed
        tokens = self.emotion_tokenizer.encode(text, add_special_tokens=True)
        total_tokens = len(tokens)
        
        if total_tokens <= self.emotion_max_tokens:
            # Text is short enough, analyze directly
            results = self.emotion_classifier(text)[0]
            emotion_scores = {r['label']: r['score'] for r in results}
            dominant = max(results, key=lambda x: x['score'])
            
            return {
                'dominant_emotion': dominant['label'],
                'confidence': dominant['score'],
                'all_emotions': emotion_scores,
                'chunks_analyzed': 1,
                'total_tokens': total_tokens,
                'chunking_applied': False,
                'chunk_distributions': [emotion_scores]  # Single distribution
            }
        
        # Text is too long, apply chunking
        print(f"Text too long ({total_tokens} tokens). Applying chunking...")
        
        chunks = self.chunk_text_by_sentences(
            text, 
            self.emotion_max_tokens, 
            self.emotion_tokenizer
        )
        
        print(f"Split into {len(chunks)} chunks")
        
        # Analyze each chunk and PRESERVE individual distributions
        chunk_results = []
        chunk_distributions = []  # NEW: Store all distributions
        
        for i, chunk in enumerate(chunks):
            chunk_token_count = len(self.emotion_tokenizer.encode(chunk, add_special_tokens=True))
            print(f"  Chunk {i+1}: {chunk_token_count} tokens, preview: {chunk[:50]}...")
            
            results = self.emotion_classifier(chunk)[0]
            emotion_scores = {r['label']: r['score'] for r in results}
            chunk_results.append(emotion_scores)
            
            # Store full distribution with metadata
            chunk_distributions.append({
                'chunk_index': i + 1,
                'chunk_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk,
                'token_count': chunk_token_count,
                'distribution': emotion_scores,
                'dominant': max(emotion_scores.items(), key=lambda x: x[1])[0]
            })
        
        # Aggregate for overall statistics (backward compatibility)
        chunk_lengths = [len(chunk) for chunk in chunks]
        total_length = sum(chunk_lengths)
        weights = [length / total_length for length in chunk_lengths]
        
        aggregated_emotions = {}
        emotion_labels = chunk_results[0].keys()
        
        for emotion in emotion_labels:
            weighted_sum = sum(
                chunk_result[emotion] * weight 
                for chunk_result, weight in zip(chunk_results, weights)
            )
            aggregated_emotions[emotion] = weighted_sum
        
        dominant_emotion = max(aggregated_emotions.items(), key=lambda x: x[1])
        
        return {
            'dominant_emotion': dominant_emotion[0],
            'confidence': dominant_emotion[1],
            'all_emotions': aggregated_emotions,  # For compatibility
            'chunks_analyzed': len(chunks),
            'total_tokens': total_tokens,
            'chunking_applied': True,
            'chunk_distributions': chunk_distributions,  # NEW: All individual distributions
            'chunk_details': [
                {
                    'chunk_num': i + 1,
                    'length': len(chunk),
                    'tokens': len(self.emotion_tokenizer.encode(chunk, add_special_tokens=True)),
                    'dominant': max(scores.items(), key=lambda x: x[1])[0],
                    'preview': chunk[:80] + '...' if len(chunk) > 80 else chunk
                }
                for i, (chunk, scores) in enumerate(zip(chunks, chunk_results))
            ]
        }
    
    def analyze_depression_chunked(self, text: str) -> Dict:
        """
        Analyze depression with automatic chunking for long texts
        NOW PRESERVES ALL CHUNK DISTRIBUTIONS FOR LLM
        
        Returns:
            {
                'depression_level': str,
                'confidence': float,
                'severity': int,
                'all_scores': dict,
                'chunks_analyzed': int,
                'chunk_distributions': list,  # NEW: Individual chunk softmax outputs
                'chunk_details': list
            }
        """
        # Check if chunking is needed
        tokens = self.depression_tokenizer.encode(text, add_special_tokens=True)
        total_tokens = len(tokens)
        
        if total_tokens <= self.depression_max_tokens:
            # Text is short enough, analyze directly
            results = self.depression_classifier(text)[0]
            depression_scores = {r['label']: r['score'] for r in results}
            dominant = max(results, key=lambda x: x['score'])
            
            severity_map = {"not depression": 0, "moderate": 5, "severe": 9}
            
            return {
                'depression_level': dominant['label'],
                'confidence': dominant['score'],
                'severity': severity_map.get(dominant['label'], 0),
                'all_scores': depression_scores,
                'chunks_analyzed': 1,
                'total_tokens': total_tokens,
                'chunking_applied': False,
                'chunk_distributions': [depression_scores]  # Single distribution
            }
        
        # Text is too long, apply chunking
        print(f"Text too long ({total_tokens} tokens). Applying chunking for depression analysis...")
        
        chunks = self.chunk_text_by_sentences(
            text, 
            self.depression_max_tokens, 
            self.depression_tokenizer
        )
        
        print(f"Split into {len(chunks)} chunks")
        
        # Analyze each chunk and PRESERVE individual distributions
        chunk_results = []
        chunk_distributions = []  # NEW
        
        for i, chunk in enumerate(chunks):
            results = self.depression_classifier(chunk)[0]
            depression_scores = {r['label']: r['score'] for r in results}
            chunk_results.append(depression_scores)
            
            # Store full distribution with metadata
            chunk_distributions.append({
                'chunk_index': i + 1,
                'chunk_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk,
                'distribution': depression_scores,
                'dominant': max(depression_scores.items(), key=lambda x: x[1])[0]
            })
        
        # Aggregate using WORST-CASE approach for depression (more conservative)
        # Take the highest severity across chunks
        severity_map = {"not depression": 0, "moderate": 5, "severe": 9}
        reverse_severity_map = {0: "not depression", 5: "moderate", 9: "severe"}
        
        max_severity = 0
        max_severity_scores = None
        
        for scores in chunk_results:
            dominant_label = max(scores.items(), key=lambda x: x[1])[0]
            severity = severity_map.get(dominant_label, 0)
            
            if severity > max_severity:
                max_severity = severity
                max_severity_scores = scores
        
        # Use weighted average for all_scores
        chunk_lengths = [len(chunk) for chunk in chunks]
        total_length = sum(chunk_lengths)
        weights = [length / total_length for length in chunk_lengths]
        
        aggregated_scores = {}
        score_labels = chunk_results[0].keys()
        
        for label in score_labels:
            weighted_sum = sum(
                chunk_result[label] * weight 
                for chunk_result, weight in zip(chunk_results, weights)
            )
            aggregated_scores[label] = weighted_sum
        
        dominant_label = reverse_severity_map[max_severity]
        dominant_confidence = max_severity_scores[dominant_label]
        
        return {
            'depression_level': dominant_label,
            'confidence': dominant_confidence,
            'severity': max_severity,
            'all_scores': aggregated_scores,  # For compatibility
            'chunks_analyzed': len(chunks),
            'total_tokens': total_tokens,
            'chunking_applied': True,
            'aggregation_method': 'worst-case (most conservative)',
            'chunk_distributions': chunk_distributions,  # NEW: All individual distributions
            'chunk_details': [
                {
                    'chunk_num': i + 1,
                    'depression_level': max(scores.items(), key=lambda x: x[1])[0],
                    'severity': severity_map.get(max(scores.items(), key=lambda x: x[1])[0], 0),
                    'preview': chunks[i][:80] + '...' if len(chunks[i]) > 80 else chunks[i]
                }
                for i, scores in enumerate(chunk_results)
            ]
        }


# Test function
if __name__ == "__main__":
    analyzer = ChunkedTextAnalyzer()
    
    # Test with short text
    short_text = "I'm feeling really happy today!"
    print("\n=== SHORT TEXT TEST ===")
    print(f"Text: {short_text}")
    emotion_result = analyzer.analyze_emotion_chunked(short_text)
    print(f"Result: {emotion_result}")
    
    # Test with long text
    long_text = " ".join([
        "I've been feeling really down lately. Every morning I wake up and just don't want to get out of bed.",
        "Work has been incredibly stressful and I can't seem to focus on anything.",
        "My relationships are suffering because I just don't have the energy to maintain them.",
        "I used to love going out with friends but now I just make excuses to stay home.",
        "Sleep is terrible - either I can't fall asleep or I wake up multiple times during the night.",
        "Food doesn't taste good anymore and I've lost my appetite.",
        "I keep thinking about all my failures and mistakes from the past.",
        "It feels like nothing will ever get better and I'm stuck in this dark place.",
        "Sometimes I wonder if anyone would even notice if I just disappeared.",
        "I've tried to be positive but it just feels fake and exhausting."
    ] * 20)  # Repeat to exceed token limit
    
    print("\n=== LONG TEXT TEST ===")
    print(f"Text length: {len(long_text)} characters")
    emotion_result = analyzer.analyze_emotion_chunked(long_text)
    print(f"\nEmotion Analysis:")
    print(f"  Chunks: {emotion_result['chunks_analyzed']}")
    print(f"  Tokens: {emotion_result['total_tokens']}")
    print(f"  Dominant: {emotion_result['dominant_emotion']} ({emotion_result['confidence']:.2f})")
    
    depression_result = analyzer.analyze_depression_chunked(long_text)
    print(f"\nDepression Analysis:")
    print(f"  Chunks: {depression_result['chunks_analyzed']}")
    print(f"  Level: {depression_result['depression_level']} ({depression_result['confidence']:.2f})")
    print(f"  Severity: {depression_result['severity']}/10")
