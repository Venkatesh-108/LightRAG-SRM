#!/usr/bin/env python3
"""
System Status Test for LightRAG
This script tests all system components to ensure everything is working correctly.
"""

import os
import time
import psutil
from rag_pipeline import RAGPipeline

def test_system_resources():
    """Test system resources."""
    print("🔍 Testing System Resources")
    print("-" * 30)
    
    try:
        # Memory check
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        print(f"✅ Memory: {available_gb:.1f}GB available")
        
        # Disk check
        disk = psutil.disk_usage('.')
        free_gb = disk.free / (1024**3)
        print(f"✅ Disk: {free_gb:.1f}GB free")
        
        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"✅ CPU: {cpu_percent:.1f}% usage")
        
        return True
    except Exception as e:
        print(f"❌ System resources check failed: {e}")
        return False

def test_python_packages():
    """Test if all required packages are available."""
    print("\n📦 Testing Python Packages")
    print("-" * 30)
    
    packages = [
        ('flask', 'flask'),
        ('psutil', 'psutil'),
        ('PyPDF2', 'PyPDF2'),
        ('faiss-cpu', 'faiss'),
        ('sentence-transformers', 'sentence_transformers'),
        ('numpy', 'numpy'),
        ('ollama', 'ollama'),
        ('openai', 'openai')
    ]
    
    all_good = True
    for package_name, import_name in packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - Missing")
            all_good = False
    
    return all_good

def test_ollama_connection():
    """Test Ollama connection and models."""
    print("\n🤖 Testing Ollama Connection")
    print("-" * 30)
    
    try:
        import ollama
        
        # Test connection
        models = ollama.list()
        print(f"✅ Ollama connection successful")
        print(f"✅ Found {len(models['models'])} models")
        
        # Test model availability
        target_model = 'llama3.2:3b'
        available_models = [model['model'] for model in models['models']]
        
        if target_model in available_models:
            print(f"✅ Target model '{target_model}' is available")
            
            # Test a simple query
            print("🧪 Testing model response...")
            response = ollama.chat(
                model=target_model,
                messages=[{'role': 'user', 'content': 'Hello, are you working?'}]
            )
            print(f"✅ Model response: {response['message']['content'][:50]}...")
            return True
        else:
            print(f"⚠️  Target model '{target_model}' not found")
            print(f"Available models: {available_models}")
            return False
            
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
        return False

def test_rag_pipeline():
    """Test RAG pipeline initialization."""
    print("\n🔧 Testing RAG Pipeline")
    print("-" * 30)
    
    try:
        print("Initializing RAG pipeline...")
        start_time = time.time()
        pipeline = RAGPipeline(model_provider='ollama')
        init_time = time.time() - start_time
        
        print(f"✅ RAG pipeline initialized successfully")
        print(f"✅ Initialization time: {init_time:.2f} seconds")
        
        # Test if pipeline has required components
        if hasattr(pipeline, 'embedder') and pipeline.embedder is not None:
            print("✅ Embedding model loaded")
        else:
            print("❌ Embedding model not loaded")
            return False
            
        if hasattr(pipeline, 'index'):
            print("✅ FAISS index available")
        else:
            print("⚠️  FAISS index not initialized (normal for empty system)")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_directories():
    """Test if required directories exist and are writable."""
    print("\n📁 Testing Directories")
    print("-" * 30)
    
    directories = ['documents', 'vector_store', 'templates', 'static']
    all_good = True
    
    for directory in directories:
        if os.path.exists(directory):
            if os.access(directory, os.W_OK):
                print(f"✅ {directory}/ - Exists and writable")
            else:
                print(f"❌ {directory}/ - Exists but not writable")
                all_good = False
        else:
            print(f"⚠️  {directory}/ - Does not exist (will be created)")
    
    return all_good

def test_web_interface():
    """Test if the web interface is accessible."""
    print("\n🌐 Testing Web Interface")
    print("-" * 30)
    
    try:
        import requests
        response = requests.get('http://127.0.0.1:5000/system_health', timeout=5)
        if response.status_code == 200:
            print("✅ Web interface is accessible")
            data = response.json()
            if data.get('status') == 'healthy':
                print("✅ System health endpoint working")
                return True
            else:
                print("⚠️  System health endpoint returned warning")
                return True
        else:
            print(f"❌ Web interface returned status code: {response.status_code}")
            return False
    except ImportError:
        print("⚠️  requests package not available, skipping web interface test")
        return True
    except Exception as e:
        print(f"❌ Web interface test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("LightRAG System Status Test")
    print("=" * 50)
    
    tests = [
        ("System Resources", test_system_resources),
        ("Python Packages", test_python_packages),
        ("Ollama Connection", test_ollama_connection),
        ("RAG Pipeline", test_rag_pipeline),
        ("Directories", test_directories),
        ("Web Interface", test_web_interface)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("Your LightRAG system is fully functional.")
        print("\nNext steps:")
        print("1. Add PDF files to the documents/ folder")
        print("2. Use the web interface to upload and query documents")
        print("3. Start with small PDF files (<10MB) for testing")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("Please address the issues above before using the system.")
    
    print("\n💡 Tip: Run 'python diagnose_system.py' for detailed system information")

if __name__ == "__main__":
    main()
