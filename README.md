# mausbot-meet

MausBot's open-source meeting bot. It joins Zoom, Google Meet and Microsoft Teams calls as a guest, talks, posts in the meeting chat and keeps a live transcript.

It is built on **[joinly](https://github.com/joinly-ai/joinly)** (MIT), an MCP server that does the hard parts:
- it joins the call in a real Chromium;
- it gives that browser a virtual speaker and a virtual microphone;
- it transcribes what it hears;
- it speaks through text-to-speech.

joinly runs unmodified, from its published container image pinned by digest. None of its code is copied here.

> **Status: proof of concept.** The only question right now is "does it really join?", for each platform.
> Results are in [RESULTS.md](RESULTS.md). There is no service API yet: that waits until a real Google Meet join works.

## How it runs

```
your machine ──Boat API──▶ one throwaway Linux VM (Boat, 4 vCPU / 8 GB)
                              └─ docker: joinly (pinned)  ── listens on 127.0.0.1 inside its own container only
                                    ├─ private PulseAudio: virtual speaker (meeting audio in), virtual mic (TTS out)
                                    ├─ private Xvfb + Chromium  ──▶ Meet / Zoom / Teams
                                    ├─ Whisper (local, CPU) speech-to-text, Kokoro (local) text-to-speech
                                    └─ client/test_client.py, run with docker exec (no LLM)
```

- joinly has no authentication, so it is **never** exposed: no published port and no public URL.
- The test client runs inside the same container.
- Nothing runs on your own machine except the `curl` calls in `scripts/boat.sh`.
- Speech is local by default (Whisper base and Kokoro), so no paid keys are needed.
- joinly also supports ElevenLabs, Deepgram and Gemini for speech. Keys go only in a `0600` env file on the VM.

## Try it

```bash
export BOAT_API_KEY=...                       # your boat.dev key; never commit it
ID=$(scripts/boat.sh create)                  # wait until `scripts/boat.sh state $ID` says idle/ready
scripts/boat.sh put  $ID scripts/boat-vm-setup.sh /home/user/meet/boat-vm-setup.sh
scripts/boat.sh put  $ID client/test_client.py    /home/user/meet/test_client.py
scripts/boat.sh exec $ID 120 'bash ~/meet/boat-vm-setup.sh preflight'
scripts/boat.sh exec $ID 600 'bash ~/meet/boat-vm-setup.sh pull'
scripts/boat.sh exec $ID 120 'bash ~/meet/boat-vm-setup.sh start'
scripts/boat.sh exec $ID 300 'bash ~/meet/boat-vm-setup.sh ttsstt'      # Kokoro speaks, Whisper reads it back
scripts/boat.sh exec $ID 200 'docker cp ~/meet/test_client.py joinly:/tmp/c.py &&
  docker exec joinly /app/.venv/bin/python /tmp/c.py --selfcheck --hold 20'

# A real meeting (one long connection, so run it detached and follow the log):
scripts/boat.sh detach $ID "docker exec joinly /app/.venv/bin/python /tmp/c.py --url 'https://meet.google.com/xxx-yyyy-zzz' > /tmp/run.log 2>&1"
scripts/boat.sh exec   $ID 30 'tail -n 40 /tmp/run.log; bash ~/meet/boat-vm-setup.sh stats'
scripts/boat.sh exec   $ID 30 'docker exec joinly touch /tmp/admitted'   # if the script hasn't noticed you admitted it

scripts/boat.sh delete $ID                    # when done; the 3 h TTL also stops it
```

What the test client does:
1. `join_meeting`.
2. It waits for you to admit the bot.
3. `send_chat_message`, a notice that it is transcribing.
4. It waits for you to speak.
5. `speak_text` ("Hi, I'm a test bot. Can you hear me clearly?").
6. It reads `transcript://live` for 90 s.
7. `leave_meeting`.

It prints timings and a `SUMMARY` line. Use `--passcode` for Zoom and `--name` for another display name. The default name has no brackets, because Teams refuses brackets in guest names.

## What the host needs

Only Docker, about 3 GB of free RAM, about 5 GB of disk and outbound HTTPS. The joinly image brings its own PulseAudio, Xvfb and Chromium, so the host needs no sound card, audio server or display.

## Known limits

- A person must admit the bot from the waiting room.
- Meetings that block outside or anonymous guests can't be joined.
- Google Meet may refuse guests from cloud IPs ("You can't join this video call").
- Zoom must allow joining from the browser and may show a captcha.
- joinly matches only `*.zoom.us`, `teams.microsoft.com` and `teams.live.com` links.

## Credits

- [joinly](https://github.com/joinly-ai/joinly): MIT, Copyright (c) 2025 Dominik Brockmann, Johannes Dittrich, Fynn Aurand.
- Kokoro (Apache-2.0), faster-whisper (MIT) and Silero VAD (MIT), as packaged in joinly's image.

## License

MIT. See [LICENSE](LICENSE).
