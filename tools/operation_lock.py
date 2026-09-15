"""Serialize agent and CLI client changes across threads and Linux processes."""
import contextlib
import os
import threading

mutex = threading.RLock()
local = threading.local()


@contextlib.contextmanager
def locked(root):
    with mutex:
        if getattr(local, "depth", 0):
            yield
            return
        path = root / "data/control/operation.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as stream:
            if os.name == "posix":
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX)
            local.depth = 1
            try:
                yield
            finally:
                local.depth = 0
                if os.name == "posix":
                    fcntl.flock(stream, fcntl.LOCK_UN)
