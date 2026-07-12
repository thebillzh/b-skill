#!/usr/bin/env python3
"""Analyze one Codex thread turn from raw rollout JSONL.

The script is intentionally stdlib-only so the skill can run from any Codex
checkout without project dependencies.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - Python <3.9 fallback is UTC-only.
    ZoneInfo = None  # type: ignore


ISO_Z_RE = re.compile(r"Z$")
WALL_RE = re.compile(r"Wall time:\s*([0-9]+(?:\.[0-9]+)?)\s*seconds", re.I)
EXIT_RE = re.compile(r"(?:Process exited with code|Exit code:)\s*(-?\d+)", re.I)
ORIG_TOK_RE = re.compile(r"Original token count:\s*([0-9]+)", re.I)

STALL_WORDS = re.compile(
    r"\b(blocked|quota|failed|failure|error|retry|relaunch|stale|still running|aborted|timeout|timed out|not stale|empty output)\b",
    re.I,
)


def parse_ts(value: str) -> dt.datetime:
    value = ISO_Z_RE.sub("+00:00", value)
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def fmt_ms(ms: float) -> str:
    total_tenths = int(round(ms / 100.0))
    total_seconds, tenths = divmod(total_tenths, 10)
    if total_seconds < 60:
        return f"{total_seconds}.{tenths}s"
    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}.{tenths}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds:02d}.{tenths}s"


def fmt_dt(ts: dt.datetime, tz_name: str) -> str:
    if ZoneInfo is not None:
        try:
            return ts.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            pass
    return ts.isoformat().replace("+00:00", "Z")


def short(text: Any, max_chars: int = 180) -> str:
    if text is None:
        return ""
    s = str(text).replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def command_from_arguments(arguments: Any) -> tuple[str, dict[str, Any]]:
    if not arguments:
        return "", {}
    if isinstance(arguments, dict):
        data = arguments
    else:
        try:
            data = json.loads(arguments)
        except Exception:
            return str(arguments), {}
    cmd = data.get("cmd") or data.get("command") or data.get("chars") or ""
    return str(cmd), data


def classify_tool(name: str, command: str, input_text: str = "") -> str:
    hay = f"{name} {command} {input_text}".lower()
    stripped = command.strip().lower()
    if name == "apply_patch":
        return "edit_patch"
    if name == "write_stdin":
        return "session_wait"
    if re.search(r"\b(cargo (test|nextest|check|clippy)|npm (test|run|exec)|pnpm |pytest|tsc|typecheck|lint|format)\b", hay):
        return "verification"
    if re.search(r"\b(gh |git |pr-summary)\b", hay):
        return "git_pr"
    if "claude" in hay or "opencode" in hay or "codex review" in hay:
        return "external_agent_review"
    if re.search(r"\b(start|stop|restart|sandbox|server|pm2|launch|health|curl|observe)\b", hay):
        return "runtime_probe"
    if stripped.startswith(("sed ", "rg ", "grep ", "cat ", "ls ", "find ", "jq ", "python", "node", "awk ", "wc ", "head ", "tail ")):
        return "inspection"
    if name in {"exec_command", "write_stdin"}:
        return "shell_other"
    return name or "tool_other"


def output_stats(output: Any, max_chars: int) -> dict[str, Any]:
    text = "" if output is None else str(output)
    wall = None
    m = WALL_RE.search(text)
    if m:
        wall = float(m.group(1))
    exit_code = None
    m = EXIT_RE.search(text)
    if m:
        exit_code = int(m.group(1))
    original_tokens = None
    m = ORIG_TOK_RE.search(text)
    if m:
        original_tokens = int(m.group(1))
    return {
        "exit_code": exit_code,
        "reported_wall_seconds": wall,
        "original_token_count": original_tokens,
        "truncated_by_codex": "Warning: truncated output" in text or "truncated" in text.lower(),
        "preview": text[:max_chars],
        "tail_preview": text[-max_chars:] if len(text) > max_chars else "",
        "char_count": len(text),
    }


@dataclass
class Turn:
    turn_id: str
    start_index: int
    start_ts: dt.datetime
    completed_ts: dt.datetime | None = None
    end_index: int | None = None
    user_message: str = ""

    @property
    def duration_ms(self) -> float:
        end = self.completed_ts or self.start_ts
        return max(0.0, (end - self.start_ts).total_seconds() * 1000)


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    skipped_malformed = 0
    skipped_missing_ts = 0
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped_malformed += 1
                continue
            if not isinstance(obj, dict):
                skipped_malformed += 1
                continue
            timestamp = obj.get("timestamp")
            if timestamp is None:
                skipped_missing_ts += 1
                continue
            obj["_index"] = idx
            obj["_ts"] = parse_ts(timestamp)
            events.append(obj)
    if skipped_malformed or skipped_missing_ts:
        print(
            f"warning: skipped {skipped_malformed} malformed JSON line(s) and "
            f"{skipped_missing_ts} event(s) missing a timestamp while loading {path}",
            file=sys.stderr,
        )
    events.sort(key=lambda e: (e["_ts"], e["_index"]))
    return events


def resolve_session_path(thread_id: str | None, session_path: str | None) -> Path:
    if session_path:
        path = Path(session_path).expanduser()
        if not path.exists():
            raise SystemExit(f"session file not found: {path}")
        return path
    if not thread_id:
        raise SystemExit("provide --thread-id or --session")
    base = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    matches = glob.glob(str(base / "sessions" / "**" / f"*{thread_id}*.jsonl"), recursive=True)
    matches = [p for p in matches if Path(p).is_file()]
    if not matches:
        raise SystemExit(f"no Codex session JSONL found for thread id {thread_id} under {base / 'sessions'}")
    matches.sort(key=lambda p: Path(p).stat().st_mtime, reverse=True)
    return Path(matches[0])


def message_text_from_event(ev: dict[str, Any]) -> str:
    payload = ev.get("payload") or {}
    ev_type = ev.get("type")
    ptype = payload.get("type")
    if ev_type == "event_msg" and ptype == "user_message":
        return str(payload.get("message") or "")
    if ev_type == "response_item" and ptype == "message" and payload.get("role") == "user":
        return text_from_message_content(payload.get("content"))
    return ""


def is_environment_message(text: str) -> bool:
    return "<environment_context>" in text


def is_synthetic_turn_start(ev: dict[str, Any]) -> bool:
    payload = ev.get("payload") or {}
    ev_type = ev.get("type")
    ptype = payload.get("type")
    if ev_type == "session_meta":
        return False
    if message_text_from_event(ev):
        return True
    if ev_type == "response_item":
        return True
    return ev_type == "event_msg" and ptype in {"agent_message", "agent_reasoning", "token_count"}


def synthesize_session_turn(events: list[dict[str, Any]]) -> Turn | None:
    if not events:
        return None
    start = next((ev for ev in events if is_synthetic_turn_start(ev)), events[0])
    end = events[-1]
    meta = next((e.get("payload") for e in events if e.get("type") == "session_meta"), {}) or {}
    turn_id = meta.get("id") or meta.get("session_id") or f"synthetic-turn-{start['_index']}"
    turn = Turn(
        turn_id=str(turn_id),
        start_index=start["_index"],
        start_ts=start["_ts"],
        completed_ts=end["_ts"],
        end_index=end["_index"],
    )
    return turn


def find_turns(events: list[dict[str, Any]]) -> list[Turn]:
    turns: list[Turn] = []
    active: dict[str, Turn] = {}
    for ev in events:
        payload = ev.get("payload") or {}
        if ev.get("type") == "event_msg" and payload.get("type") == "task_started":
            turn_id = payload.get("turn_id") or f"turn-at-{ev['_index']}"
            turn = Turn(turn_id=turn_id, start_index=ev["_index"], start_ts=ev["_ts"])
            turns.append(turn)
            active[turn_id] = turn
        elif ev.get("type") == "event_msg" and payload.get("type") == "task_complete":
            turn_id = payload.get("turn_id")
            turn = active.get(turn_id) if turn_id else (turns[-1] if turns else None)
            if turn:
                turn.completed_ts = ev["_ts"]
                turn.end_index = ev["_index"]
                active.pop(turn.turn_id, None)
    if not turns:
        synthetic = synthesize_session_turn(events)
        if synthetic:
            turns.append(synthetic)
    for i, turn in enumerate(turns):
        if turn.completed_ts is None:
            next_start = turns[i + 1].start_ts if i + 1 < len(turns) else events[-1]["_ts"]
            turn.completed_ts = next_start
        if turn.end_index is None:
            next_idx = turns[i + 1].start_index if i + 1 < len(turns) else events[-1]["_index"]
            turn.end_index = next_idx
    # Attach the first non-environment user message inside each turn.
    for turn in turns:
        for ev in events:
            if ev["_index"] < turn.start_index or ev["_index"] > (turn.end_index or turn.start_index):
                continue
            msg = message_text_from_event(ev)
            if msg and not is_environment_message(msg):
                turn.user_message = msg
                break
    return turns


def select_turn(turns: list[Turn], turn_id: str | None, select: str, min_duration_min: float) -> Turn:
    if not turns:
        raise SystemExit("no task_started/task_complete turns found")
    if turn_id:
        for turn in turns:
            if turn.turn_id == turn_id:
                return turn
        raise SystemExit(f"turn id not found: {turn_id}")
    if select == "latest":
        return turns[-1]
    if select == "longest":
        return max(turns, key=lambda t: t.duration_ms)
    if select == "recent-long":
        min_ms = min_duration_min * 60_000
        for turn in reversed(turns):
            if turn.duration_ms >= min_ms:
                return turn
        return max(turns, key=lambda t: t.duration_ms)
    raise SystemExit(f"unknown --select value: {select}")


def text_from_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("message") or ""))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)
    return ""


def text_from_reasoning_payload(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("text", "content", "summary"):
        text = text_from_message_content(payload.get(key))
        if text:
            parts.append(text)
    if parts:
        return "\n".join(parts)
    if payload.get("encrypted_content"):
        return "[encrypted reasoning content present]"
    return ""


def reasoning_title(text: str) -> str:
    m = re.match(r"\*\*([^*]+)\*\*", text.strip())
    if m:
        return m.group(1).strip()
    first = text.strip().splitlines()[0] if text.strip() else "reasoning"
    return short(first, 80)


def analyze_turn(
    events: list[dict[str, Any]],
    turn: Turn,
    session_path: Path,
    tz: str,
    max_output_chars: int,
    long_call_ms: float,
    long_gap_ms: float,
) -> dict[str, Any]:
    interval = [e for e in events if turn.start_index <= e["_index"] <= (turn.end_index or turn.start_index)]
    calls: dict[str, dict[str, Any]] = {}
    ordered_calls: list[dict[str, Any]] = []
    agent_messages: list[dict[str, Any]] = []
    reasoning: list[dict[str, Any]] = []
    compactions: list[dict[str, Any]] = []
    token_records: list[dict[str, Any]] = []
    user_messages: list[str] = []

    for ev in interval:
        payload = ev.get("payload") or {}
        ts = ev["_ts"]
        ev_type = ev.get("type")
        ptype = payload.get("type")

        if ev_type == "event_msg" and ptype == "user_message":
            msg = payload.get("message") or ""
            if "<environment_context>" not in msg:
                user_messages.append(msg)
        if ev_type == "response_item" and ptype == "message" and payload.get("role") == "user":
            msg = text_from_message_content(payload.get("content"))
            if msg and "<environment_context>" not in msg:
                user_messages.append(msg)

        if ev_type == "event_msg" and ptype == "agent_message":
            agent_messages.append({"ts": ts.isoformat(), "local_time": fmt_dt(ts, tz), "message": payload.get("message") or ""})
        elif ev_type == "event_msg" and ptype == "agent_reasoning":
            text = payload.get("text") or ""
            reasoning.append({"ts": ts.isoformat(), "local_time": fmt_dt(ts, tz), "title": reasoning_title(text), "text": text, "source": "event_msg"})
        elif ev_type == "response_item" and ptype == "reasoning":
            text = text_from_reasoning_payload(payload)
            reasoning.append({"ts": ts.isoformat(), "local_time": fmt_dt(ts, tz), "title": reasoning_title(text), "text": text, "source": "response_item"})
        elif ev_type in {"compacted", "inter_agent_communication"} or (ev_type == "event_msg" and ptype == "context_compacted"):
            compactions.append({"ts": ts.isoformat(), "local_time": fmt_dt(ts, tz), "type": ev_type, "payload_type": ptype})
        elif ev_type == "event_msg" and ptype == "token_count":
            info = payload.get("info") or {}
            token_records.append({"ts": ts.isoformat(), "local_time": fmt_dt(ts, tz), "info": info})

        if ev_type == "response_item" and ptype in {"function_call", "custom_tool_call", "web_search_call"}:
            call_id = payload.get("call_id") or payload.get("id") or f"call-{ev['_index']}"
            name = payload.get("name") or payload.get("action", {}).get("type") or ptype
            command, args_obj = command_from_arguments(payload.get("arguments"))
            input_text = payload.get("input") or ""
            if not command and input_text:
                command = short(input_text, 500)
            category = classify_tool(name, command, input_text)
            call = {
                "ordinal": len(ordered_calls) + 1,
                "call_id": call_id,
                "type": ptype,
                "name": name,
                "category": category,
                "start_ts": ts.isoformat(),
                "start_local": fmt_dt(ts, tz),
                "end_ts": None,
                "end_local": None,
                "elapsed_ms": None,
                "arguments": args_obj if args_obj else payload.get("arguments"),
                "command": command,
                "input_preview": short(input_text, 800),
                "status": payload.get("status"),
                "output": None,
            }
            if ptype == "web_search_call":
                call["end_ts"] = ts.isoformat()
                call["end_local"] = fmt_dt(ts, tz)
                call["elapsed_ms"] = 0.0
                call["output"] = output_stats(
                    json.dumps({"status": payload.get("status"), "action": payload.get("action")}, ensure_ascii=False),
                    max_output_chars,
                )
            calls[call_id] = call
            ordered_calls.append(call)
        elif ev_type == "response_item" and ptype in {"function_call_output", "custom_tool_call_output"}:
            call_id = payload.get("call_id") or f"output-{ev['_index']}"
            call = calls.get(call_id)
            if call is None:
                call = {
                    "ordinal": len(ordered_calls) + 1,
                    "call_id": call_id,
                    "type": "unknown_call",
                    "name": "unknown",
                    "category": "unknown_tool",
                    "start_ts": None,
                    "start_local": None,
                    "end_ts": ts.isoformat(),
                    "end_local": fmt_dt(ts, tz),
                    "elapsed_ms": None,
                    "arguments": None,
                    "command": "",
                    "input_preview": "",
                    "status": None,
                    "output": None,
                }
                calls[call_id] = call
                ordered_calls.append(call)
            call["end_ts"] = ts.isoformat()
            call["end_local"] = fmt_dt(ts, tz)
            if call.get("start_ts"):
                call["elapsed_ms"] = (ts - parse_ts(call["start_ts"])).total_seconds() * 1000
            call["output"] = output_stats(payload.get("output"), max_output_chars)

    # Timeline segment allocation.
    active: dict[str, dict[str, Any]] = {}
    last_mode = "startup"
    prev_ts: dt.datetime | None = None
    segments: list[dict[str, Any]] = []
    mode_ms: Counter[str] = Counter()
    category_ms: Counter[str] = Counter()

    for ev in interval:
        ts = ev["_ts"]
        if prev_ts is not None and ts > prev_ts:
            gap_ms = (ts - prev_ts).total_seconds() * 1000
            if active:
                first_active = next(iter(active.values()))
                mode = "tool_wait"
                category = first_active.get("category") or "tool_other"
                label = f"tool_wait:{category}"
            else:
                mode = last_mode
                category = last_mode
                label = last_mode
            segments.append({"start_ts": prev_ts.isoformat(), "end_ts": ts.isoformat(), "elapsed_ms": gap_ms, "mode": mode, "category": category, "label": label})
            mode_ms[mode] += gap_ms
            category_ms[category] += gap_ms
        payload = ev.get("payload") or {}
        ev_type = ev.get("type")
        ptype = payload.get("type")
        if ev_type == "response_item" and ptype in {"function_call", "custom_tool_call"}:
            call_id = payload.get("call_id") or payload.get("id") or f"call-{ev['_index']}"
            if call_id in calls:
                active[call_id] = calls[call_id]
            last_mode = "tool_issued"
        elif ev_type == "response_item" and ptype == "web_search_call":
            last_mode = "tool_output_processing"
        elif ev_type == "response_item" and ptype in {"function_call_output", "custom_tool_call_output"}:
            call_id = payload.get("call_id") or f"output-{ev['_index']}"
            active.pop(call_id, None)
            last_mode = "tool_output_processing"
        elif ev_type == "event_msg" and ptype == "agent_reasoning":
            last_mode = "model_reasoning"
        elif ev_type == "response_item" and ptype == "reasoning":
            last_mode = "model_reasoning"
        elif ev_type == "event_msg" and ptype == "agent_message":
            last_mode = "agent_message"
        elif ev_type in {"compacted"} or (ev_type == "event_msg" and ptype == "context_compacted"):
            last_mode = "context_compaction"
        elif ev_type == "event_msg" and ptype == "token_count":
            # Token telemetry often lands between true activity markers; keep current mode.
            pass
        prev_ts = ts

    long_calls = [c for c in ordered_calls if (c.get("elapsed_ms") or 0) >= long_call_ms]
    failed_calls = [c for c in ordered_calls if (c.get("output") or {}).get("exit_code") not in (None, 0)]
    truncated_calls = [c for c in ordered_calls if (c.get("output") or {}).get("truncated_by_codex")]
    long_gaps = [s for s in segments if s["elapsed_ms"] >= long_gap_ms]
    stall_messages = [m for m in agent_messages if STALL_WORDS.search(m["message"])]
    stall_reasoning = [r for r in reasoning if STALL_WORDS.search(r["title"] + "\n" + r["text"])]

    category_counts = Counter(c["category"] for c in ordered_calls)
    category_call_ms: Counter[str] = Counter()
    for c in ordered_calls:
        category_call_ms[c["category"]] += c.get("elapsed_ms") or 0

    # Time bins for quick visual inspection.
    bin_ms = 5 * 60_000
    bins: list[dict[str, Any]] = []
    start = turn.start_ts
    end = turn.completed_ts or interval[-1]["_ts"]
    cursor = start
    while cursor < end:
        b_end = min(end, cursor + dt.timedelta(milliseconds=bin_ms))
        b_events = [e for e in interval if cursor <= e["_ts"] < b_end]
        b_calls = [c for c in ordered_calls if c.get("start_ts") and cursor <= parse_ts(c["start_ts"]) < b_end]
        b_agent = [m for m in agent_messages if cursor <= parse_ts(m["ts"]) < b_end]
        b_stall = [m for m in b_agent if STALL_WORDS.search(m["message"])]
        bins.append(
            {
                "start_local": fmt_dt(cursor, tz),
                "end_local": fmt_dt(b_end, tz),
                "event_count": len(b_events),
                "tool_call_count": len(b_calls),
                "tool_categories": dict(Counter(c["category"] for c in b_calls)),
                "agent_message_count": len(b_agent),
                "stall_message_count": len(b_stall),
                "sample_agent_messages": [short(m["message"], 220) for m in b_agent[:3]],
            }
        )
        cursor = b_end

    last_token = token_records[-1]["info"] if token_records else {}
    total_usage = last_token.get("total_token_usage") or {}

    result = {
        "session_path": str(session_path),
        "thread_id": None,
        "turn": {
            "turn_id": turn.turn_id,
            "start_ts": turn.start_ts.isoformat(),
            "start_local": fmt_dt(turn.start_ts, tz),
            "completed_ts": (turn.completed_ts or interval[-1]["_ts"]).isoformat(),
            "completed_local": fmt_dt(turn.completed_ts or interval[-1]["_ts"], tz),
            "duration_ms": turn.duration_ms,
            "duration_human": fmt_ms(turn.duration_ms),
            "user_message": (turn.user_message or (user_messages[-1] if user_messages else "")).strip(),
        },
        "counts": {
            "events": len(interval),
            "tool_calls": len(ordered_calls),
            "agent_messages": len(agent_messages),
            "reasoning_items": len(reasoning),
            "compactions": len(compactions),
            "token_records": len(token_records),
        },
        "time_allocation": {
            "by_segment_mode_ms": dict(mode_ms),
            "by_segment_mode_human": {k: fmt_ms(v) for k, v in mode_ms.most_common()},
            "by_tool_wait_category_ms": dict(category_ms),
            "by_tool_wait_category_human": {k: fmt_ms(v) for k, v in category_ms.most_common()},
            "by_tool_call_elapsed_ms": dict(category_call_ms),
            "by_tool_call_elapsed_human": {k: fmt_ms(v) for k, v in category_call_ms.most_common()},
        },
        "tool_summary": {
            "category_counts": dict(category_counts),
            "long_calls": [summarize_call(c) for c in long_calls],
            "failed_calls": [summarize_call(c) for c in failed_calls],
            "truncated_calls": [summarize_call(c) for c in truncated_calls],
        },
        "stuck_signals": {
            "long_gap_count": len(long_gaps),
            "long_gaps": long_gaps[:80],
            "stall_agent_messages": stall_messages,
            "stall_reasoning": [{"ts": r["ts"], "local_time": r["local_time"], "title": r["title"], "text_preview": short(r["text"], 500)} for r in stall_reasoning[:80]],
            "compactions": compactions,
        },
        "token_usage_last_record": total_usage,
        "reasoning_title_counts": dict(Counter(r["title"] for r in reasoning).most_common(40)),
        "agent_messages": agent_messages,
        "time_bins_5m": bins,
        "tool_calls": ordered_calls,
    }

    meta = next((e.get("payload") for e in events if e.get("type") == "session_meta"), {}) or {}
    result["thread_id"] = meta.get("id") or meta.get("session_id")
    return result


def summarize_call(call: dict[str, Any]) -> dict[str, Any]:
    out = call.get("output") or {}
    return {
        "ordinal": call.get("ordinal"),
        "call_id": call.get("call_id"),
        "name": call.get("name"),
        "category": call.get("category"),
        "start_local": call.get("start_local"),
        "elapsed_human": fmt_ms(call.get("elapsed_ms") or 0),
        "reported_wall_seconds": out.get("reported_wall_seconds"),
        "exit_code": out.get("exit_code"),
        "command": short(call.get("command") or call.get("input_preview"), 240),
        "output_preview": short(out.get("preview"), 240),
    }


def render_markdown(analysis: dict[str, Any], tz: str) -> str:
    turn = analysis["turn"]
    counts = analysis["counts"]
    tool_summary = analysis["tool_summary"]
    lines: list[str] = []
    lines.append(f"# Codex turn analysis: `{turn['turn_id']}`")
    lines.append("")
    lines.append(f"- Thread: `{analysis.get('thread_id')}`")
    lines.append(f"- Local window: {turn['start_local']} → {turn['completed_local']}")
    lines.append(f"- Duration: **{turn['duration_human']}**")
    lines.append(f"- Raw session: `{analysis['session_path']}`")
    if turn.get("user_message"):
        lines.append(f"- User message: {short(turn['user_message'], 260)}")
    lines.append("")

    lines.append("## 1. Headline counts")
    lines.append("")
    lines.append(f"1. Events in interval: {counts['events']}")
    lines.append(f"2. Tool calls: {counts['tool_calls']}")
    lines.append(f"3. Agent messages: {counts['agent_messages']}")
    lines.append(f"4. Reasoning items: {counts['reasoning_items']}")
    lines.append(f"5. Context compactions: {counts['compactions']}")
    usage = analysis.get("token_usage_last_record") or {}
    if usage:
        lines.append(
            "6. Last recorded cumulative tokens: "
            + ", ".join(f"{k}={v}" for k, v in usage.items() if isinstance(v, int))
        )
    lines.append("")

    lines.append("## 2. Wall-clock allocation")
    lines.append("")
    lines.append("### Segment modes")
    for i, (mode, human) in enumerate(analysis["time_allocation"]["by_segment_mode_human"].items(), 1):
        pct = (analysis["time_allocation"]["by_segment_mode_ms"].get(mode, 0) / max(turn["duration_ms"], 1)) * 100
        lines.append(f"{i}. `{mode}`: {human} ({pct:.1f}%)")
    lines.append("")
    lines.append("### Tool wait / tool category time")
    for i, (cat, human) in enumerate(analysis["time_allocation"]["by_tool_wait_category_human"].items(), 1):
        pct = (analysis["time_allocation"]["by_tool_wait_category_ms"].get(cat, 0) / max(turn["duration_ms"], 1)) * 100
        lines.append(f"{i}. `{cat}`: {human} ({pct:.1f}%)")
    lines.append("")

    lines.append("## 3. Tool call categories")
    lines.append("")
    for i, (cat, count) in enumerate(tool_summary["category_counts"].items(), 1):
        elapsed = analysis["time_allocation"]["by_tool_call_elapsed_human"].get(cat, "0.0s")
        lines.append(f"{i}. `{cat}`: {count} calls, {elapsed} summed call elapsed")
    lines.append("")

    lines.append("## 4. Long calls")
    lines.append("")
    if tool_summary["long_calls"]:
        lines.append("| # | Local start | Duration | Category | Tool | Exit | Command |")
        lines.append("|---:|---|---:|---|---|---:|---|")
        for c in tool_summary["long_calls"][:80]:
            lines.append(
                f"| {c['ordinal']} | {c['start_local']} | {c['elapsed_human']} | `{c['category']}` | `{c['name']}` | {c['exit_code']} | {md_escape(c['command'])} |"
            )
    else:
        lines.append("No long calls crossed the threshold.")
    lines.append("")

    lines.append("## 5. Failure and stuck signals")
    lines.append("")
    failed = tool_summary["failed_calls"]
    lines.append(f"1. Failed/non-zero tool calls: {len(failed)}")
    for c in failed[:30]:
        lines.append(f"   - #{c['ordinal']} {c['elapsed_human']} `{c['category']}` exit={c['exit_code']}: {c['command']}")
    lines.append(f"2. Long gaps: {analysis['stuck_signals']['long_gap_count']}")
    for gap in analysis["stuck_signals"]["long_gaps"][:20]:
        lines.append(
            f"   - {fmt_dt(parse_ts(gap['start_ts']), tz)} → {fmt_dt(parse_ts(gap['end_ts']), tz)}: {fmt_ms(gap['elapsed_ms'])} as `{gap['label']}`"
        )
    lines.append(f"3. Stall-keyword agent messages: {len(analysis['stuck_signals']['stall_agent_messages'])}")
    for m in analysis["stuck_signals"]["stall_agent_messages"][:30]:
        lines.append(f"   - {m['local_time']}: {short(m['message'], 300)}")
    lines.append(f"4. Stall-keyword reasoning items: {len(analysis['stuck_signals']['stall_reasoning'])}")
    for r in analysis["stuck_signals"]["stall_reasoning"][:20]:
        lines.append(f"   - {r['local_time']}: {r['title']} — {r['text_preview']}")
    lines.append("")

    lines.append("## 6. Five-minute bins")
    lines.append("")
    lines.append("| Window | Tool calls | Categories | Agent msgs | Stall msgs | Sample visible messages |")
    lines.append("|---|---:|---|---:|---:|---|")
    for b in analysis["time_bins_5m"]:
        cats = ", ".join(f"{k}:{v}" for k, v in b["tool_categories"].items())
        samples = "<br>".join(md_escape(s) for s in b["sample_agent_messages"])
        lines.append(f"| {b['start_local']} → {b['end_local']} | {b['tool_call_count']} | {md_escape(cats)} | {b['agent_message_count']} | {b['stall_message_count']} | {samples} |")
    lines.append("")

    lines.append("## 7. All tool calls")
    lines.append("")
    lines.append("| # | Local start | Elapsed | Category | Tool | Exit | Command/input summary |")
    lines.append("|---:|---|---:|---|---|---:|---|")
    for c in analysis["tool_calls"]:
        out = c.get("output") or {}
        cmd = c.get("command") or c.get("input_preview") or ""
        elapsed = fmt_ms(c.get("elapsed_ms") or 0)
        lines.append(
            f"| {c['ordinal']} | {c.get('start_local') or ''} | {elapsed} | `{c.get('category')}` | `{c.get('name')}` | {out.get('exit_code')} | {md_escape(short(cmd, 220))} |"
        )
    lines.append("")

    lines.append("## 8. Analyst prompt handoff")
    lines.append("")
    lines.append("Use `references/deep-analysis-prompt.md` with this Markdown file plus the sibling JSON artifact. The JSON contains output previews, full call ordering, token records, and stall signals.")
    lines.append("")
    return "\n".join(lines)


def md_escape(text: Any) -> str:
    s = short(text, 300)
    return s.replace("|", "\\|").replace("\n", "<br>")


def render_prompt(analysis: dict[str, Any], json_path: Path, md_path: Path) -> str:
    turn = analysis["turn"]
    return textwrap.dedent(
        f"""
        Use $analyze-codex-turn to perform a deep time-spent analysis of Codex turn `{turn['turn_id']}`.

        Inputs:
        1. Markdown summary: `{md_path}`
        2. Structured JSON: `{json_path}`
        3. Raw session JSONL if extra proof is needed: `{analysis['session_path']}`

        Treat the script output as an evidence packet, not the final answer. Read the artifacts, then synthesize the analysis yourself. If the evidence is too coarse, run additional focused jq/python analysis against the JSON artifact or raw JSONL before concluding.

        Produce:
        1. A granular wall-clock breakdown by phase, with exact local time windows.
        2. The top places the agent got stuck, including failed retries, long waits, wrong turns, and review/verification loops.
        3. Which tool calls consumed the most time and whether they were necessary.
        4. Model-behavior critique: planning quality, over/under-verification, context compaction effects, and avoidable churn.
        5. Concrete improvement recommendations for future agents and for skill/tooling automation.

        Ground every claim in the artifacts. Call out uncertainty separately from confirmed evidence.
        """
    ).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze one turn from a raw Codex rollout JSONL thread transcript.")
    parser.add_argument("--thread-id", help="Codex thread id; resolves under $CODEX_HOME/sessions")
    parser.add_argument("--session", help="Path to rollout JSONL; overrides --thread-id")
    parser.add_argument("--turn-id", help="Specific turn id to analyze")
    parser.add_argument("--select", choices=["recent-long", "latest", "longest"], default="recent-long")
    parser.add_argument("--min-duration-min", type=float, default=60.0, help="Minimum duration for --select recent-long")
    parser.add_argument("--timezone", default=os.environ.get("TZ", "UTC"))
    parser.add_argument("--out-dir", default=".", help="Directory for generated artifacts")
    parser.add_argument("--max-output-chars", type=int, default=2000, help="Output preview chars to keep per tool call")
    parser.add_argument("--long-call-sec", type=float, default=60.0)
    parser.add_argument("--long-gap-sec", type=float, default=90.0)
    parser.add_argument("--list-turns", action="store_true", help="List detected turns and exit")
    args = parser.parse_args()

    session_path = resolve_session_path(args.thread_id, args.session)
    events = load_events(session_path)
    turns = find_turns(events)

    if args.list_turns:
        for idx, turn in enumerate(turns, 1):
            print(
                json.dumps(
                    {
                        "index": idx,
                        "turn_id": turn.turn_id,
                        "start_local": fmt_dt(turn.start_ts, args.timezone),
                        "completed_local": fmt_dt(turn.completed_ts or turn.start_ts, args.timezone),
                        "duration": fmt_ms(turn.duration_ms),
                        "user_message": short(turn.user_message, 240),
                    },
                    ensure_ascii=False,
                )
            )
        return

    turn = select_turn(turns, args.turn_id, args.select, args.min_duration_min)
    analysis = analyze_turn(
        events,
        turn,
        session_path,
        args.timezone,
        args.max_output_chars,
        args.long_call_sec * 1000,
        args.long_gap_sec * 1000,
    )

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_turn = re.sub(r"[^A-Za-z0-9_.-]+", "-", turn.turn_id)
    prefix = f"codex-turn-{safe_turn}"
    json_path = out_dir / f"{prefix}.analysis.json"
    md_path = out_dir / f"{prefix}.analysis.md"
    prompt_path = out_dir / f"{prefix}.ai-prompt.md"

    json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(analysis, args.timezone), encoding="utf-8")
    prompt_path.write_text(render_prompt(analysis, json_path, md_path), encoding="utf-8")

    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "prompt": str(prompt_path), "turn_id": turn.turn_id, "duration": analysis["turn"]["duration_human"]}, indent=2))


if __name__ == "__main__":
    main()
