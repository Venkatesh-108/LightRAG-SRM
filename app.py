import os
from flask import Flask, request, jsonify, render_template, session
from werkzeug.utils import secure_filename

from config import Config
from rag_pipeline import RAGPipeline
from utils import allowed_file

app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)

# A simple in-memory cache for RAG pipelines
_rag_pipelines = {}

def get_rag_pipeline():
    model_provider = session.get('model_provider', 'ollama')
    
    # Check if the pipeline for the current model is already cached
    if model_provider in _rag_pipelines:
        return _rag_pipelines[model_provider], None

    # If not, create a new one and cache it
    try:
        pipeline = RAGPipeline(model_provider=model_provider)
        _rag_pipelines[model_provider] = pipeline
        return pipeline, None
    except ValueError as e:
        return None, str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Check file type
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Only PDF files are supported.'}), 400
        
        # Secure filename and check for duplicates
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Ensure upload folder exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Check file size (optional - you can set a limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        # Set max file size to 50MB (adjust as needed)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if file_size > max_size:
            return jsonify({'error': f'File too large. Maximum size is {max_size // (1024*1024)}MB'}), 400
        
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        # Save file
        try:
            file.save(file_path)
        except Exception as e:
            return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
        
        # Verify file was saved correctly
        if not os.path.exists(file_path):
            return jsonify({'error': 'File was not saved properly'}), 500
        
        # Get RAG pipeline
        rag_pipeline, error = get_rag_pipeline()
        if error:
            # Clean up saved file if pipeline initialization fails
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': f'Pipeline initialization failed: {error}'}), 400
        
        # Index the document
        try:
            indexing_time = rag_pipeline.index_documents([file_path])
        except Exception as e:
            # Clean up saved file if indexing fails
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': f'Failed to index document: {str(e)}'}), 500
        
        return jsonify({
            'success': f'File "{filename}" uploaded in {indexing_time:.1f}s.',
            'indexing_time': indexing_time
        }), 200
        
    except Exception as e:
        # Catch any unexpected errors
        return jsonify({'error': f'Unexpected error during upload: {str(e)}'}), 500

@app.route('/documents', methods=['GET'])
def get_documents():
    try:
        # Check if upload folder exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            return jsonify([])
        
        # Check if folder is readable
        if not os.access(app.config['UPLOAD_FOLDER'], os.R_OK):
            return jsonify({'error': 'Cannot access upload folder'}), 500
        
        documents = []
        try:
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    # Check if file still exists and is readable
                    if os.path.exists(file_path) and os.access(file_path, os.R_OK):
                        documents.append(filename)
        except Exception as e:
            return jsonify({'error': f'Failed to list documents: {str(e)}'}), 500
        
        return jsonify(documents)
        
    except Exception as e:
        return jsonify({'error': f'Unexpected error retrieving documents: {str(e)}'}), 500

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    query_text = data.get('query')
    if not query_text:
        return jsonify({'error': 'Query text is required'}), 400

    rag_pipeline, error = get_rag_pipeline()
    if error:
        return jsonify({'error': error}), 400

    response = rag_pipeline.query(query_text)
    return jsonify({'response': response})

@app.route('/select_model', methods=['POST'])
def select_model():
    data = request.get_json()
    model_provider = data.get('model_provider')
    if model_provider not in ['ollama', 'openai']:
        return jsonify({'error': 'Invalid model provider'}), 400
    
    session['model_provider'] = model_provider
    # Pre-initialize the pipeline for the selected model
    get_rag_pipeline()

    return jsonify({'success': f'Model switched to {model_provider}.'}) 

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            # Here you might want to re-index your documents if the pipeline supports removal
            return jsonify({'success': f'File "{filename}" deleted successfully.'}), 200
        else:
            return jsonify({'error': 'File not found.'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_all', methods=['DELETE'])
def delete_all_files():
    try:
        folder = app.config['UPLOAD_FOLDER']
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        # Re-initialize or clear the RAG pipeline
        global _rag_pipelines
        _rag_pipelines = {}
        return jsonify({'success': 'All documents deleted successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
