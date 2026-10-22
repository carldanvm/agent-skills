"""Build GitHub review payloads from an approved .pr-review-<N>-draft.md.

Usage (from the repo root):
  python build_review_payload.py <draft.md> <base_ref> <head_sha> <EVENT> <out_dir>

- Reads every '### Finding N: <title>' block that has a Location like
  `path:42` (`RIGHT`) or `path:40-45` (`RIGHT`). LEFT = deleted lines.
  Findings with Location `Overall review body` are skipped: they live in the overall body.
- Checks each line is commentable in `git diff base...head` (the PR diff):
  RIGHT = added or context lines, LEFT = deleted lines. Exits 1 listing bad locations.
- Writes <out_dir>/review.json (pending review: commit_id + comments, no event/body)
  and <out_dir>/submit.json (event + Overall Review Body).
"""
import json, os, re, subprocess, sys

draft, base, head, event, out = sys.argv[1:6]
diff = subprocess.run(["git", "diff", f"{base}...{head}"], capture_output=True, text=True,
                      encoding="utf-8", check=True).stdout

# Lines GitHub accepts inline comments on, per side and file.
ok = {"RIGHT": {}, "LEFT": {}}
path, in_hunk = None, False
for d in diff.splitlines():
    if d.startswith("diff --git"):
        path, in_hunk = None, False
    elif not in_hunk and d.startswith("+++ "):
        path = d[6:] if d.startswith("+++ b/") else None
    elif path and d.startswith("@@"):
        m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", d)
        old, new, in_hunk = int(m[1]), int(m[2]), True
    elif path and in_hunk:
        if d[:1] in ("+", " "):
            ok["RIGHT"].setdefault(path, set()).add(new)
            new += 1
        if d[:1] in ("-", " "):
            if d[:1] == "-":
                ok["LEFT"].setdefault(path, set()).add(old)
            old += 1

s = open(draft, encoding="utf-8").read().replace("\r\n", "\n")
if "## Overall Review Body\n\n" not in s:
    sys.exit("Draft has no '## Overall Review Body' section")
comments, bad = [], []
blocks = re.finditer(r"### Finding (\d+): ([^\n]*)\n(.*?)(?=\n### Finding \d+:|\n## )", s, flags=re.S)
for blk in blocks:
    num, title, text = blk[1], blk[2].strip(), blk[3]
    loc = re.search(r"- Location: `([^`]+?):(\d+)(?:-(\d+))?` \(`(RIGHT|LEFT)`\)", text)
    if not loc:
        continue  # overall-body finding
    fpath, first, side = loc[1], int(loc[2]), loc[4]
    last = int(loc[3] or first)
    if any(n not in ok[side].get(fpath, set()) for n in range(first, last + 1)):
        bad.append(f"Finding {num}: {fpath}:{first}-{last} ({side})")
        continue
    if "#### Exact GitHub Comment\n\n" not in text:
        sys.exit(f"Finding {num} has no '#### Exact GitHub Comment' section")
    body = text.split("#### Exact GitHub Comment\n\n", 1)[1].strip()
    body = re.sub(r"\n+---\s*$", "", body).strip()  # drop the draft's finding separator
    # GitHub does not number comments: put 'Finding N: title' under the badge line
    badge, _, rest = body.partition("\n")
    body = f"{badge}\n\n**Finding {num}: {title}**\n\n{rest.lstrip()}"
    c = {"path": fpath, "line": last, "side": side, "body": body}
    if last != first:
        c.update(start_line=first, start_side=side)
    comments.append(c)
if bad:
    sys.exit("Not commentable in the PR diff:\n  " + "\n  ".join(bad))

overall = s.split("## Overall Review Body\n\n", 1)[1].split("\n## Not Proposed")[0].strip()
with open(os.path.join(out, "review.json"), "w", encoding="utf-8") as f:
    json.dump({"commit_id": head, "comments": comments}, f, ensure_ascii=False, indent=1)
with open(os.path.join(out, "submit.json"), "w", encoding="utf-8") as f:
    json.dump({"event": event, "body": overall}, f, ensure_ascii=False, indent=1)
print(f"{len(comments)} inline comments; event {event}")
for c in comments:
    print(f"  {c['path']}:{c.get('start_line', c['line'])}-{c['line']} {c['side']}")
