import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', '3cf9644e1f054dcc77e66ecf4fc51295e683a2129901db747b46307e06eba586')
    DATABASE_URL = os.path.join(BASE_DIR, 'campus_helpdesk.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
