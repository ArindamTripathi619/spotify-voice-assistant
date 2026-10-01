# 03 — Module Reference

Per-module index of every public surface. **All line numbers in this document were verified
against the source.** Where a symbol does not exist, it is listed as such — several members
that a naive reading suggests (and that an earlier draft of this document wrongly claimed) do
not exist at all.

---

## `app/__init__.py` — 26 lines

**Role:** package facade. Re-exports 8 names.

```python
__version__ = "1.0.0"
__author__  = "DevCrewX"

from .assistant   import EnhancedVoiceAssistant
from .audio       import AudioManager
from .notifications import NotificationManager
from .platform_utils import get_platform, is_windows, is_linux, is_mac
from .spotify_control import SpotifyController
from .utils       import load_environment
```

**Critical caveat:** unconditional top-level imports. Importing `app` therefore requires
`spotipy`, `speech_recognition`, `pyttsx3`, and `python-dotenv`. Consequence:
`python -m app.health_check` cannot run in the situation it exists to diagnose.
Verified: `ModuleNotFoundError: No module named 'spotipy'` from both `python -m app` and
`python -m app.health_check` in a dependency-free environment. See 07/D2.

---

## `app/main.py` — 5 lines

```python
from .assistant import EnhancedVoiceAssistant

if __name__ == "__main__":
    assistant = EnhancedVoiceAssistant()
    assistant.run()
```

**Correction to the first pass:** this module uses a **relative** import, not an absolute one —
every module in the package does. The first pass claimed `from app.assistant import …` and
described `main.py` as "the only module that does not use relative imports". Both were wrong.

The documented invocation `python -m app.main` is nonetheless correct: run that way, `__package__`
is set to `"app"`, so the relative import resolves. Run as `python app/main.py` and `__package__`
is `""`, so the relative import raises — which is the real reason for the D38 finding, not an
absolute-vs-relative mistake.

---

## `app/__main__.py` — 8 lines

```python
from app.health_check import HealthCheck
if __name__ == "__main__":
    raise SystemExit(HealthCheck().main())
```

`python -m app` → the health check. Note the **exit codes are non-standard** (see
`health_check` below).

---

## `app/assistant.py` — 274 lines

**Role:** **the orchestrator.** Owns the control loop, signal handlers, the interactive text
REPL, the command router, and logging setup.

### Import-time side effects (module level, lines 11-17)

```python
log_dir = os.path.join(os.path.dirname(__file__), '../logs')
os.makedirs(log_dir, exist_ok=True)
handler = RotatingFileHandler(... voice_assistant.log ..., maxBytes=1_048_576, backupCount=5)
```

These run on **any** import of `app.assistant`, including via `__init__.py`.

### Public surface

| Member | Line | Behaviour |
|---|---|---|
| `__init__` | 21 | `self.notifier` (23) → `self.error_handler = ErrorHandler(...)` (26) → path setup (31) → clients (35, 43) → `_validate_environment()` (48). |
| `run` | 92 | Notifies (95), installs `handle_sigterm` (102) and `handle_sigint` (106), then `while self.is_running` (113). |
| `process_command` | **238** | The command router. See the dispatch table below. |
| `change_wake_word` | 190 | Interactive wake-word change. |
| `show_enhanced_tips` | 220 | Prints a tip; called from the run loop. |
| `text_mode_loop` | 162 | Blocking `input()` REPL. |
| `_cleanup_resources` | 151 | `hasattr`-guarded calls to `audio_manager.cleanup()` (155) and `spotify_controller.cleanup()` (157). |

**Correction to an earlier draft of this document:** there is **no** public `cleanup()` method and
no `_handle_command_error()` method on this class. `assistant.py` is 274 lines; line 278 does not
exist. Error handling in `process_command` is inline at `:273-274`.

**Private surface**

| Member | Line | Behaviour |
|---|---|---|
| `_validate_environment` | 48 | Docstring: "Validate required environment variables at startup." Raises `EnvironmentError`; notifies at 72-73. **Misplaced state init at 82-84**: `self.is_running = True`, `self.is_awake`, and `self.switch_to_text_mode = False` are assigned *inside the validation method*, so they only exist on the success path. |
| `handle_sigterm` / `handle_sigint` | 102 / 106 | SIGTERM → `is_running = False`. SIGINT → logs, sets `switch_to_text_mode = True` (109). Installed at 110-111. |

`app/assistant.py:8` imports five names from `error_handling`:
`ErrorHandler, ConfigurationError, error_handler, ErrorCategory, ErrorSeverity`.
**`ErrorHandler` is the only one used** (constructed at `assistant.py:26`, called at `:274`).
The other four — including the `error_handler` decorator and both enums — are imported and
never referenced. The real error path in `process_command` is
`self.error_handler.handle_error(e, f"Failed to process command: {command}")` at `:274`.

### `process_command` dispatch table (`assistant.py:238-274`) — VERIFIED ORDER

Every test is a substring test on the lowercased, stripped input. **First match wins.** There is
**no `else` branch** — an unmatched command is a silent no-op.

| # | Line | Condition | Action |
|---|---|---|---|
| 1 | 242 | `'play' in command and len(command.split()) > 1` | `play_song(...)`, with `the song`/`song called`/`track` stripped (243-246); **returns early** if non-empty |
| 2 | 250 | `any(w in c for w in ['play','start','resume','go'])` | `resume_playback()` |
| 3 | 252 | `any(w in c for w in ['pause','stop','halt'])` | `pause_playback()` |
| 4 | 254 | `any(w in c for w in ['next','skip','forward'])` | `next_track()` |
| 5 | 256 | `any(w in c for w in ['previous','back','last'])` | `previous_track()` |
| 6 | 258 | `'volume up' in c or 'louder' in c or 'turn up' in c` | `adjust_volume(+15)` |
| 7 | 260 | `'volume down' in c or 'quieter' in c or 'turn down' in c` | `adjust_volume(-15)` |
| 8 | 262 | `any(w in c for w in ['what','playing','current','now'])` | `get_current_track()` |
| 9 | 264 | `any(w in c for w in ['quit','exit','bye','goodbye'])` | notify + `is_running = False` |
| — | | **otherwise** | **silent no-op — no notification, no log** |

**Correction to an earlier draft of this document:** that draft listed a `'volume'` rule, a
bare `'play'` fallback rule, a `help`/`commands` rule, a `whats` keyword, and an
"❓ I didn't understand" fallback branch. **None of those exist.** Volume is matched as the
two-word phrases `volume up`/`volume down` (plus `louder`/`quieter`/`turn up`/`turn down`), and
there is no help route and no unmatched-input feedback.

**Executed dispatch results** (recording fakes for `spotify_controller`, transcribed from a
faithful re-implementation of `:240-274`):

```
'quit' / 'exit' / 'bye'    -> notify + is_running=False   OK
'goodbye'                  -> resume_playback()            rule 2 eats rule 9 (D6)
'play bohemian rhapsody'   -> play_song('bohemian rhapsody')          OK
'what is playing'          -> play_song('ing')             rule 1 (D5)
"what's playing"           -> play_song('ing')             rule 1 (D5)
'now playing'              -> play_song('ing')             rule 1 (D5)
'go back to previous track'-> resume_playback()            rule 2 (D6)
'stop doing that'          -> pause_playback()             'stop' substring, unintended
'next' / 'skip' / 'forward'-> next_track()                             OK
'back' / 'last' / 'previous' -> previous_track()                        OK
'volume up' / 'louder'     -> adjust_volume(+15)                        OK
'turn it up'               -> SILENT NO-OP                'turn up' needs adjacency
'hello there'              -> SILENT NO-OP
'help'                     -> SILENT NO-OP                 no help route exists
'what is this' / 'now'     -> get_current_track()                       OK
'what song'                -> get_current_track()                       OK
'current song'             -> get_current_track()                       OK
```

Rule 8 **is** reachable — but only by utterances that avoid `'play'`, `'go'`, and `'back'`.
`get_current_track` is therefore reachable from voice input in general, contrary to an earlier
draft of this document; what is unreachable is the *documented* phrasings "what's playing" /
"now playing", both of which rule 1 intercepts.

**Two substring traps not previously documented:** `'stop doing that'` pauses playback (rule 3
matches `'stop'` in any sentence), and `'turn it up'` / `'turn it down'` are silent no-ops
because rules 6/7 require `'turn up'`/`'turn down'` as **contiguous** substrings.

---|---|---|---|
| 1 | 242 | `'play' in command and len(command.split()) > 1` | `play_song(command.split('play', 1)[1].strip())` |
| 2 | | `'stop' in command or 'pause' in command` | `pause_playback()` |
| 3 | 250 | `any(w in command for w in ['play','start','resume','go'])` | `resume_playback()` |
| 4 | | `any(w in command for w in ['next','skip'])` | `next_track()` |
| 5 | | `any(w in command for w in ['previous','back','last'])` | `previous_track()` |
| 6 | | `any(w in command for w in ['volume','louder','quieter'])` | `adjust_volume(+15 / −15)` |
| 7 | | `'play' in command` | `resume_playback()` |
| 8 | | `any(w in command for w in ['what','current','whats'])` | `get_current_track()` |
| 9 | 264 | `any(w in command for w in ['quit','exit','bye','goodbye'])` | notify + `is_running = False` |
| 10 | | `any(w in command for w in ['help','commands'])` | notify help |
| — | | otherwise | notify "❓ I didn't understand" → `False` |

**Executed dispatch results** (recording fake for `spotify_controller`):

```
'quit'                     -> notify("👋 Enhanced Assistant Stopping"), is_running=False   ✔
'exit'                     -> notify, is_running=False                                    ✔
'bye'                      -> notify, is_running=False                                    ✔
'goodbye'                  -> resume_playback()                                           ✘ rule 3 eats rule 9
'volume down'              -> adjust_volume(-15)                                          ✔
'louder' / 'quieter'       -> adjust_volume(±15)                                          ✔
'next' / 'skip'            -> next_track()                                                ✔
'back' / 'last'            -> previous_track()                                            ✔
'play bohemian rhapsody'   -> play_song('bohemian rhapsody')                             ✔
'play a song by drake'     -> play_song('a song by drake')        ⚠ filler words retained
'what is playing'          -> play_song('ing')                        ✘ D5
'go back to previous track'-> resume_playback()                      ✘ D6
```

**Key insight for D6:** line 264 explicitly lists `'goodbye'` as a quit word. The intent is
unambiguous. It simply never executes, because rule 3 (`'go' in command`) matches `goodbye`
first. This is an ordering bug, not a missing keyword.

**Ruled out:** an earlier probe reported `'quit'` raising `AttributeError: error_handler`.
That was a harness artifact (`__new__` without `notifier`). Re-tested with collaborators
populated: `quit`/`exit`/`bye` all work. Not a defect.

---

## `app/audio.py` — 387 lines

**Role:** microphone, ambient calibration, Google STT, wake-word matching, TTS (unused),
sensitivity policy.

### Constructor (line 14-32)

| Line | Statement |
|---|---|
| 15 | `self.recognizer = sr.Recognizer()` |
| 16 | `self.tts = pyttsx3.init()` — **not wrapped in try/except**; can abort construction |
| 23 | `self.is_awake = False` |
| 26 | `self.attempt_count = 0` |

### The configured-but-unused recognizer

`setup_enhanced_audio()` (line 45) sets **eight** attributes on `self.recognizer`:

```
:50  energy_threshold = 200          (not 300)
:51  dynamic_energy_threshold = True
:52  dynamic_energy_adjustment_damping = 0.1
:53  dynamic_energy_ratio = 1.2
:54  pause_threshold = 1.0
:55  phrase_threshold = 0.2
:56  non_speaking_duration = 0.5
:57  operation_timeout = None
```

**None of these ever affect capture**, because both listening methods create their own local
recognizer:

| Method | Line | Local recognizer | Calls `adjust_for_ambient_noise` on it? |
|---|---|---|---|
| `listen_for_command` | 258 | `:270` | **Yes** — `:286`, `duration=0.2` |
| `listen_for_wake_word` | 353 | `:356` | **Yes** — `:359`, `duration=0.2` |

So the precise finding is narrower than "calibration does nothing": the local recognizers do
receive a fresh 0.2 s ambient sample, but they do **not** receive the saved/tuned thresholds
from `self.recognizer`. The 0.2 s adaptation overrides the 2 s (`smart_calibration`) / 4 s
(`enhanced_calibration`) tuning entirely. See 07/D7.

Project-wide grep for `self.recognizer` returns exactly: line 15 (assignment), 50-57
(the eight settings), and 386-387 (the two mutations inside `adjust_sensitivity`). Nothing
ever passes it to `listen()`.

### The three calibration methods (all write to a local recognizer)

| Method | Line | Local recognizer | `adjust_for_ambient_noise` | Effect |
|---|---|---|---|---|
| `smart_calibration` | 193 | `:196` | `:203`, `duration=2` | Sets `energy_threshold` from saved data (`:199`), then discarded. |
| `enhanced_calibration` | 209 | `:211` | `:215`, `duration=4` | Threshold only ever changes **if no sample succeeds** (`:224` ×0.8, floor `:226`=250, `:234`=300). Dead local. |
| `adjust_sensitivity` | 382 | n/a | n/a | **No loop at all.** Body guarded by `if self.attempt_count > 2` (`:383`); `attempt_count` is initialised to 0 (`:26`) and **never incremented anywhere** → the body is a permanent no-op. See 07/D8. |

### Calibration persistence

| Member | Line | Note |
|---|---|---|
| `_validate_calibration_path` | 83 | |
| `load_calibration_data` | 104 | Required fields checked at `:121`: `['date', 'energy_threshold', 'pause_threshold']` |
| `save_calibration_data(energy_threshold, pause_threshold, success_rate=1.0)` | 139 | Validates inputs (`:147-148`); writes `'date'` (`:156`) |

**Correction to the "6 float keys" framing used elsewhere in this knowledge base:** the
calibration file's schema is `date`, `energy_threshold`, `pause_threshold`, `success_rate`.
`wake_word` is **not** part of the validated schema. `README.md:178-179` describes
`.voice_calibration.json` with a "7-day validity" that the code does not implement (there is
no expiry check anywhere in `load_calibration_data`).

### Other members

| Member | Line | Note |
|---|---|---|
| `cleanup` | 33 | First method; not at the end of the file as one would expect |
| `select_best_microphone` | 70 | First working device index |
| `speak(text, wait=False)` | 242 | Spawns `speak_thread` (244). **No call sites anywhere in the codebase** (verified by grep). |
| `_apply_google_api_rate_limit` | 308 | 60 req/min ceiling, sleeps inline |
| `_try_speech_recognition(recognizer, audio)` | 322 | Shared Google STT call for both listeners |

`is_awake` (`:23`) is set in the constructor and never read or written again.

---

## `app/spotify_control.py` — 485 lines

**Role:** the entire Spotify integration. Defines **two local exception classes** of its own.

| Line | Definition |
|---|---|
| 19 | `class AuthenticationError(Exception)` — local, **shadows nothing** (spotipy's is `spotipy.SpotifyException`) |
| 24 | `class ConnectionError(Exception)` — **shadows the builtin `ConnectionError`** |

Neither is raised or caught anywhere. `ConnectionError` at line 24 shadows the Python builtin
for the whole module, which is a latent hazard for any future `except ConnectionError` in this
file.

### `SecureTokenStorage` (line 29) — the spotipy `cache_handler`

spotipy's documented protocol requires **`get_cached_token()`** and **`save_to_cache(token_info)`**
(plus optional `clear_cached_token()`).

| Method | Line | Implements the protocol? |
|---|---|---|
| `__init__(self, cache_dir)` | 32 | — (note: the parameter is `cache_dir`, not `cache_path`) |
| `_setup_encryption` | 39 | — |
| `get_cached_token` | 58 | ✔ |
| `save_token_to_cache(self, token_info)` | 78 | **✘ WRONG NAME** — see below |
| `save_to_cache` | — | **DOES NOT EXIST** |
| `clear_cached_token` | — | **DOES NOT EXIST** |
| `encrypt_file` / `decrypt_file` | — | **DO NOT EXIST** (earlier drafts of this document claimed they did; they do not) |

**⚠️ `save_to_cache` is missing.** Verified by grep across the module: the only occurrences of
the token-save concept are `save_token_to_cache` (definition, `:78`) and `get_cached_token`
(`:58`). spotipy calls `self._cache_handler.save_to_cache(token_info)` after a successful
authorization, so this is expected to raise `AttributeError` on the first successful OAuth.
See 07/D40 — confirming it requires a live OAuth flow, which was not available here.

### `SpotifyRateLimiter` (line 98)

| Member | Line |
|---|---|
| `__init__(self, calls_per_second=8)` | 101 — it is a **per-second** rate, not a per-minute request count |
| `__call__(self, func)` | 106 — a real decorator |
| 429-retry handling | 120 — `int(e.headers.get('Retry-After', 60))` |

Decorated methods (`:172, 229, 270, 286, 317, 348, 367`) each use
`@SpotifyRateLimiter(calls_per_second=6)`. **Because each decorator expression evaluates a
fresh `SpotifyRateLimiter()` at class-definition time, every method gets its own independent
bucket.** `self.rate_limiter = SpotifyRateLimiter(calls_per_second=8)` at `:149` is
constructed and never used. There is no `_rate_limited_call` method. See 07/D10.

### `SpotifyController` (line 127) — actual method inventory

| Method | Line | Notes |
|---|---|---|
| `__init__(client_id, client_secret, redirect_uri, cache_path, notifier=None)` | 128 | `cache_dir = os.path.dirname(cache_path)` (136) |
| `play_song(song_name)` | 173 | `search(q=song_name, type='track', limit=3)` (174) → `items[0]` (177) → `start_playback(uris=[track['uri']])` (179) |
| `resume_playback` | 230 | |
| `pause_playback` | 271 | |
| `next_track` | 287 | `track = current['item']` at 293 |
| `previous_track` | 318 | `track = current['item']` at 324 |
| `adjust_volume(change)` | 349 | `volume = max(0, min(100, current['device']['volume_percent'] + change))` (353) → `self.spotify.volume(volume)` |
| `get_current_track` | 368 | `track = current['item']` at 372 — **unreachable from the router** |
| `_find_active_device()` | 403 | Returns the first device with `is_active` **or** `type == 'Computer'` |
| `_launch_and_setup_device()` | 411 | `launch_spotify()`, then polls `_find_active_device()` **10× at 0.3 s = 3 s**, then `transfer_playback(force_play=True)` |
| `_handle_no_active_device(action_name="playback")` | 453 | Notifies "❌ Spotify Not Running" |
| `cleanup` | 474 | |

**Device handling is exception-driven, not pre-flight.** `play_song` calls `start_playback()`
with **no** `device_id` (179), catches `SpotifyException`, and tests
`'No active device' in str(e)` (181) as a **string match**. Only then does it call
`_handle_no_active_device()` → `_launch_and_setup_device()` → retry `start_playback` with a
`device_id` (185). There is no `get_active_device()`, no `activate_spotify()`, and **no
re-authentication per command** — an earlier draft of this document wrongly described one;
that claim is retracted.

`adjust_volume` reads volume from `current['device']['volume_percent']`, confirming it is
**device-scoped**, and calls `self.spotify.volume(absolute_value)` — **not** `volume_up` /
`volume_down`. It special-cases `'Cannot control device volume'` with a friendly message and
has **no `else` branch**: if `current['device']` is falsy, nothing happens and no notification
is shown.

`cleanup` (474) guards with `hasattr(self.spotify_oauth, 'cache_path')` (478). spotipy's
`SpotifyOAuth` *does* have that attribute (value `None`), so the guard passes and
`os.path.exists(None)` raises `TypeError`, which is caught (480) and then **silently discarded**
because `self.error_handler` is `None` (481). The comment claims it "clears cached tokens"; it
never does. See 07/D36 — the no-op holds whether `cache_path` is `None`, spotipy's default
`".cache"`, or absent, so it does not depend on the unresolved spotipy question. The file also
ends with an abandoned refactor note (484-485):
`# All Spotify control methods will be moved here from EnhancedVoiceAssistant`.

**Do not look for** `play_music`, `play_song_by_artist`, `check_spotify_status`,
`_rate_limited_call`, `get_active_device`, `activate_spotify`, or `search_spotify_track` —
all verified absent (0 `def` matches each).

---

## `app/platform_utils.py` — 154 lines

Stdlib only — **no `psutil` import at all** (see 07/D26).

| Function | Line | Notes |
|---|---|---|
| `get_platform` | 5 | |
| `is_windows` / `is_linux` / `is_mac` | 9 / 13 / 17 | |
| `get_spotify_executable_path` | 21 | Windows candidate list `:25-30`; Windows-Store probe `:33-45`; every candidate passed through `os.path.expandvars` at `:49` before `os.path.exists`. Linux uses `shutil.which` (`:57`). |
| `get_notification_command` | 88 | |
| `get_audio_requirements` | 98 | no call sites |
| `setup_platform_environment` | 134 | no call sites |

**Verified correct, contrary to an earlier draft:** the `"C:\\Users\\%USERNAME%\\AppData\\Roaming\\Spotify\\Spotify.exe"`
literal at `:27` **is** expanded — `os.path.expandvars(path)` runs on every candidate at `:49`.
07/D23 is retracted. `import logging` is repeated inside function bodies (`:34`, `:44`) — 07/D50.

---

## `app/notifications_cross_platform.py` — 194 lines

**The best-hardened module in the project.** Its fallback design and its input sanitisation are
both correct — which is precisely what makes D9 (the fallback cannot fire) a subtle defect.

| Method | Line |
|---|---|
| `__init__` | 5 |
| `setup_notifications` | 10 — per-platform dispatch; unknown platform or exception ⇒ `notifications_enabled = False` (`:20, 23`) |
| `_setup_windows_notifications` | 26 |
| `_setup_linux_notifications` | 47 |
| `_setup_mac_notifications` | 71 |
| `send_notification(title, message, icon, urgency, timeout)` | **92** — **title first** |
| `_try_send_with_backend` | 116 — `False` for an unknown backend (`:127`), `True` after dispatch (`:128`) |
| `_send_windows_toast` | 130 — swallows everything (`:141`) |
| `_send_plyer_notification` | 144 — swallows everything (`:153`) |
| `_send_linux_notification` | 156 — swallows everything (`:171`) |
| `_send_mac_notification` | 174 — **sanitises**, see below |

`send_notification` builds `backends_to_try` from the primary backend, appends `'plyer'` when
available (`:100-102`), loops (`:104-111`), then falls back to `print()` (`:113-114`).

**D9:** the loop cannot fire. All four send methods catch every exception internally and only
`logging.warning`, so `_try_send_with_backend` always returns `True` on its first iteration and
the console fallback is unreachable. The fix is to have each send method return `bool`.

**D9 / D35 retracted.** `_send_mac_notification` (`:174-194`) is genuinely defensive:
length-limits to 100/300 chars, escapes `"` → `\"`, replaces newlines with spaces, and calls
**array-form** `subprocess.run(['osascript', '-e', script], capture_output=True, timeout=5)`.
No `shell=True`, no `which`, no injection. `import shlex` at `:177` is unused (D49).

---

## `app/launch_spotify_cross_platform.py` — 112 lines

| Function | Line |
|---|---|
| `launch_spotify` | 7 — the only entry point; dispatching per platform |
| `_launch_spotify_windows` | 29 — `subprocess.Popen([path], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)` (`:33`) |
| `_launch_spotify_linux` | 43 — Flatpak preferred when `"flatpak" in spotify_path` (`:48-49`), `com.spotify.Client` |
| `_launch_spotify_mac` | 63 |
| `check_spotify_installation` | 73 |
| `get_spotify_installation_instructions` | 78 — includes the `flatpak install flathub com.spotify.Client` hint (`:92`) |

`launch_spotify` is called from `spotify_control.py:412` and is **not** dead. There is **no**
`wait_for_spotify` function — the 10×/0.3 s poll lives in `SpotifyController._launch_and_setup_device`
(`spotify_control.py:425-429`) instead. `subprocess.CREATE_NO_WINDOW` is a bare attribute access,
safe only because the enclosing function is Windows-only (D51).

---

## `app/error_handling.py` — 308 lines

**The best-structured module in the project, and almost entirely unused** (see 07/D18). A real
exception hierarchy with a shared base class, not a bag of independent exceptions.

| Surface | Line | Used? |
|---|---|---|
| `ErrorSeverity` / `ErrorCategory` enums | 13 / 21 | imported by `assistant.py:8`, **never referenced there** |
| `SpotifyVoiceAssistantError` (base) | 33 | never raised |
| 7 subclasses: `NetworkError` 49, `AuthenticationError` 55, `RateLimitError` 61, `AudioError` 68, `FileSystemError` 74, `SpotifyError` 80, `ConfigurationError` 86 | 49-88 | **never raised** — all inherit the base |
| `ErrorHandler.__init__` | 95 | constructed at `assistant.py:26` |
| `ErrorHandler.handle_error` | 101 | **called once** — `assistant.py:274` |
| `_standardize_error` | 126 | only from `handle_error` |
| `_log_error` / `_notify_user` / `_create_user_friendly_message` | 170 / 186 / 228 | only from `handle_error` |
| `get_error_stats` | 258 | no call sites |
| `error_handler(category, severity, notify_user, reraise, fallback_value)` | 267 | applied to **no** function |
| `safe_call` | 302 | no call sites |

`assistant.py:274` calls `handle_error(e, f"Failed to process command: {command}")` — positionally,
so the string lands in `context`.

**D11 retracted and merged into D18.** The decorator at `:276-287` does **not** raise
`AttributeError` when `error_handler` is absent: it `hasattr`-checks both `error_handler` and
`_error_handler` and falls back to constructing a fresh `ErrorHandler()`. It is correctly written
and simply never applied.

---

## `app/config.py` — 286 lines — **ORPHANED**

AST-verified: zero inbound imports. `AudioConfig`, `SpotifyConfig`, `NotificationConfig`,
`AssistantConfig` dataclasses; `get_absolute_path()` (uses `lstrip('../')` at 255);
`ConfigManager` with `load_config` / `save_config` / `get_setting` / `set_setting` /
`validate_config`; and a `__main__` block that calls `create_default_config_file()`.

---

## `app/health_check.py` — 369 lines

**Role:** standalone diagnostic CLI. **Exit codes are non-standard and were initially
mis-documented**: `main()` (355) exits `1` for `critical`, `2` for `warning`, `0` otherwise.
So **`2` means warning, not failure.**

| Check | Line | Notes |
|---|---|---|
| `__init__` | 20 | |
| `setup_logging` | 29 | |
| `check_python_version` | 37 | |
| `check_python_packages` | 47 | aggregates properly (`:62,70,79`) |
| `check_environment_variables` | 81 | aggregates properly (`:93,101,110`) |
| `check_audio_system` | 112 | opens the mic |
| `check_spotify_connectivity` | **140** | `SpotifyClientCredentials` (152) + a real `search()` call (159) — reports "✅ Spotify API connectivity working" (162). Accurate for what it does, but it tests the **client-credentials** flow, which the application never uses. |
| `check_platform_support` | 169 | |
| `check_file_permissions` | 199 | `rel_path.lstrip('../')` (211), `os.makedirs` (215), `.test_write` (218) — mutates the repo |
| `check_network_connectivity` | 231 | endpoints `speech.googleapis.com:443` and `api.spotify.com:443` (234-237); `all_good = True` (238) is **never** set to `False` — the `except` deliberately only warns (248) |
| `run_all_checks` | 252 | |
| `display_summary` | 306 | |
| `main` | 355 | see exit codes above |

Note: the network check and the Spotify check both emit a line beginning "Spotify API
connectivity" — one from a TCP probe, one from a real API call. This is duplication, **not** a
false positive; an earlier draft of this document claimed otherwise and is corrected in 07/D24.

---

## `app/utils.py` — 7 lines

```python
def load_environment():
    env_path = os.path.join(os.path.dirname(__file__), "../env/.env")
    load_dotenv(env_path)
```

**`<repo>/env/.env` is the only file the application ever reads for configuration.**
`load_dotenv` does not override real environment variables.

---

## Shim modules

| File | Lines | Content |
|---|---|---|
| `app/notifications.py` | 6 | re-exports `CrossPlatformNotificationManager as NotificationManager` |
| `app/launch_spotify.py` | 6 | re-exports `launch_spotify`, `check_spotify_installation` |

---

## `recalibrate` / `wake` — text mode only, not voice

`README.md:55, 198, 200, 207, 230` tells the user to type `recalibrate` and `wake` **in text
mode**, and in that context both work:

- `text_mode_loop` (`:162`) — `'wake'` → `change_wake_word()` (`:176-177`);
  `'recalibrate'` → `audio_manager.enhanced_calibration()` (`:178-183`).
- `change_wake_word` is therefore **not** dead — it is called at `:177`.

But `process_command` (`:238-274`) handles **neither**. Spoken *"recalibrate"* therefore falls
Text mode has `help` → `show_enhanced_tips()` (`:174`), `wake` → `change_wake_word()`
(`:176-177`) and `recalibrate` → `enhanced_calibration()` (`:178-183`); voice mode routes
through `process_command` and has **none** of them. The real finding is that voice/text
**asymmetry** (07/D43) —
and `recalibrate` invokes `enhanced_calibration` (`audio.py:209`), which tunes a *local*
recognizer and discards it, so it cannot persist anything either way (07/D7).

**Names that genuinely do not exist anywhere in `app/`** (0 `def` matches each):
`get_active_device`, `activate_spotify`, `search_spotify_track`, `play_music`,
`play_song_by_artist`, `check_spotify_status`, `_rate_limited_call`, `wait_for_spotify`,
`get_microphone_names`, `get_cpu_usage`, `get_memory_usage`, `get_terminal_command`,
`get_spotify_data_path`, `encrypt_file`, `decrypt_file`, `save_to_cache`, `clear_cached_token`.