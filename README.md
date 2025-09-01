# SRM AI Doc Assist (LightRAG App)

This is a Retrieval-Augmented Generation (RAG) application built with Python, Flask, and LightRAG. It provides a simple web interface to upload PDF documents and ask questions about their content. The application supports both Ollama (for local models like Llama 3) and OpenAI APIs.

## Features

- **PDF Document Upload**: Easily upload and index PDF files.
- **Dual LLM Support**: Switch between using a local Ollama model or the OpenAI API.
- **Simple Chat Interface**: Ask questions about your documents in a clean, intuitive chat UI.
- **Document Library**: View and manage your uploaded documents.
- **Lightweight and Performant**: Designed to run efficiently on a standard laptop. 

## Project Structure

```
/LightRag
|-- /documents/            # Stores uploaded PDF files
|-- /static/
|   |-- /css/style.css     # Frontend styles
|   `-- /js/main.js        # Frontend JavaScript
|-- /templates/
|   `-- index.html         # Main HTML file for the UI
|-- /vector_store/         # Stores the FAISS vector index
|-- /venv/                 # Python virtual environment
|-- .env                   # Environment variables (API keys, etc.)
|-- app.py                 # Main Flask application
|-- config.py              # Application configuration settings
|-- rag_pipeline.py        # Core RAG logic using LightRAG
|-- requirements.txt       # Python dependencies
`-- utils.py               # Utility functions
```

## Setup and Installation

### 1. Create a Virtual Environment

First, set up a Python virtual environment to keep dependencies isolated.

```bash
# Create the virtual environment
python -m venv venv
```

### 2. Install Dependencies

Activate the virtual environment and install the required packages from `requirements.txt`.

```bash
# Activate the virtual environment (on Windows)
.\venv\Scripts\activate

# Install the packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory and add your configuration. If you plan to use OpenAI, you must provide an API key.

```
OPENAI_API_KEY="your_openai_api_key_here"
OLLAMA_MODEL="llama3" # Or any other model you have installed with Ollama
```

## How to Run the Application

With the virtual environment activated, run the `app.py` file to start the Flask web server.

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`.

## How to Use

1.  **Upload Documents**: Navigate to the **Documents** tab and click **Upload PDF**.
2.  **Select a Model**: Use the dropdown menu in the **Documents** view to switch between `Ollama` and `OpenAI`.
3.  **Start a Chat**: Go to the **Chats** tab and click **+ New Chat** to ask general questions, or click **Chat about this document** on a document card to focus the conversation.
