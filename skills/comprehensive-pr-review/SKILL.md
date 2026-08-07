---
name: comprehensive-pr-review
description: Use for an end-to-end GitHub pull request review that validates the local PR branch, evaluates correctness, regressions, security, maintainability, project conventions, tests, performance, and edge cases, writes an English review draft for user feedback, and publishes only after explicit approval.
---

# Comprehensive PR Review

## Purpose

Perform a rigorous, evidence-based pull request review. First inspect the PR without modifying its source code, then write every proposed GitHub comment to a temporary Markdown draft in the repository root. Iterate on that draft with the user and publish a batched GitHub review only after the user explicitly approves the exact final content.

The review is educational, not accusatory. Every comment must explain the failure mode, its impact, and a practical recommended solution. All text intended for GitHub must be in English, regardless of the language used to communicate with the user.

## Non-Negotiable Rules

1. Obtain the PR URL. If the invocation does not include one, ask for it with the `question` tool.
2. Verify the local checkout is on the PR head branch and exact reviewed head commit. Ask for explicit permission before changing branches or updating the working tree.
3. Never discard, overwrite, reset, stash, or otherwise disturb local changes to reach the PR branch.
4. Do not modify the PR's implementation during review. This workflow reviews code; it does not fix it.
5. Review the entire PR and relevant surrounding code, not only isolated changed lines.
6. Create a temporary root-level draft named `.pr-review-<PR_NUMBER>-draft.md`.
7. Never publish during the initial review pass. Stop after presenting the draft path and wait for user feedback or explicit approval.
8. Any material draft revision requires fresh approval. A new PR head commit invalidates the draft and all prior approval.
9. Use one GitHub pending review to batch all approved comments. This skill is standalone and must not depend on another skill being installed.
10. Never post a comment that was not present in the approved draft.
11. Preserve the draft if publication fails. Remove it only after the complete review is successfully submitted, unless the user explicitly asks to keep it.

## Phase 1: PR And Environment Preflight

### Obtain And Validate The PR

Use the supplied GitHub PR URL as the canonical identifier. Do not guess from the current branch when no URL was supplied.

Verify prerequisites and collect metadata:

```bash
gh --version
gh auth status
gh pr view "<PR_URL>" --json number,url,title,body,state,isDraft,author,baseRefName,headRefName,headRefOid,files,commits
git status --short
git branch --show-current
git rev-parse HEAD
git remote -v
```

If `gh` is unavailable, stop before reviewing and tell the user that GitHub CLI is required. Point them to `https://cli.github.com/` and provide an appropriate installation example:

```text
macOS:   brew install gh
Windows: winget install GitHub.cli
Linux:   use the package instructions at https://github.com/cli/cli/blob/trunk/docs/install_linux.md
```

After installation, authentication is required with `gh auth login`. Use an interactive terminal only when the user must complete that authentication flow. Re-run `gh auth status` afterward and do not continue until it succeeds.

Confirm that the PR belongs to the repository in the current workspace. If it belongs to another repository, stop and explain that the correct local repository is required; do not clone or change workspaces without permission.

### Branch And Commit Gate

Compare:

- Current local branch against the PR `headRefName`.
- Local `HEAD` against the PR `headRefOid`.
- Current repository against the PR repository.

If the branch differs, show the current branch, target branch, and current worktree status, then ask permission with the `question` tool before running `gh pr checkout "<PR_URL>"`.

If the branch name matches but `HEAD` differs from the PR head, determine whether the local branch is behind, ahead, or diverged. Ask permission before any checkout, pull, merge, rebase, or working-tree update. Prefer a safe fast-forward where possible. Never force-update, reset, stash, or overwrite work. If local changes or divergence make a safe switch/update impossible, stop and describe the blocker.

After an approved checkout or update, re-run the branch, `HEAD`, status, and PR head checks. Do not continue until the reviewed local commit exactly matches the current PR head commit.

## Phase 2: Understand Intent And Project Context

Before judging the implementation:

1. Read the PR title, body, commit list, linked issue or specification when accessible, and base/head information.
2. Read repository instructions such as `AGENTS.md`, `CLAUDE.md`, relevant documentation, package scripts, lint configuration, and architectural guidance.
3. Identify the intended behavior, acceptance criteria, constraints, and explicitly out-of-scope work.
4. Inspect the complete diff and classify changed files by domain: application code, API, data, authentication, UI, infrastructure, tests, generated files, and documentation.
5. Trace affected callers, consumers, types, persistence boundaries, authorization boundaries, and neighboring code paths.
6. Compare changed behavior with the base version when needed using Git history or `git show`; do not switch branches merely to inspect the base implementation.

Do not assume the PR description is complete or that repository documentation is current. Cross-check claims against code and observable behavior. If intent remains ambiguous, record the assumption and phrase the potential finding as a question rather than an assertion.

## Phase 3: Review Rubric

Evaluate every applicable category. Record concrete evidence, not generic impressions.

### Correctness And Objective Completion

- Does the implementation satisfy the PR's stated objective and acceptance criteria end to end?
- Are all relevant layers wired together, including UI, API, domain logic, persistence, permissions, and feedback states?
- Are return values, state transitions, contracts, and failure behavior correct?
- Are there incomplete branches, dead code, placeholders, or paths that only appear to work in the happy case?

### Regression Risk

- Could the change break existing callers, flows, state, persisted data, API consumers, shared components, or configuration?
- Did a signature, default, condition, side effect, ordering assumption, or data shape change unexpectedly?
- Does the implementation preserve behavior outside the new feature's intended scope?
- Compare against the base implementation and inspect all meaningful call sites before claiming a regression.

### Code Quality, Maintainability, And Scalability

- Is the code clear, cohesive, minimally complex, and appropriately decomposed?
- Are names, abstractions, boundaries, and ownership understandable?
- Will the design remain workable as data volume, feature variants, or team ownership grows?
- Does it avoid premature abstraction as well as tightly coupled one-off logic?

### Project Consistency

- Does the change follow repository architecture, conventions, design system, API patterns, validation, error handling, access control, and dependency rules?
- Does it reuse existing framework and project primitives rather than introducing parallel patterns?
- Are repository-specific constraints applied in every required layer?

### DRY And Reuse

- Is behavior duplicated that should use an existing utility, component, schema, service, constant, or source of truth?
- Did the PR create multiple implementations that can drift?
- Would centralization actually improve correctness and ownership, or would it merely create an unnecessary abstraction? Only report meaningful duplication.

### Security And Privacy

- Authentication, authorization, tenant isolation, ownership checks, and read-only restrictions.
- Input validation, output encoding, injection, path traversal, SSRF, XSS, CSRF, unsafe redirects, and deserialization risks where applicable.
- Secret, token, personal data, logging, caching, and error-message exposure.
- Server-side enforcement. UI hiding alone is not security.
- Dependency or supply-chain concerns introduced by the PR.

### Edge Cases And Failure Modes

- Empty, null, missing, malformed, duplicate, stale, deleted, and maximum-size inputs.
- Partial failures, retries, timeouts, cancellation, offline behavior, and external-service failures.
- Concurrency, races, idempotency, transaction boundaries, double submission, and out-of-order responses.
- Time zones, locale, precision, ordering, pagination, and boundary values where relevant.
- Loading, empty, error, permission-denied, and recovery states in user-facing flows.

### Tests And Verification

- Do tests cover the new behavior, regression-sensitive paths, failures, boundaries, and permissions?
- Do assertions validate behavior rather than implementation details?
- Would the tests fail if the suspected bug were present?
- Are existing tests now stale or misleading?
- Run only checks permitted by repository instructions. Never invent a test command or run prohibited database, migration, deployment, or destructive commands.

### Performance And Resource Use

- Algorithmic growth, repeated work, unnecessary renders, N+1 queries, unbounded reads, large payloads, memory pressure, connection use, and cache behavior.
- Behavior under realistic production volume, not only sample data.
- Do not report speculative micro-optimizations without a credible impact path.

### Data Integrity And Compatibility

- Schema and migration safety, defaults, nullability, constraints, transactions, soft deletes, and rollback implications.
- Backward compatibility for APIs, events, persisted state, configuration, clients, and rolling deployments.
- Data conversion, version skew, and partial deployment behavior.

### Operability And Observability

- Are failures diagnosable through useful errors, logs, metrics, or traces without leaking sensitive data?
- Are retry behavior, alerts, feature flags, rollout, and recovery appropriate for the risk?
- Could the change fail silently or leave inconsistent state?

### User Experience And Accessibility

- When UI changes are present, inspect responsiveness, keyboard access, focus, semantics, labels, contrast, motion, and screen-reader behavior.
- Check destructive-action safeguards, feedback timing, error recovery, and consistency with the project's design system.

### Scope And Dependency Hygiene

- Is the diff focused on the stated goal, with no accidental generated files, debug code, unrelated refactors, secrets, or dependency churn?
- Are new dependencies necessary, maintained, license-compatible where relevant, and used safely?
- Are documentation or operational changes required for the feature to work safely?

## Phase 4: Evidence And Confidence

Every proposed finding must be grounded in a specific changed behavior and a plausible execution path. Reproduce or verify it when feasible.

Confidence is not severity. Score confidence from 0 to 100 based on evidence that the issue is real and correctly understood:

| Score | Meaning | Treatment |
|---|---|---|
| 95-100 | Directly reproducible or logically certain from the executed path and contract | State clearly |
| 85-94 | Strong code-path evidence with only minor contextual uncertainty | State as a finding and name the assumption |
| 70-84 | Plausible but material context is missing | Phrase as a non-blocking question or request for verification |
| Below 70 | Too speculative for a public review comment | Do not propose for publication; place in the private `Not Proposed` section if useful |

Before retaining a finding, attempt to disprove it:

- Search for validation, guards, call-site guarantees, framework behavior, tests, or project conventions that resolve it.
- Check whether the cited path is reachable.
- Check whether the behavior is intentional and documented.
- Check whether another changed file handles the concern.
- Distinguish a defect from a preference or optional refactor.

Classify origin precisely:

- `Introduced by this PR`: the base branch did not contain the issue.
- `Pre-existing, amplified by this PR`: the weakness existed, but this PR reuses it in a new path, increases exposure, or makes its impact relevant to the changed feature.
- `Pre-existing, unchanged`: unrelated to the PR. Do not publish it as a PR finding; optionally note it privately under `Not Proposed`.
- `Uncertain`: history or intent is insufficient. Explain what evidence is missing and use question wording.

Do not blame the PR author for pre-existing behavior. Deduplicate findings that share one root cause. Prefer one well-placed comment over repeated comments on every symptom.

## Phase 5: Validation

Run the smallest useful set of repository-approved checks after static analysis. Examples include type checking, linting, targeted tests, build checks, or a focused reproduction, but repository instructions take precedence.

Record every command and its result in the draft. If a check cannot be run because of missing credentials, environment, services, prohibited commands, or absent test infrastructure, state that limitation. Never claim the feature works solely because the code looks reasonable.

Do not use validation as a substitute for review. A passing build does not prove behavior, security, permissions, or edge cases.

## Phase 6: Draft The Review

Create `.pr-review-<PR_NUMBER>-draft.md` in the repository root. Check whether the path already exists before writing; read and preserve relevant user edits rather than overwriting them blindly. Keep the file untracked and never stage it.

The draft itself and all proposed GitHub text must be in English. Use this structure:

````markdown
# PR #<NUMBER> Review Draft

> Status: DRAFT - DO NOT POST
> This file is temporary and will be removed after successful publication unless the user asks to keep it.

- PR: <URL>
- Title: <TITLE>
- Base: `<BASE_BRANCH>`
- Reviewed head: `<FULL_HEAD_SHA>`
- Proposed event: `REQUEST_CHANGES | COMMENT | APPROVE`

## Review Summary

<Concise summary of what was reviewed and the overall result.>

## Validation Performed

| Command/check | Result | Notes |
|---|---|---|
| `<command>` | Passed/Failed/Not run | <evidence or limitation> |

## Coverage Checklist

| Area | Result | Evidence/notes |
|---|---|---|
| Objective completion | Pass/Finding/Not applicable/Not verified | ... |
| Correctness and regressions | ... | ... |
| Maintainability and project consistency | ... | ... |
| DRY and reuse | ... | ... |
| Security and privacy | ... | ... |
| Edge cases and failure modes | ... | ... |
| Tests | ... | ... |
| Performance and scalability | ... | ... |
| Data integrity and compatibility | ... | ... |
| Operability and observability | ... | ... |
| UX and accessibility | ... | ... |
| Scope and dependencies | ... | ... |

## Proposed GitHub Review

### Finding 1: <Short actionable title>

- Severity: `Critical | High | Medium | Low`
- Confidence: `<0-100>/100`
- Disposition: `Blocking | Non-blocking question | Non-blocking suggestion`
- Origin: `Introduced by this PR | Pre-existing, amplified by this PR | Uncertain`
- Location: `<path>:<line>` (`RIGHT` or `LEFT`) or `Overall review body`

#### Exact GitHub Comment

<The exact English text to publish. It must include all sections below.>

**Issue**
<Clear explanation grounded in the code.>

**Origin**
<Whether and how the PR introduced or amplified it.>

**When this occurs**
<Concrete input, state, sequence, or production scenario.>

**Impact**
<Why it matters and what breaks, leaks, slows down, or becomes hard to maintain.>

**Recommended fix**
1. <Implementation step.>
2. <Implementation step.>
3. <Verification or regression-test step.>

<Optional alternative wording making clear the proposal is recommended, not the only acceptable design.>

**Confidence: <score>/100**

## Overall Review Body

<Exact English body submitted with the batched review.>

## Not Proposed For Publication

<Low-confidence suspicions, unrelated pre-existing issues, or optional notes. Explain why each is excluded. Use `None` when empty.>
````

Order findings by severity, then confidence. Findings are the primary output; do not bury them beneath a long overview.

### Comment Quality Rules

- Make the title and first sentence actionable and specific.
- Explain one root issue per comment.
- Include a concrete occurrence example, not merely "this could fail."
- Describe user, security, data, operational, or maintenance impact without exaggeration.
- Give clear implementation steps and include a regression test or verification step when applicable.
- Present the solution as the recommended approach, not the only valid approach, unless a hard project/security requirement leaves no alternative.
- Avoid personal language, sarcasm, vague criticism, praise padding, and style-only nitpicks already enforced by automation.
- Attach inline comments only to lines eligible in the PR diff. If no suitable changed line exists, use the overall review body.
- Include a GitHub `suggestion` block only when the replacement is complete, syntactically valid, scoped to the exact line range, and genuinely clearer than prose.

### Event Selection

- `REQUEST_CHANGES`: at least one confirmed blocking correctness, regression, security, data-integrity, or objective-completion issue.
- `COMMENT`: findings are questions/non-blocking, verification is materially incomplete, or approval is inappropriate.
- `APPROVE`: no blocking findings remain and available evidence supports merge readiness.

Severity guidance:

- `Critical`: likely severe security breach, irreversible data loss/corruption, or broad production outage.
- `High`: major feature failure, authorization bypass, serious regression, or significant data-integrity risk.
- `Medium`: real defect affecting a narrower path, meaningful edge case, or maintainability problem likely to cause defects.
- `Low`: limited-impact issue or worthwhile non-blocking improvement. Do not use review comments for trivial preferences.

## Phase 7: User Review And Iteration Gate

After writing the draft:

1. Tell the user the exact file path, number of proposed findings, proposed event, and reviewed head SHA.
2. Stop. Do not publish in the same pass.
3. Wait for the user to inspect the file and either provide feedback or explicitly approve it.
4. If feedback is provided, update the draft, summarize what changed, and stop again for fresh approval.
5. If the user edited the file directly, re-read it and treat the file's current content as the candidate draft.
6. Use the `question` tool when explicit approval is needed, with choices equivalent to `Approve exactly as drafted` and `Request revisions`. Custom feedback must remain available.

Approval applies only to the exact draft contents and reviewed head SHA. General statements such as "review the PR," "looks mostly fine," or prior permission to perform a review are not publication approval.

## Phase 8: Revalidate Before Publishing

After explicit approval and immediately before any GitHub write:

1. Re-read the complete draft from disk.
2. Re-fetch PR metadata and compare the current head SHA with `Reviewed head`.
3. Confirm the local branch and `HEAD` still match the PR.
4. Confirm every inline location is still part of the current diff and the exact approved comment maps to the intended code.
5. Confirm the event type and overall body match the approved draft.

If the PR head changed, do not post stale comments. Mark the draft as stale, review the new commits and affected findings, update the reviewed SHA, and return to the user approval gate.

If the draft changed after approval, request fresh approval.

## Phase 9: Publish Through GitHub

Publication requirements:

- Re-check `gh` availability and authentication.
- Create one pending review containing all approved inline comments.
- Submit that pending review once with the approved `APPROVE`, `COMMENT`, or `REQUEST_CHANGES` event and exact overall body.
- Do not publish comments individually and do not add unapproved text.
- If there are no inline findings, still create an empty pending review and then submit the approved overall review/event.
- If GitHub does not permit the selected event, such as approving one's own PR, do not silently choose a different public action. Explain the constraint and obtain approval for any changed event/body.

### Collect Publication Identifiers

Immediately before publishing, collect and verify the repository, PR number, and latest commit:

```bash
gh repo view --json nameWithOwner
gh pr view "<PR_URL>" --json number,headRefName,headRefOid
git branch --show-current
git rev-parse HEAD
```

Use the base repository's `nameWithOwner`, the PR number, and the exact approved `headRefOid`. Do not infer the repository owner from the PR author's fork.

### Build The Review Payload

Prefer `gh api --input` with a JSON payload over many shell `-f` arguments. This avoids quoting bugs in multiline comments, Markdown code fences, apostrophes, and repeated `comments[]` fields.

Construct a temporary JSON payload from the exact approved draft:

```json
{
  "commit_id": "<APPROVED_HEAD_SHA>",
  "comments": [
    {
      "path": "src/example.ts",
      "line": 42,
      "side": "RIGHT",
      "body": "<EXACT APPROVED ENGLISH COMMENT>"
    }
  ]
}
```

For deleted lines, use `"side": "LEFT"` with the base-side line number. For a multiline comment range, include `start_line` and `start_side` in addition to `line` and `side`. Omit `comments` or use an empty array when there are no inline comments.

Do not place `event` in the creation payload. Omitting it is what creates a pending review. Do not place the overall review body in the creation payload; submit that exact body only in the final event request.

Create the payload only after approval. Keep it untracked, never stage it, and remove it after successful publication. Use the environment's safe file-writing tools rather than shell string interpolation when comments contain multiline Markdown.

### Create One Pending Review

Create the pending review with the approved comments:

```text
gh api "repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/reviews" --method POST --input "<REVIEW_PAYLOAD_PATH>" --jq "{id, state, commit_id}"
```

The expected state is `PENDING`. Capture the returned review ID. If the request returns another state or an incomplete response, stop and inspect the server result before continuing.

### Submit The Pending Review

Submit the captured pending review exactly once:

```text
gh api "repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/reviews/<REVIEW_ID>/events" --method POST -f event="<APPROVE|COMMENT|REQUEST_CHANGES>" -f body="<EXACT_APPROVED_OVERALL_BODY>" --jq "{id, state, submitted_at, html_url}"
```

When the overall body contains multiline Markdown or shell-sensitive characters, use a small JSON input payload for this request as well:

```json
{
  "event": "REQUEST_CHANGES",
  "body": "<EXACT APPROVED OVERALL BODY>"
}
```

Then submit it with:

```text
gh api "repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/reviews/<REVIEW_ID>/events" --method POST --input "<SUBMIT_PAYLOAD_PATH>" --jq "{id, state, submitted_at, html_url}"
```

Prefer the JSON input form whenever the body is not a simple one-line string.

### Verify Publication

After submission, query the review directly:

```text
gh api "repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/reviews/<REVIEW_ID>" --jq "{id, state, commit_id, submitted_at, html_url, body}"
```

Confirm that:

- The state matches the approved event (`APPROVED`, `COMMENTED`, or `CHANGES_REQUESTED`).
- The `commit_id` is the approved reviewed head SHA.
- The body matches the approved overall body.
- The expected number of inline comments exists. Query `repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/reviews/<REVIEW_ID>/comments` if needed.

Do not report success until this verification passes.

### Failure Recovery

If publication fails, inspect whether a pending or submitted review was already created before retrying. Never retry blindly and risk duplicate comments. Preserve the draft and report any pending review ID. If API behavior has changed, consult current official GitHub CLI and GitHub REST API documentation before adapting the request.

Use only official documentation for publication troubleshooting:

- GitHub CLI `gh api`: `https://cli.github.com/manual/gh_api`
- Pull request reviews REST API: `https://docs.github.com/en/rest/pulls/reviews`
- Pull request review comments REST API: `https://docs.github.com/en/rest/pulls/comments`

If review creation succeeded but submission failed, reuse the existing pending review ID after diagnosing the failure; do not create a second review. If submission may have succeeded but the response was lost, query the review ID and current user's reviews before taking another write action.

After submission, verify the resulting review state and URL or review ID. Only then remove the temporary draft unless the user asked to retain it. Report the published event, comment count, reviewed SHA, and verification result.

## Review Completion Standard

The workflow is complete only when one of these is true:

- The draft exists and the process is explicitly waiting for user feedback/approval.
- The approved review was published and verified, and temporary-file cleanup was handled.
- A concrete blocker was reported without altering local work or publishing partial feedback.
