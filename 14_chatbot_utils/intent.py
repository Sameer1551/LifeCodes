from __future__ import annotations

import joblib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np

log = logging.getLogger(__name__)

try:
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    _SKLEARN = True
except ImportError:
    _SKLEARN = False

class IntentManager:
    """
    Unified Intent Classifier supporting Rules and ML.
    Uses confidence thresholds to decide between ML prediction and Rules.
    """

    def __init__(self, 
                 rules: Optional[Dict[str, List[str]]] = None, 
                 model_path: Optional[Path] = None,
                 threshold: float = 0.7):
        
        self.rules = rules or {}
        self.threshold = threshold
        self.model = None

        if model_path and model_path.exists():
            self.load_model(model_path)

    def train(self, texts: List[str], labels: List[str]):
        """Train a TF-IDF + Logistic Regression pipeline."""
        if not _SKLEARN:
            raise ImportError("scikit-learn is required for training")
        
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), stop_words='english')),
            ('clf', LogisticRegression(max_iter=1000))
        ])
        self.model.fit(texts, labels)
        log.info(f"Trained intent classifier on {len(texts)} samples.")

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predict intent.
        Returns: (intent_name, confidence)
        """
        # 1. Check Rules first (High Precision)
        text_lower = text.lower()
        for intent, keywords in self.rules.items():
            if any(kw in text_lower for kw in keywords):
                return intent, 1.0 # Rules have 100% confidence if matched

        # 2. Check ML Model
        if self.model:
            probs = self.model.predict_proba([text])[0]
            max_idx = np.argmax(probs)
            score = probs[max_idx]
            label = self.model.classes_[max_idx]

            if score >= self.threshold:
                return label, score

        return "unknown", 0.0

    def save_model(self, path: Path):
        joblib.dump(self.model, path)

    def load_model(self, path: Path):
        self.model = joblib.load(path)
