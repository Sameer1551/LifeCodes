#!/usr/bin/env python3
"""
Document Classifier Tool
Assign classification labels to text snippets using Naive Bayes.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Optional


class DocumentClassifier:
    """Simple Naive Bayes document classifier."""

    def __init__(self):
        self.model = None
        self.vectorizer = None

    def train(self, texts: list[str], labels: list[str]) -> None:
        """
        Train the classifier on labeled data.

        Args:
            texts: List of text documents.
            labels: List of corresponding labels.
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import Pipeline

        self.model = Pipeline([
            ('tfidf', TfidfVectorizer()),
            ('classifier', MultinomialNB())
        ])
        self.model.fit(texts, labels)

    def predict(self, text: str) -> str:
        """
        Predict the label for a single text.

        Args:
            text: Text to classify.

        Returns:
            Predicted label.
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        return self.model.predict([text])[0]

    def predict_proba(self, text: str) -> dict[str, float]:
        """
        Get probability distribution over all labels.

        Args:
            text: Text to classify.

        Returns:
            Dict mapping labels to probabilities.
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")

        proba = self.model.predict_proba([text])[0]
        classes = self.model.named_steps['classifier'].classes_
        return {cls: float(p) for cls, p in zip(classes, proba)}

    def save(self, filepath: str) -> None:
        """Save model to file."""
        import joblib
        joblib.dump(self.model, filepath)

    def load(self, filepath: str) -> None:
        """Load model from file."""
        import joblib
        self.model = joblib.load(filepath)


def train_from_csv(csv_path: str, text_column: str, label_column: str) -> DocumentClassifier:
    """
    Train classifier from CSV file.

    Args:
        csv_path: Path to CSV file.
        text_column: Name of text column.
        label_column: Name of label column.

    Returns:
        Trained DocumentClassifier.
    """
    import pandas as pd

    df = pd.read_csv(csv_path)
    texts = df[text_column].tolist()
    labels = df[label_column].tolist()

    classifier = DocumentClassifier()
    classifier.train(texts, labels)
    return classifier


def classify_file(
    input_path: str,
    model_path: str,
    output_path: Optional[str] = None
) -> dict:
    """
    Classify a text file.

    Args:
        input_path: Path to input file.
        model_path: Path to saved model.
        output_path: Path to output file (optional).

    Returns:
        Classification result.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    classifier = DocumentClassifier()
    classifier.load(model_path)

    label = classifier.predict(text)
    proba = classifier.predict_proba(text)

    result = {
        "file": input_path,
        "predicted_label": label,
        "probabilities": proba
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    return result


def create_sample_model() -> None:
    """
    Create a generic sample classifier model.

    This is just one example — you can train on any labels and any text
    (e.g., sentiments, topics, languages, priorities, etc.).
    Replace the texts and labels below with your own data.
    """
    texts = [
        "The project deadline has been moved to next week",
        "Please review and approve the attached proposal",
        "Can we schedule a follow-up meeting on Thursday",
        "Here is the final version of the report",
        "Reminder: submit your timesheet by end of day",
        "The new feature is now live in production",
        "A critical bug has been found in the login flow",
        "Deployment failed due to a configuration error",
        "Tests are failing on the main branch",
        "Server is down and needs immediate attention"
    ]
    labels = [
        "category_a", "category_a", "category_a", "category_a", "category_a",
        "category_b", "category_b", "category_b", "category_b", "category_b"
    ]

    classifier = DocumentClassifier()
    classifier.train(texts, labels)

    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)
    classifier.save(str(models_dir / "sample_classifier.joblib"))

    print(f"Sample model saved to {models_dir / 'sample_classifier.joblib'}")
    print("Note: Replace the sample texts/labels with your own data to classify anything you need.")


def main():
    parser = argparse.ArgumentParser(
        description="Classify documents using Naive Bayes."
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Train command
    train_parser = subparsers.add_parser("train", help="Train a new classifier")
    train_parser.add_argument(
        "-c", "--csv",
        type=str,
        required=True,
        help="Path to training CSV file"
    )
    train_parser.add_argument(
        "--text-column",
        type=str,
        default="text",
        help="Name of text column (default: text)"
    )
    train_parser.add_argument(
        "--label-column",
        type=str,
        default="label",
        help="Name of label column (default: label)"
    )
    train_parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Path to save trained model"
    )

    # Predict command
    predict_parser = subparsers.add_parser("predict", help="Predict label for text")
    predict_parser.add_argument(
        "-m", "--model",
        type=str,
        required=True,
        help="Path to trained model"
    )
    predict_parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input text to classify"
    )
    predict_parser.add_argument(
        "-f", "--file",
        type=str,
        help="Input file to classify"
    )
    predict_parser.add_argument(
        "--show-probabilities",
        action="store_true",
        help="Show probability distribution"
    )

    # Create sample command
    sample_parser = subparsers.add_parser("sample", help="Create a generic sample classifier (category_a vs category_b) as a starting point")

    args = parser.parse_args()

    if args.command == "train":
        classifier = train_from_csv(
            args.csv,
            args.text_column,
            args.label_column
        )
        classifier.save(args.output)
        print(f"Model trained and saved to {args.output}")

    elif args.command == "predict":
        if not args.input and not args.file:
            predict_parser.error("Either --input or --file is required")

        text = args.input if args.input else open(args.file, "r", encoding="utf-8").read()

        classifier = DocumentClassifier()
        classifier.load(args.model)

        label = classifier.predict(text)

        if args.show_probabilities:
            proba = classifier.predict_proba(text)
            print(f"Predicted label: {label}")
            print("\nProbability distribution:")
            for cls, prob in sorted(proba.items(), key=lambda x: x[1], reverse=True):
                print(f"  {cls}: {prob*100:.2f}%")
        else:
            print(label)

    elif args.command == "sample":
        create_sample_model()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()