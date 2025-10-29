# Voice-to-Text Summarization System

**A lightweight web application that converts spoken audio into text and generates a concise summary** — built for low-end devices like Intel i3 processors.

---

## Features

- Real-time **audio recording** via browser (HTML5 `getUserMedia`)
- **Accurate transcription** using Google Speech-to-Text API
- **Automatic summarization** (T5-Small attempted, extractive fallback used)
- **Flask-based web UI** (responsive, clean interface)
- **Local processing** — no cloud dependency after transcription
- **FFmpeg-powered audio chunking** for long recordings

---

## System Architecture
[Microphone]
↓ (Audio Capture - recorder.js)
[Browser]
↓ (Upload .wav file)
[Flask Server]
↓ (Chunking with pydub + FFmpeg)
[Transcription Engine] → speech_recognition + Google API
↓ (Full transcript)
[Summarization Engine] → T5-Small (failed) → Extractive (NLTK + TF-IDF)


---

## Technologies Used

| Component          | Technology |
|--------------------|------------|
| **Frontend**       | HTML, CSS, JavaScript (`recorder.js`, `main.js`) |
| **Backend**        | Python, Flask |
| **Transcription**  | `speech_recognition`, Google Speech-to-Text API |
| **Audio Processing**| `pydub`, `ffmpeg` (v6.1.1) |
| **Summarization**  | `transformers` (T5-Small), `nltk`, `scikit-learn` |
| **Hardware**       | Intel Core i3 (4–8 GB RAM), Local CPU only |

---

## Demo Output (Quantum Mechanics Example)

<img width="1301" height="617" alt="image" src="https://github.com/user-attachments/assets/5b07dc30-d31d-4f25-af05-e4a7697bbeaa" />  <img width="1302" height="645" alt="image" src="https://github.com/user-attachments/assets/aed27952-6ff5-48a7-a969-ec4c9e1f7bc9" />



### Input Audio
> Spoken: *"Quantum mechanics is a fundamental branch of physics..."*

### Transcribed Text (609 characters) and Generated Summary
<img width="1302" height="645" alt="image" src="https://github.com/user-attachments/assets/ef391464-a346-4fde-bd8b-6cfcec9e250e" />

> **Note**: T5-Small model failed to load due to i3 memory constraints. Extractive summarization used as fallback.

## How to Run (For Examiners)

```bash
# 1. Clone or copy project
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run Flask app
python app.py

# 4. Open browser: http://127.0.0.1:5000
# 5. Record or upload audio → View transcript + summary


↓ (Summary)
[Web UI] → Display transcript + summary
