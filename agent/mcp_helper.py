"""MCP client helpers for the orchestrator."""

import json
import re
from typing import Any, Dict, Optional


async def call_tool(session, tool_name: str, args: Optional[Dict[str, Any]] = None):
    """Call an MCP tool and parse JSON/text payloads into Python objects."""
    try:
        result = await session.call_tool(tool_name, args or {})
        if not result or not result.content:
            return None

        parsed_contents = []
        for content in result.content:
            parsed = None
            if hasattr(content, "text"):
                text = content.text.strip()
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = text
            elif isinstance(content, dict) and "text" in content:
                try:
                    parsed = json.loads(content["text"])
                except Exception:
                    parsed = content["text"]

            if parsed is not None:
                parsed_contents.append(parsed)

        if not parsed_contents:
            return None
        return parsed_contents if len(parsed_contents) > 1 else parsed_contents[0]
    except Exception as e:
        print(f"Tool call error ({tool_name}): {e}")
    return None


def robust_json_parse(text: str):
    """Robust JSON parsing with auto-repair for LLM output."""
    json_str = text
    if "```json" in text:
        json_str = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        json_str = text.split("```")[1].split("```")[0].strip()

    try:
        start = json_str.find("{")
        end = json_str.rfind("}")
        if start != -1 and end != -1:
            json_str = json_str[start : end + 1]
    except Exception:
        pass

    json_str = json_str.replace("\t", "\\t")

    # Remove single-line C-style comments (e.g., // comment)
    json_str = re.sub(r"//.*", "", json_str)

    # Fix LLM arbitrarily placing closing parenthesis instead of brace e.g. {"sector": "...", "reason": "...".)
    json_str = re.sub(r'"\s*\)\s*,', '"},', json_str)
    json_str = re.sub(r'"\s*\)(\s*)$', '"}', json_str)
    json_str = re.sub(r'\.\s*"\)', '."}', json_str)

    # Auto-close missing braces
    open_braces = json_str.count("{")
    close_braces = json_str.count("}")
    if open_braces > close_braces:
        json_str += "}" * (open_braces - close_braces)

    # Fix missing commas between drone entries
    json_str = re.sub(r'}\s*\n\s*"drone_', '},\n"drone_', json_str)

    try:
        return json.loads(json_str, strict=False)
    except Exception as first_error:
        try:
            relaxed = re.sub(
                r'("reason":\s*")(.*?)("(?=\s*[},]))',
                lambda m: m.group(1) + m.group(2).replace('"', "'") + m.group(3),
                json_str,
                flags=re.DOTALL,
            )
            return json.loads(relaxed, strict=False)
        except Exception:
            with open("/tmp/last_malformed_response.txt", "w") as f:
                f.write(text)
            raise first_error
