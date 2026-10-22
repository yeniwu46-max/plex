"""Reproducible, model-free retrieval ablation in a disposable SQLite database."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
DATASET = ROOT / 'docs/evaluation/plex-retrieval-engineering-v1.json'


def seed_corpus(dataset):
    from app.models import db, KnowledgeDocument, KnowledgeChunk
    from app.services.knowledge.vector_service import VectorService
    from app.services.knowledge.lexical_index import LexicalIndex
    from app.services.knowledge.graph_service import GraphService
    from app.services.knowledge.providers.vector_store import reset_vector_store
    reset_vector_store()
    GraphService.seed_from_registry()
    specs = {d['id']: d for d in dataset['documents']}
    chunks = []
    for item in dataset['documents']:
        source = specs.get(item.get('copy_of'), item)
        if not GraphService.concept_exists(source['concept']):
            raise ValueError('Evaluation material has an unknown course concept: ' + source['concept'])
        row_id = item['id']
        db.session.add(KnowledgeDocument(id=row_id, title=source['title'], version=1,
            status='READY', visibility=item.get('visibility', 'public'), published=True,
            teacher_verified=True, concept_ids=[source['concept']]))
        row = KnowledgeChunk(chunk_id=row_id, document_id=row_id, title=source['title'],
            content=source['content'], concept_ids=[source['concept']], primary_concept_id=source['concept'],
            version=1, teacher_verified=True, knowledge_type=item.get('knowledge_type', 'concept_explanation'))
        db.session.add(row)
        chunks.append(row)
    db.session.flush()
    VectorService().index_chunks(chunks)
    db.session.commit()
    LexicalIndex.invalidate()


def metrics(rows):
    answerable = [r for r in rows if r['relevant_groups']]
    unknown = [r for r in rows if not r['relevant_groups']]
    mean = lambda items, key: round(sum(r[key] for r in items) / len(items), 4) if items else None
    return {'queries': len(rows), 'answerable': len(answerable), 'unanswerable': len(unknown),
        'recall_at_3': mean(answerable, 'recall_at_3'), 'ndcg_at_3': mean(answerable, 'ndcg_at_3'),
        'mrr_at_3': mean(answerable, 'mrr_at_3'), 'answerable_grounded_rate': mean(answerable, 'grounded'),
        'false_grounded_rate': mean(unknown, 'grounded'), 'duplicate_rate_at_3': mean(rows, 'duplicate_rate_at_3')}


def evaluate(dataset, user_id):
    from app.services.knowledge import KnowledgeService
    from app.services.knowledge.settings import retrieval_config
    config = retrieval_config()
    original = deepcopy(config)
    groups = {d['id']: d.get('copy_of', d['id']) for d in dataset['documents']}
    reports = {}
    # The same current retrieval implementation, same corpus and model are
    # compared with individual features disabled. This is not a historical replay.
    variants = [('baseline', False, False, False, 0.), ('cleanup', True, False, False, 0.),
                ('cleanup_dedup', True, True, False, 0.),
                ('cleanup_dedup_coverage', True, True, False, 1.),
                ('cleanup_dedup_coverage_mmr', True, True, True, 1.)]
    for name, cleanup, dedup, mmr, offset in variants:
        cfg = deepcopy(original)
        cfg['query_understanding']['cleanup_enabled'] = cleanup
        cfg['rerank'].update(deduplicate_exact=dedup, mmr_enabled=mmr)
        cfg['confidence']['deduplicate_support'] = dedup
        cfg['confidence']['lexical_idf_offset'] = offset
        rows = []
        with patch.dict(config, cfg, clear=True):
            for case in dataset['queries']:
                started = time.perf_counter()
                plan = KnowledgeService.prepare(case['query'], user_id=user_id, scene='trial',
                    context={'task_type': 'practice'})
                top = plan.chunks[:3]
                ids = [c.chunk_id for c in top]
                retrieved_groups = [groups.get(cid, cid) for cid in ids]
                relevant = case['relevant']
                seen, gains = set(), []
                for group in retrieved_groups:
                    gains.append(relevant.get(group, 0) if group not in seen else 0)
                    seen.add(group)
                dcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(gains))
                ideal = sorted(relevant.values(), reverse=True)[:3]
                idcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(ideal))
                rows.append({'id': case['id'], 'query': case['query'], 'relevant_groups': relevant,
                    'retrieval_query': plan.retrieval.understanding.retrieval_query,
                    'cleanup': plan.retrieval.understanding.query_preparation,
                    'chunks': ids, 'grounded': plan.knowledge_grounded, 'confidence': round(plan.confidence, 4),
                    'raw_lexical': [c.score_breakdown.get('lexical_raw', 0) for c in top],
                    'clean_lexical': [c.score_breakdown.get('lexical_abs', 0) for c in top],
                    'recall_at_3': len(set(retrieved_groups) & set(relevant)) / max(1, len(relevant)),
                    'ndcg_at_3': dcg / idcg if idcg else 0,
                    'mrr_at_3': next((1 / (i + 1) for i, g in enumerate(gains) if g), 0),
                    'duplicate_rate_at_3': (len(ids) - len(set(retrieved_groups))) / max(1, len(ids)),
                    'elapsed_ms': round((time.perf_counter() - started) * 1000, 2)})
        reports[name] = {'config': cfg, 'metrics': metrics(rows), 'cases': rows}
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'output/plex-retrieval-engineering-v1.json')
    args = parser.parse_args()
    os.environ.update(VECTOR_BACKEND='memory', EMBEDDING_PROVIDER='local', KNOWLEDGE_AUTO_BOOTSTRAP='0')
    from app import create_app
    from app.config import TestingConfig
    from app.models import db, User
    dataset = json.loads(DATASET.read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='plex_retrieval_eval_') as directory:
        uri = 'sqlite:///' + str(Path(directory) / 'evaluation.db')
        with patch.object(TestingConfig, 'SQLALCHEMY_DATABASE_URI', uri), patch.object(TestingConfig, 'SQLALCHEMY_ECHO', False):
            app = create_app('testing')
        with app.app_context():
            try:
                seed_corpus(dataset)
                user_id = User.query.filter_by(username='student001').one().id
                results = evaluate(dataset, user_id)
            finally:
                db.session.remove()
                db.engine.dispose()
    report = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'dataset': dataset['version'],
        'dataset_sha256': hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        'label_source': dataset['label_source'], 'split': dataset['split'],
        'embedding': 'local-hash', 'vector_store': 'memory', 'model_calls': 0,
        'graph': 'repository course registry',
        'implementation_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), *(ROOT / 'backend/app/services/knowledge').glob('*.py')]},
        'results': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({name: value['metrics'] for name, value in results.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
