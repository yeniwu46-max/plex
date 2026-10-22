"""Bounded, restart-safe maintenance for exam deadlines and resource expiry."""
import threading


def start_student_maintenance(app):
    if app.config.get('TESTING') or not app.config.get('STUDENT_MAINTENANCE_ENABLED', True) or app.extensions.get('student_maintenance'):
        return
    stop = threading.Event()
    app.extensions['student_maintenance'] = stop

    def run():
        while not stop.wait(15):
            with app.app_context():
                from app.models import db
                try:
                    from app.services.resource_trash import ResourceTrash
                    from app.services.student_practice import MockExams
                    ResourceTrash.purge()
                    MockExams.sweep()
                except Exception:
                    db.session.rollback()
                    app.logger.exception('Student maintenance deferred')
                finally:
                    db.session.remove()
    threading.Thread(target=run, name='student-maintenance', daemon=True).start()
