import json
from typing import Any, Optional


def extract_first_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = [line for line in stripped.splitlines() if not line.strip().startswith("```")]
        stripped = "\n".join(lines).strip()
    try:
        value = json.loads(stripped)
        return value if isinstance(value, dict) else None
    except Exception:
        pass

    start = stripped.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(stripped)):
            char = stripped[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = stripped[start : index + 1]
                    try:
                        value = json.loads(candidate)
                        return value if isinstance(value, dict) else None
                    except Exception:
                        break
        start = stripped.find("{", start + 1)
    return None
