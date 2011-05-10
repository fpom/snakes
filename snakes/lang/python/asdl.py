# this file has been automatically generated running:
# snakes/lang/asdl.py --output=snakes/lang/python/asdl.py snakes/lang/python/python.asdl
# timestamp: 2010-04-22 11:40:44.120690

from snakes.lang import ast
from snkast import *

class _AST (ast.AST):
    def __init__ (self, **ARGS):
        ast.AST.__init__(self)
        for k, v in ARGS.items():
            setattr(self, k, v)

class arguments (_AST):
    _fields = ('args', 'vararg', 'varargannotation', 'kwonlyargs', 'kwarg', 'kwargannotation', 'defaults', 'kw_defaults')
    _attributes = ()
    def __init__ (self, args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[], **ARGS):
        _AST.__init__(self, **ARGS)
        self.args = list(args)
        self.vararg = vararg
        self.varargannotation = varargannotation
        self.kwonlyargs = list(kwonlyargs)
        self.kwarg = kwarg
        self.kwargannotation = kwargannotation
        self.defaults = list(defaults)
        self.kw_defaults = list(kw_defaults)

class slice (_AST):
    pass

class Slice (slice):
    _fields = ('lower', 'upper', 'step')
    _attributes = ()
    def __init__ (self, lower=None, upper=None, step=None, **ARGS):
        slice.__init__(self, **ARGS)
        self.lower = lower
        self.upper = upper
        self.step = step

class ExtSlice (slice):
    _fields = ('dims',)
    _attributes = ()
    def __init__ (self, dims=[], **ARGS):
        slice.__init__(self, **ARGS)
        self.dims = list(dims)

class Index (slice):
    _fields = ('value',)
    _attributes = ()
    def __init__ (self, value, **ARGS):
        slice.__init__(self, **ARGS)
        self.value = value

class cmpop (_AST):
    pass

class Eq (cmpop):
    _fields = ()
    _attributes = ()

class NotEq (cmpop):
    _fields = ()
    _attributes = ()

class Lt (cmpop):
    _fields = ()
    _attributes = ()

class LtE (cmpop):
    _fields = ()
    _attributes = ()

class Gt (cmpop):
    _fields = ()
    _attributes = ()

class GtE (cmpop):
    _fields = ()
    _attributes = ()

class Is (cmpop):
    _fields = ()
    _attributes = ()

class IsNot (cmpop):
    _fields = ()
    _attributes = ()

class In (cmpop):
    _fields = ()
    _attributes = ()

class NotIn (cmpop):
    _fields = ()
    _attributes = ()

class expr_context (_AST):
    pass

class Load (expr_context):
    _fields = ()
    _attributes = ()

class Store (expr_context):
    _fields = ()
    _attributes = ()

class Del (expr_context):
    _fields = ()
    _attributes = ()

class AugLoad (expr_context):
    _fields = ()
    _attributes = ()

class AugStore (expr_context):
    _fields = ()
    _attributes = ()

class Param (expr_context):
    _fields = ()
    _attributes = ()

class keyword (_AST):
    _fields = ('arg', 'value')
    _attributes = ()
    def __init__ (self, arg, value, **ARGS):
        _AST.__init__(self, **ARGS)
        self.arg = arg
        self.value = value

class unaryop (_AST):
    pass

class Invert (unaryop):
    _fields = ()
    _attributes = ()

class Not (unaryop):
    _fields = ()
    _attributes = ()

class UAdd (unaryop):
    _fields = ()
    _attributes = ()

class USub (unaryop):
    _fields = ()
    _attributes = ()

class expr (_AST):
    pass

class BoolOp (expr):
    _fields = ('op', 'values')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, op, values=[], lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.op = op
        self.values = list(values)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class BinOp (expr):
    _fields = ('left', 'op', 'right')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, left, op, right, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.left = left
        self.op = op
        self.right = right
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class UnaryOp (expr):
    _fields = ('op', 'operand')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, op, operand, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.op = op
        self.operand = operand
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Lambda (expr):
    _fields = ('args', 'body')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, args, body, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.args = args
        self.body = body
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class IfExp (expr):
    _fields = ('test', 'body', 'orelse')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, test, body, orelse, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.test = test
        self.body = body
        self.orelse = orelse
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Dict (expr):
    _fields = ('keys', 'values')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, keys=[], values=[], lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.keys = list(keys)
        self.values = list(values)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Set (expr):
    _fields = ('elts',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, elts=[], lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.elts = list(elts)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class ListComp (expr):
    _fields = ('elt', 'generators')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, elt, generators=[], lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.elt = elt
        self.generators = list(generators)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class SetComp (expr):
    _fields = ('elt', 'generators')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, elt, generators=[], lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.elt = elt
        self.generators = list(generators)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class DictComp (expr):
    _fields = ('key', 'value', 'generators')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, key, value, generators=[], lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.key = key
        self.value = value
        self.generators = list(generators)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class GeneratorExp (expr):
    _fields = ('elt', 'generators')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, elt, generators=[], lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.elt = elt
        self.generators = list(generators)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Yield (expr):
    _fields = ('value',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, value=None, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.value = value
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Compare (expr):
    _fields = ('left', 'ops', 'comparators')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, left, ops=[], comparators=[], lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.left = left
        self.ops = list(ops)
        self.comparators = list(comparators)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Call (expr):
    _fields = ('func', 'args', 'keywords', 'starargs', 'kwargs')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, func, args=[], keywords=[], starargs=None, kwargs=None, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.func = func
        self.args = list(args)
        self.keywords = list(keywords)
        self.starargs = starargs
        self.kwargs = kwargs
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Num (expr):
    _fields = ('n',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, n, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.n = n
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Str (expr):
    _fields = ('s',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, s, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.s = s
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Ellipsis (expr):
    _fields = ()
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Attribute (expr):
    _fields = ('value', 'attr', 'ctx')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, value, attr, ctx=None, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.value = value
        self.attr = attr
        self.ctx = ctx
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Subscript (expr):
    _fields = ('value', 'slice', 'ctx')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, value, slice, ctx=None, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.value = value
        self.slice = slice
        self.ctx = ctx
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Starred (expr):
    _fields = ('value', 'ctx')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, value, ctx=None, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.value = value
        self.ctx = ctx
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Name (expr):
    _fields = ('id', 'ctx')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, id, ctx=None, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.id = id
        self.ctx = ctx
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class List (expr):
    _fields = ('elts', 'ctx')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, elts=[], ctx=None, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.elts = list(elts)
        self.ctx = ctx
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Tuple (expr):
    _fields = ('elts', 'ctx')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, elts=[], ctx=None, lineno=0, col_offset=0, **ARGS):
        expr.__init__(self, **ARGS)
        self.elts = list(elts)
        self.ctx = ctx
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class boolop (_AST):
    pass

class And (boolop):
    _fields = ()
    _attributes = ()

class Or (boolop):
    _fields = ()
    _attributes = ()

class stmt (_AST):
    pass

class FunctionDef (stmt):
    _fields = ('name', 'args', 'body', 'decorator_list', 'returns')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, name, args, body=[], decorator_list=[], returns=None, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.name = name
        self.args = args
        self.body = list(body)
        self.decorator_list = list(decorator_list)
        self.returns = returns
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class ClassDef (stmt):
    _fields = ('name', 'bases', 'keywords', 'starargs', 'kwargs', 'body', 'decorator_list')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, name, bases=[], keywords=[], starargs=None, kwargs=None, body=[], decorator_list=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.name = name
        self.bases = list(bases)
        self.keywords = list(keywords)
        self.starargs = starargs
        self.kwargs = kwargs
        self.body = list(body)
        self.decorator_list = list(decorator_list)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Return (stmt):
    _fields = ('value',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, value=None, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.value = value
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Delete (stmt):
    _fields = ('targets',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, targets=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.targets = list(targets)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Assign (stmt):
    _fields = ('targets', 'value')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, value, targets=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.targets = list(targets)
        self.value = value
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class AugAssign (stmt):
    _fields = ('target', 'op', 'value')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, target, op, value, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.target = target
        self.op = op
        self.value = value
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class For (stmt):
    _fields = ('target', 'iter', 'body', 'orelse')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, target, iter, body=[], orelse=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.target = target
        self.iter = iter
        self.body = list(body)
        self.orelse = list(orelse)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class While (stmt):
    _fields = ('test', 'body', 'orelse')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, test, body=[], orelse=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.test = test
        self.body = list(body)
        self.orelse = list(orelse)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class If (stmt):
    _fields = ('test', 'body', 'orelse')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, test, body=[], orelse=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.test = test
        self.body = list(body)
        self.orelse = list(orelse)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class With (stmt):
    _fields = ('context_expr', 'optional_vars', 'body')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, context_expr, optional_vars=None, body=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.context_expr = context_expr
        self.optional_vars = optional_vars
        self.body = list(body)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Raise (stmt):
    _fields = ('exc', 'cause')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, exc=None, cause=None, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.exc = exc
        self.cause = cause
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class TryExcept (stmt):
    _fields = ('body', 'handlers', 'orelse')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, body=[], handlers=[], orelse=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.body = list(body)
        self.handlers = list(handlers)
        self.orelse = list(orelse)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class TryFinally (stmt):
    _fields = ('body', 'finalbody')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, body=[], finalbody=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.body = list(body)
        self.finalbody = list(finalbody)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Assert (stmt):
    _fields = ('test', 'msg')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, test, msg=None, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.test = test
        self.msg = msg
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Import (stmt):
    _fields = ('names',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, names=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.names = list(names)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class ImportFrom (stmt):
    _fields = ('module', 'names', 'level')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, module, names=[], level=None, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.module = module
        self.names = list(names)
        self.level = level
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Exec (stmt):
    _fields = ('body', 'globals', 'locals')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, body, globals=None, locals=None, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.body = body
        self.globals = globals
        self.locals = locals
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Global (stmt):
    _fields = ('names',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, names=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.names = list(names)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Nonlocal (stmt):
    _fields = ('names',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, names=[], lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.names = list(names)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Expr (stmt):
    _fields = ('value',)
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, value, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.value = value
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Pass (stmt):
    _fields = ()
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Break (stmt):
    _fields = ()
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class Continue (stmt):
    _fields = ()
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, lineno=0, col_offset=0, **ARGS):
        stmt.__init__(self, **ARGS)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class excepthandler (_AST):
    pass

class ExceptHandler (excepthandler):
    _fields = ('type', 'name', 'body')
    _attributes = ('lineno', 'col_offset')
    def __init__ (self, type=None, name=None, body=[], lineno=0, col_offset=0, **ARGS):
        excepthandler.__init__(self, **ARGS)
        self.type = type
        self.name = name
        self.body = list(body)
        self.lineno = int(lineno)
        self.col_offset = int(col_offset)

class alias (_AST):
    _fields = ('name', 'asname')
    _attributes = ()
    def __init__ (self, name, asname=None, **ARGS):
        _AST.__init__(self, **ARGS)
        self.name = name
        self.asname = asname

class comprehension (_AST):
    _fields = ('target', 'iter', 'ifs')
    _attributes = ()
    def __init__ (self, target, iter, ifs=[], **ARGS):
        _AST.__init__(self, **ARGS)
        self.target = target
        self.iter = iter
        self.ifs = list(ifs)

class arg (_AST):
    _fields = ('arg', 'annotation')
    _attributes = ()
    def __init__ (self, arg, annotation=None, **ARGS):
        _AST.__init__(self, **ARGS)
        self.arg = arg
        self.annotation = annotation

class operator (_AST):
    pass

class Add (operator):
    _fields = ()
    _attributes = ()

class Sub (operator):
    _fields = ()
    _attributes = ()

class Mult (operator):
    _fields = ()
    _attributes = ()

class Div (operator):
    _fields = ()
    _attributes = ()

class Mod (operator):
    _fields = ()
    _attributes = ()

class Pow (operator):
    _fields = ()
    _attributes = ()

class LShift (operator):
    _fields = ()
    _attributes = ()

class RShift (operator):
    _fields = ()
    _attributes = ()

class BitOr (operator):
    _fields = ()
    _attributes = ()

class BitXor (operator):
    _fields = ()
    _attributes = ()

class BitAnd (operator):
    _fields = ()
    _attributes = ()

class FloorDiv (operator):
    _fields = ()
    _attributes = ()

class mod (_AST):
    pass

class Module (mod):
    _fields = ('body',)
    _attributes = ()
    def __init__ (self, body=[], **ARGS):
        mod.__init__(self, **ARGS)
        self.body = list(body)

class Interactive (mod):
    _fields = ('body',)
    _attributes = ()
    def __init__ (self, body=[], **ARGS):
        mod.__init__(self, **ARGS)
        self.body = list(body)

class Expression (mod):
    _fields = ('body',)
    _attributes = ()
    def __init__ (self, body, **ARGS):
        mod.__init__(self, **ARGS)
        self.body = body

class Suite (mod):
    _fields = ('body',)
    _attributes = ()
    def __init__ (self, body=[], **ARGS):
        mod.__init__(self, **ARGS)
        self.body = list(body)
