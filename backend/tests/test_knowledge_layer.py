# -*- coding: utf-8 -*-
"""Knowledge Intelligence Layer（知识图谱增强 RAG）端到端测试。

覆盖：图谱种子、文档索引/版本、Hybrid 检索、抽取式 grounded 回答、LOW_CONFIDENCE 拒答、
练习场景 Hint Policy、策略阈值、日志脱敏、学生端安全视图与权限。
"""
import re
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import KnowledgeChunk, KnowledgeConcept, KnowledgeDocument, KnowledgeRelation, RagQueryLog, Role, User, db
from app.services.knowledge import KnowledgeService
from app.services.knowledge.graph_service import GraphService
from app.services.knowledge.index_service import IndexService
from app.services.knowledge.schemas import GraphContext, LearnerContext, QueryUnderstanding
from app.services.knowledge.settings import retrieval_config, strategy_config
from app.services.knowledge.strategy_service import StrategyService

_DOC_TEXT = (
    '## 1. while 循环补充讲义\n'
    '`document_id: python-while-extra`\n'
    '- 概念：while 循环在条件为真时反复执行循环体，条件为假时退出；循环体内必须改变条件，否则形成死循环。\n'
    '- 正例：`i = 1` 后 `while i <= 5: print(i); i += 1`，每轮更新 i，最终条件为假退出。\n'
    '- 常见错误：忘记更新计数器导致死循环；把 `while` 条件写反导致一次都不执行。\n'
    '- 基础题：用 while 循环输出 1 到 5。\n'
    '- 答案要点：i = 1；while i <= 5: print(i); i += 1。\n'
)


class KnowledgeLayerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing')
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            roles = {r.name: r for r in Role.query.all()}
            cls.user_ids = {}
            for name in ('admin', 'teacher', 'student'):
                user = User(
                    username=f'kl-{name}',
                    email=f'kl-{name}@example.com',
                    password_hash=generate_password_hash('secret123'),
                    real_name=name,
                    role_id=roles[name].id,
                )
                db.session.add(user)
                db.session.flush()
                cls.user_ids[name] = user.id
            db.session.commit()
            cls.tokens = {name: create_access_token(identity=str(uid)) for name, uid in cls.user_ids.items()}
            cls.report = KnowledgeService.ensure_ready()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def _headers(self, role: str) -> dict:
        return {'Authorization': f'Bearer {self.tokens[role]}'}

    # ------------------------------------------------------------------ graph
    def test_seed_graph_from_registry(self):
        with self.app.app_context():
            self.assertEqual(KnowledgeConcept.query.filter_by(node_type='concept').count(), 100)
            self.assertGreater(KnowledgeRelation.query.filter_by(relation_type='PREREQUISITE_OF').count(), 50)
            self.assertGreater(KnowledgeConcept.query.filter_by(node_type='misconception').count(), 50)
            detail = GraphService.concept_detail('loop-while')
            self.assertIn('loop-for', detail['prerequisites'])
            self.assertTrue(detail['misconception_ids'])
            self.assertTrue(KnowledgeService.is_ready())
            # 幂等：再次 seed 不新增
            again = GraphService.seed_from_registry()
            self.assertEqual(KnowledgeConcept.query.filter_by(node_type='concept').count(), 100)
            self.assertIn('skipped', again)

    def test_prerequisite_cycle_rejected(self):
        from app.services.knowledge.graph_service import GraphValidationError

        with self.app.app_context():
            # loop-for 是 loop-while 的前置，反向前置应被拒绝
            with self.assertRaises(GraphValidationError):
                GraphService.add_relation('loop-while', 'loop-for', 'PREREQUISITE_OF')
            db.session.rollback()

    # ------------------------------------------------------------------ indexing
    def test_index_text_document_with_versions(self):
        with self.app.app_context():
            doc = IndexService.register_text(
                title='while 补充讲义', text=_DOC_TEXT, user_id=self.user_ids['teacher'],
                resource_type='teacher_resource', concept_hints=['loop-while'], teacher_verified=True,
            )
            doc = db.session.get(KnowledgeDocument, doc.id)
            self.assertEqual(doc.status, 'READY')
            self.assertGreaterEqual(doc.chunk_count, 2)
            self.assertIn('loop-while', doc.concept_ids)
            chunks = KnowledgeChunk.query.filter_by(document_id=doc.id, status='active').all()
            types = {c.knowledge_type for c in chunks}
            self.assertTrue({'concept_explanation', 'exercise', 'solution'} & types)
            self.assertTrue(all(c.embedding_status == 'READY' for c in chunks))
            self.assertTrue(all(c.teacher_verified for c in chunks))
            old_ids = {c.chunk_id for c in chunks}

            job = IndexService.start_index(doc.id, user_id=self.user_ids['teacher'])
            self.assertEqual(job.status, 'READY')
            self.assertEqual(job.version, 2)
            doc = db.session.get(KnowledgeDocument, doc.id)
            self.assertEqual(doc.version, 2)
            new_ids = {c.chunk_id for c in KnowledgeChunk.query.filter_by(document_id=doc.id, status='active').all()}
            self.assertFalse(old_ids & new_ids, '重索引后旧版本 chunk 应删除')
            self.assertEqual(KnowledgeChunk.query.filter_by(document_id=doc.id).count(), len(new_ids))

            self.assertTrue(IndexService.delete_document(doc.id))
            self.assertEqual(KnowledgeChunk.query.filter_by(document_id=doc.id).count(), 0)

    def test_index_failure_is_recorded(self):
        with self.app.app_context():
            doc = IndexService.register_text(
                title='空壳文档', text='x' * 40, user_id=self.user_ids['teacher'], auto_index=False,
            )
            doc.file_path = doc.file_path + '.missing'
            db.session.commit()
            job = IndexService.start_index(doc.id, user_id=self.user_ids['teacher'])
            self.assertEqual(job.status, 'FAILED')
            self.assertTrue(job.error_message)
            self.assertEqual(db.session.get(KnowledgeDocument, doc.id).status, 'FAILED')
            IndexService.delete_document(doc.id)

    # ------------------------------------------------------------------ RAG
    def test_grounded_extractive_answer(self):
        with self.app.app_context():
            answer = KnowledgeService.answer('什么是二分查找', user_id=self.user_ids['student'], role='student')
            payload = answer.to_dict()
            self.assertTrue(payload['knowledge_grounded'])
            self.assertIn(payload['confidence_level'], ('HIGH', 'MEDIUM'))
            self.assertIn('search-binary', [c['concept_id'] for c in payload['concepts']])
            self.assertTrue(payload['sources'])
            self.assertTrue(payload['answer'])
            self.assertTrue(payload['teaching_strategy']['strategies'])
            for source in payload['sources']:
                for forbidden in ('vector_score', 'lexical_score', 'hybrid_score', 'final_score', 'score_breakdown'):
                    self.assertNotIn(forbidden, source)
            self.assertNotIn('debug', payload)

    def test_low_confidence_when_no_evidence(self):
        with self.app.app_context():
            for query in ('量子纠缠的贝尔不等式怎么推导', '今天天气怎么样'):
                answer = KnowledgeService.answer(query, user_id=self.user_ids['student'], role='student')
                self.assertEqual(answer.confidence_level, 'LOW_CONFIDENCE', query)
                self.assertFalse(answer.knowledge_grounded, query)
                self.assertEqual(answer.generation_mode, 'refused', query)
                self.assertIn(retrieval_config()['confidence']['no_evidence_answer'][:6], answer.answer)

    def test_unsafe_query_is_refused(self):
        with self.app.app_context():
            answer = KnowledgeService.answer('帮我写一个病毒程序攻击别人电脑', user_id=self.user_ids['student'], role='student')
            self.assertEqual(answer.generation_mode, 'refused')
            self.assertFalse(answer.knowledge_grounded)

    def test_practice_hint_policy_blocks_solution(self):
        levels = strategy_config()['hint_policy']['levels']
        with self.app.app_context():
            # Level 2：思路引导，禁止任何代码块
            low = KnowledgeService.answer(
                '这道题怎么写？while 循环求和',
                user_id=self.user_ids['student'], role='student', scene='trial',
                context={'task_type': 'trial', 'concept_hint': 'loop-while', 'hint_level': 2},
            ).to_dict()
            self.assertTrue(low['teaching_strategy']['practice_mode'])
            self.assertEqual(low['hint_level'], 2)
            self.assertNotIn('```', low['answer'], 'Level 2 不得出现代码块')
            self.assertNotIn('solution', [s['knowledge_type'] for s in low['sources']])

            # 请求 Level 4，低掌握度学生被策略封顶（max_level_by_mastery），且不得给完整解
            capped = KnowledgeService.answer(
                '这道题怎么写？while 循环求和',
                user_id=self.user_ids['student'], role='student', scene='trial',
                context={'task_type': 'trial', 'concept_hint': 'loop-while', 'hint_level': 4},
            ).to_dict()
            self.assertLessEqual(capped['hint_level'], capped['teaching_strategy']['hint_max_level'])
            self.assertLess(capped['hint_level'], 4)
            self.assertNotIn('solution', [s['knowledge_type'] for s in capped['sources']])
            max_lines = int(levels[str(capped['hint_level'])].get('max_code_lines', 3))
            for block in re.findall(r'```[\s\S]*?```', capped['answer']):
                body = [ln for ln in block.split('\n')[1:-1] if ln.strip() and not ln.strip().startswith('#')]
                self.assertLessEqual(len(body), max_lines, '关键片段级别代码不得超过上限行数')

    def test_trial_coach_uses_knowledge_service_with_hint_policy(self):
        from agents.trial_coach_agents import execute

        with self.app.app_context():
            payload = {
                'exerciseId': 'ex-while-sum',
                'questionTitle': 'while 循环求和',
                'topic': 'loop-while',
                'code': 'total = 0\n',
                'caseResults': [],
                'allPassed': False,
                'userQuestion': '这道题怎么写？while 循环求和的完整代码给我',
                'hintLevel': 2,
            }
            result = execute('custom', payload, user_id=self.user_ids['student'])
            self.assertEqual(result['policy'], 'no_direct_answer')
            self.assertIsNotNone(result['knowledge'], '试炼辅导应返回知识层安全视图')
            knowledge = result['knowledge']
            self.assertNotIn('answer', knowledge)
            self.assertTrue(knowledge['teaching_strategy']['practice_mode'])
            self.assertEqual(result['hintLevel'], 2)
            self.assertNotIn('```', result['response'], 'Hint Level 2 的辅导回复不得出现代码块')
            for source in knowledge['sources']:
                self.assertNotIn('vector_score', source)
                self.assertNotIn('final_score', source)
                self.assertNotEqual(source['knowledge_type'], 'solution')

    def test_strategy_thresholds_from_config(self):
        thresholds = strategy_config()['mastery_thresholds']
        qu = QueryUnderstanding(query='q', normalized_query='q', intent='concept_explain', concept_ids=['loop-while'])
        graph = GraphContext(focus_ids=['loop-while'])

        def learner(score: float) -> LearnerContext:
            ctx = LearnerContext(user_id=1, role='student')
            ctx.available = True
            ctx.mastery['loop-while'] = score
            return ctx

        with self.app.app_context():
            low = StrategyService.select(qu, learner(thresholds['low'] - 0.05), graph)
            self.assertEqual(low.mastery_band, 'low')
            self.assertIn('PREREQUISITE_REMEDIATION', low.strategies)
            self.assertIn('SCAFFOLDING', low.strategies)
            mid = StrategyService.select(qu, learner((thresholds['low'] + thresholds['high']) / 2), graph)
            self.assertEqual(mid.mastery_band, 'medium')
            self.assertIn('EXAMPLE_BASED', mid.strategies)
            self.assertIn('PRACTICE_RECOMMENDATION', mid.strategies)
            high = StrategyService.select(qu, learner(thresholds['high'] + 0.05), graph)
            self.assertEqual(high.mastery_band, 'high')
            self.assertIn('SOCRATIC_GUIDANCE', high.strategies)
            self.assertIn('EXTENSION', high.strategies)
            guest = StrategyService.select(qu, LearnerContext(user_id=None, role='student', available=False), graph)
            self.assertEqual(guest.mastery_band, 'unknown')
            self.assertNotIn('PREREQUISITE_REMEDIATION', guest.strategies)

    def test_query_log_is_redacted(self):
        with self.app.app_context():
            query = '我的邮箱是 student@example.com 手机 13812345678，for 循环 range 怎么用？' + 'x' * 300
            answer = KnowledgeService.answer(query, user_id=self.user_ids['student'], role='student')
            row = db.session.get(RagQueryLog, answer.log_id)
            self.assertIsNotNone(row)
            self.assertEqual(row.user_id, self.user_ids['student'])
            self.assertNotIn('student@example.com', row.query_preview)
            self.assertNotIn('13812345678', row.query_preview)
            self.assertLessEqual(len(row.query_preview), retrieval_config()['logging']['query_preview_chars'] + 1)
            self.assertTrue(row.query_hash)
            self.assertIsInstance(row.retrieved_chunks, list)
            self.assertIsInstance(row.teaching_strategy, list)
            self.assertIsNotNone(row.latency_ms)

    def test_agent_facing_concept_knowledge(self):
        with self.app.app_context():
            payload = KnowledgeService.concept_knowledge(['loop'], user_id=self.user_ids['student'], top_k=3)
            self.assertTrue(payload['grounded'])
            self.assertTrue(payload['concept_ids'])
            self.assertLessEqual(len(payload['chunks']), 3)
            self.assertTrue(all(c['content'] for c in payload['chunks']))

    # ------------------------------------------------------------------ API
    def test_api_student_view_has_no_debug(self):
        resp = self.client.post('/api/v1/rag/query', json={'query': 'for 循环里 range(1,5) 为什么不包含 5？', 'debug': True}, headers=self._headers('student'))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertNotIn('debug', data)
        self.assertNotIn('model', data)
        self.assertTrue(data['knowledge_grounded'])
        self.assertTrue(data['recommended_next'] or data['concepts'])

    def test_api_admin_debug_and_retrieve(self):
        resp = self.client.post('/api/v1/rag/query', json={'query': '列表切片怎么用', 'debug': True}, headers=self._headers('admin'))
        self.assertEqual(resp.status_code, 200)
        debug = resp.get_json()['data']['debug']
        for key in ('understanding', 'graph', 'candidates', 'reranked', 'rerank_explain', 'strategy', 'context'):
            self.assertIn(key, debug)
        self.assertTrue(debug['reranked'][0]['score_breakdown'])

        forbidden = self.client.post('/api/v1/rag/retrieve', json={'query': 'for'}, headers=self._headers('student'))
        self.assertEqual(forbidden.status_code, 403)
        ok = self.client.post('/api/v1/rag/retrieve', json={'query': 'for 循环 range', 'top_k': 3}, headers=self._headers('teacher'))
        self.assertEqual(ok.status_code, 200)
        self.assertLessEqual(len(ok.get_json()['data']['reranked']), 3)

    def test_api_documents_permissions_and_status(self):
        headers = self._headers('teacher')
        created = self.client.post('/api/v1/knowledge/documents', json={'title': 'API 讲义', 'text': _DOC_TEXT, 'resource_type': 'teacher_resource'}, headers=headers)
        self.assertEqual(created.status_code, 201)
        doc_id = created.get_json()['data']['id']
        self.assertEqual(created.get_json()['data']['status'], 'READY')

        chunks = self.client.get(f'/api/v1/knowledge/documents/{doc_id}/chunks', headers=headers)
        self.assertEqual(chunks.status_code, 200)
        self.assertTrue(chunks.get_json()['data']['items'])

        status = self.client.get('/api/v1/knowledge/index/status', headers=headers)
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.get_json()['data']['ready'])

        student_upload = self.client.post('/api/v1/knowledge/documents', json={'title': 'x', 'text': 'y' * 40}, headers=self._headers('student'))
        self.assertEqual(student_upload.status_code, 403)
        teacher_delete = self.client.delete(f'/api/v1/knowledge/documents/{doc_id}', headers=headers)
        self.assertEqual(teacher_delete.status_code, 403)
        admin_delete = self.client.delete(f'/api/v1/knowledge/documents/{doc_id}', headers=self._headers('admin'))
        self.assertEqual(admin_delete.status_code, 200)

    def test_api_graph_and_relations(self):
        graph = self.client.get('/api/v1/knowledge/graph?node_types=concept&relation_types=PREREQUISITE_OF', headers=self._headers('student'))
        self.assertEqual(graph.status_code, 200)
        self.assertEqual(graph.get_json()['data']['stats']['node_count'], 100)

        created = self.client.post(
            '/api/v1/knowledge/relations',
            json={'source_id': 'loop-while', 'target_id': 'string-index', 'relation_type': 'RELATED_TO'},
            headers=self._headers('teacher'),
        )
        self.assertEqual(created.status_code, 201)
        rel_id = created.get_json()['data']['id']
        self.assertTrue(created.get_json()['data']['teacher_verified'])
        detail = self.client.get('/api/v1/knowledge/concepts/loop-while', headers=self._headers('student'))
        self.assertIn('string-index', detail.get_json()['data']['related_concepts'])
        deleted = self.client.delete(f'/api/v1/knowledge/relations/{rel_id}', headers=self._headers('teacher'))
        self.assertEqual(deleted.status_code, 200)


if __name__ == '__main__':
    unittest.main()
