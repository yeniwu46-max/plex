"""Explicit learning artifacts reuse reviewed tutoring and its authorized history."""
import re
import uuid

from app.services.course_safety import CourseSafetyService
from app.services.tutor_context import TutorContextError, _text
from app.services.tutor_policy import ARTIFACT_MODES
from app.services.tutor_sessions import TutorSessions
from app.services.tutoring import TutorService

FIELDS = {'topic', 'message', 'request_id', 'session_id', 'question_ref', 'formal_question_id',
          'question_version', 'code', 'run_id'}


def plain(value):
    # Model text is plain content. Only this renderer creates Markdown structure/links.
    text = str(value or '').replace('\\', '\\\\')
    return re.sub(r'([`*_[\]{}<>!#|.:@])', r'\\\1', text)


def diagram(response):
    lines = ['graph TD']
    for node in response.get('nodes', []):
        label = re.sub(r'[^\w\u4e00-\u9fff .，、：-]', ' ', node['label']).strip() or '概念'
        lines.append(f'  {node["id"]}["{label}"]')
    lines.extend(f'  {edge["from"]} --> {edge["to"]}' for edge in response.get('edges', []))
    return '\n'.join(lines)


class MessengerArtifactService:
    @staticmethod
    def generate(user_id, body, kind):
        if isinstance(body, str):  # Legacy service call, same reviewed policy.
            body = {'topic': body}
        if not isinstance(body, dict) or set(body) - FIELDS:
            raise TutorContextError('学习工具请求字段不符合约定')
        if 'topic' in body and 'message' in body and body['topic'] != body['message']:
            raise TutorContextError('主题字段不一致')
        topic = _text(body.get('topic', body.get('message')), '主题', 500).strip()
        if len(topic) < 2:
            raise TutorContextError('请描述一个具体的编程学习主题')
        CourseSafetyService.ensure_safe(topic, enforce_course_scope=True)
        if kind not in ARTIFACT_MODES:
            raise TutorContextError('学习工具不存在', 404)
        payload = {k:v for k,v in body.items() if k not in {'topic', 'message'}}
        payload.update(question=topic, mode=kind, hint_level=2)
        payload.setdefault('request_id', str(uuid.uuid4()))
        response = TutorService.ask(user_id, payload, automatic=True, require_evidence=True)
        return MessengerArtifactService.view(response)

    @staticmethod
    def read(user_id, request_id):
        response = TutorSessions.read_turn(user_id, request_id)
        if response['mode'] not in ARTIFACT_MODES:
            raise TutorContextError('学习工具记录不存在', 404)
        return MessengerArtifactService.view(response)

    @staticmethod
    def view(response):
        successful = response['status'] == 'ok'
        kind = 'document' if response['mode'] == 'learning_document' else 'graph'
        title = response.get('title') if successful else '学习材料暂未生成'
        parts = [f'# {plain(title)}', plain(response['summary'])]
        mermaid = ''
        if successful and kind == 'document':
            for section in response['sections']:
                parts += [f'## {plain(section["heading"])}', plain(section['text'])]
        if successful and kind == 'graph':
            mermaid = diagram(response)
            parts.append('```mermaid\n' + mermaid + '\n```')
        if response.get('next_step'):
            parts += ['## 下一步', plain(response['next_step'])]
        if response.get('follow_up'):
            parts.append(plain(response['follow_up']))
        sources = response.get('citations', [])
        parts += ['## 材料依据', plain(response['evidence_notice'])]
        for i, source in enumerate(sources, 1):
            location = f'{source.get("chapter") or ""} · 版本 {source.get("version")}'
            if source.get('source_page') is not None:
                location += f' · 第 {source["source_page"]} 页'
            parts.append(f'{i}. {plain(source["title"])}（{plain(location)}）：{plain(source["supports"])}')
        return {
            'artifact_id': response['request_id'], 'request_id': response['request_id'],
            'session_id': response['session_id'], 'kind': kind, 'status': response['status'],
            'title': title, 'topic': title, 'markdown': '\n\n'.join(parts), 'mermaid': mermaid,
            'illustration': None, 'backend': response['generation_mode'],
            'evidence_status': response['evidence_status'], 'evidence_notice': response['evidence_notice'],
            'policy_result': response['policy_result'], 'learning_context': response.get('learning_context'),
            'knowledge': {'knowledge_grounded': successful and bool(sources), 'sources': sources,
                'concepts': [], 'recommended_next': [], 'confidence': None, 'confidence_level': 'UNASSESSED',
                'teaching_strategy': {'strategies': [], 'mastery_band':'unknown','style':'',
                    'practice_mode': response['teaching_plan']['task_policy'] != 'autonomous',
                    'hint_level':response['teaching_plan']['hint_level'],'hint_max_level':response['teaching_plan']['hint_level'],'hint_name':None},
                'hint_level':response['teaching_plan']['hint_level'], 'intent':response['mode'],
                'generation_mode': 'llm_reviewed' if successful else 'refused', 'latency_ms':response.get('timing', {}).get('tutoring_ms', 0), 'log_id':None},
        }
