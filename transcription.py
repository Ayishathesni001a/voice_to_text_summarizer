import os
import logging
import tempfile
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)

def transcribe_audio(audio_file_path):
    """
    Transcribes audio from a file using the SpeechRecognition library.
    
    Args:
        audio_file_path (str): Path to the audio file
        
    Returns:
        str: Transcribed text, or empty string if transcription failed
    """
    try:
        # Initialize recognizer
        recognizer = sr.Recognizer()
        
        # Check if file exists
        if not os.path.isfile(audio_file_path):
            logger.error(f"File not found: {audio_file_path}")
            return ""
        
        # Convert audio to WAV format if needed
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        
        if file_ext != '.wav':
            logger.info(f"Converting {file_ext} to WAV format")
            try:
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_wav_path = temp_wav.name
                temp_wav.close()
                
                audio = AudioSegment.from_file(audio_file_path)
                audio.export(temp_wav_path, format='wav')
                audio_file_path = temp_wav_path
                logger.info(f"Converted audio to {temp_wav_path}")
            except Exception as e:
                logger.error(f"Error converting audio to WAV: {str(e)}")
                return ""
        
        # Load audio file and transcribe
        with sr.AudioFile(audio_file_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source)
            
            # Record audio
            logger.info("Recording audio from file")
            audio_data = recognizer.record(source)
            
            # Recognize speech using Google Speech Recognition
            logger.info("Recognizing speech...")
            text = recognizer.recognize_google(audio_data)
            logger.info(f"Transcription complete. Length: {len(text)} characters")
            
            # Clean up temporary file if created
            if file_ext != '.wav' and 'temp_wav_path' in locals():
                os.unlink(temp_wav_path)
                
            return text
    
    except sr.UnknownValueError:
        logger.error("Speech Recognition could not understand audio")
        return ""
    except sr.RequestError as e:
        logger.error(f"Could not request results from Speech Recognition service: {str(e)}")
        return ""
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}")
        return ""
