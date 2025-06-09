"""Text processing utilities."""
import re
from typing import List

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text."""
    if not text:
        return []
    # Simple keyword extraction - can be enhanced with NLP
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return list(set(words))[:max_keywords]
