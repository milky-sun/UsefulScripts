#!/usr/bin/env python3
"""Claude Code status line.

Reads the session JSON on stdin and renders:
  <model> | TTL <cost> <tokens> | MEM <context> | CUR <5h %> | Week <7d %>

Everything except the cumulative token count comes straight from the fields
Claude Code passes in. Cumulative tokens are summed from the `usage` blocks the
API returned on each request, read out of the session transcript and cached
incrementally so a long transcript is only ever parsed once.

Renders (colors dimmed/heat-coded in the terminal):

    Opus 5 | TTL $0.70 1.22M(53.6k/1.16M) | MEM 50.1k/1M | CUR 2% (2h07m) | Week 17% (4d14h)

    TTL   session cost, then total tokens as (fresh / cache-hit). Fresh is
          uncached input + cache writes + output; cache-hit is prefix tokens
          served from the prompt cache.
    MEM   tokens currently in the context window / context window size.
    CUR   share of the 5-hour rate limit used, and time until it resets.
    Week  same for the 7-day limit.

Install: drop this file at ~/.claude/statusline.py and point settings.json at it:

    {
      "statusLine": {
        "type": "command",
        "command": "python3 ~/.claude/statusline.py",
        "refreshInterval": 30
      }
    }

refreshInterval keeps the reset countdowns ticking while the session is idle.
Requires Python 3.9+ (str.removesuffix) and Claude Code 2.1.x for the
rate_limits and context_window fields.
"""
import json
import os
import sys
import time

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
SEP = f"{DIM} │ {RESET}"

CACHE_DIR = os.path.expanduser("~/.claude/statusline-cache")
CACHE_VERSION = 2


def heat(pct):
    """Green under 50%, yellow under 80%, red at/above 80%."""
    if pct is None:
        return DIM
    if pct >= 80:
        return RED
    if pct >= 50:
        return YELLOW
    return GREEN


def tokens(n):
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}".removesuffix("0").removesuffix(".0") + "M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}".removesuffix(".0") + "k"
    return str(n)


def until(resets_at):
    """Human 'time left' until an epoch-seconds reset point."""
    if not resets_at:
        return None
    secs = int(resets_at - time.time())
    if secs <= 0:
        return "now"
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d}d{h}h"
    if h:
        return f"{h}h{m:02d}m"
    return f"{m}m"


def limit_field(label, block):
    block = block or {}
    pct = block.get("used_percentage")
    left = until(block.get("resets_at"))
    if pct is None:
        return f"{DIM}{label} -{RESET}"
    body = f"{heat(pct)}{pct:.0f}%{RESET}"
    if left:
        body += f" {DIM}({left}){RESET}"
    return f"{DIM}{label}{RESET} {body}"


def session_tokens(transcript_path, session_id):
    """Tokens the API reported for this session: (fresh, cache_hit).

    fresh     = uncached input + cache writes + output, i.e. tokens the model
                had to process for the first time.
    cache_hit = cache reads, i.e. prefix tokens served from the prompt cache.

    Their sum is everything the session's requests moved. Requests are deduped
    by requestId because the transcript repeats a usage block once per content
    block.
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return None, None

    cache_path = os.path.join(CACHE_DIR, f"{session_id or 'unknown'}.json")
    offset, seen = 0, {}
    try:
        with open(cache_path) as fh:
            cached = json.load(fh)
        if cached.get("path") == transcript_path and cached.get("v") == CACHE_VERSION:
            offset = cached.get("offset", 0)
            seen = cached.get("requests", {})
    except Exception:
        pass

    # A shrunken file means it was rewritten, so start over.
    if os.path.getsize(transcript_path) < offset:
        offset, seen = 0, {}

    try:
        with open(transcript_path, "rb") as fh:
            fh.seek(offset)
            data = fh.read()
            # Only consume whole lines; a partial trailing line is re-read next time.
            cut = data.rfind(b"\n") + 1
            offset += cut
            for raw in data[:cut].splitlines():
                try:
                    rec = json.loads(raw)
                except Exception:
                    continue
                usage = (rec.get("message") or {}).get("usage")
                rid = rec.get("requestId")
                if not usage or not rid:
                    continue
                seen[rid] = [
                    usage.get("input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("output_tokens", 0),
                    usage.get("cache_read_input_tokens", 0),
                ]
    except Exception:
        return None, None

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = cache_path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(
                {
                    "v": CACHE_VERSION,
                    "path": transcript_path,
                    "offset": offset,
                    "requests": seen,
                },
                fh,
            )
        os.replace(tmp, cache_path)
    except Exception:
        pass

    return sum(v[0] for v in seen.values()), sum(v[1] for v in seen.values())


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        print(f"{DIM}statusline: no session data{RESET}")
        return

    parts = []

    model = (d.get("model") or {}).get("display_name") or (d.get("model") or {}).get("id") or "?"
    model = model.split(" (")[0]
    parts.append(f"{BOLD}{CYAN}{model}{RESET}")

    cost = (d.get("cost") or {}).get("total_cost_usd")
    ttl = f"${cost:.2f}" if cost is not None else "-"
    fresh, cached_hit = session_tokens(d.get("transcript_path"), d.get("session_id"))
    if fresh is not None:
        ttl += (
            f" {tokens(fresh + cached_hit)}"
            f"{DIM}({tokens(fresh)}/{tokens(cached_hit)}){RESET}"
        )
    parts.append(f"{DIM}TTL{RESET} {ttl}")

    cw = d.get("context_window") or {}
    used = (cw.get("total_input_tokens") or 0) + (cw.get("total_output_tokens") or 0)
    size = cw.get("context_window_size")
    mem = tokens(used)
    if size:
        mem += f"/{tokens(size)}"
    parts.append(f"{DIM}MEM{RESET} {mem}")

    rl = d.get("rate_limits") or {}
    parts.append(limit_field("CUR", rl.get("five_hour")))
    parts.append(limit_field("Week", rl.get("seven_day")))

    print(SEP.join(parts))


if __name__ == "__main__":
    main()
