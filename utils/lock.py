# utils/lock.py
import atexit
import os

LOCK_DIR = os.path.expanduser("~/.crypto_tracker")
LOCK_PATH = os.path.join(LOCK_DIR, "daemon.lock")


class SingleInstanceLock:
    def __init__(self, path: str = LOCK_PATH):
        self.path = path
        self._acquired = False

    def acquire(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            # atomic create, fail if exists
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as f:
                f.write(str(os.getpid()))
            self._acquired = True
            atexit.register(self.release)
            return True
        except FileExistsError:
            return False

    def release(self):
        if self._acquired:
            try:
                os.remove(self.path)
            except FileNotFoundError:
                pass
            self._acquired = False
