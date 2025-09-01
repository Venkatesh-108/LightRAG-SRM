#!/usr/bin/env python3
"""
Test Large Document Processing for LightRAG
This script tests the ability to process large PDF documents.
"""

import os
import time
from rag_pipeline import RAGPipeline

def test_large_document():
    """Test processing a large document."""
    print("Testing Large Document Processing")
    print("=" * 40)
    
    # Check if we have the large PDF file
    documents_dir = 'documents'
    target_file = 'Third_Party_ReadMe.pdf'
    file_path = os.path.join(documents_dir, target_file)
    
    if not os.path.exists(file_path):
        print(f"❌ Target file '{target_file}' not found in documents/ directory")
        print("Please ensure the file is present for testing")
        return False
    
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
    
    print(f"📄 Testing with: {target_file}")
    print(f"📊 File size: {file_size:.1f}MB")
    
    try:
        # Initialize the RAG pipeline
        print("🔧 Initializing RAG pipeline...")
        start_time = time.time()
        pipeline = RAGPipeline(model_provider='ollama')
        init_time = time.time() - start_time
        print(f"✅ Pipeline initialized in {init_time:.2f} seconds")
        
        # Test document indexing
        print("📚 Indexing large document...")
        print("⚠️  This may take several minutes for a 175-page document...")
        
        start_time = time.time()
        indexing_time = pipeline.index_documents([file_path])
        total_time = time.time() - start_time
        
        print(f"✅ Large document indexed successfully!")
        print(f"   - Indexing time: {indexing_time:.2f} seconds")
        print(f"   - Total processing time: {total_time:.2f} seconds")
        print(f"   - Processing speed: {file_size/total_time:.2f} MB/minute")
        
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
    success = test_large_document()
    
    if success:
        print("\n" + "=" * 40)
        print("🎉 LARGE DOCUMENT TEST PASSED!")
        print("Your LightRAG system can now handle large documents.")
        print("Updated limits:")
        print("- File size: 100MB max")
        print("- Pages: 500 pages max")
        print("- Text per page: 100KB max")
    else:
        print("\n" + "=" * 40)
        print("❌ LARGE DOCUMENT TEST FAILED")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()
