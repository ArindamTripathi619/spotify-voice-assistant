# 11 — Features & Capabilities

The definitive feature list, graded against the **actual code** rather than the README. Every row
is traceable to a `file:line`; every "Broken / Missing / Dead" verdict is backed by
[07 — Findings & Issues](07_FINDINGS_AND_ISSUES.md).

> **How to read the status column**
>
> | Status | Meaning |
> |---|---|
> | ✅ **Works** | Reachable from the control loop and functionally correct on the main path |
> | ⚠️ **Partial** | Reachable, but degrades in a common case, or works only for some inputs |
> | 🐛 **Broken** | Reachable and produces the wrong behaviour |
> | 💀 **Dead** | Defined, but no reachable call site, or provably a no-op |
> | 👻 **Missing** | Documented in user-facing docs, but no implementation exists |
> | 🧪 **Unverified** | Plausible from code, never executed (no live Spotify account / mic / Windows host) |

---

## F-0 · Summary scoreboard

| Area | ✅ Works | ⚠️ Partial | 🐛 Broken | 💀 Dead | 👻 Missing |
|---|---|---|---|---|---|
| Voice command routing | 6 | 1 | 2 | — | — |
| Audio capture & STT | 3 | 4 | — | 2 | 1 |
| Spotify control | 7 | 3 | — | — | — |
| Device management | 2 | 1 | — | — | — |
| Notifications | 1 | 1 | 1 | — | — |
| Configuration | 2 | 2 | 1 | 1 | — |
| Diagnostics | 7 | 1 | 1 | — | — |
| Security | 2 | 1 | 1 | — | — |
| **Totals** | **30** | **14** | **6** | **4** | **1** |

> Roughly **30 of 55** documented capabilities work as advertised. The failures are concentrated
> in three places: the command router, the "enhanced"/adaptive-audio features, and the
> configuration layer.

---

## F-1 · Voice commands — the full routing table

All of these are reachable **by voice** and **by text**. The router is a flat substring chain
(`app/assistant.py:238-274`); first match wins. See
[14 § D-6](14_ARCHITECTURE_DIAGRAMS.md#d-6--command-dispatch--the-exact-9-rule-chain).

| # | Rule condition (verbatim) | Handler | Phrasings that work | Status |
|---|---|---|---|---|
| 1 | `'play' in c and len(c.split()) > 1` | `play_song(song_name)` | "play hotel california", "play bohemian rhapsody by queen" | ⚠️ destructive — see below |
| 2 | `any(c for ['play','start','resume','go'])` | `resume_playback()` | "resume", "start music", "play", "go" | ⚠️ substring traps — see below |
| 3 | `any(c for ['pause','stop','halt'])` | `pause_playback()` | "pause", "stop", "halt" | ✅ |
| 4 | `any(c for ['next','skip','forward'])` | `next_track()` | "next", "skip this", "forward" | ✅ |
| 5 | `any(c for ['previous','back','last'])` | `previous_track()` | "previous", "go back", "last track" | ⚠️ rule 2 wins first on "go back" |
| 6 | `'volume up' \| 'louder' \| 'turn up'` | `adjust_volume(+15)` | "volume up", "louder", "turn it up" | ✅ |
| 7 | `'volume down' \| 'quieter' \| 'turn down'` | `adjust_volume(−15)` | "volume down", "quieter", "turn it down" | ✅ |
| 8 | `any(c for ['what','playing','current','now'])` | `get_current_track()` | "what is this", "now", "what song", "current song" | 🐛 documented phrasing broken |
| 9 | `any(c for ['quit','exit','bye','goodbye'])` | quit + `is_running = False` | "quit", "exit", "bye" | 🐛 "goodbye" broken |
| — | *(no `else` branch)* | — | anything unmatched | ⚠️ **silently ignored** |

### Reproduced routing bugs

| Input | What actually happens | Why | Finding |
|---|---|---|---|
| `"what's playing"` | searches Spotify for a track named **`"ing"`** and plays it | R1 fires first: the string contains `"play"` | [D5](07_FINDINGS_AND_ISSUES.md) |
| `"play track"` | **resumes playback** instead of searching | R1 strips `"track"`, leaving an empty name, then falls through to R2 | [D5](07_FINDINGS_AND_ISSUES.md) |
| `"play dream track"` | searches for **`"dream "`**, not "Dream Track" | R1 blindly removes the substring `"track"` anywhere in the name | [D5](07_FINDINGS_AND_ISSUES.md) |
| `"play the song"` | searches for an empty-ish string, falls through to resume | `"the song"` is stripped and nothing is left | [D5](07_FINDINGS_AND_ISSUES.md) |
| `"goodbye"` | **resumes playback** | R2 matches the bare substring `"go"` inside `"goodbye"` | [D6](07_FINDINGS_AND_ISSUES.md) |
| `"go back to previous track"` | **resumes playback** | R2 again — checked before R5 | [D6](07_FINDINGS_AND_ISSUES.md) |
| `"now playing"` | plays a track named `"ing"` | same as row 1 | [D45](07_FINDINGS_AND_ISSUES.md) |
| `"playback speed"` | rule 1 → searches for `"back speed"` | `"play"` prefix, not a word boundary | [D5](07_FINDINGS_AND_ISSUES.md) |
| `"stopwatch music"` | **pauses** | `"stop"` is a substring of `"stopwatch"` | [D5](07_FINDINGS_AND_ISSUES.md) |

**Rule 1 is destructive, not just imprecise.** `assistant.py:243-246` applies three unconditional
`.replace()` calls — `'the song'`, `'song called'`, `'track'` — anywhere in the extracted title.
There is no word boundary and no check that the remainder is meaningful, so a title containing the
word "track" cannot be searched at all.

**No word-boundary matching.** Every rule is `in` on a raw lowercased string, so any keyword
embedded inside a longer word triggers it. The wake word has the same problem — see F-2.

---

## F-2 · Wake word

| Aspect | Behaviour | Status |
|---|---|---|
| Default wake word | `jarvis` (`assistant.py:32`, from `WAKE_WORD` env var) | ✅ |
| Changeable at runtime | text mode `wake` → prompts, lowercases, writes to calibration JSON | ✅ |
| Persisted across restarts | `calibration/.voice_calibration.json` → `wake_word` key | ✅ |
| Validation on load | rejects non-`isalnum()` and > 50 chars | ✅ |
| Listening window | 30 s timeout, `phrase_time_limit=5`, then one Google call | ✅ |
| Matching method | `self.wake_word.lower() in recognized_text.lower()` — **naive substring** | 🐛 |
| Acoustic echo rejection | none | 👻 |
| Multi-word wake words | work, but a substring match means `"go"` fires on "going", "good", "ago" | 🐛 |

> **Consequence of substring matching:** short or common wake words (`go`, `a`, `hey`, `the`) cause
> near-constant false wake-ups. The loader's `isalnum()` check does not prevent this.
> See [D6](07_FINDINGS_AND_ISSUES.md) for the same class of bug in the router.

Wake word is only changeable **in text mode** — there is no spoken command for it.
→ [D43](07_FINDINGS_AND_ISSUES.md)

---

## F-3 · Speech recognition

| Aspect | Behaviour | Status |
|---|---|---|
| Engine | Google Web Speech via `SpeechRecognition.recognize_google` | ✅ |
| Offline / local mode | none | 👻 |
| Ambient adaptation (wake) | `adjust_for_ambient_noise(duration=0.2)` | ✅ |
| Ambient adaptation (command) | `duration=0.2` | ✅ |
| **Tuned recognizer settings** | `setup_enhanced_audio()` sets 8 attributes on `self.recognizer`, but both `listen_*` methods build a **local** `sr.Recognizer()` | 🐛 all tuning is discarded |
| Fallback chain | `en-US` → `en-GB` → `en-US` with `show_all`, accepts `confidence > 0.3` | ✅ |
| Rate limit | 45 calls/min fixed window (`audio.py:308-320`) | ⚠️ only 1 of 2 call sites invokes it |
| Command window | 3 s timeout, `phrase_time_limit=7` | ✅ |
| Spoken response (TTS) | `AudioManager.speak()` — **0 call sites** | 💀 dead |
| Adaptive sensitivity | `adjust_sensitivity()` — guard `attempt_count > 2` is permanently false, and `attempt_count` is never incremented | 💀 no-op |
| Success-rate tracking | `success_count` incremented at `audio.py:296`, but nothing ever *reads* it for a decision | ⚠️ vestigial |

> **The tuning that does survive:** `adjust_for_ambient_noise` is called on the *local*
> recognizer, so ambient noise adaptation genuinely works. What is lost is the tuned and
> persisted threshold state. → [D7](07_FINDINGS_AND_ISSUES.md), [D8](07_FINDINGS_AND_ISSUES.md)

---

## F-4 · Audio calibration

| Aspect | Behaviour | Status |
|---|---|---|
| Startup calibration | `setup_enhanced_audio()` → `smart_calibration()` | ✅ |
| Load saved thresholds | reads `energy_threshold`, `pause_threshold` from JSON | ✅ |
| First-run calibration | 4 s ambient sample, then an 8 s spoken test | ✅ |
| Adaptivity to short utterance | if the test yields < 3 words, threshold × 0.8 | ✅ |
| Failure fallback | threshold 250, pause 3.5 | ✅ |
| Persistence | `save_calibration_data()` writes JSON | ✅ |
| **Path traversal guard** | `startswith()` string check after `normpath` | ⚠️ `../calibration_evil` also passes |
| Permission repair | rewrites the file if mode allows group/other access | ✅ |
| Directory perms | `0o700` on `calibration/` | ✅ |
| Manual recalibration | text mode `recalibrate` → `enhanced_calibration()` | ⚠️ not available by voice |

→ [D20](07_FINDINGS_AND_ISSUES.md) (path check), [D43](07_FINDINGS_AND_ISSUES.md) (voice-only gap),
[D53](07_FINDINGS_AND_ISSUES.md) (README's "7-day validity" claim is false — it persists forever)

---

## F-5 · Spotify playback control

| Operation | API | Status | Notes |
|---|---|---|---|
| Search + play | `search(type=track)` → `PUT /me/player/play` with album `context_uri` | ✅ | `spotify_control.py:173` |
| Resume | `PUT /me/player/play` | ✅ | `:230` |
| Pause | `PUT /me/player/pause` | ✅ | `:271` |
| Next | `POST /me/player/next` | ✅ | `:287` |
| Previous | `POST /me/player/previous` | ✅ | `:318` |
| Volume +15 / −15 | `PUT /me/player/volume` | ⚠️ | **silent no-op** if the device reports no `volume_percent` — no `else` branch → [D46](07_FINDINGS_AND_ISSUES.md) |
| Current track | `GET /me/player/current` | ✅ | `:368`, but unreachable for the advertised phrasing → [D45](07_FINDINGS_AND_ISSUES.md) |
| Song-not-found | notifies `❌ Could not find '…'` | ✅ | |
| API rate limiting | `SpotifyRateLimiter(8/s)` decorator | ⚠️ per-method, not per-client → [D10](07_FINDINGS_AND_ISSUES.md) |
| Search result typing | — | ⚠️ `current['item']` assumed non-`None` on 3 paths → [D12](07_FINDINGS_AND_ISSUES.md) |

---

## F-6 · Device management & auto-launch

| Capability | Behaviour | Status |
|---|---|---|
| Find active device | `_find_active_device()` | ⚠️ matches `is_active` **or** a `type` in the allowlist → [D48](07_FINDINGS_AND_ISSUES.md) |
| Auto-launch when none active | `_launch_and_setup_device()` — native and Flatpak on Linux | ✅ |
| Wait for device to appear | polls up to ~15 s | ✅ |
| Recover from "no active device" 403 | `_handle_no_active_device()` | ✅ |
| Notification on recovery | `🎵 Launching Spotify…` then `✅ ready` | ✅ |

Full flow: [14 § D-10](14_ARCHITECTURE_DIAGRAMS.md#d-10--play_song--the-most-complex-single-path)

---

## F-7 · Notifications — the only output channel

| Aspect | Behaviour | Status |
|---|---|---|
| Windows backend | `win10toast`, falling back to `plyer` | ✅ |
| Linux backend | `notify-send` with icon/urgency/timeout | ✅ |
| macOS backend | `osascript` | ✅ |
| Fallback chain | 5 backends tried in order | 🐛 **can never trigger** — the first importable backend always reports success → [D9](07_FINDINGS_AND_ISSUES.md) |
| Last resort | `print()` to stdout | ✅ deliberate |
| Argument order at every call site | `(title, message, icon, urgency, timeout)`, title-first, positional, uniform across ~30 sites | ✅ *(an earlier claim of inconsistency, D54, was retracted)* |
| `subprocess.CREATE_NO_WINDOW` | referenced bare; only exists on Windows | ⚠️ → [D51](07_FINDINGS_AND_ISSUES.md) |

---

## F-8 · Text mode (the only real escape hatch)

Entered with **Ctrl+C** — which sets a flag, it does not quit. `assistant.py:162-188`.

| Input | Action | Status |
|---|---|---|
| any command | routed through the same `process_command` | ✅ |
| `quit` / `exit` / `q` | **the only reliable shutdown** | ✅ |
| `voice` | return to wake-word mode | ✅ |
| `help` | prints recognition tips | ✅ |
| `wake` | change the wake word | ✅ |
| `recalibrate` | force audio recalibration | ✅ |
| blank | re-prompts | ✅ |
| `Ctrl+C` inside the REPL | returns to voice mode | ✅ |

⚠️ `recalibrate` and `wake` exist **only** in text mode — there is no spoken equivalent.
→ [D43](07_FINDINGS_AND_ISSUES.md)

> The tips printed by `help` include the claim *"I'll automatically adjust sensitivity"* — that
> feature does not exist. → [D29](07_FINDINGS_AND_ISSUES.md)

---

## F-9 · Configuration

| Aspect | Behaviour | Status |
|---|---|---|
| Env file location | `env/.env` (`utils.py:5`, resolved as `app/../env/.env`) | ✅ |
| Loader | `python-dotenv.load_dotenv` | ✅ |
| Required vars | `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` — validated at startup | ✅ |
| Optional vars | `SPOTIFY_REDIRECT_URI` (default `http://127.0.0.1:8080/callback`), `WAKE_WORD` (default `jarvis`) | ✅ |
| Startup failure mode | `EnvironmentError` + a `⚠️ Configuration Error` notification | ✅ |
| Accuracy of the error text | points at the wrong `.env` path | 🐛 → [D4](07_FINDINGS_AND_ISSUES.md) |
| `config/config.json` | `ConfigManager`, 286 lines | 💀 **zero inbound imports** → [D17](07_FINDINGS_AND_ISSUES.md) |
| Runtime config changes | none — all paths hardcoded in `assistant.py` | 💀 |

> `ConfigManager.save_config()` would write `client_secret` into a **tracked** file. The method
> is unreachable, which is the only thing preventing a secret leak. → [D19](07_FINDINGS_AND_ISSUES.md)

---

## F-10 · Diagnostics — `python -m app.health_check`

Nine checks, `health_check.py:252-304`. Reachable only if all third-party packages import — which
is precisely the situation the tool exists to diagnose. → [D2](07_FINDINGS_AND_ISSUES.md)

| Check | Verifies | Status |
|---|---|---|
| `check_python_version` | 3.7+ | ✅ |
| `check_python_packages` | all 7 declared packages importable | ✅ |
| `check_environment_variables` | required vars present and non-blank | ✅ |
| `check_audio_system` | PortAudio present, mic device list reachable | ✅ |
| `check_spotify_connectivity` | API reachable + token valid | ✅ |
| `check_platform_support` | OS is one of Windows/Linux/macOS | ✅ |
| `check_file_permissions` | `env/`, `cache/`, `logs/`, `calibration/` readable/writable | ✅ |
| `check_network_connectivity` | reachability | 🐛 **can never report failure** → [D24](07_FINDINGS_AND_ISSUES.md) |
| `run_all_checks` / `display_summary` | aggregation + output | ⚠️ exit codes are `0` ok / `1` critical / **`2` warning** → inverted vs convention → [D44](07_FINDINGS_AND_ISSUES.md) |

⚠️ The health check **writes to the filesystem** — it creates `cache/`, `logs/`, `calibration/`
and a temporary probe file. It is a prober, not a test suite. → [D25](07_FINDINGS_AND_ISSUES.md)

---

## F-11 · Security posture

| Control | Status |
|---|---|
| OAuth token encrypted with Fernet | ⚠️ `cryptography` is **undeclared** → plaintext fallback → [D16](07_FINDINGS_AND_ISSUES.md) |
| Token cache permissions | ✅ `cache/` = `0o700`, `.key` = `0o600` |
| Key storage | ⚠️ key sits **beside** its ciphertext → [D15](07_FINDINGS_AND_ISSUES.md) |
| Token save path | 🐛 `save_to_cache` not implemented → first save raises → [D40](07_FINDINGS_AND_ISSUES.md) |
| Calibration path traversal guard | ⚠️ `startswith()` is prefix-on-chars → [D20](07_FINDINGS_AND_ISSUES.md) |
| `env/` git-ignored | ✅ |
| `config/` git-ignored | ❌ **tracked**, and `save_config()` would write a secret there → [D19](07_FINDINGS_AND_ISSUES.md) |
| Shelling out | uses `subprocess.run` with list args — no `shell=True` anywhere | ✅ |
| `lstrip('../')` misuse | 🐛 character-set strip, not prefix strip → [D20](07_FINDINGS_AND_ISSUES.md) |
| Notification content | no user data interpolated into shell strings | ✅ |

---

## F-12 · Features that are documented but do not exist

| Claim | Where claimed | Reality |
|---|---|---|
| "Automatic fallback to text mode" | README | only SIGINT ever sets the flag → [D27](07_FINDINGS_AND_ISSUES.md) |
| Spoken / TTS responses | README, `show_enhanced_tips` | `speak()` has zero call sites → [D28](07_FINDINGS_AND_ISSUES.md) |
| "I'll automatically adjust sensitivity" | in-app `help` output | `adjust_sensitivity()` is a no-op → [D29](07_FINDINGS_AND_ISSUES.md) |
| Settings in `config/config.json` | README | module never imported → [D17](07_FINDINGS_AND_ISSUES.md) |
| "7-day validity / recalibrates weekly" | `README.md:179` | persists indefinitely; no expiry logic → [D53](07_FINDINGS_AND_ISSUES.md) |
| Token cache at `cache/tokens.json` | README | actual path is `cache/.spotify_tokens.enc` → [D30](07_FINDINGS_AND_ISSUES.md) |
| `.env` in the repo root | README, QUICKSTART | actual path is `env/.env` → [D4](07_FINDINGS_AND_ISSUES.md) |
| `python app/main.py` | README | fails — relative import needs `-m` → [D38](07_FINDINGS_AND_ISSUES.md) |
| macOS automated setup | `setup` dispatcher | `setup_macos.sh` does not exist → [D21](07_FINDINGS_AND_ISSUES.md) |
| "Wake word detection ~100ms" | `WINDOWS_PORT_GUIDE.md:220` | unmeasured; the path is a network round-trip → [D56](07_FINDINGS_AND_ISSUES.md) |

---

## F-13 · Deliberately absent

Not bugs — scope decisions. Listed so nobody "fixes" them.

| Absent | Why it is fine |
|---|---|
| No web server / HTTP API | It is a local CLI daemon; a server would be a net loss at this size |
| No database | All state is four small JSON/enc files |
| No async runtime | The app is network-bound and single-threaded by design |
| No dependency injection framework | Constructor injection is sufficient for 3 collaborators |
| No container/CI/test framework | Out of scope for a personal project — but see [D33](07_FINDINGS_AND_ISSUES.md) |
| No plugin system | 9 commands is the whole surface |

**Scope discipline rule for contributors:** do not introduce a web framework, database, async
runtime, or DI container. Fix the existing single control loop instead.

---

## Related

[00 — Project Overview](00_PROJECT_OVERVIEW.md) ·
[03 — Module Reference](03_MODULE_REFERENCE.md) ·
[04 — Data Flows](04_DATA_FLOWS.md) ·
[05 — Configuration & Environment](05_CONFIGURATION_AND_ENV.md) ·
[12 — Caveats & Limitations](12_KNOWN_CAVEATS_AND_LIMITATIONS.md) ·
[14 — Architecture Diagrams](14_ARCHITECTURE_DIAGRAMS.md) ·
[07 — Findings & Issues](07_FINDINGS_AND_ISSUES.md)
