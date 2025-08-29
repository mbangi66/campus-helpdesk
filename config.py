import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY','3cf9644e1f054dcc77e66ecf4fc51295e683a2129901db747b46307e06eba586')
    DB_HOST = os.getenv('DB_HOST','127.0.0.1')
    DB_USER = os.getenv('DB_USER','root')
    DB_PASS = os.getenv('DB_PASS','Rihan@#$%80')
    DB_NAME = os.getenv('DB_NAME','campus')