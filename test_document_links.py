#!/usr/bin/env python3
"""
Test script to verify document link functionality
"""

import json
from app import app

def test_document_links():
    """Test that document links use correct filenames."""
    print("🧪 Testing Document Link Functionality")
    print("=" * 40)
    
    with app.test_client() as client:
        # Get documents
        response = client.get('/documents')
        
        if response.status_code == 200:
            documents = response.get_json()
            print(f"✅ Found {len(documents)} documents")
            print("\n📄 Document Details:")
            print("-" * 30)
            
            for doc in documents:
                filename = doc.get('filename', 'N/A')
                title = doc.get('title', 'N/A')
                
                print(f"📁 Filename: {filename}")
                print(f"🏷️  Title: {title}")
                
                # Test that the document can be accessed via filename
                doc_response = client.get(f'/documents/{filename}')
                if doc_response.status_code == 200:
                    print(f"✅ Document accessible via: /documents/{filename}")
                else:
                    print(f"❌ Document not accessible via: /documents/{filename}")
                
                # Test that the title URL would fail (this is what we're fixing)
                title_url = title.replace(' ', '%20')
                title_response = client.get(f'/documents/{title_url}')
                if title_response.status_code == 200:
                    print(f"⚠️  Title URL also works (unexpected): /documents/{title_url}")
                else:
                    print(f"✅ Title URL correctly fails: /documents/{title_url}")
                
                print("-" * 20)
        else:
            print(f"❌ Failed to retrieve documents: {response.status_code}")

if __name__ == "__main__":
    test_document_links()
