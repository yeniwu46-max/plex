"""Versioned, bounded contracts for Python counterexample exercises.

Parsing is static here. Candidate, fixed and reference programs execute only in
the isolated code adapter, each without the other programs or expected outputs.
"""
import ast
import hashlib
import json

CONTRACT_VERSION = 'counterexample-v2'
LEGACY_CONTRACT_VERSION = 'counterexample-v1'
BUG_KINDS = {'loop_boundary', 'empty_input', 'duplicate_elements'}
EXCEPTIONS = {'IndexError', 'ValueError', 'ZeroDivisionError'}
FUNCTIONS = {'solve', 'len', 'range', 'sum', 'min', 'max', 'abs', 'sorted', 'reversed',
             'enumerate', 'zip', 'list', 'set', 'tuple', 'int', 'bool', 'all', 'any',
             'IndexError', 'ValueError', 'ZeroDivisionError'}
METHODS = {'append', 'extend', 'pop', 'count', 'index', 'sort', 'reverse', 'copy'}
NODES = {getattr(ast, name) for name in (
    'Module FunctionDef arguments arg Return Assign AnnAssign AugAssign Expr Pass '
    'If For While Break Continue Raise Assert Name Load Store Constant List Tuple Set '
    'Subscript Slice BinOp UnaryOp BoolOp Compare IfExp Call keyword Attribute '
    'ListComp SetComp GeneratorExp comprehension Add Sub Mult Div FloorDiv Mod '
    'USub UAdd Not And Or Eq NotEq Lt LtE Gt GtE In NotIn Is IsNot'
).split()}


class CounterexampleError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def text(value, name, maximum, *, optional=False):
    if optional and value is None:
        return ''
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise CounterexampleError(f'{name} 必须为 1–{maximum} 字的文本')
    return value.strip()


def object_fields(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise CounterexampleError('请求字段不符合反例挑战约定')


def integer(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise CounterexampleError(f'{name} 必须为 {minimum}–{maximum} 的整数')
    return value


def value_contract(raw, *, output=False):
    object_fields(raw, {'type', 'minimum', 'maximum', 'min_items', 'max_items'}, {'type'})
    kind = raw['type']
    if kind not in ('integer', 'integer_array', 'boolean') or (kind == 'boolean' and not output):
        raise CounterexampleError('输入仅支持整数或整数数组，输出另支持布尔值')
    if kind == 'boolean':
        if set(raw) != {'type'}:
            raise CounterexampleError('布尔值契约不接受数值边界')
        return {'type': kind}
    lower = integer(raw.get('minimum'), 'minimum', -10**12 if output else -10**6, 10**12 if output else 10**6)
    upper = integer(raw.get('maximum'), 'maximum', lower, 10**12 if output else 10**6)
    result = {'type': kind, 'minimum': lower, 'maximum': upper}
    if kind == 'integer_array':
        least = integer(raw.get('min_items'), 'min_items', 0, 128)
        result.update(min_items=least, max_items=integer(raw.get('max_items'), 'max_items', least, 128))
    elif 'min_items' in raw or 'max_items' in raw:
        raise CounterexampleError('整数契约不接受数组长度')
    return result


def check_value(value, contract):
    kind = contract['type']
    if kind == 'boolean':
        return type(value) is bool
    def valid_integer(item):
        return type(item) is int and contract['minimum'] <= item <= contract['maximum']
    if kind == 'integer':
        return valid_integer(value)
    return (isinstance(value, list) and contract['min_items'] <= len(value) <= contract['max_items']
            and all(valid_integer(item) for item in value))


def python_function(source):
    source = text(source, 'Python 程序', 16000)
    if len(source.encode('utf-8')) > 16000:
        raise CounterexampleError('Python 程序最多 16000 UTF-8 字节')
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError, ValueError):
        raise CounterexampleError('Python 语法无效') from None
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise CounterexampleError('程序必须只定义 solve(data) 函数')
    function = tree.body[0]
    args = function.args
    if (function.name != 'solve' or function.decorator_list or function.returns or getattr(function, 'type_params', [])
            or args.posonlyargs or len(args.args) != 1 or args.args[0].arg != 'data'
            or args.args[0].annotation or args.vararg or args.kwarg or args.kwonlyargs or args.defaults):
        raise CounterexampleError('函数签名必须是 def solve(data)，不带装饰器或默认值')
    nodes = list(ast.walk(tree))
    if len(nodes) > 600:
        raise CounterexampleError('程序过于复杂，请使用单一概念的小函数')
    for node in nodes:
        if type(node) not in NODES or (isinstance(node, ast.FunctionDef) and node is not function):
            raise CounterexampleError('程序超出首版教学函数语法范围')
        if isinstance(node, ast.Name) and '__' in node.id:
            raise CounterexampleError('程序不能访问内部名称')
        if isinstance(node, ast.Attribute) and (node.attr not in METHODS or not isinstance(node.ctx, ast.Load)):
            raise CounterexampleError('仅允许列表的常用操作方法')
        if isinstance(node, ast.Call):
            if not ((isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS)
                    or (isinstance(node.func, ast.Attribute) and node.func.attr in METHODS)):
                raise CounterexampleError('程序包含不支持的函数调用')
        if isinstance(node, ast.AnnAssign):
            raise CounterexampleError('首版程序不使用可执行的类型注解')
        if isinstance(node, ast.comprehension) and node.is_async:
            raise CounterexampleError('不支持异步表达式')
    return source


def specification(raw):
    required = {'title', 'statement', 'concept_id', 'input_contract', 'output_contract',
                'reference_code', 'tests', 'reference_note', 'allowed_bug_exceptions'}
    object_fields(raw, required | {'verification'}, required)
    result = {key: text(raw[key], key, size) for key, size in (
        ('title', 120), ('statement', 4000), ('concept_id', 80), ('reference_note', 1500))}
    result['contract_version'] = CONTRACT_VERSION if 'verification' in raw else LEGACY_CONTRACT_VERSION
    result['input_contract'] = value_contract(raw['input_contract'])
    result['output_contract'] = value_contract(raw['output_contract'], output=True)
    result['reference_code'] = python_function(raw['reference_code'])
    allowed = raw['allowed_bug_exceptions']
    if not isinstance(allowed, list) or any(not isinstance(v, str) or v not in EXCEPTIONS for v in allowed):
        raise CounterexampleError('仅允许明确列出的 IndexError、ValueError、ZeroDivisionError')
    result['allowed_bug_exceptions'] = sorted(set(allowed))
    cases = raw['tests']
    if not isinstance(cases, list) or not 3 <= len(cases) <= 24:
        raise CounterexampleError('请提供 3–24 个独立测试')
    result['tests'] = []
    seen = set()
    for case in cases:
        object_fields(case, {'input', 'expected'}, {'input', 'expected'})
        if not check_value(case['input'], result['input_contract']) or not check_value(case['expected'], result['output_contract']):
            raise CounterexampleError('测试的输入或预期输出违反已声明契约')
        key = digest(case['input'])
        if key in seen:
            raise CounterexampleError('独立测试不能重复输入')
        seen.add(key)
        result['tests'].append({'input': case['input'], 'expected': case['expected']})
    if 'verification' in raw:
        from app.services.counterexample_properties import configuration
        result['verification'] = configuration(raw['verification'], result['input_contract'], result['output_contract'], result['tests'])
    return result


def candidate(raw):
    object_fields(raw, {'buggy_code', 'fixed_code', 'bug_kind', 'explanation'},
                  {'buggy_code', 'fixed_code', 'bug_kind', 'explanation'})
    if not isinstance(raw['bug_kind'], str) or raw['bug_kind'] not in BUG_KINDS:
        raise CounterexampleError('首版支持循环边界、空输入和重复元素三种错误类型')
    return {'buggy_code': python_function(raw['buggy_code']), 'fixed_code': python_function(raw['fixed_code']),
        'bug_kind': raw['bug_kind'], 'explanation': text(raw['explanation'], '错误说明', 3000)}
