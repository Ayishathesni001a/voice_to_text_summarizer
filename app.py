import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from flask_migrate import Migrate  # ✅ Import Migrate

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_session_secret")
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "fallback_flask_secret")

# ✅ Print for debug (remove in production)
print(f"SECRET_KEY: {app.config['SECRET_KEY']}")

# ✅ Database configuration
# Fallback URI if DATABASE_URL is not set
default_db_url = "postgresql://postgres:123456789@localhost/speechrec"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", default_db_url)

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database **before** Migrate
db.init_app(app)  # ✅ This is required before `Migrate(app, db)`

# Initialize Flask-Migrate
migrate = Migrate(app, db)  # ✅ Now Migrate can detect `db`

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import and register routes
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    import models  # noqa: F401
    
    # ✅ No need for `db.create_all()` when using Flask-Migrate

    # Import routes after db initialization to avoid circular imports
    from routes import register_routes
    register_routes(app)

    logger.info("App initialized successfully")
