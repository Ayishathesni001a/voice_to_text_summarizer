import os
import logging
import tempfile
import numpy as np
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
from scipy.signal import butter, lfilter

logger = logging.getLogger(__name__)

def apply_noise_reduction(audio_segment, sample_rate=16000):
    """
    Apply a bandpass filter to reduce noise in audio.
    
    Args:
        audio_segment (AudioSegment): The audio segment to filter
        sample_rate (int): Sample rate of the audio
        
    Returns:
        AudioSegment: Filtered audio segment
    """
    # Convert audio segment to numpy array
    audio_array = np.array(audio_segment.get_array_of_samples())
    
    # Convert to float for signal processing
    if audio_segment.sample_width == 2:  # 16-bit audio
        audio_array = audio_array.astype(np.float32) / 32768.0
    
    # Design bandpass filter (speech typically between 300Hz-3400Hz)
    nyq = 0.5 * sample_rate
    low_cutoff = 300 / nyq
    high_cutoff = 3400 / nyq
    b, a = butter(4, [low_cutoff, high_cutoff], btype='band')
    
    # Apply filter
    filtered_audio = lfilter(b, a, audio_array)
    
    # Convert back to original format
    if audio_segment.sample_width == 2:
        filtered_audio = (filtered_audio * 32768.0).astype(np.int16)
    
    # Create new audio segment from filtered data
    filtered_segment = AudioSegment(
        filtered_audio.tobytes(),
        frame_rate=sample_rate,
        sample_width=audio_segment.sample_width,
        channels=audio_segment.channels
    )
    
    return filtered_segment

def resample_audio(audio_segment, target_rate=16000):
    """
    Resample audio to a target sample rate.
    
    Args:
        audio_segment (AudioSegment): The audio segment to resample
        target_rate (int): Target sample rate
        
    Returns:
        AudioSegment: Resampled audio segment
    """
    return audio_segment.set_frame_rate(target_rate)

def transcribe_audio(audio_file_path, noise_reduction=True):
    temp_files = []
    try:
        recognizer = sr.Recognizer()
        if not os.path.isfile(audio_file_path):
            logger.error(f"File not found: {audio_file_path}")
            return ""
            
        # Convert to WAV if needed
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        if file_ext != '.wav':
            logger.info(f"Converting {file_ext} to WAV format")
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav_path = temp_wav.name
            temp_wav.close()
            temp_files.append(temp_wav_path)
            audio = AudioSegment.from_file(audio_file_path)
            audio.export(temp_wav_path, format='wav')
            audio_file_path = temp_wav_path
            logger.info(f"Converted audio to {temp_wav_path}")
        
        audio = AudioSegment.from_file(audio_file_path)
        logger.debug(f"Raw audio: duration={len(audio)/1000}s, channels={audio.channels}, sample_width={audio.sample_width}, frame_rate={audio.frame_rate}")
        
        # Resample
        audio = resample_audio(audio, target_rate=16000)
        logger.debug(f"Resampled audio: duration={len(audio)/1000}s, frame_rate={audio.frame_rate}")
        
        # Noise reduction (optional bypass)
        if noise_reduction:
            logger.info("Applying noise reduction")
            audio = apply_noise_reduction(audio)
            logger.debug("Noise reduction applied")
        else:
            logger.info("Skipping noise reduction")
        
        processed_temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        processed_temp_path = processed_temp.name
        processed_temp.close()
        temp_files.append(processed_temp_path)
        audio.export(processed_temp_path, format='wav', parameters=["-acodec", "pcm_s16le"])
        logger.info(f"Saved processed audio to {processed_temp_path}, size={os.path.getsize(processed_temp_path)} bytes")
        
        # Split into chunks
        logger.info("Splitting audio into chunks")
        chunks = split_on_silence(
            audio,
            min_silence_len=500,
            silence_thresh=-40,
            keep_silence=300
        )
        if len(chunks) == 0:
            logger.warning("Could not split audio on silence, processing as one chunk")
            chunks = [audio]
        logger.info(f"Split into {len(chunks)} chunks")
        
        transcript_pieces = []
        for i, chunk in enumerate(chunks):
            chunk_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            chunk_path = chunk_file.name
            chunk_file.close()
            temp_files.append(chunk_path)
            chunk.export(chunk_path, format='wav', parameters=["-acodec", "pcm_s16le"])
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            with sr.AudioFile(chunk_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = recognizer.record(source)
                try:
                    chunk_text = recognizer.recognize_google(audio_data)
                    transcript_pieces.append(chunk_text)
                    logger.info(f"Chunk {i+1} transcribed: '{chunk_text[:30]}...' ({len(chunk_text)} chars)")
                except sr.UnknownValueError:
                    logger.warning(f"Could not understand audio in chunk {i+1}")
                except sr.RequestError as e:
                    logger.error(f"API error in chunk {i+1}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing chunk {i+1}: {str(e)}")
        
        full_transcript = " ".join(transcript_pieces)
        logger.info(f"Full transcription complete. Length: {len(full_transcript)} characters")
        return full_transcript
        
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)} with traceback: {traceback.format_exc()}")
        return ""
    finally:
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.debug(f"Deleted temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Error deleting temporary file {temp_file}: {str(e)}")
# Example usage
if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example call
    result = transcribe_audio("path/to/your/audio/file.mp3")
    print(f"Transcription result: {result}")