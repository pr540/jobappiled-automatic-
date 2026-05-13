"""
Continuous loop runner — runs Search → Apply → Outreach every INTERVAL minutes.
Runs until Ctrl+C or laptop shutdown.  Logs to logs/loop_run.log.

Usage:
  python run_loop.py                         # linkedin + naukri + indeed, every 120 min
  python run_loop.py --platforms linkedin naukri
  python run_loop.py --interval 90
  python run_loop.py --search-only
"""
import os
import sys
import time
import signal
import argparse
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

os.makedirs(os.path.join(SCRIPT_DIR, "logs"), exist_ok=True)
LOG_FILE = os.path.join(SCRIPT_DIR, "logs", "loop_run.log")


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def kill_chrome():
    for proc in ["chromedriver.exe", "chrome.exe"]:
        subprocess.run(["taskkill", "/F", "/IM", proc],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def run_cycle(platforms: list[str], limit: int, search_only: bool, apply_only: bool):
    """One full cycle via run_daily.py subprocess so each cycle gets a fresh process."""
    cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "run_daily.py"),
        "--platforms", *platforms,
        "--limit", str(limit),
        "--retry-errors",
    ]
    if search_only:
        cmd.append("--search-only")
    if apply_only:
        cmd.append("--apply-only")

    log(f"Cycle START  platforms={platforms}  limit={limit}")
    kill_chrome()

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)

    kill_chrome()
    status = "OK" if result.returncode == 0 else f"exit={result.returncode}"
    log(f"Cycle END  [{status}]")
    return result.returncode == 0


_stop = False


def _handle_signal(signum, frame):
    global _stop
    log("Stop signal received — finishing after current cycle")
    _stop = True


def main():
    parser = argparse.ArgumentParser(description="Continuous JobBot loop")
    parser.add_argument("--platforms", nargs="+",
                        choices=["linkedin", "naukri", "indeed", "glassdoor"],
                        default=["linkedin", "naukri", "indeed"])
    parser.add_argument("--interval", type=int, default=120,
                        help="Minutes between cycles (default: 120)")
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--search-only", action="store_true")
    parser.add_argument("--apply-only", action="store_true")
    args = parser.parse_args()

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    log("=" * 60)
    log(f"  JOBBOT LOOP STARTED")
    log(f"  Platforms : {args.platforms}")
    log(f"  Interval  : every {args.interval} min")
    log(f"  Limit     : {args.limit} jobs/cycle")
    log(f"  Log file  : {LOG_FILE}")
    log("=" * 60)

    cycle = 0
    while not _stop:
        cycle += 1
        log(f"--- Cycle #{cycle} ---")
        run_cycle(args.platforms, args.limit, args.search_only, args.apply_only)

        if _stop:
            break

        next_run = datetime.now().replace(second=0, microsecond=0)
        wait_secs = args.interval * 60
        log(f"Sleeping {args.interval} min — next cycle at "
            f"{datetime.fromtimestamp(time.time() + wait_secs).strftime('%H:%M')}")

        # Sleep in 30-second slices so Ctrl+C is responsive
        for _ in range(wait_secs // 30):
            if _stop:
                break
            time.sleep(30)
        remaining = wait_secs % 30
        if remaining and not _stop:
            time.sleep(remaining)

    log("Loop stopped cleanly.")


if __name__ == "__main__":
    main()
