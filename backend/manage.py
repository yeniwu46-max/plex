"""Non-destructive database and demo-data management commands."""
from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from flask import Flask
from sqlalchemy import inspect, text

from app.config import DevelopmentConfig
from app.models import Role, StudentProfile, User, db


ROOT = Path(__file__).resolve().parent


def database_app() -> Flask:
    app = Flask('plex-manage')
    app.config.from_object(DevelopmentConfig)
    app.config['SQLALCHEMY_ECHO'] = False
    db.init_app(app)
    return app


def alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(ROOT / 'alembic.ini'))
    config.set_main_option('script_location', str(ROOT / 'migrations'))
    return config


def cleanup_interrupted_sqlite_batches() -> None:
    if db.engine.dialect.name != 'sqlite':
        return
    allowed = {
        '_alembic_tmp_resource_generation_tasks',
        '_alembic_tmp_personalized_learning_resources',
    }
    present = set(inspect(db.engine).get_table_names())
    for table in sorted(allowed & present):
        db.session.execute(text(f'DROP TABLE "{table}"'))
    if allowed & present:
        db.session.commit()
        print(f"removed interrupted migration tables: {sorted(allowed & present)}")


def init_database() -> None:
    app = database_app()
    with app.app_context():
        cleanup_interrupted_sqlite_batches()
        before = set(inspect(db.engine).get_table_names())
        config = alembic_config()
        if not before:
            db.create_all()
            command.stamp(config, 'head')
        elif 'alembic_version' in before:
            command.upgrade(config, 'head')
            db.create_all()
        else:
            inspector = inspect(db.engine)
            resource_columns = (
                {item['name'] for item in inspector.get_columns('resource_generation_tasks')}
                if 'resource_generation_tasks' in before else set()
            )
            trial_columns = (
                {item['name'] for item in inspector.get_columns('trials')}
                if 'trials' in before else set()
            )
            if 'profile_version' in resource_columns:
                baseline = 'head'
            elif resource_columns:
                baseline = '20260609_0003'
            elif 'system_announcements' in before and 'draft_questions_json' in trial_columns:
                baseline = '20260530_0002'
            else:
                baseline = '20260529_0001'
            command.stamp(config, baseline)
            command.upgrade(config, 'head')
            db.create_all()
        after = set(inspect(db.engine).get_table_names())
        print(f'database initialized: existing={len(before)} total={len(after)} revision=head')


def upgrade_database() -> None:
    app = database_app()
    with app.app_context():
        cleanup_interrupted_sqlite_batches()
        command.upgrade(alembic_config(), 'head')
        print('database upgraded to head')


def migration_smoke() -> None:
    app = database_app()
    with app.app_context():
        cleanup_interrupted_sqlite_batches()
        command.downgrade(alembic_config(), '20260609_0003')
        command.upgrade(alembic_config(), 'head')
        required = {
            'student_profile_suggestions',
            'student_profiles',
            'resource_generation_tasks',
            'personalized_learning_resources',
        }
        present = set(inspect(db.engine).get_table_names())
        missing = required - present
        if missing:
            raise RuntimeError(f'migration smoke missing tables: {sorted(missing)}')
        print('migration downgrade/upgrade smoke passed')


def seed_demo() -> None:
    from app import create_app
    from app.services.student_profile import StudentProfileService
    from werkzeug.security import generate_password_hash

    app = create_app('development')
    with app.app_context():
        student_role = Role.query.filter_by(name='student').first()
        if not User.query.filter_by(username='student002').first():
            db.session.add(User(
                username='student002',
                email='student002@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='学生2',
                role_id=student_role.id,
            ))
            db.session.commit()
        profiles = {
            'student001': {
                'major_background': '计算机专业大一',
                'knowledge_foundation': 'Python 零基础',
                'learning_goal': '两周掌握 Python 基础',
                'explanation_preference': '代码案例优先、分步骤讲解',
                'learning_pace': '每天 30 分钟',
                'interest_direction': '数据处理与校园项目',
                'mistake_pattern': '循环边界与缩进容易出错',
            },
            'student002': {
                'major_background': '软件工程专业',
                'knowledge_foundation': '具备 Python 基础',
                'learning_goal': '强化算法设计与代码质量',
                'explanation_preference': '先解释原理，再分析复杂度',
                'learning_pace': '周末集中学习 3 小时',
                'interest_direction': '算法竞赛',
                'mistake_pattern': '复杂边界条件考虑不足',
            },
        }
        for username, dimensions in profiles.items():
            user = User.query.filter_by(username=username).first()
            if not user:
                continue
            existing = StudentProfile.query.filter_by(user_id=user.id).first()
            if existing and existing.completion_rate == 100:
                continue
            StudentProfileService.apply_changes(user.id, dimensions, 'demo_seed', 'local_rules')
        print('demo profiles seeded idempotently')


def knowledge_check() -> None:
    from app.data.course_knowledge import validate_course_knowledge

    report = validate_course_knowledge()
    if report['status'] != 'passed':
        raise RuntimeError('; '.join(report['errors']))
    print(
        'knowledge base validated: '
        f"{report['valid_knowledge_point_count']}/"
        f"{report['knowledge_point_count']} points, "
        f"{report['document_id_count']} unique document IDs"
    )


def seed_neo4j_graph() -> None:
    import runpy

    runpy.run_path(str(ROOT / 'scripts' / 'seed_neo4j_knowledge_graph.py'), run_name='__main__')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'command',
        choices=('init', 'upgrade', 'migration-smoke', 'seed-demo', 'knowledge-check', 'seed-neo4j-graph'),
    )
    args = parser.parse_args()
    {
        'init': init_database,
        'upgrade': upgrade_database,
        'migration-smoke': migration_smoke,
        'seed-demo': seed_demo,
        'knowledge-check': knowledge_check,
        'seed-neo4j-graph': seed_neo4j_graph,
    }[args.command]()


if __name__ == '__main__':
    main()
