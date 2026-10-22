"""Hard publication gate: independent expected tests + repeated differential runs."""
import json
import time

from app.services.code_execution import CodeExecutionService
from app.services.counterexample_contract import (CONTRACT_VERSION, CounterexampleError,
    candidate, check_value, digest, specification)
from app.services.execution_errors import ExecutionUnavailable
from app.services.counterexample_properties import POLICY, build_plan, evaluate

VALIDATOR_VERSION = 'differential-properties-v2'
HARNESS = '''import builtins, json, sys
p = json.load(sys.stdin)
names = ('len range sum min max abs sorted reversed enumerate zip list set tuple int bool all any '
         'IndexError ValueError ZeroDivisionError').split()
results = []
for value in p['inputs']:
    namespace = {'__builtins__': {name: getattr(builtins, name) for name in names}}
    try:
        exec(compile(p['source'], '<challenge>', 'exec'), namespace)
        value = namespace['solve'](value)
        json.dumps(value, allow_nan=False)
        results.append({'kind': 'value', 'value': value})
    except Exception as error:
        results.append({'kind': 'exception', 'exception': type(error).__name__})
print(json.dumps({'python': sys.version.split()[0], 'results': results}, allow_nan=False))
'''


class ValidationFailure(Exception):
    def __init__(self, reason):
        self.reason = reason


def run_function(source, inputs):
    """The container never receives another implementation or expected answers."""
    result = CodeExecutionService.run('python', HARNESS,
        json.dumps({'source': source, 'inputs': inputs}, ensure_ascii=False, allow_nan=False))
    status = (result.get('status') or {}).get('id')
    if status != 3:
        raise ValidationFailure({5:'execution_timeout', 7:'memory_limit', 14:'output_limit'}.get(status, 'execution_failed'))
    try:
        payload = json.loads(result['stdout'])
        if (set(payload) != {'python', 'results'} or not isinstance(payload['python'], str)
                or not isinstance(payload['results'], list) or len(payload['results']) != len(inputs)):
            raise ValueError()
        for item in payload['results']:
            if not isinstance(item, dict) or not (
                (item.get('kind') == 'value' and set(item) == {'kind', 'value'}) or
                (item.get('kind') == 'exception' and set(item) == {'kind', 'exception'} and isinstance(item['exception'], str))):
                raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise ValidationFailure('invalid_execution_contract') from None
    runtime = {'backend': result.get('backend'), 'python': payload['python'],
               'image_id': result.get('image_id'), 'harness_hash': digest(HARNESS)}
    if runtime['backend'] not in {'docker', 'judge0'}:
        raise ValidationFailure('unverified_execution_backend')
    if runtime['backend'] == 'docker' and not runtime['image_id']:
        raise ValidationFailure('missing_runtime_identity')
    return payload['results'], runtime


def run_suite(source, inputs):
    """Keep each isolated request below the adapter's 64 KiB stdin bound."""
    batches, batch = [], []
    for value in inputs:
        trial = [*batch, value]
        # At most 24 legal outputs (up to 128 integers each) also fit 64 KiB.
        if len(trial) > 24 or len(json.dumps({'source': source, 'inputs': trial}, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 60000:
            if not batch: raise ValidationFailure('execution_payload_limit')
            batches.append(batch); batch = [value]
        else: batch = trial
    if batch: batches.append(batch)
    outcomes, baseline = [], None
    for batch in batches:
        results, runtime = run_function(source, batch)
        if baseline and runtime != baseline: raise ValidationFailure('runtime_changed')
        baseline = runtime; outcomes.extend(results)
    return outcomes, baseline, len(batches)


def validate(spec, proposed):
    """Bounded report, suitable for the teacher view only. Raises on infra failure."""
    started = time.perf_counter()
    report = {'validator_version': VALIDATOR_VERSION, 'contract_version': CONTRACT_VERSION,
              'spec_hash': digest(spec), 'candidate_hash': digest(proposed), 'passed': False,
              'runtimes': [], 'witnesses': [], 'scope': 'declared_tests_only', 'execution_batches': 0}
    report['artifact_hashes'] = {name: digest(value) for name, value in {
        'reference_code': spec.get('reference_code'), 'fixed_code': proposed.get('fixed_code'),
        'buggy_code': proposed.get('buggy_code'), 'tests': spec.get('tests'),
        'statement': spec.get('statement'), 'input_contract': spec.get('input_contract'),
        'output_contract': spec.get('output_contract'), 'verification': spec.get('verification')}.items()}
    try:
        # Recheck persisted content before any execution; never trust a queued hash.
        spec = specification({k:v for k,v in spec.items() if k != 'contract_version'})
        proposed = candidate(proposed)
        report['contract_version'] = spec['contract_version']
        report['spec_hash'] = digest(spec)
        expected = [{'kind':'value', 'value': case['expected']} for case in spec['tests']]
        plan = build_plan(spec['input_contract'], spec['tests'], spec.get('verification'))
        inputs = plan['inputs']
        if spec.get('verification'):
            report['scope'] = 'declared_and_bounded_checks'
            report['coverage'] = {'policy_version': POLICY, 'plan_hash': plan['hash'],
                'declared_inputs': len(expected), 'total_inputs': len(inputs),
                'boundary_inputs': plan['origins'].count('boundary'), 'metamorphic_inputs': plan['origins'].count('metamorphic'),
                'properties': [], 'failures': []}
        def failure_detail(name, index, outcome, expected_value=None):
            report['failure_detail'] = {'program': name, 'input_index': index, 'input': inputs[index],
                'input_origin': plan['origins'][index], 'observed': outcome, 'expected': expected_value}
        runs = {}
        for name, source in [('reference', spec['reference_code']), ('fixed', proposed['fixed_code']), ('buggy', proposed['buggy_code'])]:
            results, runtime, batches = run_suite(source, inputs)
            repeated, runtime_again, repeated_batches = run_suite(source, inputs)
            report['execution_batches'] += batches+repeated_batches
            report['runtimes'].append({'program': name, **runtime})
            if runtime != runtime_again or (report['runtimes'] and any(
                    {k:v for k,v in item.items() if k != 'program'} != runtime for item in report['runtimes'])):
                raise ValidationFailure('runtime_changed')
            if digest(results) != digest(repeated):
                raise ValidationFailure('non_deterministic')
            for index, item in enumerate(results):
                if item['kind'] == 'value' and not check_value(item['value'], spec['output_contract']):
                    failure_detail(name, index, item)
                    raise ValidationFailure(name + '_output_contract')
                if item['kind'] == 'exception' and (name != 'buggy' or item['exception'] not in spec['allowed_bug_exceptions']):
                    failure_detail(name, index, item)
                    raise ValidationFailure(name + '_exception')
            if name in {'reference', 'fixed'}:
                for index, expected_value in enumerate(expected):
                    if digest(results[index]) != digest(expected_value):
                        failure_detail(name, index, results[index], expected_value)
                        raise ValidationFailure(name + '_test_mismatch')
                if name == 'fixed':
                    for index, (actual, reference) in enumerate(zip(results, runs['reference'])):
                        if digest(actual) != digest(reference):
                            failure_detail(name, index, actual, reference)
                            raise ValidationFailure('fixed_reference_mismatch')
                if plan['relations']:
                    checks, failures = evaluate(plan, results, name)
                    report['coverage']['properties'].extend(checks)
                    report['coverage']['failures'].extend(failures)
                    if failures: raise ValidationFailure(name + '_property_mismatch')
            runs[name] = results
        witness_count = 0
        for index, (wrong, correct) in enumerate(zip(runs['buggy'], runs['reference'])):
            if digest(wrong) != digest(correct):
                witness_count += 1
                if len(report['witnesses']) < 8:
                    report['witnesses'].append({'test_index': index, 'input': inputs[index], 'buggy': wrong,
                        'reference': correct, 'input_origin': plan['origins'][index]})
        report['witness_count'] = witness_count
        if not report['witnesses']:
            raise ValidationFailure('no_counterexample')
        report.update(passed=True, reason=None)
    except CounterexampleError:
        report['reason'] = 'invalid_program_or_contract'
    except ValidationFailure as exc:
        report['reason'] = exc.reason
    report['elapsed_ms'] = round((time.perf_counter() - started) * 1000)
    return report
