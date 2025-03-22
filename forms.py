from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class AudioUploadForm(FlaskForm):
    title = StringField('Title (Optional)', validators=[Length(max=100)])
    audio_file = FileField('Audio File')
    submit = SubmitField('Transcribe')

class TranscriptionEditForm(FlaskForm):
    transcription = TextAreaField('Transcription', validators=[DataRequired()])
    submit = SubmitField('Update Transcription')
    
class SummaryEditForm(FlaskForm):
    summary = TextAreaField('Summary', validators=[DataRequired()])
    submit = SubmitField('Update Summary')
