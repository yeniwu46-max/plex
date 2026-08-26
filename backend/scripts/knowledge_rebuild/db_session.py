# -*- coding: utf-8 -*-
"""给批处理脚本用的轻量数据库会话。

**不要在这些脚本里用 `app.create_app()`**：它除了配置数据库，还会跑建表、种子
数据、权限同步、示例账号引导，并且通过 `PersonalizedResourceService.recover_stale_tasks`
把待处理任务提交到一个线程池。那些线程是非守护线程，会在脚本主逻辑结束（或抛异常）
后继续把进程吊着，同时连接池里的连接仍持有未提交事务——结果就是下一次运行必然撞上
`Lock wait timeout exceeded`。批处理脚本只需要"模型 + 一个会话"，用这里的最小应用即可。
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from flask import Flask  # noqa: E402

from app.config import Config  # noqa: E402


def make_app() -> Flask:
    """只做数据库绑定的最小 Flask 应用，不建表、不种子、不起后台线程。"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False

    from app.models import db

    db.init_app(app)
    return app


@contextlib.contextmanager
def session_scope():
    """进入应用上下文并交出 db.session；异常回滚，正常提交，退出时确保连接释放。"""
    app = make_app()
    from app.models import db

    with app.app_context():
        try:
            yield db.session
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        finally:
            db.session.remove()
            db.engine.dispose()


@contextlib.contextmanager
def readonly_scope():
    """只读场景：结束时回滚，绝不留下未提交事务。"""
    app = make_app()
    from app.models import db

    with app.app_context():
        try:
            yield db.session
        finally:
            db.session.rollback()
            db.session.remove()
            db.engine.dispose()
