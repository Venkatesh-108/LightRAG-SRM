#!/usr/bin/env python3
"""
Test Second Document Processing for LightRAG
This script tests indexing and querying the second document.
"""

import os
import time
from rag_pipeline import RAGPipeline

def test_second_document():
    """Test processing the second document."""
    print("Testing Second Document Processing")
    print("=" * 40)
    
    # Check if we have the second PDF file
    documents_dir = 'documents'
    target_file = 'SRM_Upgrade_Guide.pdf'
    file_path = os.path.join(documents_dir, target_file)
    
    if not os.path.exists(file_path):
        print(f"❌ Target file '{target_file}' not found in documents/ directory")
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
        
        # Check current document count
        print(f"📚 Current documents in index: {len(pipeline.documents)}")
        
        # Test document indexing
        print("📚 Indexing second document...")
        start_time = time.time()
        indexing_time = pipeline.index_documents([file_path])
        total_time = time.time() - start_time
        
        print(f"✅ Second document indexed successfully!")
        print(f"   - Indexing time: {indexing_time:.2f} seconds")
        print(f"   - Total processing time: {total_time:.2f} seconds")
        
        # Check updated document count
        print(f"📚 Total documents in index: {len(pipeline.documents)}")
        
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
    success = test_second_document()
    
    if success:
        print("\n" + "=" * 40)
        print("🎉 SECOND DOCUMENT TEST PASSED!")
        print("Both documents are now indexed and queryable.")
    else:
        print("\n" + "=" * 40)
        print("❌ SECOND DOCUMENT TEST FAILED")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()
