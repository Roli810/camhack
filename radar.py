#!/usr/bin/env python3
import subprocess
import re
import os
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT_FILE = "ips_with_port.txt"
OUTPUT_FILE = "working_ips.txt"
FULL_OUTPUT_FILE = "cameradar_output.txt"
ERROR_LOG = "errors.txt"

THREADS = 5
TIMEOUT = 120
USE_SUDO = True
DOCKER_CMD = ["sudo", "docker"] if USE_SUDO else ["docker"]
ANSI_ESCAPE = re.compile(r'(\x9B|\x1B\[)[0-9;]*[A-Za-z]|\x1B[@-_][0-9;]*[A-Za-z]?')

shutdown_flag = False

def strip_ansi(text):
    return ANSI_ESCAPE.sub('', text)

def scan_ip(target):
    if shutdown_flag:
        return target, "SHUTDOWN", False, -99

    # No "scan" subcommand — flags go directly after the image name
    cmd = DOCKER_CMD + [
    "run", "--rm",
    "--network=host",
    "ullaakut/cameradar",
    "-t", target.split(":")[0],   # IP only
    "-p", target.split(":")[1],   # port only
    "--skip-scan",
    "-T", "10s",
    "--ui", "plain",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
            env={**os.environ, "TERM": "dumb"}
        )
        output = strip_ansi(result.stdout + result.stderr)
        success = (
            "Accessible streams:" in output
            and "Accessible streams: 0" not in output
        )
        return target, output, success, result.returncode
    except subprocess.TimeoutExpired:
        return target, f"TIMEOUT after {TIMEOUT}s", False, -1
    except Exception as e:
        return target, f"EXCEPTION: {e}", False, -2


def handle_sigint(sig, frame):
    global shutdown_flag
    print("\n[!] Ctrl+C — finishing current batch...")
    shutdown_flag = True


def main():
    signal.signal(signal.SIGINT, handle_sigint)

    with open(INPUT_FILE) as f:
        targets = [line.strip() for line in f if line.strip()]

    print(f"[*] Loaded {len(targets)} targets")
    print(f"[*] Threads: {THREADS} | Timeout: {TIMEOUT}s | skip-scan: ON\n")

    working, full, errors = [], [], []
    completed = 0

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(scan_ip, t): t for t in targets}
        for future in as_completed(futures):
            if shutdown_flag:
                for f in futures:
                    f.cancel()
                break

            target, output, success, retcode = future.result()
            completed += 1

            if success:
                working.append(target)
                full.append(f"=== {target} ===\n{output}\n")
                print(f"[+] HIT: {target}")
            else:
                errors.append(f"{target}: retcode={retcode} | {output[:300].replace(chr(10), ' ')}")
                print(f"[-] {target} (retcode={retcode})")

            if completed % 5 == 0 or completed == len(targets):
                print(f"[*] Progress: {completed}/{len(targets)} | Hits: {len(working)}")

    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(working))
    with open(FULL_OUTPUT_FILE, "w") as f:
        f.write("\n".join(full))
    with open(ERROR_LOG, "w") as f:
        f.write("\n".join(errors))

    print(f"\n[*] DONE: {len(working)}/{len(targets)} streams accessible")
    print(f"[*] Hits     → {OUTPUT_FILE}")
    print(f"[*] Full log → {FULL_OUTPUT_FILE}")
    print(f"[*] Errors   → {ERROR_LOG}")

if __name__ == "__main__":
    main()
