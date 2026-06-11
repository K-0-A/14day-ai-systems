import os
import json
from typing import Any, Dict, List, Callable, Optional
from dotenv import load_dotenv

# SDK Imports
from groq import Groq
from openai import OpenAI
try:
    import anthropic
except ImportError:
    anthropic = None  # Graceful fallback if package is missing

from src import tools as tool_impl

ToolFn = Callable[..., Dict[str, Any]]

TOOL_REGISTRY: Dict[str, ToolFn] = {
    "list_files": tool_impl.list_files,
    "read_file": tool_impl.read_file,
    "write_file": tool_impl.write_file,
    "search_docs": tool_impl.search_docs,
    "calculator": tool_impl.calculator,
    "read_pdf_page": tool_impl.read_pdf_page,
}

# Standard OpenAI-format Schema
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files inside the workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace-relative folder path"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text (.txt) or document (.pdf) file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace-relative file path"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a text file to the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search local documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query"},
                    "max_hits": {"type": "integer", "description": "Limit results", "default": 10}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate math expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Arithmetic expression"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_pdf_page",
            "description": "Extract text from a specific PDF page (1-indexed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "PDF path"},
                    "page_number": {"type": "integer", "description": "Page number"}
                },
                "required": ["path", "page_number"]
            }
        }
    }
]

def _get_anthropic_tools():
    """Convert OpenAI schema to Anthropic format on the fly."""
    claude_tools = []
    for t in TOOLS_SCHEMA:
        fn = t["function"]
        claude_tools.append({
            "name": fn["name"],
            "description": fn["description"],
            "input_schema": fn["parameters"]
        })
    return claude_tools

def run_agent(goal: str, model_name: str = "llama-3.3-70b-versatile", max_steps: int = 40) -> Dict[str, Any]:
    load_dotenv()
    
    # --- PROVIDER ROUTING LOGIC ---
    provider = "groq"
    client = None
    
    if "claude" in model_name.lower():
        provider = "anthropic"
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
    elif "gemini" in model_name.lower():
        provider = "google"
        if not os.getenv("GOOGLE_API_KEY"):
             raise RuntimeError("Missing GOOGLE_API_KEY in .env")
        # Use Google's OpenAI-compatible endpoint
        client = OpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://googleapis.com"
        )
        
    elif "gpt" in model_name.lower():
        provider = "openai"
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Missing OPENAI_API_KEY in .env")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    else:
        provider = "groq"
        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError("Missing GROQ_API_KEY in .env")
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # --- SHARED SYSTEM PROMPT ---
    system_text = (
        "You are a task-executing AI agent. Use tools to search, read/write files, and calculate.\n"
        "Constraints:\n"
        "- Execute tools by passing ONLY the function name and strict JSON arguments.\n"
        "- Stop when the task is complete.\n"
    )

    messages = [{"role": "user", "content": f"GOAL: {goal}"}]
    if provider != "anthropic":
        messages.insert(0, {"role": "system", "content": system_text})

    # --- EXECUTION LOOP ---
    for step in range(1, max_steps + 1):
        try:
            # === BRANCH A: ANTHROPIC (Native SDK) ===
            if provider == "anthropic":
                resp = client.messages.create(
                    model=model_name,
                    max_tokens=1024,
                    system=system_text,
                    messages=messages,
                    tools=_get_anthropic_tools()
                )
                
                # Handle Stop Reason
                if resp.stop_reason != "tool_use":
                    return {"ok": True, "steps": step, "final": resp.content[0].text}

                # Append Assistant Response to History
                messages.append({"role": "assistant", "content": resp.content})

                # Process Tools
                tool_results_content = []
                for block in resp.content:
                    if block.type == "tool_use":
                        name = block.name
                        args = block.input
                        
                        # Execute
                        if name in TOOL_REGISTRY:
                            try:
                                res = TOOL_REGISTRY[name](**args)
                            except Exception as e:
                                res = {"error": str(e)}
                        else:
                            res = {"error": f"Unknown tool: {name}"}

                        tool_results_content.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(res)
                        })
                
                messages.append({"role": "user", "content": tool_results_content})

            # === BRANCH B: OPENAI / GROQ / GEMINI (Standard SDK) ===
            else:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                    temperature=0.2
                )
                
                msg = resp.choices[0].message
                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    return {"ok": True, "steps": step, "final": msg.content}

                messages.append(msg)

                for tc in tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments or "{}")

                    if name in TOOL_REGISTRY:
                        try:
                            res = TOOL_REGISTRY[name](**args)
                        except Exception as e:
                            res = {"error": str(e)}
                    else:
                        res = {"error": f"Unknown tool: {name}"}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": json.dumps(res)
                    })

        except Exception as e:
            return {"ok": False, "error": f"Provider Error ({provider}): {str(e)}"}

    return {"ok": False, "error": "Max steps exceeded."}