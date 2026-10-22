"""Short database admission locks; never held during model or executor work."""
from contextlib import contextmanager
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from app.models import db
from app.models.ai_runtime import AiRuntimeLock


@contextmanager
def admission_lock(scope):
    # Discard any JWT/read snapshot before serializing across processes.
    db.session.rollback()
    try:
        try:
            with db.session.begin_nested():
                db.session.add(AiRuntimeLock(scope=scope,revision=0));db.session.flush()
        except IntegrityError:
            pass
        db.session.execute(update(AiRuntimeLock).where(AiRuntimeLock.scope==scope)
                           .values(revision=AiRuntimeLock.revision+1))
        yield
    finally:
        # Callers explicitly commit the task and its admission together.
        db.session.rollback()
