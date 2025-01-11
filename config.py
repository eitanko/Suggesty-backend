from dotenv import load_dotenv
import os

class Config:
    load_dotenv()

    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    S3_BUCKET_NAME = 'suggesty-screenshots'
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_KEY")