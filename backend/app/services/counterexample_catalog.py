"""Teacher-only frozen drafts; development evidence is never publication proof."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
from app.data.knowledge_node_registry import get_entry
from app.services.counterexample_contract import CounterexampleError as Error, candidate, digest, object_fields, specification
from app.services.counterexample_validation import VALIDATOR_VERSION

CATALOG_PATH=Path(__file__).resolve().parents[1]/'data/counterexample_catalog_v1.json'
VALIDATION_PATH=CATALOG_PATH.with_name('counterexample_catalog_v1_validation.json')


def require(condition):
    if not condition:
        raise ValueError('invalid catalog')


@lru_cache(maxsize=1)
def load_catalog():
    try:
        catalog=json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
        require(catalog['version']=='counterexample-catalog-v1')
        require(catalog['provenance']=='ai_assisted_draft' and catalog['human_review_status']=='pending')
        require(catalog['catalog_hash']==digest({k:v for k,v in catalog.items() if k!='catalog_hash'}))
        require(len(catalog['items'])==30)
        seen=set()
        for item in catalog['items']:
            require(re.fullmatch(r'[LED](0[1-9]|10)',item['id']) and item['id'] not in seen)
            seen.add(item['id'])
            require(item['revision']==1 and item['provenance']=='ai_assisted_draft' and item['human_review_status']=='pending')
            require(item['content_hash']==digest({k:v for k,v in item.items() if k!='content_hash'}))
            spec=specification({k:v for k,v in item['specification'].items() if k!='contract_version'})
            require(spec==item['specification'] and candidate(item['candidate'])==item['candidate'])
            require(get_entry(spec['concept_id']))
        return catalog
    except (OSError,ValueError,AssertionError,KeyError,TypeError,RecursionError):
        raise Error('待审草稿库暂不可用，请检查版本文件',503) from None


def lookup(template_id):
    if not isinstance(template_id,str) or not re.fullmatch(r'[LED](0[1-9]|10)',template_id):
        raise Error('待审草稿编号无效',400)
    for item in load_catalog()['items']:
        if item['id']==template_id:return item
    raise Error('待审草稿不存在',404)


def development_records(catalog_hash):
    try:
        result=json.loads(VALIDATION_PATH.read_text(encoding='utf-8'))
        if result['catalog_hash']!=catalog_hash or result['human_review_status']!='pending':return {}
        return {item['id']:item for item in result['items'] if item['validator_version']==VALIDATOR_VERSION}
    except (OSError,ValueError,KeyError,TypeError):return {}


def summary(item, records):
    record=records.get(item['id'])
    if record and record.get('content_hash')!=item['content_hash']:record=None
    return {'id':item['id'],'revision':item['revision'],'content_hash':item['content_hash'],
        'title':item['specification']['title'],'concept_id':item['specification']['concept_id'],
        'bug_kind':item['candidate']['bug_kind'],'difficulty':item['difficulty'],'objective':item['objective'],
        'human_review_status':'pending','provenance':'ai_assisted_draft','development_validation':deepcopy(record)}


def source_reference(raw,spec,proposed):
    if raw is None:return None,'teacher_submitted'
    object_fields(raw,{'id','content_hash'},{'id','content_hash'})
    if not isinstance(raw['content_hash'],str) or not re.fullmatch(r'[a-f0-9]{64}',raw['content_hash']):
        raise Error('草稿版本摘要无效',400)
    item=lookup(raw['id'])
    if raw['content_hash']!=item['content_hash']:raise Error('草稿版本已变化，请重新载入',409)
    exact=digest(spec)==digest(item['specification']) and digest(proposed)==digest(item['candidate'])
    return {'id':item['id'],'revision':item['revision'],'content_hash':item['content_hash']},'catalog_draft' if exact else 'catalog_adapted'


class CounterexampleCatalogService:
    @staticmethod
    def list(user_id,class_id):
        from app.services.counterexample import owns_class
        owns_class(user_id,class_id)
        catalog=load_catalog();records=development_records(catalog['catalog_hash'])
        return {'version':catalog['version'],'catalog_hash':catalog['catalog_hash'],
            'items':[summary(item,records) for item in catalog['items']]}

    @staticmethod
    def get(user_id,class_id,template_id,content_hash):
        from app.services.counterexample import owns_class
        owns_class(user_id,class_id)
        item=lookup(template_id)
        if content_hash!=item['content_hash']:raise Error('草稿版本已变化，请刷新列表',409)
        result=summary(item,development_records(load_catalog()['catalog_hash']))
        return {**result,'specification':deepcopy(item['specification']),'candidate':deepcopy(item['candidate'])}
