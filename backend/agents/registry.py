"""Tool registry: declarations for Gemini, argument validation, permission checks,
execution logging, and graceful failure.

Every tool returns a JSON-serialisable dict. Failures are returned as
{"ok": False, "error": "..."} so the model can adapt instead of the request crashing.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from database import db
from models import ToolExecutionLog

log = logging.getLogger(__name__)

MAX_RESULT_CHARS = 30000


class ToolError(Exception):
    """A user-presentable tool failure (bad id, missing prerequisite, etc.)."""


@dataclass
class ToolContext:
    user_id: str
    conversation_id: str | None = None
    google_connected: bool = False  # set in Phase 5 from the user's stored OAuth grant
    citations: list = field(default_factory=list)  # filled by retrieval/research tools
    calls: list = field(default_factory=list)      # [{name, status, duration_ms}] for the UI
    presentation_id: str | None = None             # last draft the run created/touched
    on_call: Callable | None = None                # progress hook: on_call(tool_name, status)
    # The user's explicit choices (e.g. from the Create form). Tools enforce these no matter what the model passes.
    overrides: dict = field(default_factory=dict)

    def add_citation(self, **info) -> int:
        n = len(self.citations) + 1
        self.citations.append({"n": n, **info})
        return n


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[[ToolContext, dict], dict]
    requires_google: bool = False


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, properties: dict, required: list[str] | None = None, requires_google=False):
    def deco(fn):
        REGISTRY[name] = Tool(
            name=name,
            description=description,
            parameters={"type": "object", "properties": properties, "required": required or []},
            fn=fn,
            requires_google=requires_google,
        )
        return fn

    return deco


def declarations():
    from google.genai import types

    return [
        types.FunctionDeclaration(name=t.name, description=t.description, parameters_json_schema=t.parameters)
        for t in REGISTRY.values()
    ]


_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}


def _validate(t: Tool, args: dict):
    props = t.parameters["properties"]
    for req in t.parameters["required"]:
        if req not in args or args[req] in (None, ""):
            raise ToolError(f"Missing required argument '{req}'.")
    for k, v in args.items():
        spec = props.get(k)
        if not spec:
            continue  # ignore unknown args rather than failing the whole call
        want = _TYPES.get(spec.get("type"))
        if want and isinstance(v, bool) and spec.get("type") in ("integer", "number"):
            raise ToolError(f"Argument '{k}' must be {spec['type']}.")
        if want and not isinstance(v, want):
            if spec.get("type") == "integer" and isinstance(v, float) and v.is_integer():
                args[k] = int(v)  # Gemini sometimes sends 5.0
            else:
                raise ToolError(f"Argument '{k}' must be {spec['type']}.")


def execute(name: str, args: dict, ctx: ToolContext) -> dict:
    started = time.monotonic()
    status, error, result = "success", None, {}
    t = REGISTRY.get(name)
    try:
        if not t:
            raise ToolError(f"Unknown tool '{name}'.")
        if t.requires_google and not ctx.google_connected:
            raise ToolError("The user has not connected a Google account yet, so Google Slides actions are unavailable.")
        args = dict(args or {})
        _validate(t, args)
        result = t.fn(ctx, args)
        result = {"ok": True, **result} if "ok" not in result else result
    except ToolError as e:
        status, error = "error", str(e)
        result = {"ok": False, "error": error}
    except Exception as e:  # unexpected: log details, give the model a safe message
        db.session.rollback()
        log.exception("Tool %s crashed", name)
        status, error = "error", f"{type(e).__name__}"
        result = {"ok": False, "error": "The tool failed unexpectedly. Try a different approach or tell the user."}

    duration = int((time.monotonic() - started) * 1000)
    ctx.calls.append({"name": name, "status": status, "duration_ms": duration})
    if ctx.on_call:
        try:
            ctx.on_call(name, status)
        except Exception:
            log.exception("Progress hook failed")
    try:
        db.session.add(ToolExecutionLog(
            conversation_id=ctx.conversation_id, user_id=ctx.user_id, tool_name=name[:64],
            arguments=_loggable(args), result_summary=str(result)[:500], status=status,
            error=error, duration_ms=duration))
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.exception("Could not write tool log")

    text = str(result)
    if len(text) > MAX_RESULT_CHARS:
        result = {"ok": result.get("ok", True), "truncated": True, "note": "Result too large; narrow the request.",
                  "preview": text[:MAX_RESULT_CHARS // 3]}
    return result


def _loggable(args: dict):
    out = {}
    for k, v in (args or {}).items():
        out[k] = v if isinstance(v, (int, float, bool, type(None))) else str(v)[:300]
    return out
