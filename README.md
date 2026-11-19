# zectrix-note4c-catthew

A general voice interface to the existing Catthew Hermes profile, with a four-color household display. Talk to Catthew about any topic; Tasks and Grocery Shopping are display views, not conversation limits. The Zectrix Note4C handles buttons, microphone, speaker and display. Bluehost runs Hermes, shared household knowledge, speech recognition, speech synthesis, household tools and screen rendering, so the Mac is needed only for setup and development.

This project targets the **ESP32-S3 N16R8 Note4C with a real 400 × 300 black/white/red/yellow panel**. Firmware contains no Wi-Fi password, device token or model credential.

This is a standalone repository owned by `theduy3`, with the current product on `main`. The previous fork and its unmerged review record are retained in [hearth-catthew-fork-archive](https://github.com/theduy3/hearth-catthew-fork-archive). Original source history, licenses and attribution are preserved.

## Controls

- **Hold the front button:** interrupt reply playback and record once the indicator turns steady.
- **Release:** submit the recording. The maximum recording is 30 seconds.
- **Short-press the front button or Down:** advance a page.
- **Short-press Up:** return to the previous page.
- **Hold Down:** stop audio/display work safely and enter deep sleep. The front button wakes the device.

There are exactly two screens: **Tasks** and **Grocery Shopping**. Tasks shows up to five tasks due **today in America/Vancouver**, with an overflow count. Grocery records, overdue work, undated work and future work do not appear there; hidden tasks remain in the shared records until completed. Grocery Shopping shows only needed item names, up to seven at once; its empty list has no placeholder instruction. Purchased items disappear. Ask Catthew by voice to add groceries, change quantities or check off purchases. Asking for tasks refreshes and opens Tasks; asking for the shopping list or modifying groceries refreshes and opens Grocery Shopping. Replies play through the speaker, and unrelated conversation leaves the selected screen alone. Either navigation direction toggles between the two screens. Hidden calendar/notes or reply-text changes do not repaint them.

The panel uses full refreshes; the user observed about15seconds for a page change, with flashing stopping once it settles. Navigation presses during a refresh are combined; recording and reply playback run independently. Recording and processing use the indicator rather than additional screen refreshes. An offline badge distinguishes a cached page from current data.

## Household scope

Catthew keeps its existing SOUL. The user-selected model is `openai-codex` / `gpt-6.1-terra`; setup and release checks preserve that choice. Zectrix voice requests ask for **low reasoning effort** through supported per-request model options. The Catthew profile default and other gateways' reasoning settings remain unchanged; this is the same central Catthew, not another model or agent. Note4C has a separate persistent conversation while sharing the same underlying records with Telegram and CLI.

- Calendar: **Kittyggup Family**, timezone **America/Vancouver**.
- Tasks: exact `catthew` tag in existing `Tasks/tasks`, `Tasks/bugs` and `Tasks/ideas`.
- Reference notes: exact `kittyggup` tag anywhere in the vault.
- Calendar edits/deletions create proposals. A private, expiring, one-use human confirmation authorizes the exact version and change. Device buttons cannot approve changes.

The household MCP exposes scoped record operations. It does not expose a shell, arbitrary paths, calendar selection or an approval/apply tool to the model. The terminal checks the native Hermes tool policy before every turn and refuses unexpected capabilities.

## Remembering across voice and Telegram

Ask Catthew to remember household facts, inventory items, locations or preferences. It searches existing reference notes first, then saves a new fact or updates a Catthew-managed fact using its current revision. These are shared Bluehost records under `/vault/References/Catthew`, tagged `kittyggup`, so Telegram and Note4C can look them up without sharing their entire conversation threads. Existing family reference notes remain read-only through these tools.

For example, you can tell Catthew where you keep a household item, then ask about that location in Telegram. Inventory is distinct from a grocery shopping request or a task: remembering it does not add a checklist item, create a Calendar event or select another screen. Replies remain spoken. Facts are saved only through successful tool results, with duplicate-retry protection and retained prior versions; do not treat a conversational promise alone as proof of a saved record.

The display refresh reads only tasks and groceries. Calendar and reference notes are fetched through their tools when a conversation needs them, rather than on every voice completion or display poll.

## Current verified checkpoint

Installed firmware `09d1fa2e92dc437be0192ca489561b47c5a9d627` built with the pinned ESP-IDF 6.1 toolchain in [Actions run 43392558966](https://github.com/theduy3/hearth-catthew-fork-archive/actions/runs/43392558966). Its bootloader, partition table and application were identity-checked, flashed and verified on the backed-up Note4C with pairing retained. Wi-Fi/time/authenticated-frame readiness passed. Earlier backend `b0d61ce` and all137tests also passed [run43397344604](https://github.com/theduy3/hearth-catthew-fork-archive/actions/runs/43397344604). Earlier user evidence confirmed the full-color settling waveform and voice; current physical request-directed navigation remains part of acceptance.

The shared-knowledge backend `d5019ae` is deployed on Bluehost. All151hosttests and the pinned firmware build passed [run43622003478](https://github.com/theduy3/zectrix-note4c-catthew/actions/runs/43622003478). An actual Catthew API call saved the user's Note4C voice/shared-memory preference; a separate fresh Catthew session retrieved it through the shared notes tool. Neither call selected a page or invoked task, grocery or Calendar mutations. Telegram is connected and its installed resolver selects the same household server; no Telegram test message was sent.

The HTTPS backend, native color frames, restricted model path, unchanged SOUL, speech service and Catthew Telegram connection pass release checks. An earlier synthetic English voice round trip returned text and 16 kHz speaker audio. **Male-voice/latency confirmation, interruption/Mac-asleep acceptance and individually confirmed live household write/approval tests remain pending.** See [GATES.md](GATES.md) for the distinction between automatic and human evidence.

## Pair the already-flashed device

On the approved Mac, with the Note4C connected by USB:

```bash
./tools/setup-note4c.sh
```

The wizard checks the four labeled calibration patches before pairing. Enter the 2.4 GHz network name and hidden Wi-Fi password in that terminal. The helper verifies the device against the private backup record and retrieves its dedicated device token privately through the existing `bluehost` SSH alias. Credentials are sent over USB into device NVS; they are not written to a local `.env`, printed, or committed.

It then guides a read-only English greeting, page navigation, playback interruption and a reply while the Mac sleeps and the tablet uses wall power. A fresh VPS job and full-playback acknowledgement are checked for voice tests. Physical acceptance evidence stays under `$HOME/.local/share/catthew-note4c/`.

The wizard verifies Wi-Fi, time synchronization and a successful authenticated frame before advancing to voice. If it reports Wi-Fi reason201, the configured network was not found. Retry only private Wi-Fi pairing with `./tools/setup-note4c.sh --wifi-only`, using the exact reachable2.4GHz network name. USB status checks hold one connection open because opening USB restarts this board; do not run them during a recording.

If a color, audio or gesture check fails, stop at that stage and report the observed behavior. Live family write tests require their separately confirmed record and cleanup; pairing does not authorize test calendar/task mutations.

## Build and verify

Host tests need Python and [requirements.txt](requirements.txt):

```bash
python3 -m unittest discover -s tests -v
```

Native C++ tests compile the actual e-paper driver against trace stubs and check BWRY byte order, command sequencing, power removal, timeout and retry. The PCM decoder tests fragmented WAV input, format/length limits and cancellation. Backend tests cover source scope, concurrency, durable requests, uncertain outcomes, expiry, private approvals, Unicode projection and HTTP boundaries.

[The firmware workflow](.github/workflows/firmware.yml) pins the ESP-IDF 6.1 container by digest and emits a checksummed manifest with build artifacts. It requires no credentials. Avoid installing a large SDK on the Mac or compiling on the production VPS.

Verify a downloaded artifact before writing. Pass the directory containing `note4c-manifest.json`:

```bash
python3 -m tools.flash_note4c \
  --artifact-dir /private/path/to/note4c-firmware/build \
  --expect-commit FULL_COMMIT_SHA
```

Writing additionally requires `--write`, a private verified full factory backup, and matching physical device identity. Use `--initial-provision` only for the first layout installation; it erases the new NVS region. Updates preserve pairing unless explicitly erased. The original full 16 MiB image remains private and is never an Actions artifact.

## Voice and latency

Catthew now receives its small approved tool catalog directly (`tools.tool_search.enabled: off` in the Catthew profile). This removes tool-description round trips without changing the model, voice, allowed tools or central-agent/gateway architecture.

A fixed recorded question about the user's saved voice-topic preference was measured through Whisper, Catthew and Joe, using the existing voice worker with an isolated journal and stubbed display lists. No audio was delivered to the physical tablet. Across three fresh sessions per setting, median server-side audio readiness fell from **24.6seconds to11.9seconds (52% faster)**. Tool-description calls fell from one to zero; note lookups fell from two–three to one–two. All replies correctly used the real saved preference; no write/page actions occurred.

The Note4C adapter also requests **low reasoning effort for each voice turn**, while the central profile remains at its existing medium default for other gateways. In separate read-only comparisons with the direct catalog already active (three runs per setting), task-list audio readiness measured12.1→5.4seconds and grocery-list readiness5.6→4.5seconds. Answers matched the current records and no write/page actions occurred. These are separate task/grocery workloads, not additional percentages to combine with the saved-fact result above.

Simple greeting controls were variable: an initial fresh-session comparison measured medians2.8/4.2seconds and was rolled back for further checks. Repeating with one explicitly excluded warmup and three measured turns in a persistent conversation gave4.0/2.9seconds. These small samples establish no universal greeting-speed claim. First requests and complex questions still vary; recording time, network upload, device polling and physical playback start are outside the measurement. The central profile setting applies to Catthew across its gateways, preserving each gateway's existing tool permissions.

The local Piper voice is Joe (`en_US-joe-medium`, male US-English, CC0 dataset). Whisper remains base.en int8. The requested731MB Parakeet Unified Q8 candidate was prepared and tested but is inactive: it measured slower and used more resident memory on this VPS. The user chose the lowest measured latency, so Whisper is retained. See [measurements and decision](docs/PARAKEET-BENCHMARK.md). Active requests and completed text awaiting audio poll every500ms; idle/terminal requests poll every5seconds. A regression trace covers the completion boundary that previously caused a five-second wait for ready audio.

`tools.voice_smoke` reports upload, audio-ready/download timings and status transitions without transcript or reply text. Historical VPS audio readiness before the shared-memory/display-fetch change: the synthetic greeting took about4.3–4.4seconds. A read-only task query including record access and page selection took22.4seconds. These are different workloads and neither measures end-to-end physical-device latency. The removed Calendar/reference projection work has not yet been assigned a measured latency saving.

## VPS operation

The production endpoint is `https://zectrix.theduy.cloud`. Caddy terminates TLS; terminal and speech listeners remain loopback-only. The terminal is a supervised systemd service using `deploy/run-terminal.sh` to enter the Hermes container namespaces while retaining its own service cgroup. Do not replace that daemon launcher with `docker exec`: stopping its client can leave the server running stale code.

`tools/configure_catthew.py` performs backed-up profile configuration. Device/API credentials belong in private service state, not this repository. Deployment units and the dedicated Caddy site are under [deploy/](deploy/). Existing unrelated proxy routes and Hermes profiles remain outside this change.

Release checks:

```bash
python3 tools/verify_vps.py --soul-sha256 EXPECTED_SOUL_SHA256
ssh bluehost 'docker exec --user 1500 \
  --workdir /home/hermes/.hermes/catthew-terminal hermes \
  /home/hermes/.hermes/hermes-agent/venv/bin/python -m tools.voice_smoke'
```

The voice smoke test uses a synthetic greeting and creates no family records. After an intentional gateway reload, allow its messaging adapters to initialize before checking `/p/catthew/health`; startup can take minutes.

## Design, protocol and delivery

- [Approved design and delivery plan](docs/CATTHEW-NOTE4C-PLAN.md)
- [Implementation ledger](docs/CATTHEW-IMPLEMENTATION-PROGRESS.md)
- [Device protocol and native pixel format](docs/NOTE4C-PROTOCOL.md)
- [Acceptance gates](GATES.md)
- [Standards and specification source review](docs/NOTE4C-REVIEW.md)
- [Archived fork PR #1](https://github.com/theduy3/hearth-catthew-fork-archive/pull/1), retained as unmerged review history

Unmodified DejaVu fonts and their attribution are in [assets/fonts/](assets/fonts/). Speech dependencies and pinned model provenance are maintained separately by the speech preparation tools; the Piper engine is GPLv3 and is not vendored into the firmware.
