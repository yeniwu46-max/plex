"""Teacher-declared history inputs for isolated state-availability comparisons.

No production export, no automatic labels, no code execution. Provenance and
permission are declarations; this offline tool cannot authenticate them.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from scripts.teacher_baseline_contract import (ContractError, read_json, verify_frozen,
    _require as require, _id, _sha, _text)
from scripts.prepare_teacher_baseline import digest

PROTOCOL = 'teacher-state-availability-v1'
ARMS = ('tutor_state_masked', 'tutor_state_visible')
PROVENANCE = {'synthetic_scenarios', 'declared_deidentified_observations'}
KINDS = {'grade', 'hint', 'review_schedule'}
ROW_FIELDS = {'case_id','case_sha256','history_id','observations','accepted',
              'reviewer_id','reviewed_at','rationale','expected_adjustment'}
EVENT_FIELDS = {'id','kind','concept_id','at','correct','assisted','mode','due_at','source_sha256'}
MODES = {'explain_error','review_approach','next_step','pseudocode'}


def timestamp(value):
    try:
        require(isinstance(value, str), 'History time must be an ISO string')
        parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
        require(parsed.tzinfo is not None, 'History time must include timezone')
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ContractError('Invalid history time') from None


def accepted_cases(baseline):
    report = verify_frozen(baseline)
    allowed = set(report['accepted_case_ids'])
    return {c['id']:c for c in baseline['case_pack']['cases'] if c['id'] in allowed}


def template(baseline):
    cases = accepted_cases(baseline)
    return {'schema_version':1, 'status':'pending_history_review',
        'baseline_sha256':baseline['artifact_sha256'], 'provenance':'synthetic_scenarios',
        'permission_reference':None, 'as_of':datetime.now(timezone.utc).isoformat(), 'reviewers':[],
        'histories':[{'case_id':c['id'],'case_sha256':digest(c),'history_id':c['family_id'],
            'observations':[], 'accepted':None, 'reviewer_id':None,'reviewed_at':None,
            'rationale':None,'expected_adjustment':None} for c in cases.values()]}


def validate(baseline, pack):
    from app.data.knowledge_node_registry import resolve_node_id
    cases = accepted_cases(baseline)
    require(isinstance(pack,dict) and set(pack)=={'schema_version','status','baseline_sha256',
        'provenance','permission_reference','as_of','reviewers','histories'}, 'Invalid history package fields')
    require(type(pack['schema_version']) is int and pack['schema_version']==1
        and pack['status']=='pending_history_review', 'Unsupported history schema')
    require(pack['baseline_sha256']==baseline['artifact_sha256'], 'History belongs to a different frozen baseline')
    require(isinstance(pack['provenance'],str) and pack['provenance'] in PROVENANCE, 'History provenance must be explicit')
    as_of = timestamp(pack['as_of'])
    require(as_of <= datetime.now(timezone.utc), 'History as_of cannot be in the future')
    permission = pack['permission_reference']
    require(permission is None or _text(permission,300), 'Invalid permission reference')
    people = set()
    require(isinstance(pack['reviewers'],list), 'History reviewers must be an array')
    for person in pack['reviewers']:
        require(isinstance(person,dict) and set(person)=={'id','declares_python_teaching_experience',
            'declares_personal_review','declares_data_use_permission'}, 'Invalid history reviewer fields')
        require(_id(person['id']) and person['id'] not in people, 'Invalid or duplicate history reviewer')
        require(all(person[k] is True for k in ('declares_python_teaching_experience',
            'declares_personal_review','declares_data_use_permission')), 'Explicit history review and permission declarations required')
        people.add(person['id'])
    rows = pack['histories']
    require(isinstance(rows,list) and len(rows)==len(cases), 'Every accepted baseline case needs a history decision')
    seen, accepted, rejected, pending = set(), [], [], []
    groups, sources = {}, {}
    for row in rows:
        require(isinstance(row,dict) and set(row)==ROW_FIELDS, 'Invalid history row fields')
        cid = row['case_id']
        require(_id(cid) and cid in cases and cid not in seen, 'Unknown or duplicate history case')
        seen.add(cid); case = cases[cid]
        require(row['case_sha256']==digest(case), 'Case changed after history review')
        require(_id(row['history_id']), 'Invalid history grouping id')
        require(row['accepted'] is None or type(row['accepted']) is bool, 'History acceptance must be a boolean or null')
        observations = row['observations']
        require(isinstance(observations,list) and len(observations)<=40, 'History supports at most 40 observations per case')
        event_ids, event_sources = set(), set(); previous = None
        for event in observations:
            require(isinstance(event,dict) and set(event)==EVENT_FIELDS, 'Invalid observation fields')
            require(_id(event['id']) and event['id'] not in event_ids, 'Invalid or duplicate observation id')
            event_ids.add(event['id'])
            require(isinstance(event['kind'],str) and event['kind'] in KINDS, 'Unsupported history event kind')
            require(_id(event['concept_id']) and resolve_node_id(event['concept_id'])==event['concept_id'], 'Canonical course concept required')
            at = timestamp(event['at'])
            require(as_of-timedelta(days=365) <= at <= as_of and (previous is None or previous<=at),
                'History must be chronological and precede the query within 365 days')
            previous = at
            if event['kind']=='grade':
                require(type(event['correct']) is bool and type(event['assisted']) is bool
                    and event['mode'] is None and event['due_at'] is None, 'Invalid grade observation')
            elif event['kind']=='hint':
                require(event['correct'] is None and event['assisted'] is None
                    and isinstance(event['mode'],str) and event['mode'] in MODES
                    and event['due_at'] is None, 'Invalid hint observation')
            else:
                require(event['correct'] is None and event['assisted'] is None and event['mode'] is None,
                    'Review self-report cannot invent a grade')
                require(at <= timestamp(event['due_at']) <= as_of+timedelta(days=365), 'Invalid review due time')
            source = event['source_sha256']
            require(source is None or _sha(source), 'Invalid observation source digest')
            if pack['provenance']=='declared_deidentified_observations':
                require(_sha(source), 'Declared real observations need source evidence digests')
            if source:
                require(source not in event_sources, 'Same source cannot count as multiple observations in one history')
                event_sources.add(source)
                source_signature=(case['split'],digest({k:v for k,v in event.items() if k!='id'}))
                require(source not in sources or sources[source]==source_signature,
                    'Observation source crosses evaluation splits or changes facts')
                sources[source]=source_signature
        group = row['history_id']
        signature = (case['split'],digest(observations))
        require(group not in groups or groups[group]==signature, 'History grouping crosses splits or changes observations')
        groups[group]=signature
        if row['reviewer_id'] is not None:
            require(isinstance(row['reviewer_id'],str) and row['reviewer_id'] in people, 'Undeclared history reviewer')
        if row['reviewed_at'] is not None:
            require(as_of <= timestamp(row['reviewed_at']) <= datetime.now(timezone.utc), 'Invalid history review time')
        for key in ('rationale','expected_adjustment'):
            require(row[key] is None or _text(row[key],2000), 'Invalid history review text')
        if row['accepted'] is None:
            pending.append(cid); continue
        require(all(row[key] is not None for key in ('reviewer_id','reviewed_at','rationale')), 'History decision missing human review')
        if row['accepted']:
            require(observations and _text(row['expected_adjustment'],2000), 'Accepted history needs observations and expected teaching adjustment')
            accepted.append(cid)
        else:
            rejected.append(cid)
    coverage = {split:sum(cases[cid]['split']==split for cid in accepted) for split in ('development','test')}
    permission_ready = bool(permission) if pack['provenance']=='declared_deidentified_observations' else True
    return {'ready_to_freeze':not pending and all(coverage.values()) and permission_ready,
        'accepted_case_ids':accepted,'pending_case_ids':pending,'reviewed':len(accepted)+len(rejected),
        'accepted':len(accepted),'rejected':len(rejected),'pending':len(pending),'coverage':coverage,
        'permission_declared':permission_ready,'identity_and_origin_authenticated':False,
        'provenance':pack['provenance'],'package_sha256':digest(pack)}


def write_new(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as out:
        json.dump(value,out,ensure_ascii=False,indent=2,allow_nan=False);out.write('\n')


def freeze(baseline, pack, path):
    report=validate(baseline,pack)
    require(report['ready_to_freeze'], 'History review is incomplete, lacks permission or has no accepted cases in a split')
    value={'schema_version':1,'protocol':PROTOCOL,'status':'frozen_teacher_declared_history',
        'frozen_at':datetime.now(timezone.utc).isoformat(),'package':pack,'validation':report}
    value['artifact_sha256']=digest(value)
    write_new(path,value)
    return value


def verify(baseline, artifact):
    require(isinstance(artifact,dict) and set(artifact)=={'schema_version','protocol','status','frozen_at',
        'package','validation','artifact_sha256'}, 'Invalid frozen history fields')
    require(type(artifact['schema_version']) is int and artifact['schema_version']==1 and artifact['protocol']==PROTOCOL
        and artifact['status']=='frozen_teacher_declared_history','Not a frozen history artifact')
    require(_sha(artifact['artifact_sha256']) and digest({k:v for k,v in artifact.items() if k!='artifact_sha256'})==artifact['artifact_sha256'],
        'Frozen history has changed')
    report=validate(baseline,artifact['package'])
    require(report['ready_to_freeze'] and report==artifact['validation'],'Frozen history no longer validates')
    require(timestamp(artifact['package']['as_of']) <= timestamp(artifact['frozen_at']) <= datetime.now(timezone.utc), 'Invalid history freeze time')
    require(all(timestamp(row['reviewed_at']) <= timestamp(artifact['frozen_at']) for row in artifact['package']['histories']),
        'History freeze precedes a review decision')
    return {r['case_id']:r for r in artifact['package']['histories'] if r['accepted']}


@contextmanager
def decision_clock(as_of):
    moment=timestamp(as_of).replace(tzinfo=None)
    with patch('app.services.learner_decision.utc_now',return_value=moment):
        yield


def replay(user_id, row, as_of):
    """Replay declarations only in the runner's new disposable database.

    These are hypothetical/declared past observations, never new actual grades.
    The strict package has already been verified by the runner.
    """
    from flask import current_app
    from app.models import db, User
    from app.services.learner_state import LearnerStateService as State
    require(current_app.name=='plex-frozen-evaluation' and current_app.config.get('EVALUATION_HISTORY_REPLAY') is True
        and db.engine.url.get_backend_name()=='sqlite' and Path(db.engine.url.database).name=='evaluation.sqlite',
        'History replay requires the isolated evaluation database')
    user=db.session.get(User,user_id)
    require(user and user.username.startswith('eval-'), 'History replay requires an evaluation account')
    require(State.snapshot(user_id)['state_version']==0, 'History requires a fresh evaluation account')
    kinds={'grade':('submission_graded','trial_question_progress','server_graded'),
        'hint':('hint_displayed','tutor_response','display_acknowledgement'),
        'review_schedule':('review_recorded','mistake_review','self_report')}
    for event in row['observations']:
        kind,source,scope=kinds[event['kind']]
        payload={'concept_id':event['concept_id'],'evidence_scope':scope,
                 'evaluation_replay':True, 'not_a_new_actual_observation':True}
        if event['kind']=='grade': payload.update(correct=event['correct'],assisted=event['assisted'])
        elif event['kind']=='hint': payload.update(mode=event['mode'])
        else: payload.update(due_at=event['due_at'])
        State.append(user_id=user_id,kind=kind,source_type=source,source_id='evaluation/'+event['id'],
            source_version='1',payload=payload,occurred_at=timestamp(event['at']).replace(tzinfo=None))
    db.session.commit()
    State.drain(limit=41)
    with patch('app.services.learner_state.utc_now',return_value=timestamp(as_of).replace(tzinfo=None)):
        snapshot=State.snapshot(user_id)
    require(snapshot['state_version']==len(row['observations']) and not snapshot['pending_events'] and not snapshot['failed_events'],
        'History projection failed or lost observations')
    return snapshot


def visible_history(row, pack):
    # Both blind-review arms receive the same context. Expected adjustment and
    # reviewer rationale are not given to the model or used as automatic scores.
    return {'provenance':pack['provenance'],'as_of':pack['as_of'],
        'observations':[{k:v for k,v in e.items() if k not in ('id','source_sha256')} for e in row['observations']]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--prepare',type=Path)
    choice.add_argument('--history',type=Path)
    parser.add_argument('--freeze',type=Path)
    args=parser.parse_args()
    try:
        baseline=read_json(args.baseline)
        if args.prepare:
            require(args.freeze is None,'Prepare and freeze are separate steps')
            pack=template(baseline);write_new(args.prepare,pack)
            report={'status':'pending_history_review','cases':len(pack['histories']),'reviewed':0}
        else:
            pack=read_json(args.history);report=validate(baseline,pack)
            if args.freeze: freeze(baseline,pack,args.freeze)
        print(json.dumps({k:v for k,v in report.items() if not k.endswith('_case_ids')},ensure_ascii=False))
        return 0 if args.prepare or report['ready_to_freeze'] else 2
    except (ContractError,ValueError,OSError,TypeError,KeyError) as exc:
        print(json.dumps({'status':'invalid_input','error_type':type(exc).__name__,
            'detail':str(exc) if isinstance(exc,ContractError) else None}))
        return 1


if __name__=='__main__':
    sys.exit(main())
