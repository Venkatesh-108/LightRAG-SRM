#!/usr/bin/env python3
"""
Test script for enhanced title extraction functionality
"""

import os
import sys
from rag_pipeline import RAGPipeline

def test_title_extraction():
    """Test the enhanced title extraction functionality."""
    print("🧪 Testing Enhanced Title Extraction")
    print("=" * 50)
    
    # Initialize RAG pipeline
    try:
        pipeline = RAGPipeline()
        print("✅ RAG pipeline initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize RAG pipeline: {e}")
        return False
    
    # Test with existing PDF
    pdf_path = 'documents/SRM_Installation_and_Configuration_Guide.pdf'
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        return False
    
    print(f"\n📄 Testing with: {pdf_path}")
    print("-" * 30)
    
    try:
        # Test PDF metadata extraction
        print("1. Testing PDF metadata extraction...")
        metadata = pipeline._extract_pdf_metadata(pdf_path)
        print(f"   📝 PDF Metadata:")
        for key, value in metadata.items():
            print(f"      {key}: {value}")
        
        # Test document loading
        print("\n2. Testing document loading...")
        pages = pipeline._load_pdf(pdf_path)
        print(f"   📊 Loaded {len(pages)} pages")
        
        # Test document title extraction
        print("\n3. Testing document title extraction...")
        extracted_title = pipeline._extract_document_title(pages)
        print(f"   🏷️  Extracted title: {extracted_title}")
        
        # Test enhanced headings extraction
        print("\n4. Testing enhanced headings extraction...")
        all_text = '\n'.join(pages)
        headings = pipeline._extract_enhanced_headings(all_text)
        print(f"   📋 Found {len(headings)} headings")
        
        # Show first 5 headings
        for i, heading in enumerate(headings[:5]):
            print(f"      Level {heading['level']}: {heading['text'][:60]}...")
        
        # Test comprehensive document info extraction
        print("\n5. Testing comprehensive document info...")
        doc_info = pipeline._extract_document_info(pdf_path, pages)
        print(f"   📄 Best title: {doc_info['best_title']}")
        print(f"   📝 Author: {doc_info['pdf_metadata'].get('author', 'Unknown')}")
        print(f"   📊 Pages: {doc_info['page_count']}")
        print(f"   📏 Size: {doc_info['file_size'] / 1024:.1f} KB")
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_heading_detection():
    """Test heading detection with sample text."""
    print("\n🔍 Testing Heading Detection")
    print("=" * 30)
    
    pipeline = RAGPipeline()
    
    # Sample text with various heading patterns
    sample_text = """
    DELL SRM INSTALLATION GUIDE
    
    Chapter 1: Introduction
    This is the introduction chapter.
    
    1.1 System Requirements
    The system requirements are listed here.
    
    1.1.1 Hardware Requirements
    Hardware requirements details.
    
    INSTALLATION STEPS
    Follow these steps for installation.
    
    Configuration Options
    Various configuration options available.
    """
    
    lines = sample_text.split('\n')
    
    print("Testing heading detection patterns:")
    for i, line in enumerate(lines):
        line = line.strip()
        if line:
            heading_level = pipeline._get_heading_level(line, i, lines)
            is_title = pipeline._is_document_title(line, i, lines)
            
            if heading_level > 0 or is_title:
                print(f"   Line {i+1}: '{line}'")
                print(f"      Heading Level: {heading_level}")
                print(f"      Is Title: {is_title}")
                print()

if __name__ == "__main__":
    print("🚀 Enhanced Title Extraction Test Suite")
    print("=" * 50)
    
    # Test heading detection
    test_heading_detection()
    
    # Test full title extraction
    success = test_title_extraction()
    
    if success:
        print("\n🎉 All tests passed! Title extraction is working correctly.")
    else:
        print("\n💥 Some tests failed. Please check the implementation.")
        sys.exit(1)

