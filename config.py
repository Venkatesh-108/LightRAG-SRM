import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-secret-key'
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'documents')
    ALLOWED_EXTENSIONS = {'pdf'}
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3')
    VECTOR_STORE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vector_store')

# Create the upload and vector store directories if they don't exist
if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER)

if not os.path.exists(Config.VECTOR_STORE_PATH):
    os.makedirs(Config.VECTOR_STORE_PATH)
