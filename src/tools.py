import os
import glob
import ast
import operator as op
from typing import Dict, Any, List
 
WORKSPACE_ROOT = os.path.abspath("workspace")
DOCS_ROOT = os.path.abspath("data/docs")
 
# -------------------------
# File tools (workspace only)
# -------------------------
 
def _safe_path(root: str, user_path: str) -> str:
    """Prevent path traversal by forcing paths to stay within root."""
    full = os.path.abspath(os.path.join(root, user_path))
    if not full.startswith(root):
        raise ValueError("Unsafe path: outside allowed directory.")
    return full
 
def list_files(path: str = "") -> Dict[str, Any]:
    root = WORKSPACE_ROOT
    target = _safe_path(root, path)
    if not os.path.exists(target):
        return {"ok": False, "error": "Path does not exist."}
    if os.path.isfile(target):
        return {"ok": True, "files": [os.path.relpath(target, root)]}
    files = []
    for p in glob.glob(os.path.join(target, "**/*"), recursive=True):
        if os.path.isfile(p):
            files.append(os.path.relpath(p, root))
    return {"ok": True, "files": sorted(files)}
 
def read_file(path: str) -> Dict[str, Any]:
    full = _safe_path(WORKSPACE_ROOT, path)
    if not os.path.exists(full):
        return {"ok": False, "error": "File not found."}
    with open(full, "r", encoding="utf-8", errors="ignore") as f:
        return {"ok": True, "content": f.read()}
 
def write_file(path: str, content: str) -> Dict[str, Any]:
    full = _safe_path(WORKSPACE_ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return {"ok": True, "written": os.path.relpath(full, WORKSPACE_ROOT)}
 
# -------------------------
# Doc search tool (local "search")
# -------------------------
 
def search_docs(query: str, max_hits: int = 5) -> Dict[str, Any]:
    query_l = (query or "").strip().lower()
    if not query_l:
        return {"ok": False, "error": "Empty query."}
 
    hits: List[Dict[str, Any]] = []
    for path in glob.glob(os.path.join(DOCS_ROOT, "**/*.txt"), recursive=True):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        text_l = text.lower()
        idx = text_l.find(query_l)
        if idx != -1:
            start = max(0, idx - 120)
            end = min(len(text), idx + 240)
            snippet = text[start:end].replace("\n", " ")
            hits.append({
                "doc": os.path.relpath(path, DOCS_ROOT),
                "snippet": snippet,
            })
        if len(hits) >= max_hits:
            break
 
    return {"ok": True, "query": query, "hits": hits}
 
# -------------------------
# Calculator tool (safe)
# -------------------------
 
_ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}
 
def _eval_expr(node):
    if isinstance(node, ast.Num):  # type: ignore[attr-defined]
        return node.n
    if isinstance(node, ast.BinOp):
        return _ALLOWED_OPS[type(node.op)](_eval_expr(node.left), _eval_expr(node.right))
    if isinstance(node, ast.UnaryOp):
        return _ALLOWED_OPS[type(node.op)](_eval_expr(node.operand))
    raise ValueError("Unsupported expression")
 
def calculator(expression: str) -> Dict[str, Any]:
    expr = (expression or "").strip()
    if not expr:
        return {"ok": False, "error": "Empty expression."}
    try:
        node = ast.parse(expr, mode="eval").body
        value = _eval_expr(node)
        return {"ok": True, "expression": expr, "result": value}
    except Exception as e:
        return {"ok": False, "error": str(e)}