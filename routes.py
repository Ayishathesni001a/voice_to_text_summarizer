import os
import tempfile
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from models import User, Transcription
from forms import LoginForm, SignupForm, AudioUploadForm, TranscriptionEditForm
from transcription import transcribe_audio
from summarization import generate_summary
from pdf_generator import create_pdf
import logging

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
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Congratulations, you are now registered!')
            return redirect(url_for('login'))
        
        return render_template('signup.html', form=form)
    
    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))
    
    @app.route('/home')
    @login_required
    def home():
        form = AudioUploadForm()
        transcriptions = current_user.transcriptions.order_by(Transcription.created_at.desc()).all()
        return render_template('home.html', form=form, transcriptions=transcriptions)
    
    @app.route('/upload_audio', methods=['POST'])
    @login_required
    def upload_audio():
        form = AudioUploadForm()
        if form.validate_on_submit():
            try:
                # Get audio file from the form
                audio_file = form.audio_file.data
                
                if not audio_file:
                    flash('No audio file provided.')
                    return redirect(url_for('home'))
                
                # Save the file temporarily
                filename = secure_filename(audio_file.filename)
                temp_dir = tempfile.mkdtemp()
                file_path = os.path.join(temp_dir, filename)
                audio_file.save(file_path)
                
                # Process the audio file
                title = form.title.data if form.title.data else f"Transcription {len(current_user.transcriptions.all()) + 1}"
                transcription_text = transcribe_audio(file_path)
                
                if not transcription_text:
                    flash('Failed to transcribe the audio file.')
                    return redirect(url_for('home'))
                
                # Generate summary from the transcription
                summary = generate_summary(transcription_text)
                
                # Save to database
                transcription = Transcription(
                    title=title,
                    transcription_text=transcription_text,
                    summary_text=summary,
                    user_id=current_user.id
                )
                db.session.add(transcription)
                db.session.commit()
                
                flash('Audio successfully transcribed!')
                
                # Clean up the temporary file
                os.unlink(file_path)
                os.rmdir(temp_dir)
                
                return redirect(url_for('home'))
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
            # Check if the request has the file
            if 'audio' not in request.files:
                return jsonify({'error': 'No audio file provided'}), 400
            
            audio_file = request.files['audio']
            title = request.form.get('title', f"Recording {len(current_user.transcriptions.all()) + 1}")
            
            # Save the file temporarily
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, 'recording.wav')
            audio_file.save(file_path)
            
            # Process the audio file
            transcription_text = transcribe_audio(file_path)
            
            if not transcription_text:
                return jsonify({'error': 'Failed to transcribe the audio'}), 500
            
            # Generate summary from the transcription
            summary = generate_summary(transcription_text)
            
            # Save to database
            transcription = Transcription(
                title=title,
                transcription_text=transcription_text,
                summary_text=summary,
                user_id=current_user.id
            )
            db.session.add(transcription)
            db.session.commit()
            
            # Clean up the temporary file
            os.unlink(file_path)
            os.rmdir(temp_dir)
            
            return jsonify({
                'success': True,
                'transcription_id': transcription.id,
                'transcription': transcription_text,
                'summary': summary
            })
            
        except Exception as e:
            logger.error(f"Error in transcribe_recording: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/transcription/<int:id>')
    @login_required
    def view_transcription(id):
        transcription = Transcription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
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
    <title>{{ transcription.title }} - VoiceText</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body>
    <div class="container">
        <div class="row justify-content-center mt-5">
            <div class="col-lg-10">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h2>{{ transcription.title }}</h2>
                        <div>
                            <a href="{{ url_for('edit_transcription', id=transcription.id) }}" class="btn btn-primary btn-sm">Edit</a>
                            <a href="{{ url_for('download_pdf', id=transcription.id) }}" class="btn btn-success btn-sm">Download PDF</a>
                            <button type="button" class="btn btn-danger btn-sm" data-bs-toggle="modal" data-bs-target="#deleteModal">Delete</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="mb-4">
                            <h4>Summary</h4>
                            <div class="summary-text">{{ transcription.summary_text }}</div>
                        </div>
                        <div>
                            <h4>Full Transcription</h4>
                            <div class="transcription-text">{{ transcription.transcription_text }}</div>
                        </div>
                    </div>
                    <div class="card-footer text-muted">
                        Created on {{ transcription.created_at.strftime('%B %d, %Y at %H:%M') }}
                    </div>
                </div>
                <div class="mt-3">
                    <a href="{{ url_for('home') }}" class="btn btn-secondary">Back to Home</a>
                </div>
            </div>
        </div>
    </div>

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
    <title>Edit Transcription - VoiceText</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body>
    <div class="container">
        <div class="row justify-content-center mt-5">
            <div class="col-lg-10">
                <div class="card">
                    <div class="card-header">
                        <h2>Edit Transcription: {{ transcription.title }}</h2>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            {{ form.hidden_tag() }}
                            <div class="mb-3">
                                <label for="transcription" class="form-label">Transcription Text</label>
                                {{ form.transcription(class="form-control", rows=10) }}
                                {% for error in form.transcription.errors %}
                                <div class="invalid-feedback d-block">{{ error }}</div>
                                {% endfor %}
                            </div>
                            <div class="d-flex justify-content-between">
                                <a href="{{ url_for('view_transcription', id=transcription.id) }}" class="btn btn-secondary">Cancel</a>
                                {{ form.submit(class="btn btn-primary") }}
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''
