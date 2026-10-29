"""
Shared access to OPEN_WORK.md: parse the hand-maintained thread blocks, and write
them back without disturbing anything else in the file.

A thread heading is `### <slug> · <Title>`; the slug is the stable identity, used
as the `[[ow:<slug>][...]]` link target in the TODO and as the key for board decisions.

Writes are surgical: a block is re-rendered only where a field actually changed, so
prose, code fences and sub-bullets under a field survive a round trip untouched.
"""

import os
import re
from pathlib import Path

HERE = Path(os.environ.get("OPEN_WORK_DATA", Path.home() / "src/abyss/.open-work"))  # data, not code
TRACKER = HERE.parent / "OPEN_WORK.md"

BEGIN_PRS = "<!-- BEGIN GENERATED: pull requests — regenerate with .open-work/build.py, do not hand-edit -->"
END_PRS = "<!-- END GENERATED -->"

STATUS_ORDER = ["blocked", "active", "review", "resolved", "flagged", "backlog", "done"]
PRIORITIES = ["P1", "P2", "P3", "parked"]
FIELD_ORDER = ["status", "priority", "parent", "todo", "repos", "waiting on", "next", "links",
               "updated", "reviewed"]
FIELD_LABELS = {"todo": "TODO", "waiting on": "Waiting on"}
FIELD_RE = re.compile(r"^- \*\*([^:]+):\*\*\s*(.*)$")


def parse_threads(markdown: str) -> list:
    """
    Pull every `### slug · Title` block out of the threads section.
    """
    threads = []
    section = markdown.split("## Threads", 1)[-1].split(BEGIN_PRS, 1)[0]
    for block in re.split(r"^### ", section, flags=re.M)[1:]:
        lines = block.splitlines()
        heading = lines[0].strip()
        fields, body, last_field, in_fields = {}, [], None, True
        # `fields` joins continuation lines into one string, which every script relies on;
        # `field_lines` keeps them apart so the board can render nested bullets
        field_lines, updates = {}, []
        for line in lines[1:]:
            match = re.match(r"^- \*\*([^:]+):\*\*\s*(.*)$", line)
            if match:
                last_field = match.group(1).strip().lower()
                fields[last_field] = match.group(2).strip()
                field_lines[last_field] = [match.group(2).strip()]
                if last_field == "updated":
                    updates.append(field_lines[last_field])
                in_fields = True
            elif in_fields and last_field and line.startswith("  ") and line.strip():
                fields[last_field] += " " + line.strip()
                field_lines[last_field].append(line[2:].rstrip())
            elif line.strip().startswith("---"):
                in_fields = False
            elif line.strip():
                in_fields = False
                body.append(line.strip())
            elif body:
                body.append("")
        slug, _, title = heading.partition(" · ")
        threads.append({
            "slug": slug.strip(),
            "title": title.strip() or heading,
            "fields": fields,
            "field_lines": field_lines,
            # every Updated: line, newest first as written; `fields` keeps only the last
            "updates": updates,
            "paragraphs": [p.strip() for p in " \n".join(body).split("\n \n") if p.strip()],
            # the block exactly as written, and the fields as they read then, so a write
            # can tell what actually changed and leave the rest of the text alone
            "raw": re.sub(r"\n-{3,}$", "", ("### " + block).rstrip()).rstrip(),
            "was": dict(fields),
        })
    return threads


def priority_rank(thread) -> int:
    priority = thread["fields"].get("priority", "P3").split()[0]
    return PRIORITIES.index(priority) if priority in PRIORITIES else 2


def status_rank(thread) -> int:
    status = thread["fields"].get("status", "backlog")
    return STATUS_ORDER.index(status) if status in STATUS_ORDER else 99


def sort_threads(threads: list) -> list:
    """
    Priority first — that is what the user asked to see — then how blocked it is.
    """
    return sorted(threads, key=lambda thread: (priority_rank(thread), status_rank(thread), thread["slug"]))


def field_spans(lines: list) -> list:
    """
    Where each field sits in a block: (field, label, start, end), end exclusive and
    covering the field's continuation lines.
    """
    spans, field, label, start, last = [], None, None, None, None
    for index, line in enumerate(lines):
        match = FIELD_RE.match(line)
        if match:
            if field:
                spans.append((field, label, start, last + 1))
            label = match.group(1).strip()
            field, start, last = label.lower(), index, index
        elif field and line.startswith("  ") and line.strip():
            last = index
        elif line.strip():
            spans.append((field, label, start, last + 1)) if field else None
            field = None
    if field:
        spans.append((field, label, start, last + 1))
    return spans


def field_line(field: str, value: str, label: str = None) -> str:
    return f"- **{label or FIELD_LABELS.get(field, field.title())}:** {value}"


def patch_block(thread) -> str:
    """
    Re-render only the fields that changed since the block was parsed.

    Field values arrive from the parser with their continuation lines joined, so a
    field nobody touched compares equal and keeps its original lines — which is the
    whole point: `Next:` blocks carry code fences and nested bullets, and rebuilding
    them from the joined value would flatten the lot.
    """
    lines = thread["raw"].splitlines()
    spans = field_spans(lines)
    changed = {field for field in set(thread["fields"]) | set(thread["was"])
               if thread["fields"].get(field) != thread["was"].get(field)}
    if not changed:
        return thread["raw"]

    # rewrite or drop the fields that were already in the block, bottom-up so earlier
    # spans keep their indices
    present = {}
    for field, label, start, end in spans:
        present[field] = (label, start, end)
    for field, label, start, end in sorted(spans, key=lambda span: -span[2]):
        if field not in changed:
            continue
        value = thread["fields"].get(field)
        lines[start:end] = [field_line(field=field, value=value, label=label)] if value else []

    # insert the fields the block did not have, each after the last field that precedes
    # it in FIELD_ORDER, so a new `Reviewed:` lands next to `Updated:` rather than last
    for field in changed:
        value = thread["fields"].get(field)
        if not value or field in present:
            continue
        order = FIELD_ORDER.index(field) if field in FIELD_ORDER else len(FIELD_ORDER)
        after, spans = None, field_spans(lines)
        for other, _, start, end in spans:
            rank = FIELD_ORDER.index(other) if other in FIELD_ORDER else len(FIELD_ORDER)
            if rank <= order:
                after = end
        lines.insert(after if after is not None else 1, field_line(field=field, value=value))
    return "\n".join(lines)


def render_thread(thread) -> str:
    """
    A thread read from the file keeps its own text; one built in memory is rendered.
    """
    if thread.get("raw"):
        return patch_block(thread)
    lines = [f"### {thread['slug']} · {thread['title']}"]
    for field in FIELD_ORDER:
        if thread["fields"].get(field):
            lines.append(field_line(field=field, value=thread["fields"][field]))
    for field, value in thread["fields"].items():
        if field not in FIELD_ORDER and value:
            lines.append(field_line(field=field, value=value))
    for paragraph in thread["paragraphs"]:
        lines.append("")
        lines.append(paragraph)
    return "\n".join(lines)


def write_threads(threads: list, text: str = None) -> None:
    """
    Replace the whole threads section with these threads, in sorted order.
    """
    text = TRACKER.read_text() if text is None else text
    head, _, rest = text.partition("## Threads")
    preamble, _, _ = rest.partition("### ")
    tail = rest[rest.index(BEGIN_PRS):]
    body = "\n\n".join(render_thread(thread) for thread in sort_threads(threads))
    TRACKER.write_text(f"{head}## Threads{preamble}{body}\n\n---\n\n{tail}")
