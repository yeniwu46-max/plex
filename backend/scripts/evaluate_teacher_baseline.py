"""Frozen teacher-declared inputs -> isolated comparison and blind review packs.

Default: three-arm cold-start comparison. With separately approved history:
paired snapshot availability within the same tutor pipeline. Neither establishes
learning gain. No grading labels enter model inputs.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import tempfile
import time
from unittest.mock import patch
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from scripts.prepare_teacher_baseline import digest
from scripts.teacher_baseline_contract import ContractError, read_json, verify_frozen
from app.services.knowledge.providers.llm import OpenAICompatibleLLMProvider, LLMResult
from agents.http_client import direct_post as transport_post
from app.services.tutor_policy import REVIEW_PROMPT
from scripts import teacher_state_history as state_history

ARMS = ('direct_model', 'course_rag', 'full_tutor')
PROTOCOL = 'teacher-baseline-cold-start-v1'
PARAMETERS = {'temperature': .1, 'max_tokens': 1300, 'timeout_seconds': 22,
              'review_max_tokens': 220, 'review_timeout_seconds': 12, 'http_retries': 0,
              'preserve_model_text': True}
DIRECT_PROMPT = ('你是 Python 学习助教。根据学生的问题和已有代码提供帮助，说明不确定之处；'
    '不要编造课程来源或声称实际执行了代码。检查上下文是否足够。学生请求提示时不要直接代做完整答案。')
UNKNOWN_STATE = {'state_version': 0, 'concepts': [], 'misconceptions': [], 'changes': []}


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')


def implementation_hash():
    paths = [*sorted((ROOT/'backend/app/services').rglob('*.py')),
             *sorted((ROOT/'backend/app/services/knowledge/config').glob('*.json')),
             *sorted((ROOT/'backend/app/models').glob('*.py')),
             *sorted((ROOT/'backend/app/data').glob('*.py')),
             *sorted((ROOT/'backend/agents').rglob('*.py')),
             Path(__file__), ROOT/'backend/scripts/teacher_baseline_contract.py',
             ROOT/'backend/scripts/prepare_teacher_baseline.py', ROOT/'backend/scripts/teacher_state_history.py']
    return digest({p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


def select_cases(artifact, split, maximum=None):
    report = verify_frozen(artifact)
    documents = artifact['corpus']['documents']
    if len({row['content_sha256'] for row in documents}) != len(documents):
        raise ContractError('Duplicate course content in frozen corpus; deduplicate and review a new dataset version')
    if split not in {'development', 'test'}:
        raise ContractError('Select development or test explicitly')
    if maximum is not None and (type(maximum) is not int or not 1 <= maximum <= 120):
        raise ContractError('max_cases must be an integer from 1 to 120')
    accepted = set(report['accepted_case_ids'])
    candidates = sorted((deepcopy(c) for c in artifact['case_pack']['cases']
                         if c['id'] in accepted and c['split'] == split), key=lambda c: c['id'])
    selected = candidates if maximum is None else candidates[:maximum]
    if not selected:
        raise ContractError('No accepted cases in this split')
    return selected, len(candidates)


class RecordedProvider(OpenAICompatibleLLMProvider):
    """Pin a single endpoint/configuration and account for each physical POST.

    The production provider handles JSON and transport errors. A separate fatal
    flag prevents its safe fallback from hiding a missing/drifting actual model.
    """
    def __init__(self, resolved, maximum_calls, post=transport_post):
        super().__init__(purpose='structured_code')
        if not resolved or len(resolved) != 3:
            raise ContractError('A configured model provider is required')
        if type(maximum_calls) is not int or not 1 <= maximum_calls <= 1000:
            raise ContractError('max_calls must be from 1 to 1000')
        self.resolved = tuple(resolved)
        self.maximum_calls, self.post = maximum_calls, post
        self.calls, self.actual_model, self.fatal = [], None, None
        self.request_id, self.arm, self.case_id = None, None, None

    def _resolve(self):
        return self.resolved

    def public_config(self):
        endpoint = urlsplit(self.resolved[1])
        return {'provider_host': endpoint.hostname, 'endpoint_sha256': digest(self.resolved[1]),
                'configured_model': self.resolved[2], 'parameters': dict(PARAMETERS),
                'max_physical_calls': self.maximum_calls}

    def generate(self, *, system, user, history=None, **kwargs):
        if self.fatal:
            raise ContractError(self.fatal)
        review = system == REVIEW_PROMPT
        maximum = PARAMETERS['review_max_tokens'] if review else PARAMETERS['max_tokens']
        timeout = PARAMETERS['review_timeout_seconds'] if review else PARAMETERS['timeout_seconds']
        start_index = len(self.calls)
        try:
            with patch.dict(os.environ, {'LLM_HTTP_RETRIES': '0'}), \
                 patch('app.services.knowledge.providers.llm.direct_post', self._post):
                result = super().generate(system=system, user=user, history=history,
                    max_tokens=maximum, timeout=timeout, temperature=PARAMETERS['temperature'], preserve_text=True)
        finally:
            for call in self.calls[start_index:]:
                call['stage'] = 'review' if review else 'generation'
        if result is None and self.calls[start_index:] and self.calls[-1]['status'] == 'succeeded':
            self.calls[-1].update(status='failed', error_code='empty_or_invalid_response')
        if result and self.calls[start_index:]:
            return replace(result, model=self.calls[-1].get('actual_model'))
        return result

    def _post(self, url, *args, **kwargs):
        if self.fatal or len(self.calls) >= self.maximum_calls:
            self.fatal = self.fatal or 'physical_call_budget_exhausted'
            raise ContractError(self.fatal)
        payload = kwargs['json']
        row = {'request_id': self.request_id, 'case_id': self.case_id, 'arm': self.arm,
               'sequence': len(self.calls) + 1, 'prompt_sha256': digest(payload['messages']),
               'configured_model': payload['model'], 'actual_model': None,
               'temperature': payload['temperature'], 'max_tokens': payload['max_tokens'],
               'status': 'failed', 'error_code': 'transport_or_response_error', 'usage': None}
        self.calls.append(row)
        started = time.monotonic()
        try:
            response = self.post(url, *args, **kwargs)
            response.raise_for_status()
            data = response.json()
            actual = data.get('model')
            if not isinstance(actual, str) or not actual.strip():
                self.fatal = 'actual_model_not_reported'
            elif self.actual_model is not None and actual != self.actual_model:
                self.fatal = 'actual_model_changed_during_run'
            else:
                self.actual_model = actual
            row['actual_model'] = actual if isinstance(actual, str) else None
            usage = data.get('usage') or {}
            row['usage'] = {key: usage[key] if type(usage.get(key)) is int and usage[key] >= 0 else None
                            for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
            row['status'], row['error_code'] = 'succeeded', None
            return response
        except Exception as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            row['error_code'] = f'http_{status}' if type(status) is int else 'transport_or_response_error'
            raise
        finally:
            row['elapsed_ms'] = round((time.monotonic() - started) * 1000)


@contextmanager
def isolated_course(artifact, directory, *, allow_history=False):
    """Never call create_app/bootstrap, load production records or execute case code."""
    from flask import Flask
    from app.models import db, Role, KnowledgeDocument, KnowledgeChunk
    from app.services.knowledge.graph_service import GraphService
    from app.services.knowledge.chunk_service import ChunkService
    from app.services.knowledge.vector_service import VectorService
    from app.services.knowledge.providers.vector_store import reset_vector_store
    from app.services.knowledge.providers.embedding import reset_embedding_provider
    from app.services.knowledge.lexical_index import LexicalIndex
    database = Path(directory)/'evaluation.sqlite'
    if database.exists():
        raise ContractError('Evaluation database must be a new file')
    app = Flask('plex-frozen-evaluation')
    app.config.update(TESTING=True, SECRET_KEY='isolated-evaluation-only',
        SQLALCHEMY_DATABASE_URI='sqlite:///' + database.as_posix(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False, SQLALCHEMY_ECHO=False,
        TUTOR_MODELS_ENABLED=True, LEARNER_STATE_READ_MODE='evidence',
        LEARNER_STATE_WORKER_ENABLED=False, LLM_ALLOW_IN_TESTS=True,
        CODE_EXECUTION_BACKEND='disabled', EVALUATION_HISTORY_REPLAY=allow_history)
    db.init_app(app)
    with patch.dict(os.environ, {'VECTOR_BACKEND': 'memory', 'EMBEDDING_PROVIDER': 'local', 'LLM_HTTP_RETRIES': '0'}), app.app_context():
        reset_vector_store(); reset_embedding_provider(); LexicalIndex.invalidate()
        try:
            db.create_all()
            db.session.add(Role(name='student', description='Isolated evaluation account'))
            db.session.commit()
            GraphService.seed_from_registry()
            chunker = ChunkService(GraphService.concept_lexicon())
            sources, rows = {}, []
            for material in artifact['corpus']['documents']:
                doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, 'plex-evaluation/' + material['id']))
                document = KnowledgeDocument(id=doc_id, title=material['title'], version=material['version'],
                    status='READY', course_id='python-basics', visibility='public', published=True,
                    teacher_verified=False, quality_score=.6, source='evaluation')
                db.session.add(document)
                drafts = chunker.chunk_markdown(material['content'], title=material['title'])
                if not drafts:
                    raise ContractError('An approved source produces no usable chunks: ' + material['id'])
                for draft in drafts:
                    chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'{doc_id}/{material["version"]}/{draft.sequence}'))
                    row = KnowledgeChunk(chunk_id=chunk_id, document_id=doc_id, version=material['version'],
                        content=draft.content, title=draft.title, sequence=draft.sequence,
                        content_hash=hashlib.sha256(draft.content.encode()).hexdigest(),
                        knowledge_type=draft.knowledge_type, course_id='python-basics',
                        concept_ids=draft.concept_ids, primary_concept_id=draft.primary_concept_id,
                        source_page=draft.source_page, difficulty=draft.difficulty,
                        status='active', teacher_verified=False, meta=draft.meta)
                    db.session.add(row); rows.append(row)
                    sources[chunk_id] = {'document_id': material['id'], 'version': material['version'],
                        'content_sha256': material['content_sha256'], 'title': material['title'],
                        'source_reference': material['source_reference'], 'content': draft.content[:2200],
                        'preview_truncated': len(draft.content) > 2200,
                        'chunk_content_sha256': hashlib.sha256(draft.content.encode()).hexdigest()}
            db.session.commit()
            VectorService().index_chunks(rows)
            db.session.commit()
            yield app, sources
        finally:
            db.session.remove()
            db.engine.dispose()
            reset_vector_store(); reset_embedding_provider(); LexicalIndex.invalidate()


def new_student(case_id, arm):
    from app.models import db, User, Role
    user = User(username=f'eval-{case_id}-{arm}', email=f'{uuid.uuid4().hex}@example.invalid',
        real_name='评测虚拟学生', password_hash='disabled-evaluation-account',
        role_id=Role.query.filter_by(name='student').one().id, status='active')
    db.session.add(user); db.session.commit()
    return user.id


def model_input(case):
    # Explicit allowlist: no proposed intent/concept, gold labels, evidence relevance,
    # expected response, split or boundary labels reach retrieval or generation.
    task = case.get('task_context')
    return {'question': case['query'], 'code': case.get('code') or '',
            'attached_task': {key:task[key] for key in ('title','prompt') if key in task} if isinstance(task, dict) else None,
            'execution_record': None}


def question_text(case):
    payload = model_input(case)
    text = payload['question']
    if payload['attached_task']:
        text += '\n学生附带的题目（不是服务器正式试题）：' + json.dumps(payload['attached_task'], ensure_ascii=False)
    if payload['code'] and payload['code'] not in text:
        text += '\n当前代码：\n```python\n' + payload['code'] + '\n```'
    return text


def retrieval_metrics(ranked, review, sources, k=6):
    """Document-level graded relevance, exact frozen version/hash, no zero for N/A."""
    gold = {(row['document_id'], row['version'], row['content_sha256']): row['relevance']
            for row in review['evidence']}
    if not gold:
        return {'recall_at_k': None, 'ndcg_at_k': None, 'k': k, 'relevant_documents': 0}
    selected, seen = [], set()
    for chunk_id in ranked:
        source = sources.get(chunk_id)
        if not source:
            continue
        key = (source['document_id'], source['version'], source['content_sha256'])
        if key in seen:
            continue
        seen.add(key); selected.append(key)
        if len(selected) == k:
            break
    scores = [gold.get(key, 0) for key in selected]
    dcg = sum((2**value - 1) / math.log2(i + 2) for i, value in enumerate(scores))
    ideal = sum((2**value - 1) / math.log2(i + 2) for i, value in enumerate(sorted(gold.values(), reverse=True)[:k]))
    return {'recall_at_k': sum(key in gold for key in selected)/len(gold),
            'ndcg_at_k': dcg/ideal if ideal else None, 'k': k, 'relevant_documents': len(gold)}


def run_arm(case, arm, provider, sources, *, history_context=None):
    from app.services.knowledge import KnowledgeService
    from app.services.knowledge.rag_service import KnowledgeRagService
    from app.services.knowledge.schemas import LearnerContext
    from app.services.messenger_tutoring import MessengerTutoring
    from app.services.tutor_context import TutorContextError
    from app.services.course_safety import SafetyViolation
    user_id = new_student(case['id'], arm)
    snapshot = deepcopy(UNKNOWN_STATE)
    projected = None
    if history_context is not None:
        history_row, history_pack = history_context
        projected = state_history.replay(user_id, history_row, history_pack['as_of'])
        if arm == 'tutor_state_visible': snapshot = deepcopy(projected)
        elif arm != 'tutor_state_masked': raise ContractError('History requires paired tutor arms')
    request_id = str(uuid.uuid4())
    provider.request_id, provider.case_id, provider.arm = request_id, case['id'], arm
    before, started = len(provider.calls), time.monotonic()
    ranked, plans = [], []
    original_prepare = KnowledgeService.prepare

    def tracked_prepare(*args, **kwargs):
        plan = original_prepare(*args, **kwargs)
        ranked.extend(chunk.chunk_id for chunk in plan.chunks)
        plans.append({'intent': plan.retrieval.understanding.intent, 'grounded': plan.knowledge_grounded,
                      'state_version': plan.learner.state_version, 'state_source': plan.learner.state_source})
        return plan

    result = {'request_id': request_id, 'case_id': case['id'], 'arm': arm,
              'state_provenance': 'cold_start_no_prior_evidence', 'status': 'failed', 'answer': None,
              'ranked_chunk_ids': ranked, 'retrieval': plans, 'citations': []}
    if history_context is not None:
        result.update(state_provenance=history_pack['provenance'], state_available=arm=='tutor_state_visible',
            projected_state=projected, supplied_state_sha256=digest(snapshot),
            state_projection_is_new_measurement=False)
    try:
        if arm == 'direct_model':
            answer = provider.generate(system=DIRECT_PROMPT, user=json.dumps(model_input(case), ensure_ascii=False))
            if answer:
                result.update(status='completed', answer={'text': answer.text}, generation_mode='llm')
        elif arm == 'course_rag':
            # Current graph/hybrid retrieval retained. No durable learner state,
            # explicit tutor-mode schema, model review or hint-receipt side effects.
            service = KnowledgeRagService(llm=provider)
            plan = service.prepare(question_text(case), user_id=user_id, role='student', scene='chat',
                learner_context=LearnerContext(user_id=user_id, state_source='evaluation_no_state', available=False))
            ranked.extend(chunk.chunk_id for chunk in plan.chunks)
            plans.append({'intent': plan.retrieval.understanding.intent, 'grounded': plan.knowledge_grounded,
                          'state_source': plan.learner.state_source, 'state_version': None})
            if plan.blocked_reason:
                final = service.finalize(plan, answer_text=None, generation_mode='refused', status='blocked', error=plan.blocked_reason)
                result.update(status='completed', answer={'text': final.answer}, generation_mode='refused')
            else:
                text, generation, _ = service.generate(plan, use_llm=True)
                result.update(status='completed', answer={'text': text}, generation_mode=generation)
                result['context_source_labels'] = deepcopy(plan.context.source_index)
                # Candidate sources are separately recorded; do not claim the model
                # actually cited every retrieved passage.
        elif arm in ('full_tutor', *state_history.ARMS):
            with patch.object(KnowledgeService, 'prepare', side_effect=tracked_prepare), \
                 patch('app.services.tutoring.get_llm_provider', return_value=provider):
                payload = MessengerTutoring.prepare(user_id, {'request_id': request_id,
                    'message': question_text(case), 'code': case.get('code') or ''})
                if history_context is not None and payload['mode'] in {'learning_overview','learning_document','knowledge_graph'}:
                    result['error_code'] = 'mode_reads_more_than_supplied_state'
                    raise ContractError('This mode is outside the state-only comparison')
                if history_context is None:
                    delivered = MessengerTutoring.answer(user_id, payload, state_snapshot=snapshot)
                else:
                    with state_history.decision_clock(history_pack['as_of']):
                        delivered = MessengerTutoring.answer(user_id, payload, state_snapshot=snapshot)
                response = delivered['tutor']
            visible = {key: response[key] for key in ('summary', 'next_step', 'follow_up', 'example',
                'annotations', 'pseudocode_lines', 'scope', 'trace_input', 'trace_steps', 'trace_notice', 'evidence_notice') if key in response}
            result.update(status='completed', answer={'text': delivered['reply']}, tutor_visible=visible,
                          tutor_status=response.get('status'),
                          generation_mode=response.get('generation_mode'),
                          mode=response.get('mode'), policy_result=response.get('policy_result'),
                          citations=response.get('citations') or [])
        else:
            raise ContractError('Unknown comparison arm')
    except (TutorContextError, SafetyViolation) as exc:
        status = getattr(exc, 'status', 400)
        if status in {400, 403, 404, 413, 422}:
            # This is the public request rejection seen by the student. Keep it
            # for over-refusal/action grading rather than silently dropping it.
            result.update(status='completed', answer={'text': str(exc)},
                          generation_mode='request_rejected', public_http_status=status)
        else:
            result.update(error_type=type(exc).__name__, public_http_status=status)
    except Exception as exc:
        # Exception bodies may contain provider URLs/content; retain only class/status.
        result['error_type'] = type(exc).__name__
    result['elapsed_ms'] = round((time.monotonic() - started) * 1000)
    result['calls'] = deepcopy(provider.calls[before:])
    result['infrastructure_failure'] = any(call['status'] != 'succeeded' for call in result['calls'])
    result['model_comparable'] = not provider.fatal
    result['sources'] = [dict(chunk_id=key, **sources[key]) for key in dict.fromkeys(ranked) if key in sources]
    for source in result['sources']:
        source['label'] = next((s['label'] for s in result.get('context_source_labels', []) if s['chunk_id'] == source['chunk_id']), None)
    return result


def export_review(output, cases, results, seed, *, histories=None, history_package=None):
    case_map = {case['id']: case for case in cases}
    pack, mapping = [], []
    for result in results:
        if result['status'] != 'completed':
            continue
        review_id = uuid.uuid4().hex
        citations = []
        for citation in result['citations']:
            source = next((s for s in result['sources'] if s['chunk_id'] == citation.get('chunk_id')), None)
            citations.append({'chunk_id': citation.get('chunk_id'), 'supports': citation.get('supports'),
                'source': {key:source[key] for key in ('document_id','version','content_sha256','source_reference','title')} if source else None})
        pack.append({'review_id': review_id, 'case_id': result['case_id'],
            'input': model_input(case_map[result['case_id']]), 'answer': result['answer'],
            'citations': citations, 'retrieved_sources': result['sources'],
            'scores': {'correctness': None, 'evidence_support': None, 'teaching_action': None,
                       'actionable_next_step': None, 'answer_leakage': None, 'over_refusal': None},
            'reviewer_id': None, 'reviewed_at': None, 'rationale': None})
        if histories is not None:
            pack[-1]['history_context'] = state_history.visible_history(histories[result['case_id']], history_package)
        mapping.append({'review_id': review_id, 'case_id': result['case_id'], 'arm': result['arm'],
                        'request_id': result['request_id']})
    random.Random(seed).shuffle(pack)
    write_json(output/'blind-review.json', {'schema_version': 1, 'status': 'pending_human_review', 'reviewers': [],
        'reviewed': 0, 'identity_blinding': 'arm and model labels hidden; answer style may reveal method', 'items': pack})
    write_json(output/'private-arm-map.json', {'items': mapping})


def run(artifact, output, *, split='development', maximum_cases=None, provider=None, seed=17, history_artifact=None):
    from app.services.knowledge.settings import retrieval_config, strategy_config
    cases, baseline_total = select_cases(artifact, split, None)
    histories = state_history.verify(artifact, history_artifact) if history_artifact is not None else None
    arms = state_history.ARMS if histories is not None else ARMS
    if histories is not None: cases = [case for case in cases if case['id'] in histories]
    total = len(cases)
    if maximum_cases is not None:
        if type(maximum_cases) is not int or not 1 <= maximum_cases <= 120: raise ContractError('max_cases must be from 1 to 120')
        cases = cases[:maximum_cases]
    if not cases: raise ContractError('No accepted cases in the requested split')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'protocol': state_history.PROTOCOL if histories is not None else PROTOCOL, 'dataset_sha256': artifact['artifact_sha256'],
        'implementation_sha256': implementation_hash(), 'split': split, 'eligible_cases': total,
        'selected_case_ids': [case['id'] for case in cases], 'complete_split': len(cases) == total,
        'seed': seed, 'arms': list(arms), 'parameters': dict(PARAMETERS),
        'retrieval_config': retrieval_config(), 'strategy_config': strategy_config(),
        'embedding': 'local_hash', 'vector_store': 'isolated_in_memory',
        'learner_state': 'unknown; no actual learning history imported',
        'comparison': 'current graph/hybrid course RAG vs current tutor system; not historical replay or isolated state ablation',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'model': provider.public_config() if provider else None,
        'planned_max_physical_calls': 4 * len(cases),
        'execution_verified': False, 'teacher_answer_reviews': 0}
    if histories is not None:
        manifest.update(history_sha256=history_artifact['artifact_sha256'],
            history_provenance=history_artifact['package']['provenance'],
            history_validation=history_artifact['validation'], baseline_eligible_cases=baseline_total,
            state_as_of=history_artifact['package']['as_of'],
            learner_state='same declared history replayed in both arms; only supplied snapshot masked/visible',
            comparison='state availability within the same tutor pipeline; not learning gain or state-estimator accuracy')
        write_json(output/'input-history-frozen.json', history_artifact)
    write_json(output/'manifest.json', manifest)
    write_json(output/'input-frozen.json', artifact)
    write_json(output/'approved-course-materials.json', artifact['corpus'])
    if provider is None:
        write_json(output/'report.json', {'status': 'planned_only', 'model_calls': 0, 'quality_metrics': None})
        return {'status': 'planned_only', 'cases': len(cases), 'model_calls': 0}
    results = []
    reviews = {row['case_id']: row for row in artifact['annotations']['reviews']}
    status = 'completed'
    try:
        with tempfile.TemporaryDirectory(prefix='plex-eval-') as temporary, isolated_course(artifact, temporary, allow_history=histories is not None) as (_, sources):
            order = [(case, arm) for case in cases for arm in arms]
            random.Random(seed).shuffle(order)
            for case, arm in order:
                row = run_arm(case, arm, provider, sources,
                    **({'history_context':(histories[case['id']],history_artifact['package'])} if histories is not None else {}))
                row['retrieval_metrics'] = (None if arm == 'direct_model' else
                    retrieval_metrics(row['ranked_chunk_ids'], reviews[case['id']], sources))
                results.append(row)
                write_json(output/f'result-{row["request_id"]}.json', row)
                if provider.fatal:
                    status = 'stopped_model_contract'; break
    except KeyboardInterrupt:
        status = 'interrupted'
    except Exception as exc:
        status = 'failed_setup_or_execution'
        write_json(output/'error.json', {'error_type': type(exc).__name__})
    export_review(output, cases, results, seed, histories=histories,
        history_package=history_artifact['package'] if histories is not None else None)
    if implementation_hash() != manifest['implementation_sha256']:
        status = 'stopped_implementation_changed'
    pairs = [case['id'] for case in cases if len([r for r in results if r['case_id'] == case['id']
             and r['status'] == 'completed' and not r['infrastructure_failure'] and r['model_comparable']]) == len(arms)]
    report = {'status': status, 'selected_cases': len(cases), 'expected_results': len(cases)*len(arms),
        'completed_results': sum(r['status'] == 'completed' for r in results),
        'paired_case_ids': pairs, 'unpaired_case_ids': [case['id'] for case in cases if case['id'] not in pairs],
        'actual_model': provider.actual_model, 'stop_reason': provider.fatal,
        'physical_calls': len(provider.calls), 'failed_physical_calls': sum(c['status'] != 'succeeded' for c in provider.calls),
        'teacher_answer_reviews': 0, 'quality_metrics': None, 'learning_gain': None,
        'retrieval': {arm: {'evaluable_results': len(values := [r['retrieval_metrics'] for r in results
            if r['arm'] == arm and r['status'] == 'completed' and r['retrieval_metrics']
            and r['retrieval_metrics']['recall_at_k'] is not None]),
            'mean_recall_at_6': sum(v['recall_at_k'] for v in values)/len(values) if values else None,
            'mean_ndcg_at_6': sum(v['ndcg_at_k'] for v in values)/len(values) if values else None}
            for arm in (state_history.ARMS if histories is not None else ('course_rag', 'full_tutor'))}}
    if status == 'completed' and len(pairs) != len(cases):
        report['status'] = 'completed_with_missing_pairs'
    write_json(output/'report.json', report)
    write_json(output/'calls.json', {'calls': provider.calls})
    write_json(output/'integrity.json', {'files': {path.name: digest(read_json(path, max_bytes=64*1024*1024))
        for path in sorted(output.glob('*.json'))}})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--history-frozen', type=Path, help='Switch to paired masked/visible state comparison after independent history review')
    parser.add_argument('--split', choices=('development', 'test'), default='development')
    parser.add_argument('--max-cases', type=int)
    parser.add_argument('--max-calls', type=int, default=500)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--execute-model-calls', action='store_true', help='Makes billable calls after frozen-input validation')
    args = parser.parse_args()
    try:
        artifact = read_json(args.frozen)
        select_cases(artifact, args.split, args.max_cases)  # Reject draft before resolving credentials/creating output.
        history = read_json(args.history_frozen) if args.history_frozen else None
        if history is not None: state_history.verify(artifact, history)
        provider = None
        if args.execute_model_calls:
            resolved = OpenAICompatibleLLMProvider()._resolve()
            provider = RecordedProvider(resolved, args.max_calls)
        report = run(artifact, args.output, split=args.split, maximum_cases=args.max_cases, provider=provider, seed=args.seed, history_artifact=history)
        print(json.dumps({key: report.get(key) for key in ('status', 'selected_cases', 'cases', 'physical_calls', 'model_calls')}, ensure_ascii=False))
        return 0 if report['status'] in {'planned_only', 'completed'} else 2
    except (ContractError, ValueError, OSError) as exc:
        # No provider exception content or credentials are printed.
        print(json.dumps({'status': 'invalid_input_or_configuration', 'error_type': type(exc).__name__,
                          'detail': str(exc) if isinstance(exc, ContractError) else None}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
