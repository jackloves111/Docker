from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

from flask import Flask, Response, abort, jsonify, render_template, request


QuoteStyle = Literal["none", "single", "double"]


class EnvEntry(TypedDict):
    id: int
    key: str
    value: str
    quote: QuoteStyle
    desc: str


@dataclass(frozen=True)
class ParsedLine:
    raw: str
    key: Optional[str]
    value: Optional[str]
    quote: QuoteStyle


_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _env_root() -> Path:
    return Path(os.environ.get("ENV_ROOT", "/config")).resolve()


def _env_filename() -> str:
    return os.environ.get("ENV_FILENAME", "app.env")

def _safe_path(rel_path: str) -> Path:
    root = _env_root()
    if not rel_path:
        abort(400, description="Missing path")
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        abort(400, description="Invalid path")
    return candidate


def _discover_env_files() -> list[str]:
    root = _env_root()
    name = _env_filename()
    if not root.exists():
        return []
    paths: list[str] = []
    for p in root.rglob(name):
        if not p.is_file():
            continue
        try:
            rel = p.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        paths.append(rel)
    paths.sort(key=lambda s: (s.count("/"), s))
    return paths


def _load_descriptions() -> dict[str, str]:
    p = Path(__file__).parent / "descriptions.json"
    if not p.exists():
        return {}
    try:
        import json
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, dict):
            out: dict[str, str] = {}
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, str) and _KEY_RE.match(k):
                    out[k] = v
            return out
    except Exception:
        return {}
    return {}


def _parse_line(raw: str) -> ParsedLine:
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return ParsedLine(raw=raw, key=None, value=None, quote="none")

    line = raw.lstrip()
    if line.startswith("export "):
        line = line[len("export ") :]

    if "=" not in line:
        return ParsedLine(raw=raw, key=None, value=None, quote="none")

    left, right = line.split("=", 1)
    key = left.strip()
    if not _KEY_RE.match(key):
        return ParsedLine(raw=raw, key=None, value=None, quote="none")

    value_part = right.strip()
    if len(value_part) >= 2 and value_part[0] == "'" and value_part[-1] == "'":
        return ParsedLine(raw=raw, key=key, value=value_part[1:-1], quote="single")
    if len(value_part) >= 2 and value_part[0] == '"' and value_part[-1] == '"':
        return ParsedLine(raw=raw, key=key, value=value_part[1:-1], quote="double")
    return ParsedLine(raw=raw, key=key, value=value_part, quote="none")


def _serialize_value(value: str, quote: QuoteStyle) -> str:
    if quote == "single":
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if quote == "double":
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def _read_env_file(path: Path) -> tuple[list[str], list[EnvEntry]]:
    if not path.exists() or not path.is_file():
        abort(404, description="File not found")
    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    descriptions = _load_descriptions()
    entries: list[EnvEntry] = []
    for i, raw in enumerate(raw_lines):
        parsed = _parse_line(raw)
        if parsed.key is None:
            continue
        entries.append(
            EnvEntry(
                id=i,
                key=parsed.key,
                value=parsed.value if parsed.value is not None else "",
                quote=parsed.quote,
                desc=descriptions.get(parsed.key, ""),
            )
        )
    return raw_lines, entries


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent)) as tf:
        tf.write(content)
        tf.flush()
        tmp_name = tf.name
    Path(tmp_name).replace(path)


def _update_env_file(path: Path, payload: dict[str, Any]) -> None:
    raw_lines, _ = _read_env_file(path)

    incoming_entries = payload.get("entries")
    if not isinstance(incoming_entries, list):
        abort(400, description="Invalid entries")

    updates_by_id: dict[int, dict[str, Any]] = {}
    for e in incoming_entries:
        if not isinstance(e, dict):
            continue
        if "id" in e and isinstance(e["id"], int):
            updates_by_id[e["id"]] = e

    for line_id, e in updates_by_id.items():
        if line_id < 0 or line_id >= len(raw_lines):
            abort(400, description="Invalid id")
        value = e.get("value")
        quote = e.get("quote", "none")
        if not isinstance(value, str):
            abort(400, description="Invalid value")
        if quote not in ("none", "single", "double"):
            abort(400, description="Invalid quote")
        # Preserve original key from the line
        parsed = _parse_line(raw_lines[line_id])
        key = parsed.key or ""
        if not _KEY_RE.match(key):
            abort(400, description="Invalid key")
        raw_lines[line_id] = f"{key}={_serialize_value(value, quote)}"
    upserts = payload.get("upserts")
    if isinstance(upserts, list):
        appended_lines: list[str] = []
        for u in upserts:
            if not isinstance(u, dict):
                continue
            key = u.get("key")
            value = u.get("value")
            quote = u.get("quote", "none")
            if not isinstance(key, str) or not _KEY_RE.match(key):
                abort(400, description="Invalid key")
            if not isinstance(value, str):
                abort(400, description="Invalid value")
            if quote not in ("none", "single", "double"):
                abort(400, description="Invalid quote")
            found_index: Optional[int] = None
            for i, raw in enumerate(raw_lines):
                p = _parse_line(raw)
                if p.key == key:
                    found_index = i
                    break
            line_text = f"{key}={_serialize_value(value, quote)}"
            if found_index is not None:
                raw_lines[found_index] = line_text
            else:
                appended_lines.append(line_text)
        while raw_lines and raw_lines[-1] == "":
            raw_lines.pop()
        if appended_lines:
            if raw_lines:
                raw_lines.append("")
            raw_lines.extend(appended_lines)


    content = "\n".join(raw_lines).rstrip("\n") + "\n"


app = Flask(__name__)


@app.get("/")
def index() -> str:
    return render_template(
        "index.html",
        env_root=_env_root().as_posix(),
        env_filename=_env_filename(),
    )


@app.get("/api/files")
def api_files() -> Response:
    root = _env_root()
    return jsonify(
        {"root": root.as_posix(), "rootExists": root.exists(), "files": _discover_env_files()}
    )


@app.get("/api/env")
def api_env() -> Response:
    rel_path = request.args.get("path", "")
    path = _safe_path(rel_path)
    _, entries = _read_env_file(path)
    return jsonify({"path": rel_path, "entries": entries})


@app.put("/api/env")
def api_env_put() -> Response:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, description="Invalid JSON")
    rel_path = payload.get("path")
    if not isinstance(rel_path, str):
        abort(400, description="Missing path")
    path = _safe_path(rel_path)
    _update_env_file(path, payload)
    _, entries = _read_env_file(path)
    return jsonify({"path": rel_path, "entries": entries})


@app.get("/healthz")
def healthz() -> Response:
    return Response("ok", mimetype="text/plain")


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
