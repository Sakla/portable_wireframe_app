"""Run blocking work on a thread pool and deliver results on the UI thread."""
import traceback

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from ..engines.base import EngineError


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = _Signals()

    def run(self):
        try:
            result = self.fn()
        except EngineError as exc:
            self.signals.failed.emit(str(exc))
        except Exception as exc:  # show unexpected failures on the card instead of crashing
            traceback.print_exc()
            self.signals.failed.emit(f"Unexpected error: {exc}")
        else:
            self.signals.done.emit(result)


class Runner:
    def __init__(self, max_threads: int = 2):
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(max_threads)  # models are memory-hungry on CPU
        self._jobs = set()

    def submit(self, fn, on_done, on_failed):
        job = _Job(fn)
        job.setAutoDelete(False)
        self._jobs.add(job)

        def finish(handler):
            def slot(value):
                self._jobs.discard(job)
                handler(value)
            return slot

        job.signals.done.connect(finish(on_done))
        job.signals.failed.connect(finish(on_failed))
        self.pool.start(job)

    def wait(self, msecs: int = -1) -> bool:
        return self.pool.waitForDone(msecs)
