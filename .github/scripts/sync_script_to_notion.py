"""Sync presentation/script/presenter-script.md to the team's Notion page.

One-way: the markdown file in this repo is the source of truth. On each run the
Notion page's content is replaced with blocks generated from the markdown.

Conventions (see the header comment in presenter-script.md):
  ## heading           -> heading_2, colored by the speaker named in it
  ---                  -> divider
  STAGE:/KEY:/NOTE: p  -> gray callout (stage directions / keys / notes)
  KAYVON:/MIA:/FINN:/NATHANAEL:/OM: paragraph -> colored callout for that speaker
  anything else        -> plain paragraph
  **bold** supported everywhere.

Env vars: NOTION_TOKEN (integration secret), NOTION_PAGE_ID.
"""
import json
import os
import re
import sys
import time
import urllib.request

TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ.get("NOTION_PAGE_ID", "c1d1e1bfcf2e40ec9bbcf8aacd7abbbe")
MD_PATH = os.environ.get(
    "SCRIPT_MD", "presentation/script/presenter-script.md")

API = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

SPEAKERS = {
    "KAYVON": ("blue_background", "\U0001F535"),      # blue circle
    "MIA": ("purple_background", "\U0001F7E3"),       # purple circle
    "FINN": ("green_background", "\U0001F7E2"),       # green circle
    "NATHANAEL": ("orange_background", "\U0001F7E0"), # orange circle
    "OM": ("yellow_background", "\U0001F7E1"),        # yellow circle
}
GRAY_ICONS = {"STAGE": "\U0001F3AC", "KEY": "\U0001F3A8", "NOTE": "\U0001F5E3"}


def request(method, path, body=None, retries=4):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(
            API + path, data=data, headers=HEADERS, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:400]
            if e.code in (409, 429, 502, 503) and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise SystemExit(f"Notion API {e.code} on {method} {path}: {detail}")
    raise SystemExit("unreachable")


def rich(text, max_len=1900):
    """Markdown-ish text -> Notion rich_text array, honoring **bold**."""
    spans = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not part:
            continue
        bold = i % 2 == 1
        for j in range(0, len(part), max_len):
            spans.append({
                "type": "text",
                "text": {"content": part[j:j + max_len]},
                "annotations": {"bold": bold},
            })
    return spans or [{"type": "text", "text": {"content": ""}}]


def heading_color(title):
    up = title.upper()
    for name, (color, _) in SPEAKERS.items():
        if name in up:
            return color
    return "default"


def parse(md):
    blocks = []
    # strip HTML comments and the top-level title line
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    paragraphs, buff = [], []
    for line in md.splitlines():
        if line.startswith("## ") or line.strip() == "---":
            if buff:
                paragraphs.append("\n".join(buff))
                buff = []
            paragraphs.append(line.strip())
        elif line.strip() == "":
            if buff:
                paragraphs.append("\n".join(buff))
                buff = []
        elif line.startswith("# "):
            continue
        else:
            buff.append(line)
    if buff:
        paragraphs.append("\n".join(buff))

    for p in paragraphs:
        if p == "---":
            blocks.append({"type": "divider", "divider": {}})
            continue
        if p.startswith("## "):
            title = p[3:].strip()
            blocks.append({
                "type": "heading_2",
                "heading_2": {"rich_text": rich(title),
                              "color": heading_color(title)},
            })
            continue
        m = re.match(r"^([A-Z]+):\s*(.*)$", p, flags=re.S)
        tag = m.group(1) if m else None
        if tag in GRAY_ICONS:
            body = m.group(2)
            blocks.append({
                "type": "callout",
                "callout": {"rich_text": rich(body), "color": "gray_background",
                            "icon": {"type": "emoji",
                                     "emoji": GRAY_ICONS[tag]}},
            })
        elif tag in SPEAKERS:
            color, icon = SPEAKERS[tag]
            body = f"**{tag}**\n" + m.group(2)
            blocks.append({
                "type": "callout",
                "callout": {"rich_text": rich(body), "color": color,
                            "icon": {"type": "emoji", "emoji": icon}},
            })
        else:
            blocks.append({"type": "paragraph",
                           "paragraph": {"rich_text": rich(p)}})
    return blocks


def main():
    md = open(MD_PATH, encoding="utf-8").read()
    new_blocks = parse(md)
    print(f"parsed {len(new_blocks)} blocks from {MD_PATH}")

    # delete existing page content
    deleted, cursor = 0, None
    while True:
        q = f"/blocks/{PAGE_ID}/children?page_size=100"
        if cursor:
            q += f"&start_cursor={cursor}"
        page = request("GET", q)
        for child in page.get("results", []):
            request("DELETE", f"/blocks/{child['id']}")
            deleted += 1
        if not page.get("has_more"):
            break
        cursor = page.get("next_cursor")
    print(f"deleted {deleted} existing blocks")

    # append new content in chunks of 90
    for i in range(0, len(new_blocks), 90):
        request("PATCH", f"/blocks/{PAGE_ID}/children",
                {"children": new_blocks[i:i + 90]})
    print(f"appended {len(new_blocks)} blocks; sync complete")


if __name__ == "__main__":
    sys.exit(main())
