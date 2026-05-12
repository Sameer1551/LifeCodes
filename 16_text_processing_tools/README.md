# Text Processing Tools

A collection of offline-ready Python tools for text processing tasks.

## Installation

```bash
cd 16_text_processing_tools
pip install -r requirements.txt

# Download NLTK data (required for some tools)
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab')"
```

## Tools

### 1. text_summarizer.py
Summarize text to a specific sentence count.

```bash
# Summarize from text
python text_summarizer.py -i "Your long text here..." -n 5

# Summarize from file
python text_summarizer.py -f input.txt -n 3 -o summary.txt
```

### 2. keyword_extractor.py
Extract key phrases from text.

```bash
python keyword_extractor.py -f document.txt -n 15 -g 3
```

### 3. language_detector.py
Detect the language of text.

```bash
python language_detector.py -i "Bonjour le monde"
python language_detector.py -f file.txt --probabilities
```

### 4. text_normalizer.py
Clean and standardize text.

```bash
python text_normalizer.py -f input.txt --remove-urls --remove-emails
python text_normalizer.py -i "Hello WORLD!" --keep-punctuation
```

### 5. stopword_remover.py
Remove stopwords from text.

```bash
python stopword_remover.py -f input.txt -l english -o cleaned.txt
python stopword_remover.py --list-languages
```

### 6. sentence_splitter.py
Split text into sentences.

```bash
python sentence_splitter.py -f input.txt --format numbered
python sentence_splitter.py -i "First sentence. Second sentence." --format json
```

### 7. word_frequency_counter.py
Count word frequencies.

```bash
python word_frequency_counter.py -f input.txt -n 20 --format table
python word_frequency_counter.py -f input.txt --min-length 3 --format csv
```

### 8. text_similarity_checker.py
Compare similarity between two texts.

```bash
python text_similarity_checker.py -f1 doc1.txt -f2 doc2.txt
python text_similarity_checker.py -t1 "hello world" -t2 "hi world" --format json
```

### 9. document_classifier.py
Classify documents using Naive Bayes — works with **any labels** (topics, sentiments, priorities, categories, etc.).

```bash
# Create a generic sample model (category_a vs category_b) as a starting point
python document_classifier.py sample

# Train on your own data from a CSV (any labels you define)
python document_classifier.py train -c data.csv --text-column text --label-column label -o model.joblib

# Predict label for text, with probability scores
python document_classifier.py predict -m model.joblib -i "Your text here" --show-probabilities

# Predict from a file
python document_classifier.py predict -m model.joblib -f input.txt
```

### 10. text_encoding_converter.py
Detect and convert text encoding — works with **any file type**.

```bash
# Detect encoding of a file
python text_encoding_converter.py detect file.txt

# Convert a single file to UTF-8 (or any target encoding)
python text_encoding_converter.py convert input.txt -o output.txt
python text_encoding_converter.py convert input.txt -e latin-1

# Batch convert all files in a directory (default: all files)
python text_encoding_converter.py batch ./input_dir -o ./output_dir

# Batch convert only specific file types
python text_encoding_converter.py batch ./input_dir -o ./output_dir -p "*.csv"
python text_encoding_converter.py batch ./input_dir -o ./output_dir -p "*.log"
```

## License

MIT License