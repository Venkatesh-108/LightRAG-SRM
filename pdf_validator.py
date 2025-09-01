#!/usr/bin/env python3
"""
PDF Validator for LightRAG
This script validates PDF files and provides diagnostics for corrupted files.
"""

import os
import PyPDF2
import sys

def validate_pdf_structure(file_path):
    """Validate PDF file structure."""
    print(f"Validating PDF: {os.path.basename(file_path)}")
    print("-" * 50)
    
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        print(f"File size: {file_size / (1024*1024):.2f} MB")
        
        # Check for EOF marker
        with open(file_path, 'rb') as file:
            file.seek(-1024, 2)  # Seek to end minus 1024 bytes
            end_bytes = file.read()
            
            if b'%%EOF' in end_bytes:
                print("✅ EOF marker found")
            else:
                print("❌ EOF marker not found - file may be corrupted")
        
        # Try to read with PyPDF2
        with open(file_path, 'rb') as file:
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                print(f"✅ PDF structure valid")
                print(f"📄 Pages: {len(pdf_reader.pages)}")
                
                # Check if encrypted
                if pdf_reader.is_encrypted:
                    print("❌ PDF is encrypted")
                    return False
                else:
                    print("✅ PDF is not encrypted")
                
                # Try to extract text from first page
                try:
                    first_page = pdf_reader.pages[0]
                    text = first_page.extract_text()
                    if text and text.strip():
                        print(f"✅ Text extraction works (first page: {len(text)} characters)")
                    else:
                        print("⚠️  No text found on first page")
                except Exception as e:
                    print(f"❌ Text extraction failed: {e}")
                    return False
                
                return True
                
            except PyPDF2.errors.PdfReadError as e:
                print(f"❌ PDF read error: {e}")
                return False
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                return False
                
    except Exception as e:
        print(f"❌ File access error: {e}")
        return False

def suggest_fixes(file_path):
    """Suggest fixes for PDF issues."""
    print("\n🔧 SUGGESTED FIXES:")
    print("-" * 30)
    
    print("1. **Re-download the PDF file**")
    print("   - The file may have been corrupted during download")
    print("   - Try downloading it again from the original source")
    
    print("\n2. **Re-save the PDF file**")
    print("   - Open the PDF in a PDF reader (Adobe Reader, Chrome, etc.)")
    print("   - Save it again with 'Save As' to create a fresh copy")
    
    print("\n3. **Convert to PDF**")
    print("   - If you have the original document, convert it to PDF again")
    print("   - Use tools like Microsoft Word, Google Docs, or online converters")
    
    print("\n4. **Use a different PDF**")
    print("   - Try uploading a different PDF file to test the system")
    print("   - Ensure the new PDF is properly formatted and not corrupted")
    
    print("\n5. **Check file permissions**")
    print("   - Ensure the file is not locked or in use by another application")
    print("   - Try copying the file to a different location")

def main():
    """Main validation function."""
    if len(sys.argv) != 2:
        print("Usage: python pdf_validator.py <pdf_file_path>")
        print("Example: python pdf_validator.py documents/SRM_Web_Portal_Guide.pdf")
        return
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    if not file_path.lower().endswith('.pdf'):
        print(f"❌ Not a PDF file: {file_path}")
        return
    
    print("PDF Validator for LightRAG")
    print("=" * 50)
    
    is_valid = validate_pdf_structure(file_path)
    
    if is_valid:
        print("\n🎉 PDF is valid and ready for processing!")
        print("You can now upload this file to LightRAG.")
    else:
        print("\n❌ PDF has issues that need to be fixed.")
        suggest_fixes(file_path)

if __name__ == "__main__":
    main()
