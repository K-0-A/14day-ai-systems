from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
 
from src.ai_service import generate_answer
 
app = FastAPI(title="Day 7 AI Web App")
 
# Serve static frontend
app.mount("/web", StaticFiles(directory="web"), name="web")
 
 
class AskRequest(BaseModel):
    prompt: str
 
 
@app.get("/")
def home():
    return FileResponse("web/index.html")
 
 
@app.post("/api/ask")
def ask(req: AskRequest):
    prompt = req.prompt.strip()
    if not prompt:
        return {"ok": False, "error": "Prompt cannot be empty."}
 
    try:
        answer = generate_answer(prompt)
        return {"ok": True, "answer": answer}
    except Exception as e:
        return {"ok": False, "error": str(e)}