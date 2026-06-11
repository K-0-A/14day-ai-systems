import os
import re
from pypdf import PdfReader

WORKSPACE_DIR = "workspace"
DOCS_DIR = "data/docs"

# Ensure the required folders exist so tools don't crash
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Helper to convert PDF pages into simple text safely."""
    try:
        reader = PdfReader(pdf_path)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)
    except Exception as e:
        return f"[Error parsing PDF file: {str(e)}]"


def list_files(path: str = "") -> dict:
    """List files inside the workspace directory."""
    target_dir = os.path.normpath(os.path.join(WORKSPACE_DIR, path))
    
    # Security Sandbox Check
    if not target_dir.startswith(os.path.abspath(WORKSPACE_DIR)):
        return {"ok": False, "error": "Access denied: Path outside workspace."}
        
    if not os.path.exists(target_dir):
        return {"ok": False, "error": f"Folder not found: {path}"}
        
    try:
        files = os.listdir(target_dir)
        return {"ok": True, "files": files}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def read_file(path: str) -> dict:
    """Read a text file OR pull text from a PDF from the workspace directory."""
    full_path = os.path.normpath(os.path.join(WORKSPACE_DIR, path))
    
    # Security Sandbox Check
    if not full_path.startswith(os.path.abspath(WORKSPACE_DIR)):
        return {"ok": False, "error": "Access denied: Path outside workspace."}
        
    if not os.path.exists(full_path):
        return {"ok": False, "error": f"File not found: {path}"}

    try:
        if full_path.lower().endswith(".pdf"):
            text = _extract_text_from_pdf(full_path)
            return {"ok": True, "content": text}
        else:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                return {"ok": True, "content": f.read()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def write_file(path: str, content: str) -> dict:
    """Write a text file to the workspace directory."""
    full_path = os.path.normpath(os.path.join(WORKSPACE_DIR, path))
    
    # Security Sandbox Check
    if not full_path.startswith(os.path.abspath(WORKSPACE_DIR)):
        return {"ok": False, "error": "Access denied: Path outside workspace."}
        
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "message": f"Successfully wrote to {path}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def search_docs(query: str, max_hits: int = 10) -> dict:
    """Search within local .txt and .pdf documents in data/docs to find relevant snippets."""
    query = query.lower()
    hits = []
    
    if not os.path.exists(DOCS_DIR):
        return {"ok": False, "error": f"Docs directory {DOCS_DIR} missing."}

    try:
        for root, _, files in os.walk(DOCS_DIR):
            for file in files:
                file_path = os.path.normpath(os.path.join(root, file))
                rel_path = os.path.relpath(file_path, DOCS_DIR)
                
                if file.lower().endswith(".pdf"):
                    content = _extract_text_from_pdf(file_path)
                elif file.lower().endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                else:
                    continue
                    
                if query in content.lower():
                    idx = content.lower().find(query)
                    start = max(0, idx - 150)
                    end = min(len(content), idx + 350)
                    snippet = content[start:end].strip()
                    
                    hits.append({
                        "file": rel_path,
                        "snippet": f"... {snippet} ..."
                    })
                    
                    if len(hits) >= max_hits:
                        break
            if len(hits) >= max_hits:
                break
        return {"ok": True, "hits": hits}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def calculator(expression: str) -> dict:
    """Evaluate a basic arithmetic expression safely using regex filtering."""
    # Allow only digits, basic operators (+, -, *, /), decimals, and spaces
    clean_expr = re.sub(r'[^0-9\+\-\*\/\.\s\(\)]', '', expression)
    
    if not clean_expr.strip():
        return {"ok": False, "error": "Invalid arithmetic expression."}
        
    try:
        # Using eval safely because we stripped out characters/malicious syntax strings
        result = eval(clean_expr)
        return {"ok": True, "result": float(result)}
    except Exception as e:
        return {"ok": False, "error": f"Math error: {str(e)}"}


def read_pdf_page(path: str, page_number: int) -> dict:
    """Extract text from one specific page (1-indexed) of a PDF inside the workspace folder."""
    full_path = os.path.normpath(os.path.join(WORKSPACE_DIR, path))
    
    # Security Sandbox Check
    if not full_path.startswith(os.path.abspath(WORKSPACE_DIR)):
        return {"ok": False, "error": "Access denied: Path outside workspace."}
        
    if not os.path.exists(full_path):
        return {"ok": False, "error": f"File not found: {path}"}
        
    if not full_path.lower().endswith(".pdf"):
        return {"ok": False, "error": "The target file must be a PDF format."}
        
    if page_number < 1:
        return {"ok": False, "error": "Page numbers must be 1 or greater."}

    try:
        reader = PdfReader(full_path)
        total_pages = len(reader.pages)
        
        if page_number > total_pages:
            return {
                "ok": False, 
                "error": f"Page {page_number} requested, but document only has {total_pages} pages."
            }
            
        # Extract specific page (Adjusting to 0-index for pypdf)
        target_page = reader.pages[page_number - 1]
        page_text = target_page.extract_text() or ""
        
        return {
            "ok": True,
            "page": page_number,
            "total_pages": total_pages,
            "content": page_text.strip()
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
