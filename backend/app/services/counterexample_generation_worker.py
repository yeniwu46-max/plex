"""DB queue dispatcher sharing the existing resource execution pool."""
from threading import Event, Thread
from app.services.resource_executor import submit_resource_task, RESOURCE_WORKERS
from app.services.counterexample_generation import run_once


def start_counterexample_generation_worker(app):
    if app.testing or not app.config.get('COUNTEREXAMPLE_GENERATION_WORKER_ENABLED', True):
        return
    if 'counterexample_generation_worker' in app.extensions:
        return
    stop = Event()

    def dispatch():
        pending = []
        while not stop.is_set():
            active = []
            for future in pending:
                if not future.done():
                    active.append(future)
                else:
                    try:
                        future.result()
                    except Exception as exc:
                        # No exception text: driver errors can include bound values.
                        app.logger.warning('Candidate queue iteration failed: %s', type(exc).__name__)
            pending = active
            for _ in range(RESOURCE_WORKERS-len(pending)):
                pending.append(submit_resource_task(run_once, app))
            stop.wait(3)

    thread = Thread(target=dispatch, name='plex-counterexample-dispatch', daemon=True)
    app.extensions['counterexample_generation_worker'] = {'thread': thread, 'stop': stop}
    thread.start()
