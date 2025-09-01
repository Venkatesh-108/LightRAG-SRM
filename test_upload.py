#!/usr/bin/env python3
"""
Test Upload Script for LightRAG
This script tests the document upload functionality safely.
"""

import os
import sys
import time
from rag_pipeline import RAGPipeline

def test_small_upload():
    """Test uploading a small document to verify the system works."""
    print("Testing document upload functionality...")
    
    # Create a small test PDF (if you have one in documents folder)
    test_files = []
    documents_dir = 'documents'
    
    if os.path.exists(documents_dir):
        for file in os.listdir(documents_dir):
            if file.endswith('.pdf'):
                test_files.append(os.path.join(documents_dir, file))
                break
    
    if not test_files:
        print("No PDF files found in documents/ folder.")
        print("Please add a small PDF file (<5MB) to test with.")
        return False
    
    test_file = test_files[0]
    file_size = os.path.getsize(test_file) / (1024 * 1024)  # MB
    
    print(f"Testing with: {os.path.basename(test_file)} ({file_size:.1f}MB)")
    
    try:
        # Initialize pipeline
        print("Initializing RAG pipeline...")
        pipeline = RAGPipeline(model_provider='ollama')
        
        # Test indexing
        print("Testing document indexing...")
        start_time = time.time()
        indexing_time = pipeline.index_documents([test_file])
        end_time = time.time()
        
        print(f"✅ Success! Document indexed in {indexing_time:.1f} seconds")
        print(f"Total processing time: {end_time - start_time:.1f} seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

def main():
    """Run the upload test."""
    print("LightRAG Upload Test")
    print("=" * 30)
    
    # Check if we have any PDF files
    if not os.path.exists('documents') or not any(f.endswith('.pdf') for f in os.listdir('documents')):
        print("No PDF files found in documents/ folder.")
        print("Please add a small PDF file (<5MB) to test with.")
        print("\nYou can:")
        print("1. Copy a small PDF to the documents/ folder")
        print("2. Use the web interface to upload a file")
        print("3. Run this test again after adding a file")
        return
    
    success = test_small_upload()
    
    if success:
        print("\n✅ Upload test completed successfully!")
        print("Your system should now handle document uploads without crashing.")
        print("\nNext steps:")
        print("1. Try uploading documents through the web interface")
        print("2. Start with smaller files (<10MB)")
        print("3. Monitor system resources during upload")
    else:
        print("\n❌ Upload test failed.")
        print("Please check the error message above and try again.")

if __name__ == "__main__":
    main()
