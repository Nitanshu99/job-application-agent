"""
Text processing utilities for job automation system.

Provides functions for cleaning, processing, and analyzing text content
including job descriptions, resumes, and cover letters.
"""

import re
import string
from typing import List, Optional
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Load spaCy model for advanced text processing
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # If model not found, use basic processing
    nlp = None

# Initialize NLTK components
stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))


def clean_text(text: str, remove_special_chars: bool = False) -> str:
    """
    Clean and normalize text by removing extra whitespace and optionally special characters.
    
    Args:
        text: Input text to clean
        remove_special_chars: Whether to remove special characters
        
    Returns:
        Cleaned text string
    """
    if not isinstance(text, str):
        return ""
    
    # Remove multiple whitespaces, newlines, and tabs
    cleaned = re.sub(r'\s+', ' ', text)
    
    # Remove special characters if requested
    if remove_special_chars:
        # Keep alphanumeric characters and basic punctuation
        cleaned = re.sub(r'[^a-zA-Z0-9\s\.\,\!\?]', '', cleaned)
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def extract_keywords(text: str, limit: int = 10) -> List[str]:
    """
    Extract relevant keywords from text using TF-IDF.
    
    Args:
        text: Input text to extract keywords from
        limit: Maximum number of keywords to return
        
    Returns:
        List of extracted keywords
    """
    if not text or not isinstance(text, str):
        return []
    
    # Clean and preprocess text
    cleaned_text = clean_text(text.lower())
    
    # Use spaCy if available for better keyword extraction
    if nlp:
        doc = nlp(cleaned_text)
        # Extract noun phrases and named entities
        keywords = []
        
        # Get noun phrases
        noun_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3]
        keywords.extend(noun_phrases)
        
        # Get named entities (excluding PERSON, DATE, TIME)
        entities = [ent.text for ent in doc.ents 
                   if ent.label_ not in ['PERSON', 'DATE', 'TIME', 'CARDINAL', 'ORDINAL']]
        keywords.extend(entities)
        
        # Remove duplicates and filter
        keywords = list(set([kw.strip() for kw in keywords if len(kw.strip()) > 2]))
        
        # If we have enough keywords, return them
        if len(keywords) >= limit:
            return keywords[:limit]
    
    # Fallback to TF-IDF based extraction
    try:
        # Tokenize and remove stop words
        tokens = word_tokenize(cleaned_text)
        filtered_tokens = [word for word in tokens 
                          if word.lower() not in stop_words 
                          and word.isalpha() 
                          and len(word) > 2]
        
        if not filtered_tokens:
            return []
        
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=limit * 2,
            ngram_range=(1, 2),
            stop_words='english'
        )
        
        # Join tokens back for TF-IDF
        processed_text = ' '.join(filtered_tokens)
        tfidf_matrix = vectorizer.fit_transform([processed_text])
        
        # Get feature names and scores
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        
        # Sort by TF-IDF score
        keyword_scores = list(zip(feature_names, scores))
        keyword_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top keywords
        keywords = [kw[0] for kw in keyword_scores[:limit] if kw[1] > 0]
        return keywords
        
    except Exception:
        # Simple frequency-based fallback
        word_freq = Counter(filtered_tokens)
        return [word for word, _ in word_freq.most_common(limit)]


def similarity_score(text1: str, text2: str) -> float:
    """
    Calculate similarity score between two texts using cosine similarity.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    try:
        # Clean texts
        clean_text1 = clean_text(text1.lower())
        clean_text2 = clean_text(text2.lower())
        
        # Use TF-IDF vectorizer
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([clean_text1, clean_text2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        return float(similarity)
        
    except Exception:
        # Fallback to simple word overlap
        words1 = set(clean_text(text1.lower()).split())
        words2 = set(clean_text(text2.lower()).split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


def normalize_text(text: str) -> str:
    """
    Normalize text by converting to lowercase and removing punctuation.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text
    """
    if not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    normalized = text.lower()
    
    # Remove punctuation
    normalized = normalized.translate(str.maketrans('', '', string.punctuation))
    
    # Clean whitespace
    normalized = clean_text(normalized)
    
    return normalized


def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text.
    
    Args:
        text: Input text to extract emails from
        
    Returns:
        List of found email addresses
    """
    if not isinstance(text, str):
        return []
    
    # Email regex pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    emails = re.findall(email_pattern, text)
    
    # Remove duplicates and return
    return list(set(emails))


def extract_phone_numbers(text: str) -> List[str]:
    """
    Extract phone numbers from text.
    
    Args:
        text: Input text to extract phone numbers from
        
    Returns:
        List of found phone numbers
    """
    if not isinstance(text, str):
        return []
    
    # Phone number patterns
    patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (123) 456-7890 or 123-456-7890
        r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
        r'\d{10}',  # 10 consecutive digits
    ]
    
    phone_numbers = []
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        phone_numbers.extend(matches)
    
    # Clean and deduplicate
    cleaned_numbers = []
    for number in phone_numbers:
        # Remove non-digit characters for comparison
        digits_only = re.sub(r'\D', '', number)
        if len(digits_only) >= 10:  # Valid phone number should have at least 10 digits
            cleaned_numbers.append(number.strip())
    
    return list(set(cleaned_numbers))


def count_words(text: str) -> int:
    """
    Count words in text.
    
    Args:
        text: Input text to count words
        
    Returns:
        Number of words
    """
    if not isinstance(text, str):
        return 0
    
    cleaned = clean_text(text)
    if not cleaned:
        return 0
    
    words = cleaned.split()
    return len(words)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length.
    
    Args:
        text: Input text to truncate
        max_length: Maximum length of output text
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if not isinstance(text, str) or max_length <= 0:
        return ""
    
    if len(text) <= max_length:
        return text
    
    # Account for suffix length
    actual_max = max_length - len(suffix)
    if actual_max <= 0:
        return suffix[:max_length]
    
    # Try to truncate at word boundary
    truncated = text[:actual_max]
    last_space = truncated.rfind(' ')
    
    if last_space > actual_max * 0.7:  # If we can keep most of the text
        truncated = truncated[:last_space]
    
    return truncated + suffix


def remove_html_tags(text: str) -> str:
    """
    Remove HTML tags from text.
    
    Args:
        text: Input text with HTML tags
        
    Returns:
        Text with HTML tags removed
    """
    if not isinstance(text, str):
        return ""
    
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    
    # Decode common HTML entities
    html_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' '
    }
    
    for entity, char in html_entities.items():
        clean = clean.replace(entity, char)
    
    # Clean up whitespace
    clean = clean_text(clean)
    
    return clean