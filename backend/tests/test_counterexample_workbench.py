"""Teacher navigation preserves ownership, immutable versions and review evidence."""
from unittest.mock import patch
from test_learner_state import app
from test_counterexample_gates import make_challenge, call, auth, uid, proposed
from test_counterexample_attempts import publish, body_for, submit, fake_run
from app.models import db, User, Class


def get(app, path, kind='teacher'):
    return app.test_client().get('/api/v1/'+path, headers=auth(app,kind))


def test_teacher_list_spec_and_version_history(app):
    row=make_challenge(app)
    path='teacher/counterexample-challenges'
    listed=get(app,path+'?class_id='+str(row['class_id'])).json['data']
    assert listed['total']==1 and listed['items'][0]['id']==row['id']
    assert 'candidate' not in listed['items'][0] and listed['items'][0]['validation_status'] is None
    assert get(app,path+'?class_id='+str(row['class_id'])+'&page=2').json['data']['items']==[]
    spec=get(app,'teacher/counterexample-specifications/'+row['spec_id']).json['data']
    assert spec['specification']==row['specification']
    revised=call(app,path+'/'+row['id']+'/versions',{'request_id':uid(),'expected_revision':1,
        'spec_id':row['spec_id'],'candidate':{**proposed(),'explanation':'修订解释'}})
    assert revised.status_code==200
    history=get(app,path+'/'+row['id']+'/versions').json['data']
    assert [item['revision'] for item in history['items']]==[2,1]
    old=get(app,path+'/'+row['id']+'/versions/1').json['data']
    assert old['revision']==1 and old['current_revision']==2 and old['candidate']['explanation']!='修订解释'
    assert get(app,path+'/'+row['id']+'/versions/3').status_code==400


def test_workbench_permissions_and_query_validation(app):
    row=make_challenge(app)
    paths=['teacher/counterexample-challenges?class_id='+str(row['class_id']),
        'teacher/counterexample-specifications/'+row['spec_id'],
        'teacher/counterexample-challenges/'+row['id']+'/versions',
        'teacher/counterexample-challenges/'+row['id']+'/versions/1',
        'teacher/counterexample-challenges/'+row['id']+'/attempts']
    for path in paths:
        assert get(app,path,'student').status_code==403
        assert app.test_client().get('/api/v1/'+path).status_code==401
    for query in ('','?class_id=nope','?class_id=0','?class_id=1&page=0','?class_id=1&page=1.5','?class_id=1&page=100001'):
        assert get(app,'teacher/counterexample-challenges'+query).status_code==400
    with app.app_context():
        other=User.query.filter(User.id.notin_([app.config['TEST_STUDENT'],app.config['TEST_TEACHER']])).first()
        db.session.get(Class,row['class_id']).teacher_id=other.id;db.session.commit()
    for path in paths: assert get(app,path).status_code==404
    assert get(app,paths[0],'admin').status_code==200


def test_attempt_list_frozen_context_and_explanation_history(app):
    row=publish(app);body=body_for(row)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run):
        assert submit(app,row,body).status_code==200
    path='teacher/counterexample-challenges/'+row['id']+'/attempts'
    listed=get(app,path).json['data']
    assert listed['total']==1 and listed['items'][0]['explanation_status']=='needs_teacher'
    attempt_path='teacher/counterexample-attempts/'+body['request_id']
    for revision in (0,1):
        reviewed=call(app,attempt_path+'/review',{'request_id':uid(),'expected_revision':revision,
            'verdict':'supported' if revision else 'needs_revision','note':'核对说明 '+str(revision)})
        assert reviewed.status_code==200,reviewed.json
    detail=get(app,attempt_path).json['data']
    assert [item['revision'] for item in detail['review_history']]==[2,1]
    assert detail['task_snapshot']['buggy_code']==row['candidate']['buggy_code']
    assert detail['task_snapshot']['statement']==row['specification']['statement']
    call(app,'teacher/counterexample-challenges/'+row['id']+'/versions',{'request_id':uid(),'expected_revision':1,
        'spec_id':row['spec_id'],'candidate':{**proposed(),'buggy_code':'def solve(data):\n    return 0'}})
    assert get(app,attempt_path).json['data']['task_snapshot']==detail['task_snapshot']
    assert get(app,path).json['data']['items'][0]['revision']==1
    student=get(app,'student/counterexample-attempts/'+body['request_id'],'student')
    assert student.status_code==404  # New draft withdrew the task; old private material stays teacher-only.
    with app.app_context():
        db.session.get(User,app.config['TEST_STUDENT']).status='deleted';db.session.commit()
    assert get(app,path).json['data']['items']==[] and get(app,attempt_path).status_code==404
    with app.app_context():
        student=db.session.get(User,app.config['TEST_STUDENT']);student.status='active';student.class_id=None;db.session.commit()
    assert get(app,path).json['data']['items']==[] and get(app,attempt_path).status_code==404
