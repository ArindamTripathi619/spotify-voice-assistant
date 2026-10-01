# 08 — Exploration Ledger

Exhaustive per-file record. Every tracked file in the repository has exactly one row here.
Nothing is omitted silently — items not investigated carry an explicit exclusion reason.

## Coverage Metrics

| Metric | Value |
|---|---|
| Tracked files in repository | **31** |
| Files appearing in this ledger | **31** |
| Files with full read + traced (L2) | **30** |
| Files with structure + targeted claims verified (L1 only) | **0** — `WINDOWS_PORT_GUIDE.md` was promoted to L2 in the second pass |
| Files not investigated | **0** |
| Files excluded by justification | **0** tracked files (see "Explicit Exclusions" for untracked paths) |
| Python modules | **15** |
| Python LOC | **2,627** |
| Python files read in full | **15 / 15 = 100%** |
| Non-code files read in full | **16 / 16 = 100%** |
| Tracked files modified during reconnaissance | **0** (verified: `git status --porcelain` empty) |

Per-file line counts (authoritative, from `git ls-files` + `wc -l`):

```
485  app/spotify_control.py        194  app/notifications_cross_platform.py
387  app/audio.py                  154  app/platform_utils.py
369  app/health_check.py           112  app/launch_spotify_cross_platform.py
308  app/error_handling.py          26  app/__init__.py
286  app/config.py                   8  app/__main__.py
274  app/assistant.py                7  app/utils.py
                                   6  app/notifications.py
                                    6  app/launch_spotify.py
                                    5  app/main.py
```

## Per-File Ledger

Legend — **Coverage**: L1 structure, L2 full read + traced. **Method**: how it was read.
**Value**: why a future maintainer cares.

### Application source (15 files)

| # | Path | Cvg | Method | Value | Findings |
|---|---|---|---|---|---|
| 1 | `app/__init__.py` | L2 | full read; executed `import app` in a dependency-free env | Facade + version metadata; the cause of the diagnostic's failure | **D2** (eager imports) |
| 2 | `app/main.py` | L2 | full read | The documented entry point; 5 lines | **D38** |
| 3 | `app/__main__.py` | L2 | full read; `python -m app` executed | Maps `python -m app` to the health check | — |
| 4 | `app/assistant.py` | L2 | full read; **imported and executed** `process_command` across 20 inputs against a recording fake | **The orchestrator and the command router — the most behaviour-critical file** | **D5, D6, D27, D22 context, cleanup double-call** |
| 5 | `app/audio.py` | L2 | full read; project-wide grep for `self.recognizer`; traced every call site | All audio capture, calibration, STT, TTS | **D7, D8, D28, D47, D22, D55 (shared mic cached, never closed)** |
| 6 | `app/spotify_control.py` | L2 | full read; traced every Spotify call; grep for `self.rate_limiter` and `cache_path` | The entire Spotify integration incl. token security | **D10, D12, D13, D15, D16, D36, D19 context** |
| 7 | `app/notifications_cross_platform.py` | L2 | full read | The **only** user-facing output channel | **D9, D49** |
| 8 | `app/platform_utils.py` | L2 | full read | OS abstraction; every platform branch lives here. Verified `os.path.expandvars` at `:49` ⇒ **D23 retracted** | **D26, D50** |
| 9 | `app/launch_spotify_cross_platform.py` | L2 | full read | Auto-launch + device re-acquisition | correct Flatpak handling (disproved a hypothesis); `subprocess.CREATE_NO_WINDOW` at `:33` — **D51** (the first pass misfiled D51 under `platform_utils.py`; corrected here) |
| 10 | `app/error_handling.py` | L2 | full read; reference sweep for every public symbol | Designed error taxonomy | **D18** (first pass wrote "D18" twice); independent note: `_standardize_error` (`:126`) tests the **network** class first, so an error whose *message* contains "token" plus "timeout" is classified `NetworkError` |
| 11 | `app/health_check.py` | L2 | full read; **executed twice** (natively → crash; with stubs → full run) | The only automated verification mechanism | **D2, D24, D25** |
| 12 | `app/config.py` | L2 | full read; AST inbound-edge count = 0 | Intended configuration layer | **D17, D19, D20** |
| 13 | `app/notifications.py` | L2 | full read (6 lines) | Compatibility shim; adds one hop | indirection with no consumer |
| 14 | `app/launch_spotify.py` | L2 | full read (6 lines) | Compatibility shim | indirection with no consumer |
| 15 | `app/utils.py` | L2 | full read (7 lines) | **Defines the only configuration file path the app reads** | **D4** (path mismatch with docs) |

### Configuration & data (1 file)

| # | Path | Cvg | Method | Value | Findings |
|---|---|---|---|---|---|
| 16 | `config/config.json` | L2 | full read; reference sweep across `*.py`, `*.sh`, `*.ps1`, `*.bat`, `*.md` → **zero runtime readers** | Documents the intended settings surface | **D17** (entire subsystem inert; the "14/17" count from the first pass was unverifiable and has been withdrawn), **D19 context** |

### Documentation (7 files)

| # | Path | Cvg | Method | Value | Findings |
|---|---|---|---|---|---|
| 17 | `README.md` | L2 | full read, all 370 lines | The project's primary documentation | **D4** (:115 wrong path), **D27** (:191), **D28** (:162), **D29** (:204), **D30** (:316), **D31** (:292-295, :305 corruption, stale tree), **D39** |
| 18 | `SETUP.md` | L2 | full read, all 215 lines | Per-platform setup reference | **D21** (:82 macOS/Homebrew), **D4** (:110 is the *only* correct `.env` path), **D27** (:201) |
| 19 | `QUICKSTART.md` | L2 | full read, all 190 lines | Fast-track onboarding | **D4** (:51), **D27** (:110, :134), references the missing "What's playing" feature |
| 20 | `Promotion.md` | L2 | full read, all 48 lines | Social copy | **D56** (`:28` merge artifact — the *performance claim* the first pass filed as D32 turned out to be fabricated), **D27** (:11, :38) |
| 21 | `windows_port_plan.md` | L2 | full read, all 40 lines | Historical record; all items ✅ complete | consistent with reality |
| 22 | `WINDOWS_PORT_GUIDE.md` | **L2** *(upgraded in second pass)* | full read of all 295 lines; every install command, `pip` invocation and launch command checked against `app/`, `requirements*.txt` and `setup_windows.*` | Windows port reference (295 lines) | **D3** (`:83` `copy env\.env.template env\.env` — file does not exist), accurately lists all four vars incl. `SPOTIFY_REDIRECT_URI` and `WAKE_WORD` (`:176-180`) — the **best** `.env` reference in the repo, **D38** (`:196, :200, :279` all correctly use `python -m app.main`), **D30** (`:276` `pip install -r requirements_cross_platform.txt` — a file no installer ever references), **D56** (`:220` unmeasured "~100ms response time") |
| 23 | `LICENSE` | L2 | full read (20 lines) | MIT, 2025, ArindamTripathi619 | — |

**Second-pass change of heart:** this file was L1 in the first pass, on the reasoning that it
was a "porting reference" and therefore low-risk. That was the wrong call — it contains an
install command, a `.env` template copy, a performance table, and three launch invocations, i.e.
exactly the class of content that is actionable and wrong. It is now **L2 (full read)**, and the
full read found D56, which the first pass had not seen at all. It is now the only file in the
repository at L2 rather than L1, and it is cited nowhere else in this knowledge base.

### Build / setup / infrastructure (7 files)

| # | Path | Cvg | Method | Value | Findings |
|---|---|---|---|---|---|
| 24 | `setup` | L2 | full read, all 83 lines | Universal dispatcher | **D21** (:51 `setup_macos.sh` does not exist) |
| 25 | `setup.sh` | L2 | full read, all 113 lines; traced the `set -euo pipefail` interaction | Arch-only installer | **D3** (:63 abort), **D27** (:107), **D30** (:111) |
| 26 | `universal_setup.sh` | L2 | full read, all 165 lines | Interactive multi-distro installer | **D3** (:115 abort), **D27** (:161), **D30** (:165) |
| 27 | `setup_windows.ps1` | L2 | full read, all 212 lines | Windows installer — **the reference implementation** | Correctly generates `env\.env` (:163-180); supports `-SkipDependencies`, `-SkipSpotifyCheck`, `-NoVenv` |
| 28 | `setup_windows.bat` | L2 | full read, all 188 lines | cmd equivalent | Same correct inline-`.env` (:125-143) |
| 29 | `requirements.txt` | L2 | full read; cross-checked every entry against a project-wide import sweep | Authoritative dependency manifest | **D16** (`cryptography` missing), **D26** (`colorama`, `psutil` unused) |
| 30 | `requirements_cross_platform.txt` | L2 | full read; confirmed no installer references it | Duplicate manifest | dead file |
| 31 | `.gitignore` | L2 | full read, all 105 lines; verified rule 13 with `git check-ignore -v` | Ignore policy | **D1** (:13 ignores `docs/`) |

## Explicit Exclusions (untracked paths)

| Path | Reason | How its behaviour is still documented |
|---|---|---|
| `.git/` | VCS internals | 16 commits, all by one author, single branch `main` |
| `venv/` | Git-ignored; created by setup scripts | Documented in 05 |
| `logs/` | Git-ignored; **created during reconnaissance by the import-time side effect** and by the health check | Import-time side effect documented in 02/03; side effect documented in D25 |
| `cache/` | Git-ignored; created by the health check and by `SpotifyController.__init__` | Documented in 05 and D15/D16 |
| `calibration/` | Git-ignored; created by the health check | Documented in 05 and D7 |
| `env/` | Git-ignored; never existed (no `.env` present, correctly) | The `env/.env` contract is documented in 05; **no `.env` was created or read during reconnaissance** |
| `app/__pycache__/` | Byte-cache written by `py_compile` and by imports; git-ignored | n/a |
| `/tmp/opencode/sva-sandbox` | Scratch copy used to execute application logic without touching the repo | Methodology documented in 06 |

## Non-Repository Context Consulted

| Source | Used for | Constraint |
|---|---|---|
| spotipy 2.22.1 API contract | `cache_handler` protocol (`get_cached_token`/`save_to_cache`/`clear_cached_token`), `prompt_for_user_token` needing client credentials, `SpotifyOAuth.cache_path` being `None` | Interface-level only; the library was not installed |
| `SpeechRecognition` 3.14.3 | `sr.Microphone`, `sr.Recognizer().listen/recognize_google`, `get_all_microphone_names` | Interface-level only |
| `python-dotenv` 1.0.0 | `load_dotenv` defaults to `override=False` | Interface-level only |
| PyAudio / PortAudio | Imported transitively via SpeechRecognition; platform build requirements | Documented in 05 |
| Third-party internals were **not** vendored, modified, or audited | — | Out of scope for first-party reconnaissance |

## Methodology Applied

| Phase | Action | Result |
|---|---|---|
| Zero | `pwd`, `git status`, `git branch`, `git log`, `git remote -v`, Python version, host packages | Clean `main`, 16 commits, Python 3.14.3 |
| One | `git ls-files` + `find` + tree rendering | 31 files, 3 directories, exhaustive |
| Two | Full read of all 31 files | **31 at L2, 0 at L1** (after the second pass promoted `WINDOWS_PORT_GUIDE.md`) |
| Three | Traced every entry point, every public method's call sites, and every data path | Complete call graph in 02/03/04 |
| Four | AST import walk of all 15 modules | DAG confirmed; `config.py` isolated |
| Five | Swept `config/`, `.env.template`, `.env.example`, `env/` across all file types | All absence claims confirmed |
| Six | `py_compile`; executed `python -m app` and `python -m app.health_check` natively, then with stubs; 20-case dispatch probe | D2, D5, D6, D24 reproduced |
| Seven | Enumerated all non-code assets; no binary assets, no fonts, no images | Nothing to profile |
| Eight | Existence check for 17 test/CI/lint/type config paths; `find` for test-shaped files and any `.yml`/`.yaml`; high-entropy secret sweep; `git check-ignore` | D33, no secrets, D1 |
| — | `git status --porcelain` at completion | **Empty — zero tracked files modified** |

## Known Gaps and Limitations of This Knowledge Base

1. ~~**`WINDOWS_PORT_GUIDE.md` is L1, not L2**~~ — **RESOLVED in the second pass.** All 295
   lines were read end-to-end and every install/`pip`/launch command was checked against the
   Windows scripts and the code. This is no longer a gap: it is now L2, and the read produced
   **D56**, which the first pass had missed entirely. **Every one of the 31 tracked files is now
   at L2; there is no L1 file outstanding.**
2. **No Windows or macOS host was available.** All platform behaviour on those two OSes is
   `[INSPECTED]` from source, not executed. This affects D21, D23, D51 and the correctness of
   the `setup_windows.*` claims.
3. **No live Spotify account, microphone, or audio device.** All audio and Spotify behaviour is
   `[INSPECTED]` or `[INFERRED]`; only the pure command-routing logic was executed, against a
   recording fake. **D40** (the most severe finding) is the one item still needing a live run.
4. **Third-party package internals were not installed or audited** — no version-conflict or
   API-drift verification was performed. All version pins (`spotipy==2.22.1`,
   `SpeechRecognition==3.14.3`, `pyttsx3==2.90`, `pyaudio==0.2.11`) were **not** validated
   against Python 3.14.3; `pyaudio` in particular is known to require compilation on several
   platforms.
5. **Runtime directories created during reconnaissance** (`logs/`, `cache/`, `calibration/`
   via the health check, and `app/__pycache__/` via `py_compile`) were left in place rather
   than deleted, to remain non-destructive. They are git-ignored and can be removed with
   `rm -rf logs cache calibration app/__pycache__`.
6. **D34 was rebuilt by direct grep after verification.** The first draft's dead-code table
   listed four members that **do not exist** — `audio.get_microphone_names`,
   `platform_utils.get_cpu_usage` / `get_memory_usage` / `get_terminal_command` — and claimed
   `get_microphone_names` was "live". All four names were fabricated. The table has been
   recomputed and every remaining row is grep-confirmed. The general caution still stands: a name
   being absent from grep output is weaker evidence than a name being present at a call site.
7. **`docs/` remains git-ignored (D1).** This knowledge base exists on disk but will not be
   committed until a maintainer decides on `.gitignore`.