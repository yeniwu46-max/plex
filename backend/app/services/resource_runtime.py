"""Durable resource request budgets and ownership of an executing task."""
from datetime import timedelta
from flask import current_app
from sqlalchemy import select,func,update,or_
from sqlalchemy.orm import Session
from app.models import db,ResourceGenerationTask as Task,User,Class
from app.services.tutor_context import TutorContextError
from app.utils.time import utc_now

STALE_SECONDS=600


def limits():
    defaults={'USER_DAILY':10,'CLASS_DAILY':60,'USER_ACTIVE':2,'CLASS_ACTIVE':6,'GLOBAL_ACTIVE':12,'ATTEMPTS':3}
    return {key.lower():max(1,int(current_app.config.get('RESOURCE_'+key+'_LIMIT',value))) for key,value in defaults.items()}


def day_start():return utc_now().replace(hour=0,minute=0,second=0,microsecond=0)


def check_capacity(user_id,class_id):
    """Called while the resource admission lock is held, before creating a row."""
    cap=limits()
    daily=select(func.count()).select_from(Task).where(Task.created_at>=day_start())
    active=select(func.count()).select_from(Task).where(Task.status.in_(['pending','running']))
    checks=[(daily.where(Task.user_id==user_id),'user_daily','本周期资源生成额度已用完'),
            (active.where(Task.user_id==user_id),'user_active','已有资源任务正在排队或生成'),
            (active,'global_active','资源生成队列暂时已满')]
    if class_id is not None:
        checks.extend([(daily.where(Task.class_id==class_id),'class_daily','本班本周期资源生成额度已用完'),
                       (active.where(Task.class_id==class_id),'class_active','本班资源任务已达并行上限')])
    for query,key,message in checks:
        if db.session.scalar(query)>=cap[key]:raise TutorContextError(message+'，请稍后再试',429)


def retry_remaining(row):
    root=row.retry_root_id or row.task_id
    used=Task.query.filter(or_(Task.retry_root_id==root,Task.task_id==root)).count()
    return max(0,limits()['attempts']-used)


def ensure_running(task_id):
    """Lock the still-live task before publishing any step/resources."""
    with db.session.no_autoflush:
        changed=db.session.execute(update(Task).where(Task.task_id==task_id,Task.status=='running',
            Task.updated_at>=utc_now()-timedelta(seconds=STALE_SECONDS)).values(updated_at=utc_now())
            .execution_options(synchronize_session=False)).rowcount
    if not changed:raise TutorContextError('资源任务已过期或结束，请从任务历史恢复',409)


def usage(user_id,*,class_id=None):
    cap=limits();start=day_start()
    with Session(db.engine) as session:
        actor=session.get(User,user_id)
        if not actor or actor.status!='active':raise TutorContextError('账号不可用',403)
        if class_id is not None:
            cohort=session.get(Class,class_id)
            if not cohort or actor.role.name not in {'teacher','admin'} or (actor.role.name!='admin' and cohort.teacher_id!=user_id):
                raise TutorContextError('班级不存在或不可管理',404)
        where=Task.class_id==class_id if class_id is not None else Task.user_id==user_id
        used=session.scalar(select(func.count()).select_from(Task).where(where,Task.created_at>=start))
        active=session.scalar(select(func.count()).select_from(Task).where(where,Task.status.in_(['pending','running'])))
        kind='class' if class_id is not None else 'user'
        return {'scope':'resource','audience':'class' if class_id is not None else 'self','class_id':class_id,
            'request_limit':cap[kind+'_daily'],'requests_used':used,'requests_remaining':max(0,cap[kind+'_daily']-used),
            'active_tasks':active,'active_limit':cap[kind+'_active'],'attempt_limit':cap['attempts'],
            'period_start':start.isoformat()+'Z','reset_at':(start+timedelta(days=1)).isoformat()+'Z'}
