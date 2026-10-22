"""One frozen, read-only learning context for a resource pipeline and its retries."""
from copy import deepcopy
import hashlib
import json

from flask import current_app
from sqlalchemy.orm import Session
from app.models import User, StudentProfile, db
from app.services.student_profile import PROFILE_DIMENSIONS
from app.services.learner_state import LearnerStateService
from app.services.learner_decision import LearnerDecisionService
from app.utils.time import utc_now

POLICY = 'resource-learning-context-v1'


class ResourceLearningContext:
    @staticmethod
    def capture(user_id, knowledge_key, *, origin='task_created'):
        mode = current_app.config.get('LEARNER_STATE_READ_MODE', 'shadow')
        if mode not in {'shadow', 'evidence'}:
            raise ValueError('学习状态读取配置无效')
        with Session(db.engine) as session:
            if session.get_bind().dialect.name == 'sqlite':
                session.connection().exec_driver_sql('BEGIN')
            elif session.get_bind().dialect.name == 'mysql':
                session.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            actor = session.get(User, user_id)
            if not actor or actor.status != 'active' or not actor.role or actor.role.name != 'student':
                raise ValueError('账号当前不可生成学习资源')
            row = session.query(StudentProfile).filter_by(user_id=user_id).first()
            profile = {}
            for key, item in (row.dimensions or {}).items() if row else ():
                if (key in PROFILE_DIMENSIONS and isinstance(item, dict) and item.get('value')
                        and not (mode == 'evidence' and item.get('source') == 'behavior')):
                    profile[key] = str(item['value'])[:500]
            state = LearnerStateService.snapshot(user_id, session=session) if mode == 'evidence' else None
            return {'policy_version': POLICY, 'user_id': user_id, 'class_id': actor.class_id,
                'knowledge_key': knowledge_key, 'captured_at': utc_now().isoformat()+'Z', 'origin': origin,
                'profile_version': row.version if row else 0, 'profile': profile,
                'state_source': mode, 'learner_state': state,
                'learning_decision': LearnerDecisionService.from_snapshot(state, focus_concept=knowledge_key) if state else None}

    @staticmethod
    def bind(snapshot, pedagogical_context, requested_types, require_real_api):
        result = deepcopy(snapshot)
        result.update(pedagogical_context=deepcopy(pedagogical_context),
            requested_types=sorted(requested_types), require_real_api=bool(require_real_api))
        return result

    @staticmethod
    def digest(snapshot):
        # Capture time is metadata; an unchanged state/request can still reuse a recent task.
        body = {key:value for key,value in snapshot.items() if key != 'captured_at'}
        return hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,allow_nan=False,
            separators=(',', ':')).encode('utf-8')).hexdigest()

    @staticmethod
    def read(row):
        snapshot = row.context_snapshot
        if not isinstance(snapshot, dict) or snapshot.get('policy_version') != POLICY:
            raise ValueError('生成依据缺失或版本不受支持，请重新创建任务')
        if (ResourceLearningContext.digest(snapshot) != row.context_hash
                or snapshot.get('user_id') != row.user_id or snapshot.get('knowledge_key') != row.knowledge_key
                or snapshot.get('requested_types') != sorted(row.requested_types)
                or snapshot.get('profile_version') != row.profile_version):
            raise ValueError('生成依据与任务不一致，请重新创建任务')
        return deepcopy(snapshot)

    @staticmethod
    def authorize(snapshot):
        # Long-running calls must not use an ORM identity cached before an account/class change.
        with Session(db.engine) as session:
            actor = session.get(User, snapshot['user_id'])
            if (not actor or actor.status != 'active' or not actor.role or actor.role.name != 'student'
                    or actor.class_id != snapshot['class_id']):
                raise ValueError('账号或班级已变化，请重新创建生成任务')

    @staticmethod
    def guidance(snapshot):
        """Teaching actions and estimates only; raw histories/profile evidence stay server-side."""
        state = snapshot.get('learner_state') or {}
        decision = snapshot.get('learning_decision') or {}
        return {'policy_version': snapshot['policy_version'], 'state_source': snapshot['state_source'],
            'state_version': state.get('state_version'), 'profile_version': snapshot['profile_version'],
            'basis': decision.get('basis', 'profile_only'),
            'reason': decision.get('reason', '本次依据资料自述与偏好安排讲解，未使用证据状态判断掌握程度。'),
            'hint_action': (decision.get('hint') or {}).get('action'),
            'exercise_action': (decision.get('next_exercise') or {}).get('action'),
            'review_action': (decision.get('review') or {}).get('action'),
            'evidence_count': len(decision.get('evidence_ids') or []),
            'estimate_disclaimer': state.get('estimate_disclaimer', '自述不等于已验证的能力或测验成绩。')}

    @staticmethod
    def public_summary(snapshot, context_hash):
        if not isinstance(snapshot, dict) or snapshot.get('policy_version') != POLICY:
            return None  # Historical completed tasks did not capture this evidence.
        if ResourceLearningContext.digest(snapshot) != context_hash:
            return None
        return {**ResourceLearningContext.guidance(snapshot), 'context_hash': context_hash,
            'captured_at': snapshot['captured_at'], 'origin': snapshot['origin']}
