import json
from typing import Dict, Any, List
from pathlib import Path
 
from src.eval.validators import evaluate_output
 
# Choose one AI function to test:
# Option A: reuse your Day 10 extraction step
from src.workflow_steps import step2_extract_structured
 
 
def call_system_under_test(user_input: str) -> str:
    """
    Returns raw model text output (JSON string expected).
    step2_extract_structured currently parses JSON internally.
    For eval, we want the raw JSON string. If your function parses internally,
    modify it to optionally return raw text.
    """
    # QUICK ADAPTATION:
    # If your step2 returns dict with extracted data, we re-serialize for validation.
    # (This makes it less strict than validating the raw model output, but still useful.)
    result = step2_extract_structured(user_input)
    if not result.get("ok"):
        # Return something clearly invalid for the validator
        return "INVALID_JSON"
    return json.dumps(result["extracted"])
 
 
def main():
    cases: List[Dict[str, Any]] = json.loads(Path("tests/test_cases.json").read_text(encoding="utf-8"))
    report = {"total": len(cases), "passed": 0, "failed": 0, "results": []}
 
    for c in cases:
        case_id = c["id"]
        user_input = c["input"]
        expect = c["expect"]
 
        raw = call_system_under_test(user_input)
 
        eval_result = evaluate_output(
            raw_model_text=raw,
            required_keys=expect["required_keys"],
            urgency_allowed=expect["urgency_allowed"],
        )
 
        row = {
            "id": case_id,
            "pass": eval_result["pass"],
            "errors": eval_result.get("errors", []),
        }
        report["results"].append(row)
 
        if row["pass"]:
            report["passed"] += 1
        else:
            report["failed"] += 1
 
    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("reports/eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
 
    print(f"Total: {report['total']}, Passed: {report['passed']}, Failed: {report['failed']}")
    print("Report saved to reports/eval_report.json")
 
 
if __name__ == "__main__":
    main()