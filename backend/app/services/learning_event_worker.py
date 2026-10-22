"""Recoverable DB queue worker. Multiple app processes may safely run it."""
import threading
import time
from app.models import db, StudentMistake
from app.services.learner_state import LearnerStateService
from app.services.mistake import MistakeService
from app.utils.time import utc_now


def scan_due_reviews():
    # Schedule snapshots are bounded per worker pass; no mastery modification.
    now = utc_now()
    for row in StudentMistake.query.yield_per(100):
        schedule = (row.meta or {}).get('review_schedule') or {}
        due = MistakeService._parse_review_time(schedule.get('due_at'))
        if due and due <= now:
            LearnerStateService.append(user_id=row.user_id, kind='review_due', source_type='mistake_schedule',
                source_id=row.id, source_version=schedule['due_at'], occurred_at=due,
                payload={'concept_id': row.knowledge_key, 'due_at': schedule['due_at'], 'evidence_scope': 'schedule'})
    db.session.commit()


def start_learning_event_worker(app):
    if app.config.get('TESTING') or not app.config.get('LEARNER_STATE_WORKER_ENABLED', True):
        return
    if app.extensions.get('learning_event_worker'):
        return
    def work():
        next_scan = 0
        while True:
            with app.app_context():
                try:
                    if time.monotonic() >= next_scan:
                        scan_due_reviews()
                        next_scan = time.monotonic() + 60
                    LearnerStateService.drain(50)
                except Exception:
                    db.session.rollback()
                    app.logger.exception('Learning evidence worker failed; committed events remain recoverable.')
                finally:
                    db.session.remove()
            time.sleep(3)
    thread = threading.Thread(target=work, daemon=True, name='plex-learning-events')
    app.extensions['learning_event_worker'] = thread
    thread.start()
