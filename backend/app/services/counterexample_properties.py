"""Finite, deterministic input generation and teacher-declared relations.

These are supplementary checks, not an oracle learned from candidate code.
Only immutable, explicit teacher selections enable a semantic property.
"""
from app.services.counterexample_contract import CounterexampleError, check_value, digest, object_fields, text

POLICY = 'bounded-properties-v1'
PROPERTY_IDS = {'permutation_invariant', 'duplicate_invariant', 'append_zero_invariant',
                'concatenation_additive', 'result_is_member'}
MAX_INPUTS = 64
MAX_RELATIONS_PER_PROPERTY = 4


def configuration(raw, input_contract, output_contract, tests):
    fields = {'policy_version', 'boundary_checks', 'properties', 'rationale'}
    object_fields(raw, fields, fields)
    if raw['policy_version'] != POLICY or type(raw['boundary_checks']) is not bool:
        raise CounterexampleError('补充验证策略或边界检查设置无效')
    properties = raw['properties']
    if (not isinstance(properties, list) or len(properties) > len(PROPERTY_IDS)
            or any(not isinstance(item, str) or item not in PROPERTY_IDS for item in properties)
            or len(set(properties)) != len(properties)):
        raise CounterexampleError('请选择已支持且不重复的程序性质')
    if not raw['boundary_checks'] and not properties:
        raise CounterexampleError('补充验证至少启用边界输入或一项适用性质')
    if properties and input_contract['type'] != 'integer_array':
        raise CounterexampleError('当前性质检查适用于整数数组输入')
    if {'concatenation_additive', 'result_is_member'} & set(properties) and output_contract['type'] != 'integer':
        raise CounterexampleError('拼接可加性和结果来自输入要求整数输出')
    if raw['boundary_checks'] and check_value([], input_contract) and not any(case['input'] == [] for case in tests):
        raise CounterexampleError('允许空数组时，请先为 [] 填写独立预期测试，再启用边界检查')
    result = {'policy_version': POLICY, 'boundary_checks': raw['boundary_checks'],
              'properties': sorted(properties), 'rationale': text(raw['rationale'], '性质依据', 1000)}
    plan = build_plan(input_contract, tests, result)
    if any(not any(check['property'] == key for check in plan['relations']) for key in properties):
        raise CounterexampleError('所选性质在当前范围与样例中没有可执行的非重复检查，请调整输入范围或取消该性质')
    return result


def boundary_inputs(contract):
    low, high = contract['minimum'], contract['maximum']
    values = list(dict.fromkeys([low, high, *[x for x in (0, -1, 1) if low <= x <= high]]))
    if contract['type'] == 'integer':
        return values
    sizes = list(dict.fromkeys([0, 1, 2, contract['min_items'], contract['max_items'], max(0, contract['max_items']-1)]))
    # Deterministic pattern priority covers legal lengths before applying the cap.
    samples = []
    for pattern in ('low', 'high', 'alternate', 'reverse', 'zero'):
        for size in sizes:
            if not contract['min_items'] <= size <= contract['max_items']:
                continue
            if pattern == 'low': value = [low]*size
            elif pattern == 'high': value = [high]*size
            elif pattern == 'alternate': value = [values[i % len(values)] for i in range(size)]
            elif pattern == 'reverse': value = [values[-1-i % len(values)] for i in range(size)]
            else: value = [0]*size
            if check_value(value, contract) and value not in samples:
                samples.append(value)
    return samples[:16]


def build_plan(contract, tests, config=None):
    inputs, origins, indices, relations = [], [], {}, []
    def add(value, origin):
        if not check_value(value, contract): return None
        key = digest(value)
        if key in indices: return indices[key]
        if len(inputs) >= MAX_INPUTS: return None
        index = len(inputs); indices[key] = index
        inputs.append(value); origins.append(origin)
        return index
    for test in tests: add(test['input'], 'teacher_test')
    if config and config['boundary_checks']:
        for value in boundary_inputs(contract): add(value, 'boundary')
    # Freeze bases: one relation does not recursively feed another relation.
    bases = list(enumerate(inputs))
    for key in (config or {}).get('properties', []):
        count, seen = 0, set()
        for index, value in bases:
            if not isinstance(value, list) or not value: continue
            if key == 'result_is_member':
                relations.append({'property': key, 'base': index, 'derived': None, 'transform': 'membership'})
                count += 1
            else:
                if key == 'permutation_invariant': candidates = [('reverse', value[::-1]), ('rotate', value[1:]+value[:1])]
                elif key == 'duplicate_invariant': candidates = [('append_existing', value+[value[0]]), ('repeat', value+value)]
                elif key == 'append_zero_invariant': candidates = [('append_zero', value+[0])]
                else: candidates = [('repeat', value+value)]
                for transform, derived in candidates:
                    if derived == value or not check_value(derived, contract): continue
                    derived_index = add(derived, 'metamorphic')
                    if derived_index is None or (index, derived_index) in seen: continue
                    seen.add((index, derived_index))
                    relations.append({'property': key, 'base': index, 'derived': derived_index, 'transform': transform})
                    count += 1
                    if count == MAX_RELATIONS_PER_PROPERTY: break
            if count == MAX_RELATIONS_PER_PROPERTY: break
    result = {'inputs': inputs, 'origins': origins, 'relations': relations}
    return {**result, 'hash': digest(result)}


def evaluate(plan, outcomes, program):
    """Outcomes are already checked as values; never execute code on the host."""
    records, failures = {}, []
    for relation in plan['relations']:
        key, base, derived = relation['property'], relation['base'], relation['derived']
        before = outcomes[base]['value']
        after = outcomes[derived]['value'] if derived is not None else None
        if key == 'result_is_member': passed = before in plan['inputs'][base]
        elif key == 'concatenation_additive': passed = after == 2*before
        else: passed = digest(after) == digest(before)
        record = records.setdefault(key, {'property': key, 'program': program, 'checked': 0, 'failed': 0})
        record['checked'] += 1
        if not passed:
            record['failed'] += 1
            if len(failures) < 4:
                failures.append({**relation, 'program': program, 'base_input': plan['inputs'][base],
                    'derived_input': plan['inputs'][derived] if derived is not None else None,
                    'base_output': before, 'derived_output': after})
    return list(records.values()), failures
