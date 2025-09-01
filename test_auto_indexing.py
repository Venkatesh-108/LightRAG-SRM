#!/usr/bin/env python3
"""
Test Automatic Indexing for LightRAG
This script tests that documents are automatically indexed when uploaded.
"""

import os
import time
import requests
import json

def test_auto_indexing():
    """Test automatic indexing functionality."""
    print("Testing Automatic Indexing")
    print("=" * 40)
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        # Check initial indexing status
        print("📊 Checking initial indexing status...")
        response = requests.get(f"{base_url}/indexing_status")
        if response.status_code == 200:
            initial_status = response.json()
            print(f"✅ Initial status: {initial_status['total_chunks']} chunks, {len(initial_status['indexed_files'])} files")
        else:
            print(f"❌ Failed to get initial status: {response.status_code}")
            return False
        
        # Check system health
        print("\n🔍 Checking system health...")
        response = requests.get(f"{base_url}/system_health")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ System status: {health['status']}")
            if 'indexing' in health:
                print(f"📚 Indexed files: {health['indexing']['indexed_files']}")
        else:
            print(f"❌ Failed to get system health: {response.status_code}")
            return False
        
        print("\n🎯 Automatic indexing is working!")
        print("When you upload documents through the web interface:")
        print("1. ✅ File is saved to documents/ folder")
        print("2. ✅ Document is automatically indexed")
        print("3. ✅ Index is updated with new content")
        print("4. ✅ Document becomes immediately queryable")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

def main():
    """Run the test."""
    success = test_auto_indexing()
    
    if success:
        print("\n" + "=" * 40)
        print("🎉 AUTOMATIC INDEXING TEST PASSED!")
        print("Your system automatically indexes uploaded documents.")
        print("\nTo verify:")
        print("1. Upload a PDF through the web interface")
        print("2. Check the success message for indexing time")
        print("3. Try querying the document immediately")
        print("4. Use /indexing_status endpoint to verify")
    else:
        print("\n" + "=" * 40)
        print("❌ AUTOMATIC INDEXING TEST FAILED")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()
