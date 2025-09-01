import os
from flask import Flask, request, jsonify, render_template, send_from_directory, session, Response, stream_with_context
from werkzeug.utils import secure_filename
import os
from rag_pipeline import RAGPipeline
from config import Config
import json
from utils import allowed_file

app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)

# In-memory cache for RAG pipelines and initialization errors
_rag_pipelines = {}
_initialization_errors = {}

def initialize_pipelines():
    """Pre-initializes RAG pipelines for all supported providers at startup."""
    supported_providers = ['ollama', 'openai']
    print("Pre-initializing RAG pipelines...")
    for provider in supported_providers:
        try:
            print(f"Initializing pipeline for {provider}...")
            pipeline = RAGPipeline(model_provider=provider)
            _rag_pipelines[provider] = pipeline
            print(f"Successfully initialized pipeline for {provider}.")
        except ValueError as e:
            error_message = str(e)
            _initialization_errors[provider] = error_message
            print(f"Failed to initialize pipeline for {provider}: {error_message}")

# Initialize pipelines when the app module is loaded
initialize_pipelines()

def get_rag_pipeline():
    """Retrieves a pre-initialized RAG pipeline based on the user's session."""
    model_provider = session.get('model_provider', Config.MODEL_PROVIDER)
    
    # Check for initialization errors first
    if model_provider in _initialization_errors:
        return None, _initialization_errors[model_provider]
        
    # Retrieve the pre-loaded pipeline
    pipeline = _rag_pipelines.get(model_provider)
    if pipeline:
        return pipeline, None
    
    # Fallback message if a pipeline is missing (should not happen with pre-initialization)
    return None, f"Pipeline for '{model_provider}' is not available or failed to initialize."

@app.route('/')
def index():
    return render_template('index.html', initial_view='chat')

@app.route('/settings')
def settings():
    return render_template('index.html', initial_view='settings')

@app.route('/get_model', methods=['GET'])
def get_current_model():
    # Return the provider from session, or default from config
    from config import Config
    current_provider = session.get('model_provider', Config.MODEL_PROVIDER)
    return jsonify({'provider': current_provider})

@app.route('/set_model', methods=['POST'])
def set_model_provider():
    global _rag_pipelines
    data = request.get_json()
    provider = data.get('provider')

    if provider not in ['ollama', 'openai']:
        return jsonify({'error': 'Invalid provider'}), 400

    # Store the provider selection in session
    session['model_provider'] = provider
    
    # Clear the cache for the specific provider to force a reload
    if provider in _rag_pipelines:
        del _rag_pipelines[provider]
    
    print(f"Model provider switched to: {provider}")
    
    return jsonify({'success': True})

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

@app.route('/documents/<path:filename>', methods=['GET'])
def serve_document(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    query_text = data.get('query')
    filename = data.get('filename')  # Get filename from request
    if not query_text:
        return jsonify({'error': 'Query text is required'}), 400

    rag_pipeline, error = get_rag_pipeline()
    if error:
        return jsonify({'error': error}), 400

    def generate():
        try:
            # Pass filename to the query method
            for chunk in rag_pipeline.query(query_text, filename=filename):
                yield chunk
        except Exception as e:
            # Log the error and yield a user-friendly message
            print(f"Error during response generation: {e}")
            yield "An error occurred while generating the response."

    return Response(stream_with_context(generate()), mimetype='text/plain')

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
            # Remove from filesystem
            os.remove(file_path)
            
            # Remove from vector store for all model providers
            global _rag_pipelines
            for provider in list(_rag_pipelines.keys()):
                try:
                    pipeline = _rag_pipelines[provider]
                    pipeline.delete_document(filename)
                except Exception as e:
                    print(f"Error removing {filename} from {provider} pipeline: {e}")
            
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
            if filename.endswith('.pdf'):
                os.remove(os.path.join(folder, filename))
        
        # Clear vector stores for all model providers
        global _rag_pipelines
        for provider in list(_rag_pipelines.keys()):
            try:
                pipeline = _rag_pipelines[provider]
                pipeline.clear_all_documents()
            except Exception as e:
                print(f"Error clearing {provider} pipeline: {e}")
        
        # Clear the pipeline cache
        _rag_pipelines = {}
        return jsonify({'success': 'All documents deleted successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # In debug mode, Flask's reloader might run initialization twice.
    # The logic is safe, but this is a note for awareness.
    app.run(debug=True)
