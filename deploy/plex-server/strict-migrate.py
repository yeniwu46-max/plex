"""Apply Alembic without the development init/reseed/stamp recovery path."""
import sys
from pathlib import Path
from alembic import command
from sqlalchemy import inspect, text

backend = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(backend))
from manage import database_app, alembic_config
from app.models import db

app = database_app()
with app.app_context():
    before = set(inspect(db.engine).get_table_names())
    if 'alembic_version' not in before:
        raise SystemExit('Existing versioned database required; no automatic initialization.')
    counts = {name: db.session.execute(text(f'SELECT COUNT(*) FROM {name}')).scalar_one()
              for name in ('users','trial_participations','personalized_learning_resources') if name in before}
    db.session.remove()
    command.upgrade(alembic_config(), 'head')
    db.engine.dispose()
    for name, expected in counts.items():
        actual = db.session.execute(text(f'SELECT COUNT(*) FROM {name}')).scalar_one()
        if actual != expected:
            raise RuntimeError(f'Migration changed {name} row count: {expected} -> {actual}')
    print('migration_counts_preserved:', counts)
    print('revision:', db.session.execute(text('SELECT version_num FROM alembic_version')).scalar_one())
