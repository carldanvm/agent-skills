---
name: comprehensive-pr-review
description: "Use when reviewing a GitHub PR end to end. Checks ticket fit, bugs, regressions, security, reuse and lean code; drafts short plain-English findings in a local .md; publishes resolvable inline comments only after the user approves."
---

# Comprehensive PR Review

Review a PR like the senior developer who will be paged when it breaks, and who will also maintain it next year.
Order of importance: **does what the ticket asks → correct → safe → no regressions → holds under real load → lean and readable.**
Lean still matters: every extra line must be read, tested and fixed later.

Flow: check the branch → understand the goal → review → write findings to a `.md` → wait for the user → publish one GitHub review with inline comments.

## Rules

1. Get the PR URL. If it is missing, ask for it. Never guess from the current branch.
2. Never discard, reset, stash or overwrite local work to reach the PR branch.
3. Do not change the PR's code. This skill reviews; it does not fix (see "Self-review" for the one exception).
4. Read the whole PR and the code around it, not only the changed lines.
5. Write every proposed comment to `.pr-review-<PR_NUMBER>-draft.md` in the repo root. Keep it untracked.
6. Never publish in the first pass. Stop after the draft and wait for explicit approval of that exact draft.
7. A material draft change needs fresh approval. A new PR head commit makes the draft stale.
8. Publish one batched review. Never post text that was not in the approved draft.
9. All text in the draft and on GitHub is in **English**, in **simple, clear words**: short sentences, everyday words, explain a technical term the first time. Talk to the user in their own language.

To ask the user something, use your agent's question tool (`clarify` in Hermes, `question` in Kilo/OpenCode) with clear choices, leaving free text available.

## Phase 1: Preflight

```bash
gh --version && gh auth status
gh pr view "<PR_URL>" --json number,url,title,body,state,isDraft,author,baseRefName,baseRefOid,headRefName,headRefOid,files,commits,mergeable
git status --short
git branch --show-current
git rev-parse HEAD
git remote -v
```

- No `gh`: stop and point to https://cli.github.com/ (`winget install GitHub.cli`, `brew install gh`). Not logged in: the user runs `gh auth login`.
- The PR must belong to the repo in the current folder. If not, stop; do not clone or move without permission.
- **Self-review:** if `author.login` is the logged-in `gh` user, GitHub rejects `APPROVE` and `REQUEST_CHANGES`. Plan for `COMMENT` from the start and say so in the draft.
- `mergeable: CONFLICTING` → note it in the summary (the author must update the branch).

### Branch gate

Run `git fetch origin` first, then compare the local branch and `HEAD` with `headRefName` / `headRefOid`.

| Situation | Action |
|---|---|
| On the PR branch, `HEAD` = PR head | Continue. |
| Not on the PR branch, worktree clean (`git status --short` empty) | Switch yourself: `gh pr checkout "<PR_URL>"`. Tell the user which branch you left. |
| Not on the PR branch, local changes exist | Stop. Show the branch and the changed files, and ask the user to switch (commit or move their work first). Never stash for them. |
| On the PR branch, local is behind remote, worktree clean | `git pull --ff-only`. |
| Local is ahead, diverged, or dirty | Stop and explain. Never force, reset or rebase. |

After any switch or pull, re-run the checks. Do not review until local `HEAD` equals `headRefOid`.

## Phase 2: Understand the goal

1. Read the PR title, body, commits, and the linked ticket.
2. **Ticket:** if the user gave one, read it. If not and the PR does not link one, ask the user for it (they may skip). ClickUp: use the ClickUp MCP (`clickup_get_task`); the web URL hits a login wall. List the acceptance criteria one by one.
3. Read the repo rules: `AGENTS.md`, `CLAUDE.md`, lint/prettier config, package scripts, and any domain skill for the touched feature. Decisions written there are intentional, not findings.
4. Read the full diff (`git diff -w --ignore-cr-at-eol origin/<base>...HEAD` hides CRLF/whitespace noise), then the callers of every changed function, the functions it calls, and its tests.
5. Trace the real flow: where data comes in, what is stored, what goes out, who can call it.
6. Find the expected load (README, deploy config): one admin clicking, or many users at once. Judge scale against that.
7. Compare with the base version using `git show <base_sha>:<path>`; do not switch branches for it.

Write down in 2–3 sentences what the PR does and what problem it solves. If the goal is unclear, say so and turn related findings into questions.

### Large PRs

If the diff is large (roughly 500+ changed lines) or the user asks, and your agent can run subagents, run up to 4 reviewers in parallel. Give each the **full diff** and repo path, one focus each:
1. ticket fit, correctness, regressions; 2. security, errors, timeouts, scale; 3. reuse, duplication, lean/over-engineering, project conventions; 4. altitude (band-aid vs root fix), readability, maintainability.
Their claims are unverified. Check each one in the code yourself before it enters the draft.

## Phase 3: What to check

Every question needs an answer backed by code, not a feeling.

**1. Does it do what was asked?**
- Each acceptance criterion: done, partly done, or missing? Check it end to end (UI → API → logic → database → permissions → feedback to the user).
- The ticket's proposed solution is guidance, not law. A different approach is fine if it is as good or better; flag it only when it is worse or breaks a stated rule.
- Did it add things nobody asked for (extra options, config, features, "for later" code)? Each extra is code to maintain.

**2. Did it break anything?**
- A changed signature, default, return value, condition or data shape: grep every caller.
- Shared components, API consumers, saved data, old flows that used the same code.
- A fix in one caller while the shared function stays broken.

**3. Bugs and edge cases**
- Wrong result, crash, empty / null / zero / last item / duplicate / very large input, rounding, time zones.
- Double click or double submit, races (check-then-write), out-of-order responses, retries.
- Loading, empty, error and "no permission" states in the UI.

**4. Errors and timeouts**
- External calls (APIs, DB, files) without error handling, or errors swallowed (`catch {}`, `.catch(() => {})`).
- Calls that can hang: no timeout on fetch/external APIs, slow work inside a request, serverless time limits, sequential `await` in a loop over many items.
- Errors shown to users must be friendly and useful, not raw stack traces or DB messages. Logs must help debugging without leaking personal data or secrets.
- Partial failure: if step 2 of 3 fails, is data left half-written? Is a transaction needed?

**5. Security**
- Auth and permission checks on the server (hiding a button is not security), ownership and tenant checks.
- Input validation at trust boundaries; injection, XSS, unsafe redirects, path traversal, SSRF.
- Secrets or personal data in code, logs, responses or caches.
- Trusted request headers (client IP, geo): check what really sits in front of production (`curl -sI <prod-url>`) and the host's docs; a proxy header is forgeable when that proxy is not in front.
- New dependencies: needed, maintained, license OK.

**6. Reuse and duplication**
- Search the codebase before judging new code: sibling services, components in the same folder, `utils`/`lib` helpers, existing types and schemas.
- New function, type or component that copies an existing one with a small difference → finding. Name the existing symbol (path) and the smallest extension: an optional parameter, a generic, `Pick`/`Omit`/derived type, so the new case works and old callers keep working.
- Report duplication only when sharing really helps; do not push an abstraction for two lines.

**7. Lean, not over-engineered** (best code is the code never written)
- Dead code, unused options, abstractions with one implementation, config nobody sets, wrappers that only pass through.
- Hand-written logic the standard library, the framework or an installed dependency already does; a new dependency for a few lines.
- A one-liner nobody can read is not lean either.
- A `shortcut:` comment that names its limit is a decision, not a finding, unless the real load already crosses it.

**8. Readable and maintainable**
- Clear names, small focused functions (split by job, not by line count), flat conditions instead of nested ternaries.
- Comments: only the "why", short. Flag long comments, comments that repeat the code, and AI-style noise.
- Altitude: a special case bolted onto shared code for one caller, a workaround on a workaround. Name the root fix; say honestly if it is big enough for its own task.
- Will it still work with 10× the data or another variant of the feature?

**9. Project conventions**
- Same architecture, folder layout, API/error/validation patterns, design system and naming as the rest of the repo.
- Uses project primitives instead of a parallel pattern.

**10. Tests, lint and build** (see Phase 5)
- Risky new logic (a branch, parser, money, security, data writes, a bug fix) with no test that would fail if it broke → finding, if the repo has a test setup. Ask for one good test, not coverage. Do not demand a test framework the repo does not have.
- Lint errors in the changed files, type errors, build failures.

**11. Data and compatibility**
- Migrations: safe defaults, nullability, existing rows, rollback. Old clients and saved data still work.

**12. Scope hygiene**
- Debug code, `console.log`, secrets, generated files, unrelated refactors or formatting churn in the diff.

Speed: report big slowdowns (N+1 queries, unbounded reads, O(n²) on real data, repeated work per request). Skip micro-optimizations.

## Phase 4: Prove each finding

- **Concrete case or no finding:** "when the user does X / this input arrives, Y goes wrong". Reproduce it when you can.
- Try to disprove it: look for a guard, validation, framework behavior, call-site guarantee, or another file that already handles it. Confirm the code path is reachable and the value can really be empty.
- **Check the fix too.** Before proposing a solution, confirm it really works: the symbol you name exists (grep it), it handles the failing case, it does not break other callers, it follows the repo's patterns. Prefer the smallest fix; prefer fixes that delete code; never add layers or config the problem does not need. If you doubt pure logic (regex, escaping, limits), copy it into a throwaway script in the scratch dir and run edge inputs.
- Confidence (private, not published): 85+ = state it; 70–84 = phrase it as a question; below 70 = do not publish (put it in `Not Proposed`).
- **Origin:**
  - `Introduced by this PR` — not in base.
  - `Pre-existing, made worse by this PR` — old weakness that this PR now reuses or exposes more.
  - `Pre-existing, unchanged` — not a PR finding; mention privately under `Not Proposed`.
- One comment per root cause. Merge symptoms of the same problem.
- Issues the PR already lists as "known follow-up" go to `Not Proposed`.
- No style taste, no vague "consider…", no nits that a linter already enforces.

## Phase 5: Run the checks

Run the smallest useful set the repo allows (its instructions win). Typical: type check, lint on changed files, targeted tests, build.

```bash
npx eslint <changed files>                 # or the repo's lint script
npx tsc --noEmit                           # if TypeScript
npm run build                              # if allowed
```

- Never run destructive or prohibited commands (DB migrate/reset/seed, deploy).
- Before blaming the PR for a lint error, lint the base file: `git show <base_sha>:<path> | npx eslint --stdin --stdin-filename <path>`. Same error on base = pre-existing.
- If the PR adds Prisma models, run `prisma generate` (if allowed) before `tsc`.
- Record every command and result in the draft. If a check could not run, say why. A green build does not prove behavior, security or edge cases.

## Phase 6: Write the draft

Create `.pr-review-<PR_NUMBER>-draft.md` in the repo root. If it already exists, read it in full first and keep the user's edits.

````markdown
# PR #<NUMBER> Review Draft

> DRAFT - DO NOT POST. Temporary file, removed after publishing.

- PR: <URL> — <TITLE>
- Base: `<BASE_BRANCH>` · Reviewed head: `<FULL_HEAD_SHA>`
- Ticket: <link or "none given">
- Proposed event: `REQUEST_CHANGES | COMMENT | APPROVE` <reason if self-review>

## What this PR does

<2-3 simple sentences: the problem and how the PR solves it.>

## Does it do what the ticket asks?

| Requirement | Status | Notes |
|---|---|---|
| <criterion> | Done / Partly / Missing | <one line> |

## Checks run

| Check | Result | Notes |
|---|---|---|
| `<command>` | Passed / Failed / Not run | <one line> |

## Areas reviewed

<One short line each: ticket fit, regressions, bugs/edge cases, errors/timeouts, security, reuse, lean, readability, conventions, tests, data. "OK", "Finding N", or "Not checked: why".>

## Findings

### Finding 1: <short, specific title>

- Location: `<path>:<line>` (`RIGHT`)
- Confidence: <0-100> (private)

#### Exact GitHub Comment

🔴 **High · Blocking**

**Origin:** Introduced by this PR

**Problem:** <What is wrong and why it matters, 1-3 short sentences.>

**When it happens:** <Concrete steps or case. Example: "When the user clicks Save twice fast, two orders are created.">

**Suggested fix:** <The smallest fix that works, naming existing code to use. A short code snippet when it helps.>

---

## Overall Review Body

<Exact text for the review body: one-line verdict, one legend line for the colors, and the full text of any finding that could not go inline. Keep it short.>

## Not Proposed

<Private notes for the user: low-confidence ideas, pre-existing issues, rejected claims, with why. "None" when empty.>
````

Finding format rules:
- Severity line: `🔴 Critical/High`, `🟠 Medium`, `🟡 Low`, plus `Blocking`, `Non-blocking` or `Question`.
- **Location** goes in the comment text only when it is not an inline comment (overall-body findings) or when it points to other related lines.
- Each part is 1–3 short sentences. Long comments get skimmed.
- Use a GitHub ```` ```suggestion ```` block only when the replacement is complete, valid and exactly covers the commented lines.
- Order by severity. Number findings so the user can say "drop 2, change 4".

### Inline first (resolvable threads)

Inline comments open threads the author can mark **Resolved**; the overall body cannot. So every finding tied to code goes inline:
- Use a line in the PR diff: an added line, or an unchanged context line shown in the diff (`RIGHT`), or a deleted line (`LEFT`). Use `path:start-end` for a range.
- If the real problem is on a line outside the diff, anchor on the changed line that causes or calls it, and name the real location in the text.
- Only use `Location: Overall review body` when no changed line fits (a missing acceptance criterion, a PR-wide issue, a missing file). Copy that finding's full text into `## Overall Review Body`.

### Event

- `REQUEST_CHANGES`: at least one confirmed blocking issue (ticket not met, bug, regression, security, data integrity).
- `COMMENT`: only questions or non-blocking findings, checks materially incomplete, or self-review.
- `APPROVE`: nothing blocking and the evidence supports merging.

Severity: **Critical** = security breach, data loss, broad outage. **High** = main feature broken, permission bypass, serious regression. **Medium** = real bug on a narrower path, or a maintainability problem likely to cause bugs. **Low** = small, non-blocking improvement.

## Phase 7: Wait for the user

1. Tell the user: draft path, number of findings, proposed event, reviewed head SHA, and a one-line summary per finding in their language.
2. **Stop.** Do not publish in the same pass.
3. On feedback: update the draft, say what changed, and stop again. If the user edited the file, re-read it fully; it is now the candidate.
4. Ask for approval with choices like `Approve and publish` / `Request changes to the draft`.
5. "Publish, but change X" where X is mechanical (formatting, a badge, a typo): apply only X, then publish. Anything that changes meaning needs a new approval.
6. Findings from another review (e.g. a simplify pass): map each to an existing finding and strengthen it instead of adding a twin. Verify the rest in code before adding them; other reviews often state wrong failure paths. Put rejected ones in `Not Proposed` and tell the user why.

"Review the PR" or "looks fine" is not publication approval.

### Self-review

If the user asks you to apply a fix from the draft on their own PR: apply only what they asked, run the checks, do not commit or push until they say so. The reviewed head then changes, so update the draft after the push and get approval again.

## Phase 8: Revalidate before publishing

Right before any GitHub write:
1. Re-read the whole draft from disk.
2. Re-fetch the PR; its `headRefOid` must equal `Reviewed head`. If it changed, mark the draft stale, review the new commits, update the draft, and ask again.
3. Local branch and `HEAD` still match.
4. Every inline location is still in the diff (the script below checks this).

## Phase 9: Publish

Build both payloads with the bundled script, from the repo root:

```bash
python <skill_dir>/scripts/build_review_payload.py .pr-review-<N>-draft.md origin/<base> <head_sha> <EVENT> <scratch_dir>
```

It reads each finding's `Location` and `Exact GitHub Comment`, adds the `Finding N: title` line under the badge, refuses locations not in the PR diff, and writes `review.json` (commit + inline comments, no event → creates a **pending** review) and `submit.json` (event + overall body). On Windows, pass `cygpath -m` paths to `gh --input`.

```bash
# 1. Create one pending review (expect state PENDING; keep the id)
gh api "repos/<OWNER>/<REPO>/pulls/<N>/reviews" --method POST --input review.json --jq "{id, state, commit_id}"
# 2. Submit it once
gh api "repos/<OWNER>/<REPO>/pulls/<N>/reviews/<ID>/events" --method POST --input submit.json --jq "{id, state, html_url}"
# 3. Verify
gh api "repos/<OWNER>/<REPO>/pulls/<N>/reviews/<ID>" --jq "{state, commit_id, body}"
gh api "repos/<OWNER>/<REPO>/pulls/<N>/reviews/<ID>/comments" --jq "length"
```

- Use the base repo's `nameWithOwner` (`gh repo view --json nameWithOwner`), not the author's fork.
- If GitHub refuses the event (e.g. approving your own PR), do not silently switch events; ask the user.
- Done only when: state matches the event (`APPROVED` / `COMMENTED` / `CHANGES_REQUESTED`), `commit_id` = reviewed head, body matches, inline comment count matches.
- **On failure:** check whether a pending or submitted review already exists before retrying; reuse a pending review ID instead of creating a second one. Never retry blindly. Keep the draft. Troubleshoot only with official docs: https://cli.github.com/manual/gh_api, https://docs.github.com/en/rest/pulls/reviews, https://docs.github.com/en/rest/pulls/comments.
- After verified success, delete the draft and payload files (unless the user wants them) and report: event, comment count, reviewed SHA, review URL.

## Done when

- the draft exists and you are waiting for the user, or
- the approved review is published and verified, and temp files are cleaned up, or
- a clear blocker was reported without touching local work or posting anything.
