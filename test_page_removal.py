#!/usr/bin/env python3
"""
Test script to verify page count removal from documents display
"""

from app import app

def test_page_count_removal():
    """Test that documents endpoint still works without page display."""
    print("🧪 Testing Page Count Removal")
    print("=" * 40)
    
    with app.test_client() as client:
        response = client.get('/documents')
        
        if response.status_code == 200:
            documents = response.get_json()
            print(f"✅ Found {len(documents)} documents")
            print("\n📄 Document Details (Page Count Removed):")
            print("-" * 40)
            
            for doc in documents:
                filename = doc.get('filename', 'N/A')
                title = doc.get('title', 'N/A')
                author = doc.get('author', 'N/A')
                size = doc.get('size', 'N/A')
                pages = doc.get('pages', 'N/A')  # Still available in backend
                
                print(f"📁 Filename: {filename}")
                print(f"🏷️  Title: {title}")
                print(f"👤 Author: {author}")
                print(f"📏 Size: {size} bytes")
                print(f"📊 Pages (backend): {pages} (not displayed in UI)")
                print("-" * 20)
                
                # Verify that page count is still available in backend
                if pages == 0:
                    print("⚠️  Warning: Page count is 0 - might need re-indexing")
        else:
            print(f"❌ Failed to retrieve documents: {response.status_code}")

if __name__ == "__main__":
    test_page_count_removal()
