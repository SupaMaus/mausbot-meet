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
| Session start: PulseAudio, Xvfb, Chromium processes | not run |
| Virtual speaker and mic present | not run |
| Kokoro speaks → Whisper reads it back | not run |
| CPU / RAM idle, session open | not run |

## Per platform

| | Google Meet | Zoom (web) | Teams |
|---|---|---|---|
| Reached the waiting room (s from start) | no: refused before the name screen | | |
| Admitted (s) | | | |
| Refused by the platform? (what it said) | **yes**: Meet showed "You can't join this video call" to joinly's Chromium; joinly timed out after 20 s waiting for the name field | | |
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
