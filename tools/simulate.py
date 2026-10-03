#!/usr/bin/env python3
"""Render the board at true 296x128 using the same TTFs the GFX fonts came from.

Faster than a flash-and-photograph cycle, and faithful enough to catch the
thing that actually bites: text running into the column to its right.
"""

from PIL import Image, ImageDraw, ImageFont

W, H, SCALE = 296, 128, 4
PAPER, INK, RED = (0xD9, 0xD7, 0xD1), (0x23, 0x23, 0x26), (0xB2, 0x39, 0x2C)

PAD, TOP, ROW_H = 6, 2, 23
KEY_BASE, LINE2_TOP, FOOT_TOP = 11, 13, 119
NUM_W = 24                       # width of "N) " in the mono face
KEY_X = PAD + NUM_W              # ticket key, and what line 2 indents to
PAGE_SIZE = 5

mono = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14, index=1)
sans = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14, index=1)
# stand-in for Adafruit's built-in 5x7: what matters is the fixed 6px advance
tiny = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 9, index=0)
TINY_ADV = 6

ROWS = [
    ("PROJ-4821", "Code Review",          "frontend", "#2410  changes requested", "changes"),
    ("PROJ-4790", "Waiting to be Merged", "frontend", "#2387  ready to merge",    "ready"),
    ("PROJ-4815", "In Progress",          "frontend", "#2402  code review",       "review"),
    (None,        "no ticket",            "frontend", "#2415  code review",       "review"),
    ("PROJ-4766", "Code Review",          "promo",    "#1192  code review",         "review"),
    ("PROJ-4302", "Ready for QA",         "ui",       "no pull request",           "none"),
    ("PROJ-4588", "Testing",              "frontend", "#2301  code review",       "review"),
    ("PROJ-4801", "In Progress",          "ui",       "no pull request",           "none"),
]
PAGE = int(__import__('sys').argv[1]) if len(__import__('sys').argv) > 1 else 0

ICONS = {
    "review":  ["..#####..", ".#.....#.", "#.......#", "#.......#", "#.......#",
                "#.......#", "#.......#", ".#.....#.", "..#####.."],
    "changes": ["..#####..", ".#######.", "#########", "#########", "#.......#",
                "#########", "#########", ".#######.", "..#####.."],
    "ready":   [".......##", "......###", ".....###.", "#...###..", "##.###...",
                "#####....", ".###.....", "..#......", "........."],
    "none":    [".........", ".........", ".........", "#########", "#########",
                ".........", ".........", ".........", "........."],
}
ICON_RED = {"changes", "ready"}

img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)


def tiny_w(s):
    return len(s) * TINY_ADV


def tiny_text(s, x, y, colour):
    for i, ch in enumerate(s):                       # fixed pitch, like the real font
        d.text((x + i * TINY_ADV, y - 1), ch, font=tiny, fill=colour)


page_rows = ROWS[PAGE * PAGE_SIZE:(PAGE + 1) * PAGE_SIZE]

for i, (key, status, repo, prline, state) in enumerate(page_rows):
    top = TOP + i * ROW_H
    n = PAGE * PAGE_SIZE + i + 1

    d.text((PAD, top + KEY_BASE), f"{n})", font=mono, fill=INK, anchor="ls")
    k = key or "-"
    d.text((KEY_X, top + KEY_BASE), k, font=mono, fill=INK, anchor="ls")
    kw = int(mono.getlength(k))
    d.text((KEY_X + kw + 8, top + KEY_BASE), status, font=sans, fill=INK, anchor="ls")

    colour = RED if state in ICON_RED else INK
    for r, line in enumerate(ICONS[state]):
        for c, ch in enumerate(line):
            if ch == "#":
                img.putpixel((KEY_X + c, top + LINE2_TOP + r), colour)

    repo_x = W - PAD - tiny_w(repo)
    line_x = KEY_X + 14
    budget = repo_x - line_x - 10
    text = prline
    while text and tiny_w(text) > budget:
        text = text[:-1]
    tiny_text(text, line_x, top + LINE2_TOP, colour)
    tiny_text(repo, repo_x, top + LINE2_TOP, INK)

lo = PAGE * PAGE_SIZE + 1
hi = min(lo + PAGE_SIZE - 1, len(ROWS))
pages = (len(ROWS) + PAGE_SIZE - 1) // PAGE_SIZE
tiny_text(f"{lo}-{hi} of {len(ROWS)}   page {PAGE+1}/{pages}", PAD, FOOT_TOP, INK)
tiny_text("updated 3m", W - PAD - tiny_w("updated 3m"), FOOT_TOP, INK)

img.resize((W * SCALE, H * SCALE), Image.NEAREST).save(f"tools/sim{PAGE+1}.png")
print(f"wrote tools/sim{PAGE+1}.png")
print(f"widest row: {KEY_X + int(mono.getlength('PROJ-4790')) + 8 + int(sans.getlength('Waiting to be Merged'))}px of {W}")
