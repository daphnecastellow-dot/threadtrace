#!/usr/bin/env python3
"""Threadtrace: tiny provenance trails for evolving claims.

Standard-library only. Records are plain JSON and meant to remain inspectable.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

FORMAT = "threadtrace/0.1"
STATUSES = ("documented", "inference", "unresolved", "rejected")


class ThreadtraceError(Exception):
    pass


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ThreadtraceError(f"trail not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ThreadtraceError(f"invalid JSON in {p}: {exc}") from exc
    validate(data)
    return data


def save(path: str | Path, data: dict[str, Any]) -> None:
    validate(data)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ThreadtraceError("trail must be a JSON object")
    if data.get("format") != FORMAT:
        raise ThreadtraceError(f"unsupported format: {data.get('format')!r}")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ThreadtraceError("trail requires a non-empty title")
    if not isinstance(data.get("items"), list):
        raise ThreadtraceError("trail requires an items list")

    seen = set()
    for item in data["items"]:
        if not isinstance(item, dict):
            raise ThreadtraceError("each item must be an object")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ThreadtraceError("each item requires an id")
        if item_id in seen:
            raise ThreadtraceError(f"duplicate item id: {item_id}")
        seen.add(item_id)
        if item.get("status") not in STATUSES:
            raise ThreadtraceError(f"{item_id}: invalid status {item.get('status')!r}")
        if not isinstance(item.get("claim"), str) or not item["claim"].strip():
            raise ThreadtraceError(f"{item_id}: claim must be non-empty")
        if not isinstance(item.get("sources", []), list):
            raise ThreadtraceError(f"{item_id}: sources must be a list")
        if not isinstance(item.get("history"), list) or not item["history"]:
            raise ThreadtraceError(f"{item_id}: history must be a non-empty list")


def new_trail(title: str) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "title": title.strip(),
        "created_at": now_utc(),
        "items": [],
    }


def next_id(data: dict[str, Any]) -> str:
    max_num = 0
    for item in data["items"]:
        item_id = item.get("id", "")
        if item_id.startswith("T") and item_id[1:].isdigit():
            max_num = max(max_num, int(item_id[1:]))
    return f"T{max_num + 1:03d}"


def add_item(
    data: dict[str, Any],
    claim: str,
    status: str,
    source: str | None = None,
    source_url: str | None = None,
    note: str | None = None,
) -> str:
    if status not in STATUSES:
        raise ThreadtraceError(f"invalid status: {status}")
    claim = claim.strip()
    if not claim:
        raise ThreadtraceError("claim cannot be empty")

    item_id = next_id(data)
    sources = []
    if source:
        src = {"label": source}
        if source_url:
            src["url"] = source_url
        sources.append(src)

    ts = now_utc()
    item = {
        "id": item_id,
        "claim": claim,
        "status": status,
        "sources": sources,
        "note": note or "",
        "history": [
            {
                "at": ts,
                "action": "created",
                "claim": claim,
                "status": status,
                "reason": note or "",
            }
        ],
    }
    data["items"].append(item)
    return item_id


def find_item(data: dict[str, Any], item_id: str) -> dict[str, Any]:
    for item in data["items"]:
        if item["id"] == item_id:
            return item
    raise ThreadtraceError(f"item not found: {item_id}")


def revise_item(
    data: dict[str, Any],
    item_id: str,
    claim: str,
    reason: str,
    status: str | None = None,
) -> None:
    item = find_item(data, item_id)
    claim = claim.strip()
    reason = reason.strip()
    if not claim:
        raise ThreadtraceError("revised claim cannot be empty")
    if not reason:
        raise ThreadtraceError("revision requires a reason")
    new_status = status or item["status"]
    if new_status not in STATUSES:
        raise ThreadtraceError(f"invalid status: {new_status}")

    item["history"].append(
        {
            "at": now_utc(),
            "action": "revised",
            "claim": claim,
            "status": new_status,
            "reason": reason,
            "previous_claim": item["claim"],
            "previous_status": item["status"],
        }
    )
    item["claim"] = claim
    item["status"] = new_status


def change_status(data: dict[str, Any], item_id: str, status: str, reason: str) -> None:
    item = find_item(data, item_id)
    if status not in STATUSES:
        raise ThreadtraceError(f"invalid status: {status}")
    reason = reason.strip()
    if not reason:
        raise ThreadtraceError("status change requires a reason")
    item["history"].append(
        {
            "at": now_utc(),
            "action": "status",
            "claim": item["claim"],
            "status": status,
            "reason": reason,
            "previous_status": item["status"],
        }
    )
    item["status"] = status


def add_source(
    data: dict[str, Any],
    item_id: str,
    label: str,
    url: str | None = None,
    reason: str | None = None,
) -> None:
    item = find_item(data, item_id)
    src = {"label": label.strip()}
    if not src["label"]:
        raise ThreadtraceError("source label cannot be empty")
    if url:
        src["url"] = url
    item["sources"].append(src)
    item["history"].append(
        {
            "at": now_utc(),
            "action": "source-added",
            "claim": item["claim"],
            "status": item["status"],
            "reason": reason or f"Added source: {src['label']}",
        }
    )


def render_markdown(data: dict[str, Any], item_id: str | None = None) -> str:
    items = [find_item(data, item_id)] if item_id else data["items"]
    lines = [f"# {data['title']}", "", f"_Threadtrace format: `{data['format']}`_", ""]
    if not items:
        lines.append("_No items yet._")
        return "\n".join(lines) + "\n"

    for item in items:
        lines += [
            f"## {item['id']} · {item['status']}",
            "",
            item["claim"],
            "",
        ]
        if item.get("note"):
            lines += [f"**Note:** {item['note']}", ""]
        if item.get("sources"):
            lines += ["### Sources", ""]
            for src in item["sources"]:
                if src.get("url"):
                    lines.append(f"- [{src['label']}]({src['url']})")
                else:
                    lines.append(f"- {src['label']}")
            lines.append("")
        lines += ["### Trail", ""]
        for h in item["history"]:
            reason = h.get("reason") or ""
            lines.append(f"- **{h['at']} · {h['action']} · {h['status']}**")
            lines.append(f"  - Claim: {h['claim']}")
            if reason:
                lines.append(f"  - Why: {reason}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def summary(data: dict[str, Any], item_id: str | None = None) -> str:
    if item_id:
        item = find_item(data, item_id)
        return f"{item['id']} [{item['status']}] {item['claim']}"
    if not data["items"]:
        return f"{data['title']}: 0 items"
    rows = [f"{data['title']}: {len(data['items'])} item(s)"]
    rows += [f"{x['id']} [{x['status']}] {x['claim']}" for x in data["items"]]
    return "\n".join(rows)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="threadtrace",
        description="Keep the transformation trail of evolving claims.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    n = sub.add_parser("new", help="create a new trail")
    n.add_argument("file")
    n.add_argument("--title", required=True)

    a = sub.add_parser("add", help="add a claim")
    a.add_argument("file")
    a.add_argument("claim")
    a.add_argument("--status", choices=STATUSES, default="unresolved")
    a.add_argument("--source")
    a.add_argument("--source-url")
    a.add_argument("--note")

    r = sub.add_parser("revise", help="revise a claim while preserving the previous state")
    r.add_argument("file")
    r.add_argument("id")
    r.add_argument("claim")
    r.add_argument("--reason", required=True)
    r.add_argument("--status", choices=STATUSES)

    s = sub.add_parser("status", help="change a claim's status")
    s.add_argument("file")
    s.add_argument("id")
    s.add_argument("status", choices=STATUSES)
    s.add_argument("--reason", required=True)

    src = sub.add_parser("source", help="attach a source to a claim")
    src.add_argument("file")
    src.add_argument("id")
    src.add_argument("label")
    src.add_argument("--url")
    src.add_argument("--reason")

    show = sub.add_parser("show", help="show current claim state")
    show.add_argument("file")
    show.add_argument("--id")

    render = sub.add_parser("render", help="render a trail as Markdown")
    render.add_argument("file")
    render.add_argument("--id")
    render.add_argument("-o", "--output")

    check = sub.add_parser("check", help="validate a trail file")
    check.add_argument("file")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "new":
            p = Path(args.file)
            if p.exists():
                raise ThreadtraceError(f"refusing to overwrite existing file: {p}")
            save(p, new_trail(args.title))
            print(f"created {p}")
            return 0

        data = load(args.file)

        if args.command == "add":
            item_id = add_item(data, args.claim, args.status, args.source, args.source_url, args.note)
            save(args.file, data)
            print(item_id)
        elif args.command == "revise":
            revise_item(data, args.id, args.claim, args.reason, args.status)
            save(args.file, data)
            print(args.id)
        elif args.command == "status":
            change_status(data, args.id, args.status, args.reason)
            save(args.file, data)
            print(args.id)
        elif args.command == "source":
            add_source(data, args.id, args.label, args.url, args.reason)
            save(args.file, data)
            print(args.id)
        elif args.command == "show":
            print(summary(data, args.id))
        elif args.command == "render":
            text_out = render_markdown(data, args.id)
            if args.output:
                Path(args.output).write_text(text_out, encoding="utf-8")
                print(args.output)
            else:
                print(text_out, end="")
        elif args.command == "check":
            print(f"ok: {args.file} ({len(data['items'])} item(s))")
        return 0
    except ThreadtraceError as exc:
        print(f"threadtrace: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
