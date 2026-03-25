import sys
import os

from document_loader import extract_pdf_chunks

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pdf.py path_to_pdf")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    
    print(f"Reading {pdf_path}...")
    chunks = extract_pdf_chunks(pdf_path)
    
    print(f"Extracted {len(chunks)} chunks.")
    if chunks:
        print("First chunk preview:")
        print(chunks[0]['content'][:100])
        print("...")
        print("Success!")
