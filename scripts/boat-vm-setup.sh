#!/bin/bash
# Runs ON the meeting VM (a throwaway Boat VM), never on your own machine.
# Preflight, pull joinly pinned by digest, start it bound to 127.0.0.1 inside its own container (no port published),
# check TTS -> STT offline, and sample CPU/RAM.
# Usage on the VM: bash boat-vm-setup.sh preflight | pull | start | ttsstt | stats | stop
set -u
# joinly v0.5.4 (MIT, https://github.com/joinly-ai/joinly), multi-arch index digest, resolved from ghcr.io on 2026-11-17.
IMG=ghcr.io/joinly-ai/joinly:v0.5.4@sha256:d19ca294eb24625d69d8069d0168cb5214af3652fbf721eb07480177eb4b9ea0
# Docker may need sudo on the VM; set D="sudo docker" if `docker ps` is refused.
D=${D:-docker}

case "${1:-}" in
preflight)
  echo "== os";   . /etc/os-release; echo "$PRETTY_NAME"; uname -r
  echo "== cpu";  nproc; grep -m1 'model name' /proc/cpuinfo
  echo "== ram";  free -m
  echo "== disk"; df -h / | tail -1
  echo "== docker"; $D version --format 'server {{.Server.Version}}' 2>&1 | tail -1
  echo "== host audio (not needed by the joinly image, which brings its own PulseAudio)"; pactl info 2>&1 | sed -n '1,4p'
  echo "== display"; echo "DISPLAY=${DISPLAY:-unset}"; command -v Xvfb || echo "no Xvfb on host (the image brings its own)"
  echo "== outbound https"
  for u in https://ghcr.io/v2/ https://meet.google.com/ https://app.zoom.us/wc https://teams.microsoft.com/ https://teams.live.com/ https://huggingface.co/; do
    curl -sS -o /dev/null --max-time 15 -w "%{http_code} %{time_total}s $u\n" "$u" || echo "FAIL $u"
  done
  echo "== outbound UDP (STUN to Google, the path Meet media prefers)"
  python3 - <<'PY'
import os, socket, struct
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(4)
req = struct.pack("!HHI12s", 1, 0, 0x2112A442, os.urandom(12))
try:
    s.sendto(req, ("stun.l.google.com", 19302)); data, _ = s.recvfrom(2048)
    print("UDP 19302 ok: STUN answered", len(data), "bytes")
except Exception as e:
    print("UDP 19302 FAILED:", e)
PY
  ;;
pull)
  start=$SECONDS; $D pull "$IMG" | tail -3; echo "pull took $((SECONDS - start))s"
  $D image inspect "$IMG" --format 'digest {{index .RepoDigests 0}}  size {{.Size}} bytes'
  ;;
start)
  $D rm -f joinly >/dev/null 2>&1
  # --host 127.0.0.1: the MCP server listens only inside the container's own network namespace; no -p, so nothing
  # on the VM (let alone the internet) can reach it. The test client runs inside the same container.
  $D run -d --name joinly --restart no "$IMG" --host 127.0.0.1 --port 8000 --stt whisper --tts kokoro -v
  sleep 8; $D logs --tail 30 joinly
  ;;
ttsstt)
  # Offline round trip with the image's own models: Kokoro speaks a sentence, Whisper base transcribes it.
  $D exec -i joinly /app/.venv/bin/python - <<'PY'
import os, time, wave, numpy as np
from pathlib import Path
from kokoro_onnx import Kokoro
from faster_whisper import WhisperModel
cache = Path(os.getenv("XDG_CACHE_HOME", "~/.cache")).expanduser() / "kokoro"
t = time.time(); k = Kokoro(str(cache / "kokoro-v1.0.onnx"), str(cache / "voices-v1.0.bin"))
text = "Hi, I'm a test bot. Can you hear me clearly?"
samples, sr = k.create(text, voice="af_bella")
print(f"kokoro: {len(samples)/sr:.2f}s of audio at {sr} Hz in {time.time()-t:.1f}s (incl. load)")
pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
with wave.open("/tmp/tts.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
t = time.time(); m = WhisperModel("base", device="cpu", compute_type="int8")
segs, _ = m.transcribe("/tmp/tts.wav", language="en")
print(f"whisper base heard: {' '.join(s.text.strip() for s in segs)!r} in {time.time()-t:.1f}s (incl. load)")
PY
  ;;
stats)
  echo "== $(date -u +%FT%TZ) loadavg $(cut -d' ' -f1-3 /proc/loadavg)"; free -m | sed -n '1,2p'
  $D stats --no-stream --format 'container {{.Name}} cpu {{.CPUPerc}} mem {{.MemUsage}}' joinly
  ;;
stop)
  $D rm -f joinly
  ;;
*) echo "usage: $0 preflight|pull|start|ttsstt|stats|stop"; exit 2 ;;
esac
