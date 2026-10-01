# 09 — Glossary & Terminology

## Project-Specific Terms

| Term | Definition | Where |
|---|---|---|
| **Wake word** | The activation phrase ("jarvis" by default) that must be recognised before any command is processed. Changing it takes effect immediately and **persists across restarts** via the calibration file. | `app/audio.py:348-358`, `audio.py:353` |
| **Enhanced Assistant** | `EnhancedVoiceAssistant` — the orchestrator class. Named "Enhanced" after a refactor that was never completed; the old name `VoiceAssistant` survives only in two stale comments. | `app/assistant.py:19`, `audio.py:9`, `spotify_control.py:14` |
| **Base manager** | The two `try/except ImportError` blocks in `AudioManager.__init__` and `SpotifyController.__init__` that set `self.error_handler = None  # Will be assigned by VoiceAssistant`. **The assignment never happens.** | `audio.py:9-12`, `spotify_control.py:14-17` |
| **Shim** | `app/notifications.py` and `app/launch_spotify.py` — 6-line modules that only re-export from the `_cross_platform` modules. Added in the same commit as the split they protect. | `app/notifications.py`, `app/launch_spotify.py` |
| **Base manager / config manager** | `ConfigManager` — the orphaned 286-line configuration layer with no callers. | `app/config.py:67` |
| **Google API rate limit** | A misnomer: `app/audio.py:290-320` throttles **Google Speech-to-Text**, not the Spotify API. 60 requests/minute, enforced per assistant instance by sleeping inline. | `app/audio.py:290-320` |

## Recognition Terms

| Term | Definition |
|---|---|
| **STT** | Speech-to-Text. The project uses Google STT via `SpeechRecognition.recognize_google()`, with no API key, so it consumes the anonymous free tier. Audio is transmitted to Google; **there is no offline mode**. |
| **Wake cycle** | One pass of: listen for the wake word (30 s budget) → listen for a command (3 s budget) → execute. Two Google STT requests minimum. |
| **Google rate limiter** | `_apply_google_api_rate_limit` (`audio.py:308`) — a correct fixed-interval limiter at 45 requests/minute with an inline `sleep`. The defect is not the algorithm but that it has **one call site** (`:283`, inside `listen_for_command`); `listen_for_wake_word` bypasses it (07/D47). The earlier claim that a `google_request_times` list grows without bound is **retracted** — no such symbol exists (07/D47). |
| **Calibration** | Two distinct things the codebase calls "calibration". ① *Ambient calibration* (`smart_calibration` `:193`, 2 s sample; `enhanced_calibration` `:209`, 4 s sample) — both tune a **local** recognizer that is then discarded, so neither persists anything. ② *The saved calibration file* `calibration/.voice_calibration.json`, whose validated schema is `date`, `energy_threshold`, `pause_threshold`, `success_rate` (`:121`). `smart_calibration` does read `energy_threshold` back from it (`:199`, confirmed) — into a local recognizer. `wake_word` is **not** part of the schema. No expiry check exists despite `README.md:178-179` (07/D53). |
| **Sensitivity adjustment** | `AudioManager.adjust_sensitivity()` (`:382`) — **dead code**: no call sites, no loop, and its body is guarded by permanently-false `if self.attempt_count > 2` (`:383`). `attempt_count` is initialised to 0 (`:26`) and never incremented. (07/D8) |
| **`recognizer` confusion** | `self.recognizer` is configured by `setup_enhanced_audio()` (`:45`, 8 attributes at `:50-57`) but never passed to `listen()`. Both listening methods create a local `sr.Recognizer()` (`:270`, `:356`) which *does* receive `adjust_for_ambient_noise(duration=0.2)` (`:286`, `:359`). So ambient adaptation works; the **tuned and persisted** state does not. (07/D7) |
| **`UnknownValueError`** | `SpeechRecognition`'s exception for "speech was unintelligible". Caught at `audio.py:283-288` → notification "Could not understand audio" → `None`. No text-mode fallback (D27). |

## Audio / Hardware Terms

| Term | Definition |
|---|---|
| **`sr.Microphone`** | `speech_recognition`'s context-manager wrapper over a PyAudio stream. The app uses `with sr.Microphone(...) as source:` and `source.audio` (a raw `AudioData`) as Google's API input. |
| **ambient noise threshold** | `Recognizer.energy_threshold` — the RMS energy above which audio is considered speech. Set to 300 in `__init__`, then never used. |
| **`dynamic_energy_threshold`** | Auto-adapting threshold using a rolling average of recent audio. Also set on the unused recognizer. |
| **PortAudio** | The C audio I/O layer PyAudio binds to. Requires system packages (`portaudio19-dev` on Debian, `brew install portaudio` on macOS) — documented, never checked. |
| **PyAudio** | Python binding to PortAudio. **Requires compilation on most platforms**; on Windows this needs the MSVC build tools. Declared as `pyaudio==0.2.11`; imported only transitively via `SpeechRecognition`. |
| **espeak-ng / libespeak** | The default `pyttsx3` backend on Linux. `pyttsx3.init()` raises without it. |

## Spotify Terms

| Term | Definition |
|---|---|
| **spotipy** | The Spotify Web API client used throughout `app/spotify_control.py`. |
| **OAuth** | The Spotify authorization-code flow with PKCE. **Requires client ID, client secret, and a registered redirect URI.** The first run opens a browser. |
| **Client-credentials flow** | A *different* OAuth flow (app-only, no user context). Used **only** by `health_check.check_spotify_connection()`, never by the application — so the health check does not test the app's real auth path. |
| **`prompt_for_user_token`** | `spotipy.util` helper that spins up a temporary local HTTP server and blocks until the user authorises. Requires client credentials as arguments. The app calls it **without** them (`spotify_control.py:~400`). |
| **Redirect URI** | Where Spotify sends the auth code. Default `http://127.0.0.1:8080/callback`; must be registered in the Spotify Developer Dashboard. Never cross-checked against the actual value in use. |
| **PKCE** | Proof Key for Code Exchange — the `code_verifier`/`code_challenge` pair spotipy generates. Makes the public client flow work without a client secret in the browser. |
| **`cache_handler`** | The duck-typed protocol spotipy uses for token storage: requires `get_cached_token()` and **`save_to_cache(token)`**, plus optional `clear_cached_token()`. `SecureTokenStorage` implements only the first — `save_token_to_cache()` (`:78`) is the wrong name, and `save_to_cache` **does not exist**. Since it is wired in as the handler at `:145`, the first token save should fail. **The most severe finding in the project (07/D40).** |
| **`token.json` / `.spotify_cache`** | spotipy's *own* default on-disk cache path. **Not used here** — the project installs its own `SecureTokenStorage`. Still referenced by 3 stale documentation lines (07/D30). |
| **Active device** | The Spotify Connect device currently playing. `_find_active_device()` (`spotify_control.py:403`) returns the first device with `is_active` **or** `type == 'Computer'` — so it can return an *idle* computer, which `_launch_and_setup_device` then `transfer_playback(force_play=True)`s, silently hijacking playback (07/D48). There is **no** `get_active_device()` and no per-command re-OAuth; recovery is exception-driven off a `'No active device' in str(e)` string match (`:181`). |
| **Device-scoped volume** | Spotify's volume is a property of the Connect **device**, not of the user. `adjust_volume()` (`:349`) reads `volume_percent` from `current['device']`, adds ±15, clamps to `0..100` (`:353`) and calls `spotify.volume(<absolute value>)` — **not** `volume_up`/`volume_down`. It has **no `else` branch**, so a falsy `current['device']` is a silent no-op (07/D46). |
| **`spotify_cd`** | Alias some spotipy versions expose for the currently-playing track. **Not used** by this project; `get_current_track()` reads `current_playback` directly. |
| **Flatpak Spotify** | The sandboxed Linux distribution (`com.spotify.Client`). Preferred over the native binary on Linux; handled correctly in `launch_spotify_cross_platform.py:63-78`. |

## Security Terms

| Term | Definition |
|---|---|
| **Fernet** | `cryptography`'s symmetric encryption (AES-128-CBC + HMAC-SHA256). Used by `SecureTokenStorage` to encrypt the OAuth token blob. **Not installed by default** (D16). |
| **Encryption key (`.key`)** | A 32-byte url-safe-base64 Fernet key written to `cache/.key`, chmod `0o600`. **Stored beside the ciphertext it protects** (D15) — so the encryption only deters casual inspection. |
| **Plaintext fallback** | When `cryptography` is absent, the token is written as readable JSON to `cache/.spotify_tokens.enc` (misleadingly named) with only a WARNING log line. **Silent by design.** |
| **Directory permissions** | `cache/` is created with mode `0o700`; the token file is chmod `0o600`. Both are correct and worth preserving in any refactor. |
| **Client secret** | The Spotify app's server-side secret. Read from `SPOTIFY_CLIENT_SECRET`. `config.json` has an empty placeholder field, and `ConfigManager.save_config()` **would** write a real secret to a tracked file (D19). |
| **Client ID** | The public Spotify app identifier. Safe to log; treated like a secret by the docs' tone. |

## Environment & Filesystem Terms

| Term | Definition |
|---|---|
| **`env/.env`** | The **only** configuration file the application reads (`app/utils.py:5-6`). Git-ignored. `README.md` and `QUICKSTART.md` incorrectly instruct users to create it at the repository root. |
| **`env/.env.template`** | **Does not exist** anywhere in the repository. Two Linux setup scripts `cp` it unconditionally and abort under `set -e` (D3). |
| **Parent-directory resolution** | `os.path.join(os.path.dirname(__file__), '../logs')` — every runtime path is built relative to the *module file*, so the app only works when run from a source checkout, never from an installed package. |
| **Import-time side effect** | `assistant.py:11-17` creates `logs/` and installs a `RotatingFileHandler` at **module import**. So merely importing `app` (including from `__init__.py`) creates directories and opens a file handle. |
| **Rotating log** | `RotatingFileHandler` with `maxBytes=1_048_576` (1 MB) and `backupCount=5`, at DEBUG level, UTF-8. Total cap ~6 MB. |
| **`WAKE_WORD` (env)** | Read by `health_check.py:104` but **not** applied at startup by `assistant.py` — the effective wake word comes from the calibration file, falling back to the hardcoded `"jarvis"` in `audio.py:45`. |
| **Git-ignored `docs/`** | `.gitignore:13` ignores `docs/`, so this knowledge base cannot be committed (D1). |

## Notification Terms

| Term | Definition |
|---|---|
| **Notification backend** | One of: `win10toast` (Windows), `plyer.notification` (cross-platform), `notify-send` (Linux), `osascript` (macOS), `print()` (last resort). Selected once at construction. |
| **Backend fallback chain** | The ordered list `send_notification()` walks. **It cannot fall through**, because the `win10toast` and `plyer` branches return `True` even on `ImportError` (D9). |
| **`notify-send`** | libnotify CLI. Reached only if `win10toast` and `plyer` are both absent — in practice never, because the `plyer` branch reports false success first. |
| **Toast** | The Windows notification mechanism (`win10toast` wraps it). |
| **AppleScript** | macOS scripting language, used via `osascript -e`. Notification text **is** escaped and passed array-form to `subprocess.run` — no injection (07/D9 is the real finding here: the fallback cannot fire). |
| **stdout degradation** | With no backend available, every message becomes a `print()` to the terminal. Acceptable for a foreground app; the app is designed to run in the background, where this means silence. |

## Architecture Terms Used in This Knowledge Base

| Term | Meaning here |
|---|---|
| **L1 / L2** | Exploration depth. L1 = structure and headings read. L2 = full file read plus callers, callees, and data paths traced. |
| **Orchestrator** | `EnhancedVoiceAssistant` — the only component that owns control flow. |
| **ORPHANED** | A module reachable from no entry point. Verified by AST inbound-edge count, not by grep. |
| **SHIM** | A module whose entire body is a re-export. |
| **S1–S4** | Severity: Critical / High / Medium / Low. |
| **VERIFIED / INSPECTED / INFERRED** | Evidence class: reproduced by execution / proven by direct code reading at a cited line / reasoned but not executed. **No finding in this knowledge base is marked INFERRED**, because every listed finding was either executed or read at a specific line. |
| **Latent** | A defect that is currently harmless because its inputs are known and benign, but will misbehave on other input. |
| **Dead code** | Zero call sites, verified by reference sweep. |
| **Ruled-out false positive** | A hypothesis investigated and disproved; recorded so it is not re-investigated. See the table at the end of `07_FINDINGS_AND_ISSUES.md`. |

## Frequently Confused Project Terms

| Pair | Distinction |
|---|---|
| `app/config.py` vs. actual configuration | `config.py` is **dead**. Real configuration is 4 environment variables plus hardcoded paths in `assistant.py:31-44`. |
| `SPOTIFY_REDIRECT_URI` vs. `config.json.spotify.redirect_uri` | Only the **environment variable** is read. The JSON key is inert. |
| `WAKE_WORD` env vs. `calibration/.voice_calibration.json` | The env var is only read by the health check. At runtime the calibration file wins, then the hardcoded `"jarvis"`. |
| "rate limiter" (two of them) | `SpotifyRateLimiter` in `spotify_control.py` (per-method, unenforced in aggregate — D10) and `_apply_google_api_rate_limit()` in `audio.py` (per-instance, genuinely enforced for Google STT). They govern different APIs. |
| `spotify_oauth.cache_path` vs. `cache_path` constructor arg | The constructor arg is used to build `SecureTokenStorage`'s directory. The `cache_path` **attribute** on a real spotipy `SpotifyOAuth` is `None`, which is why `cleanup()`'s token purge never runs (D36). |
| "fallback to text mode" (documented) vs. Ctrl+C toggle (actual) | No automatic fallback exists. Text mode is entered only via SIGINT (D27). |
| `Self.recognizer` vs. the recognizer that listens | Two different objects. Only the local one in `listen_for_wake_word`/`listen_for_command` ever captures audio (D7). |
| `play` the verb vs. `play` in "playing" | `process_command` cannot tell them apart (D5). This single ambiguity breaks a documented feature. |