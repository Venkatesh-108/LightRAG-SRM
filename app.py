import os
import threading
import time
from flask import Flask, request, jsonify, render_template, send_from_directory, session, Response, stream_with_context
from werkzeug.utils import secure_filename
from rag_pipeline import RAGPipeline
from config import Config
import json
from utils import allowed_file, check_system_resources, get_memory_info

app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)

# In-memory cache for RAG pipelines and initialization errors
_rag_pipelines = {}
_initialization_errors = {}

# Global flag to track indexing status
_indexing_in_progress = False
_indexing_thread = None

def run_with_timeout(func, args, timeout_seconds=300):
    """Run a function with a timeout using threading (Windows compatible)."""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        # Thread is still running, timeout occurred
        return None, TimeoutError("Operation timed out")
    
    if exception[0]:
        return None, exception[0]
    
    return result[0], None

def get_indexed_files():
    """Get list of files that are currently indexed in the RAG pipeline."""
    try:
        # Access the global pipeline directly to avoid request context issues
        global _rag_pipelines
        default_provider = Config.MODEL_PROVIDER
        
        if default_provider not in _rag_pipelines:
            return set()
        
        rag_pipeline = _rag_pipelines[default_provider]
        if not rag_pipeline or not rag_pipeline.documents:
            return set()
        
        # Get unique filenames from indexed documents
        indexed_files = set()
        for doc in rag_pipeline.documents:
            filename = doc.metadata.get('filename')
            if filename:
                indexed_files.add(filename)
        
        return indexed_files
    except Exception as e:
        print(f"Error getting indexed files: {e}")
        return set()

def get_unindexed_files():
    """Get list of PDF files in upload folder that are not indexed."""
    try:
        # Get all PDF files in upload folder
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            return []
        
        all_pdf_files = set()
        for filename in os.listdir(upload_folder):
            if filename.endswith('.pdf'):
                all_pdf_files.add(filename)
        
        # Get indexed files
        indexed_files = get_indexed_files()
        
        # Return files that are not indexed
        unindexed_files = all_pdf_files - indexed_files
        return list(unindexed_files)
    
    except Exception as e:
        print(f"Error getting unindexed files: {e}")
        return []

def auto_index_unindexed_files():
    """Automatically index any unindexed PDF files."""
    global _indexing_in_progress, _indexing_thread, _rag_pipelines
    
    if _indexing_in_progress:
        print("Indexing already in progress, skipping...")
        return
    
    try:
        _indexing_in_progress = True
        print("🔍 Checking for unindexed files...")
        
        # Get unindexed files
        unindexed_files = get_unindexed_files()
        
        if not unindexed_files:
            print("✅ All PDF files are already indexed!")
            return
        
        print(f"📄 Found {len(unindexed_files)} unindexed files: {unindexed_files}")
        
        # Get RAG pipeline directly from global cache
        default_provider = Config.MODEL_PROVIDER
        if default_provider not in _rag_pipelines:
            print(f"❌ RAG pipeline not available for {default_provider}")
            return
        
        rag_pipeline = _rag_pipelines[default_provider]
        
        # Prepare file paths
        upload_folder = app.config['UPLOAD_FOLDER']
        file_paths = [os.path.join(upload_folder, filename) for filename in unindexed_files]
        
        print(f"🚀 Starting automatic indexing of {len(file_paths)} files...")
        
        # Index the files
        start_time = time.time()
        indexing_time = rag_pipeline.index_documents(file_paths)
        end_time = time.time()
        
        print(f"✅ Automatic indexing completed in {indexing_time:.1f} seconds")
        print(f"📊 Total time including overhead: {end_time - start_time:.1f} seconds")
        
        # Verify indexing
        remaining_unindexed = get_unindexed_files()
        if not remaining_unindexed:
            print("✅ All files successfully indexed!")
        else:
            print(f"⚠️  {len(remaining_unindexed)} files still unindexed: {remaining_unindexed}")
            
    except Exception as e:
        print(f"❌ Error during automatic indexing: {e}")
    finally:
        _indexing_in_progress = False

def start_auto_indexing_thread():
    """Start automatic indexing in a background thread."""
    global _indexing_thread
    
    if _indexing_thread and _indexing_thread.is_alive():
        print("Auto-indexing thread already running...")
        return
    
    _indexing_thread = threading.Thread(target=auto_index_unindexed_files, daemon=True)
    _indexing_thread.start()
    print("🔄 Auto-indexing thread started...")

def initialize_pipelines():
    """Pre-initializes RAG pipelines for all supported providers at startup."""
    # Only initialize the default provider to avoid conflicts
    default_provider = Config.MODEL_PROVIDER
    print(f"Pre-initializing RAG pipeline for {default_provider}...")
    
    try:
        print(f"Initializing pipeline for {default_provider}...")
        pipeline = RAGPipeline(model_provider=default_provider)
        _rag_pipelines[default_provider] = pipeline
        print(f"Successfully initialized pipeline for {default_provider}.")
        print(f"DEBUG: Pipeline {default_provider} stored in _rag_pipelines: {default_provider in _rag_pipelines}")
        
        # Start automatic indexing after pipeline initialization
        print("🔄 Starting automatic indexing verification...")
        start_auto_indexing_thread()
        
    except ValueError as e:
        error_message = str(e)
        _initialization_errors[default_provider] = error_message
        print(f"Failed to initialize pipeline for {default_provider}: {error_message}")
    except Exception as e:
        error_message = f"Unexpected error initializing {default_provider}: {str(e)}"
        _initialization_errors[default_provider] = error_message
        print(f"Unexpected error initializing {default_provider}: {error_message}")
    
    print(f"DEBUG: Final pipeline state - Available: {list(_rag_pipelines.keys())}, Errors: {_initialization_errors}")

# Initialize pipelines when the app module is loaded
initialize_pipelines()

def get_rag_pipeline():
    """Retrieves a pre-initialized RAG pipeline based on the user's session."""
    model_provider = session.get('model_provider', Config.MODEL_PROVIDER)
    
    # Debug logging
    print(f"DEBUG: Requested model provider: {model_provider}")
    print(f"DEBUG: Available pipelines: {list(_rag_pipelines.keys())}")
    print(f"DEBUG: Initialization errors: {_initialization_errors}")
    
    # Check for initialization errors first
    if model_provider in _initialization_errors:
        print(f"DEBUG: Found initialization error for {model_provider}: {_initialization_errors[model_provider]}")
        return None, _initialization_errors[model_provider]
        
    # Retrieve the pre-loaded pipeline
    pipeline = _rag_pipelines.get(model_provider)
    if pipeline:
        print(f"DEBUG: Successfully retrieved pipeline for {model_provider}")
        return pipeline, None
    
    # Try to initialize the pipeline on-demand if it's not available
    print(f"DEBUG: Pipeline not found for {model_provider}, attempting to initialize...")
    try:
        pipeline = RAGPipeline(model_provider=model_provider)
        _rag_pipelines[model_provider] = pipeline
        print(f"DEBUG: Successfully initialized pipeline for {model_provider}")
        return pipeline, None
    except Exception as e:
        error_message = f"Failed to initialize pipeline for {model_provider}: {str(e)}"
        _initialization_errors[model_provider] = error_message
        print(f"DEBUG: {error_message}")
        return None, error_message

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
    global _rag_pipelines, _initialization_errors
    data = request.get_json()
    provider = data.get('provider')

    if provider not in ['ollama', 'openai']:
        return jsonify({'error': 'Invalid provider'}), 400

    # Store the provider selection in session
    session['model_provider'] = provider
    
    # Clear any previous initialization errors for this provider
    if provider in _initialization_errors:
        del _initialization_errors[provider]
    
    # Try to initialize the pipeline for the new provider
    try:
        print(f"Initializing pipeline for {provider}...")
        pipeline = RAGPipeline(model_provider=provider)
        _rag_pipelines[provider] = pipeline
        print(f"Successfully initialized pipeline for {provider}.")
        return jsonify({'success': True})
    except ValueError as e:
        error_message = str(e)
        _initialization_errors[provider] = error_message
        print(f"Failed to initialize pipeline for {provider}: {error_message}")
        return jsonify({'error': f'Failed to initialize {provider}: {error_message}'}), 400
    except Exception as e:
        error_message = f"Unexpected error initializing {provider}: {str(e)}"
        _initialization_errors[provider] = error_message
        print(error_message)
        return jsonify({'error': error_message}), 500

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

        # Check for duplicate filename
        if os.path.exists(file_path):
            return jsonify({'error': f'Document "{filename}" already exists.'}), 409
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        # Set max file size to 100MB (increased for large documents)
        max_size = 100 * 1024 * 1024  # 100MB in bytes
        if file_size > max_size:
            return jsonify({'error': f'File too large ({file_size / (1024*1024):.1f}MB). Maximum size is 100MB'}), 400
        
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        # Check available memory before processing
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            if available_gb < 2.0:  # Less than 2GB available
                return jsonify({'error': f'Insufficient memory available ({available_gb:.1f}GB). Please close other applications and try again.'}), 400
        except ImportError:
            # psutil not available, continue without memory check
            pass
        
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
        
        # Index the document with timeout protection
        try:
            print(f"Starting automatic indexing of {filename}...")
            result, error = run_with_timeout(rag_pipeline.index_documents, [[file_path]], timeout_seconds=300)
            
            if error:
                if isinstance(error, TimeoutError):
                    # Clean up saved file if processing times out
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    return jsonify({'error': 'Document processing timed out. The file may be too large or complex.'}), 408
                else:
                    # Clean up saved file if indexing fails
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    return jsonify({'error': f'Failed to index document: {str(error)}'}), 500
            
            indexing_time = result
            print(f"✅ Successfully indexed {filename} in {indexing_time:.1f} seconds")
            print(f"📚 Total documents in index: {len(rag_pipeline.documents)}")
                
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
                        # Get file size
                        file_size = os.path.getsize(file_path)
                        
                        # Get page count
                        page_count = 0
                        try:
                            import PyPDF2
                            with open(file_path, 'rb') as file:
                                pdf_reader = PyPDF2.PdfReader(file)
                                page_count = len(pdf_reader.pages)
                        except Exception as e:
                            print(f"Warning: Could not get page count for {filename}: {e}")
                            page_count = 0
                        
                        # Try to get enhanced metadata from RAG pipeline
                        title = filename.replace('.pdf', '').replace('_', ' ').title()
                        author = "Unknown"
                        is_indexed = False
                        
                        try:
                            # Get RAG pipeline to access document metadata
                            rag_pipeline, error = get_rag_pipeline()
                            if not error and rag_pipeline.documents:
                                # Find documents with this filename
                                doc_metadata = None
                                for doc in rag_pipeline.documents:
                                    if doc.metadata.get('filename') == filename:
                                        doc_metadata = doc.metadata
                                        is_indexed = True
                                        break
                                
                                if doc_metadata:
                                    title = doc_metadata.get('title', title)
                                    author = doc_metadata.get('author', author)
                        except Exception as e:
                            print(f"Warning: Could not get enhanced metadata for {filename}: {e}")
                        
                        documents.append({
                            'filename': filename,
                            'title': title,
                            'author': author,
                            'size': file_size,
                            'pages': page_count,
                            'is_indexed': is_indexed
                        })
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

@app.route('/system_health', methods=['GET'])
def system_health():
    """Check system resources and health."""
    try:
        resources = check_system_resources()
        memory_info = get_memory_info()
        
        # Get indexing status
        rag_pipeline, error = get_rag_pipeline()
        indexing_status = {
            'total_documents': len(rag_pipeline.documents) if rag_pipeline else 0,
            'indexed_files': list(set([doc.metadata.get('filename', 'Unknown') for doc in (rag_pipeline.documents if rag_pipeline else [])])),
            'pipeline_error': error
        }
        
        return jsonify({
            'resources': resources,
            'memory': memory_info,
            'indexing': indexing_status,
            'status': 'healthy' if resources.get('all_ok', False) else 'warning'
        })
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/indexing_status', methods=['GET'])
def indexing_status():
    """Get current indexing status."""
    try:
        rag_pipeline, error = get_rag_pipeline()
        if error:
            return jsonify({'error': error}), 400
        
        # Count documents by filename
        file_counts = {}
        for doc in rag_pipeline.documents:
            filename = doc.metadata.get('filename', 'Unknown')
            file_counts[filename] = file_counts.get(filename, 0) + 1
        
        # Get unindexed files
        unindexed_files = get_unindexed_files()
        
        return jsonify({
            'total_chunks': len(rag_pipeline.documents),
            'indexed_files': file_counts,
            'unindexed_files': unindexed_files,
            'indexing_in_progress': _indexing_in_progress,
            'status': 'ready'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auto_index', methods=['POST'])
def trigger_auto_index():
    """Manually trigger automatic indexing of unindexed files."""
    try:
        global _indexing_in_progress
        
        if _indexing_in_progress:
            return jsonify({
                'status': 'in_progress',
                'message': 'Indexing is already in progress. Please wait.'
            }), 200
        
        # Start auto-indexing in background thread
        start_auto_indexing_thread()
        
        return jsonify({
            'status': 'started',
            'message': 'Automatic indexing started in background.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check_indexing', methods=['GET'])
def check_indexing():
    """Check if all PDF files are indexed and return detailed status."""
    try:
        # Get all PDF files in upload folder
        upload_folder = app.config['UPLOAD_FOLDER']
        all_pdf_files = []
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                if filename.endswith('.pdf'):
                    all_pdf_files.append(filename)
        
        # Get indexed files
        indexed_files = get_indexed_files()
        
        # Get unindexed files
        unindexed_files = get_unindexed_files()
        
        # Check if any files need indexing
        needs_indexing = len(unindexed_files) > 0
        
        return jsonify({
            'all_pdf_files': all_pdf_files,
            'indexed_files': list(indexed_files),
            'unindexed_files': unindexed_files,
            'needs_indexing': needs_indexing,
            'indexing_in_progress': _indexing_in_progress,
            'total_files': len(all_pdf_files),
            'indexed_count': len(indexed_files),
            'unindexed_count': len(unindexed_files)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # In debug mode, Flask's reloader might run initialization twice.
    # The logic is safe, but this is a note for awareness.
    app.run(debug=True)
