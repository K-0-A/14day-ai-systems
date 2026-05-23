import os
import time
from typing import Dict, Any
 
from src.workflow_steps import (
    step1_load_input,
    step2_extract_structured,
    step3_classify_and_route,
    step4_generate_draft_reply,
    step5_save_outputs,
    step6_log_run
)
 
def run_workflow(input_file: str, out_dir: str, log_file: str) -> Dict[str, Any]:
    # Step 1: load
    s1 = step1_load_input(input_file)
    if not s1["ok"]:
        step6_log_run(log_file, {"ok": False, "step": 1, "error": s1.get("error"), "file": input_file})
        return s1
 
    # Step 2: extract JSON
    s2 = step2_extract_structured(s1["raw_text"])
    if not s2["ok"]:
        step6_log_run(log_file, {"ok": False, "step": 2, "error": s2.get("error"), "file": input_file})
        return s2
 
    extracted = s2["extracted"]
 
    # Step 3: route
    s3 = step3_classify_and_route(extracted)
    if not s3["ok"]:
        step6_log_run(log_file, {"ok": False, "step": 3, "error": s3.get("error"), "file": input_file})
        return s3
 
    # Step 4: draft reply
    s4 = step4_generate_draft_reply(extracted, s3["route"], s3["sla"])
    if not s4["ok"]:
        step6_log_run(log_file, {"ok": False, "step": 4, "error": s4.get("error"), "file": input_file})
        return s4
 
    payload = {
        "input_file": input_file,
        "extracted": extracted,
        "route": s3["route"],
        "sla": s3["sla"],
        "draft_reply": s4["draft_reply"],
    }
 
    # Step 5: save
    out_base = os.path.join(out_dir, os.path.splitext(os.path.basename(input_file))[0])
    s5 = step5_save_outputs(out_base, payload)
 
    # Step 6: log
    step6_log_run(log_file, {"ok": True, "file": input_file, "out_base": out_base})
 
    return {"ok": True, "out_base": out_base, "saved": s5}