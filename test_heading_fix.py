#!/usr/bin/env python3
"""
Test script to verify heading extraction fix
"""

from rag_pipeline import RAGPipeline

def test_heading_fix():
    """Test that headings are properly extracted without double markers."""
    print("🧪 Testing Heading Extraction Fix")
    print("=" * 40)
    
    pipeline = RAGPipeline()
    
    # Sample text with headings
    sample_text = """Dell SRM Installation Guide

Chapter 1: Introduction
This is the introduction chapter.

1.1 System Requirements
The system requirements are listed here.

INSTALLATION STEPS
Follow these steps for installation."""
    
    print("📄 Original text:")
    print(sample_text)
    print("\n" + "-" * 40)
    
    # Process the text
    processed_text = pipeline._process_page_text(sample_text, 0)
    print("📝 Processed text:")
    print(processed_text)
    print("\n" + "-" * 40)
    
    # Split into chunks
    chunks = pipeline._split_text(processed_text)
    print(f"📦 Split into {len(chunks)} chunks:")
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(chunk)
        print("-" * 20)
    
    # Check for double ## markers
    double_markers = processed_text.count('## ##')
    if double_markers > 0:
        print(f"❌ Found {double_markers} double ## markers")
    else:
        print("✅ No double ## markers found")
    
    # Count proper headings
    proper_headings = processed_text.count('## ')
    print(f"✅ Found {proper_headings} proper headings")

if __name__ == "__main__":
    test_heading_fix()
