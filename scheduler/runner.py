# scheduler/runner.py
import random
import signal
import time
from typing import Callable

from utils.logging import get_logger

from utils.lock import SingleInstanceLock


log = get_logger("scheduler")

class _StopFlag:
    stop = False

def _handle_sig(signum, frame):
    log.info("Received signal %s — stopping after current cycle.", signum)
    _StopFlag.stop = True

def run_daemon(job_fn: Callable[[], None], interval_sec: int = 600, jitter_sec: int = 30):
    lock = SingleInstanceLock()
    if not lock.acquire():
        log.error("Another crypto daemon is already running (lock present). Exiting.")
        return

    try:
        signal.signal(signal.SIGINT, _handle_sig)
        signal.signal(signal.SIGTERM, _handle_sig)

        log.info("Daemon started. Interval=%ss, Jitter=±%ss", interval_sec, jitter_sec)
        while not _StopFlag.stop:
            start = time.time()
            try:
                job_fn()
                log.info("Cycle complete.")
            except Exception as e:
                log.exception("Cycle failed: %s", e)

            base_sleep = max(1, interval_sec - int(time.time() - start))
            jitter = random.randint(-jitter_sec, jitter_sec) if jitter_sec > 0 else 0
            sleep_for = max(1, base_sleep + jitter)
            log.info("Next run in %ss", sleep_for)

            slept = 0
            while slept < sleep_for and not _StopFlag.stop:
                chunk = min(1, sleep_for - slept)
                time.sleep(chunk)
                slept += chunk

        log.info("Daemon stopped.")
    finally:
        lock.release()

