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
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        rag_pipeline, error = get_rag_pipeline()
        if error:
            return jsonify({'error': error}), 400
        
        rag_pipeline.index_documents([file_path])
        
        return jsonify({'success': f'File "{filename}" uploaded and indexed successfully.'}), 200
    else:
        return jsonify({'error': 'File type not allowed'}), 400

@app.route('/documents', methods=['GET'])
def get_documents():
    documents = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.pdf')]
    return jsonify(documents)

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
