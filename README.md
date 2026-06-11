14-DAY PRODUCTION AI SYSTEMS ARCHITECTURE
=========================================

A self-contained exploration of local-first AI pipelines: RAG, autonomous agents,
event-driven workflows, persistent memory, JSON validation, CLI assistants,
and automated testing.


PROBLEM STATEMENT
-----------------

When you work with sensitive financial or corporate data, you cannot afford to leak
it to third-party cloud logs or expose API keys. Off-the-shelf AI wrappers often
return unpredictable formatting (stray markdown, broken JSON) that crashes deterministic
pipelines. I built this environment to prove that AI systems can be secure, deterministic,
and production-ready while keeping full control over data and costs.


SOLUTION OVERVIEW
-----------------

This repository shows what I can build in two weeks: a modular AI framework that
runs entirely on my hardware (or cheap cloud VMs). The system is split into
interoperable layers:

- Autonomous ReAct agent – A multi-turn reasoning engine that takes a request,
  picks the right tool from a small registry, runs it, and keeps going until it
  has an answer. It can read/write files, search the local knowledge base, do math,
  and update its own workspace.

- CLI assistant – A simple text-in/text-out command-line chat for quick questions
  and prototyping.

- Structured JSON assistant – Forces the AI to return validated JSON against a
  schema, with parsing and safety checks.

- Event-driven workflow – A file-system watcher that picks up new files, cleans
  malformed JSON, and routes them through a multi-step pipeline.

- Local RAG – A vector database that runs entirely on my machine. No remote
  embeddings, no data leaks. It tokenises and indexes documents using
  sentence-transformers.

- Session-persistent memory – A hybrid store (in-memory + disk backup) that keeps
  conversation history across stateless web requests.

- CI/CD test harness – A set of deterministic tests that throw adversarial prompts,
  empty inputs, and non-English text at the system to catch crashes early.


ARCHITECTURE OVERVIEW
---------------------

The codebase separates runnable scripts (scripts/) from reusable core logic (src/),
keeping the system testable and scalable.

.
├── requirements.txt
├── .env                         # API keys (never committed)
├── .gitignore
├── README.txt
├── data/
│   └── docs/                    # Put your transcripts, notes, PDFs here
│   └── sessions.json
├── inbox/                       # Hot folder for file ingestion
├── logs/
│   └── workflow.log
├── outbox/                      # Structured output from pipelines
├── reports/
│   └── eval_report.json         # Test results
├── scripts/
│   ├── agent_cli.py             # Autonomous agent terminal
│   ├── cli_assistant.py         # Basic CLI chat (text-in/text-out)
│   ├── eval_run.py              # Automated evaluation test engine
│   ├── hello_ai.py              # Setup verification
│   ├── json_assistant.py        # Structured JSON schema testing
│   ├── rag_assistant.py         # Build & query local RAG
│   └── watch_inbox.py           # Filesystem polling loop
├── src/
│   ├── agent_core.py            # Tool registry + agent loop
│   ├── ai_service.py            # Model wrappers + sliding memory
│   ├── app.py                   # FastAPI backend
│   ├── eval/                    # Evaluation and safety validators
│   │   └── validators.py        # JSON schema, constraints, blocklist
│   ├── session_store.py         # Memory + disk persistence
│   ├── tools.py                 # File, calculator, search, PDF tools
│   ├── workflow_runner.py       # Orchestrator
│   └── workflow_steps.py        # Extraction, validation, routing
├── tests/
│   └── test_cases.json          # Benchmark + adversarial inputs
├── web/
│   └── index.html               # Session-aware UI (localStorage)
└── workspace/                   # Agent sandbox (read/write)


TECH STACK (THE PARTS THAT MATTER)
-----------------------------------

Backend:           FastAPI, Uvicorn
Frontend:          plain HTML/CSS/JS, localStorage API
LLMs:              Llama-3.3-70b (Groq), Llama-3-8b (Groq),
                   Gemini 1.5 Flash (Google), Claude 4.6 Sonnet (Anthropic),
                   GPT-4o-mini (OpenAI)
                   – I switch depending on what I’m testing and which rate limit
                     I’ve hit.
Local embeddings:  sentence-transformers (nomic-ai/nomic-embed-text-v1.5)
Automation:        filesystem polling, shutil transactional moves
Memory management: in-memory dict + JSON serialisation + TTL cleanup
Testing:           scripted validation sweeps, aggressive string sanitisation,
                   safety blocklists
Deployment:        Render (web service, environment variables)


KEY FEATURES & CAPABILITY SHOWCASE
----------------------------------

--- AUTONOMOUS REACT AGENT ---

The agent isn’t a linear script. It runs a loop:

  evaluate the goal → pick a tool → generate inputs → read feedback → loop again.

Tools exposed via src/agent_core.py:

  - list_files      – scan workspace/
  - read_file       – read text or PDF files (extracts text from PDFs on the fly)
  - write_file      – save results
  - search_docs     – query the local RAG index
  - calculator      – evaluate arithmetic expressions safely
  - read_pdf_page   – extract a single page from a PDF (saves tokens vs reading
                      the whole file)

The agent supports multiple providers. When you run it, you pick an engine:

  =============================================
    Select AI Engine (Multi-Provider Support)
  =============================================
  1) Llama 3.3 70B (Groq)    - High Reasoning [Rate Limited]
  2) Llama 3 8B (Groq)       - Fast / Free Tier
  3) Gemini 1.5 Flash (Google)- Fast / Efficient
  4) Claude 4.6 Sonnet (Anthropic) - Latest SOTA (2026)
  5) GPT-4o-Mini (OpenAI)    - Standard
  =============================================

Example session (Claude 4.6):

  Goal: Read every word on page 22 in workspace/FOMC-pres-conf-2026-04-29.pdf
        and save the results into a file called FOMC statement.txt inside the
        workspace folder.

  Result:
  {
    "ok": true,
    "steps": 3,
    "final": "I have successfully invoked the 'read_pdf_page' tool on page 22,
              extracted its contents, and saved the text to workspace/FOMC
              statement.txt."
  }


--- CLI ASSISTANT (TEXT-IN/TEXT-OUT) ---

A minimal command-line interface that sends user input to an LLM and prints the
response. Useful for quick prototyping, testing prompts, or simple Q&A without
any tool-calling complexity.

Run it:

  python scripts/cli_assistant.py

Example:

  You: Explain tokens in one paragraph.
  Assistant: Tokens are the basic units of text that an LLM processes...

The script uses a system prompt for consistency, low temperature for reliability,
and reads the API key from .env. It handles errors gracefully and keeps no state
between turns.


--- STRUCTURED JSON ASSISTANT ---

Forces the AI to return only valid JSON against a defined schema, with parsing
and validation in code. This is critical for any downstream automation that
expects deterministic data.

Run it:

  python scripts/json_assistant.py

How it works:

  - System prompt forbids markdown, explanations, or extra text – only raw JSON.
  - The model returns a string, which we parse with json.loads().
  - Validation checks: required keys, data types, allowed values
    (e.g., category in ["phishing", "benign", "unknown"]).
  - Any failure (invalid JSON, missing fields, type mismatch) raises a clear error.

This pattern is reused inside the event-driven workflow to extract structured
fields from free-text inputs.


--- EVENT-DRIVEN WORKFLOW AUTOMATION ---

A non-blocking filesystem watcher (watch_inbox.py) polls inbox/ for .txt files,
runs a multi-step pipeline, and moves processed files to inbox/processed/.

Example input (inbox/escalation.txt):

  Subject: Urgent customer escalation about billing errors. Please summarize and
  create next steps.

Pipeline steps (from workflow_steps.py):

  1. Load raw text – read file content.
  2. Extract structured fields – step2_extract_structured() calls the LLM to
     pull out topic, requester, urgency, summary, and action_items. Includes
     defensive cleaning (strip markdown, repair malformed JSON).
  3. Classify urgency → route (priority/standard/low) + SLA (4h/24h/72h).
  4. Generate draft reply – writes a professional response using only the
     extracted fields.
  5. Save outputs – writes result.json and draft_reply.txt to outbox/.
  6. Log execution – appends a timestamped record to logs/workflow.log.

Generated output (outbox/escalation/result.json):

  {
    "input_file": "inbox/escalation.txt",
    "extracted": {
      "topic": "Billing Errors",
      "requester": "Customer Support",
      "urgency": "high",
      "summary": "Urgent escalation from customer regarding discrepancies in billing cycles.",
      "action_items": ["Audit latest invoice records", "Draft adjustments validation payload"]
    },
    "route": "priority",
    "sla": "4 hours",
    "draft_reply": "Hello, thank you for reaching out..."
  }

The extraction step includes defensive markdown stripping and a try/except fallback,
so malformed LLM output never crashes the automation loop.


--- LOCAL RAG ON EARNINGS TRANSCRIPTS ---

To test the system’s ability to read financial disclosures without sending data
to third-party embedding APIs, you can place a sample transcript (say, a quarterly
earnings call) into data/docs/ and build a local index.

  python -m scripts.rag_assistant --build-index

The script chunks the text, runs a local embedding model (Nomic), and saves the
index to data/index.json. Once indexed, the terminal assistant can answer questions
without calling any external embedding API.

  Loading local embedding model...
  Document-Aware Assistant (type 'exit' to quit)

  You: Give me a concise summary of the financial performance and core focuses
        mentioned in the call.

  Top retrieved chunks:
  - score=0.814 source=meta_q1_2026.txt chunk=0
  - score=0.782 source=meta_q1_2026.txt chunk=1

  Assistant:
  According to the call [Source: meta_q1_2026.txt | chunk 0], the company showed
  double-digit revenue growth driven by ad targeting. Core focuses include
  infrastructure scaling for generative models, increased monetisation across
  family apps, and operational discipline [Source: meta_q1_2026.txt | chunk 1].

(The transcript files shown in examples are not part of this repository. Drop your
own .txt or .pdf files into data/docs/ and run the build command – you’ll get
similar structured output.)


--- SESSION-PERSISTENT MEMORY ---

The web UI (web/index.html) generates a session_id using crypto.randomUUID() and
stores it in localStorage. Each request to /api/chat sends { session_id, prompt }.

On the backend, src/session_store.py maintains an in-memory cache, writes sessions
to data/sessions.json, and cleans up old sessions automatically. This keeps the
stateless FastAPI server truly stateless while preserving conversation history
across page refreshes.


--- AUTOMATED TESTING & SYSTEM EVALUATION ---

To avoid breaking things when I tweak prompts or tool definitions, I built a
validation pipeline that enforces both structural correctness and safety.

Run it:

  python -m scripts.eval_run

What it includes:

  - Test cases (tests/test_cases.json) – ten scenarios: normal inputs, high urgency,
    missing fields, ambiguous content, long text, prompt injections, weird formatting,
    non-English, emptyish, and hostile language.

  - Validator module (src/eval/validators.py) – checks:
      * JSON parsing (strict)
      * Required keys (topic, requester, urgency, summary, action_items)
      * Urgency allowed values (low/medium/high)
      * Summary length <= 1200 chars
      * Action items <= 10, each a non-empty string
      * Safety blocklist – phrases like "ignore previous instructions",
        "system prompt" are rejected.

  - Evaluation runner (eval_run.py) – calls the extraction step, runs all test cases,
    and writes a report to reports/eval_report.json.

Why this matters: every change to the extraction prompt or model is automatically
tested against adversarial inputs. If something breaks, I know immediately.


DEPLOYMENT
----------

The FastAPI backend runs on Render. It’s containerised and accepts traffic through the usual web gateway.

Live URL: https://one4day-ai-systems-3e3v.onrender.com

Endpoints:

  GET /health
  Returns a simple status check – confirms the service is alive.

  POST /api/chat
  Expects JSON: { "session_id": "...", "prompt": "..." }
  Uses the session ID to keep conversation history (in‑memory + disk). Returns the AI response as JSON.

Environment variables you need to set in the Render dashboard (or locally in a `.env` file):

  PORT                     – assigned automatically by Render
  GROQ_API_KEY             – for Llama‑3‑8B (fast, free tier)
  OPENAI_API_KEY           – if you want GPT‑4o‑mini fallback
  ANTHROPIC_API_KEY        – for Claude 4.6 Sonnet 
  GOOGLE_API_KEY           – for Gemini 1.5 Flash

The start command (Render uses `$PORT` automatically):

  uvicorn src.app:app --host 0.0.0.0 --port $PORT
