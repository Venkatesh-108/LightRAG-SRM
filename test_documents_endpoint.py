#!/usr/bin/env python3
"""
Test script for enhanced documents endpoint
"""

import json
from app import app

def test_documents_endpoint():
    """Test the enhanced documents endpoint."""
    print("🧪 Testing Enhanced Documents Endpoint")
    print("=" * 40)
    
    with app.test_client() as client:
        response = client.get('/documents')
        
        if response.status_code == 200:
            documents = response.get_json()
            print(f"✅ Successfully retrieved {len(documents)} documents")
            print("\n📄 Document Details:")
            print("-" * 30)
            
            for doc in documents:
                print(f"📁 Filename: {doc.get('filename', 'N/A')}")
                print(f"🏷️  Title: {doc.get('title', 'N/A')}")
                print(f"📝 Author: {doc.get('author', 'N/A')}")
                print(f"📊 Pages: {doc.get('pages', 'N/A')}")
                print(f"📏 Size: {doc.get('size', 'N/A')} bytes")
                print("-" * 20)
        else:
            print(f"❌ Failed to retrieve documents: {response.status_code}")
            print(f"Response: {response.get_data(as_text=True)}")

if __name__ == "__main__":
    test_documents_endpoint()

