"""Request-local transport metadata; never retains prompts, replies or secrets."""
from contextlib import contextmanager
from contextvars import ContextVar

_observer = ContextVar('plex_model_observer', default=None)

@contextmanager
def observe_model():
    observed = {}
    token = _observer.set(observed)
    try:
        yield observed
    finally:
        _observer.reset(token)

def report_model(**metadata):
    observer = _observer.get()
    if observer is not None:
        observer.update(metadata)
