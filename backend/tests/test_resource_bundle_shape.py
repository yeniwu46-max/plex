"""Preserve model text as a whole block, never split strings into characters."""
from app.services.pedagogical_resource import _normalize_bundle_shape, render_markdown


def test_single_code_string_preserves_indentation_and_is_one_block():
    source = 'total = 0\nfor number in [1, 2]:\n    total += number\nprint(total)'
    bundle = _normalize_bundle_shape({'code': source, 'cases': 'one scenario', 'exercises': 'one question'})
    assert len(bundle['code']) == 1
    assert bundle['code'][0]['source'] == source
    assert 'complexity' not in bundle['code'][0]
    assert bundle['cases'] == [{'scenario': 'one scenario'}]
    assert bundle['exercises'] == [{'stem': 'one question'}]
    assert source in render_markdown(bundle)


def test_single_code_mapping_keeps_fields_without_iterating_its_keys():
    bundle = _normalize_bundle_shape({'code': {'title': 'sum', 'code': 'print(3)', 'complexity': 'O(n)'}})
    assert bundle['code'] == [{'title': 'sum', 'code': 'print(3)', 'source': 'print(3)', 'complexity': 'O(n)'}]


def test_existing_block_lists_remain_lists_and_invalid_collection_types_are_empty():
    bundle = _normalize_bundle_shape({'code': ['print(1)', {'source': 'print(2)'}], 'cases': 7, 'diagrams': None})
    assert [block['source'] for block in bundle['code']] == ['print(1)', 'print(2)']
    assert bundle['cases'] == [] and bundle['diagrams'] == []
