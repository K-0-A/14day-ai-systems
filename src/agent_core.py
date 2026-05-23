import os
import json
from typing import Any, Dict, List, Callable
 
from dotenv import load_dotenv
from groq import Groq
 
from src import tools as tool_impl
 
 
ToolFn = Callable[..., Dict[str, Any]]
 
TOOL_REGISTRY: Dict[str, ToolFn] = {
    "list_files": tool_impl.list_files,
    "read_file": tool_impl.read_file,
    "write_file": tool_impl.write_file,
    "search_docs": tool_impl.search_docs,
    "calculator": tool_impl.calculator,
}
 
# Tool schemas for function calling
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files inside the workspace directory. Use to discover outputs created by the agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace-relative folder path, e.g. '' or 'reports/'"}
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace-relative file path, e.g. 'output.txt'"}
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a text file to the workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace-relative file path to write, e.g. 'plan.md'"},
                    "content": {"type": "string", "description": "File contents"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search within local .txt documents in data/docs to find relevant snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_hits": {"type": "integer", "description": "Maximum number of hits to return", "default": 10},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression safely (e.g., '12*4 + 3').",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Arithmetic expression"},
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
]
 
 
def run_agent(goal: str, max_steps: int = 10) -> Dict[str, Any]:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY in .env")
 
    client = Groq(api_key=api_key)
 
    system = (
        "You are a task-executing AI agent.\n"
        "You have tools to search local documents, read/write files in a workspace, and do calculations.\n"
        "You must use tools when needed.\n"
        "You must stop when the task is complete and provide a clear final result.\n"
        "Constraints:\n"
        "- Only write files inside the workspace.\n"
        "- Keep steps bounded; do not loop forever.\n"
        "- If the goal is ambiguous, ask one clarifying question.\n"
    )
 
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"GOAL:\n{goal}"},
    ]
 
    for step in range(1, max_steps + 1):
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.6,
            max_tokens=700,
        )
 
        msg = resp.choices[0].message
 
        # If the model produced a normal answer and no tool calls, we treat it as final.
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            final_text = (msg.content or "").strip()
            return {"ok": True, "steps": step, "final": final_text}
 
        # Otherwise, execute each tool call and append results.
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": tool_calls})
 
        for tc in tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
 
            if name not in TOOL_REGISTRY:
                tool_result = {"ok": False, "error": f"Unknown tool: {name}"}
            else:
                try:
                    tool_result = TOOL_REGISTRY[name](**args)
                except Exception as e:
                    tool_result = {"ok": False, "error": str(e)}
 
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": json.dumps(tool_result),
            })
 
    return {"ok": False, "error": f"Max steps exceeded ({max_steps}). Try a narrower goal."}