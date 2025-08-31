import os
import pickle
from typing import List
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
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text.strip():
                    texts.append(text)
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

    def index_documents(self, file_paths: List[str]):
        """Loads, splits, and indexes documents from the given file paths."""
        all_chunks = []
        
        for file_path in file_paths:
            # Load PDF
            pages = self._load_pdf(file_path)
            
            # Split into chunks
            for page_num, page_text in enumerate(pages):
                chunks = self._split_text(page_text)
                for chunk_num, chunk in enumerate(chunks):
                    doc = Document(
                        content=chunk,
                        metadata={
                            'file_path': file_path,
                            'page': page_num,
                            'chunk': chunk_num
                        }
                    )
                    all_chunks.append(doc)

        # Add to existing documents
        self.documents.extend(all_chunks)
        
        # Create embeddings
        texts = [doc.content for doc in self.documents]
        embeddings = self.embedder.encode(texts)
        
        # Create or update FAISS index
        if self.index is None:
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
        
        self.index.add(embeddings.astype('float32'))
        
        # Save index and documents
        faiss.write_index(self.index, os.path.join(self.vector_store_path, "index.faiss"))
        with open(os.path.join(self.vector_store_path, "documents.pkl"), 'wb') as f:
            pickle.dump(self.documents, f)

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
