import os
import pickle
import time
import urllib.parse
import gc
import psutil
from typing import List, Tuple
import PyPDF2
import faiss
import numpy as np
import openai
import ollama
import re

# Disable transformers model scanning on Windows to prevent hanging
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

from config import Config

class Document:
    def __init__(self, content: str, metadata: dict = None):
        self.content = content
        self.metadata = metadata or {}

class RAGPipeline:
    def __init__(self, model_provider: str = 'ollama'):
        self.model_provider = model_provider
        self.vector_store_path = Config.VECTOR_STORE_PATH
        self.embedder = None  # Lazy load the embedder
        self.index = None
        self.documents = []
        self._initialize_pipeline()
    
    def _get_embedder(self):
        """Lazy load the embedding model."""
        if self.embedder is None:
            print("Loading embedding model...")
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            print("Embedding model loaded successfully")
        return self.embedder

    def _check_memory_usage(self):
        """Check if system has enough available memory."""
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        if available_gb < 1.0:  # Less than 1GB available
            raise ValueError(f"Insufficient memory available: {available_gb:.2f}GB. Please close other applications and try again.")
        return available_gb

    def _extract_pdf_metadata(self, file_path: str) -> dict:
        """Extract PDF metadata including title, author, subject, etc."""
        metadata = {
            'title': None,
            'author': None,
            'subject': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
            'modification_date': None
        }
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract document info
                if pdf_reader.metadata:
                    info = pdf_reader.metadata
                    metadata['title'] = info.get('/Title', None)
                    metadata['author'] = info.get('/Author', None)
                    metadata['subject'] = info.get('/Subject', None)
                    metadata['creator'] = info.get('/Creator', None)
                    metadata['producer'] = info.get('/Producer', None)
                    metadata['creation_date'] = info.get('/CreationDate', None)
                    metadata['modification_date'] = info.get('/ModDate', None)
                
                # Clean up metadata (remove None values)
                metadata = {k: v for k, v in metadata.items() if v is not None}
                
        except Exception as e:
            print(f"Warning: Failed to extract PDF metadata: {e}")
        
        return metadata

    def _extract_document_title(self, pages: List[str]) -> str:
        """Extract document title from first page content."""
        if not pages:
            return None
        
        first_page = pages[0]
        lines = first_page.split('\n')
        
        # Look for title patterns in first few lines
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if not line:
                continue
            
            # Title detection patterns
            if self._is_document_title(line, i, lines):
                return line
        
        return None

    def _is_document_title(self, line: str, index: int, all_lines: List[str]) -> bool:
        """Detect if a line is likely a document title."""
        # Skip very short or very long lines
        if len(line) < 5 or len(line) > 200:
            return False
        
        # Title patterns
        patterns = [
            # All caps title (common in technical documents)
            r'^[A-Z][A-Z\s\-&()]+$',
            # Title case with proper capitalization
            r'^[A-Z][a-zA-Z\s\-&()]+$',
            # Title with version numbers
            r'^[A-Z][a-zA-Z\s\-&()]+(?:v?\d+\.?\d*\.?\d*)?$',
            # Title with company/product names
            r'^[A-Z][a-zA-Z\s\-&()]+(?:User|Installation|Configuration|Guide|Manual|Handbook)',
        ]
        
        for pattern in patterns:
            if re.match(pattern, line) and len(line.split()) <= 15:
                return True
        
        # Check if it's the first substantial line
        if index <= 2 and len(line.split()) >= 3:
            return True
        
        return False

    def _extract_enhanced_headings(self, text: str) -> List[dict]:
        """Extract all headings with their hierarchy levels."""
        headings = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            heading_level = self._get_heading_level(line, i, lines)
            if heading_level > 0:
                headings.append({
                    'text': line,
                    'level': heading_level,
                    'line_number': i
                })
        
        return headings

    def _get_heading_level(self, line: str, index: int, all_lines: List[str]) -> int:
        """Determine heading level (1-6, 0 for non-heading)."""
        # Level 1: Main document title
        if self._is_document_title(line, index, all_lines):
            return 1
        
        # Level 2: Chapter titles
        if re.match(r'^(?:Chapter|Section|Part)\s+\d+', line, re.IGNORECASE):
            return 2
        
        # Level 3: Numbered sections (1.1, 1.2, etc.)
        if re.match(r'^\d+\.\d+', line):
            return 3
        
        # Level 4: Sub-sections
        if re.match(r'^\d+\.\d+\.\d+', line):
            return 4
        
        # Level 5: All caps short lines
        if re.match(r'^[A-Z\s\-&()]{3,50}$', line) and len(line.split()) <= 8:
            return 5
        
        # Level 6: Title case short lines
        if re.match(r'^[A-Z][a-zA-Z\s\-&()]{3,50}$', line) and len(line.split()) <= 6:
            return 6
        
        return 0

    def _extract_document_info(self, file_path: str, pages: List[str]) -> dict:
        """Extract comprehensive document information."""
        document_info = {
            'filename': os.path.basename(file_path),
            'pdf_metadata': self._extract_pdf_metadata(file_path),
            'extracted_title': self._extract_document_title(pages),
            'headings': self._extract_enhanced_headings('\n'.join(pages)),
            'page_count': len(pages),
            'file_size': os.path.getsize(file_path)
        }
        
        # Determine the best title
        title_candidates = [
            document_info['pdf_metadata'].get('title'),
            document_info['extracted_title'],
            document_info['filename'].replace('.pdf', '').replace('_', ' ').title()
        ]
        
        document_info['best_title'] = next((title for title in title_candidates if title), 
                                          document_info['filename'])
        
        return document_info

    def _initialize_pipeline(self):
        """Initializes the retriever and generator based on the model provider."""
        # Check memory before loading
        self._check_memory_usage()
        
        # Load existing index if available
        index_path = os.path.join(self.vector_store_path, "index.faiss")
        docs_path = os.path.join(self.vector_store_path, "documents.pkl")
        
        if os.path.exists(index_path) and os.path.exists(docs_path):
            try:
                self.index = faiss.read_index(index_path)
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
            except Exception as e:
                print(f"Warning: Failed to load existing index: {e}")
                # Clear corrupted data
                self.index = None
                self.documents = []

        # Validate model provider
        if self.model_provider == 'openai':
            if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY == "your_openai_api_key_here":
                raise ValueError("OpenAI API key is not set. Please set it in the .env file.")

    def _load_pdf(self, file_path: str) -> List[str]:
        """Load and extract text from PDF file with enhanced structure detection."""
        texts = []
        try:
            # Check memory before processing
            self._check_memory_usage()

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

            # Check if file is too large (100MB limit)
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                raise ValueError(f"PDF file too large ({file_size / (1024*1024):.1f}MB). Maximum size is 100MB.")

            # Validate PDF structure before processing
            try:
                with open(file_path, 'rb') as file:
                    # Read the last 1024 bytes to check for EOF marker
                    file.seek(-1024, 2)  # Seek to end minus 1024 bytes
                    end_bytes = file.read()
                    if b'%%EOF' not in end_bytes:
                        print(f"Warning: PDF file may be corrupted - EOF marker not found: {file_path}")
                        print("Attempting to process anyway...")
            except Exception as e:
                print(f"Warning: Could not validate PDF structure: {e}")

            with open(file_path, 'rb') as file:
                try:
                    pdf_reader = PyPDF2.PdfReader(file)

                    # Check if PDF is encrypted
                    if pdf_reader.is_encrypted:
                        raise ValueError(f"PDF file is encrypted and cannot be processed: {file_path}")

                    # Check if PDF has pages
                    if len(pdf_reader.pages) == 0:
                        raise ValueError(f"PDF file has no pages: {file_path}")

                    # Check if PDF has too many pages (limit to 500 pages)
                    if len(pdf_reader.pages) > 500:
                        raise ValueError(f"PDF file has too many pages ({len(pdf_reader.pages)}). Maximum is 500 pages.")

                    print(f"Processing PDF with {len(pdf_reader.pages)} pages...")

                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            # Check memory periodically for large documents
                            if page_num % 20 == 0:
                                self._check_memory_usage()
                                print(f"Processed {page_num}/{len(pdf_reader.pages)} pages...")

                            text = page.extract_text()
                            if text and text.strip():
                                # Enhanced text processing
                                processed_text = self._process_page_text(text, page_num)
                                if processed_text.strip():
                                    texts.append(processed_text)
                        except Exception as e:
                            print(f"Warning: Failed to extract text from page {page_num + 1} of {file_path}: {str(e)}")
                            continue

                    if not texts:
                        raise ValueError(f"No readable text found in PDF: {file_path}")

                    print(f"Successfully extracted text from {len(texts)} pages")

                except PyPDF2.errors.PdfReadError as e:
                    error_msg = str(e)
                    if "EOF marker not found" in error_msg:
                        raise ValueError(f"PDF file appears to be corrupted or incomplete: {file_path}. "
                                       f"Error: {error_msg}. "
                                       f"Try re-downloading or re-saving the PDF file.")
                    else:
                        raise ValueError(f"Invalid or corrupted PDF file: {file_path}. Error: {error_msg}")
                except Exception as e:
                    raise ValueError(f"Failed to read PDF file: {file_path}. Error: {str(e)}")

        except Exception as e:
            # Re-raise with more context if it's not already our custom error
            if not isinstance(e, (FileNotFoundError, PermissionError, ValueError)):
                raise ValueError(f"Unexpected error loading PDF {file_path}: {str(e)}")
            raise

        return texts

    def _process_page_text(self, text: str, page_num: int) -> str:
        """Process page text to enhance structure and readability."""
        import re

        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single

        # Detect and preserve document structure
        lines = text.split('\n')
        processed_lines = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Detect headings (all caps, short lines, etc.)
            if self._is_heading(line, i, lines):
                # Add markdown heading markers
                processed_lines.append(f"## {line}")
            else:
                processed_lines.append(line)

        # Join lines with proper spacing
        processed_text = '\n\n'.join(processed_lines)

        # Limit text length to prevent memory issues
        if len(processed_text) > 100000:  # 100KB per page limit
            processed_text = processed_text[:100000] + "\n\n... [truncated]"

        return processed_text

    def _is_heading(self, line: str, index: int, all_lines: List[str]) -> bool:
        """Detect if a line is likely a heading."""
        import re

        # Skip very short or very long lines
        if len(line) < 3 or len(line) > 100:
            return False

        # Check for common heading patterns
        # 1. All caps with numbers (like "1. INTRODUCTION" or "CHAPTER 1")
        if re.match(r'^[A-Z0-9\s.,\-&()]+$', line) and len(line.split()) <= 10:
            return True

        # 2. Title case with numbers
        if re.match(r'^[A-Z][a-zA-Z0-9\s.,\-&()]+$', line) and len(line.split()) <= 8:
            return True

        # 3. Lines that are followed by more whitespace or shorter content
        if index < len(all_lines) - 1:
            next_line = all_lines[index + 1].strip() if index + 1 < len(all_lines) else ""
            if not next_line or len(next_line) < len(line) * 0.7:
                return True

        return False

    def _split_text(self, text: str, chunk_size: int = 1200, chunk_overlap: int = 150) -> List[str]:
        """Split text into chunks while preserving document structure."""
        chunks = []

        # Split text by paragraphs first (double newlines)
        paragraphs = text.split('\n\n')
        current_chunk = ""
        current_size = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            paragraph_size = len(paragraph)

            # If adding this paragraph would exceed chunk size and we already have content
            if current_size + paragraph_size > chunk_size and current_chunk:
                # Save current chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # Start new chunk with overlap from previous chunk
                if len(chunks) > 0:
                    # Get last part of previous chunk for overlap
                    overlap_text = chunks[-1][-chunk_overlap:] if len(chunks[-1]) > chunk_overlap else chunks[-1]
                    current_chunk = overlap_text + "\n\n" + paragraph
                    current_size = len(current_chunk)
                else:
                    current_chunk = paragraph
                    current_size = paragraph_size
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_size += paragraph_size + 2  # +2 for \n\n

        # Add the last chunk if it exists
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Limit total chunks to prevent memory issues
        if len(chunks) > 2000:
            chunks = chunks[:2000]

        return chunks

    def _create_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Create embeddings in batches to manage memory usage."""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Check memory before processing batch
            self._check_memory_usage()
            
            try:
                embedder = self._get_embedder()
                batch_embeddings = embedder.encode(batch)
                all_embeddings.append(batch_embeddings)
                
                # Force garbage collection after each batch
                gc.collect()
                
            except Exception as e:
                raise ValueError(f"Failed to create embeddings for batch {i//batch_size + 1}: {str(e)}")
        
        if not all_embeddings:
            raise ValueError("No embeddings were created")
            
        return np.vstack(all_embeddings)

    def index_documents(self, file_paths: List[str]) -> float:
        """Loads, splits, and indexes documents from the given file paths. Returns indexing time in seconds."""
        start_time = time.time()
        
        if not file_paths:
            raise ValueError("No file paths provided for indexing")
        
        # Check initial memory
        self._check_memory_usage()
        
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
                    
                    # Extract comprehensive document information
                    doc_info = self._extract_document_info(file_path, pages)
                    print(f"📄 Document: {doc_info['best_title']}")
                    print(f"   📝 Author: {doc_info['pdf_metadata'].get('author', 'Unknown')}")
                    print(f"   📊 Pages: {doc_info['page_count']}")
                    print(f"   📏 Size: {doc_info['file_size'] / 1024:.1f} KB")
                    
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
                                            'filename': doc_info['filename'],
                                            'title': doc_info['best_title'],
                                            'pdf_title': doc_info['pdf_metadata'].get('title'),
                                            'author': doc_info['pdf_metadata'].get('author'),
                                            'subject': doc_info['pdf_metadata'].get('subject'),
                                            'page_count': doc_info['page_count'],
                                            'file_size': doc_info['file_size']
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

            # Check memory before adding to existing documents
            self._check_memory_usage()

            # Add to existing documents
            self.documents.extend(all_chunks)
            
            # Create embeddings in batches
            try:
                texts = [doc.content for doc in self.documents]
                if not texts:
                    raise ValueError("No text content available for embedding")
                
                # Use batch processing for embeddings (smaller batch size for large documents)
                batch_size = 8 if len(texts) > 100 else 16
                embeddings = self._create_embeddings_batch(texts, batch_size=batch_size)
                
                if embeddings is None or embeddings.size == 0:
                    raise ValueError("Failed to generate embeddings")
                    
            except Exception as e:
                # Remove the chunks we just added if embedding fails
                self.documents = self.documents[:-len(all_chunks)]
                gc.collect()
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
                gc.collect()
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
                        embeddings = self._create_embeddings_batch(texts, batch_size=16)
                        dimension = embeddings.shape[1]
                        self.index = faiss.IndexFlatL2(dimension)
                        self.index.add(embeddings.astype('float32'))
                    except:
                        self.index = None
                else:
                    self.index = None
                gc.collect()
                raise ValueError(f"Failed to save processed documents: {str(e)}")
                
        except Exception as e:
            # Catch any unexpected errors
            if not isinstance(e, ValueError):
                raise ValueError(f"Unexpected error during document indexing: {str(e)}")
            raise
        finally:
            # Force garbage collection
            gc.collect()
        
        # Calculate and return indexing time
        end_time = time.time()
        indexing_time = end_time - start_time
        return indexing_time

    def _retrieve_documents(self, query: str, top_k: int = 5, filename: str = None) -> List[Document]:
        """Retrieve relevant documents for the query with enhanced relevance."""
        if self.index is None or len(self.documents) == 0:
            return []

        embedder = self._get_embedder()
        query_embedding = embedder.encode([query])
        distances, indices = self.index.search(query_embedding.astype('float32'), min(top_k * 2, len(self.documents)))

        retrieved_docs = []
        if not filename:
            # Get initial results
            for idx in indices[0]:
                if idx < len(self.documents):
                    retrieved_docs.append(self.documents[idx])

            # Re-rank based on content relevance (simple keyword matching)
            retrieved_docs = self._rerank_documents(query, retrieved_docs)[:top_k]
            return retrieved_docs
        else:
            # Filter by filename
            filtered_docs = []
            for idx in indices[0]:
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    if doc.metadata.get('filename') == filename:
                        filtered_docs.append(doc)

            # Re-rank filtered results
            filtered_docs = self._rerank_documents(query, filtered_docs)[:top_k]
            return filtered_docs

    def _rerank_documents(self, query: str, documents: List[Document]) -> List[Document]:
        """Re-rank documents based on query relevance."""
        if not documents:
            return documents

        # Simple keyword-based scoring
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_docs = []
        for doc in documents:
            content_lower = doc.content.lower()
            score = 0

            # Exact phrase match (highest weight)
            if query_lower in content_lower:
                score += 10

            # Word matches
            for word in query_words:
                if len(word) > 2:  # Skip short words
                    if word in content_lower:
                        score += 1

            # Heading matches (higher weight for headings)
            if "##" in doc.content and any(word in doc.content.lower() for word in query_words):
                score += 3

            scored_docs.append((score, doc))

        # Sort by score (descending) and return documents
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs]

    def _generate_response(self, query: str, context_docs: List[Document]):
        """Generate response using the selected model provider, yielding chunks for streaming."""
        # Organize context by document structure
        structured_context = self._organize_context(context_docs)

        prompt = f"""Please provide a concise and accurate answer to the following question based on the provided document context.

**Guidelines:**
- Answer based ONLY on the provided context
- If information is not available, say "This information is not available in the provided documents"
- Be specific and include key details from the source
- Keep the answer focused and relevant
- Use clear, direct language

**Context:**
{structured_context}

**Question:** {query}

**Answer:**"""

        if self.model_provider == 'openai':
            try:
                from openai import OpenAI
                client = OpenAI(api_key=Config.OPENAI_API_KEY)
                response_stream = client.chat.completions.create(
                    model=Config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a precise technical assistant. Answer questions using ONLY the provided context. Be specific with details, references, and page numbers. If information is missing, state it clearly. Structure answers with markdown for clarity. Focus on accuracy over completeness."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                for chunk in response_stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content, None
            except Exception as e:
                yield f"Error with OpenAI: {str(e)}.", None

        elif self.model_provider == 'ollama':
            try:
                response_stream = ollama.chat(
                    model=Config.OLLAMA_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a precise technical assistant. Answer questions using ONLY the provided context. Be specific with details, references, and page numbers. If information is missing, state it clearly. Structure answers with markdown for clarity. Focus on accuracy over completeness."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                for chunk in response_stream:
                    content = chunk['message']['content']
                    if content:
                        yield content, None
            except Exception as e:
                yield f"Error with Ollama: {str(e)}. Make sure Ollama is running and the model '{Config.OLLAMA_MODEL}' is available.", None

    def _organize_context(self, context_docs: List[Document]) -> str:
        """Organize context documents by source and structure, focusing on most relevant content."""
        if not context_docs:
            return "No context available."

        organized_parts = []

        # Group by filename and find the most relevant document per file
        docs_by_file = {}
        for doc in context_docs:
            filename = doc.metadata.get('filename', 'Unknown')
            if filename not in docs_by_file:
                docs_by_file[filename] = []
            docs_by_file[filename].append(doc)

        # For each file, select the most relevant document (first one after ranking)
        for filename, docs in docs_by_file.items():
            if docs:  # Only process if we have documents
                # Sort by chunk number to get sequential content
                docs_sorted = sorted(docs, key=lambda x: x.metadata.get('chunk', 0))

                # Use the first (most relevant) document from this file
                doc = docs_sorted[0]
                page = doc.metadata.get('page', 0) + 1

                organized_parts.append(f"## From {filename} (Page {page}):")
                content = doc.content.strip()
                organized_parts.append(content)
                organized_parts.append("")  # Empty line for spacing

        return "\n".join(organized_parts)

    def query(self, query_text: str, filename: str = None):
        """Performs a RAG query, yielding the response and performance metrics."""
        if self.index is None or len(self.documents) == 0:
            yield "No documents have been indexed yet. Please upload some PDF documents first."
            return

        # 1. Retrieve documents
        retrieval_start_time = time.time()
        relevant_docs = self._retrieve_documents(query_text, top_k=5, filename=filename)
        retrieval_end_time = time.time()
        retrieval_time = retrieval_end_time - retrieval_start_time

        if not relevant_docs:
            yield "No relevant documents found for your query."
            return

        # 2. Generate response and stream it
        generation_start_time = time.time()
        first_token_time = None
        ttft = 0
        full_response = ""
        sources_content = ""
        
        response_generator = self._generate_response(query_text, relevant_docs)

        for chunk, marker in response_generator:
            if first_token_time is None:
                first_token_time = time.time()
                ttft = first_token_time - generation_start_time

            full_response += chunk
            yield chunk

        generation_end_time = time.time()
        # Ensure generation_time is not zero to avoid division errors
        generation_time = (generation_end_time - generation_start_time) or 1e-6

        # Calculate tokens per second (approximating 1 token ~= 4 chars)
        total_chars = len(full_response)
        estimated_tokens = total_chars / 4
        tokens_per_sec = estimated_tokens / generation_time

        # Determine model name
        if self.model_provider == 'openai':
            model_name = Config.OPENAI_MODEL
        else:
            model_name = Config.OLLAMA_MODEL

        # Generate and yield only the most relevant source
        if relevant_docs:
            # Find the most relevant document (first in re-ranked list)
            primary_doc = relevant_docs[0]
            filename = primary_doc.metadata.get('filename', 'Unknown')
            page = primary_doc.metadata.get('page', -1) + 1

            # Create single source citation
            encoded_filename = urllib.parse.quote(filename)
            source_text = f"\n\n---\n**Source:** [{filename}](/documents/{encoded_filename}#page={page}) (Page {page})"
            yield source_text

        performance_data = (
            f"\n\n---\n"
            f"*Model: {model_name} | "
            f"TTFT: {ttft:.2f}s | "
            f"Tokens/sec: {tokens_per_sec:.2f} | "
            f"Retrieval: {retrieval_time:.2f}s | "
            f"Generation: {generation_time:.2f}s*"
        )
        yield performance_data

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
