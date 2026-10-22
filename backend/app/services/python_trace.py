"""Bounded Python teaching traces. Student code executes only inside Docker.

The AST subset prevents inspection or modification of the tracer. It is not a
replacement for process isolation; both boundaries are required.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import secrets
from copy import deepcopy
from pathlib import Path

from app.services.code_execution import CodeExecutionService
from app.services.execution_errors import ExecutionInputError, ExecutionUnavailable

POLICY = 'python-subset-trace-v1'
MAX_STEPS = 80
MAX_CODE_BYTES = 12000
MAX_LINES = 200
CALLS = {'print', 'input', 'range', 'int', 'float', 'str', 'bool', 'len', 'abs',
         'min', 'max', 'sum', 'round', 'sorted', 'list', 'tuple', 'dict', 'set',
         'enumerate', 'zip', 'all', 'any'}
NODES = {ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.If, ast.For, ast.While,
         ast.Break, ast.Continue, ast.Pass, ast.Name, ast.Load, ast.Store, ast.Constant,
         ast.List, ast.Tuple, ast.Dict, ast.Set, ast.Subscript, ast.Slice, ast.BinOp,
         ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call, ast.keyword,
         ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
         ast.UAdd, ast.USub, ast.Not, ast.Invert, ast.And, ast.Or,
         ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift,
         ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot}


def validate_source(source):
    try:
        length = len(source.encode('utf-8')) if isinstance(source, str) else MAX_CODE_BYTES + 1
    except UnicodeError:
        raise ExecutionInputError('代码包含无效的 Unicode 字符') from None
    if not isinstance(source, str) or not source.strip() or length > MAX_CODE_BYTES:
        raise ExecutionInputError('执行轨迹需要非空且不超过 12 KB 的 Python 代码')
    normalized = CodeExecutionService.normalize_python_source(source)
    if len(normalized.splitlines()) > MAX_LINES:
        raise ExecutionInputError('执行轨迹最多支持 200 行代码')
    try:
        tree = ast.parse(normalized, filename='<plex-trace-input>')
        # Compile checks context (e.g. break outside a loop) without executing it.
        compile(tree, '<plex-trace-input>', 'exec')
    except (SyntaxError, ValueError, RecursionError) as exc:
        line = getattr(exc, 'lineno', None)
        raise ExecutionInputError(f'代码语法不完整，请先检查第 {line or 1} 行') from None
    nodes = list(ast.walk(tree))
    if not tree.body:
        raise ExecutionInputError('请至少输入一条可执行语句')
    if len(nodes) > 1000:
        raise ExecutionInputError('代码结构过大，请用较短的示例查看轨迹')
    names = set()
    for node in nodes:
        if type(node) not in NODES:
            raise ExecutionInputError('当前轨迹支持赋值、条件、循环和基础集合；导入、函数定义、属性访问、推导式等请使用普通运行')
        if isinstance(node, ast.Name):
            if node.id.startswith('__') or len(node.id) > 40:
                raise ExecutionInputError('轨迹模式不支持双下划线名称或超过 40 字符的变量名')
            if isinstance(node.ctx, ast.Store):
                if node.id in CALLS:
                    raise ExecutionInputError('轨迹模式中请不要覆盖内置函数名称')
                names.add(node.id)
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in CALLS):
            raise ExecutionInputError('轨迹模式只支持约定的基础 Python 函数')
        if isinstance(node, ast.keyword) and node.arg is None:
            raise ExecutionInputError('轨迹模式暂不支持展开关键字参数')
    return normalized, sorted(names)


def build_program(normalized, names, nonce):
    template = (Path(__file__).with_name('python_trace_runtime.txt')).read_text(encoding='utf-8')
    return template.replace('# __PLEX_INPUT__', '\n'.join([
        'SOURCE = ' + ascii(normalized), 'NAMES = ' + ascii(names),
        'NONCE = ' + repr(nonce), 'POLICY = ' + repr(POLICY),
        'MAX_STEPS = ' + repr(MAX_STEPS), 'ALLOWED_CALLS = ' + repr(sorted(CALLS))]))


def decode_report(text, normalized, names, nonce):
    """Validate only server-controlled fields; never trust a client trace object."""
    def invalid():
        raise ExecutionUnavailable('invalid_trace_report')

    try:
        if not isinstance(text, str) or len(text.encode('utf-8')) > 60000:
            invalid()
    except UnicodeError:
        invalid()
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: invalid()
            result[key] = value
        return result
    try:
        report = json.loads(text, object_pairs_hook=pairs, parse_constant=lambda _: invalid())
        json.dumps(report, ensure_ascii=False).encode('utf-8')
    except (ValueError, TypeError, RecursionError, UnicodeError):
        invalid()
    fields = {'policy', 'nonce', 'source_sha256', 'python_version', 'outcome', 'steps',
              'final_variables', 'stdout', 'error_type', 'error_message', 'last_line'}
    if not isinstance(report, dict) or set(report) != fields:
        invalid()
    if (report['policy'] != POLICY or report['nonce'] != nonce
            or report['source_sha256'] != hashlib.sha256(normalized.encode()).hexdigest()):
        invalid()
    if not isinstance(report['python_version'], str) or not re.fullmatch(r'3\.\d{1,2}\.\d{1,3}', report['python_version']):
        invalid()
    if not isinstance(report['outcome'], str) or report['outcome'] not in {'completed', 'runtime_error', 'step_limit', 'output_limit'}:
        invalid()
    lines = len(normalized.splitlines())
    def check_snapshot(snapshot):
        if not isinstance(snapshot, dict) or set(snapshot) != {'values','omitted'}:
            invalid()
        values, omitted = snapshot['values'], snapshot['omitted']
        if (not isinstance(values, dict) or len(values) > 6 or not set(values) <= set(names)
                or any(not isinstance(value, str) for value in values.values())
                or type(omitted) is not int or not 0 <= omitted <= len(names) - len(values)
                or len(json.dumps(snapshot, ensure_ascii=False).encode()) > 700):
            invalid()
    if not isinstance(report['steps'], list) or not 1 <= len(report['steps']) <= MAX_STEPS:
        invalid()
    for step in report['steps']:
        if (not isinstance(step, dict) or set(step) != {'line','variables'}
                or type(step['line']) is not int or not 1 <= step['line'] <= lines):
            invalid()
        check_snapshot(step['variables'])
    check_snapshot(report['final_variables'])
    if type(report['last_line']) is not int or not 1 <= report['last_line'] <= lines:
        invalid()
    if not isinstance(report['stdout'], str) or len(report['stdout'].encode()) > 4096:
        invalid()
    for field in ('error_type','error_message'):
        if not isinstance(report[field], str) or len(report[field].encode()) > 1200:
            invalid()
    if report['outcome'] == 'completed' and (report['error_type'] or report['error_message']):
        invalid()
    if report['outcome'] == 'runtime_error' and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}', report['error_type']):
        invalid()
    if report['outcome'] == 'step_limit' and len(report['steps']) != MAX_STEPS:
        invalid()
    return {key: value for key, value in report.items() if key != 'nonce'}


def for_tutor(run):
    """Only a bounded excerpt goes to the model; the stored trace is unchanged."""
    value = deepcopy(run)
    if value and value.get('kind') == 'trace' and (value.get('result') or {}).get('trace'):
        trace = value['result']['trace']
        rows = trace['steps']
        trace['total_steps'] = len(rows)
        if len(rows) > 10:
            trace['steps'] = rows[:8] + rows[-2:]
        trace['omitted_steps'] = len(rows) - len(trace['steps'])
    return value


class PythonTraceService:
    @staticmethod
    def capabilities():
        enabled = CodeExecutionService._setting('CODE_TRACE_ENABLED', 'false').lower() in {'true','1','yes'}
        return {'enabled': enabled, 'backend_supported': CodeExecutionService.backend_name() == 'docker',
                'policy': POLICY, 'max_steps': MAX_STEPS, 'max_code_bytes': MAX_CODE_BYTES,
                'supported': ['assignment','condition','loop','basic_collections'],
                'execution_health_verified': False}

    @staticmethod
    def run(source, stdin=''):
        caps = PythonTraceService.capabilities()
        if not caps['enabled']:
            raise ExecutionUnavailable('trace_feature_disabled')
        if not caps['backend_supported']:
            raise ExecutionUnavailable('trace_backend_not_validated')
        try:
            stdin_length = len(stdin.encode()) if isinstance(stdin, str) else 4097
        except UnicodeError:
            raise ExecutionInputError('输入包含无效的 Unicode 字符') from None
        if not isinstance(stdin, str) or stdin_length > 4096:
            raise ExecutionInputError('轨迹输入必须是最多 4 KiB 的文本')
        normalized, names = validate_source(source)
        nonce = secrets.token_hex(16)
        program = build_program(normalized, names, nonce)
        # This is the same isolated adapter as normal execution. No exec/runpy
        # or student subprocess is used in the application process.
        result = CodeExecutionService.run('python', program, stdin)
        if (not isinstance(result, dict) or result.get('backend') != 'docker' or not isinstance(result.get('image_id'), str)
                or not re.fullmatch(r'sha256:[a-f0-9]{64}', result['image_id'])):
            raise ExecutionUnavailable('trace_environment_not_identified')
        status = result.get('status')
        status = status.get('id') if isinstance(status, dict) else None
        if type(status) is not int:
            raise ExecutionUnavailable('invalid_trace_execution_status')
        if status in {5, 7, 14}:
            return {'backend':'docker', 'status':result['status'], 'stdout':'', 'stderr':'',
                    'compile_output':None, 'trace':None, 'trace_status':'sandbox_limit',
                    'graded':False, 'evidence_scope':'self_test'}
        if status != 3:
            raise ExecutionUnavailable('trace_runtime_failed')
        trace = decode_report(result.get('stdout'), normalized, names, nonce)
        trace.update(backend='docker', image_id=result['image_id'],
                     timing='variables_before_line', evidence_scope='self_test',
                     completed=trace['outcome'] == 'completed', code_normalized=normalized != source,
                     original_code_sha256=hashlib.sha256(source.encode()).hexdigest(),
                     stdin=stdin, stdin_sha256=hashlib.sha256(stdin.encode()).hexdigest())
        sid = {'completed':3,'runtime_error':11,'step_limit':5,'output_limit':14}[trace['outcome']]
        descriptions = {3:'Accepted',11:'Runtime Error',5:'Trace Step Limit',14:'Trace Output Limit'}
        return {'backend':'docker', 'status':{'id':sid, 'description':descriptions[sid]},
            'stdout':trace['stdout'], 'stderr':f"{trace['error_type']}: {trace['error_message']}" if sid == 11 else '',
            'compile_output':None, 'trace':trace, 'trace_status':'recorded',
            'graded':False, 'evidence_scope':'self_test'}
