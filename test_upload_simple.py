#!/usr/bin/env python3
"""
Simple Upload Test for LightRAG
This script tests the upload functionality by directly calling the RAG pipeline.
"""

import os
import time
from rag_pipeline import RAGPipeline

def test_upload():
    """Test the upload functionality."""
    print("Testing LightRAG Upload Functionality")
    print("=" * 40)
    
    # Check if we have any PDF files
    documents_dir = 'documents'
    if not os.path.exists(documents_dir):
        print("❌ Documents directory not found")
        return False
    
    pdf_files = [f for f in os.listdir(documents_dir) if f.endswith('.pdf')]
    if not pdf_files:
        print("❌ No PDF files found in documents/ directory")
        print("Please add a PDF file to test with")
        return False
    
    # Use the first PDF file
    test_file = os.path.join(documents_dir, pdf_files[0])
    file_size = os.path.getsize(test_file) / (1024 * 1024)  # MB
    
    print(f"📄 Testing with: {pdf_files[0]} ({file_size:.1f}MB)")
    
    try:
        # Initialize the RAG pipeline
        print("🔧 Initializing RAG pipeline...")
        start_time = time.time()
        pipeline = RAGPipeline(model_provider='ollama')
        init_time = time.time() - start_time
        print(f"✅ Pipeline initialized in {init_time:.2f} seconds")
        
        # Test document indexing
        print("📚 Indexing document...")
        start_time = time.time()
        indexing_time = pipeline.index_documents([test_file])
        total_time = time.time() - start_time
        
        print(f"✅ Document indexed successfully!")
        print(f"   - Indexing time: {indexing_time:.2f} seconds")
        print(f"   - Total processing time: {total_time:.2f} seconds")
        
        # Test a simple query
        print("🔍 Testing query functionality...")
        query = "What is this document about?"
        print(f"Query: {query}")
        
        response_chunks = []
        for chunk in pipeline.query(query):
            response_chunks.append(chunk)
            print(chunk, end='', flush=True)
        
        print("\n✅ Query test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test."""
    success = test_upload()
    
    if success:
        print("\n" + "=" * 40)
        print("🎉 ALL TESTS PASSED!")
        print("Your LightRAG system is working correctly.")
        print("You can now upload documents through the web interface.")
    else:
        print("\n" + "=" * 40)
        print("❌ TESTS FAILED")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()
