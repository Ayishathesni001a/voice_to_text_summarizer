
import nltk
nltk.download('punkt_tab')
import os
import tempfile
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from models import User, Transcription 
from forms import LoginForm, SignupForm, AudioUploadForm, TranscriptionEditForm, SummaryEditForm
from transcription import transcribe_audio
from summarization import generate_summary
from pdf_generator import create_pdf
from app import app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, logger  # Adjust imports
from models import Transcription  # Adjust model import
import traceback
import logging
from pydub import AudioSegment

import logging
from uuid import uuid4
import traceback
import time
import io
import subprocess





logger = logging.getLogger(__name__)

def register_routes(app):
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Invalid email or password')
                return redirect(url_for('login'))
            
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('home')
            return redirect(next_page)
        
        return render_template('login.html', form=form)
        

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        
        form = SignupForm()
        if form.validate_on_submit():
            username = form.username.data
            email = form.email.data
            plain_password = form.password.data  # The raw password entered by the user
            
            # Hash the password before storing it in the database
            hashed_password = generate_password_hash(plain_password)

            # Register as a normal User
            user = User(username=username, email=email, password_hash=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('Congratulations, you are now registered!', 'success')
            return redirect(url_for('login'))

        return render_template('signup.html', form=form)

        
    @app.route('/delete_user/<int:user_id>')
    def delete_user(user_id):
        # Fetch the user and delete from database
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
        return redirect(url_for('admin_dashboard'))

    @app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
    def edit_user(user_id):
        user = User.query.get(user_id)
        if request.method == 'POST':
            # Update user details
            user.username = request.form['username']
            user.email = request.form['email']
            db.session.commit()
            return redirect(url_for('admin_dashboard'))
        return render_template('edit_user.html', user=user)
        
    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))
    
    @app.route('/home')
    @login_required
    def home():
        form = AudioUploadForm()
        transcriptions = Transcription.query.filter_by(user_id=current_user.id).order_by(Transcription.created_at.desc()).all()
        return render_template('home.html', form=form, transcriptions=transcriptions)
    
    @app.route('/upload_audio', methods=['POST'])
    @login_required
    def upload_audio():
        form = AudioUploadForm()
        if form.validate_on_submit():
            try:
                audio_file = form.audio_file.data
                if not audio_file:
                    flash('No audio file provided.')
                    return redirect(url_for('home'))
                
                filename = secure_filename(audio_file.filename)
                temp_dir = tempfile.mkdtemp()
                file_path = os.path.join(temp_dir, filename)
                audio_file.save(file_path)
                
                title = form.title.data if form.title.data else f"Transcription {len(current_user.transcriptions.all()) + 1}"
                transcription_text = transcribe_audio(file_path)
                if not transcription_text:
                    flash('Failed to transcribe the audio file.')
                    return redirect(url_for('home'))
                
                logger.debug(f"Transcription text for summary: {transcription_text}")
                summary = generate_summary(transcription_text)
                logger.debug(f"Generated summary: {summary}")
                
                transcription = Transcription(
                    title=title,
                    transcription_text=transcription_text,
                    summary_text=summary,
                    user_id=current_user.id
                )
                db.session.add(transcription)
                db.session.commit()
                
                os.unlink(file_path)
                os.rmdir(temp_dir)
                
                flash('Audio successfully transcribed!')
                return redirect(url_for('view_transcription', id=transcription.id))
            except Exception as e:
                logger.error(f"Error in upload_audio: {str(e)}")
                flash(f'Error processing audio: {str(e)}')
                return redirect(url_for('home'))
        
        flash('Invalid form submission.')
        return redirect(url_for('home'))



    @app.route('/transcribe_recording', methods=['POST'])
    @login_required
    def transcribe_recording():
        try:
            if 'audio' not in request.files:
                return jsonify({'success': False, 'error': 'No audio file provided.'}), 400
            
            audio_file = request.files['audio']
            logger.debug(f"Received audio file: {audio_file.filename}, content length: {request.content_length}, mimetype: {audio_file.mimetype}")
            
            title = request.form.get('title', f"Recording {len(Transcription.query.filter_by(user_id=current_user.id).all()) + 1}")
            request_id = request.form.get('request_id', str(uuid4()))

            temp_dir = tempfile.mkdtemp()
            original_filename = secure_filename(audio_file.filename or 'recording.webm')
            original_file_path = os.path.join(temp_dir, original_filename)
            
            audio_file.save(original_file_path)
            if not os.path.exists(original_file_path):
                error_msg = f"Failed to save audio file to {original_file_path}"
                logger.error(error_msg)
                for file in [original_file_path]:
                    if os.path.exists(file):
                        os.unlink(file)
                os.rmdir(temp_dir)
                return jsonify({'success': False, 'error': error_msg}), 400
            logger.info(f"Saved original file as: {original_file_path}, size: {os.path.getsize(original_file_path)} bytes")

            wav_file_path = os.path.join(temp_dir, 'recording.wav')
            try:
                audio = AudioSegment.from_file(original_file_path)
                logger.debug(f"Original audio duration: {len(audio) / 1000} seconds")
                audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                audio.export(wav_file_path, format='wav', parameters=["-acodec", "pcm_s16le"])
                logger.info(f"Converted to WAV: {wav_file_path}, size: {os.path.getsize(wav_file_path)} bytes")
            except Exception as e:
                error_msg = f"Error converting audio to WAV: {str(e)} with traceback: {traceback.format_exc()}"
                logger.error(error_msg)
                with open(original_file_path, 'rb') as f:
                    logger.debug(f"File header: {f.read(44).hex() if f.read(44) else 'Empty'}")
                for file in [original_file_path, wav_file_path]:
                    if os.path.exists(file):
                        os.unlink(file)
                os.rmdir(temp_dir)
                return jsonify({'success': False, 'error': error_msg}), 400
            
            transcription_text = transcribe_audio(wav_file_path, noise_reduction=True)
            if not transcription_text:
                error_msg = 'Failed to transcribe the audio file. Check audio format or transcription service.'
                logger.warning(error_msg)
                logger.debug(f"WAV file details: size={os.path.getsize(wav_file_path)} bytes, path={wav_file_path}")
                with open(wav_file_path, 'rb') as f:
                    logger.debug(f"WAV file header: {f.read(44).hex()}")
                for file in [wav_file_path, original_file_path]:
                    if os.path.exists(file):
                        os.unlink(file)
                os.rmdir(temp_dir)
                return jsonify({'success': False, 'error': error_msg}), 400
            
            logger.debug(f"Transcription text for summary: {transcription_text}")
            summary = generate_summary(transcription_text)
            logger.debug(f"Generated summary: {summary}")
            
            transcription = Transcription(title=title, transcription_text=transcription_text, summary_text=summary, user_id=current_user.id, request_id=request_id)
            db.session.add(transcription)
            db.session.commit()
            transcription_id = transcription.id
            
            for file in [wav_file_path, original_file_path]:
                if os.path.exists(file):
                    os.unlink(file)
            os.rmdir(temp_dir)
            
            return jsonify({'success': True, 'id': transcription_id})
        except Exception as e:
            logger.error(f"Error in transcribe_recording: {str(e)} with traceback: {traceback.format_exc()}")
            return jsonify({'success': False, 'error': f'Error processing audio: {str(e)}'}), 500
    @app.route('/view_transcription/<int:id>')
    @login_required
    def view_transcription(id):
        transcription = Transcription.query.get_or_404(id)
        return render_template('view_transcription.html', transcription=transcription)
   
   
    @app.route('/edit_transcription/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_transcription(id):
        transcription = Transcription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
        form = TranscriptionEditForm()
        
        if request.method == 'GET':
            form.transcription.data = transcription.transcription_text
            
        if form.validate_on_submit():
            transcription.transcription_text = form.transcription.data
            transcription.summary_text = generate_summary(form.transcription.data)
            db.session.commit()
            flash('Transcription updated successfully!')
            return redirect(url_for('view_transcription', id=id))
            
        return render_template('edit_transcription.html', form=form, transcription=transcription)
        
    @app.route('/edit_summary/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_summary(id):
        transcription = Transcription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
        form = SummaryEditForm()
        
        if request.method == 'GET':
            form.summary.data = transcription.summary_text
            
        if form.validate_on_submit():
            transcription.summary_text = form.summary.data
            db.session.commit()
            flash('Summary updated successfully!')
            return redirect(url_for('view_transcription', id=id))
            
        return render_template('edit_summary.html', form=form, transcription=transcription)
    
    @app.route('/download_pdf/<int:id>')
    @login_required
    def download_pdf(id):
        transcription = Transcription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
        
        # Create a temporary file to store the PDF
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        pdf_path = temp_file.name
        temp_file.close()
        
        # Generate the PDF
        create_pdf(transcription.title, transcription.transcription_text, 
                   transcription.summary_text, pdf_path)
        
        # Serve the file
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"{transcription.title.replace(' ', '_')}.pdf",
            mimetype='application/pdf'
        )
    
    @app.route('/delete_transcription/<int:id>', methods=['POST'])
    @login_required
    def delete_transcription(id):
        transcription = Transcription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
        db.session.delete(transcription)
        db.session.commit()
        flash('Transcription deleted successfully!')
        return redirect(url_for('home'))

    # Create the view_transcription.html and edit_transcription.html templates
    @app.route('/templates/view_transcription.html')
    @login_required
    def view_transcription_template():
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ transcription.title }} - SpeechScribe</title>
    <link rel="icon" href="{{ url_for('static', filename='favicon.svg') }}" type="image/svg+xml">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body style="background-color: var(--dark-bg); color: var(--text-light);">
    <!-- Navigation Bar -->
    <nav class="navbar navbar-expand-lg navbar-dark" style="background-color: var(--dark-surface);">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center" href="{{ url_for('index') }}">
                <span class="fs-4 fw-bold text-primary me-2"><i class="fas fa-headphones"></i></span>
                <span>SpeechScribe</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">Home</a>
                    </li>
                    {% if current_user.is_authenticated %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('home') }}">Dashboard</a>
                    </li>
                    {% endif %}
                </ul>
                <ul class="navbar-nav">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fas fa-user-circle me-1"></i> {{ current_user.username }}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="navbarDropdown" style="background-color: var(--dark-card);">
                            <li><a class="dropdown-item text-light" href="{{ url_for('home') }}">Dashboard</a></li>
                            <li><hr class="dropdown-divider" style="border-color: rgba(255,255,255,0.1);"></li>
                            <li><a class="dropdown-item text-light" href="{{ url_for('logout') }}">Logout</a></li>
                        </ul>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('login') }}">Login</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('signup') }}">Sign Up</a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>
    
    <div class="container my-4">
        <div class="row mb-4">
            <div class="col-12">
                <nav aria-label="breadcrumb">
                    <ol class="breadcrumb">
                        <li class="breadcrumb-item"><a href="{{ url_for('home') }}">Home</a></li>
                        <li class="breadcrumb-item active" aria-current="page">Transcription</li>
                    </ol>
                </nav>
            </div>
        </div>

        <div class="row">
            <div class="col-md-12 mb-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h2>{{ transcription.title }}</h2>
                    <div>
                        <a href="{{ url_for('edit_transcription', id=transcription.id) }}" class="btn btn-outline-primary btn-sm me-2">
                            <i class="fas fa-edit me-1"></i> Edit
                        </a>
                        <a href="{{ url_for('download_pdf', id=transcription.id) }}" class="btn btn-outline-success btn-sm me-2">
                            <i class="fas fa-file-pdf me-1"></i> Download PDF
                        </a>
                        <button type="button" class="btn btn-outline-danger btn-sm" data-bs-toggle="modal" data-bs-target="#deleteModal">
                            <i class="fas fa-trash-alt me-1"></i> Delete
                        </button>
                    </div>
                </div>
                <div class="card mb-4">
                    <div class="card-header" style="background-color: var(--primary-color); color: white;">
                        <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>Transcription</h5>
                    </div>
                    <div class="card-body">
                        <p class="mb-0 transcription-text">{{ transcription.transcription_text }}</p>
                    </div>
                    <div class="card-footer text-muted">
                        <small>Created on {{ transcription.created_at.strftime('%B %d, %Y at %H:%M') }}</small>
                    </div>
                </div>

                {% if transcription.summary_text %}
                <div class="card">
                    <div class="card-header" style="background-color: var(--secondary-color); color: white;">
                        <h5 class="mb-0"><i class="fas fa-list-alt me-2"></i>Summary</h5>
                    </div>
                    <div class="card-body">
                        <p class="mb-0 summary-text">{{ transcription.summary_text }}</p>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="footer mt-auto py-3" style="background-color: var(--dark-surface);">
        <div class="container text-center">
            <span class="text-muted">&copy; 2025 SpeechScribe. All rights reserved.</span>
        </div>
    </footer>

    <!-- Delete Confirmation Modal -->
    <div class="modal fade" id="deleteModal" tabindex="-1" aria-labelledby="deleteModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="deleteModalLabel">Confirm Deletion</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    Are you sure you want to delete this transcription? This action cannot be undone.
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <form action="{{ url_for('delete_transcription', id=transcription.id) }}" method="post">
                        <button type="submit" class="btn btn-danger">Delete</button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''

    @app.route('/templates/edit_transcription.html')
    @login_required
    def edit_transcription_template():
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Transcription - SpeechScribe</title>
    <link rel="icon" href="{{ url_for('static', filename='favicon.svg') }}" type="image/svg+xml">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body style="background-color: var(--dark-bg); color: var(--text-light);">
    <!-- Navigation Bar -->
    <nav class="navbar navbar-expand-lg navbar-dark" style="background-color: var(--dark-surface);">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center" href="{{ url_for('index') }}">
                <span class="fs-4 fw-bold text-primary me-2"><i class="fas fa-headphones"></i></span>
                <span>SpeechScribe</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">Home</a>
                    </li>
                    {% if current_user.is_authenticated %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('home') }}">Dashboard</a>
                    </li>
                    {% endif %}
                </ul>
                <ul class="navbar-nav">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fas fa-user-circle me-1"></i> {{ current_user.username }}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="navbarDropdown" style="background-color: var(--dark-card);">
                            <li><a class="dropdown-item text-light" href="{{ url_for('home') }}">Dashboard</a></li>
                            <li><hr class="dropdown-divider" style="border-color: rgba(255,255,255,0.1);"></li>
                            <li><a class="dropdown-item text-light" href="{{ url_for('logout') }}">Logout</a></li>
                        </ul>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('login') }}">Login</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('signup') }}">Sign Up</a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>
    
    <div class="container my-4">
        <div class="row mb-4">
            <div class="col-12">
                <nav aria-label="breadcrumb">
                    <ol class="breadcrumb">
                        <li class="breadcrumb-item"><a href="{{ url_for('home') }}">Home</a></li>
                        <li class="breadcrumb-item"><a href="{{ url_for('view_transcription', id=transcription.id) }}">Transcription</a></li>
                        <li class="breadcrumb-item active" aria-current="page">Edit</li>
                    </ol>
                </nav>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-12">
                <div class="card">
                    <div class="card-header" style="background-color: var(--primary-color); color: white;">
                        <h4 class="mb-0"><i class="fas fa-edit me-2"></i>Edit Transcription</h4>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            {{ form.hidden_tag() }}
                            <div class="mb-4">
                                <label for="transcription" class="form-label">Transcription Text</label>
                                {{ form.transcription(class="form-control", rows=15) }}
                                {% for error in form.transcription.errors %}
                                <div class="invalid-feedback d-block">{{ error }}</div>
                                {% endfor %}
                                <div class="form-text">Edit the transcription text as needed. The summary will be automatically regenerated.</div>
                            </div>
                            <div class="d-flex justify-content-between">
                                <a href="{{ url_for('view_transcription', id=transcription.id) }}" class="btn btn-outline-secondary">
                                    <i class="fas fa-arrow-left me-1"></i> Cancel
                                </a>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save me-1"></i> {{ form.submit.label.text }}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="footer mt-auto py-3" style="background-color: var(--dark-surface);">
        <div class="container text-center">
            <span class="text-muted">&copy; 2025 SpeechScribe. All rights reserved.</span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''
