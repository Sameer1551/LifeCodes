# Implementation Plan: Text Processing Toolkit (Tools 1–10)

This document outlines the technical approach to building the first 10 "Text Processing Tools" as defined in `make.md`.

## 📂 Proposed Directory Structure
```text
16_text_processing_tools/
├── text_summarizer.py
├── keyword_extractor.py
├── language_detector.py
├── text_normalizer.py
├── stopword_remover.py
├── sentence_splitter.py
├── word_frequency_counter.py
├── text_similarity_checker.py
├── document_classifier.py
├── text_encoding_converter.py
└── requirements.txt
```

---

## 🛠️ Individual Tool Specifications

### 1. text_summarizer.py
- **Goal**: Summarize a text block down to a specific sentence count.
- **Library**: `sumy` (extractive approach).
- **Core Logic**:
  - Load the plaintext parser from string.
  - Choose `LexRank` summarizer for robust, general-purpose results.
  - Export the top $N$ sentences to the user.

### 2. keyword_extractor.py
- **Goal**: Identify key phrases and terms within a long document.
- **Library**: `yake` (Yet Another Keyword Extractor).
- **Core Logic**:
  - It is an unsupervised approach that does not require heavy corpora.
  - Provide parameters for $N$-gram size and top $K$ results.

### 3. language_detector.py
- **Goal**: Detect the source language of a given text.
- **Library**: `langdetect`.
- **Core Logic**:
  - Simple wrapper around `detect` or `detect_langs` to return ISO language codes (e.g., "en", "es").

### 4. text_normalizer.py
- **Goal**: Clean and standardize text for downstream processing.
- **Library**: `re` (builtin), `string`, `unicodedata`.
- **Core Logic**:
  - Remove all punctuation.
  - Lowercase all characters.
  - Normalize unicode (NFKD) to handle accented characters.
  - Collapse multiple spaces into one.

### 5. stopword_remover.py
- **Goal**: Strip "noise" words to focus on meaningful content.
- **Library**: `nltk`.
- **Core Logic**:
  - Load the `stopwords` corpus from NLTK.
  - Filter input text based on the detected or specified language list.

### 6. sentence_splitter.py
- **Goal**: Divide a wall of text into discrete, analyzeable sentences.
- **Library**: `nltk`.
- **Core Logic**:
  - Utilize `sent_tokenize` which handles common edge cases like abbreviations and punctuation mid-sentence.

### 7. word_frequency_counter.py
- **Goal**: Identify the most common non-stopword terms.
- **Library**: `collections` (builtin).
- **Core Logic**:
  - Tokenize text.
  - Run `Counter` to get counts.
  - Display as a sorted table or list.

### 8. text_similarity_checker.py
- **Goal**: Measure how related two documents/strings are.
- **Library**: `scikit-learn` (sklearn).
- **Core Logic**:
  - Convert both texts into TF-IDF vectors.
  - Compute `cosine_similarity` between the two vectors.
  - Output as a percentage.

### 9. document_classifier.py
- **Goal**: Assign a classification label (e.g., "Spam", "Billing") to a text snippet.
- **Library**: `scikit-learn`.
- **Core Logic**:
  - provide a script that can train a simple Naive Bayes model on CSV data or predict based on a pre-saved model.

### 10. text_encoding_converter.py
- **Goal**: Fix "broken" or localized text encoding.
- **Library**: `chardet`.
- **Core Logic**:
  - Use `chardet` to detect current encoding.
  - Read input as bytes and decode with detected encoding.
  - Re-save or output as UTF-8.

---

## 📦 Global Dependencies
- `sumy`
- `yake`
- `langdetect`
- `nltk`
- `scikit-learn`
- `chardet`
