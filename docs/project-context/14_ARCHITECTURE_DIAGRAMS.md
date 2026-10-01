# 14 — Architecture Diagrams

A visual index of the whole system. Every diagram here is derived from the source at commit
`69a9724` and cross-references the prose docs. **Nothing in this file is aspirational** — if a
box exists, there is code for it; if an edge is dashed, the edge does not exist at runtime.

Companion prose: [02 — Architecture](02_ARCHITECTURE.md) (style & patterns),
[04 — Data Flows](04_DATA_FLOWS.md) (step-by-step traces),
[03 — Module Reference](03_MODULE_REFERENCE.md) (per-function detail).

---

## D-1 · System context — what the process touches

The assistant is a single foreground process. It talks to exactly three things outside itself:
the Spotify Web API, Google's speech endpoint, and the local operating system.

```mermaid
flowchart LR
    U(["👤 User<br/>speaks / types"])

    subgraph PROC["spotify-voice-assistant · one Python process"]
        APP["EnhancedVoiceAssistant"]
    end

    SPOTIFY[("Spotify Web API<br/>api.spotify.com")]
    GOOGLE["Google Speech-to-Text<br/>speech.googleapis.com"]
    OS["Local OS<br/>notifications · process launch · audio device"]

    U -->|"voice, after wake word"| APP
    U -->|"Ctrl+C then keystrokes"| APP
    APP -->|"HTTPS: playback, search, devices"| SPOTIFY
    APP -->|"HTTPS: PCM audio → transcript"| GOOGLE
    APP -->|"notify-send / osascript / toast<br/>subprocess spawn · Spotify desktop app"| OS

    classDef ext fill:#eef4ff,stroke:#4a6fa5
    classDef core fill:#fff4e6,stroke:#c98a2e,stroke-width:2px
    class SPOTIFY,GOOGLE,OS ext
    class APP core
```

**Caveats that shape this picture**

| Fact | Consequence | Finding |
|---|---|---|
| Audio leaves the machine for Google | No offline mode; Google quota + internet are hard requirements | — |
| Audio is recognised with a **30 s timeout per wake poll** | Each idle cycle costs one blocking network round-trip | — |
| Spotify OAuth happens during `__init__` | First run can block on a browser before the loop starts | [D40](07_FINDINGS_AND_ISSUES.md) |
| Notifications are the *only* user-facing output | With no notification backend, everything degrades to `print()` | [D9](07_FINDINGS_AND_ISSUES.md) |
| `config/` is not part of the runtime | Shown greyed in [D-3](#d-3--container--what-is-actually-loaded-at-runtime) | [D17](07_FINDINGS_AND_ISSUES.md) |

---

## D-2 · Component graph — all 15 modules

```mermaid
flowchart TD
    subgraph ENTRY["Entry points"]
        MAIN["app/main.py · 5 LOC"]
        DUNDER["app/__main__.py · 8 LOC"]
        PKG["app/__init__.py · 26 LOC<br/>⚠️ eager, 8 re-exports"]
    end

    subgraph CORE["Runtime core"]
        ASST["app/assistant.py · 274 LOC<br/>EnhancedVoiceAssistant<br/>THE ORCHESTRATOR"]
        AUD["app/audio.py · 387 LOC<br/>AudioManager"]
        SPT["app/spotify_control.py · 485 LOC<br/>SpotifyController"]
    end

    subgraph ADAPT["OS adaptation"]
        NSHIM["app/notifications.py · 6 LOC<br/>shim"]
        NCP["app/notifications_cross_platform.py · 194 LOC"]
        LSHIM["app/launch_spotify.py · 6 LOC<br/>shim"]
        LSCP["app/launch_spotify_cross_platform.py · 112 LOC"]
        PU["app/platform_utils.py · 154 LOC<br/>the ONLY OS predicate"]
    end

    subgraph SUPPORT["Support"]
        HC["app/health_check.py · 369 LOC"]
        UTIL["app/utils.py · 7 LOC"]
        EH["app/error_handling.py · 308 LOC<br/>⚠️ ~95% unreached"]
    end

    subgraph DEAD["Never imported by anything"]
        CFG["app/config.py · 286 LOC<br/>⚠️ 100% unreachable"]
    end

    MAIN --> ASST
    DUNDER --> HC
    PKG -. "imports everything" .-> ASST
    PKG -.-> AUD
    PKG -.-> SPT

    ASST --> AUD
    ASST --> SPT
    ASST --> NSHIM
    ASST --> UTIL
    ASST --> EH

    NSHIM --> NCP
    NCP --> PU
    LSHIM --> LSCP
    LSCP --> PU
    SPT --> LSHIM
    SPT --> PU
    SPT -. "import, unused" .-> EH
    AUD -. "import, unused" .-> EH
    HC --> PU

    CFG -. "no inbound imports" .-x ASST

    classDef dead fill:#f6f6f6,stroke:#999,stroke-dasharray:5 5,color:#666
    classDef warn fill:#fff0f0,stroke:#c04a4a
    classDef ok fill:#f0fff4,stroke:#3a9a5c
    classDef shim fill:#f7f5ff,stroke:#7a6fb0,stroke-dasharray:3 3
    class CFG dead
    class EH,PKG warn
    class ASST,AUD,SPT,PU,HC,UTIL,NCP,LSCP ok
    class NSHIM,LSHIM shim
```

**Dependency rule that holds everywhere:** `assistant` → {audio, spotify_control, notifications,
utils}. Everything else flows downward. `platform_utils.py` depends on the standard library
only. **No import cycles exist** (verified by AST walk — see [02](02_ARCHITECTURE.md)).

Two red flags are structural, not cosmetic:

- **`app/__init__.py` is the reason `health_check` cannot run.** Any `python -m app.*` executes
  the package body, which imports `spotipy`, `speech_recognition` and `pyttsx3`. So the
  missing-dependency diagnostic *requires* the dependencies. → [D2](07_FINDINGS_AND_ISSUES.md)
- **`config.py` has zero inbound imports.** `config/config.json` is never read at runtime.
  → [D17](07_FINDINGS_AND_ISSUES.md)

---

## D-3 · Container — what is actually loaded at runtime

Trace of a real `python -m app.main`. Dashed = declared/imported but never exercised.

```mermaid
flowchart LR
    subgraph IMPORT["Module import time — before any object exists"]
        I1["assistant.py:11-17<br/>os.makedirs('../logs')"]
        I2["RotatingFileHandler<br/>1 MiB × 5"]
        I3["logging.basicConfig(INFO)"]
    end

    subgraph INIT["EnhancedVoiceAssistant.__init__ — assistant.py:21-90"]
        C1["load_environment()<br/>load_dotenv('&lt;repo&gt;/env/.env')"]
        C2["NotificationManager()"]
        C3["ErrorHandler(logger, notifier)"]
        C4["_validate_environment()<br/>raises EnvironmentError if no creds"]
        C5["AudioManager(calibration_file, notifier, wake_word)"]
        C6["SpotifyController(id, secret, uri, cache_path, notifier)"]
    end

    subgraph RUN["run() — assistant.py:92-149"]
        R1["setup_enhanced_audio()<br/>tunes 8 recognizer attrs"]
        R2["signal handlers<br/>SIGTERM→stop · SIGINT→text mode"]
        R3["THE CONTROL LOOP"]
        R4["_cleanup_resources()"]
    end

    subgraph GONE["Declared but never reached"]
        X1["config.ConfigManager<br/>never constructed"]
        X2["error_handling.error_handler<br/>decorator: 0 uses"]
        X3["AudioManager.speak()<br/>0 call sites"]
        X4["adjust_sensitivity()<br/>no-op"]
        X5["switch_to_text_mode<br/>only SIGINT sets it"]
    end

    I1 --> I2 --> I3 --> C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> R1 --> R2 --> R3 --> R4

    classDef bad fill:#fff0f0,stroke:#c04a4a,stroke-dasharray:4 3,color:#8a3030
    class X1,X2,X3,X4,X5 bad
```

> **Note on ordering.** `is_running`, `is_awake`, `switch_to_text_mode` and `_lock` are
> initialised at `assistant.py:82-88` — *inside* `_validate_environment()`, after its early
> return. They therefore only exist on the success path. Code-organisation defect, not a
> functional one.

---

## D-4 · The control loop

This is the only loop in the program. It is single-threaded, blocking, and network-bound.

```mermaid
flowchart TD
    START(["run()"]) --> SETUP["setup_enhanced_audio()"]
    SETUP --> NOTIFY["notify: 😴 Wake Word Mode Active"]
    NOTIFY --> SIG["install SIGTERM / SIGINT handlers"]
    SIG --> LOOP{"while self.is_running"}

    LOOP -->|"false"| CLEAN["_cleanup_resources()"]
    LOOP -->|"true"| TEXT{"switch_to_text_mode?"}
    TEXT -->|"true — set only by Ctrl+C"| RESET["flag = False"]
    RESET --> TML["text_mode_loop()<br/>blocking input() REPL"]
    TML --> REANN[("re-notify: back to voice mode")]
    REANN --> LOOP

    TEXT -->|"false"| AWAKE{"is_awake?"}
    AWAKE -->|"false — the normal path"| WAKE["listen_for_wake_word()<br/>timeout 30 s"]
    WAKE --> HIT{"wake word<br/>detected?"}
    HIT -->|"no"| LOOP
    HIT -->|"yes"| SET1["is_awake = True<br/>notify: 👂 Assistant Awakened"]
    SET1 --> CMD["listen_for_command()<br/>timeout 3 s"]
    CMD --> GOT{"transcript?"}
    GOT -->|"no"| OFF1["is_awake = False"] --> LOOP
    GOT -->|"yes"| PROC["process_command(text)"]
    PROC --> OFF2["is_awake = False"] --> LOOP

    AWAKE -->|"true — unreachable"| DEAD["is_awake = False"]

    LOOP -.->|"any exception"| ERR["log · notify 💥 · cleanup · re-raise<br/>process terminates"]
    ERR --> CLEAN

    classDef dead fill:#f6f6f6,stroke:#999,stroke-dasharray:4 3
    classDef term fill:#ffe8e8,stroke:#b03a3a
    class DEAD dead
    class ERR,START,CLEAN term
```

Three structural facts worth internalising:

1. **`is_awake` is always cleared before the next iteration.** The `else` branch at
   `assistant.py:141-142` is therefore dead code. → [D52](07_FINDINGS_AND_ISSUES.md)
2. **Ctrl+C does not quit.** `SIGINT` sets `switch_to_text_mode`; quitting requires typing
   `quit`/`exit`/`q`, or speaking a quit phrase.
3. **A fatal error terminates the process.** `run()` re-raises after cleanup. There is no
   supervisor, no retry-with-backoff, no circuit breaker.

---

## D-5 · Voice cycle — wake word to Spotify call

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant A as EnhancedVoiceAssistant
    participant AM as AudioManager
    participant SR as speech_recognition
    participant G as Google STT
    participant SC as SpotifyController
    participant S as Spotify Web API
    participant N as Notifications

    U->>A: (idle loop) listen_for_wake_word()
    A->>AM: listen_for_wake_word()
    Note over AM: builds a LOCAL sr.Recognizer()<br/>— self.recognizer is ignored (D7)
    AM->>AM: r.adjust_for_ambient_noise(duration=0.2)
    AM->>SR: r.listen(source, timeout=30)
    SR->>G: HTTPS POST audio → transcript
    G-->>SR: text or UnknownValueError
    SR-->>AM: text
    AM->>AM: _apply_google_api_rate_limit()<br/>45 calls/min fixed window (audio.py:308)
    AM->>AM: wake_word.lower() in text.lower()<br/>naive substring test
    AM-->>A: True / False

    alt wake word matched
        A->>N: 👂 Assistant Awakened
        A->>AM: listen_for_command(timeout=3)
        Note over AM: 3 fallback attempts:<br/>en-US → en-GB → en-US show_all<br/>(confidence > 0.3)
        AM->>G: HTTPS POST audio → transcript
        G-->>AM: text
        AM-->>A: transcript or None
        A->>A: process_command(text)
        A->>SC: e.g. play_song('Hotel California')
        SC->>S: search(q=..., type=track)
        S-->>SC: items[]
        alt no result
            SC->>N: ❌ not found
        else no active device
            SC->>N: 🎵 launching Spotify…
            SC->>SC: _launch_and_setup_device()
            SC->>N: ✅ ready
        else success
            SC->>S: PUT /me/player/play
            SC->>N: ▶️ Now playing …
        end
    end
```

> **The rate limiter is correct but nearly unused.** `_apply_google_api_rate_limit()`
> (`audio.py:308`) enforces 45 calls/min, yet only *one* of its two call sites invokes it.
> → [D47](07_FINDINGS_AND_ISSUES.md)

---

## D-6 · Command dispatch — the exact 9-rule chain

`process_command` (`assistant.py:238-274`) is a flat substring chain with no tokenizer and no
normalisation beyond `.lower().strip()`. **The first matching rule wins.** This is the single
largest source of user-visible bugs.

```mermaid
flowchart TD
    IN(["command string"]) --> NORM["command.lower().strip()"]

    NORM --> R1{"R1 · 'play' in cmd<br/>AND len(split()) > 1"}
    R1 -->|yes| R1A["strip 'the song' / 'song called' / 'track'<br/>→ play_song(rest)"]
    R1 -->|no| R2

    R2{"R2 · play | start |<br/>resume | go"}
    R2 -->|yes| R2A["resume_playback()"]
    R2 -->|no| R3

    R3{"R3 · pause | stop | halt"}
    R3 -->|yes| R3A["pause_playback()"]
    R3 -->|no| R4

    R4{"R4 · next | skip | forward"}
    R4 -->|yes| R4A["next_track()"]
    R4 -->|no| R5

    R5{"R5 · previous | back | last"}
    R5 -->|yes| R5A["previous_track()"]
    R5 -->|no| R6

    R6{"R6 · 'volume up' | louder | 'turn up'"}
    R6 -->|yes| R6A["adjust_volume(+15)"]
    R6 -->|no| R7

    R7{"R7 · 'volume down' | quieter | 'turn down'"}
    R7 -->|yes| R7A["adjust_volume(−15)"]
    R7 -->|no| R8

    R8{"R8 · what | playing |<br/>current | now"}
    R8 -->|yes| R8A["get_current_track()"]
    R8 -->|no| R9

    R9{"R9 · quit | exit | bye | goodbye"}
    R9 -->|yes| R9A["notify 👋 · is_running = False"]
    R9 -->|no| DROP["⚠️ silent no-op — no else branch"]

    classDef bug fill:#fff0f0,stroke:#c04a4a
    classDef drop fill:#f4f4f4,stroke:#888,stroke-dasharray:4 3
    class R1,R2 bug
    class DROP,R9 drop
```

### Two reproducible routing bugs

| Input | Rule that fires | Actual result | Correct intent | Finding |
|---|---|---|---|---|
| `"what's playing"` | **R1** — contains `"play"` | searches Spotify for a track literally named **`"ing"`** and plays it | R8 `get_current_track()` | [D5](07_FINDINGS_AND_ISSUES.md), [D45](07_FINDINGS_AND_ISSUES.md) |
| `"goodbye"` | **R2** — contains substring `"go"` | **resumes playback** instead of quitting | R9 quit | [D6](07_FINDINGS_AND_ISSUES.md) |

> `"go back to previous track"` is a third casualty of R2's bare `"go"`. R2 is checked *before*
> R5, so "previous track" intent never reaches the previous-track rule.
>
> Note `"what's playing"` reaches R8 only for phrasings that avoid the letters `p-l-a-y` —
> `"what is this"`, `"now"`, `"what song"`, `"current song"` all work correctly (verified by
> execution).

---

## D-7 · Application state machine

Three booleans, all on `EnhancedVoiceAssistant`. There is no enum, no dataclass, and no
validation of transitions.

```mermaid
stateDiagram-v2
    [*] --> Constructing

    Constructing --> CredentialError : _validate_environment raises
    Constructing --> Idle : creds present

    Idle --> ListeningForWake : loop iteration
    ListeningForWake --> Idle : no wake word / no speech
    ListeningForWake --> Awake : wake word matched
    Awake --> Idle : command handled → is_awake = False
    Awake --> Idle : no transcript → is_awake = False

    Idle --> TextMode : Ctrl+C sets switch_to_text_mode
    TextMode --> Idle : 'voice' or 'recalibrate' or blank-then-return
    TextMode --> Stopping : 'quit' | 'exit' | 'q'
    TextMode --> Stopping : spoken quit phrase (R9)

    Idle --> Stopping : SIGTERM sets is_running = False
    Idle --> Crashed : unhandled exception in loop

    Stopping --> [*] : finally → _cleanup_resources
    Crashed --> [*] : cleanup runs, then re-raise

    note right of Crashed
        Cleanup runs twice on a crash —
        once in except, once in finally.
        Harmless: it is idempotent.
    end note

    note right of TextMode
        Entered only by SIGINT.
        Nothing else ever sets
        switch_to_text_mode, so the
        "automatic fallback to text mode"
        feature does not exist (D27).
    end note
```

**Invalid-but-reachable states** are not guarded against. `is_awake = True` and
`is_running = False` can be simultaneously true; `process_command` is callable from anywhere and
mutates `is_running` directly (`assistant.py:272`).

---

## D-8 · Filesystem — the only shared state

There is no database, no cache service, no queue. Four git-ignored runtime directories hold
100% of the mutable state. `config/` is tracked but **never read** (see [D17](07_FINDINGS_AND_ISSUES.md)).

```mermaid
flowchart TB
    subgraph IGN["git-ignored runtime state"]
        ENV[("env/.env<br/>🔑 CLIENT_ID, CLIENT_SECRET,<br/>REDIRECT_URI, WAKE_WORD")]
        LOGS[("logs/voice_assistant.log<br/>1 MiB × 5 rotating")]
        CAL[("calibration/.voice_calibration.json<br/>wake_word · energy_threshold<br/>pause_threshold · success_rate")]
        CACHE[("cache/.spotify_cache  0o700<br/>cache/.key  0o600<br/>cache/.spotify_tokens.enc")]
    end

    subgraph TRACKED["tracked, but inert"]
        CFGJ[("config/config.json<br/>⚠️ never read at runtime")]
    end

    APP["app/*.py"]
    ENV -->|"load_dotenv"| APP
    APP -->|"RotatingFileHandler"| LOGS
    APP -->|"read/write JSON"| CAL
    APP -->|"Fernet key + ciphertext"| CACHE
    CFGJ -. "no reader" .-x APP

    classDef secret fill:#ffeef0,stroke:#c0392b
    classDef inert fill:#f0f0f0,stroke:#999,stroke-dasharray:5 4,color:#777
    class ENV,CACHE secret
    class CFGJ inert
```

| Path | Written by | Tracked? | Permission note |
|---|---|---|---|
| `env/.env` | human | no | must be `0o600` |
| `logs/voice_assistant.log` | import-time handler | no | — |
| `calibration/.voice_calibration.json` | `change_wake_word`, `save_calibration_data` | no | — |
| `cache/.spotify_tokens.enc` | spotipy via `SecureTokenStorage` | no | `0o600`, key in `cache/.key` |
| `config/config.json` | `ConfigManager.save_config()` | **yes** ⚠️ | would write `client_secret` into a tracked file → [D19](07_FINDINGS_AND_ISSUES.md) |

> `env/.env` is at `env/.env`, **not** the repo root. `README.md` and `QUICKSTART.md` both say
> the root. → [D4](07_FINDINGS_AND_ISSUES.md)

---

## D-9 · Notification fan-out

Notifications are the entire user-facing output channel. There is no GUI and no stdout logging
of user-facing state (except the deliberate fallback).

```mermaid
flowchart TD
    CALL["send_notification(title, message, icon, urgency, timeout)"] --> SETUP{"backend<br/>selected at __init__"}
    SETUP --> W["win10toast<br/>(Windows)"]
    SETUP --> P["plyer<br/>(any)"]
    SETUP --> N["notify-send<br/>(Linux)"]
    SETUP --> O["osascript<br/>(macOS)"]

    W --> TRY["_try_send_with_backend()"]
    P --> TRY
    N --> TRY
    O --> TRY
    TRY --> OK{"returned<br/>without raising?"}
    OK -->|yes| DONE(["visible notification"])
    OK -->|no| NEXT["next backend in chain"]

    NOTE["⚠️ D9: the first backend that merely<br/>imports successfully always reports success,<br/>so the chain never falls through"]

    classDef warn fill:#fff0f0,stroke:#c04a4a
    class NOTE warn
```

Platform predicates come from `platform_utils.py` (`is_windows()`, `is_linux()`, `is_mac()`) —
the single place OS branching is centralised. → [D9](07_FINDINGS_AND_ISSUES.md),
(D54 retracted — see [07 §Explicit retractions](07_FINDINGS_AND_ISSUES.md))

---

## D-10 · `play_song` — the most complex single path

The only method with a three-way fallback (search → device check → launch) and the one most
worth reading end-to-end. Source: `spotify_control.py:173-229`.

```mermaid
flowchart TD
    P(["play_song(song_name)"]) --> CLEAN["strip whitespace; rate-limited"]
    CLEAN --> SEARCH["search(q=song_name, type=track, limit=1)"]

    SEARCH --> RES{"items?"}
    RES -->|"empty"| ERR["notify ❌ Could not find<br/>'{song_name}' — return"]
    RES -->|"found"| ITEM["items[0]"]

    ITEM --> DEV{"active device<br/>with volume_percent?"}
    DEV -->|"yes"| PLAY["PUT /me/player/play<br/>context_uri = album"]
    DEV -->|"no, none active"| LAUNCH["_launch_and_setup_device(action_name)"]
    DEV -->|"no, device exists but<br/>reports no volume"| VOLERR["notify ❌ cannot control<br/>volume state — return"]

    LAUNCH --> FOUND{"Spotify running<br/>with a device?"}
    FOUND -->|yes| PLAY
    FOUND -->|"no"| SPAWN["launch_spotify()<br/>wait up to 15 s, poll"]
    SPAWN --> FOUND
    SPAWN -. "timeout" .-> NOLAUNCH["notify ❌ could not start Spotify"]

    PLAY --> NOTIFY["notify ▶️ Now playing<br/>'{name}' by '{artist}'"]

    classDef warn fill:#fff0f0,stroke:#c04a4a
    class VOLERR,NOLAUNCH warn
```

`adjust_volume` (`spotify_control.py:349`) has **no `else` branch** — when
`current['device']['volume_percent']` is `None` the method silently returns without notifying.
→ [D46](07_FINDINGS_AND_ISSUES.md)

---

## D-11 · Token persistence — a broken contract

The clearest example in the codebase of a *contract* mismatch: the implementation is fine, the
name is wrong.

```mermaid
flowchart LR
    subgraph SPOTIPY["spotipy — SpotifyOAuth(cache_handler=…)"]
        NEED["calls the protocol method<br/>save_to_cache(token_info)"]
        READ["calls<br/>cache_handler.get_cached_token()"]
    end

    subgraph OURS["SecureTokenStorage — spotify_control.py:29-96"]
        HAS["get_cached_token() ✅ :58"]
        MISS["save_token_to_cache() at :78<br/>❌ wrong name — not in the protocol"]
    end

    NEED -. "AttributeError<br/>on first token save" .-x MISS
    READ --> HAS

    subgraph DISK["cache/"]
        K[(".key · 0o600<br/>Fernet key")]
        T[(".spotify_tokens.enc")]
    end
    HAS --> K
    HAS --> T

    classDef bad fill:#ffe6e6,stroke:#b03a3a,stroke-width:2px
    classDef good fill:#e6ffe6,stroke:#3a8a3a
    class MISS bad
    class HAS good
```

Sequence: OAuth succeeds → spotipy calls `save_to_cache` → `AttributeError` → **the app can fail
after a successful login and never cache a token**. This supersedes the plaintext-fallback
concern ([D16](07_FINDINGS_AND_ISSUES.md)) for the user-facing path, because nothing is ever
written. → [D40](07_FINDINGS_AND_ISSUES.md)

Secondary: `_setup_encryption` catches `ImportError` when `cryptography` is absent (it is
undeclared in `requirements.txt`) and falls back to plaintext storage with only a log warning.
→ [D15](07_FINDINGS_AND_ISSUES.md), [D16](07_FINDINGS_AND_ISSUES.md)

---

## D-12 · Startup failure modes

What actually happens, and what the user sees. Reproduced in a dependency-free environment.

```mermaid
flowchart TD
    RUN(["python -m app.main"]) --> IMP{"import app.assistant"}
    IMP -->|"spotipy missing"| E1["ModuleNotFoundError: spotipy<br/>💥 no notification, no log entry"]
    IMP -->|"speech_recognition missing"| E2["ModuleNotFoundError: speech_recognition"]
    IMP -->|"pyttsx3.init() fails<br/>(headless host)"| E3["❌ Audio Manager Error notification<br/>process continues"]
    IMP -->|"ok"| CREDS{"SPOTIFY_CLIENT_ID +<br/>SPOTIFY_CLIENT_SECRET set?"}
    CREDS -->|no| E4["EnvironmentError<br/>💡 '⚠️ Configuration Error' notification<br/>points at the wrong .env path (D4)"]
    CREDS -->|yes| OAUTH{"current_user()"}
    OAUTH -->|"token cache unusable"| E5["⚠️ Authentication error<br/>⚠️ likely AttributeError from D40"]
    OAUTH -->|ok| LOOP["control loop begins"]

    DIAG(["python -m app.health_check"]) --> IMP2{"import app"}
    IMP2 -->|"deps missing"| E6["ModuleNotFoundError<br/>⚠️ THE DIAGNOSTIC CANNOT<br/>DIAGNOSE — D2"]

    classDef err fill:#ffe6e6,stroke:#b03a3a
    classDef diag fill:#fff4e6,stroke:#c98a2e,stroke-width:2px
    class E1,E2,E4,E5 err
    class E6 diag
```

---

## D-13 · Reachability — the honest picture

Roughly 40% of the codebase is unreachable from the running application. This is worth seeing
as a diagram before changing anything.

```mermaid
flowchart TB
    subgraph REACH["Reachable — ~1,990 LOC of 2,627"]
        direction LR
        R1["assistant.py · 274<br/>100%"]
        R2["audio.py · ~330 of 387<br/>speak() and adjust_sensitivity() dead"]
        R3["spotify_control.py · ~470 of 485<br/>get_error_stats etc."]
        R4["platform_utils · 154"]
        R5["notifications_cross_platform · 194"]
        R6["launch_spotify_cross_platform · 112"]
        R7["health_check.py · 369"]
        R8["utils.py · 7"]
    end

    subgraph UNREACH["Unreachable — ~600 LOC"]
        direction LR
        U1["config.py · 286<br/>100% orphaned"]
        U2["error_handling.py · ~290 of 308<br/>7 exception classes, decorator,<br/>safe_call — all unused"]
        U3["audio.speak() · ~16"]
        U4["audio.adjust_sensitivity() · ~5"]
    end

    classDef ok fill:#eefaf0,stroke:#3a8a5c
    classDef bad fill:#fdf0f0,stroke:#b03a3a
    class R1,R2,R3,R4,R5,R6,R7,R8 ok
    class U1,U2,U3,U4 bad
```

---

## D-14 · Platform support matrix

| Capability | Linux | Windows | macOS |
|---|---|---|---|
| Automated setup script | ⚠️ **fails** — copies a nonexistent template ([D3](07_FINDINGS_AND_ISSUES.md)) | ✅ generates `env\.env` inline | ❌ `setup_macos.sh` **does not exist**; `./setup` calls it anyway ([D21](07_FINDINGS_AND_ISSUES.md)) |
| Assistant runs | ✅ primary target | ✅ ported | ⚠️ works, undocumented path |
| Notifications | `notify-send` | `win10toast` → `plyer` | `osascript` |
| Spotify desktop auto-launch | native + Flatpak | executable path lookup | app path |
| `subprocess.CREATE_NO_WINDOW` | n/a | ✅ attribute exists | n/a — but referenced bare, so it is the *only* thing keeping macOS from crashing the notifier ([D51](07_FINDINGS_AND_ISSUES.md)) |

```mermaid
flowchart LR
    subgraph LX["🐧 Linux"]
        L1["universal_setup.sh<br/>⚠️ prompt-gated template copy"]
        L2["notify-send"]
        L3["native + Flatpak launch"]
    end
    subgraph WIN["🪟 Windows"]
        W1["setup_windows.ps1 / .bat<br/>✅ inline .env generation"]
        W2["win10toast → plyer"]
        W3["CREATE_NO_WINDOW"]
    end
    subgraph MAC["🍎 macOS"]
        M1["❌ setup_macos.sh missing"]
        M2["osascript"]
        M3["brew install portaudio"]
    end

    classDef bad fill:#fdf0f0,stroke:#b03a3a
    classDef warn fill:#fff8e8,stroke:#c98a2e
    classDef ok fill:#f0faf2,stroke:#3a8a5c
    class L1,M1 bad
    class M2,M3,L2,L3,W2,W3 ok
    class W1 ok
```

---

## Diagram index

| ID | Diagram | Best for |
|---|---|---|
| [D-1](#d-1--system-context--what-the-process-touches) | System context | "what does this thing talk to?" |
| [D-2](#d-2--component-graph--all-15-modules) | Component graph | "where does this symbol live?" |
| [D-3](#d-3--container--what-is-actually-loaded-at-runtime) | Container / load order | "why does importing break things?" |
| [D-4](#d-4--the-control-loop) | The control loop | "what happens in one idle cycle?" |
| [D-5](#d-5--voice-cycle--wake-word-to-spotify-call) | Voice sequence | "trace one spoken command" |
| [D-6](#d-6--command-dispatch--the-exact-9-rule-chain) | Dispatch chain | "why did my command do that?" |
| [D-7](#d-7--application-state-machine) | State machine | "what state is it in?" |
| [D-8](#d-8--filesystem--the-only-shared-state) | Filesystem | "where is state/secrets?" |
| [D-9](#d-9--notification-fan-out) | Notification chain | "why did I not see a notification?" |
| [D-10](#d-10--play_song--the-most-complex-single-path) | `play_song` flow | "why did playback fail?" |
| [D-11](#d-11--token-persistence--a-broken-contract) | Token contract | "why is login broken?" |
| [D-12](#d-12--startup-failure-modes) | Failure modes | "what just crashed?" |
| [D-13](#d-13--reachability--the-honest-picture) | Reachability | "is this code even used?" |
| [D-14](#d-14--platform-support-matrix) | Platform matrix | "does this work on my OS?" |

---

**Related:** [02 — Architecture](02_ARCHITECTURE.md) ·
[03 — Module Reference](03_MODULE_REFERENCE.md) ·
[04 — Data Flows](04_DATA_FLOWS.md) ·
[11 — Features & Capabilities](11_FEATURES_AND_CAPABILITIES.md) ·
[12 — Caveats & Limitations](12_KNOWN_CAVEATS_AND_LIMITATIONS.md) ·
[13 — Runbook](13_RUNBOOK.md) ·
[07 — Findings & Issues](07_FINDINGS_AND_ISSUES.md)
