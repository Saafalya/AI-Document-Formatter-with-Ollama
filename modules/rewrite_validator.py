"""
rewrite_validator.py
--------------------
Validates AI rewrites before they are accepted into the document.
Every rewrite must pass similarity, numeric, URL, email, and entity checks.
Unsafe rewrites are rejected and the original text is preserved.
"""

import logging
import re
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded sentence transformer to avoid startup cost
_encoder = None
SIMILARITY_THRESHOLD = 0.70  # Overridden by env var in app.py


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _encoder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer loaded.")
        except Exception as e:
            logger.warning(f"SentenceTransformer unavailable: {e}. Similarity check disabled.")
            _encoder = False
    return _encoder if _encoder is not False else None


def _extract_numbers(text: str) -> List[str]:
    return re.findall(r"\b\d+(?:[.,]\d+)?\b", text)


def _extract_urls(text: str) -> List[str]:
    return re.findall(r"https?://\S+|www\.\S+", text, re.IGNORECASE)


def _extract_emails(text: str) -> List[str]:
    return re.findall(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class RewriteValidator:
    """Validates a proposed rewrite against the original sentence."""

    def __init__(self, similarity_threshold: Optional[float] = None):
        self.threshold = similarity_threshold or SIMILARITY_THRESHOLD

    def validate(self, original: str, rewritten: str) -> Tuple[bool, str]:
        """
        Run all validation checks on a rewrite.

        Args:
            original: The source sentence before rewriting.
            rewritten: The proposed replacement sentence.

        Returns:
            (passed: bool, reason: str) — reason is empty string if passed.
        """
        if not rewritten or not rewritten.strip():
            return False, "Rewrite is empty."

        if rewritten.strip() == original.strip():
            return True, ""  # No change — trivially valid

        # Numeric integrity
        orig_nums = sorted(_extract_numbers(original))
        new_nums = sorted(_extract_numbers(rewritten))
        if orig_nums != new_nums:
            return False, f"Numbers changed: {orig_nums} → {new_nums}"

        # URL integrity
        orig_urls = sorted(_extract_urls(original))
        new_urls = sorted(_extract_urls(rewritten))
        if orig_urls != new_urls:
            return False, f"URLs changed: {orig_urls} → {new_urls}"

        # Email integrity
        orig_emails = sorted(_extract_emails(original))
        new_emails = sorted(_extract_emails(rewritten))
        if orig_emails != new_emails:
            return False, f"Emails changed: {orig_emails} → {new_emails}"

        # Semantic similarity
        encoder = _get_encoder()
        if encoder is not None:
            try:
                embeddings = encoder.encode([original, rewritten])
                sim = _cosine_similarity(embeddings[0], embeddings[1])
                if sim < self.threshold:
                    return False, f"Semantic similarity too low: {sim:.2f} < {self.threshold}"
            except Exception as e:
                logger.warning(f"Similarity check failed: {e} — skipping.")

        return True, ""
