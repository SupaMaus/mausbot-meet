# Results

joinly `v0.5.4@sha256:d19ca294…b9ea0` on one Boat VM (default: 4 vCPU / 8 GB), with Whisper base (CPU) and Kokoro.
Nothing has run yet.

## No-meeting checks on the VM

| Check | Result |
|---|---|
| OS / CPU / RAM / disk | not run |
| Docker available | not run |
| Outbound HTTPS (ghcr, Meet, Zoom, Teams, Hugging Face) | not run |
| Outbound UDP (STUN 19302) | not run |
| Image pull time / size | not run |
| Session start: PulseAudio, Xvfb, Chromium processes | not run |
| Virtual speaker and mic present | not run |
| Kokoro speaks → Whisper reads it back | not run |
| CPU / RAM idle, session open | not run |

## Per platform

| | Google Meet | Zoom (web) | Teams |
|---|---|---|---|
| Reached the waiting room (s from start) | | | |
| Admitted (s) | | | |
| Refused by the platform? (what it said) | | | |
| Chat message posted (seen in the meeting) | | | |
| Chat read back (`get_chat_history`) | | | |
| Bot heard people (transcript has their words) | | | |
| Transcript accuracy / speaker names right | | | |
| Bot spoke (heard, clear?) | | | |
| `speak_text` duration (s) | | | |
| CPU / RAM in the call | | | |
| Notes | | | |
