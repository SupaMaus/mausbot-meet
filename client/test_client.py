"""mausbot-meet test client: a tiny MCP client for a hands-on joinly test. No LLM: it calls joinly's tools in a fixed order and records timings.

Run it INSIDE the joinly container, so the server never listens outside it:
    docker cp test_client.py joinly:/tmp/c.py
    docker exec -it joinly /app/.venv/bin/python /tmp/c.py --selfcheck
    docker exec -it joinly /app/.venv/bin/python /tmp/c.py --url '<meeting link>' [--passcode 123456]

It uses the fastmcp that ships inside the joinly v0.5.4 image (pinned by joinly's uv.lock), so nothing is installed.
Admission: the script waits until it sees other participants, or until you run `docker exec joinly touch /tmp/admitted`.
UNTESTED until the first run: tool result shapes are printed raw rather than assumed.
"""

import argparse
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

URL = "http://127.0.0.1:8000/mcp/"
T0 = time.monotonic()
TIMES: dict[str, float] = {}
RESULTS: dict[str, object] = {}


def log(msg: str) -> None:
    print(f"[{time.monotonic() - T0:7.1f}s] {msg}", flush=True)


def mark(key: str) -> None:
    TIMES[key] = round(time.monotonic() - T0, 1)


def text_of(result: object) -> str:
    """Raw text of a tool result, whatever fastmcp version returned it."""
    content = getattr(result, "content", result)
    if isinstance(content, list):
        return "\n".join(getattr(c, "text", None) or f"<{type(c).__name__}>" for c in content)
    return str(content)


async def call(client: Client, name: str, args: dict | None = None, show: bool = True) -> tuple[bool, object]:
    try:
        result = await client.call_tool(name, args or {})
        if show:
            log(f"{name} -> {text_of(result)[:600]}")
        return True, result
    except Exception as e:  # noqa: BLE001
        log(f"{name} FAILED: {type(e).__name__}: {str(e)[:600]}")
        return False, e


async def snapshot(client: Client, out: Path, label: str) -> None:
    ok, result = await call(client, "get_video_snapshot", show=False)
    if not ok:
        return
    for c in getattr(result, "content", []) or []:
        data = getattr(c, "data", None)
        if data:
            path = out / f"snapshot-{label}.png"
            path.write_bytes(base64.b64decode(data))
            log(f"snapshot saved: {path}")


def procs() -> list[str]:
    seen = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        for key in ("pulseaudio", "Xvfb", "chrome", "x11vnc"):
            if key in cmd and "--type=" not in cmd:
                seen.append(f"{pid} {cmd[:160]}")
    return seen


def pulse_devices() -> str:
    """pactl against joinly's own PulseAudio (its socket path is in the daemon's environment)."""
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            if b"pulseaudio" not in Path(f"/proc/{pid}/cmdline").read_bytes():
                continue
            env = dict(
                kv.split("=", 1) for kv in Path(f"/proc/{pid}/environ").read_bytes().decode(errors="replace").split("\0") if "=" in kv
            )
        except OSError:
            continue
        runtime = env.get("PULSE_RUNTIME_PATH")
        if runtime:
            e = {**os.environ, "PULSE_SERVER": f"unix:{runtime}/native"}
            out = []
            for what in ("sinks", "sources"):
                r = subprocess.run(["pactl", "list", "short", what], env=e, capture_output=True, text=True, timeout=10)
                out.append(f"{what}:\n{r.stdout.strip() or r.stderr.strip()}")
            return "\n".join(out)
    return "no pulseaudio process found"


async def new_segments(client: Client, seen: float) -> tuple[float, list[dict]]:
    """Reads transcript://live and returns segments that start after `seen` (seconds), as joinly's own example does."""
    try:
        contents = await client.read_resource("transcript://live")
        data = json.loads(contents[0].text)
    except Exception as e:  # noqa: BLE001
        log(f"read transcript://live failed: {e}")
        return seen, []
    segs = data.get("segments", data if isinstance(data, list) else [])
    fresh = sorted((s for s in segs if float(s.get("start", 0)) > seen), key=lambda s: float(s.get("start", 0)))
    return (float(fresh[-1].get("start", seen)) if fresh else seen), fresh


async def selfcheck(client: Client, hold: int) -> None:
    tools = await client.list_tools()
    log("tools: " + ", ".join(t.name for t in tools))
    resources = await client.list_resources()
    log("resources: " + ", ".join(str(r.uri) for r in resources))
    await asyncio.sleep(5)
    log("processes started for this session:\n  " + "\n  ".join(procs() or ["(none)"]))
    log("audio devices in joinly's PulseAudio:\n" + pulse_devices())
    await call(client, "get_participants")  # expected to fail: not in a meeting
    log(f"holding the session {hold}s so CPU/RAM can be sampled from outside")
    await asyncio.sleep(hold)


async def meeting(client: Client, a: argparse.Namespace) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    flag = Path("/tmp/admitted")
    flag.unlink(missing_ok=True)

    args = {"meeting_url": a.url, "participant_name": a.name}
    if a.passcode:
        args["passcode"] = a.passcode
    log(f"join_meeting {a.url}")
    ok, _ = await call(client, "join_meeting", args)
    mark("join_returned")
    RESULTS["join"] = ok
    await snapshot(client, out, "after-join")
    if not ok:
        return

    log("waiting to be admitted (participants seen, or `docker exec joinly touch /tmp/admitted`)")
    deadline = time.monotonic() + a.lobby
    admitted = False
    while time.monotonic() < deadline:
        if flag.exists():
            admitted = True
            break
        ok, result = await call(client, "get_participants", show=False)
        if ok and text_of(result).count('"name"') >= 2:
            admitted = True
            break
        await asyncio.sleep(5)
    mark("admitted" if admitted else "lobby_gave_up")
    RESULTS["admitted"] = admitted
    await call(client, "get_participants")
    await snapshot(client, out, "admitted")
    if not admitted:
        await call(client, "leave_meeting")
        return

    ok, _ = await call(client, "send_chat_message", {"message": a.notice})
    mark("chat_sent")
    RESULTS["chat_sent"] = ok
    await call(client, "get_chat_history")

    log("say something now; waiting for the first transcript line")
    seen, first = -1.0, None
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and first is None:
        seen, segs = await new_segments(client, seen)
        for s in segs:
            log(f"HEARD {s.get('speaker')}: {s.get('text')}")
            first = first or s
        await asyncio.sleep(2)
    mark("first_heard" if first else "nothing_heard")
    RESULTS["heard"] = first is not None

    await call(client, "unmute_yourself")
    log(f"speak_text: {a.say!r} (stay quiet while it speaks; talking over it interrupts it)")
    t = time.monotonic()
    ok, _ = await call(client, "speak_text", {"text": a.say})
    mark("spoke")
    RESULTS["speak_text_ok"] = ok
    RESULTS["speak_seconds"] = round(time.monotonic() - t, 1)

    log(f"listening {a.listen}s; reply in the meeting so the transcript can be checked")
    end = time.monotonic() + a.listen
    while time.monotonic() < end:
        seen, segs = await new_segments(client, seen)
        for s in segs:
            log(f"HEARD {s.get('speaker')}: {s.get('text')}")
        await asyncio.sleep(2)

    ok, result = await call(client, "get_transcript", show=False)
    (out / "transcript.json").write_text(text_of(result))
    ok, result = await call(client, "get_chat_history", show=False)
    (out / "chat.json").write_text(text_of(result))
    try:
        usage = await client.read_resource("usage://current")
        (out / "usage.json").write_text(usage[0].text)
    except Exception:  # noqa: BLE001, S110
        pass
    await call(client, "leave_meeting")
    mark("left")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--selfcheck", action="store_true", help="no meeting: start a session, list tools, devices, processes")
    p.add_argument("--hold", type=int, default=30)
    p.add_argument("--url")
    # No brackets: Teams keeps Join disabled for guest names with them, and joinly does not sanitise names.
    # No "bot" either, in case Meet keys on it. Override per run.
    p.add_argument("--name", default="Maus Notes")
    p.add_argument("--passcode")
    p.add_argument("--notice", default="Hi, I'm a MausBot test bot. This is a test; I'm transcribing this call and will leave in a few minutes.")
    p.add_argument("--say", default="Hi, I'm a test bot. Can you hear me clearly?")
    p.add_argument("--lobby", type=int, default=600)
    p.add_argument("--listen", type=int, default=90)
    p.add_argument("--out", default="/tmp/joinly-run")
    a = p.parse_args()
    if not a.selfcheck and not a.url:
        p.error("--url or --selfcheck")

    # One connection for the whole test: joinly makes one meeting session per client connection.
    async with Client(StreamableHttpTransport(url=URL)) as client:
        mark("connected")
        log("connected to joinly")
        if a.selfcheck:
            await selfcheck(client, a.hold)
        else:
            await meeting(client, a)
    summary = {"times_s": TIMES, "results": RESULTS}
    print("SUMMARY " + json.dumps(summary), flush=True)
    if not a.selfcheck:
        Path(a.out, "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
