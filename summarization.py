import logging
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.probability import FreqDist
from heapq import nlargest

logger = logging.getLogger(__name__)

# Download required NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

def generate_summary(text, percent=0.3):
    """
    Generate a summary of the given text using extractive summarization.
    
    Args:
        text (str): The text to summarize
        percent (float): Percentage of original text to include in summary (0-1)
        
    Returns:
        str: The summarized text
    """
    if not text:
        logger.warning("Empty text provided for summarization")
        return ""
        
    try:
        # Tokenize the text into sentences
        sentences = sent_tokenize(text)
        
        # If text is too short, return the original text
        if len(sentences) <= 3:
            logger.info("Text too short for summarization, returning original")
            return text
        
        # Tokenize words and remove stop words
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text.lower())
        filtered_words = [word for word in words if word.isalnum() and word not in stop_words]
        
        # Calculate word frequencies
        word_frequencies = FreqDist(filtered_words)
        
        # Calculate sentence scores based on word frequencies
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            for word in word_tokenize(sentence.lower()):
                if word in word_frequencies:
                    if i not in sentence_scores:
                        sentence_scores[i] = 0
                    sentence_scores[i] += word_frequencies[word]
        
        # Normalize sentence scores by sentence length
        for i in sentence_scores:
            words_count = len(word_tokenize(sentences[i]))
            if words_count > 0:  # Avoid division by zero
                sentence_scores[i] = sentence_scores[i] / words_count
        
        # Determine number of sentences for the summary
        summary_sentences_count = max(int(len(sentences) * percent), 1)
        
        # Get the indices of the top sentences
        top_sentences_indices = nlargest(summary_sentences_count, sentence_scores, key=sentence_scores.get)
        
        # Sort the indices to preserve the original order
        top_sentences_indices = sorted(top_sentences_indices)
        
        # Build the summary by joining the top sentences
        summary = ' '.join([sentences[i] for i in top_sentences_indices])
        
        logger.info(f"Generated summary with {len(top_sentences_indices)} sentences from original {len(sentences)} sentences")
        return summary
        
    except Exception as e:
        logger.error(f"Error in generate_summary: {str(e)}")
        return text  # Return original text on error
