"""Account actual text-model HTTP attempts without copying sensitive contents."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta
import hashlib
import json
import time
import uuid
from urllib.parse import urlparse
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from app.models import db
from app.models.ai_runtime import AiModelCall as Call
from app.services.model_observation import observe_model
from app.utils.time import utc_now
from app.services import model_pricing

_SCOPE = ContextVar('plex_model_account_scope', default=None)
WORKFLOWS = {'tutor','resource','rag','counterexample'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def begin(**metadata):
    if metadata['workflow'] not in WORKFLOWS or type(metadata['user_id']) is not int:
        raise ValueError('Invalid trusted accounting scope')
    from app.services.knowledge.settings import retrieval_config
    return _SCOPE.set({'state_version':0,'class_id':None,'stage':'generation',
        'retrieval_config_hash':digest(retrieval_config()),**metadata,'calls':[]})


def end(token):
    _SCOPE.reset(token)


@contextmanager
def scope(**metadata):
    token=begin(**metadata)
    try:yield _SCOPE.get()
    finally:end(token)


def update_scope(**metadata):
    current=_SCOPE.get()
    if current:
        allowed={key:value for key,value in metadata.items() if key in {'stage','state_version','class_id'}}
        # Teachers have no learner-state snapshot. Zero denotes no version,
        # never a measured zero mastery; the ledger's version column is not nullable.
        if 'state_version' in allowed and allowed['state_version'] is None:allowed['state_version']=0
        _SCOPE.set({**current,**allowed})


def provider_label(endpoint):
    host=(urlparse(endpoint).hostname or '').lower()
    if host=='api.deepseek.com' or host.endswith('.deepseek.com'):return 'deepseek'
    if host=='openrouter.ai' or host.endswith('.openrouter.ai'):return 'openrouter'
    if any(host == domain or host.endswith('.'+domain) for domain in ('xf-yun.com','xfyun.cn')):return 'spark'
    if host=='api.openai.com' or host.endswith('.openai.com'):return 'openai'
    return 'openai-compatible'


class Record:
    def __init__(self,metadata,*,provider=None,model=None,prompt_hash=None,billing_context=None):
        self.rate_card = model_pricing.load_card()
        self.billing_context = billing_context
        self.started_at = utc_now()
        self.engine=db.engine;self.id=str(uuid.uuid4());self.started=time.perf_counter();self.closed=False
        with Session(self.engine) as session:
            session.add(Call(id=self.id,provider=provider,model=model,prompt_hash=prompt_hash,started_at=self.started_at,
                **{key:metadata[key] for key in ('workflow','request_id','attempt_id','user_id','stage','policy_version','state_version','retrieval_config_hash','class_id')}))
            session.commit()
        metadata['calls'].append(self.id)

    def finish(self,*,status,usage=None,error=None,model=None,service_tier=None):
        if self.closed:return
        # Mark closed only after persistence: a storage error must not appear accounted.
        with Session(self.engine) as session:
            row=session.get(Call,self.id);row.status=status;row.error_code=error
            if isinstance(model,str) and model:row.model=model[:128]
            usage=usage if isinstance(usage,dict) else {}
            for key in ('prompt_tokens','completion_tokens','total_tokens'):
                value=usage.get(key)
                setattr(row,key,value if type(value) is int and 0<=value<=2147483647 else None)
            price = model_pricing.estimate(self.rate_card, provider=row.provider,
                model=model if isinstance(model, str) else None, started_at=self.started_at, status=status,
                usage=usage, context=self.billing_context, response_tier=service_tier)
            for key, value in price.items(): setattr(row, key, value)
            row.elapsed_ms=round((time.perf_counter()-self.started)*1000);row.finished_at=utc_now()
            session.commit()
        self.closed=True


def operation(metadata,function):
    # Non-HTTP providers can report metadata explicitly; unsupported adapters are
    # unreported, not silently free. HTTP attempts already have their own records.
    with scope(**metadata) as current:
        observed={};started=time.perf_counter()
        try:
            with observe_model() as observed:return function()
        finally:
            if not current['calls']:
                record=Record(current,provider=observed.get('provider'),model=observed.get('model'))
                record.started=started
                record.finish(status=observed.get('status','unreported'),usage=observed.get('token_usage'),error=observed.get('error_code'))


class StreamResponse:
    def __init__(self,response,record):
        self.response=response;self.record=record;self.usage=None;self.model=None;self.done=False;self.error=None;self.service_tier=None
    def __getattr__(self,name):return getattr(self.response,name)
    def iter_lines(self,*args,**kwargs):
        try:
            for raw in self.response.iter_lines(*args,**kwargs):
                line=raw.decode('utf-8',errors='replace') if isinstance(raw,bytes) else raw
                if isinstance(line,str) and line.strip().startswith('data:'):
                    data=line.strip()[5:].strip()
                    if data=='[DONE]':self.done=True
                    else:
                        try:
                            payload=json.loads(data)
                            if isinstance(payload,dict):
                                if isinstance(payload.get('usage'),dict):self.usage=payload['usage']
                                if isinstance(payload.get('model'),str):self.model=payload['model']
                                if isinstance(payload.get('service_tier'),str):self.service_tier=payload['service_tier']
                                if payload.get('error'):self.error='stream_provider_error'
                        except (ValueError,TypeError):pass
                yield raw
        except Exception:
            self.error='stream_transport_error';raise
        finally:self.close()
    def close(self):
        try:self.response.close()
        finally:self.record.finish(status='failed' if self.error else 'succeeded' if self.done else 'interrupted',usage=self.usage,
            error=self.error or (None if self.done else 'stream_not_completed'),model=self.model,service_tier=self.service_tier)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def request(method,url,args,kwargs,send):
    current=_SCOPE.get();body=kwargs.get('json')
    if not current or method!='post' or not isinstance(body,dict) or not isinstance(body.get('messages'),list) or not isinstance(body.get('model'),str):
        return send()
    messages=body['messages'];system=[m.get('content') for m in messages if isinstance(m,dict) and m.get('role')=='system']
    record=Record(current,provider=provider_label(url),model=body['model'][:128],prompt_hash=digest(system),billing_context=model_pricing.billing_context(url,body))
    try:response=send()
    except Exception as exc:
        import requests
        error='connect_timeout' if isinstance(exc,requests.ConnectTimeout) else 'read_timeout' if isinstance(exc,requests.ReadTimeout) else 'connection_error' if isinstance(exc,requests.ConnectionError) else 'transport_error'
        record.finish(status='failed',error=error);raise
    if kwargs.get('stream') and response.status_code<400:return StreamResponse(response,record)
    try:data=response.json()
    except Exception:data={}
    if not isinstance(data,dict):data={}
    error=f'http_{response.status_code}' if response.status_code>=400 else 'invalid_response' if not data.get('choices') or not isinstance(data.get('choices'),list) else None
    record.finish(status='failed' if error else 'succeeded',usage=data.get('usage'),error=error,model=data.get('model'),service_tier=data.get('service_tier'))
    return response


def summary(user_id,*,class_id=None):
    start=utc_now().replace(hour=0,minute=0,second=0,microsecond=0)
    with Session(db.engine) as session:
        query=select(Call.workflow,func.count(),func.coalesce(func.sum(Call.total_tokens),0),
            func.sum(case((Call.total_tokens.is_(None),1),else_=0)),
            func.sum(case((Call.status=='failed',1),else_=0)),
            func.sum(case((Call.status.in_(['processing','interrupted']),1),else_=0))).where(Call.started_at>=start)
        query=query.where(Call.class_id==class_id) if class_id is not None else query.where(Call.user_id==user_id)
        cost = model_pricing.summary(session, Call.started_at >= start, Call.class_id == class_id if class_id is not None else Call.user_id == user_id)
        names=('calls','reported_total_tokens','unknown_usage_calls','failed_calls','unfinished_calls')
        groups={key:dict.fromkeys(names,0) for key in sorted(WORKFLOWS)}
        for workflow,*values in session.execute(query.group_by(Call.workflow)):
            groups[workflow]=dict(zip(names,map(int,values)))
        return {'scope':'connected_text_models','period_start':start.isoformat()+'Z','reset_at':(start+timedelta(days=1)).isoformat()+'Z',
            'audience':'class' if class_id is not None else 'self','class_id':class_id,
            'totals':{key:sum(group[key] for group in groups.values()) for key in names},'workflows':groups,
            'excluded':['embedding','speech','image','video','unconnected_legacy_calls'],'cost':None,'cost_status':'estimate_available' if cost['estimated_calls'] else 'not_priced','cost_estimate':cost}
