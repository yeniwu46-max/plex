"""Disposable Python containers. No project mounts, host environment or network.

Docker itself is an administrator-managed dependency; the web service never
pulls images or starts the daemon. A missing image/daemon fails closed.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import uuid

from .execution_errors import ExecutionUnavailable

OUTPUT_LIMIT = 64 * 1024
WALL_SECONDS = 8
_SLOTS = threading.BoundedSemaphore(2)
_LAUNCHER = """import json, os, sys
p = json.load(sys.stdin)
with open('/tmp/program.py', 'w', encoding='utf-8') as f: f.write(p['code'])
with open('/tmp/input.txt', 'w', encoding='utf-8') as f: f.write(p['stdin'])
fd = os.open('/tmp/input.txt', os.O_RDONLY)
os.dup2(fd, 0)
os.close(fd)
os.execv(sys.executable, [sys.executable, '-I', '-u', '/tmp/program.py'])
"""


def container_args(name: str, image: str) -> list[str]:
    return [
        'docker', 'run', '--init', '-i', '--pull=never', '--name', name,
        '--network=none', '--read-only', '--cap-drop=ALL',
        '--security-opt=no-new-privileges', '--pids-limit=32',
        '--memory=128m', '--memory-swap=128m', '--cpus=0.5',
        '--ulimit=cpu=2:3', '--ulimit=nofile=64:64',
        '--user=65534:65534', '--tmpfs=/tmp:rw,noexec,nosuid,size=16m',
        '--log-driver=none', image, 'python', '-I', '-u', '-c', _LAUNCHER,
    ]


def run_container(code: str, stdin: str, *, image: str) -> dict:
    if not _SLOTS.acquire(blocking=False):
        raise ExecutionUnavailable('busy')
    name = 'plex-exec-' + uuid.uuid4().hex
    proc = None
    readers = []
    output = [bytearray(), bytearray()]
    overflow = threading.Event()
    timed_out = False
    started = time.monotonic()
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    def drain(pipe, index):
        try:
            while chunk := pipe.read(4096):
                remaining = OUTPUT_LIMIT - len(output[index])
                output[index].extend(chunk[:max(remaining, 0)])
                if len(chunk) > remaining:
                    overflow.set()
        except (OSError, ValueError):
            pass

    try:
        proc = subprocess.Popen(container_args(name, image), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                creationflags=flags)
        for index, pipe in enumerate((proc.stdout, proc.stderr)):
            reader = threading.Thread(target=drain, args=(pipe, index), daemon=True)
            reader.start()
            readers.append(reader)

        # Writing may block while Docker starts, so it shares the wall deadline.
        def feed():
            try:
                proc.stdin.write(json.dumps({'code': code, 'stdin': stdin}).encode('utf-8'))
                proc.stdin.close()
            except (OSError, ValueError):
                pass

        writer = threading.Thread(target=feed, daemon=True)
        writer.start()
        while proc.poll() is None:
            timed_out = time.monotonic() - started > WALL_SECONDS
            if timed_out or overflow.is_set():
                break
            time.sleep(0.02)
        if timed_out or overflow.is_set():
            # A daemon failure can also time out: only a container that actually
            # started may receive a student execution verdict.
            try:
                inspected = subprocess.run(['docker', 'inspect', '--format', '{{.State.StartedAt}}', name],
                                           capture_output=True, timeout=3, creationflags=flags)
                if inspected.returncode or inspected.stdout.strip().startswith(b'0001-'):
                    raise ExecutionUnavailable('startup_timeout')
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ExecutionUnavailable('startup_timeout') from exc
        else:
            for reader in readers:
                reader.join(timeout=1)
        try:
            inspected = subprocess.run(['docker', 'inspect', '--format', '{"state":{{json .State}},"image":{{json .Image}}}', name],
                                       capture_output=True, timeout=3, creationflags=flags)
            container = json.loads(inspected.stdout) if inspected.returncode == 0 else {}
            state = container.get('state', {})
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            raise ExecutionUnavailable('container_state_unavailable') from exc
        if not state or state.get('Error') or (not timed_out and not overflow.is_set()
                and (state.get('Status') != 'exited' or state.get('ExitCode') != proc.returncode)):
            raise ExecutionUnavailable('container_start_or_transport_failed')
        status = (14 if overflow.is_set() else 5 if timed_out or state.get('ExitCode') == 152 else
                  7 if state.get('OOMKilled') else 3 if state.get('ExitCode') == 0 else 11)
        return {
            'token': name, 'status': {'id': status, 'description': {
                3: 'Accepted', 5: 'Time Limit Exceeded', 7: 'Memory Limit Exceeded', 11: 'Runtime Error',
                14: 'Output Limit Exceeded',
            }[status]},
            'stdout': output[0].decode('utf-8', errors='replace'),
            'stderr': output[1].decode('utf-8', errors='replace'),
            'compile_output': None, 'time': None, 'memory': None,
            'wall_time_ms': round((time.monotonic() - started) * 1000),
            'language': 'python', 'backend': 'docker', 'image_id': container.get('image'),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        raise ExecutionUnavailable('container_unavailable') from exc
    finally:
        # Kill by server-generated name even if the CLI disconnected. Never use
        # user input in Docker options, mounts, image names or cleanup targets.
        try:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True,
                           timeout=3, creationflags=flags)
        except (OSError, subprocess.SubprocessError):
            pass
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            for reader in readers:
                reader.join(timeout=1)
        _SLOTS.release()
