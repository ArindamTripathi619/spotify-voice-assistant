# 05 — Configuration & Environment

## Configuration Sources, in Precedence Order

| Rank | Source | Loaded by | Notes |
|---|---|---|---|
| 1 | Real process environment | `os.getenv` at `app/assistant.py:39-41` | **Wins.** `load_dotenv()` defaults to `override=False`. |
| 2 | `<repo>/env/.env` | `app/utils.py:5-6` | The **only** file the app reads. |
| 3 | Defaults in code | `app/assistant.py:41`, `app/audio.py:45` | `SPOTIFY_REDIRECT_URI`, `WAKE_WORD`. |
| — | `config/config.json` | *nothing* | **Never read.** See 07/D17. |
| — | `config.py` dataclass defaults | *nothing* | **Never read.** |

## The `.env` Contract

```bash
# <repo>/env/.env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback
WAKE_WORD=jarvis                 # optional
```

| Variable | Required | Default | Read at | Used for |
|---|---|---|---|---|
| `SPOTIFY_CLIENT_ID` | **yes** | — | `assistant.py:39` | `SpotifyController(client_id=…)` |
| `SPOTIFY_CLIENT_SECRET` | **yes** | — | `assistant.py:40` | `SpotifyController(client_secret=…)` |
| `SPOTIFY_REDIRECT_URI` | no | `http://127.0.0.1:8080/callback` | `assistant.py:41` | OAuth redirect target |
| `WAKE_WORD` | no | `jarvis` | `health_check.py:104`, `audio.py:132` (via calibration file) | wake-word string |

Validation is `_validate_environment()` (`assistant.py:49-90`): it raises `EnvironmentError`
with a message naming **every** missing variable. Note that `SPOTIFY_REDIRECT_URI` is
hardcoded-defaulted in code rather than read from `config.py`'s settings.

### ⚠️ Documented path is wrong

- `app/utils.py:5` reads `os.path.join(os.path.dirname(__file__), "../env/.env")` →
  **`<repo>/env/.env`**.
- `README.md:115` and `QUICKSTART.md:51` instruct `cp .env.example .env` at the **repo root**.
- There is **no `.env.example` and no `.env.template`** anywhere in the repository, tracked or
  otherwise. Every `cp` instruction in every document is broken.
- `env/` is git-ignored, so it does not exist in a fresh clone.

`SETUP.md:110` is the **only** document that gets the path right.

### ⚠️ Linux/macOS setup scripts break on a clean clone — in two different ways

Both do a `cp` of a template that does not exist anywhere in the repository:

```bash
# setup.sh:61-63  — UNCONDITIONAL, and the last step of the script
if [ ! -f env/.env ]; then
    echo "📝 Creating env/.env file from template..."
    cp env/.env.template env/.env

# universal_setup.sh:111-115  — GATED behind a prompt that defaults to Y
if [ ! -f env/.env ]; then
    read -p "📝 Create env/.env file from template? [Y/n] " envfile
    envfile=${envfile:-Y}
    if [[ $envfile =~ ^[Yy]$ ]]; then
        cp env/.env.template env/.env
```

**Correction (second pass):** an earlier draft claimed both scripts "abort **before the user is
ever prompted**". That is wrong for both:

- **`setup.sh`** has no prompt at this point at all. The `cp` is unconditional and sits at
  `:63` of a 113-line script, so under `set -euo pipefail` (`setup.sh:6`) the script dies at the
  very end — **after** every install step has already run. The user is left with a working
  environment and a non-zero exit code, not a clean early failure.
- **`universal_setup.sh`** *does* prompt first (`:112`), defaulting to `Y`. Answering `n` skips
  the `cp` entirely and the script completes normally.

So the accurate statement is: on a fresh clone `setup.sh` **always** fails at the last step, and
`universal_setup.sh` fails **only if the user accepts the default**. Neither is the "fails fast
before prompting" behaviour the first pass described. Both verified by inspection.

`setup_windows.ps1:163-180` and `setup_windows.bat:125-143` do the right thing — they
`Write-Host`/`echo` a template and **generate `env\.env` interactively**. This asymmetry is
the root cause of the discrepancy.

**Verified working manual path:**

```bash
mkdir -p env
cat > env/.env <<'EOF'
SPOTIFY_CLIENT_ID=xxxxxxxx
SPOTIFY_CLIENT_SECRET=xxxxxxxx
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback
EOF
```

### Spotify Redirect URI

The app must receive `http://127.0.0.1:8080/callback`. It is **not** registered with Spotify
automatically, and the default is hardcoded. To use a different port you must both add it to
your Spotify Developer Dashboard app *and* set `SPOTIFY_REDIRECT_URI`; the two are never
cross-checked, so a mismatch manifests as an opaque OAuth failure.

### `WAKE_WORD` restrictions

`AudioManager.wake_word` setter (`audio.py:348`) rejects values that are empty, > 50 chars, or
contain non-alphanumeric characters. `wake_word` is also persisted to
`calibration/.voice_calibration.json` by `save_calibration_data()` and reloaded on the next
start — so a wake word set at runtime **survives restarts**, which the documentation does not
mention. Values consisting only of short common words (`go`, `a`, `no`) are accepted and will
produce constant false wake triggers, because matching is a plain substring test.

## Runtime Filesystem State

| Path | Created by | Contents | Git |
|---|---|---|---|
| `<repo>/logs/voice_assistant.log` + `.1`…`.5` | `assistant.py:12-17` (**import time**) | DEBUG-level RotatingFileHandler, 1 MB × 5 | ignored |
| `<repo>/calibration/.voice_calibration.json` | `audio.py:97` / `save_calibration_data()` | `wake_word`, `wake_threshold`, `wake_timeout`, `command_timeout`, `command_threshold`, `sensitivity_multiplier` | ignored |
| `<repo>/cache/.key` | `spotify_control.py:29` | 32-byte Fernet key, chmod 600 | ignored |
| `<repo>/cache/.spotify_tokens.enc` | `spotify_control.py:70` | OAuth token, Fernet-encrypted **if** `cryptography` is importable | ignored |
| `<repo>/env/.env` | user | credentials | ignored |

Paths are built by `os.path.join(os.path.dirname(__file__), '../<dir>')` in `assistant.py:31-44`
and `spotify_control.py:20`, **not** through `config.py`.

### Obsolete token-cache paths

`README.md:316`, `setup.sh:111`, and `universal_setup.sh:165` still describe
`cache/.spotify_cache`. The current implementation writes `.spotify_tokens.enc` + `.key`.

### ⚠️ `cryptography` is undeclared

`requirements.txt` omits it, so `pip install -r requirements.txt` leaves
`SecureTokenStorage.cipher = None` (`app/spotify_control.py:56`), and `save_token_to_cache` then
writes the token JSON **unencrypted** (`app/spotify_control.py:88-91`).

**Second-pass correction:** the first pass described this as producing "plaintext tokens" without
qualification. Because of **D40** — `save_token_to_cache` does not match spotipy's
`save_to_cache` protocol, so this method is never invoked by the OAuth flow — the fallback branch
is **not reachable in the user flow at all**. It is dead-code risk, not an active leak. The
*actual* first-run behaviour is an `AttributeError` inside spotipy (D40).
The degradation is silent apart from one WARNING log line. See 07/D16.

## Declared vs. Imported Dependencies

**Declared in `requirements.txt` and genuinely used:** `spotipy` 2.22.1,
`SpeechRecognition` 3.14.3, `pyttsx3` 2.90, `pyaudio` 0.2.11, `python-dotenv` 1.0.0.

**Declared but never imported anywhere in `app/`:** `colorama` 0.4.6, `psutil` 5.9.8.
Verified by grep across all 15 modules: **zero references to either**. `platform_utils.py` does
not import `psutil` at all, and `get_cpu_usage` / `get_memory_usage` — which an earlier draft
claimed existed there as `psutil` wrappers — **do not exist**. See 07/D26 and 07/D34.

**Imported but not declared:** `cryptography` — `from cryptography.fernet import Fernet`
(`spotify_control.py:42`), inside `try/except ImportError`.

**Optional and correctly guarded:** `plyer`, `win10toast`
(`notifications_cross_platform.py:30,38,59,75`).

`requirements_cross_platform.txt` duplicates the manifest (plus extra notes) and **no script
consumes it**; every installer uses `requirements.txt`.

## Build System

There is **no** `setup.py`, `setup.cfg`, `pyproject.toml`, `MANIFEST.in`, or wheel/sdist
configuration. The project is installed by `pip install -r requirements.txt` into a
hand-created `venv/` and is *not* an installable distribution. Consequently:

- `python -m app` only works from the repository root.
- There is no console-script entry point; every documented invocation includes `-m`.
- No declared Python version floor in packaging; only `health_check.check_python_version()`
  asserts `>= 3.7` at runtime.

## External Dependencies & Runtime Requirements

| Layer | Requirement | Platform | Enforced? |
|---|---|---|---|
| Python | ≥ 3.7 | all | health check only |
| PortAudio | `portaudio19-dev` / `brew install portaudio` | Linux/macOS | ❌ documented only |
| espeak-ng | TTS backend | Linux | ❌ (and TTS is never used) |
| ALSA/PulseAudio | audio I/O | Linux | ❌ |
| `libnotify` → `notify-send` | notifications | Linux | ❌ (`_setup_notifications` falls back to stdout) |
| Visual C++ Build Tools | build PyAudio | Windows | ❌ |
| Microphone permission | OS-level grant | all | ❌ |
| `which` | pre-flight for `osascript` | macOS | ❌ |
| Spotify desktop app | playback target | all | ❌ |
| Google Speech API | network + implicit quota | all | ❌ (no API key, so the unauthenticated free tier) |
| Spotify Developer app | Client ID/Secret + redirect URI | all | ✅ `_validate_environment` |

## Environment Variables — Complete Matrix

| Variable | Env var | Config key | Runtime code | Docs | Health check | Consistent? |
|---|---|---|---|---|---|---|
| Spotify Client ID | `SPOTIFY_CLIENT_ID` | `spotify.client_id` | `assistant.py:39` | README, QUICKSTART | ✅ | ⚠️ `config.json` key unused |
| Spotify Client Secret | `SPOTIFY_CLIENT_SECRET` | `spotify.client_secret` | `assistant.py:40` | README, QUICKSTART | ✅ | ⚠️ `config.json` key unused; `ConfigManager.save_config()` would write it in plaintext |
| Redirect URI | `SPOTIFY_REDIRECT_URI` | `spotify.redirect_uri` | `assistant.py:41` | README, QUICKSTART | ✅ | ⚠️ hardcoded default in code, never from config |
| Wake word | `WAKE_WORD` | `assistant.wake_word` | via calibration file | QUICKSTART | ✅ | ⚠️ not read from env at startup |
| Log level | — | `logging.level` | ❌ | — | ❌ | ❌ only `config.py` |
| Log dir | — | `logging.log_dir` | ❌ | — | ❌ | ❌ only `config.py` |
| Cache dir | — | `spotify.cache_dir` | ❌ | — | ❌ | ❌ only `config.py` |
| Audio input device | — | `audio.input_device_index` | ❌ | — | ❌ | ❌ only `config.py` |
| Energy threshold | — | `audio.energy_threshold` | ❌ | — | ❌ | ❌ only `config.py` |
| Dynamic energy | — | `audio.dynamic_energy_threshold` | ❌ | — | ❌ | ❌ only `config.py` |
| Calibration file | — | `audio.calibration_file` | ❌ | — | ❌ | ❌ only `config.py` |
| Wake timeout | — | `audio.wake_word_timeout` | ❌ | — | ❌ | ❌ only `config.py` |
| Command timeout | — | `audio.command_timeout` | ❌ | — | ❌ | ❌ only `config.py` |
| TTS rate/volume | — | `audio.tts_rate`, `tts_volume` | ❌ | — | ❌ | ❌ only `config.py` |
| Notifications enabled | — | `notifications.enabled` | ❌ | — | ❌ | ❌ only `config.py` |
| Notification sound | — | `notifications.sound_enabled` | ❌ | — | ❌ | ❌ only `config.py` |

**14 of the 17 settings in `config/config.json` are inert.** The four that work are read
straight from the environment, bypassing the config layer entirely.

## `config/config.json` (29 lines, orphaned)

Mirrors `AssistantConfig`'s dataclass defaults: nested `spotify` / `audio` / `notifications` /
`assistant` objects. Credential fields are empty strings. `spotify.devices` lists
`Desktop`, `Speaker`, `Smartphone`, and `TV`. Nothing reads it; `python -m app.config` writes it.

⚠️ `ConfigManager.save_config()` serialises the dataclasses straight to JSON, which would
place `client_secret` in a plaintext, **non-gitignored** file. This is latent rather than active
because `ConfigManager` is never instantiated, but it is a trap for the first person who wires
it up. See 07/D19.

## ⚠️ `docs/` Is Git-Ignored

`.gitignore:13` ignores `docs/`. `git check-ignore -v docs/project-context/00_PROJECT_OVERVIEW.md`
confirms it. **Consequence: this knowledge base will not be committed and will not persist
across clones** unless `.gitignore` is changed. See 07/D1.