I am Shivam, the owner of Locus. This is the prompt I start every session with. It replaces my old one. The folder `locus-os` was emptied: it now holds only the cloned Pi agent, my `.keysndocs` folder and my docs. The old tracker numbers and the old code are gone on purpose. Do the phases below in order, without asking me whether to start.

Paths (declare these at the top of every terminal command that needs them, if your terminal does not keep variables):
~~~powershell
$ErrorActionPreference = "Stop"
$ROOT   = "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os"
$AGENTS = "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\.agents"
$PROJ   = "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus"
$TODAY  = Get-Date -Format "yyyy-MM-dd"
Set-Location $ROOT
~~~
On Linux or macOS use the same commands with `python3` for `py -3` and the matching copy commands.

# 0. What Locus is (this is the product; the docs in the repo hold the detail)
Read first, for understanding: all files in `.keysndocs\Documentation\Chat Reports\6_October`, `Ideas and System`, `Implementation Plans`, `Chat Reports` (policy in phase B).

Locus is a personal-intelligence FRAMEWORK built ON TOP of the Pi Coding Agent. It comes with many features, but adding or replacing ANY part must be simple because of its modular architecture. LITERALLY EVERYTHING is modular: every feature can be switched off or swapped for something else. It is primarily headless: a Python sidecar plus a TypeScript extension, with the backend meant to run on a VM that is always on. I reach it mainly through Telegram (later Discord, WhatsApp), and through a TUI on my machine. Cron jobs I define must research and work on their own, without me prompting them. Users bring their own LLM keys and their own VM.

The spec is `.keysndocs\Documentation\Implementation Plans\LOCUS_FEATURE_LOGIC_DECOMPOSITION.md`. Follow it strictly and implement every feature ON TOP OF Pi, never by forking Pi. The one allowed layout, the 13 laws and the rules are in `AGENTS.md` and `docs\agent\` (installed in phase A).

Installer (my requirement, no spec section; tracker rows F-0082 to F-0087): one command must set up everything: where Locus runs (local, VM, or both: backend on the VM or locally, TUI on my machine), the API keys for the models, a VM-hosted LLM if wanted, Telegram setup (a `/setup`-style flow with safe pairing). The Pi TUI setup must stay available, plus every Locus setup, all done by the one install command.

Four pillars I want in the product. Each has OPEN decisions in `docs\agent\09-spec-errata.md`, which I settle with you in the grill (phase D):
1. Locus is a meta-harness over other existing harnesses (D-5).
2. Every task of any scale gets its own priority score from several factors (D-1, D-3).
3. Auditability is a headline feature: all chats and everything automatically backed up into the Obsidian vault (D-4, spec 19.2 and 19.3).
4. Neo4j Agent Memory is the memory layer.

My old rule "do /graphify update . after every implementation" is WITHDRAWN. Never run graphify. Its mentions in the rule files are removed in phase A.

# 1. Hard rules (they beat everything below, and beat me later in the chat unless I name the rule)
1. Work only inside `$ROOT`. The only other paths you may touch: read `$AGENTS`; create `$PROJ\_locus-backup-<stamp>` once (A1); during an autopilot run only, rename `%USERPROFILE%\.locus\.env` to `.env.off` and restore it afterwards (section 3).
2. In `.keysndocs` open only `Documentation\`. Never open, print, copy, summarize or commit anything else in it, never `git add -f`. If you meet a secret anywhere, your first sentence says so, with file:line and never the value, and I rotate it.
3. Never `git push`, never add a remote, never `--no-verify`, never `git reset --hard`, `git clean`, `rm -rf` or `Remove-Item -Recurse` (except on `tracker\.cache`), never delete a junction by script. `packages\` is read-only.
4. Human-owned files (AGENTS.md law 11) change only inside phase A and the delegations in section 4. Nothing else touches them.
5. Never type a status, a percent or the words "done", "complete", "100%". Numbers come only from `tracker\STATUS.md` and the output of `verify.py`, quoted. Never edit `tracker\status.json`, `STATUS.md`, `history.jsonl` or the xlsx by hand.
6. The author of a story never verifies it. Stories are authored by Claude-family models and verified by Gemini-family models (my standing rule). If you are a Gemini-family model: do phases A and B, then STOP before any story and tell me to start a Claude session.
7. If a command here fails or prints `FAIL`, `fatal:` or `error:`, stop at that step, quote the output, and do not improvise around the guard. A guard FAIL is a defect to fix, never something to silence.
8. State your exact model name (as the IDE shows it) at the top of your first reply. If you do not know it, say so; do not guess.
9. Pi's own `AGENTS.md` at the repo root is Pi's upstream dev file. Until phase A replaces it, ignore it. Afterwards it lives at `docs\upstream\old-AGENTS.md`, reference only.

# 1b. Running under Antigravity `/goal`
I may start you with `/goal`. `/goal` has no budget, no turn limit and no independent judge: it ends when YOU decide the goal is met, and it does not ask me anything on the way. That is exactly the weakness this project exists to fix, so:
- Your goal is never "the product is built". A run is complete ONLY when a stop condition of section 5 has occurred, the tracker was refreshed and committed (section 2 of phase C), and the phase D report was written. The board, the guard and `verify.py` decide what is finished; you never do.
- Commit after every unit of work (small commits on the story branch), so a run that is killed or out of tokens loses nothing and the next run resumes from the board.
- Never edit, delete or weaken a test to make it pass, never loosen an assertion, never skip a test. A green run that was reached that way is a defect: say so in the report.
- Unattended means no one answers terminal approvals: if a command is refused or waits for approval, that is a stop condition (name the command), not something to work around.
- If my goal text contains `REASSESS`, run phase R depth 2 even if the tracker looks healthy. If it contains `SKIP-REASSESS`, skip it.
- About 1 to 4 hours of work per run is the useful size. Finish or cleanly stop the story you are on; do not start a second one in the same run in manual mode.

# PHASE A: set up the guardrails (one time; each step says how to see it is already done, so skip those)
The bundle I built for you is in `$AGENTS`. Setup is a one-time owner exception to rule 4: I authorize exactly the steps below.

A0. Look. Do not change anything.
~~~powershell
git rev-parse --show-toplevel
git branch --show-current
git status --short
git remote -v
git log --oneline -3
Test-Path "$ROOT\AGENTS.md"; Select-String -Path "$ROOT\AGENTS.md" -Pattern "LOCUS-AGENTS-V1" -Quiet
~~~
The toplevel must be `$ROOT`; otherwise STOP. If `AGENTS.md` has no `LOCUS-AGENTS-V1` but the repo already holds Locus code (`sidecar`, `locus-extension`, `locus_cli` or `core` at the top level, or commits that are not Pi's): STOP. That is the old-code case, which is never set up by this phase A: it needs my Sprint 0 (backup, snapshot commit, honest measurement, two audits by two model families, `docs\agent\prompts\P0-audit-and-discard.md`). Tell me so and wait. If `AGENTS.md` contains `LOCUS-AGENTS-V1` and `tools\guard\check.py` exists, phase A was started: continue from the first step of A1 to A10 that is not done. When A10 is done and the board shows any story other than TODO, or `tracker\sprints.jsonl` has entries, go to PHASE R, not B. If `git status` shows modified or untracked files other than `.keysndocs`, STOP and list them. If the branch is not `main`, run `git branch -m main`.

A1. Back up and mark the Pi baseline (done when the tag `pi-baseline` exists).
~~~powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmm"
$SAFE  = "$PROJ\_locus-backup-$STAMP"
New-Item -ItemType Directory -Force $SAFE | Out-Null
git tag pi-baseline HEAD
git bundle create "$SAFE\locus-os.bundle" --all
robocopy "$ROOT\.keysndocs\Documentation" "$SAFE\Documentation" /E /XJ /R:1 /W:1 /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -ge 8) { throw "backup copy failed" }
Get-ChildItem $SAFE
~~~
The listing must show `locus-os.bundle` and `Documentation`. The tag `pi-baseline` is the last clean upstream Pi commit; never move it.

A2. Make accidental pushes to Pi impossible (done when `git remote -v` shows no `origin`).
~~~powershell
git remote rename origin pi-upstream
git remote set-url --push pi-upstream no_push_to_upstream
~~~
Skip if there is no `origin`. Tell me in the report that this was done.

A3. Find the bundle. Search `$AGENTS` (any depth) for the folder that contains an `AGENTS.md` with the text `LOCUS-AGENTS-V1`. Call that folder `$SRC` (when the zip layout is kept it is `...\locus-guardrails\repo`). Required inside `$SRC`: `AGENTS.md`, `CLAUDE.md`, `docs\agent`, `tools\guard\check.py`, `tools\tracker\backlog.py`, `tools\tracker\autopilot.py`, `tracker\features.yaml`, `tracker\backlog.yaml`, `tests\guard`, `.githooks`, `.github\workflows\guard.yml`. Zero or several candidates, or something missing: STOP and list what you found. Read `README.md` and `RUNBOOK.md` if they sit next to `repo\`: they are background. Where they disagree with this prompt, this prompt wins (they were written for a repo that already had code).

A4. Install the rules (done when `docs\agent\08-task-protocol.md` exists in `$ROOT`).
~~~powershell
New-Item -ItemType Directory -Force "$ROOT\docs\upstream" | Out-Null
foreach ($f in "AGENTS.md","CLAUDE.md","GEMINI.md") { if (Test-Path "$ROOT\$f") { git mv "$f" "docs/upstream/old-$f" } }
robocopy "$SRC" "$ROOT" /E /XD __pycache__ .pytest_cache .cache /R:1 /W:1 /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -ge 8) { throw "bundle copy failed" }
New-Item -ItemType Directory -Force "$ROOT\tracker\.cache" | Out-Null
$ga = "$ROOT\.gitattributes"; if (-not (Test-Path $ga)) { New-Item $ga -ItemType File | Out-Null }
$have = Get-Content $ga
foreach ($l in "*.sh text eol=lf", ".githooks/* text eol=lf", "*.py text eol=lf", "*.toml text eol=lf", "*.yaml text eol=lf", "*.yml text eol=lf") { if ($have -notcontains $l) { Add-Content -Encoding ascii $ga $l } }
$gi = "$ROOT\.gitignore"; if (-not (Test-Path $gi)) { New-Item $gi -ItemType File | Out-Null }
$have = Get-Content $gi
foreach ($l in ".env", ".venv/", "node_modules/", "dist/", "data/couchdb/*", "!data/couchdb/local.ini", "__pycache__/", ".pytest_cache/", ".ruff_cache/", "tracker/.cache/", ".keysndocs/*", "!.keysndocs/Documentation/") { if ($have -notcontains $l) { Add-Content -Encoding ascii $gi $l } }
py -3 -c "import sys; assert sys.version_info >= (3, 11), sys.version; print(sys.version)"
py -3 -m pip install -r tools\requirements.txt
~~~
(`.keysndocs` is named for keys, so everything in it except `Documentation` stays out of git.) If Python is older than 3.11: STOP and tell me to run `winget install -e --id Python.Python.3.12`.

A5. Pin Pi, then check Pi is untouched (done when `tools\guard\upstream.lock.json` exists).
~~~powershell
py -3 tools\guard\pin_upstream.py --baseline (git rev-parse pi-baseline)
~~~
It must print `Files in ['packages'] that ALREADY differ from the baseline: 0`. Any other number: STOP (someone edited Pi) and show me the list.

A6. Check my docs are where the guard looks for them.
~~~powershell
Test-Path "$ROOT\.keysndocs\Documentation\Implementation Plans\LOCUS_FEATURE_LOGIC_DECOMPOSITION.md"
Test-Path "$ROOT\.keysndocs\Documentation\Implementation Plans\Implementation Report\Locus_Implementation_Tracker.xlsx"
Get-ChildItem -Recurse -File "$ROOT\.keysndocs\Documentation" | Select-String -Pattern 'sk-[A-Za-z0-9_-]{20,}','AIza[0-9A-Za-z_-]{30,}','gh[pousr]_[A-Za-z0-9]{30,}','xox[abprs]-[A-Za-z0-9-]{10,}','\b\d{8,10}:[A-Za-z0-9_-]{35}\b','AKIA[0-9A-Z]{16}' | ForEach-Object { "$($_.Path):$($_.LineNumber)" }
~~~
Both `Test-Path` must print `True`; if not, STOP and tell me where the file actually is (do not move my docs). The last command prints only locations: if it prints any line, STOP, give me those locations (never the text), and wait: I rotate the key and redact the line.

A7. Apply the one-shot setup patch. Write the script below EXACTLY as is to `tracker\.cache\setup_patch.py`, then run it. It removes the graphify rule from the rule files, rewrites the backlog for a repo with no code (the old US-01 "remove core/" becomes the skeleton story US-01 and the old US-02 is merged into it), records errata D-10 as decided (config lives in `LOCUS_HOME/config.yaml`; I accept the errata recommendation), turns every day into a slot day with 4-day sprints of 8 points so you can keep building, and adopts the top-level baseline (Pi's own files, `.keysndocs`, and the greenfield files `docker-compose.yml`, `.env.example`, `pyproject.toml`, `data`, `vault` and the usual caches). Each replacement asserts that it matched exactly once; on any mismatch it stops and you STOP and show me the message. Run it once: a second run fails on purpose.
~~~python
"""One-shot owner-authorized setup patch for a GREENFIELD Locus repo. Run once from the repo root:  py -3 setup_patch.py <YYYY-MM-DD>
Every replacement asserts it matched exactly once; on any mismatch it stops with an error and changes nothing further."""
import pathlib
import re
import sys

if len(sys.argv) != 2 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
    sys.exit("usage: setup_patch.py YYYY-MM-DD   (today, the first sprint start)")
TODAY = sys.argv[1]
ROOT = pathlib.Path(".")


def load(path):
    raw = (ROOT / path).read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), nl


def save(path, text, nl):
    (ROOT / path).write_bytes(text.replace("\n", nl).encode("utf-8"))


def sub(path, old, new):
    text, nl = load(path)
    n = text.count(old)
    if n != 1:
        sys.exit(f"PATCH FAILED: {path}: expected 1 match, found {n} for: {old[:70]!r}")
    save(path, text.replace(old, new), nl)
    print(f"ok  {path}: {old[:50]!r}")


# 1. Remove the /graphify condition everywhere it is a rule (the owner withdrew it).
sub("AGENTS.md",
    "4. `/graphify update .` in `5_Locus` and again in `5_Locus/locus-os` (the human's standing rule).\n5. Write `tracker/handoff/US-nn.md`",
    "4. Write `tracker/handoff/US-nn.md`")
sub("docs/agent/08-task-protocol.md",
    "9. **Graph.** `/graphify update .` in `5_Locus`, then again in `5_Locus/locus-os` (the owner's standing rule).\n10. **Handoff and stop.**",
    "9. **Handoff and stop.**")
sub("docs/agent/08-task-protocol.md", "After step 10 a fresh session", "After step 9 a fresh session")
sub("docs/agent/prompts/P1-implement-feature.md",
    ", then `/graphify update .` in `5_Locus` and\n  again in `5_Locus/locus-os`. Write `tracker/handoff/",
    ". Write `tracker/handoff/")
sub("docs/agent/prompts/P1-implement-feature.md", "from step 5 (Plan) to step 10 (Handoff)", "from step 5 (Plan) to step 9 (Handoff)")
sub("docs/agent/prompts/P6-autopilot-author.md",
    "6. `/graphify update .` is an interactive command that may not exist in this session. Run its command-line form if the machine has one. If you\n"
    "   cannot run it, write `graphify: NOT RUN (autopilot)` under \"Commands run\" in your handoff; the owner runs it before the demo. Never write that it ran when it did not.\n"
    "7. Commit on this branch",
    "6. Commit on this branch")

# 2. Greenfield backlog: US-01 becomes the skeleton (absorbing the Pi launcher); US-02 is removed; dependencies follow.
NEW_US01 = '''  - id: US-01
    epic: E1
    feature: F-0084
    slug: green-skeleton
    title: "Greenfield skeleton: the one layout (sidecar, locus-extension, locus_cli, docker-compose.yml) plus the Pi launcher, guard 0 FAIL"
    points: 3
    target_level: 3
    accept:
      - "py -3 tools/guard/check.py --full prints 0 FAIL. The guard's layout-required, must-define and pi-bridge-flags checks pass; nothing else in the repo changes outside the files this story creates."
      - "Created, each with real content and no stub: sidecar/__init__.py; sidecar/pi_bridge.py that DEFINES run_pi_turn and get_node_executable; locus-extension/ with a package.json and a src/ folder; locus_cli/__init__.py; a docker-compose.yml that parses as valid YAML (services may be empty: CouchDB arrives in US-03). Nothing under packages/ changes."
      - "run_pi_turn builds the Pi command line itself and always includes --approve and --no-context-files, and runs Pi with the repo root as working folder. A unit test with a fake Pi executable asserts exactly that; the string --dangerously-skip-permissions appears nowhere in the repo."
      - "A unit test asserts importlib.util.find_spec('core') is None and that no top-level folder named core, locus, locus-os or src exists. The handoff records the Pi release commit (tools/guard/upstream.lock.json baseline) it was built on."
    demo: 'Run py -3 tools\\guard\\check.py --full: it prints 0 FAIL. Look at the top level of locus-os: packages, sidecar, locus-extension, locus_cli and docker-compose.yml are there, and there is no core folder. Run the fake-Pi test file named in the handoff with py -3 -m pytest -q <that file>: it prints passed.'

'''
text, nl = load("tracker/backlog.yaml")
m = re.search(r"  - id: US-01\n.*?(?=  - id: US-03\n)", text, flags=re.S)
if not m or "  - id: US-02\n" not in m.group(0):
    sys.exit("PATCH FAILED: tracker/backlog.yaml: could not find the US-01/US-02 blocks")
text = text[:m.start()] + NEW_US01 + text[m.end():]
save("tracker/backlog.yaml", text, nl)
print("ok  tracker/backlog.yaml: US-01 replaced by the greenfield skeleton, US-02 removed")
sub("tracker/backlog.yaml", "    depends_on: [US-02, US-04, US-06]\n", "    depends_on: [US-01, US-04, US-06]\n")
text, nl = load("tracker/backlog.yaml")
if text.count("    depends_on: [US-02, US-06]\n") != 2:
    sys.exit("PATCH FAILED: tracker/backlog.yaml: expected 2 stories with depends_on [US-02, US-06]")
save("tracker/backlog.yaml", text.replace("    depends_on: [US-02, US-06]\n", "    depends_on: [US-01, US-06]\n"), nl)
print("ok  tracker/backlog.yaml: two dependents moved from US-02 to US-01")
# US-03 and US-04 need the skeleton to exist first.
sub("tracker/backlog.yaml",
    '    title: "CouchDB password comes from .env and every port binds to 127.0.0.1 (S-2)"\n    points: 1\n    target_level: 3\n    addendum: [P4]\n',
    '    title: "CouchDB password comes from .env and every port binds to 127.0.0.1 (S-2)"\n    points: 1\n    target_level: 3\n    addendum: [P4]\n    depends_on: [US-01]\n')
sub("tracker/backlog.yaml",
    '      - "The handoff says how an already-initialised data directory gets the new admin password (CouchDB applies COUCHDB_PASSWORD only when it creates the admin, so an existing data folder keeps the old one) and gives the exact commands; after them the previous login is rejected."\n',
    '      - "Greenfield: no data directory exists yet. The handoff still gives the exact commands for rotating the admin password on a data directory that already exists (CouchDB applies COUCHDB_PASSWORD only when it creates the admin), and says that a first install needs none."\n')
sub("tracker/backlog.yaml",
    '    title: "Telegram pairing: one-time code, fail closed, nobody becomes owner by messaging first (S-1)"\n    points: 2\n    target_level: 3\n    addendum: [P4]\n    accept:\n',
    '    title: "Telegram pairing: one-time code, fail closed, nobody becomes owner by messaging first (S-1)"\n    points: 3\n    target_level: 3\n    addendum: [P4]\n    depends_on: [US-01]\n    accept:\n'
    '      - "Greenfield: no Telegram gateway exists yet, so this story builds the smallest real one (long polling, token read through the secrets rules, only at the path `python tools/tracker/show.py F-0083` names) and the pairing in front of it. The six tests run against a fake Telegram transport. If this proves too big for 3 points, stop and say so: refinement splits it."\n')

# 3. Decision D-10: the owner decided it (the recommendation in the errata file).
sub("docs/agent/09-spec-errata.md", "| D-10 | OPEN | Where the `locus.*` config tree is stored |", "| D-10 | DECIDED | Where the `locus.*` config tree is stored |")
sub("docs/agent/09-spec-errata.md", "**D-10 Config location (OPEN).**",
    f"**D-10 Config location (DECIDED by the owner on {TODAY}: the recommendation below, unchanged).**")

# 4. Daily slots, one-week sprints, capacity for the greenfield start. The owner still runs acceptance, retro and sprint close.
sub("tracker/backlog.yaml", "  first_sprint_start: 2026-10-16", f"  first_sprint_start: {TODAY}")
sub("tracker/backlog.yaml", "  sprint_days: 14", "  sprint_days: 4")
sub("tracker/backlog.yaml", "  slot_days: [Mon, Tue, Fri]", "  slot_days: [Mon, Tue, Wed, Thu, Fri, Sat, Sun]")
sub("tracker/backlog.yaml", "  capacity_points: 4 ", "  capacity_points: 8 ")

# 5. Top-level baseline: adopt what exists now (Pi's own files, .keysndocs), then pre-adopt the greenfield files the layout itself requires or
#    that normal work creates, so agents are not blocked by the guard on day one. Anything else new at the top level still FAILS.
import subprocess
import tomllib
r = subprocess.run([sys.executable, "-I", "tools/guard/check.py", "--adopt-top-level"], capture_output=True, text=True)
if r.returncode not in (0, 1):
    sys.exit("PATCH FAILED: check.py --adopt-top-level:\n" + r.stdout + r.stderr)
text, nl = load("tools/guard/guard.toml")
m = re.search(r"^allowed_top_level = \[(.*?)\]\s*$", text, flags=re.M)
if not m:
    sys.exit("PATCH FAILED: tools/guard/guard.toml has no allowed_top_level line after --adopt-top-level")
have = [x.strip().strip('"') for x in m.group(1).split(",") if x.strip()]
for extra in (".dockerignore", ".env.example", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__", "data", "docker-compose.yml", "node_modules", "pyproject.toml", "vault"):
    if extra not in have:
        have.append(extra)
text = text[:m.start()] + "allowed_top_level = [" + ", ".join('"%s"' % x for x in sorted(have)) + "]" + text[m.end():]
save("tools/guard/guard.toml", text, nl)
assert "docker-compose.yml" in tomllib.loads(text)["layout"]["allowed_top_level"]
print("ok  tools/guard/guard.toml: top-level baseline adopted (+ greenfield files)")
print("SETUP PATCH COMPLETE")
~~~
~~~powershell
py -3 -I tracker\.cache\setup_patch.py $TODAY
py -3 tools\tracker\backlog.py --check
~~~
`backlog --check` must print `0 ERROR` (WARN about stories that are not Ready is normal).

A8. Prove the tools work on this PC, then commit the install. Hooks stay OFF until the guard is green.
~~~powershell
py -3 -m pytest -q tests\guard
py -3 tools\guard\check.py --only secrets,gitignore --all
~~~
All tests must pass and `secrets` must print no FAIL. A failing test or a secrets FAIL: STOP and show me the first five lines verbatim (names and locations of secrets only). If the Windows run exposes a defect in the tools themselves, report it; never edit the tools to make a test pass.
~~~powershell
$env:LOCUS_ALLOW_GUARD_EDIT = "1"
try {
  git add AGENTS.md CLAUDE.md .githooks .github docs tools tracker tests .gitattributes .gitignore
  git commit -m "chore(guardrails): add agent rules, guard, board and evidence tracker for a greenfield repo"
  git add ".keysndocs/Documentation"
  git commit -m "docs: add the owner's documentation folder"
} finally { Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT -ErrorAction SilentlyContinue }
git update-index --chmod=+x .githooks/pre-commit .githooks/pre-push
git commit -m "chore(guardrails): mark hooks executable" --allow-empty
git status --short
~~~
`git status --short` must print nothing.

A9. First honest measurement.
~~~powershell
py -3 tools\guard\check.py --full --all
py -3 tools\tracker\verify.py --static
py -3 tools\tracker\export_xlsx.py
Get-Content tracker\STATUS.md -TotalCount 12
~~~
Expected on a fresh Pi clone: exactly SIX guard FAILs, all "skeleton missing" (`layout-required` for `sidecar`, `locus-extension`, `locus_cli`, `sidecar/__init__.py`, `docker-compose.yml`, and `must-define` for `sidecar/pi_bridge.py`). Any other FAIL: STOP and show me. The verified average will be low (only the features inherited from Pi count): that is the honest starting number, report it. The old workbook is copied to `tracker\legacy\replaced-*.xlsx` and `$SAFE` holds the original too. Then commit the tracker:
~~~powershell
git add tracker ".keysndocs/Documentation/Implementation Plans/Implementation Report/Locus_Implementation_Tracker.xlsx"
git commit -m "chore(tracker): first honest measurement on the greenfield repo"
~~~

A10. Plan Sprint 1. You may run `--plan --write` yourself (my delegation). Read the plan first: it must take US-01 and US-05 (D-10 is decided; the others wait for their dependencies).
~~~powershell
py -3 tools\tracker\backlog.py --plan
$env:LOCUS_ALLOW_GUARD_EDIT = "1"
try { py -3 tools\tracker\backlog.py --plan --write } finally { Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT -ErrorAction SilentlyContinue }
git add tracker/sprints.jsonl
git commit -m "docs(agile): sprint 1 plan"
py -3 tools\tracker\backlog.py
~~~
The board must now say `START US-01`. Phase A is finished. Say so in one line and give the canary (`blue-heron-47`) as proof that you loaded the new `AGENTS.md`.

# PHASE R: resume and reassess (the guardrails are installed and work already exists)
Earlier sessions, other models and I may have written code, handoffs, evidence and claims, and rule files may have been touched. Nothing counts until a command you ran in THIS run says so, including every "done" in the tracker. Report what R finds before you plan anything. There are two depths.
- DEPTH 1 (every run that finds progress): R0 to R6.
- DEPTH 2, FULL REASSESSMENT: after depth 1, when I wrote `REASSESS` in the goal, or when no `tracker\handoff\REASSESS-*.md` exists yet and the tracker shows any story merged or any feature above L2. It re-checks every feature, not only recent work (F1 to F8). New stories wait until it is finished, unless R2 or F1 found nothing blocking and I said `SKIP-REASSESS`.

DEPTH 1
R0. Are the rules themselves intact? The bundle copy in `$AGENTS` is the reference (find `$SRC` as in A3; the setup commit is `git log --format=%h --grep="add agent rules" --reverse` first line). `git diff --no-index --stat "$SRC\tools" tools`, the same for `tests\guard`, `docs\agent`, `.githooks`, `.github\workflows` and the two files `AGENTS.md`, `CLAUDE.md`. Expected differences are only those of the setup patch (graphify removal, US-01, D-10, slots, `guard.toml` top-level list) and my own recorded edits (`git log --format="%h %ad %s" -- <human-owned paths>`: every commit there must say why). Anything else is tampering or drift: list it, do NOT repair it (restoring is mine: `git checkout <commit> -- <file>`). Then: `git config core.hooksPath` (must be `.githooks` once the guard is green), `py -3 -m pytest -q tests\guard`, and print every entry of `tracker\overrides.yaml`, `tracker\spec_exclusions.yaml` and `tracker\signoff.yaml` with its git blame date and author: those three can inflate or hide progress, so I check each line myself. `git diff <setup commit> HEAD -- tracker\features.yaml` must show no deleted or weakened evidence line (add-only): list any that is.
R1. State of git: `git status --short`, `git branch --show-current`, `git branch --list "task/*"`, `git log --oneline -30`, `git stash list`. A dirty tree or an unknown branch: do not clean it up; list it and follow the board or ask me.
R2. Recompute, never read: `py -3 tools\guard\check.py --full --all` (this compares `packages\` with the pinned Pi baseline), `py -3 tools\tracker\verify.py` (it runs the tests), `py -3 tools\tracker\export_xlsx.py`. Compare `tracker\STATUS.md` with the previous entries of `tracker\history.jsonl`. Every guard FAIL, every feature that went DOWN, every `PROOF_STALE` or `SIGNOFF_STALE`, every difference in `packages\` goes to the top of your report and is fixed before new work (through a story: the board names it, or you append a fix story at the bottom and report it).
R3. For every story at REVIEW or DONE: re-run the test files its handoff names and its demo command; check each `accept` line in `tracker\backlog.yaml` against the code and the output, one by one, and quote the output. A handoff sentence with no matching output counts as NOT PROVEN.
R4. For every story at DOING, VERIFY or REWORK: do not trust "Files changed" in the handoff: run `git diff --stat main...task/<branch>` and compare. Look for what the guard cannot see: a test with no real assertion, a test or assertion removed or loosened (`git diff main...<branch> -- tests`), `STUB`, `TODO` or `pass` in shipped code, a hard-wired provider, port, path or model, a shim, a second module doing the same job.
R5. Spec drift: for each feature touched since the last sprint start, `py -3 tools\tracker\show.py F-xxxx --spec` against what the code does. List every spec sentence not implemented and every behaviour in the code that is not in the spec.
R6. Report, short and blunt: proven (with the command), claimed but not proven, broken, and what you would discard (path, why, replaced by, who imports it; you delete nothing before I say "discard rows ..."). If DEPTH 2 does not apply, go on with PHASE C from the board, unless R2 found something that blocks it.

DEPTH 2: FULL REASSESSMENT (write the findings to `tracker\handoff\REASSESS-<date>.md` and commit that file with the progress after each feature, so a killed run resumes where it stopped; its first lines are `# REASSESS <date> - <your exact model name>` and the commit it was run on)
F1. Freeze the facts: `git rev-parse HEAD`, the guard summary, the full `verify.py` summary lines, the count of features per level. Quote them. Every later claim is compared with these.
F2. Claims against computation: for EVERY feature in `tracker\status.json` list level, flags (`OVERCLAIM`, `VACUOUS_TESTS`, `CLAIMED_FILES_MISSING`, `NO_FILES_NAMED`, `SPEC_CHANGED`, `LOW_CONFIDENCE_MAPPING`, `CAPPED_BY_HUMAN`) and what evidence the level rests on. Order the features by risk: PROVEN and INTEGRATED first, then UNIT_VERIFIED, then the rest.
F3. Attack the tests, feature by feature in that order. For a feature at L3 or above: read the test file; then prove the test can fail: `git worktree add tracker\.cache\wt-<F-id> HEAD`, break the feature in THAT copy on purpose (delete or change the one behaviour the spec sentence names), run only that test there, and write whether it FAILED (good) or still PASSED (the test is vacuous: say so), then `git worktree remove --force tracker\.cache\wt-<F-id>`. Never mutate the real working tree, never use `git stash`. A test that cannot run in a worktree (missing dependencies, real keys, network): NOT CHECKED, with the reason. Log one table row per feature: feature, test, what you broke, result.
F4. Spec check: for each feature in the order of F2, `show.py F-xxxx --spec`; list the spec sentences with no code and no test, and the code with no spec sentence.
F5. Whole-repo sweep, once: duplicates (two files doing the same job, parallel config systems, two installers, two copies of a prompt or doc), shims and aliases, stubs and fake data in shipped code, hard-wired hosts, ports, paths, models and timezones, `os.environ` or `process.env` outside the config accessor, secret-shaped strings, ports bound to `0.0.0.0`, every runtime Pi launch without `--approve --no-context-files`, anything the spec says Locus must not do (a bespoke agent loop, Git or Syncthing sync, edits under `packages\`), vault folder names, and every modularity piece (interface, `enabled` switch, off behaviour, swap test, health check) per feature at L2 or above. Each finding has file and line.
F6. The other model family: when the autopilot preconditions of phase C section 3 hold, ask the OTHER family to run the P0 audit read-only (`py -3 tools\tracker\backlog.py --prompt P0`); otherwise print the clipboard line so I can run it in a Gemini session. Its report is `tracker\handoff\P0-audit-<model>.md`. Where the two reports disagree, the one that quotes a command or a file and line wins.
F7. Turn findings into work, never into inline fixes: every confirmed defect becomes a fix story appended at the bottom of `tracker\backlog.yaml` (feature, slug, points 1 to 3, `accept` lines that quote the failing command, `demo`), named in the report; blockers (guard FAIL, a feature that went down, a secret, an edit under `packages\`) go first in your recommendation. I order the backlog. A vacuous test is fixed by a new real test added as evidence in a story, never by editing the old one away. A feature whose claim is wrong gets its level from `verify.py`, never from you; if you think a level must be capped, say so and I decide in `tracker\overrides.yaml`.
F8. Finish the file with these headings: Summary (10 lines), Facts frozen, Rules integrity (R0), Claims vs computed, Test attack table, Spec gaps, Sweep findings, Discard table, Fix stories added, Not checked, Questions for me. Count of features checked out of the total, and the number of files you actually opened. Tracker refresh and commit as in phase C section 2. Then PHASE D. If features remain unchecked when the run must stop, say how many and that the next run continues from the table. When every feature is checked, say so, and only then go on with PHASE C.

# PHASE B: understand the project and the codebase (read-only; write no file)
(If you came from phase R, read only what the next story needs.) Read in this order, with this policy: a file up to about 40 KB, whole; a larger one, its headings, its first 150 lines, and a search for decisions and requirements. Never read the 8,000-line spec or the whole of `tracker\features.yaml` (AGENTS.md says so): use `py -3 tools\tracker\show.py F-xxxx --spec`.
1. My docs: list `.keysndocs\Documentation` with sizes, then read `Ideas and System`, `Chat Reports\6_October`, `Chat Reports`, and in `Implementation Plans` everything except the spec. For the spec: its `## ` headings and its first 150 lines only.
2. The rules: `docs\agent\01`, `02`, `03`, `09` (the index and every OPEN row), `11`, and `08` in full; `04`, `05`, `06`, `07`, `10` when a story touches them (AGENTS.md has the map).
3. The Pi codebase (the base I build on): the root `README.md`, `packages\coding-agent\README.md`, and in `packages\coding-agent\docs`: `how-pi-works.md`, `extensions.md`, `cli.md`, `rpc.md`, `sdk.md`, `configuration.md`, `security.md`; plus one line per folder of `packages\*` from its `package.json`. Pi's own dev rules are `docs\upstream\old-AGENTS.md`: reference only.
4. The tracker: `tracker\STATUS.md`, the board (`py -3 tools\tracker\backlog.py`), and `show.py` for the features of the stories in Sprint 1.

Then give me ONE understanding report, 40 lines at most, every claim tied to a file and line or to command output, no flattery:
- how Locus sits on top of Pi: what Pi already gives (which tracker features are `INHERITED_OK`), what goes in `locus-extension\` and what in `sidecar\`, and how a Telegram message would travel end to end;
- the layout as it is now (one tree), and what is missing;
- the honest tracker numbers from `STATUS.md`;
- every contradiction or gap you found between my docs, the spec, the errata and the Pi code, and everything in this prompt or the bundle you think is wrong. Disagree openly;
- the first story, and the questions you cannot answer yourself.

# PHASE C: build, keep the tracker true, and do not stop until something needs me
## 1. The loop
The board orders my backlog; every story names its tracker feature, and the spec section of that feature is the only definition of what to build (`py -3 tools\tracker\show.py F-xxxx --spec`). Build nothing the spec and the story do not name. Run `py -3 tools\tracker\backlog.py` and do exactly what NEXT ACTION says, by state. After every action run the board again. Stop only for a reason in section 5.
Grill (law 13) for a story: ask me only what the spec, the errata and the code cannot answer. Nothing to ask: write "No questions" under Plan in the handoff and go on. A question: ask it with `/grill-me` (one at a time, with your recommended answer) and STOP for my answer; never assume one, and never code before it.

| Board state | What you do |
|---|---|
| TURN THE HOOKS ON NOW | `git config core.hooksPath .githooks` (once, ever; my delegation). |
| TODO: START US-nn | `py -3 tools\tracker\backlog.py --start US-nn`, then read `tracker\.cache\prompt-US-nn-P1.md` and follow it as your task (you are the author, on branch `task/US-nn-<slug>`). If the story is not `autopilot: false` and every precondition of 3 holds, run the autopilot instead (section 3). |
| DOING | You or a previous session started it and the handoff is missing: continue on the same branch with `py -3 tools\tracker\backlog.py --prompt P1 US-nn`. |
| VERIFY | A different model family must check it. See section 3. Never verify your own story. |
| REWORK | Read `tracker\handoff\US-nn-verify.md` and fix exactly the numbered findings, nothing else; then verify again with a fresh session of the other family. |
| MERGE | Run exactly the commands the board prints, in order (verdict commit only if it is not committed yet; guard `--full`; `git switch main`; `git merge --ff-only`; delete the branch; `verify.py`; `export_xlsx.py`). Then the tracker commit of section 2. |
| REVIEW | Merged, waiting for me. Do not accept. Go to the next story that is Ready. |
| REFINEMENT | See section 4. |
| ANOMALY | Run what the board prints, or stop if it asks for a decision. |

## 2. Tracker autonomy: you keep it true, I never type in it
Evidence rules are in `docs\agent\07-tracker-evidence.md`. Do all of this without being asked:
- While building: add test evidence for the feature to `tracker\features.yaml` (add only, never delete or weaken a line).
- At the end of every story, every merge, and before every stop:
~~~powershell
py -3 tools\tracker\verify.py --only F-xxxx
py -3 tools\tracker\verify.py
py -3 tools\tracker\export_xlsx.py
git add tracker ".keysndocs/Documentation/Implementation Plans/Implementation Report/Locus_Implementation_Tracker.xlsx"
git commit -m "chore(tracker): refresh after US-nn"
~~~
(On a story branch the same commands run before the handoff; after a merge they run on `main`.) If `verify.py` reports a feature that went DOWN (`REGRESSION`), or the guard shows FAIL, stop and report it first.
- Each story's handoff (`tracker\handoff\US-nn.md`, all nine headings, first line `# US-nn handoff - <your exact model name>, <date>`) holds the real command output. A statement that is not backed by output is marked `NOT RUN`.
- The workbook at `.keysndocs\Documentation\Implementation Plans\Implementation Report\Locus_Implementation_Tracker.xlsx` is generated and tamper-hashed. It is how I see progress; it is never edited.

## 3. Verification by the other model family
Unattended verification works only through the headless Antigravity CLI. Use the autopilot (`py -3 tools\tracker\autopilot.py ...`) only when ALL of these hold; otherwise use the manual path below.
- `agy --version` works and `agy models` lists a Claude-family and a Gemini-family model (set `$AUTHOR` to the newest Claude Sonnet or Opus slug and `$VERIFIER` to the newest Gemini Pro slug, copied exactly from `agy models`; unsure which: ask me).
- `main` has a guard run with 0 FAIL, the hooks are on, and `$env:LOCUS_ALLOW_GUARD_EDIT` is not set. (The autopilot refuses to start on a red guard. That is why US-01, which turns the guard green, is written by you in this session.)
- The agy permission allow-list exists: `%USERPROFILE%\.gemini\antigravity-cli\settings.json` must contain exactly this block (merged into whatever else is there). It has no push, reset, clean, switch, curl, docker, ssh or Remove-Item. If the file lacks it, print this JSON and stop: that file is mine, do not edit it.
~~~json
{
  "permissions": {
    "allow": [
      "command(regex:^git (status|diff|log|show|add|commit|rev-parse|ls-files|mv|rm|branch --show-current)( .*)?$)",
      "command(py)",
      "command(python)",
      "command(regex:^npm (test|run (build|lint|test|typecheck))$)"
    ]
  }
}
~~~
- This prints nothing (no key-like file is inside the folder the sessions can read; names only, never content): `git ls-files -co | Where-Object { $_ -notmatch '(^|/)node_modules/' -and $_ -match '(^|/)(\.env(\.local|\.prod|\.production)?|credentials[^/]*|secrets?\.[^/]*)$|\.(pem|key)$' }`. Anything in `.keysndocs` that it prints: tell me to move it to `%USERPROFILE%\.locus\`, and do not run the autopilot until I have.
- `git status --short` prints nothing.

Autopilot run. Hide the keys file, run, and always restore it:
~~~powershell
$envf = "$env:USERPROFILE\.locus\.env"
if (Test-Path $envf) { Rename-Item $envf ".env.off" }
try { py -3 tools\tracker\autopilot.py --author-model $AUTHOR --verifier-model $VERIFIER --max-steps 12 --max-minutes 240 }
finally { if (Test-Path "$envf.off") { Rename-Item "$envf.off" ".env" } }
py -3 tools\tracker\backlog.py
~~~
Never add `--dangerously-skip-permissions`. The first run after setup is `--dry-run`, then `--max-steps 1`, and you stop after it so I can look. Exit code 0 means the autopilot stopped at a gate that is mine (read what it printed, give me the next action); 1 means something unexpected (show the last 5 lines of `tracker\.cache\autopilot.log`); 2 means it refused to start (the printed reason says which precondition failed; fix it if it is in your list, else stop). It stops at `US-nn-questions.md`: that file's `Answer:` lines are mine.

Manual path (no `agy`, or a precondition failed): finish the author step, write the handoff, run the commands of section 2, and STOP at VERIFY. Print: the story, the branch, the command `py -3 tools\tracker\backlog.py --prompt P2 US-nn`, the clipboard line the board prints, and the instruction "new session of the OTHER model family, same branch, canary first, paste". The verdict file `tracker\handoff\US-nn-verify.md` comes from that session. I do not install `agy` for you: the install is a downloaded script, so it is my step (RUNBOOK, section AUTOPILOT A).

Pi must be built before any story that runs the real Pi (US-01's tests use a fake Pi executable). A story that needs the build says so in its Plan; building Pi is `npm install` and `npm run build` in the repo root: do not run it on your own; list it in the stop report.

## 4. Delegations and what stays mine
You may, on your own: `--start`, `--prompt`, `--check`, `--calendar`, `--plan --write` (command-scoped owner variable, then `git add tracker/sprints.jsonl`, commit), the hooks command, the merge commands the board prints, and the REFINEMENT work below.
REFINEMENT (the board announces it on the second-to-last slot day): `py -3 tools\tracker\backlog.py --refine`; use the P5 prompt it writes to complete the stories at the top that are not Ready: add `accept`, `demo`, `points`, `depends_on`, `target_level`, nothing else. You may append a story at the bottom for a tracker feature that no story covers (P5 does this), and you name it in the report. Never reorder the backlog, never drop or merge a story, never change a decision's status, never set `autopilot: false` or true. Questions P5 raises that the spec cannot answer go to me through the grill. Then `py -3 tools\tracker\backlog.py --check` must print `0 ERROR`, and you commit `tracker\backlog.yaml` and `docs\agent\09-spec-errata.md` with the owner variable set only for that one commit.
Mine alone: `--accept`, `--retro`, `--close-sprint`, `record_proof.py` and `tracker\signoff.yaml`, every OPEN decision, a 100% on any feature, the order of the backlog, `tools\guard\guard.toml` changes after phase A, anything in `.keysndocs` except `Documentation`, installing software, and real keys, VM, bot or accounts.

## 5. When you must stop (stop cleanly, finish what is safe, then report)
- A story is at REVIEW and nothing else is Ready, the sprint's last slot day has come, or the board says acceptance or retro is due.
- VERIFY and the autopilot preconditions fail; or a verifier asked for rework twice (the board and autopilot say when).
- An OPEN decision row is touched, the spec is silent or contradicts itself, a story needs a change in `packages\`, a new top-level entry, a new port, a new dependency, or more than about 10 files.
- A step needs my keys, my VM, my Telegram bot, Docker with real data, or the network beyond package installs.
- The guard shows a FAIL you cannot fix inside the story, a secret appears, `packages\` differs from the pinned baseline, or a feature went down.
- A full reassessment has been running for about 3 hours or you are running out of context: commit the progress table and stop.
- You catch yourself writing "should work", "probably" or "for now": mark the line `STUB(F-xxxx)` or stop.
Never half-finish silently. Never start a second story while one is not merged (WIP limit 1).

# PHASE D: the stop report, then the grill
Every stop ends with this report, in this order, short:
1. The tracker, quoted from `tracker\STATUS.md` (average verified level, count per level, features that moved and why), and the path of the workbook.
2. The board's state for every story in the sprint (the board's words, not yours).
3. What I must do now, as exact commands I can paste (for example `$env:LOCUS_ALLOW_GUARD_EDIT="1"; py -3 tools\tracker\backlog.py --accept US-01 --note "what I saw"; Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT`), together with the demo text of each story waiting for acceptance, so I can watch it.
4. Anything you did under a delegation, anything you decided, and anything you disagree with.
5. Then run `/grill-me` on me, one question at a time, each with your recommended answer and why. First the questions that block the next story; then the four-pillar decisions in order D-1, D-3, D-4, D-5, then D-13, D-15, D-16, D-9, with the options and the recommendation written in `docs\agent\09-spec-errata.md`. I answer; you record each answer by editing the row's status in the errata file and committing with the owner variable, only after I have said the exact words "decided". If there is nothing to ask, say "No questions" and stop.

Start now with phase A. Your first line: your exact model name, and "phase A, step A0".
