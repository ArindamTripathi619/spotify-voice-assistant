# 10 — Context Index

Entry point for this knowledge base. Read this first, then follow the link you need.

## Start Here

| If you want to… | Read |
|---|---|
| Understand what this project is in 3 minutes | [00 — Project Overview](00_PROJECT_OVERVIEW.md) |
| Know where every file is | [01 — Repository Map](01_REPOSITORY_MAP.md) |
| Understand how the pieces fit | [02 — Architecture](02_ARCHITECTURE.md) |
| **See the architecture as pictures** | [14 — Architecture Diagrams](14_ARCHITECTURE_DIAGRAMS.md) |
| Look up a specific class/function | [03 — Module Reference](03_MODULE_REFERENCE.md) |
| Trace what happens when a command is spoken | [04 — Data Flows](04_DATA_FLOWS.md) |
| Know exactly what works and what does not | [11 — Features & Capabilities](11_FEATURES_AND_CAPABILITIES.md) |
| **Diagnose something that broke** | [12 — Caveats & Limitations](12_KNOWN_CAVEATS_AND_LIMITATIONS.md) |
| **Install, run, or recover the project** | [13 — Runbook](13_RUNBOOK.md) |
| Configure it / fix a setup failure | [05 — Configuration & Environment](05_CONFIGURATION_AND_ENV.md) |
| Understand the (absent) quality story | [06 — Testing & Quality](06_TESTING_AND_QUALITY.md) |
| **See the bugs** | [07 — Findings & Issues](07_FINDINGS_AND_ISSUES.md) |
| Know what was and was not investigated | [08 — Exploration Ledger](08_EXPLORATION_LEDGER.md) |
| Look up a term | [09 — Glossary](09_GLOSSARY.md) |

## Knowledge Base Contents

| Doc | Contents |
|---|---|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Identity, problem, feature-vs-reality table, stack, architecture at a glance, all commands, key limitations |
| [01_REPOSITORY_MAP.md](01_REPOSITORY_MAP.md) | Directory tree, 31-file inventory table with per-file status, module boundaries, import-direction diagram |
| [02_ARCHITECTURE.md](02_ARCHITECTURE.md) | Layered-monolith analysis, dependency graph, pattern inventory (present/absent), lifecycle sequence diagram, state machine, architectural debt |
| [03_MODULE_REFERENCE.md](03_MODULE_REFERENCE.md) | Per-module public/private surface, the 9-rule dispatch table with verified results, external integration contracts |
| [04_DATA_FLOWS.md](04_DATA_FLOWS.md) | 7 flows (startup, voice cycle, text mode, calibration, request amplification, notifications, health check), application state machine, error-propagation map |
| [05_CONFIGURATION_AND_ENV.md](05_CONFIGURATION_AND_ENV.md) | Precedence order, `.env` contract, every runtime path, declared-vs-imported dependencies, full env-var matrix, build-system status |
| [06_TESTING_AND_QUALITY.md](06_TESTING_AND_QUALITY.md) | Absence of all quality infrastructure, health-check deep dive with reproduced output, testability barriers, methodology used here, coverage matrix, remediation priorities |
| [07_FINDINGS_AND_ISSUES.md](07_FINDINGS_AND_ISSUES.md) | **48 findings** (D1–D56; 8 retired: D11/D14/D23/D32/D35/D37/D41/D54) by severity with evidence labels and file:line references; **7 explicit retractions** and a **second-pass correction log** of claims the first draft asserted without evidence; prioritised remediation order |
| [08_EXPLORATION_LEDGER.md](08_EXPLORATION_LEDGER.md) | Coverage metrics, per-file ledger for all 31 files, explicit exclusions, methodology, **known gaps** |
| [09_GLOSSARY.md](09_GLOSSARY.md) | Project, recognition, audio, Spotify, security, filesystem, notification, and meta terminology; a "frequently confused" table |
| [10_CONTEXT_INDEX.md](10_CONTEXT_INDEX.md) | This file — entry point, reading order, and task→doc routing |
| [11_FEATURES_AND_CAPABILITIES.md](11_FEATURES_AND_CAPABILITIES.md) | Every feature graded ✅/⚠️/🐛/💀/👻/🧪 against the code; the full 9-rule routing table with reproduced bugs; what is deliberately absent |
| [12_KNOWN_CAVEATS_AND_LIMITATIONS.md](12_KNOWN_CAVEATS_AND_LIMITATIONS.md) | **Symptom → cause index**, then caveats grouped by install / startup / runtime / security / platform / diagnostics / doc-gap; triage flowchart; things that are *not* caveats |
| [13_RUNBOOK.md](13_RUNBOOK.md) | Prerequisites, the reliable install path (not `setup.sh`), Spotify app setup, run modes, first-run sequence, command cheat sheet, filesystem layout, troubleshooting, recovery, uninstall, hardening |
| [14_ARCHITECTURE_DIAGRAMS.md](14_ARCHITECTURE_DIAGRAMS.md) | **14 Mermaid diagrams** — system context, components, lifecycle, voice flow, dispatch, state, filesystem, notifications, playback, token persistence, error flow, reachability, platform matrix, legend |

## The Eight Things That Matter Most

1. **Two documented commands are broken.** `"what's playing"` searches Spotify for a track
   named `"ing"` and plays it; `"goodbye"` resumes playback instead of quitting. Both were
   **reproduced by execution**, and both are caused by substring matching in
   `app/assistant.py:238-274`. → [D5, D6](07_FINDINGS_AND_ISSUES.md)
2. **The diagnostic that reports missing dependencies cannot start when dependencies are
   missing** (reproduced: `python -m app.health_check` → `ModuleNotFoundError`), because `app/__init__.py` imports everything eagerly. → [D2](07_FINDINGS_AND_ISSUES.md)
3. **A clean clone cannot be set up on Linux or macOS** — `env/.env.template` does not exist
   and `setup.sh` runs under `set -euo pipefail`, so both fail at the `cp`.

   **Correction (second pass):** the two are *not* equivalent, and an earlier draft of this
   knowledge base said they were. `setup.sh:63` copies **unconditionally** and is the last step
   of the script, so it fails *after* the installs have completed — the user gets a working
   environment and a non-zero exit. `universal_setup.sh:112` prompts first
   (`read -p "Create env/.env file from template? [Y/n]"`, defaulting to `Y`) and only reaches
   `cp` at `:115` if the user answers `Y` — so answering `n` makes it survive. The correct
   framing is "two Linux installers break on a missing template in different ways", not
   "both abort before prompting".
   Windows handles this correctly, which is why the two platforms behave differently. → [D3, D4, D21](07_FINDINGS_AND_ISSUES.md)
4. **Token persistence is broken by a one-word naming error.** `SecureTokenStorage` implements
   `save_token_to_cache()` where spotipy's `cache_handler` protocol requires **`save_to_cache()`**.
   It is wired in as the handler, so the first token save should raise `AttributeError`. Found by
   comparing a *contract* against its *consumer*, not by reading the class in isolation. Needs one
   live OAuth run to confirm the exact exception. → [D40](07_FINDINGS_AND_ISSUES.md)
5. **All tuned recognizer settings are discarded.** `setup_enhanced_audio()` sets 8 attributes on
   `self.recognizer`; both `listen_*` methods build their own local recognizer. Ambient
   adaptation *does* work (0.2 s) — the tuned and persisted state does not. And
   `adjust_sensitivity()` is a no-op: no loop, and its guard is permanently false.
   → [D7, D8](07_FINDINGS_AND_ISSUES.md)
6. **Three documented recovery features do not exist.** Automatic text-mode fallback (nothing but
   SIGINT ever sets `switch_to_text_mode`); spoken TTS (`speak()` has zero call sites); automatic
   sensitivity adjustment. → [D27, D28, D29](07_FINDINGS_AND_ISSUES.md)
7. **Two whole subsystems are unreachable** — `config.py` (286 lines, zero inbound imports) and
   `error_handling.py` (308 lines, `handle_error` called once, 7 exception classes and the
   decorator entirely unused). ~600 of 2,627 LOC. → [D17, D18](07_FINDINGS_AND_ISSUES.md)
8. **There are zero tests, zero CI, zero linting, and zero type checking.** Items 1–7 are all
   trivially detectable with a table-driven test on `process_command`. → [D33](07_FINDINGS_AND_ISSUES.md)

## Findings by Severity

| Severity | Count | IDs |
|---|---|---|
| **S1 Critical** | 3 | D2, D3, D40 |
| **S2 High** | 14 | D5, D6, D7, D8, D9, D10, D12, D16, D17, D22, D24, D27, D28, D33 |
| **S3 Medium** | 21 | D4, D13, D15, D18, D19, D20, D21, D25, D26, D29, D30, D31, D34, D36, D38, D39, D42, D43, D44, D45, D56 |
| **S4 Low** | 9 | D46, D47, D48, D49, D50, D51, D52, D53, D55 |
| **Subtotal — live findings** | **47** | 3 + 14 + 21 + 9 |
| **Retracted** | 8 + 2 partial | D11 (→D18), D14, D23, D32, D35, D37, D41, **D54**; partial: D24(b), D34 |
| **Delivery blocker** | 1 | **D1** — `docs/` was git-ignored, so this knowledge base was absent from every fresh clone |
| **Headline total** | **48** | 47 live findings + D1 |

D23 appears in [07 § Explicit retractions](07_FINDINGS_AND_ISSUES.md) and is **not** counted as
live. D55 is S4 Low and holds a single canonical home in the S4 prose; D56 is S3 Medium and
appears in the S3 table only.

**D1 is not a code finding.** It is a delivery blocker, and it is now **fixed**: `docs/` has been
removed from `.gitignore`, so this documentation is trackable. Issue #4 stays open until the
change is committed.

Full table with evidence class for each: [07_FINDINGS_AND_ISSUES.md](07_FINDINGS_AND_ISSUES.md)

## Quick Reference — Commands

```bash
# Run
python -m app.main                       # the assistant (primary)

# Diagnose  — ⚠️ crashes with ModuleNotFoundError if deps are missing (D2)
python -m app.health_check               # equivalent to `python -m app`

# Configure — ⚠️ README/QUICKSTART say `.env` at the root; that is wrong (D4)
mkdir -p env && printf 'SPOTIFY_CLIENT_ID=...\nSPOTIFY_CLIENT_SECRET=...\n' > env/.env

# Install
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# There is no test command, linter, formatter, or type checker (D33).
```

## By Task

| Task | Go to |
|---|---|
| Fix the command router | [03 §`process_command` dispatch table](03_MODULE_REFERENCE.md), [11 §F-1](11_FEATURES_AND_CAPABILITIES.md), [14 §D-6](14_ARCHITECTURE_DIAGRAMS.md), [D5](07_FINDINGS_AND_ISSUES.md), [D6](07_FINDINGS_AND_ISSUES.md) |
| Make `health_check` usable | [D2](07_FINDINGS_AND_ISSUES.md), [06 §Reproduced execution](06_TESTING_AND_QUALITY.md) |
| Fix installation | [D3](07_FINDINGS_AND_ISSUES.md), [05 §The `.env` contract](05_CONFIGURATION_AND_ENV.md) |
| Add token encryption | [D16](07_FINDINGS_AND_ISSUES.md), [D15](07_FINDINGS_AND_ISSUES.md), [05 §Runtime Filesystem State](05_CONFIGURATION_AND_ENV.md) |
| Wire up or delete the config layer | [D17](07_FINDINGS_AND_ISSUES.md), [05 §env-var matrix](05_CONFIGURATION_AND_ENV.md) |
| Wire up or delete the error layer | [D18](07_FINDINGS_AND_ISSUES.md) |
| Fix audio quality | [D7](07_FINDINGS_AND_ISSUES.md), [D8](07_FINDINGS_AND_ISSUES.md), [04 §F2](04_DATA_FLOWS.md) |
| Fix the notification channel | [D9](07_FINDINGS_AND_ISSUES.md), [04 §F6](04_DATA_FLOWS.md) |
| Write the first tests | [06 §Testability Assessment](06_TESTING_AND_QUALITY.md), [06 §Recommended Test Priorities](06_TESTING_AND_QUALITY.md) |
| Know what works | [11 — Features](11_FEATURES_AND_CAPABILITIES.md), [00 §Feature status](00_PROJECT_OVERVIEW.md) |
| Diagnose a failure | [12 — Caveats](12_KNOWN_CAVEATS_AND_LIMITATIONS.md) |
| Install / run / recover | [13 — Runbook](13_RUNBOOK.md) |
| Show someone the architecture | [14 — Diagrams](14_ARCHITECTURE_DIAGRAMS.md) |
| Correct the documentation | [D27–D32](07_FINDINGS_AND_ISSUES.md), [D30](07_FINDINGS_AND_ISSUES.md) |
| Understand why platform behaviour differs | [05 §The `.env` contract](05_CONFIGURATION_AND_ENV.md), [D21](07_FINDINGS_AND_ISSUES.md) |

## Reading Order for a New Maintainer

1. [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) — what this is and what actually works.
2. [13_RUNBOOK.md](13_RUNBOOK.md) — get it running (use this, **not** `setup.sh`).
3. [14_ARCHITECTURE_DIAGRAMS.md](14_ARCHITECTURE_DIAGRAMS.md) — the whole system in pictures.
4. [02_ARCHITECTURE.md](02_ARCHITECTURE.md) §Application Lifecycle — the one control loop.
5. [03_MODULE_REFERENCE.md](03_MODULE_REFERENCE.md) §`app/assistant.py` — the command router.
6. [11_FEATURES_AND_CAPABILITIES.md](11_FEATURES_AND_CAPABILITIES.md) — what is genuinely usable.
7. [12_KNOWN_CAVEATS_AND_LIMITATIONS.md](12_KNOWN_CAVEATS_AND_LIMITATIONS.md) — before filing a bug.
8. [07_FINDINGS_AND_ISSUES.md](07_FINDINGS_AND_ISSUES.md) §S1 — fix the routing bugs first.
9. [04_DATA_FLOWS.md](04_DATA_FLOWS.md) §F1–F2 — see the whole request path.
10. [05_CONFIGURATION_AND_ENV.md](05_CONFIGURATION_AND_ENV.md) — configure it.
11. [06_TESTING_AND_QUALITY.md](06_TESTING_AND_QUALITY.md) §Recommended Test Priorities — lock in the fixes.

## Provenance & Integrity

- **Produced by:** static analysis (full read of all 31 tracked files) plus **dynamic
  verification** — `python -m py_compile`, `python -m app`, `python -m app.health_check`, and a
  15-case execution probe of `process_command` against injected fakes, all in a scratch copy.
- **Zero tracked files were modified.** `git status --porcelain` was empty at completion.
- **No secrets were read, created, or printed.** A high-entropy pattern sweep found none
  committed. `env/.env` was never created.
- **Every finding is traceable** to a `file:line` reference or a reproduced command.
- **Known gaps** are enumerated in [08 §Known Gaps and Limitations](08_EXPLORATION_LEDGER.md):
  one file at L1 depth (not L2), no Windows/macOS host, no live Spotify account, no microphone,
  and no third-party package audit.
- ⚠️ ~~These files are inside a git-ignored directory~~ — **resolved.** `docs/` was removed from
  `.gitignore` so this knowledge base is now trackable. → [D1](07_FINDINGS_AND_ISSUES.md) /
  [issue #4](https://github.com/ArindamTripathi619/spotify-voice-assistant/issues/4)
- **Docs 11–14 are new in the second pass** and were derived from the source, not from the README.
  Doc 14's Mermaid blocks are validated to parse.