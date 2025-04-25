voice to text summarisation

This project transcribes audio files and generates a summary of the transcriptions, then compiles both into a downloadable PDF document. The system uses NLTK for text processing and ReportLab for PDF generation.
Features

    Audio Transcription: Convert speech from audio files into text.
    Text Summarization: Extract a summary of the transcribed text using extractive summarization.
    PDF Generation: Combine both the full transcription and summary into a formatted PDF document.

Requirements

To run this project, make sure you have the following dependencies installed:

    Python 3.6 or higher
    nltk: For natural language processing (tokenization, stopword filtering, frequency analysis).
    reportlab: For PDF creation.
    logging: For logging important events and errors.
    Other required Python libraries (you can install them using requirements.txt).

Install Dependencies

To install the required libraries, run:

pip install -r requirements.txt

