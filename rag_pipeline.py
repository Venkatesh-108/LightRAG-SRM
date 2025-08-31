import os
import pickle
import time
from typing import List, Tuple
import PyPDF2
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import openai
import ollama

from config import Config

class Document:
    def __init__(self, content: str, metadata: dict = None):
        self.content = content
        self.metadata = metadata or {}

class RAGPipeline:
    def __init__(self, model_provider: str = 'ollama'):
        self.model_provider = model_provider
        self.vector_store_path = Config.VECTOR_STORE_PATH
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = None
        self.documents = []
        self._initialize_pipeline()

    def _initialize_pipeline(self):
        """Initializes the retriever and generator based on the model provider."""
        # Load existing index if available
        index_path = os.path.join(self.vector_store_path, "index.faiss")
        docs_path = os.path.join(self.vector_store_path, "documents.pkl")
        
        if os.path.exists(index_path) and os.path.exists(docs_path):
            self.index = faiss.read_index(index_path)
            with open(docs_path, 'rb') as f:
                self.documents = pickle.load(f)

        # Validate model provider
        if self.model_provider == 'openai':
            if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY == "your_openai_api_key_here":
                raise ValueError("OpenAI API key is not set. Please set it in the .env file.")

    def _load_pdf(self, file_path: str) -> List[str]:
        """Load and extract text from PDF file."""
        texts = []
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                raise PermissionError(f"Cannot read PDF file: {file_path}")
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise ValueError(f"PDF file is empty: {file_path}")
            
            with open(file_path, 'rb') as file:
                try:
                    pdf_reader = PyPDF2.PdfReader(file)
                    
                    # Check if PDF is encrypted
                    if pdf_reader.is_encrypted:
                        raise ValueError(f"PDF file is encrypted and cannot be processed: {file_path}")
                    
                    # Check if PDF has pages
                    if len(pdf_reader.pages) == 0:
                        raise ValueError(f"PDF file has no pages: {file_path}")
                    
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            text = page.extract_text()
                            if text and text.strip():
                                texts.append(text)
                        except Exception as e:
                            print(f"Warning: Failed to extract text from page {page_num + 1} of {file_path}: {str(e)}")
                            continue
                    
                    if not texts:
                        raise ValueError(f"No readable text found in PDF: {file_path}")
                        
                except PyPDF2.errors.PdfReadError as e:
                    raise ValueError(f"Invalid or corrupted PDF file: {file_path}. Error: {str(e)}")
                except Exception as e:
                    raise ValueError(f"Failed to read PDF file: {file_path}. Error: {str(e)}")
                    
        except Exception as e:
            # Re-raise with more context if it's not already our custom error
            if not isinstance(e, (FileNotFoundError, PermissionError, ValueError)):
                raise ValueError(f"Unexpected error loading PDF {file_path}: {str(e)}")
            raise
            
        return texts

    def _split_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[str]:
        """Split text into chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - chunk_overlap
        return chunks

    def index_documents(self, file_paths: List[str]) -> float:
        """Loads, splits, and indexes documents from the given file paths. Returns indexing time in seconds."""
        start_time = time.time()
        
        if not file_paths:
            raise ValueError("No file paths provided for indexing")
        
        all_chunks = []
        processed_files = []
        
        try:
            # Ensure vector store directory exists
            os.makedirs(self.vector_store_path, exist_ok=True)
            
            for file_path in file_paths:
                try:
                    # Load PDF
                    pages = self._load_pdf(file_path)
                    processed_files.append(file_path)
                    
                    # Split into chunks
                    for page_num, page_text in enumerate(pages):
                        try:
                            chunks = self._split_text(page_text)
                            for chunk_num, chunk in enumerate(chunks):
                                if chunk.strip():  # Only add non-empty chunks
                                    doc = Document(
                                        content=chunk,
                                        metadata={
                                            'file_path': file_path,
                                            'page': page_num,
                                            'chunk': chunk_num,
                                            'filename': os.path.basename(file_path)
                                        }
                                    )
                                    all_chunks.append(doc)
                        except Exception as e:
                            print(f"Warning: Failed to process page {page_num + 1} of {file_path}: {str(e)}")
                            continue
                            
                except Exception as e:
                    # Log the error but continue with other files
                    error_msg = f"Failed to process file {file_path}: {str(e)}"
                    print(f"Error: {error_msg}")
                    # If this is the only file, re-raise the error
                    if len(file_paths) == 1:
                        raise ValueError(error_msg)
                    continue

            if not all_chunks:
                raise ValueError("No valid content found in any of the provided files")

            # Add to existing documents
            self.documents.extend(all_chunks)
            
            # Create embeddings
            try:
                texts = [doc.content for doc in self.documents]
                if not texts:
                    raise ValueError("No text content available for embedding")
                
                embeddings = self.embedder.encode(texts)
                
                if embeddings is None or embeddings.size == 0:
                    raise ValueError("Failed to generate embeddings")
                    
            except Exception as e:
                # Remove the chunks we just added if embedding fails
                self.documents = self.documents[:-len(all_chunks)]
                raise ValueError(f"Failed to create embeddings: {str(e)}")
            
            # Create or update FAISS index
            try:
                if self.index is None:
                    dimension = embeddings.shape[1]
                    self.index = faiss.IndexFlatL2(dimension)
                
                self.index.add(embeddings.astype('float32'))
                
            except Exception as e:
                # Remove the chunks we just added if indexing fails
                self.documents = self.documents[:-len(all_chunks)]
                raise ValueError(f"Failed to update FAISS index: {str(e)}")
            
            # Save index and documents
            try:
                index_path = os.path.join(self.vector_store_path, "index.faiss")
                docs_path = os.path.join(self.vector_store_path, "documents.pkl")
                
                # Create backup of existing files
                backup_index = None
                backup_docs = None
                if os.path.exists(index_path):
                    backup_index = index_path + ".backup"
                    os.rename(index_path, backup_index)
                if os.path.exists(docs_path):
                    backup_docs = docs_path + ".backup"
                    os.rename(docs_path, backup_docs)
                
                try:
                    faiss.write_index(self.index, index_path)
                    with open(docs_path, 'wb') as f:
                        pickle.dump(self.documents, f)
                    
                    # Remove backups if save was successful
                    if backup_index and os.path.exists(backup_index):
                        os.remove(backup_index)
                    if backup_docs and os.path.exists(backup_docs):
                        os.remove(backup_docs)
                        
                except Exception as e:
                    # Restore backups if save failed
                    if backup_index and os.path.exists(backup_index):
                        os.rename(backup_index, index_path)
                    if backup_docs and os.path.exists(backup_docs):
                        os.rename(backup_docs, docs_path)
                    raise ValueError(f"Failed to save index and documents: {str(e)}")
                    
            except Exception as e:
                # Remove the chunks we just added if saving fails
                self.documents = self.documents[:-len(all_chunks)]
                # Try to rebuild the index without the failed chunks
                if len(self.documents) > 0:
                    try:
                        texts = [doc.content for doc in self.documents]
                        embeddings = self.embedder.encode(texts)
                        dimension = embeddings.shape[1]
                        self.index = faiss.IndexFlatL2(dimension)
                        self.index.add(embeddings.astype('float32'))
                    except:
                        self.index = None
                else:
                    self.index = None
                raise ValueError(f"Failed to save processed documents: {str(e)}")
                
        except Exception as e:
            # Catch any unexpected errors
            if not isinstance(e, ValueError):
                raise ValueError(f"Unexpected error during document indexing: {str(e)}")
            raise
        
        # Calculate and return indexing time
        end_time = time.time()
        indexing_time = end_time - start_time
        return indexing_time

    def _retrieve_documents(self, query: str, top_k: int = 3) -> List[Document]:
        """Retrieve relevant documents for the query."""
        if self.index is None or len(self.documents) == 0:
            return []
        
        query_embedding = self.embedder.encode([query])
        distances, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        retrieved_docs = []
        for idx in indices[0]:
            if idx < len(self.documents):
                retrieved_docs.append(self.documents[idx])
        
        return retrieved_docs

    def _generate_response(self, query: str, context_docs: List[Document]) -> str:
        """Generate response using the selected model provider."""
        context = "\n\n".join([doc.content for doc in context_docs])
        
        prompt = f"""Based on the following context, please answer the question.

Context:
{context}

Question: {query}

Answer:"""

        if self.model_provider == 'openai':
            try:
                from openai import OpenAI
                client = OpenAI(api_key=Config.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error with OpenAI API: {str(e)}"
        
        elif self.model_provider == 'ollama':
            try:
                response = ollama.chat(
                    model=Config.OLLAMA_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response['message']['content']
            except Exception as e:
                return f"Error with Ollama: {str(e)}. Make sure Ollama is running and the model '{Config.OLLAMA_MODEL}' is available."

    def query(self, query_text: str) -> str:
        """Performs a RAG query and returns the answer."""
        if self.index is None or len(self.documents) == 0:
            return "No documents have been indexed yet. Please upload some PDF documents first."
        
        # Retrieve relevant documents
        relevant_docs = self._retrieve_documents(query_text)
        
        if not relevant_docs:
            return "No relevant documents found for your query."
        
        # Generate response
        return self._generate_response(query_text, relevant_docs)

    def delete_document(self, filename: str) -> bool:
        """Remove a specific document from the vector store."""
        if not self.documents:
            return False
        
        # Find documents with matching filename
        docs_to_remove = []
        remaining_docs = []
        
        for i, doc in enumerate(self.documents):
            if doc.metadata.get('filename') == filename:
                docs_to_remove.append(i)
            else:
                remaining_docs.append(doc)
        
        if not docs_to_remove:
            return False
        
        # Update documents list
        self.documents = remaining_docs
        
        # Rebuild index with remaining documents
        if self.documents:
            try:
                texts = [doc.content for doc in self.documents]
                embeddings = self.embedder.encode(texts)
                dimension = embeddings.shape[1]
                self.index = faiss.IndexFlatL2(dimension)
                self.index.add(embeddings.astype('float32'))
                
                # Save updated index and documents
                self._save_index_and_docs()
            except Exception as e:
                print(f"Error rebuilding index after document deletion: {e}")
                return False
        else:
            # No documents left, clear everything
            self.index = None
            self._clear_vector_store()
        
        return True

    def clear_all_documents(self) -> bool:
        """Remove all documents from the vector store."""
        self.documents = []
        self.index = None
        return self._clear_vector_store()

    def _save_index_and_docs(self):
        """Save the current index and documents to disk."""
        try:
            index_path = os.path.join(self.vector_store_path, "index.faiss")
            docs_path = os.path.join(self.vector_store_path, "documents.pkl")
            
            if self.index is not None:
                faiss.write_index(self.index, index_path)
            
            with open(docs_path, 'wb') as f:
                pickle.dump(self.documents, f)
        except Exception as e:
            raise ValueError(f"Failed to save index and documents: {str(e)}")

    def _clear_vector_store(self) -> bool:
        """Clear all vector store files."""
        try:
            index_path = os.path.join(self.vector_store_path, "index.faiss")
            docs_path = os.path.join(self.vector_store_path, "documents.pkl")
            
            if os.path.exists(index_path):
                os.remove(index_path)
            if os.path.exists(docs_path):
                os.remove(docs_path)
            
            return True
        except Exception as e:
            print(f"Error clearing vector store: {e}")
            return False
