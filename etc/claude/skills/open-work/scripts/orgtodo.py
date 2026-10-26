"""
Read and rewrite headlines in the user's daily TODO.

The TODO carries three pieces of machine-readable state, all of them native org
so they render cleanly in emacs:

  `[[ow:<slug>][text]]`      links a headline to a thread — the slug is the link
                             target, so only `text` is displayed
  `[#A]`-`[#D]`              priority: A=P1, B=P2, C=P3, D=parked
  `HANDED-OFF` +
  `[[ow-to:<login>][@login]]` passed to someone else. A link, not a tag: org tags
                             allow only [[:alnum:]_@#%], so a login with a hyphen
                             (bug-author, minahil-naeem) cannot be one.

Only these three are ever written. The user's own words are never touched.
"""

import re
import shutil
from pathlib import Path

KEYWORDS = ["TODO", "IN-PROGRESS", "AWAITING-REVIEW", "HANDED-OFF", "DONE", "CANCELLED"]
COOKIE_TO_PRIORITY = {"A": "P1", "B": "P2", "C": "P3", "D": "parked"}
PRIORITY_TO_COOKIE = {value: key for key, value in COOKIE_TO_PRIORITY.items()}

HEADLINE = re.compile(
    r"^(?P<stars>\*+)\s+"
    r"(?:(?P<keyword>" + "|".join(KEYWORDS) + r")\s+)?"
    r"(?:\[#(?P<cookie>[A-Z])\]\s+)?"
    r"(?P<title>.*?)"
    r"(?:\s+(?P<tags>:[A-Za-z0-9_@#%]+(?::[A-Za-z0-9_@#%]+)*:))?"
    r"\s*$"
)
OW_LINK = re.compile(r"\[\[ow:(?P<slug>[A-Za-z0-9_-]+)\](?:\[(?P<text>[^\]]*)\])?\]")
OW_TO_LINK = re.compile(r"\[\[ow-to:(?P<login>[A-Za-z0-9_.-]+)\](?:\[[^\]]*\])?\]")
LEGACY_TAG = re.compile(r"^ow_(?P<slug>[A-Za-z0-9_-]+)$")
# an @login written as an org tag, from before this used a link — always repaired away
LEGACY_HANDOFF = re.compile(r"\s*:@(?P<login>[A-Za-z0-9_.-]+):\s*")


def parse_headline(line: str):
    """
    Split one org headline into its parts, or None if the line is not a headline.
    """
    match = HEADLINE.match(line)
    if not match:
        return None
    tags = [tag for tag in (match.group("tags") or "").strip(":").split(":") if tag]
    title = match.group("title").strip()

    slug, display = None, title
    link = OW_LINK.search(title)
    if link:
        slug = link.group("slug")
        display = OW_LINK.sub(lambda hit: hit.group("text") or hit.group("slug"), title).strip()
    else:
        for tag in tags:
            legacy = LEGACY_TAG.match(tag)
            if legacy:
                slug = legacy.group("slug")

    # who it is handed to: the ow-to link, or an @login tag left by the older format
    handoff_link = OW_TO_LINK.search(display)
    handoff = handoff_link.group("login") if handoff_link else None
    display = OW_TO_LINK.sub("", display).strip()
    legacy_handoffs = LEGACY_HANDOFF.findall(display) + [
        tag[1:] for tag in tags if tag.startswith("@")
    ]
    if legacy_handoffs and not handoff:
        handoff = legacy_handoffs[0]
    display = LEGACY_HANDOFF.sub(" ", display).strip()

    return {
        "raw": line,
        "level": len(match.group("stars")),
        "keyword": match.group("keyword") or "",
        "cookie": match.group("cookie"),
        "priority": COOKIE_TO_PRIORITY.get(match.group("cookie") or ""),
        "title": display,
        "title_raw": title,
        "slug": slug,
        "linked": bool(link),
        "tags": tags,
        "handoff": handoff,
    }


def render_headline(item, slug=None, priority=None, keyword=None, handoff=None, level=None) -> str:
    """
    Rebuild a headline with the machine-readable parts updated. Anything left as
    None keeps whatever the headline already had; the displayed words never change.
    """
    stars = "*" * (level or item["level"])
    keyword = item["keyword"] if keyword is None else keyword
    slug = item["slug"] if slug is None else slug
    handoff = item["handoff"] if handoff is None else handoff

    cookie = item["cookie"]
    if priority is not None:
        cookie = PRIORITY_TO_COOKIE.get(priority)

    title = _link_title(item["title"], slug) if slug else item["title"]
    if handoff:
        title += f" [[ow-to:{handoff}][@{handoff}]]"

    tags = [tag for tag in item["tags"] if not LEGACY_TAG.match(tag) and not tag.startswith("@")]
    if slug and not OW_LINK.search(title):
        tags.append(f"ow_{slug}")  # title began with a link, so the slug rides in a tag

    parts = [stars]
    if keyword:
        parts.append(keyword)
    if cookie:
        parts.append(f"[#{cookie}]")
    parts.append(title)
    line = " ".join(parts)
    if tags:
        line += "    :" + ":".join(tags) + ":"
    return line


def _link_title(title: str, slug: str) -> str:
    """
    Wrap the headline's words in the thread link, leaving any link the user already
    wrote alone — org has no nested links, so only the plain leading text is wrapped.
    """
    existing = title.find("[[")
    if existing == -1:
        return f"[[ow:{slug}][{title}]]"
    leading, rest = title[:existing], title[existing:]
    inside = leading.rstrip(" \t([{-–—:,")
    outside = leading[len(inside):]
    if not inside:
        # nothing plain to wrap: fall back to the tag form, handled by the caller
        return title
    return f"[[ow:{slug}][{inside}]]{outside}{rest}"


def promote(path: Path, child_raw: str, parent_raw: str, promoted_line: str,
            backup_suffix: str = ".pre-ow") -> bool:
    """
    Lift a sub-item out of its parent's subtree and re-file it as a top-level item
    directly after that subtree, so the parent's remaining children stay put.
    """
    text = path.read_text()
    if child_raw not in text or parent_raw not in text:
        return False
    lines = text.splitlines(keepends=True)
    child_index = next(i for i, line in enumerate(lines) if line.rstrip("\n") == child_raw.rstrip("\n"))
    lines.pop(child_index)

    parent_index = next(i for i, line in enumerate(lines) if line.rstrip("\n") == parent_raw.rstrip("\n"))
    insert_at = len(lines)
    for index in range(parent_index + 1, len(lines)):
        if re.match(r"^\*{1,2} ", lines[index]):  # the next top-level item, or a new section
            insert_at = index
            break
    lines.insert(insert_at, promoted_line.rstrip("\n") + "\n")

    shutil.copy(path, str(path) + backup_suffix)
    path.write_text("".join(lines))
    return True


def rewrite(path: Path, changes: dict, backup_suffix: str = ".pre-ow") -> int:
    """
    Apply {original line: new line} to the file, backing it up first.

    Matching on the original line keeps this safe against the file having been
    reordered since it was parsed — a line that no longer exists is skipped.
    """
    text = path.read_text()
    applied = 0
    for original, replacement in changes.items():
        if original == replacement or original not in text:
            continue
        text = text.replace(original, replacement, 1)
        applied += 1
    if applied:
        shutil.copy(path, str(path) + backup_suffix)
        path.write_text(text)
    return applied
