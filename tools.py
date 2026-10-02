"""Tools the agent can call. File tools are locked to the ./workspace folder."""

import ast
import datetime
import operator
from pathlib import Path

WORKSPACE = Path(__file__).parent / "workspace"
WORKSPACE.mkdir(exist_ok=True)

# ---------- safe calculator ----------
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression):
    try:
        return str(_eval(ast.parse(expression, mode="eval").body))
    except Exception as exc:
        return f"Error: {exc}"


# ---------- sandboxed files ----------
def _safe_path(name):
    path = (WORKSPACE / name).resolve()
    if WORKSPACE.resolve() not in path.parents and path != WORKSPACE.resolve():
        raise ValueError("Path is outside the workspace")
    return path


def read_file(filename):
    try:
        return _safe_path(filename).read_text(encoding="utf-8")
    except Exception as exc:
        return f"Error: {exc}"


def write_file(filename, content):
    try:
        path = _safe_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} characters to {filename}"
    except Exception as exc:
        return f"Error: {exc}"


def list_files(_unused=""):
    files = sorted(str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*") if p.is_file())
    return "\n".join(files) if files else "(workspace is empty)"


def current_time(_unused=""):
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- schemas (Gemini function-declaration format) + dispatch ----------
GEMINI_TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression, e.g. '(12 + 8) * 3'.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file from the workspace folder.",
        "parameters": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a text file in the workspace folder.",
        "parameters": {
            "type": "object",
            "properties": {"filename": {"type": "string"}, "content": {"type": "string"}},
            "required": ["filename", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files in the workspace folder.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "current_time",
        "description": "Get the current local date and time.",
        "parameters": {"type": "object", "properties": {}},
    },
]

_DISPATCH = {
    "calculator": lambda a: calculator(a.get("expression", "")),
    "read_file": lambda a: read_file(a.get("filename", "")),
    "write_file": lambda a: write_file(a.get("filename", ""), a.get("content", "")),
    "list_files": lambda a: list_files(),
    "current_time": lambda a: current_time(),
}


def run_tool(name, args):
    handler = _DISPATCH.get(name)
    return handler(args or {}) if handler else f"Error: unknown tool '{name}'"
