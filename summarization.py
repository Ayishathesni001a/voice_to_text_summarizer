import logging
import nltk
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
from heapq import nlargest
import string
from sklearn.feature_extraction.text import TfidfVectorizer
import re

logger = logging.getLogger(__name__)
from transformers import pipeline

# Initialize transformer summarizer once
try:
    transformer_summarizer = pipeline(
        "summarization",
        model="sshleifer/distilbart-cnn-12-6",
        device=-1  # CPU-only mode
    )
except Exception as e:
    transformer_summarizer = None
    logger.error(f"Could not load transformer summarizer: {e}")


# Load SpaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("SpaCy model 'en_core_web_sm' not found. Running download...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

# Download required NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

def preprocess_text(text):
    """
    Preprocess text by removing punctuation, stopwords, and speech filler words.
    Returns custom-split sentences and original sentences.
    """
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    if not sentences or len(sentences) == 1 and len(word_tokenize(sentences[0])) > 20:
        text = re.sub(r'(?<=[.,;!?])\s+', ' ', text)  # Normalize spacing
        sentences = re.split(r'[.;!?]+', text)  # Split at punctuation
        sentences = [s.strip() for s in sentences if s.strip() and any(w.lower() not in stopwords.words('english') for w in word_tokenize(s))]
        if not sentences:
            words = word_tokenize(text)
            sentences = [' '.join(words[i:i+15]) for i in range(0, len(words), 15) if any(w.lower() not in stopwords.words('english') for w in words[i:i+15])]
    cleaned_sentences = []
    stop_words = set(stopwords.words('english'))
    speech_fillers = {'um', 'uh', 'like', 'you know', 'er', 'ah', 'hmm'}
    stop_words.update(speech_fillers)
    
    for sent in sentences:
        words = word_tokenize(sent)
        words = [word for word in words if word not in string.punctuation]
        words = [word for word in words if word.lower() not in stop_words]
        cleaned_sent = ' '.join(words)
        if cleaned_sent:
            cleaned_sentences.append(cleaned_sent)
    
    return sentences, cleaned_sentences

def extract_keywords(doc, pos_tags=['PROPN', 'NOUN', 'VERB', 'ADJ']):
    """
    Extract keywords based on specified POS tags.
    Returns a list of keywords.
    """
    keywords = [token.text for token in doc if token.pos_ in pos_tags]
    return keywords

def calculate_frequencies(keywords):
    """
    Calculate normalized frequencies for keywords.
    Returns a dictionary of normalized frequencies.
    """
    freq = Counter(keywords)
    max_freq = freq.most_common(1)[0][1] if freq else 1
    for key in freq:
        freq[key] = freq[key] / max_freq
    return freq

def score_sentences(doc, sentences):
    """
    Score sentences using TF-IDF for better keyword weighting.
    Returns a dictionary mapping sentences to scores.
    """
    valid_sents = [sent for sent in doc.sents if sent.text.strip() in sentences]
    if not valid_sents:
        valid_sents = [doc[s.start:s.end] for s in doc.sents if s.text.strip()]
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([sent.text for sent in valid_sents])
    scores = tfidf_matrix.sum(axis=1).A1 / tfidf_matrix.sum(axis=1).A1.max()  # Normalize scores
    sent_strength = {sent: score for sent, score in zip(valid_sents, scores) if score > 0.05}  # Lowered threshold
    return sent_strength

def clean_summary(sentences):
    """
    Clean summary by removing redundant phrases and correcting errors.
    Returns a list of cleaned sentence strings.
    """
    cleaned_sentences = []
    redundant_phrases = ['um', 'uh', 'like', 'you know', 'quant mechanics', 'subatomic particl', 'my classical physics practical']
    corrections = {'es': 'as', 'col': 'collapse', 'distancas': 'distances', 'Momentum': 'momentum', 'describe': 'describes'}
    for sent in sentences:
        sent_text = sent.text.strip()
        for phrase in redundant_phrases:
            sent_text = sent_text.replace(phrase, '')
        for err, corr in corrections.items():
            sent_text = sent_text.replace(err, corr)
        sent_text = ' '.join(sent_text.split())
        if sent_text:
            cleaned_sentences.append(sent_text)
    return cleaned_sentences

def generate_summary(text, percent=0.2, max_length=130):
    """
    Generate summary using a small Transformer model for better results.
    Falls back to extractive method if transformer fails.
    """
    if not text or not text.strip():
        logger.warning("Empty or whitespace-only text provided for summarization")
        return ""

    # Clean up and trim input
    text = text.strip().replace('\n', ' ')
    input_limit = 800  # tokens limit for small models
    words = text.split()
    if len(words) > input_limit:
        text = ' '.join(words[:input_limit])

    try:
        if transformer_summarizer:
            logger.info("Using Transformer-based summarizer")
            summary = transformer_summarizer(text, max_length=max_length, min_length=30, do_sample=False)
            return summary[0]['summary_text']
        else:
            logger.warning("Transformer summarizer not available. Falling back.")
    except Exception as e:
        logger.error(f"Transformer summarization failed: {e}")

    # Fallback to your extractive method
    logger.info("Falling back to extractive summarization")
    return extractive_summary_fallback(text, max_length=max_length)


def extractive_summary_fallback(text, max_length=300):
    """
    Your existing fallback extractive summarization logic (can reuse your earlier logic here).
    """
    try:
        doc = nlp(text)
        sentences, _ = preprocess_text(text)
        sent_strength = score_sentences(doc, sentences)
        top_sentences = nlargest(2, sent_strength, key=sent_strength.get)
        summary = ' '.join(clean_summary(top_sentences))
        return summary[:max_length] + "..." if len(summary) > max_length else summary
    except Exception as e:
        logger.error(f"Fallback summarization failed: {e}")
        return text[:max_length] + "..."
