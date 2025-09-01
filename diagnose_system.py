#!/usr/bin/env python3
"""
System Diagnostic Script for LightRAG
This script checks your system resources and helps identify potential issues
that could cause crashes during document upload.
"""

import os
import sys
import psutil
import gc

def check_memory():
    """Check memory usage and availability."""
    print("=== Memory Check ===")
    try:
        memory = psutil.virtual_memory()
        total_gb = memory.total / (1024**3)
        available_gb = memory.available / (1024**3)
        used_gb = memory.used / (1024**3)
        percent_used = memory.percent
        
        print(f"Total Memory: {total_gb:.1f} GB")
        print(f"Available Memory: {available_gb:.1f} GB")
        print(f"Used Memory: {used_gb:.1f} GB ({percent_used:.1f}%)")
        
        if available_gb >= 4.0:
            print("✅ Memory: Excellent (>4GB available)")
        elif available_gb >= 2.0:
            print("⚠️  Memory: Good (2-4GB available)")
        elif available_gb >= 1.0:
            print("⚠️  Memory: Low (1-2GB available) - Close other applications")
        else:
            print("❌ Memory: Critical (<1GB available) - Cannot process documents safely")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking memory: {e}")
        return False

def check_disk_space():
    """Check available disk space."""
    print("\n=== Disk Space Check ===")
    try:
        disk = psutil.disk_usage('.')
        total_gb = disk.total / (1024**3)
        free_gb = disk.free / (1024**3)
        used_gb = disk.used / (1024**3)
        percent_used = (disk.used / disk.total) * 100
        
        print(f"Total Disk Space: {total_gb:.1f} GB")
        print(f"Free Disk Space: {free_gb:.1f} GB")
        print(f"Used Disk Space: {used_gb:.1f} GB ({percent_used:.1f}%)")
        
        if free_gb >= 5.0:
            print("✅ Disk Space: Excellent (>5GB free)")
        elif free_gb >= 2.0:
            print("⚠️  Disk Space: Good (2-5GB free)")
        elif free_gb >= 1.0:
            print("⚠️  Disk Space: Low (1-2GB free)")
        else:
            print("❌ Disk Space: Critical (<1GB free)")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking disk space: {e}")
        return False

def check_cpu_usage():
    """Check CPU usage."""
    print("\n=== CPU Check ===")
    try:
        cpu_percent = psutil.cpu_percent(interval=2)
        cpu_count = psutil.cpu_count()
        
        print(f"CPU Cores: {cpu_count}")
        print(f"Current CPU Usage: {cpu_percent:.1f}%")
        
        if cpu_percent < 70:
            print("✅ CPU: Good (<70% usage)")
        elif cpu_percent < 90:
            print("⚠️  CPU: High (70-90% usage)")
        else:
            print("❌ CPU: Critical (>90% usage)")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking CPU: {e}")
        return False

def check_python_packages():
    """Check if required Python packages are installed."""
    print("\n=== Python Packages Check ===")
    required_packages = [
        ('flask', 'flask'),
        ('psutil', 'psutil'),
        ('PyPDF2', 'PyPDF2'),
        ('faiss-cpu', 'faiss'),
        ('sentence-transformers', 'sentence_transformers'),
        ('numpy', 'numpy'),
        ('ollama', 'ollama'),
        ('openai', 'openai')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - Missing")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_directories():
    """Check if required directories exist and are writable."""
    print("\n=== Directory Check ===")
    directories = ['documents', 'vector_store', 'templates', 'static']
    
    for directory in directories:
        if os.path.exists(directory):
            if os.access(directory, os.W_OK):
                print(f"✅ {directory}/ - Exists and writable")
            else:
                print(f"❌ {directory}/ - Exists but not writable")
                return False
        else:
            print(f"⚠️  {directory}/ - Does not exist (will be created)")
    
    return True

def check_ollama():
    """Check if Ollama is running (optional)."""
    print("\n=== Ollama Check ===")
    try:
        import ollama
        # Try to list models
        models = ollama.list()
        if models['models']:
            print("✅ Ollama: Running with models available")
            for model in models['models']:
                print(f"   - {model['name']}")
        else:
            print("⚠️  Ollama: Running but no models found")
        return True
    except Exception as e:
        print(f"⚠️  Ollama: Not running or not accessible ({e})")
        print("   Note: This is optional if using OpenAI")
        return True

def main():
    """Run all system checks."""
    print("LightRAG System Diagnostic")
    print("=" * 40)
    
    checks = [
        check_memory(),
        check_disk_space(),
        check_cpu_usage(),
        check_python_packages(),
        check_directories(),
        check_ollama()
    ]
    
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    
    if all(checks):
        print("✅ All checks passed! Your system should be able to handle document uploads safely.")
        print("\nRecommendations:")
        print("- Close unnecessary applications to free up memory")
        print("- Ensure you have a stable internet connection")
        print("- Start with smaller PDF files (<10MB) for testing")
    else:
        print("❌ Some checks failed. Please address the issues above before uploading documents.")
        print("\nImmediate actions:")
        print("- Close other applications to free memory")
        print("- Free up disk space")
        print("- Install missing Python packages")
        print("- Restart your computer if memory issues persist")
    
    print("\nFor more help, check the README.md file or contact support.")

if __name__ == "__main__":
    main()
