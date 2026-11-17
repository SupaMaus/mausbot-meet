# Results

joinly `v0.5.4@sha256:d19ca294…b9ea0` on one Boat VM (default: 4 vCPU / 8 GB), with Whisper base (CPU) and Kokoro.
First run: 2026-11-17, Boat VM created 14:53Z.

## No-meeting checks on the VM

| Check | Result |
|---|---|
| OS / CPU / RAM / disk | Ubuntu 24.04.4, 4 vCPU (AMD Ryzen 9 9950X), 7.9 GB RAM (0.9 GB used idle), 79 GB disk (55 GB free) |
| Docker available | yes, 29.7.0, no sudo needed |
| Outbound HTTPS (ghcr, Meet, Zoom, Teams, Hugging Face) | all reachable, 0.06–0.19 s |
| Outbound UDP (STUN 19302) | ok, Google STUN answered |
| Image pull time / size | 41 s; digest verified |
| Session start: PulseAudio, Xvfb, Chromium processes | yes: all three up about 1 s after a client connects (models loaded in the same second) |
| Virtual speaker and mic present | mic: running ("mic pacing" log lines); speaker sink: not listed yet (the pactl selfcheck has not run) |
| Kokoro speaks → Whisper reads it back | yes: 2.6 s of audio in 1.3 s; Whisper base read it back word for word in 1.5 s |
| CPU / RAM idle, session open | idle container 0.3% CPU, 54–400 MB; VM 1.6 GB of 7.9 GB used |

## Per platform

| | Google Meet | Zoom (web) | Teams |
|---|---|---|---|
| Reached the waiting room (s from start) | no: refused before the name screen | | |
| Admitted (s) | | | |
| Refused by the platform? (what it said) | **yes**: "You can't join this video call". With joinly's bundled Chromium it appears at once, before the name screen. With the VM's own fingerprint-aware Chrome it appears right after "Join now". | | |
| Chat message posted (seen in the meeting) | | | |
| Chat read back (`get_chat_history`) | | | |
| Bot heard people (transcript has their words) | | | |
| Transcript accuracy / speaker names right | | | |
| Bot spoke (heard, clear?) | | | |
| `speak_text` duration (s) | | | |
| CPU / RAM in the call | | | |
| Notes | | | |

## Run log

- **Meet, run 1:** a meeting created by the owner, with the owner present.
  - joinly's session started in 1 s: Silero, Whisper base and Kokoro loaded; PulseAudio, Xvfb and Chromium came up.
  - The join failed at 24 s: `Locator.fill: Timeout 20000ms exceeded` waiting for the name field.
  - Opening the same link in the same Chromium showed Google's refusal page, "You can't join this video call", with no name field. The page is the same at 5 s and at 15 s.
  - So this is the platform refusing a guest browser from this VM, not a joinly crash.
  - joinly reports it only as a generic join failure.
- **Meet, run 2:** joinly with Google Chrome stable (157) installed in the container in place of Playwright's Chromium.
  - Chrome never opened its DevTools port for joinly (no `DevToolsActivePort`), so the session hung.
  - Stopped; not pursued.
- **Meet, run 3:** joinly with the VM's own browser mounted read-only into the container. Playwright's Chromium path was pointed at it with a two-line launcher, so joinly itself is unpatched.
  - joinly got past the name field and clicked "Join now".
  - It then failed its 10 s join check.
  - Replaying the same steps showed what Meet did. The pre-join page said "This call is open to anyone" and "System info will be sent to confirm you're not a bot". After "Join now", Meet switched to "You can't join this video call", which stayed for 25 s and more.
  - So Google's anti-bot check refuses the anonymous guest. The meeting's access settings are not the cause.
