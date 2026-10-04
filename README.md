# Threadtrace

**Version:** 0.1  
**Status:** experimental

Threadtrace is a tiny provenance tool for claims that change.

Most note systems preserve the current sentence. Git preserves text changes. Threadtrace preserves a different thing: **what a claim was, how it changed, why it changed, what sources were attached, and which uncertainty survived the revision.**

It is meant for research notes, source investigations, historical claims, journalism, technical decisions, and any other work where a conclusion without its transformation trail is incomplete.

## The problem

A claim often mutates like this:

```text
plausible → repeated → simplified → stated as fact
```

By the end, the wording may survive while the reason for confidence has vanished.

Threadtrace keeps the road.

## What it records

Each tracked item has:

- a stable ID
- a current claim
- a current status
- attached sources
- optional notes
- an append-only history of meaningful changes
- reasons for revisions and status changes

Current statuses are deliberately small:

- `documented`
- `inference`
- `unresolved`
- `rejected`

Threadtrace is **not** a truth engine. It does not decide whether a claim is correct. It preserves the trail by which a human or research process changed its treatment of the claim.

## Zero dependencies

Threadtrace v0.1 is a single Python file and uses only the standard library.

Python 3.10+ is recommended.

## Quick start

```bash
python threadtrace.py new trail.json --title "Lighthouse notes"

python threadtrace.py add trail.json \
  "The keepers left because of a storm." \
  --status inference \
  --source "Investigator's report"

python threadtrace.py revise trail.json T001 \
  "Severe weather is one plausible explanation for the disappearance." \
  --status unresolved \
  --reason "The source supports dangerous conditions, not a confirmed cause."

python threadtrace.py source trail.json T001 \
  "Contemporary weather record" \
  --url "https://example.com/source"

python threadtrace.py render trail.json -o trail.md
```

The resulting JSON remains readable without Threadtrace, and the Markdown rendering is suitable for notes, repositories, or publication.

## Commands

```text
threadtrace new FILE --title TITLE
threadtrace add FILE CLAIM [--status STATUS] [--source LABEL] [--source-url URL] [--note NOTE]
threadtrace revise FILE ID CLAIM --reason REASON [--status STATUS]
threadtrace status FILE ID STATUS --reason REASON
threadtrace source FILE ID LABEL [--url URL] [--reason REASON]
threadtrace show FILE [--id ID]
threadtrace render FILE [--id ID] [-o OUTPUT]
threadtrace check FILE
```

## Design principles

### Preserve the previous state

A revision does not overwrite the trail. The current claim changes, but the previous claim remains in history.

### Require reasons for meaningful changes

Revisions and status changes require a reason. Threadtrace is interested in *why* confidence or wording moved.

### Keep claim and interpretation separate

A source can be attached without pretending that the source itself makes a specific inference true.

### Keep unresolved visible

`unresolved` is a first-class state, not an error condition.

### Stay inspectable

The storage format is ordinary JSON. There is no database and no hidden service.

## Example

See [`examples/demo.json`](examples/demo.json) and its rendered companion [`examples/demo.md`](examples/demo.md).

## Tests

```bash
python -m unittest discover -s tests -v
```

## License and reuse

**No reuse license has been granted.**

This public build is available for inspection and development of the project by its maintainers. Do not assume that public visibility grants permission to copy, redistribute, modify, sell, incorporate, or relicense the code or documentation.

See [`COPYRIGHT.md`](COPYRIGHT.md).

## Why the name?

A final conclusion is a point.

A thread is the sequence that made the point intelligible.

Threadtrace keeps the thread.
