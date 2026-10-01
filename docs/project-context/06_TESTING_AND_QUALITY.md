# 06 — Testing & Quality

## Existing Test Infrastructure

**None.** Verified by exhaustive check for each of the following — all absent:

`tests/`, `test/`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `conftest.py`,
`noxfile.py`, `Makefile`, `.github/` (any workflow), `*.yml` / `*.yaml` (none anywhere in the
repo), `.flake8`, `.pre-commit-config.yaml`, `mypy.ini`, `.editorconfig`, `CONTRIBUTING.md`,
and any file matching `test_*.py`, `*_test.py`, `*.spec.js`.

There is no `unittest` usage, no mocking library, no assertion of any kind, and no
`assert` statement in the 2,627 lines of application code. `requirements.txt` contains no
test dependency.

| Dimension | Status |
|---|---|
| Unit tests | ❌ none |
| Integration tests | ❌ none |
| E2E / smoke tests | ❌ none |
| Test runner config | ❌ none |
| CI/CD pipelines | ❌ none |
| Linting (flake8/ruff/pylint) | ❌ none |
| Formatting (black) | ❌ none |
| Type checking (mypy) | ❌ none |
| Pre-commit hooks | ❌ none |
| Code coverage | ❌ none |
| Issue/PR templates | ❌ none |
| `CONTRIBUTING.md` | ❌ none |
| Security scanning in CI | ❌ none (a security audit was claimed in commit `69a9724` but nothing enforces it) |

**The only automated verification mechanism in the project is `app/health_check.py`**, a
runtime environment prober — not a test suite.

## The One Verification Tool: `app/health_check.py` (369 lines)

8 checks, each printing a `✔`/`⚠`/`✖` and returning a severity. `run()` returns an exit code:
`0` = all OK, `1` = warnings present, `2` = at least one failure.

| # | Check | Line | Can run without credentials? | Side effects |
|---|---|---|---|---|
| 1 | Python version ≥ 3.7 | 27 | yes | none |
| 2 | 7 dependencies importable | 45 | yes | none |
| 3 | 4 environment variables | 78 | yes | none |
| 4 | Audio system / microphones | 120 | yes | **opens a mic, records 0.5 s** |
| 5 | Platform compatibility | 165 | yes | none |
| 6 | Filesystem permissions | 190 | yes | **creates 3 dirs, writes + deletes a probe file** |
| 7 | Network connectivity | 230 | yes | outbound TCP to Google:443 |
| 8 | Spotify API auth | 290 | **no** | performs an OAuth client-credentials token request |

### Reproduced execution

Environment without the third-party dependencies:

```
$ python -m app.health_check
ModuleNotFoundError: No module named 'spotipy'        # ← from app/__init__.py
$ python -m app
ModuleNotFoundError: No module named 'spotipy'
```

The diagnostic that exists to report missing dependencies **cannot report them** (07/D2).

Environment with stub modules injected (`PYTHONPATH=stubs`), which allowed the module logic to
execute:

```
[1/8] Python version        ✔ 3.14.3
[2/8] Dependencies          ✔ 7/7 present          (satisfied by stubs — not meaningful)
[3/8] Environment           ⚠ SPOTIFY_CLIENT_ID not set
[4/8] Audio system          ⚠ no input device available
[5/8] Platform              ✔ linux
[6/8] Filesystem            ✔ writable             (created cache/ logs/ calibration/)
[7/8] Network               ✔ Internet OK
                               ✔ Spotify API connectivity      ← label for a TCP probe
[8/8] Spotify auth          ✖ Auth failed
```

### Defects in the health check itself

| ID | Defect |
|---|---|
| D2 | Unreachable when dependencies are missing (eager `__init__.py`). |
| D25 | `check_filesystem_permissions` mutates the repository — creates `cache/`, `logs/`, `calibration/`, writes and deletes `.test_write`. A diagnostic should not have this effect. |
| D24 | `check_network_connectivity` returns `all_good = True` unconditionally; its `try/except` assigns per-site results but never feeds them into the aggregate. |
| D24b | `print_summary` labels the Spotify entry "✅ Spotify API connectivity" when the underlying test was only a TCP socket connect, producing a false positive. |
| D24c | Check 8 uses `client_credentials_manager`, an OAuth flow **the application never uses**; the app uses the authorization-code flow. The check therefore does not validate the app's real auth path. |

## Testability Assessment

### Good testability characteristics

- **Pure-logic command routing.** `process_command(command: str)` takes a string and calls
  methods on `self.spotify_controller`. With a fake controller it is fully testable — this is
  how the defects in 07/D5 and D6 were confirmed empirically.
- **Constructor injection.** `AudioManager(calibration_file=, notifier=, wake_word=)` and
  `SpotifyController(client_id=, client_secret=, redirect_uri=, cache_path=, notifier=)`
  accept their collaborators.
- **Filesystem state is injectable** via the `calibration_file` and `cache_path` parameters, so
  tests need not touch the repo.
- **`health_check.py` has no external dependency beyond `platform_utils`** (when imported
  directly rather than through the package).

### Barriers to testing

| Barrier | Consequence |
|---|---|
| **Eager imports in `app/__init__.py`** | Cannot import any single module without every third-party dependency installed. Blocks isolated unit testing entirely. |
| **`self.error_handler` is never injected** | The `error_handler` decorator (which is the only exception-machinery hook) is applied to **no** function. The decorator itself is correctly written — it `hasattr`-probes and falls back to a fresh `ErrorHandler()` — it is simply never used. (07/D18; the earlier claim that it raises `AttributeError` is retracted.) |
| **No dependency-injection seam for the Spotify API** | `SpotifyController` constructs `SpotifyOAuth` internally (`spotify_control.py:139-145`); `play_song` calls `self.spotify.search` (`:175`) and `self.spotify.start_playback` (`:179`) directly. Mocking requires patching the module attribute. |
| **No seam for audio capture** | `AudioManager` constructs `sr.Microphone` (`:273`, `:358`) and `sr.Recognizer` (`:270`, `:356`) internally. |
| **Globals / module-level state** | `assistant.py:11-17` mutates the filesystem and installs a `RotatingFileHandler` at **import time**, so any test that imports `app` creates `logs/`. There is no other module-level mutable state of note — the earlier claim that `audio.py` keeps an unbounded `google_request_times` list is **retracted**; no such symbol exists (07/D47, which is now the one-call-site finding). |
| **Network calls are synchronous and inline** | No async, no injectable HTTP client, no timeout configuration beyond spotipy defaults. |
| **Two `try/except ImportError` blocks hide behaviour** | `spotify_control.py:42` and the notification backends change behaviour depending on what is installed; tests must model both branches. |
| **Constructor does I/O and can block** | `SpotifyController.__init__` performs a network round-trip and may launch an interactive browser flow — it cannot be called in a unit test without patching. |

## Verification Performed During Reconnaissance

Because no test suite exists, correctness was established by **direct execution** of the
application's logic against injected fakes. Methodology and results:

### Method

1. Copied the tree to a scratch directory (`/tmp/opencode/sva-sandbox`) — the repository was
   not modified.
2. Created minimal stub modules on `PYTHONPATH` for the seven third-party packages, plus a fake
   `spotipy` OAuth flow, so `app`'s own logic could be imported and executed.
3. Constructed `EnhancedVoiceAssistant` via `__new__` and injected a recording fake for
   `spotify_controller`, a fake `notifier`, and a real `ErrorHandler`.
4. Invoked `process_command` with 15 spoken phrasings and recorded which Spotify method was
   called.
5. Separately exercised `str.lstrip('../')` semantics to confirm a suspected path bug.

### Results

15 dispatch cases executed; 10 behaved as intended, 5 did not. See the full table in
`03_MODULE_REFERENCE.md` and the defect list in `07_FINDINGS_AND_ISSUES.md`. The headline
results:

- `"what's playing"` → `play_song('ing')` — the documented "What's playing?" feature is broken.
- `"goodbye"` → `resume_playback()` — substring `"go"` hijacks the quit intent.
- `"go back to previous track"` → `resume_playback()` — same cause.
- `'quit'`, `'exit'`, `'bye'`, `'volume down'`, `'louder'`, `'quieter'`, `'next'`, `'skip'`,
  `'back'`, `'last'`, `'play <title>'` — correct.
- One initially-suspected bug (`'quit'` → `AttributeError`) was **disproved** by re-testing with
  proper collaborators and is recorded here as a ruled-out false positive.

### Static verification performed

| Check | Result |
|---|---|
| `python3 -m py_compile app/*.py` | ✅ all 15 modules compile (Python 3.14.3) |
| AST import walk of all 15 modules | ✅ no circular imports; `config.py` has zero inbound edges |
| `self.recognizer` reference count | ✅ confirms the dead-recognizer defect (07/D7) |
| `config/` reference sweep across `*.py`, `*.sh`, `*.ps1`, `*.bat`, `*.md` | ✅ confirms `config.json` is read by no runtime code |
| `.env.template` / `.env.example` existence | ✅ confirms both are absent, invalidating every documented `cp` |
| Secret pattern sweep (`client_secret`/`api_key`/`token`/`password`/`Bearer` with high-entropy literals) across `*.py`, `*.json`, `*.sh`, `*.md`, `*.bat`, `*.ps1` | ✅ **no hardcoded secrets found** |
| `.gitignore` rule for `docs/` | ✅ confirmed via `git check-ignore -v` |

> Note: `py_compile` writes `app/__pycache__/`. This is git-ignored, and no tracked file was
> modified at any point during reconnaissance.

## Coverage Matrix — Command Router

| Documented command | Source | Verified behaviour |
|---|---|---|
| "Play <song>" | README:44, QUICKSTART:88 | ✅ works; filler words not stripped |
| "Pause" / "Stop" | README:45 | ✅ works |
| "Resume" / "Play" (bare) | README:45 | ✅ works (bare `play` → resume) |
| "Next track" / "Skip" | README:47 | ✅ works |
| "Previous track" / "Back" | README:47 | ❌ broken when the phrase contains "go" |
| "Volume up/down", "louder/quieter" | README:48 | ✅ works |
| **"What's playing?"** | **README:46, QUICKSTART:90** | ❌ **broken — plays a track named "ing"** |
| "Help" / "Commands" | README | ✅ works |
| "Quit" / "Exit" / "Bye" | README:49 | ✅ works; ⚠️ "goodbye" does not |

## Quality & Maintainability Assessment

| Aspect | Rating | Evidence |
|---|---|---|
| Correctness | ⚠️ poor | A headline documented feature is inoperable; 5/15 dispatch cases misbehave |
| Test coverage | ❌ none | 0% |
| Automated verification | ❌ none | Not even a syntax check in CI |
| Documentation accuracy | ⚠️ poor | Wrong `.env` path in 2 of 3 guides; 4 features documented that do not exist; corrupted Markdown |
| Modularity | ⚠️ mixed | Clean layer boundaries in the OS adapter; ~40% of code unreachable |
| Error handling | ⚠️ mixed | Deliberate and reasonable at the method boundary; a parallel 308-line error framework is dead |
| Security posture | ⚠️ mixed | No committed secrets, `0o700`/`0o600` modes, token encryption designed in — but `cryptography` undeclared and the key sits beside the ciphertext. Note the unencrypted fallback is **unreachable** because D40 breaks the handler contract first |
| Dependency hygiene | ❌ poor | 2 unused declared deps, 1 undeclared imported dep, duplicate manifest |
| Cross-platform story | ⚠️ partial | Windows and Linux both have working setup paths; **macOS automated setup is broken** |
| Documentation of behaviour | ❌ none | No CONTRIBUTING, no architecture doc (until this knowledge base) |

## Recommended Test Priorities

Ordered by defect density × blast radius. Listed for the maintainer's benefit; **no code was
changed** during this reconnaissance.

1. **Make `app/__init__.py` lazy** (`__getattr__`-based, PEP 562) so any module can be imported
   independently. Unblocks every other test and fixes the health check's primary failure mode.
2. **`tests/test_command_router.py`** — a table-driven test over `process_command`. The routing
   rules are already effectively a lookup table and are trivially testable; the five defects in
   07/D5/D6 are all findable this way.
3. **`tests/test_audio.py`** — assert that the recognizer instance used by
   `listen_for_wake_word`/`listen_for_command` is the calibrated one. Would have caught 07/D7/D8.
4. **Add `cryptography` to `requirements.txt`** and rename `save_token_to_cache` → `save_to_cache` (D40) — these are the same fix area: the encryption path cannot be exercised until the handler protocol is correct
   or a hard failure.
5. **Add `ruff` + `pytest` + a GitHub Actions workflow** — the absence of all three is the root
   cause of every issue in this document persisting.
6. **Integration smoke test** for `health_check.run()` asserting exit code and that it creates
   no files.