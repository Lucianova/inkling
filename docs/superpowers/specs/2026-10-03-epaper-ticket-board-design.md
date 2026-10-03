# E-paper ticket board — design

**Date:** 2026-10-03
**Status:** hardware phase complete and measured; software phase not started

A small always-on desk display showing the JIRA tickets assigned to you and the
state of the pull request attached to each one. It answers one question from
across the desk — *what is waiting on me* — without opening a browser tab.

---

## 1. Hardware

All figures below are **measured on the device**, not estimated.

| | |
|---|---|
| Panel | Waveshare 2.9″ (B), 296×128, black / white / **red** |
| Driver class | `GxEPD2_290_Z13c` (GDEH029Z13) — confirmed working |
| Controller | ESP32 DevKit v1, WROOM-32 (160 MHz-rated variant) |
| Full refresh | **17.78 s**, identical across every run |
| Partial refresh | **not supported** — tri-colour panels have no fast waveform |
| RAM | 9.5 % (31 KB of 328 KB), including both framebuffers |
| Flash | 22.3 % (292 KB of 1.3 MB) |

### Wiring

| Display | ESP32 |
|---|---|
| BUSY | GPIO 4 |
| RST | GPIO 16 |
| DC | GPIO 17 |
| CS | GPIO 5 |
| CLK | GPIO 18 |
| DIN | GPIO 23 |
| VCC | 3V3 |
| GND | GND |

| Other | |
|---|---|
| Button | GPIO 27 ↔ GPIO 26 |
| LED | GPIO 2 (onboard) |

GPIO 26 is driven permanently `LOW` and acts as the button's ground, so no GND
header is needed. A tactile switch draws microamps through the internal pull-up,
far below what a GPIO can sink.

### The constraint that shapes everything

A 17.78-second full refresh with black/white/red flashing is the single fact
this design is built around. Three rules follow, and none of them are optional:

1. **Repaint only when the data actually changes.** Poll, diff against what is
   on screen, and do nothing if nothing moved. On a quiet afternoon the panel
   never flashes once.
2. **Never repaint on a timer.** A timer repaints to say nothing new, which
   turns a slow display into a blinking one.
3. **Acknowledge input out of band.** Any input needs confirmation faster than
   the display can give it — see §5.

---

## 2. Screens

Three, reached three different ways. The distinction matters: one is the
default, one is driven by data, one is summoned by the user.

### Board — the default

Five items, two rows each.

```
1) PROJ-4821  Code Review
   ⊖ #2410  changes requested              frontend
2) PROJ-4790  Waiting to be Merged
   ✓ #2387  ready to merge                 frontend
3) PROJ-4815  In Progress
   ○ #2402  code review                    frontend
4) —  no ticket
   ○ #2415  code review                    frontend
5) PROJ-4302  Ready for QA
   –  no pull request                             ui
1-5 of 8   page 1/2                        updated 3m
```

Line 1 is `N)` + ticket key + JIRA status. Line 2 indents to the key column and
carries the PR state icon, the PR number and its state, with the repo
right-aligned. Numbering continues across pages.

### ALL CLEAR — data-driven

The GitHub Octocat and "nothing waiting on you", shown when the poller reports
zero items. Not reachable by button; it has to mean something.

### Off duty — user-summoned

A rotating phrase, second line in red. Summoned by holding the button, for when
there may well be plenty waiting and you do not want to know. Deliberately
*not* the Octocat — "there is nothing" and "I don't want to see it" are
different statements and get different art.

---

## 3. Data

### Sources, and why both are needed

**JIRA owns the ticket → PR mapping.** The dev-panel endpoint returns linked
PRs per issue, including PRs you did not author. Verified against PROJ-4815,
which returned three.

**GitHub owns the PR state.** JIRA's PR status field only reports
`OPEN` / `MERGED` / `DECLINED`, and its `approved` boolean cannot distinguish a
reviewer who *requested changes* from one who *has not looked yet* — three of
the five states below collapse into one. `gh`'s `reviewDecision` gives exactly
what is needed.

| Displayed state | Source |
|---|---|
| code review | `gh` · `reviewDecision = REVIEW_REQUIRED` |
| changes requested | `gh` · `reviewDecision = CHANGES_REQUESTED` |
| ready to merge | `gh` · approved + mergeable + checks green |
| merged | either |
| closed | either |
| no pull request | absence of a link |

PRs with no ticket reference are included as their own rows, found by querying
your authored open PRs and subtracting those already matched.

### Status allowlist — two tiers

Names taken from the project's own transition list. **"Ready for Release" does not
exist**; the status meaning *passed QA, now mergeable* is called
**Waiting to be Merged**.

| Tier | Statuses | Behaviour |
|---|---|---|
| **Primary** | In Progress, Code Review, Waiting to be Merged | always drawn first |
| **Secondary** | Testing, Ready for QA | fills leftover rows only |
| Excluded | everything else | dropped before layout |

Loose PRs count as primary — a PR with no ticket still needs you, so it must not
be pushed below something parked with QA.

### Sorting

Within a tier, by what needs you:

```
changes requested → ready to merge → code review → no PR → merged → closed
```

This is what decides **what survives truncation**, which is the real reason it
matters. Red rows float to the top; by construction later pages are
black-and-white.

### One PR per ticket

The most recently updated. One ticket genuinely had three linked PRs, two of them
superseded bot PRs — showing them all would spend three of five rows on noise.

---

## 4. Colour

Red is used in exactly three places and nowhere else:

- the **mascot** on the ALL CLEAR screen (closer to the real artwork than black)
- the **actionable PR states** — changes requested, ready to merge
- the **second line** of an off-duty phrase

Black means waiting on someone else, or finished. A third colour is easy to
squander.

---

## 5. Button

One button, two gestures, measured on release.

| | Duration | Action |
|---|---|---|
| bounce | < 40 ms | ignored |
| tap | 40–800 ms | next page |
| hold | ≥ 800 ms | toggle off duty |

| | Tap | Hold |
|---|---|---|
| Board | next page (wraps) | → off duty, next phrase |
| Off duty | *nothing* | → board, **page 1** |

**Polled with a 20 ms stable-sample debounce, not an interrupt.** A `CHANGE` ISR
must `digitalRead()` to learn which edge fired, and on a bouncing contact that
read can land after the pin has flipped back — releases get swallowed and taps go
missing. Presses during a redraw are discarded by design, which was the only
thing the interrupt was buying.

### LED acknowledgement

| LED | Meaning |
|---|---|
| solid | heard you — redrawing |
| off | settled and readable |
| two blinks | heard you, deliberately doing nothing |

Without this, a press is indistinguishable from a dead button for 17.78 seconds,
which is exactly what makes people press again. The same reasoning should apply
to the WiFi path: a flash on "data received" makes the device debuggable from
across the room.

### Why no auto-paging

Rejected deliberately. A timer-driven flip costs a 17.78 s flash to show content
you did not ask for, breaks the repaint-on-change rule, and leaves you unable to
choose which page you see. On-demand paging keeps all three.

---

## 6. Architecture

```
JIRA ──┐
       ├──► poller (Mac, launchd) ──► HTTP ──► ESP32 ──► panel
gh ────┘
```

**The ESP32 stays dumb.** It receives a rendered item list and draws it. It does
not know what JIRA is, what a PR is, or what time it is.

**The poller lives on the Mac**, as a launchd agent with `RunAtLoad` plus an
interval so it starts at login and survives a reboot. It holds the credentials,
does the JIRA/`gh` joining, applies the allowlist and sort, diffs against the
last snapshot, and pushes only when something changed.

That split means changing a status name, a sort rule or a phrase is editing a
script — not reflashing firmware.

**The previous snapshot is persisted to disk**, which is what makes transition
detection possible at all; a transition is a difference between two polls, not a
state you can read.

**Staleness must be visible.** The footer carries `updated Nm`, red past 20
minutes. If the script dies, the network drops or the Atlassian token expires,
the panel keeps showing the last good board indefinitely, and that counter is the
only thing that would tell you.

### Accounts

The work GitHub account, scoped to the employer org.
`gh` authenticates one account at a time; personal repos are out of scope.

---

## 7. Fonts

Adafruit ships `Free*` at 9/12/18/24 pt only, and 9 pt proved too heavy for a
128 px-tall panel — `FreeMono9pt7b` advances **11 px per glyph** against the
canvas mockup's 6.3 px, which drove the PR label straight through the repo
column on the first build.

`tools/ttf2gfx.py` converts any system TTF to an Adafruit GFX header at any pixel
size, removing that cliff.

| Role | Font | Notes |
|---|---|---|
| Ticket key | Menlo Bold 14 px | cap 10 px, advance 8 px |
| JIRA status | Helvetica Bold 14 px | proportional, face contrast |
| PR line, repo, footer | built-in 5×7 | 6 px advance |

All 95 glyphs verified bit-exact against Pillow's rasterisation. Adafruit packs
glyph bitmaps **continuously**, MSB first, rows *not* byte-padded — the detail
that silently corrupts hand-rolled converters.

`tools/simulate.py` renders the board at true 296×128 from the same TTFs. Layout
changes get checked there before a flash.

---

## 8. Out of scope

- Claude Code status display — the original idea; impossible on a tri-colour
  panel, which cannot animate.
- Personal-account repos.
- Battery operation. USB powered, always on.
- Any scheduled behaviour. Hiding work is a deliberate act, not a clock.

---

## 9. Open questions

1. **Push endpoint shape.** `POST /state` with a JSON item list is the
   assumption; not yet designed.
2. **WiFi credential handling.** Compile-time header, gitignored, versus a
   provisioning flow.
3. **Alert screen.** Designed in the mockup — a full-screen red takeover when a
   ticket enters *Waiting to be Merged* — but not yet built in firmware.
4. **Ghosting.** Red ghosts more persistently than black. Unknown whether an
   occasional clearing cycle is needed in practice.
5. **Poller interval.** Five minutes is the assumption; untested against JIRA
   and GitHub rate limits.
