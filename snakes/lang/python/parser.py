"""
>>> testparser(Translator)
"""

import doctest, traceback, sys, re, operator, inspect
from snakes.lang.pgen import ParseError
from snakes.lang.python.pgen import parser
import snakes.lang.python.asdl as ast
from snakes import *

_symbols = parser.tokenizer.tok_name.copy()
# next statement overrides 'NT_OFFSET' entry with 'single_input'
# (this is desired)
_symbols.update(parser.symbolMap)

class ParseTree (list) :
    _symbols = _symbols
    def __init__ (self, st) :
        self.symbol = self._symbols[st[0][0]]
        self.kind = st[0][0]
        self.srow = st[0][1].srow
        self.erow = st[0][1].erow
        self.scol = st[0][1].scol
        self.ecol = st[0][1].ecol
        self.text = st[0][1]
        list.__init__(self, (self.__class__(child) for child in st[1]))
    def __repr__ (self) :
        return repr(self.text)
    def involve (self, rule) :
        if self.kind == rule :
            return True
        for child in self :
            if child.involve(rule) :
                return True
        return False
    def source (self) :
        lines = self.text.lexer.lines[self.srow-1:self.erow]
        if self.srow == self.erow :
            lines[0] = lines[0][self.scol:self.ecol]
        else :
            lines[0] = lines[0][self.scol:]
            lines[-1] = lines[-1][:self.ecol]
        return str("\n".join(l.rstrip("\n") for l in lines))

class Translator (object) :
    ParseTree = ParseTree
    parser = parser
    def __init__ (self, st) :
        for value, name in self.parser.tokenizer.tok_name.items() :
            setattr(self, name, value)
        self.ast = self.do(self.ParseTree(st))
    def do (self, st, ctx=ast.Load) :
        name = st.symbol
        meth = getattr(self, "do_" + name)
        tree = meth(st, ctx)
        try :
            tree.st = st
        except AttributeError :
            pass
        return tree
    # unary operations
    _unary = {"not" : ast.Not,
              "+" : ast.UAdd,
              "-" : ast.USub,
              "~" : ast.Invert}
    def _do_unary (self, st, ctx=ast.Load) :
        """unary: not_test | factor
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return ast.UnaryOp(lineno=st.srow, col_offset=st.scol,
                               op=self._unary[st[0].text](),
                               operand=self.do(st[1], ctx))
    # binary operations
    _binary = {"+" : ast.Add,
               "-" : ast.Sub,
               "*" : ast.Mult,
               "/" : ast.Div,
               "%" : ast.Mod,
               "&" : ast.BitAnd,
               "|" : ast.BitOr,
               "^" : ast.BitXor,
               "<<" : ast.LShift,
               ">>" : ast.RShift,
               "**" : ast.Pow,
               "//" : ast.FloorDiv}
    def _do_binary (self, st, ctx=ast.Load) :
        """binary: expr | xor_expr | and_expr | shift_expr | arith_expr | term
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            values=[self.do(child, ctx) for child in st[::2]]
            ops = [self._binary[child.text] for child in st[1::2]]
            while len(values) > 1 :
                left = values.pop(0)
                right = values.pop(0)
                operator = ops.pop(0)
                values.insert(0, ast.BinOp(lineno=st.srow, col_offset=st.scol,
                                           left=left,
                                           op=operator(),
                                           right=right))
            return values[0]
    # boolean operation
    _boolean = {"and" : ast.And,
                "or" : ast.Or}
    def _do_boolean (self, st, ctx=ast.Load) :
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return ast.BoolOp(lineno=st.srow, col_offset=st.scol,
                              op=self._boolean[st[1].text](),
                              values=[self.do(child, ctx) for child in st[::2]])
    # start of rule handlers
    def do_file_input (self, st, ctx=ast.Load) :
        """file_input: (NEWLINE | stmt)* ENDMARKER
        -> ast.Module

        <<< pass
        'Module(body=[Pass()])'
        """
        body = reduce(operator.add,
                      (self.do(child, ctx)  for child in st
                       if child.kind not in (self.NEWLINE, self.ENDMARKER)),
                      [])
        return ast.Module(lineno=st.srow, col_offset=st.scol,
                          body=body)
    def do_decorator (self, st, ctx=ast.Load) :
        """decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE
        -> ast.AST

        <<< @foo
        ... def f() : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[Name(id='foo', ctx=Load())], returns=None)])"
        <<< @foo.bar
        ... def f() : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[Attribute(value=Name(id='foo', ctx=Load()), attr='bar', ctx=Load())], returns=None)])"
        <<< @foo()
        ... def f() : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[Call(func=Name(id='foo', ctx=Load()), args=[], keywords=[], starargs=None, kwargs=None)], returns=None)])"
        <<< @foo(x, y)
        ... def f() : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[Call(func=Name(id='foo', ctx=Load()), args=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load())], keywords=[], starargs=None, kwargs=None)], returns=None)])"
        <<< @foo.bar(x, y)
        ... def f() : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[Call(func=Attribute(value=Name(id='foo', ctx=Load()), attr='bar', ctx=Load()), args=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load())], keywords=[], starargs=None, kwargs=None)], returns=None)])"
        """
        names = self.do(st[1], ctx).split(".")
        obj = ast.Name(lineno=st[1].srow, col_offset=st[1].scol,
                       id=names.pop(0), ctx=ctx())
        while names :
            obj = ast.Attribute(lineno=st[1].srow, col_offset=st[1].scol,
                                value=obj, attr=names.pop(0), ctx=ctx())
        if len(st) == 3 :
            return obj
        elif len(st) == 5 :
            return ast.Call(lineno=st[1].srow, col_offset=st[1].scol,
                            func=obj, args=[], keywords=[],
                            starargs=None, kwargs=None)
        else :
            args, keywords, starargs, kwargs = self.do(st[3], ctx)
            return ast.Call(lineno=st[1].srow, col_offset=st[1].scol,
                            func=obj, args=args, keywords=keywords,
                            starargs=starargs, kwargs=kwargs)
    def do_decorators (self, st, ctx=ast.Load) :
        """decorators: decorator+
        -> ast.AST+

        <<< @foo
        ... @bar
        ... @spam.egg()
        ... def f () :
        ...     pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[Name(id='foo', ctx=Load()), Name(id='bar', ctx=Load()), Call(func=Attribute(value=Name(id='spam', ctx=Load()), attr='egg', ctx=Load()), args=[], keywords=[], starargs=None, kwargs=None)], returns=None)])"
        """
        return [self.do(child, ctx) for child in st]
    def do_decorated (self, st, ctx=ast.Load) :
        """decorated: decorators (classdef | funcdef)
        -> ast.AST

        <<< @foo
        ... def f () :
        ...     pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[Name(id='foo', ctx=Load())], returns=None)])"
        <<< @foo
        ... class c () :
        ...     pass
        "Module(body=[ClassDef(name='c', bases=[], keywords=[], starargs=None, kwargs=None, body=[Pass()], decorator_list=[Name(id='foo', ctx=Load())])])"
        """
        child = self.do(st[1], ctx)
        child.decorator_list.extend(self.do(st[0], ctx))
        return child
    def do_funcdef (self, st, ctx=ast.Load) :
        """funcdef: 'def' NAME parameters ['->' test] ':' suite
        -> ast.FunctionDef

        <<< def f(x, y) : x+y
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Expr(value=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load())))], decorator_list=[], returns=None)])"
        <<< def f(x, y) -> int : x+y
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Expr(value=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load())))], decorator_list=[], returns=Name(id='int', ctx=Load()))])"
        """
        if len(st) == 5 :
            return ast.FunctionDef(lineno=st.srow, col_offset=st.scol,
                                   name=st[1].text,
                                   args=self.do(st[2], ctx),
                                   returns=None,
                                   body=self.do(st[-1], ctx),
                                   decorator_list=[])
        else :
            return ast.FunctionDef(lineno=st.srow, col_offset=st.scol,
                                   name=st[1].text,
                                   args=self.do(st[2], ctx),
                                   returns=self.do(st[5], ctx),
                                   body=self.do(st[-1], ctx),
                                   decorator_list=[])
    def do_parameters (self, st, ctx=ast.Load) :
        """parameters: '(' [typedargslist] ')'
        -> ast.arguments

        <<< def f () : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(x, y) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[], returns=None)])"
        """
        if len(st) == 2 :
            return ast.arguments(lineno=st.srow, col_offset=st.scol,
                                 args=[], vararg=None,
                                 varargannotation=None,
                                 kwonlyargs=[], kwarg=None,
                                 kwargannotation=None,
                                 defaults=[], kw_defaults=[])
        else :
            return self.do(st[1], ctx)
    def do_typedargslist (self, st, ctx=ast.Load) :
        """typedargslist: ((tfpdef ['=' test] ',')*
                ('*' [tfpdef] (',' tfpdef ['=' test])* [',' '**' tfpdef]
                 | '**' tfpdef)
                | tfpdef ['=' test] (',' tfpdef ['=' test])* [','])
        -> ast.arguments

        <<< def f(x) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(x, *y, z) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=None)], vararg='y', varargannotation=None, kwonlyargs=[arg(arg='z', annotation=None)], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[None]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(*, x=1) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[arg(arg='x', annotation=None)], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[Num(n=1)]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(x, y, *z, a=1, b=2, **d) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None)], vararg='z', varargannotation=None, kwonlyargs=[arg(arg='a', annotation=None), arg(arg='b', annotation=None)], kwarg='d', kwargannotation=None, defaults=[], kw_defaults=[Num(n=1), Num(n=2)]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(x:int) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=Name(id='int', ctx=Load()))], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(x:int, *y:float, z:bool) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=Name(id='int', ctx=Load()))], vararg='y', varargannotation=Name(id='float', ctx=Load()), kwonlyargs=[arg(arg='z', annotation=Name(id='bool', ctx=Load()))], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[None]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(*, x:int=1) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[arg(arg='x', annotation=Name(id='int', ctx=Load()))], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[Num(n=1)]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(x:int, y, *z:float, a=1, b:bool=False, **d:object) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=Name(id='int', ctx=Load())), arg(arg='y', annotation=None)], vararg='z', varargannotation=Name(id='float', ctx=Load()), kwonlyargs=[arg(arg='a', annotation=None), arg(arg='b', annotation=Name(id='bool', ctx=Load()))], kwarg='d', kwargannotation=Name(id='object', ctx=Load()), defaults=[], kw_defaults=[Num(n=1), Name(id='False', ctx=Load())]), body=[Pass()], decorator_list=[], returns=None)])"
        """
        args = []
        vararg = None
        varargannotation = None
        star = False
        kwonlyargs = []
        kwarg = None
        kwargannotation = None
        defaults = []
        kw_defaults = []
        nodes = list(st)
        while nodes :
            first = nodes.pop(0)
            if first.text == "," :
                pass
            elif first.text == "*" :
                star = True
                if nodes and nodes[0].text != "," :
                    vararg, varargannotation = self.do(nodes.pop(0), ctx)
            elif first.text == "**" :
                kwarg, kwargannotation = self.do(nodes.pop(0), ctx)
            else :
                n, a = self.do(first, ctx)
                arg = ast.arg(lineno=first.srow, col_offset=first.scol,
                              arg=n, annotation=a)
                if nodes and nodes[0].text == "=" :
                    del nodes[0]
                    d = self.do(nodes.pop(0), ctx)
                else :
                    d = None
                if star :
                    kwonlyargs.append(arg)
                    kw_defaults.append(d)
                else :
                    args.append(arg)
                    if d is not None :
                        defaults.append(d)
        return ast.arguments(lineno=st.srow, col_offset=st.scol,
                             args=args,
                             vararg=vararg,
                             varargannotation=varargannotation,
                             kwonlyargs=kwonlyargs,
                             kwarg=kwarg,
                             kwargannotation=kwargannotation,
                             defaults=defaults,
                             kw_defaults=kw_defaults)
    def do_tfpdef (self, st, ctx=ast.Load) :
        """tfpdef: NAME [':' test]
        -> str, ast.AST?

        <<< def f(x:int) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=Name(id='int', ctx=Load()))], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(x:int, y:float) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=Name(id='int', ctx=Load())), arg(arg='y', annotation=Name(id='float', ctx=Load()))], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< def f(x, y:int) : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=Name(id='int', ctx=Load()))], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[], returns=None)])"
        """
        if len(st) == 1 :
            return st[0].text, None
        else :
            return st[0].text, self.do(st[2], ctx)
    def do_varargslist (self, st, ctx=ast.Load) :
        """varargslist: ((vfpdef ['=' test] ',')*
              ('*' [vfpdef] (',' vfpdef ['=' test])*  [',' '**' vfpdef]
               | '**' vfpdef)
              | vfpdef ['=' test] (',' vfpdef ['=' test])* [','])
        -> ast.arguments

        <<< lambda x, y : x+y
        "Module(body=[Expr(value=Lambda(args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load()))))])"
        <<< lambda x, y, z=1 : x+y+z
        "Module(body=[Expr(value=Lambda(args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None), arg(arg='z', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[Num(n=1)], kw_defaults=[]), body=BinOp(left=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load())), op=Add(), right=Name(id='z', ctx=Load()))))])"
        """
        tree = self.do_typedargslist(st, ctx)
        tree.st = st
        return tree
    def do_vfpdef (self, st, ctx=ast.Load) :
        """vfpdef: NAME
        -> str, None

        Return value (str, None) is choosen for compatibility with
        do_tfpdef, so that do_typedargslist can be used for
        do_varargslist.

        <<< lambda x, y : x+y
        "Module(body=[Expr(value=Lambda(args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load()))))])"
        """
        return st[0].text, None
    def do_stmt (self, st, ctx=ast.Load) :
        """stmt: simple_stmt | compound_stmt
        -> ast.AST+

        <<< pass
        'Module(body=[Pass()])'
        <<< pass; pass
        'Module(body=[Pass(), Pass()])'
        <<< with x : y
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=None, body=[Expr(value=Name(id='y', ctx=Load()))])])"
        """
        child = self.do(st[0], ctx)
        if isinstance(child, ast.AST) :
            return [child]
        else :
            return child
    def do_simple_stmt (self, st, ctx=ast.Load) :
        """simple_stmt: small_stmt (';' small_stmt)* [';'] NEWLINE
        -> ast.AST+

        <<< del x; pass; import spam as egg
        "Module(body=[Delete(targets=[Name(id='x', ctx=Del())]), Pass(), Import(names=[alias(name='spam', asname='egg')])])"
        """
        return [self.do(child, ctx) for child in st[::2]
                if child != self.NEWLINE]
    def do_small_stmt (self, st, ctx=ast.Load) :
        """small_stmt: (expr_stmt | del_stmt | pass_stmt | flow_stmt |
                     import_stmt | global_stmt | nonlocal_stmt | assert_stmt)
        -> ast.AST

        <<< x
        "Module(body=[Expr(value=Name(id='x', ctx=Load()))])"
        <<< del x
        "Module(body=[Delete(targets=[Name(id='x', ctx=Del())])])"
        <<< pass
        'Module(body=[Pass()])'
        <<< import egg as spam
        "Module(body=[Import(names=[alias(name='egg', asname='spam')])])"
        <<< global x
        "Module(body=[Global(names=['x'])])"
        <<< nonlocal x
        "Module(body=[Nonlocal(names=['x'])])"
        <<< assert x
        "Module(body=[Assert(test=Name(id='x', ctx=Load()), msg=None)])"
        """
        return self.do(st[0], ctx)
    def do_expr_stmt (self, st, ctx=ast.Load) :
        """expr_stmt: testlist (augassign (yield_expr|testlist) |
                                ('=' (yield_expr|testlist))*)
        -> ast.Expr

        <<< x = y = 1
        "Module(body=[Assign(targets=[Name(id='x', ctx=Store()), Name(id='y', ctx=Store())], value=Num(n=1))])"
        <<< x, y = z = 1, 2
        "Module(body=[Assign(targets=[Tuple(elts=[Name(id='x', ctx=Store()), Name(id='y', ctx=Store())], ctx=Store()), Name(id='z', ctx=Store())], value=Tuple(elts=[Num(n=1), Num(n=2)], ctx=Load()))])"
        <<< x += 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=Add(), value=Num(n=1))])"
        <<< x += yield 5
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=Add(), value=Yield(value=Num(n=5)))])"
        <<< x = y = yield 1, 2
        "Module(body=[Assign(targets=[Name(id='x', ctx=Store()), Name(id='y', ctx=Store())], value=Yield(value=Tuple(elts=[Num(n=1), Num(n=2)], ctx=Load())))])"
        """
        if len(st) == 1 :
            return ast.Expr(lineno=st.srow, col_offset=st.scol,
                            value=self.do(st[0], ctx))
        elif st[1].symbol == "augassign" :
            target = self.do(st[0], ast.Store)
            if isinstance(target, ast.Tuple) :
                raise ParseError(st[0].text, reason="illegal expression for"
                                 " augmented assignment")
            return ast.AugAssign(lineno=st.srow, col_offset=st.scol,
                                 target=target,
                                 op=self.do(st[1], ctx),
                                 value=self.do(st[2], ctx))
        else :
            return ast.Assign(lineno=st.srow, col_offset=st.scol,
                              targets=[self.do(child, ast.Store)
                                       for child in st[:-1:2]],
                              value=self.do(st[-1], ctx))
    def do_augassign (self, st, ctx=ast.Load) :
        """augassign: ('+=' | '-=' | '*=' | '/=' | '%=' | '&=' | '|=' | '^=' |
            '<<=' | '>>=' | '**=' | '//=')
        -> ast.AST

        <<< x += 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=Add(), value=Num(n=1))])"
        <<< x -= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=Sub(), value=Num(n=1))])"
        <<< x *= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=Mult(), value=Num(n=1))])"
        <<< x /= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=Div(), value=Num(n=1))])"
        <<< x %= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=Mod(), value=Num(n=1))])"
        <<< x &= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=BitAnd(), value=Num(n=1))])"
        <<< x |= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=BitOr(), value=Num(n=1))])"
        <<< x ^= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=BitXor(), value=Num(n=1))])"
        <<< x <<= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=LShift(), value=Num(n=1))])"
        <<< x >>= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=RShift(), value=Num(n=1))])"
        <<< x **= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=Pow(), value=Num(n=1))])"
        <<< x //= 1
        "Module(body=[AugAssign(target=Name(id='x', ctx=Store()), op=FloorDiv(), value=Num(n=1))])"
        """
        return self._binary[st[0].text[:-1]](lineno=st.srow, col_offset=st.scol)
    def do_del_stmt (self, st, ctx=ast.Load) :
        """del_stmt: 'del' exprlist
        -> ast.Delete

        <<< del x
        "Module(body=[Delete(targets=[Name(id='x', ctx=Del())])])"
        <<< del x, y
        "Module(body=[Delete(targets=[Name(id='x', ctx=Del()), Name(id='y', ctx=Del())])])"
        """
        targets = self.do(st[1], ctx=ast.Del)
        if isinstance(targets, ast.Tuple) :
            targets = targets.elts
        else :
            targets = [targets]
        return ast.Delete(lineno=st.srow, col_offset=st.scol,
                          targets=targets)
    def do_pass_stmt (self, st, ctx=ast.Load) :
        """pass_stmt: 'pass'
        -> ast.Pass

        <<< pass
        'Module(body=[Pass()])'
        """
        return ast.Pass(lineno=st.srow, col_offset=st.scol)
    def do_flow_stmt (self, st, ctx=ast.Load) :
        """flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt
                 | yield_stmt
        -> ast.AST

        <<< break
        'Module(body=[Break()])'
        <<< continue
        'Module(body=[Continue()])'
        <<< return
        'Module(body=[Return(value=None)])'
        <<< raise
        'Module(body=[Raise(exc=None, cause=None)])'
        <<< yield
        'Module(body=[Expr(value=Yield(value=None))])'
        """
        return self.do(st[0], ctx)
    def do_break_stmt (self, st, ctx=ast.Load) :
        """break_stmt: 'break'
        -> ast.Break()

        <<< break
        'Module(body=[Break()])'
        """
        return ast.Break(lineno=st.srow, col_offset=st.scol)
    def do_continue_stmt (self, st, ctx=ast.Load) :
        """continue_stmt: 'continue'
        -> ast.Continue

        <<< continue
        'Module(body=[Continue()])'
        """
        return ast.Continue(lineno=st.srow, col_offset=st.scol)
    def do_return_stmt (self, st, ctx=ast.Load) :
        """return_stmt: 'return' [testlist]
        -> ast.Return

        <<< return
        'Module(body=[Return(value=None)])'
        <<< return 1
        'Module(body=[Return(value=Num(n=1))])'
        <<< return 1, 2
        'Module(body=[Return(value=Tuple(elts=[Num(n=1), Num(n=2)], ctx=Load()))])'
        """
        if len(st) == 1 :
            return ast.Return(lineno=st.srow, col_offset=st.scol,
                              value=None)

        else :
            return ast.Return(lineno=st.srow, col_offset=st.scol,
                              value=self.do(st[1], ctx))
    def do_yield_stmt (self, st, ctx=ast.Load) :
        """yield_stmt: yield_expr
        -> ast.Expr

        <<< yield
        'Module(body=[Expr(value=Yield(value=None))])'
        <<< yield 42
        'Module(body=[Expr(value=Yield(value=Num(n=42)))])'
        """
        return ast.Expr(lineno=st.srow, col_offset=st.scol,
                        value=self.do(st[0], ctx))
    def do_raise_stmt (self, st, ctx=ast.Load) :
        """raise_stmt: 'raise' [test ['from' test]]
        -> ast.Raise

        <<< raise
        'Module(body=[Raise(exc=None, cause=None)])'
        <<< raise Exception
        "Module(body=[Raise(exc=Name(id='Exception', ctx=Load()), cause=None)])"
        <<< raise Exception from Exception
        "Module(body=[Raise(exc=Name(id='Exception', ctx=Load()), cause=Name(id='Exception', ctx=Load()))])"
        """
        count = len(st)
        if count == 1 :
            return ast.Raise(lineno=st.srow, col_offset=st.scol,
                             exc=None, cause=None)
        elif count == 2 :
            return ast.Raise(lineno=st.srow, col_offset=st.scol,
                             exc=self.do(st[1], ctx),
                             cause=None)
        else :
            return ast.Raise(lineno=st.srow, col_offset=st.scol,
                             exc=self.do(st[1], ctx),
                             cause=self.do(st[3], ctx))
    def do_import_stmt (self, st, ctx=ast.Load) :
        """import_stmt: import_name | import_from
        -> ast.AST

        <<< import foo
        "Module(body=[Import(names=[alias(name='foo', asname=None)])])"
        <<< import foo.bar
        "Module(body=[Import(names=[alias(name='foo.bar', asname=None)])])"
        <<< import foo as bar
        "Module(body=[Import(names=[alias(name='foo', asname='bar')])])"
        <<< import foo.bar as egg
        "Module(body=[Import(names=[alias(name='foo.bar', asname='egg')])])"
        <<< import foo as bar, egg as spam
        "Module(body=[Import(names=[alias(name='foo', asname='bar'), alias(name='egg', asname='spam')])])"
        <<< import foo, bar, egg as spam
        "Module(body=[Import(names=[alias(name='foo', asname=None), alias(name='bar', asname=None), alias(name='egg', asname='spam')])])"
        """
        return self.do(st[0], ctx)
    def do_import_name (self, st, ctx=ast.Load) :
        """import_name: 'import' dotted_as_names
        -> ast.Import

        <<< import foo
        "Module(body=[Import(names=[alias(name='foo', asname=None)])])"
        <<< import foo.bar
        "Module(body=[Import(names=[alias(name='foo.bar', asname=None)])])"
        <<< import foo as bar
        "Module(body=[Import(names=[alias(name='foo', asname='bar')])])"
        <<< import foo.bar as egg
        "Module(body=[Import(names=[alias(name='foo.bar', asname='egg')])])"
        <<< import foo as bar, egg as spam
        "Module(body=[Import(names=[alias(name='foo', asname='bar'), alias(name='egg', asname='spam')])])"
        <<< import foo, bar, egg as spam
        "Module(body=[Import(names=[alias(name='foo', asname=None), alias(name='bar', asname=None), alias(name='egg', asname='spam')])])"
        """
        return ast.Import(lineno=st.srow, col_offset=st.scol,
                          names=self.do(st[1], ctx))
    def do_import_from (self, st, ctx=ast.Load) :
        """import_from: ('from' (('.' | '...')* dotted_name | ('.' | '...')+)
              'import' ('*' | '(' import_as_names ')' | import_as_names))
        -> ast.ImportFrom

        <<< from foo import egg as spam
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam')], level=0)])"
        <<< from .foo import egg as spam
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam')], level=1)])"
        <<< from ...foo import egg as spam
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam')], level=3)])"
        <<< from ...foo.bar import egg as spam
        "Module(body=[ImportFrom(module='foo.bar', names=[alias(name='egg', asname='spam')], level=3)])"
        <<< from foo import egg as spam, bar as baz
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam'), alias(name='bar', asname='baz')], level=0)])"
        <<< from .foo import egg as spam, bar as baz
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam'), alias(name='bar', asname='baz')], level=1)])"
        <<< from ...foo import egg as spam, bar as baz
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam'), alias(name='bar', asname='baz')], level=3)])"
        <<< from ...foo.bar import egg as spam, baz
        "Module(body=[ImportFrom(module='foo.bar', names=[alias(name='egg', asname='spam'), alias(name='baz', asname=None)], level=3)])"
        <<< from foo import *
        "Module(body=[ImportFrom(module='foo', names=[alias(name='*', asname=None)], level=0)])"
        <<< from .foo import *
        "Module(body=[ImportFrom(module='foo', names=[alias(name='*', asname=None)], level=1)])"
        <<< from ...foo import *
        "Module(body=[ImportFrom(module='foo', names=[alias(name='*', asname=None)], level=3)])"
        <<< from ...foo.bar import *
        "Module(body=[ImportFrom(module='foo.bar', names=[alias(name='*', asname=None)], level=3)])"
        """
        level = 0
        next = 1
        for i, child in enumerate(st[1:]) :
            text = child.text
            if text not in (".", "...") :
                next = i+1
                break
            level += len(text)
        if text == "import" :
            module = ""
            next += 1
        else :
            module = self.do(st[next], ctx)
            next += 2
        text = st[next].text
        if text == "*" :
            names = [ast.alias(lineno=st[next].srow, col_offset=st[next].scol,
                               name="*", asname=None)]
        elif text == "(" :
            names = self.do(st[next+1], ctx)
        else :
            names = self.do(st[next], ctx)
        return ast.ImportFrom(lineno=st.srow, col_offset=st.scol,
                              module=module, names=names, level=level)
    def do_import_as_name (self, st, ctx=ast.Load) :
        """import_as_name: NAME ['as' NAME]
        -> ast.alias

        <<< from foo import egg as spam
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam')], level=0)])"
        """
        if len(st) == 1 :
            return ast.alias(lineno=st.srow, col_offset=st.scol,
                             name=st[0].text,
                             asname=None)
        else :
            return ast.alias(lineno=st.srow, col_offset=st.scol,
                             name=st[0].text,
                             asname=st[2].text)
    def do_dotted_as_name (self, st, ctx=ast.Load) :
        """dotted_as_name: dotted_name ['as' NAME]
        -> ast.alias

        <<< import foo.bar as egg
        "Module(body=[Import(names=[alias(name='foo.bar', asname='egg')])])"
        """
        if len(st) == 1 :
            return ast.alias(lineno=st.srow, col_offset=st.scol,
                             name=self.do(st[0], ctx),
                             asname=None)
        else :
            return ast.alias(lineno=st.srow, col_offset=st.scol,
                             name=self.do(st[0], ctx),
                             asname=st[2].text)
    def do_import_as_names (self, st, ctx=ast.Load) :
        """import_as_names: import_as_name (',' import_as_name)* [',']
        -> ast.alias+

        <<< from foo import egg as spam
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam')], level=0)])"
        <<< from foo import egg as spam, bar as baz
        "Module(body=[ImportFrom(module='foo', names=[alias(name='egg', asname='spam'), alias(name='bar', asname='baz')], level=0)])"
        """
        return [self.do(child, ctx) for child in st[::2]]
    def do_dotted_as_names (self, st, ctx=ast.Load) :
        """dotted_as_names: dotted_as_name (',' dotted_as_name)*
        -> ast.alias+

        <<< import foo.bar, egg.spam as baz
        "Module(body=[Import(names=[alias(name='foo.bar', asname=None), alias(name='egg.spam', asname='baz')])])"
        """
        return [self.do(child, ctx) for child in st[::2]]
    def do_dotted_name (self, st, ctx=ast.Load) :
        """dotted_name: NAME ('.' NAME)*
        -> str

        <<< import foo.bar
        "Module(body=[Import(names=[alias(name='foo.bar', asname=None)])])"
        """
        return ".".join(child.text for child in st[::2])
    def do_global_stmt (self, st, ctx=ast.Load) :
        """global_stmt: 'global' NAME (',' NAME)*
        -> ast.Global

        <<< global x
        "Module(body=[Global(names=['x'])])"
        <<< global x, y
        "Module(body=[Global(names=['x', 'y'])])"
        """
        return ast.Global(lineno=st.srow, col_offset=st.scol,
                          names=[child.text for child in st[1::2]])
    def do_nonlocal_stmt (self, st, ctx=ast.Load) :
        """nonlocal_stmt: 'nonlocal' NAME (',' NAME)*
        -> ast.Nonlocal

        <<< nonlocal x
        "Module(body=[Nonlocal(names=['x'])])"
        <<< nonlocal x, y
        "Module(body=[Nonlocal(names=['x', 'y'])])"
        """
        return ast.Nonlocal(lineno=st.srow, col_offset=st.scol,
                            names=[child.text for child in st[1::2]])
    def do_assert_stmt (self, st, ctx=ast.Load) :
        """assert_stmt: 'assert' test [',' test]
        -> ast.Assert

        <<< assert x
        "Module(body=[Assert(test=Name(id='x', ctx=Load()), msg=None)])"
        <<< assert x, y
        "Module(body=[Assert(test=Name(id='x', ctx=Load()), msg=Name(id='y', ctx=Load()))])"
        """
        if len(st) == 2 :
            return ast.Assert(lineno=st.srow, col_offset=st.scol,
                              test=self.do(st[1], ctx),
                              msg=None)
        else :
            return ast.Assert(lineno=st.srow, col_offset=st.scol,
                              test=self.do(st[1], ctx),
                              msg=self.do(st[3], ctx))
    def do_compound_stmt (self, st, ctx=ast.Load) :
        """compound_stmt: (if_stmt | while_stmt | for_stmt | try_stmt
                | with_stmt | funcdef | classdef | decorated)
        -> ast.AST

        <<< with x : pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=None, body=[Pass()])])"
        <<< if x : pass
        "Module(body=[If(test=Name(id='x', ctx=Load()), body=[Pass()], orelse=[])])"
        <<< while x : pass
        "Module(body=[While(test=Name(id='x', ctx=Load()), body=[Pass()], orelse=[])])"
        <<< for x in l : pass
        "Module(body=[For(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), body=[Pass()], orelse=[])])"
        <<< try : pass
        ... except : pass
        'Module(body=[TryExcept(body=[Pass()], handlers=[ExceptHandler(type=None, name=None, body=[Pass()])], orelse=[])])'
        <<< def f () : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[], returns=None)])"
        <<< class c () : pass
        "Module(body=[ClassDef(name='c', bases=[], keywords=[], starargs=None, kwargs=None, body=[Pass()], decorator_list=[])])"
        <<< @foo
        ... def f () : pass
        "Module(body=[FunctionDef(name='f', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=[Pass()], decorator_list=[Name(id='foo', ctx=Load())], returns=None)])"
        """
        return self.do(st[0], ctx)
    def do_if_stmt (self, st, ctx=ast.Load) :
        """if_stmt: 'if' test ':' suite ('elif' test ':' suite)*
               ['else' ':' suite]
        -> ast.If

        <<< if x == 1 : pass
        "Module(body=[If(test=Compare(left=Name(id='x', ctx=Load()), ops=[Eq()], comparators=[Num(n=1)]), body=[Pass()], orelse=[])])"
        <<< if x == 1 : pass
        ... else : pass
        "Module(body=[If(test=Compare(left=Name(id='x', ctx=Load()), ops=[Eq()], comparators=[Num(n=1)]), body=[Pass()], orelse=[Pass()])])"
        <<< if x == 1 : pass
        ... elif y == 2 : pass
        ... elif z == 3 : pass
        ... else : pass
        "Module(body=[If(test=Compare(left=Name(id='x', ctx=Load()), ops=[Eq()], comparators=[Num(n=1)]), body=[Pass()], orelse=[If(test=Compare(left=Name(id='y', ctx=Load()), ops=[Eq()], comparators=[Num(n=2)]), body=[Pass()], orelse=[If(test=Compare(left=Name(id='z', ctx=Load()), ops=[Eq()], comparators=[Num(n=3)]), body=[Pass()], orelse=[Pass()])])])])"

        """
        nodes = list(st)
        first = None
        last = None
        while nodes :
            if len(nodes) == 3 :
                last.orelse.extend(self.do(nodes[2], ctx))
                del nodes[:3]
            else :
                next = ast.If(lineno=nodes[0].srow, col_offset=nodes[0].scol,
                              test=self.do(nodes[1], ctx),
                              body=self.do(nodes[3], ctx),
                              orelse=[])
                if first is None :
                    first = next
                if last is not None :
                    last.orelse.append(next)
                last = next
                del nodes[:4]
        return first
    def do_while_stmt (self, st, ctx=ast.Load) :
        """while_stmt: 'while' test ':' suite ['else' ':' suite]
        -> ast.While

        <<< while x : pass
        "Module(body=[While(test=Name(id='x', ctx=Load()), body=[Pass()], orelse=[])])"
        <<< while x :
        ...     pass
        ...     pass
        "Module(body=[While(test=Name(id='x', ctx=Load()), body=[Pass(), Pass()], orelse=[])])"
        <<< while x :
        ...     pass
        ... else :
        ...     pass
        "Module(body=[While(test=Name(id='x', ctx=Load()), body=[Pass()], orelse=[Pass()])])"
        """
        if len(st) == 4 :
            return ast.While(lineno=st.srow, col_offset=st.scol,
                             test=self.do(st[1], ctx),
                             body=self.do(st[3], ctx),
                             orelse=[])
        else :
            return ast.While(lineno=st.srow, col_offset=st.scol,
                             test=self.do(st[1], ctx),
                             body=self.do(st[3], ctx),
                             orelse=self.do(st[6], ctx))
    def do_for_stmt (self, st, ctx=ast.Load) :
        """for_stmt: 'for' exprlist 'in' testlist ':' suite ['else' ':' suite]
        -> ast.For

        <<< for x in l : pass
        "Module(body=[For(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), body=[Pass()], orelse=[])])"
        <<< for x in l :
        ...     pass
        ...     pass
        "Module(body=[For(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), body=[Pass(), Pass()], orelse=[])])"
        <<< for x in l :
        ...     pass
        ... else :
        ...     pass
        "Module(body=[For(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), body=[Pass()], orelse=[Pass()])])"
        <<< for x, y in l : pass
        "Module(body=[For(target=Tuple(elts=[Name(id='x', ctx=Store()), Name(id='y', ctx=Store())], ctx=Store()), iter=Name(id='l', ctx=Load()), body=[Pass()], orelse=[])])"
        <<< for x in a, b : pass
        "Module(body=[For(target=Name(id='x', ctx=Store()), iter=Tuple(elts=[Name(id='a', ctx=Load()), Name(id='b', ctx=Load())], ctx=Load()), body=[Pass()], orelse=[])])"
        """
        if len(st) == 6 :
            return ast.For(lineno=st.srow, col_offset=st.scol,
                           target=self.do(st[1], ast.Store),
                           iter=self.do(st[3], ctx),
                           body=self.do(st[5], ctx),
                           orelse=[])
        else :
            return ast.For(lineno=st.srow, col_offset=st.scol,
                           target=self.do(st[1], ast.Store),
                           iter=self.do(st[3], ctx),
                           body=self.do(st[5], ctx),
                           orelse=self.do(st[8], ctx))
    def do_try_stmt (self, st, ctx=ast.Load) :
        """try_stmt: ('try' ':' suite
           ((except_clause ':' suite)+
            ['else' ':' suite]
            ['finally' ':' suite] |
	   'finally' ':' suite))
        -> ast.TryExcept | ast.TryFinally

        <<< try : pass
        ... except : pass
        'Module(body=[TryExcept(body=[Pass()], handlers=[ExceptHandler(type=None, name=None, body=[Pass()])], orelse=[])])'
        <<< try : pass
        ... except : pass
        ... else : pass
        ... finally : pass
        'Module(body=[TryFinally(body=[TryExcept(body=[Pass()], handlers=[ExceptHandler(type=None, name=None, body=[Pass()])], orelse=[Pass()])], finalbody=[Pass()])])'
        <<< try : pass
        ... except TypeError : pass
        ... except ValueError : pass
        ... except : pass
        "Module(body=[TryExcept(body=[Pass()], handlers=[ExceptHandler(type=Name(id='TypeError', ctx=Load()), name=None, body=[Pass()]), ExceptHandler(type=Name(id='ValueError', ctx=Load()), name=None, body=[Pass()]), ExceptHandler(type=None, name=None, body=[Pass()])], orelse=[])])"
        """
        handlers = []
        finalbody = None
        orelse = []
        nodes = st[3:]
        while nodes :
            if nodes[0].text == "else" :
                orelse.extend(self.do(nodes[2], ctx))
            elif nodes[0].text == "finally" :
                finalbody = self.do(nodes[2], ctx)
            else :
                t, n = self.do(nodes[0], ctx)
                handlers.append(ast.ExceptHandler(lineno=nodes[0].srow,
                                                  col_offset=nodes[0].scol,
                                                  type=t, name=n,
                                                  body=self.do(nodes[2], ctx)))
            del nodes[:3]
        stmt = ast.TryExcept(lineno=st.srow, col_offset=st.scol,
                             body=self.do(st[2], ctx),
                             handlers=handlers,
                             orelse=orelse)
        if finalbody is None :
            return stmt
        else :
            return ast.TryFinally(lineno=st.srow, col_offset=st.scol,
                                  body=[stmt], finalbody=finalbody)
    def do_with_stmt (self, st, ctx=ast.Load) :
        """with_stmt: 'with' test [ with_var ] ':' suite
        -> ast.With

        <<< with x : pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=None, body=[Pass()])])"
        <<< with x as y : pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=Name(id='y', ctx=Store()), body=[Pass()])])"
        <<< with x :
        ...     pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=None, body=[Pass()])])"
        <<< with x as y :
        ...     pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=Name(id='y', ctx=Store()), body=[Pass()])])"
        """
        if len(st) == 5 :
            return ast.With(lineno=st.srow, col_offset=st.scol,
                            context_expr=self.do(st[1], ctx),
                            optional_vars=self.do(st[2], ast.Store),
                            body=self.do(st[4], ctx))
        else :
            return ast.With(lineno=st.srow, col_offset=st.scol,
                            context_expr=self.do(st[1], ctx),
                            optional_vars=None,
                            body=self.do(st[3], ctx))
    def do_with_var (self, st, ctx=ast.Load) :
        """with_var: 'as' expr
        -> ast.Name

        <<< with x as y : pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=Name(id='y', ctx=Store()), body=[Pass()])])"
        """
        return self.do(st[1], ctx)
    def do_except_clause (self, st, ctx=ast.Load) :
        """except_clause: 'except' [test ['as' NAME]]
        -> ast.AST?, ast.Name?

        <<< try : pass
        ... except NameError : pass
        ... except TypeError as err : pass
        ... except : pass
        "Module(body=[TryExcept(body=[Pass()], handlers=[ExceptHandler(type=Name(id='NameError', ctx=Load()), name=None, body=[Pass()]), ExceptHandler(type=Name(id='TypeError', ctx=Load()), name=Name(id='err', ctx=Store()), body=[Pass()]), ExceptHandler(type=None, name=None, body=[Pass()])], orelse=[])])"
        """
        if len(st) == 1 :
            return None, None
        elif len(st) == 2 :
            return self.do(st[1], ctx), None
        else :
            return self.do(st[1], ctx), ast.Name(lineno=st[3].srow,
                                                 col_offset=st[3].scol,
                                                 id=st[3].text,
                                                 ctx=ast.Store())
    def do_suite (self, st, ctx=ast.Load) :
        """suite: simple_stmt | NEWLINE INDENT stmt+ DEDENT
        -> ast.AST+

        <<< with x : pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=None, body=[Pass()])])"
        <<< with x :
        ...     pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=None, body=[Pass()])])"
        <<< with x :
        ...     pass
        ...     pass
        "Module(body=[With(context_expr=Name(id='x', ctx=Load()), optional_vars=None, body=[Pass(), Pass()])])"
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return reduce(operator.add,
                          (self.do(child, ctx) for child in st[2:-1]),
                          [])
    def do_test (self, st, ctx=ast.Load) :
        """test: or_test ['if' or_test 'else' test] | lambdef
        -> ast.AST

        <<< 3
        'Module(body=[Expr(value=Num(n=3))])'
        <<< 3 if x else 4
        "Module(body=[Expr(value=IfExp(test=Name(id='x', ctx=Load()), body=Num(n=3), orelse=Num(n=4)))])"
        <<< lambda x : x+1
        "Module(body=[Expr(value=Lambda(args=arguments(args=[arg(arg='x', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Num(n=1))))])"
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return ast.IfExp(lineno=st.srow, col_offset=st.scol,
                             test=self.do(st[2], ctx),
                             body=self.do(st[0], ctx),
                             orelse=self.do(st[4], ctx))
    def do_test_nocond (self, st, ctx=ast.Load) :
        """test_nocond: or_test | lambdef_nocond
        -> ast.AST

        <<< [x for x in (lambda: True, lambda: False) if x()]
        "Module(body=[Expr(value=ListComp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Tuple(elts=[Lambda(args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=Name(id='True', ctx=Load())), Lambda(args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=Name(id='False', ctx=Load()))], ctx=Load()), ifs=[Call(func=Name(id='x', ctx=Load()), args=[], keywords=[], starargs=None, kwargs=None)])]))])"
        """
        return self.do(st[0], ctx)
    def do_lambdef (self, st, ctx=ast.Load) :
        """lambdef: 'lambda' [varargslist] ':' test
        -> ast.Lambda

        <<< lambda : True
        "Module(body=[Expr(value=Lambda(args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=Name(id='True', ctx=Load())))])"
        <<< lambda x : x+1
        "Module(body=[Expr(value=Lambda(args=arguments(args=[arg(arg='x', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Num(n=1))))])"
        """
        if len(st) == 3 :
            return ast.Lambda(lineno=st.srow, col_offset=st.scol,
                              args=ast.arguments(lineno=st.srow,
                                                 col_offset=st.scol,
                                                 args=[], vararg=None,
                                                 varargannotation=None,
                                                 kwonlyargs=[], kwarg=None,
                                                 kwargannotation=None,
                                                 defaults=[], kw_defaults=[]),
                              body=self.do(st[-1], ctx))
        else :
            return ast.Lambda(lineno=st.srow, col_offset=st.scol,
                              args=self.do(st[1], ctx),
                              body=self.do(st[-1], ctx))
    def do_lambdef_nocond (self, st, ctx=ast.Load) :
        """lambdef_nocond: 'lambda' [varargslist] ':' test_nocond
        -> ast.Lambda

        <<< [x for x in l if lambda y : x]
        "Module(body=[Expr(value=ListComp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[Lambda(args=arguments(args=[arg(arg='y', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=Name(id='x', ctx=Load()))])]))])"
        """
        tree = self.do_lambdef(st, ctx)
        tree.st = st
        return tree
    def do_or_test (self, st, ctx=ast.Load) :
        """or_test: and_test ('or' and_test)*
        -> ast.AST

        <<< x or y
        "Module(body=[Expr(value=BoolOp(op=Or(), values=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load())]))])"
        <<< x or y or z
        "Module(body=[Expr(value=BoolOp(op=Or(), values=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load()), Name(id='z', ctx=Load())]))])"
        """
        return self._do_boolean(st, ctx)
    def do_and_test (self, st, ctx=ast.Load) :
        """and_test: not_test ('and' not_test)*
        -> ast.AST

        <<< x and y
        "Module(body=[Expr(value=BoolOp(op=And(), values=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load())]))])"
        <<< x and y and z
        "Module(body=[Expr(value=BoolOp(op=And(), values=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load()), Name(id='z', ctx=Load())]))])"
        """
        return self._do_boolean(st, ctx)
    def do_not_test (self, st, ctx=ast.Load) :
        """not_test: 'not' not_test | comparison
        -> ast.AST

        <<< not x
        "Module(body=[Expr(value=UnaryOp(op=Not(), operand=Name(id='x', ctx=Load())))])"
        <<< not not x
        "Module(body=[Expr(value=UnaryOp(op=Not(), operand=UnaryOp(op=Not(), operand=Name(id='x', ctx=Load()))))])"
        """
        return self._do_unary(st, ctx)
    def do_comparison (self, st, ctx=ast.Load) :
        """comparison: star_expr (comp_op star_expr)*
        -> ast.AST

        <<< *x < *y <= *z
        "Module(body=[Expr(value=Compare(left=Starred(value=Name(id='x', ctx=Load()), ctx=Load()), ops=[Lt(), LtE()], comparators=[Starred(value=Name(id='y', ctx=Load()), ctx=Load()), Starred(value=Name(id='z', ctx=Load()), ctx=Load())]))])"
        <<< x < y <= z
        "Module(body=[Expr(value=Compare(left=Name(id='x', ctx=Load()), ops=[Lt(), LtE()], comparators=[Name(id='y', ctx=Load()), Name(id='z', ctx=Load())]))])"
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return ast.Compare(lineno=st.srow, col_offset=st.scol,
                               left=self.do(st[0], ctx),
                               ops = [self.do(child, ctx)
                                      for child in st[1::2]],
                               comparators = [self.do(child, ctx)
                                              for child in st[2::2]])
    _comparison = {"<" : ast.Lt,
                   ">" : ast.Gt,
                   "==" : ast.Eq,
                   ">=" : ast.GtE,
                   "<=" : ast.LtE,
                   "!=" : ast.NotEq,
                   "<>" : ast.NotEq,
                   "in" : ast.In,
                   "not in" : ast.NotIn,
                   "is" : ast.Is,
                   "is not" : ast.IsNot}
    def do_comp_op (self, st, ctx=ast.Load) :
        """comp_op: '<'|'>'|'=='|'>='|'<='|'!='|'<>'|'in'|'not' 'in'|'is'
                |'is' 'not'
        -> ast.cmpop

        <<< 1 < 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[Lt()], comparators=[Num(n=2)]))])'
        <<< 1 > 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[Gt()], comparators=[Num(n=2)]))])'
        <<< 1 == 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[Eq()], comparators=[Num(n=2)]))])'
        <<< 1 >= 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[GtE()], comparators=[Num(n=2)]))])'
        <<< 1 <= 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[LtE()], comparators=[Num(n=2)]))])'
        <<< 1 != 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[NotEq()], comparators=[Num(n=2)]))])'
        <<< 1 <> 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[NotEq()], comparators=[Num(n=2)]))])'
        <<< 1 in 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[In()], comparators=[Num(n=2)]))])'
        <<< 1 not in 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[NotIn()], comparators=[Num(n=2)]))])'
        <<< 1 is 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[Is()], comparators=[Num(n=2)]))])'
        <<< 1 is not 2
        'Module(body=[Expr(value=Compare(left=Num(n=1), ops=[IsNot()], comparators=[Num(n=2)]))])'
        """
        text = " ".join(child.text for child in st)
        return self._comparison[text](lineno=st.srow, col_offset=st.scol)
    def do_star_expr (self, st, ctx=ast.Load) :
        """star_expr: ['*'] expr
        -> ast.AST

        <<< x
        "Module(body=[Expr(value=Name(id='x', ctx=Load()))])"
        <<< *x
        "Module(body=[Expr(value=Starred(value=Name(id='x', ctx=Load()), ctx=Load()))])"
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return ast.Starred(lineno=st.srow, col_offset=st.scol,
                               value=self.do(st[1], ctx),
                               ctx=ctx())
    def do_expr (self, st, ctx=ast.Load) :
        """expr: xor_expr ('|' xor_expr)*
        -> ast.AST

        <<< 1
        'Module(body=[Expr(value=Num(n=1))])'
        <<< 1 | 2
        'Module(body=[Expr(value=BinOp(left=Num(n=1), op=BitOr(), right=Num(n=2)))])'
        <<< 1 | 2 | 3
        'Module(body=[Expr(value=BinOp(left=BinOp(left=Num(n=1), op=BitOr(), right=Num(n=2)), op=BitOr(), right=Num(n=3)))])'
        """
        return self._do_binary(st, ctx)
    def do_xor_expr (self, st, ctx=ast.Load) :
        """xor_expr: and_expr ('^' and_expr)*
        -> ast.AST

        <<< 1
        'Module(body=[Expr(value=Num(n=1))])'
        <<< 1 ^ 2
        'Module(body=[Expr(value=BinOp(left=Num(n=1), op=BitXor(), right=Num(n=2)))])'
        <<< 1 ^ 2 ^ 3
        'Module(body=[Expr(value=BinOp(left=BinOp(left=Num(n=1), op=BitXor(), right=Num(n=2)), op=BitXor(), right=Num(n=3)))])'
        """
        return self._do_binary(st, ctx)
    def do_and_expr (self, st, ctx=ast.Load) :
        """and_expr: shift_expr ('&' shift_expr)*
        -> ast.AST

        <<< 1
        'Module(body=[Expr(value=Num(n=1))])'
        <<< 1 & 2
        'Module(body=[Expr(value=BinOp(left=Num(n=1), op=BitAnd(), right=Num(n=2)))])'
        <<< 1 & 2 & 3
        'Module(body=[Expr(value=BinOp(left=BinOp(left=Num(n=1), op=BitAnd(), right=Num(n=2)), op=BitAnd(), right=Num(n=3)))])'
        """
        return self._do_binary(st, ctx)
    def do_shift_expr (self, st, ctx=ast.Load) :
        """shift_expr: arith_expr (('<<'|'>>') arith_expr)*
        -> ast.AST

        <<< 1
        'Module(body=[Expr(value=Num(n=1))])'
        <<< 1 << 2
        'Module(body=[Expr(value=BinOp(left=Num(n=1), op=LShift(), right=Num(n=2)))])'
        <<< 1 << 2 >> 3
        'Module(body=[Expr(value=BinOp(left=BinOp(left=Num(n=1), op=LShift(), right=Num(n=2)), op=RShift(), right=Num(n=3)))])'
        """
        return self._do_binary(st, ctx)
    def do_arith_expr (self, st, ctx=ast.Load) :
        """arith_expr: term (('+'|'-') term)*
        -> ast.AST

        <<< 1
        'Module(body=[Expr(value=Num(n=1))])'
        <<< 1 + 2
        'Module(body=[Expr(value=BinOp(left=Num(n=1), op=Add(), right=Num(n=2)))])'
        <<< 1 + 2 - 3
        'Module(body=[Expr(value=BinOp(left=BinOp(left=Num(n=1), op=Add(), right=Num(n=2)), op=Sub(), right=Num(n=3)))])'
        """
        return self._do_binary(st, ctx)
    def do_term (self, st, ctx=ast.Load) :
        """term: factor (('*'|'/'|'%'|'//') factor)*
        -> ast.AST

        <<< 1
        'Module(body=[Expr(value=Num(n=1))])'
        <<< 1 * 2
        'Module(body=[Expr(value=BinOp(left=Num(n=1), op=Mult(), right=Num(n=2)))])'
        <<< 1 * 2 / 3
        'Module(body=[Expr(value=BinOp(left=BinOp(left=Num(n=1), op=Mult(), right=Num(n=2)), op=Div(), right=Num(n=3)))])'
        <<< 1 * 2 / 3 % 4
        'Module(body=[Expr(value=BinOp(left=BinOp(left=BinOp(left=Num(n=1), op=Mult(), right=Num(n=2)), op=Div(), right=Num(n=3)), op=Mod(), right=Num(n=4)))])'
        <<< 1 * 2 / 3 % 4 // 5
        'Module(body=[Expr(value=BinOp(left=BinOp(left=BinOp(left=BinOp(left=Num(n=1), op=Mult(), right=Num(n=2)), op=Div(), right=Num(n=3)), op=Mod(), right=Num(n=4)), op=FloorDiv(), right=Num(n=5)))])'
        """
        return self._do_binary(st, ctx)
    def do_factor (self, st, ctx=ast.Load) :
        """factor: ('+'|'-'|'~') factor | power
        -> ast.AST

        <<< 1
        'Module(body=[Expr(value=Num(n=1))])'
        <<< +1
        'Module(body=[Expr(value=UnaryOp(op=UAdd(), operand=Num(n=1)))])'
        <<< -1
        'Module(body=[Expr(value=Num(n=-1))])'
        <<< ~1
        'Module(body=[Expr(value=UnaryOp(op=Invert(), operand=Num(n=1)))])'
        <<< +-1
        'Module(body=[Expr(value=UnaryOp(op=UAdd(), operand=Num(n=-1)))])'
        <<< -+1
        'Module(body=[Expr(value=UnaryOp(op=USub(), operand=UnaryOp(op=UAdd(), operand=Num(n=1))))])'
        <<< +-~1
        'Module(body=[Expr(value=UnaryOp(op=UAdd(), operand=UnaryOp(op=USub(), operand=UnaryOp(op=Invert(), operand=Num(n=1)))))])'
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            tree = self._do_unary(st, ctx)
            if (isinstance(tree.op, ast.USub)
                and isinstance(tree.operand, ast.Num)
                and tree.operand.n > 0) :
                tree = ast.Num(lineno=st.srow, col_offset=st.scol,
                               n = -tree.operand.n)
            return tree
    def do_power (self, st, ctx=ast.Load) :
        """power: atom trailer* ['**' factor]
        -> ast.AST

        <<< 1 ** 2
        'Module(body=[Expr(value=BinOp(left=Num(n=1), op=Pow(), right=Num(n=2)))])'
        <<< a.b ** 2
        "Module(body=[Expr(value=BinOp(left=Attribute(value=Name(id='a', ctx=Load()), attr='b', ctx=Load()), op=Pow(), right=Num(n=2)))])"
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            left = self.do(st[0], ctx)
            power = None
            for child in st[1:] :
                if child.text == "**" :
                    power = self.do(st[-1], ctx)
                    break
                trailer = self.do(child, ctx)
                left = trailer(left, st.srow, st.scol)
            if power :
                return ast.BinOp(lineno=st.srow, col_offset=st.scol,
                                 left=left,
                                 op=ast.Pow(lineno=st[-2].srow,
                                            col_offset=st[-2].scol),
                                 right=power)
            else :
                return left
    def do_atom (self, st, ctx=ast.Load) :
        """atom: ('(' [yield_expr|testlist_comp] ')' |
            '[' [testlist_comp] ']' |
            '{' [dictorsetmaker] '}' |
            NAME | NUMBER | STRING+ | '...' | 'None' | 'True' | 'False')
        -> ast.AST

        <<< foo
        "Module(body=[Expr(value=Name(id='foo', ctx=Load()))])"
        <<< True
        "Module(body=[Expr(value=Name(id='True', ctx=Load()))])"
        <<< 42
        'Module(body=[Expr(value=Num(n=42))])'
        <<< 1.5
        'Module(body=[Expr(value=Num(n=1.5))])'
        <<< 'hello'
        "Module(body=[Expr(value=Str(s='hello'))])"
        <<< 'hello' 'world'
        "Module(body=[Expr(value=Str(s='helloworld'))])"
        <<< '''hello
        ... world'''
        "Module(body=[Expr(value=Str(s='hello\\\\nworld'))])"
        <<< [1, 2, 3]
        'Module(body=[Expr(value=List(elts=[Num(n=1), Num(n=2), Num(n=3)], ctx=Load()))])'
        <<< [x for x in l]
        "Module(body=[Expr(value=ListComp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[])]))])"
        <<< (1, 2, 3)
        'Module(body=[Expr(value=Tuple(elts=[Num(n=1), Num(n=2), Num(n=3)], ctx=Load()))])'
        <<< (1,)
        'Module(body=[Expr(value=Tuple(elts=[Num(n=1)], ctx=Load()))])'
        <<< (1)
        'Module(body=[Expr(value=Num(n=1))])'
        <<< (x for x in l)
        "Module(body=[Expr(value=GeneratorExp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[])]))])"
        <<< {1, 2, 3}
        'Module(body=[Expr(value=Set(elts=[Num(n=1), Num(n=2), Num(n=3)]))])'
        <<< {x for x in l}
        "Module(body=[Expr(value=SetComp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[])]))])"
        <<< {1:2, 3:4}
        'Module(body=[Expr(value=Dict(keys=[Num(n=1), Num(n=3)], values=[Num(n=2), Num(n=4)]))])'
        <<< {x:y for x, y in l}
        "Module(body=[Expr(value=DictComp(key=Name(id='x', ctx=Load()), value=Name(id='y', ctx=Load()), generators=[comprehension(target=Tuple(elts=[Name(id='x', ctx=Store()), Name(id='y', ctx=Store())], ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[])]))])"
        """
        kind, text = st[0].kind, st[0].text
        if kind == self.NUMBER :
            return ast.Num(lineno=st.srow, col_offset=st.scol,
                           n=ast.literal_eval(text))
        elif kind == self.NAME :
            return ast.Name(lineno=st.srow, col_offset=st.scol,
                            id=text, ctx=ctx())
        elif kind == self.STRING :
            return ast.Str(lineno=st.srow, col_offset=st.scol,
                           s="".join(ast.literal_eval(child.text)
                                     for child in st))
        elif text == "..." :
            return ast.Ellipsis(lineno=st.srow, col_offset=st.scol)
        elif text == "[" :
            if len(st) == 2 :
                return ast.List(lineno=st.srow, col_offset=st.scol,
                                elts=[], ctx=ctx())
            else :
                loop, elts, atom = self.do(st[1], ctx)
                if atom is not None :
                    elts=[atom]
                if loop is None :
                    return ast.List(lineno=st.srow, col_offset=st.scol,
                                    elts=elts, ctx=ctx())
                else :
                    return ast.ListComp(lineno=st.srow, col_offset=st.scol,
                                        elt=loop, generators=elts)
        elif text == "(" :
            if len(st) == 2 :
                return ast.Tuple(lineno=st.srow, col_offset=st.scol,
                                 elts=[], ctx=ctx())
            elif st[1].symbol == "yield_expr" :
                return self.do(st[1], ctx)
            else :
                loop, elts, atom = self.do(st[1], ctx)
                if atom is not None :
                    return atom
                elif loop is None :
                    return ast.Tuple(lineno=st.srow, col_offset=st.scol,
                                     elts=elts, ctx=ctx())
                else :
                    return ast.GeneratorExp(lineno=st.srow, col_offset=st.scol,
                                            elt=loop, generators=elts)
        else : # text == "{"
            if len(st) == 2 :
                return ast.Dict(lineno=st.srow, col_offset=st.scol,
                                keys=[], values=[])
            else :
                return self.do(st[1], ctx)
    def do_testlist_comp (self, st, ctx=ast.Load) :
        """testlist_comp: test ( comp_for | (',' test)* [','] )
        -> ast.AST?, ast.AST+

        <<< [1, 2, 3]
        'Module(body=[Expr(value=List(elts=[Num(n=1), Num(n=2), Num(n=3)], ctx=Load()))])'
        <<< [x for x in l]
        "Module(body=[Expr(value=ListComp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[])]))])"
        """
        if len(st) == 1 :
            return None, None, self.do(st[0])
        elif st[1].text == "," :
            return None, [self.do(child, ctx) for child in st[::2]], None
        else :
            return self.do(st[0], ctx), self.do(st[1], ctx)[0], None
    def do_trailer (self, st, ctx=ast.Load) :
        """trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME
        -> (tree, line, column -> ast.AST)

        <<< a.b
        "Module(body=[Expr(value=Attribute(value=Name(id='a', ctx=Load()), attr='b', ctx=Load()))])"
        <<< a.b.c
        "Module(body=[Expr(value=Attribute(value=Attribute(value=Name(id='a', ctx=Load()), attr='b', ctx=Load()), attr='c', ctx=Load()))])"
        <<< a.b[c].d
        "Module(body=[Expr(value=Attribute(value=Subscript(value=Attribute(value=Name(id='a', ctx=Load()), attr='b', ctx=Load()), slice=Index(value=Name(id='c', ctx=Load())), ctx=Load()), attr='d', ctx=Load()))])"
        <<< f()
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[], keywords=[], starargs=None, kwargs=None))])"
        <<< f(x)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[Name(id='x', ctx=Load())], keywords=[], starargs=None, kwargs=None))])"
        <<< f(x, *l, y=2)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[Name(id='x', ctx=Load())], keywords=[keyword(arg='y', value=Num(n=2))], starargs=Name(id='l', ctx=Load()), kwargs=None))])"
        <<< f(x, *l, y=2, **d)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[Name(id='x', ctx=Load())], keywords=[keyword(arg='y', value=Num(n=2))], starargs=Name(id='l', ctx=Load()), kwargs=Name(id='d', ctx=Load())))])"
        <<< f(*l)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[], keywords=[], starargs=Name(id='l', ctx=Load()), kwargs=None))])"
        <<< f(**d)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[], keywords=[], starargs=None, kwargs=Name(id='d', ctx=Load())))])"
        <<< f(x)(a=1, b=2)
        "Module(body=[Expr(value=Call(func=Call(func=Name(id='f', ctx=Load()), args=[Name(id='x', ctx=Load())], keywords=[], starargs=None, kwargs=None), args=[], keywords=[keyword(arg='a', value=Num(n=1)), keyword(arg='b', value=Num(n=2))], starargs=None, kwargs=None))])"
        """
        hd = st[0].text
        if hd == "." :
            def trail (tree, lineno, col_offset) :
                return ast.Attribute(lineno=lineno, col_offset=col_offset,
                                     value=tree,
                                     attr=st[1].text,
                                     ctx=ctx())
        elif hd == "[" :
            subscript = self.do(st[1], ctx)
            if len(subscript) == 1 :
                subscript = subscript[0]
            else :
                subscript = ast.ExtSlice(lineno=st[1].srow,
                                         col_offset=st[1].scol,
                                         dims=subscript,
                                         ctx=ctx())
            def trail (tree, lineno, col_offset) :
                return ast.Subscript(lineno=lineno, col_offset=col_offset,
                                     value=tree,
                                     slice=subscript,
                                     ctx=ctx())
        elif len(st) == 2 : # hd = "("
            def trail (tree, lineno, col_offset) :
                return ast.Call(lineno=lineno, col_offset=col_offset,
                                func=tree, args=[], keywords=[],
                                starargs=None, kwargs=None)
        else : # hd = "("
            def trail (tree, lineno, col_offset) :
                args, keywords, starargs, kwargs = self.do(st[1], ctx)
                return ast.Call(lineno=lineno, col_offset=col_offset,
                                func=tree, args=args, keywords=keywords,
                                starargs=starargs, kwargs=kwargs)
        return trail
    def do_subscriptlist (self, st, ctx=ast.Load) :
        """subscriptlist: subscript (',' subscript)* [',']
        -> ast.Slice+

        <<< l[:]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=None, step=None), ctx=Load()))])"
        <<< l[1:]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=None, step=None), ctx=Load()))])"
        <<< l[1::]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=None, step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[1:2:]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=Num(n=2), step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[1:2:3]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=Num(n=2), step=Num(n=3)), ctx=Load()))])"
        <<< l[::]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=None, step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[:2:]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=Num(n=2), step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[:2:3]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=Num(n=2), step=Num(n=3)), ctx=Load()))])"
        <<< l[::3]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=None, step=Num(n=3)), ctx=Load()))])"
        <<< l[1:2:3,4:5:6]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=ExtSlice(dims=[Slice(lower=Num(n=1), upper=Num(n=2), step=Num(n=3)), Slice(lower=Num(n=4), upper=Num(n=5), step=Num(n=6))]), ctx=Load()))])"
        """
        return [self.do(child, ctx) for child in st[::2]]
    def do_subscript (self, st, ctx=ast.Load) :
        """subscript: test | [test] ':' [test] [sliceop]
        -> ast.Slice | ast.Index

        <<< l[:]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=None, step=None), ctx=Load()))])"
        <<< l[1:]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=None, step=None), ctx=Load()))])"
        <<< l[1::]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=None, step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[1:2:]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=Num(n=2), step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[1:2:3]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=Num(n=2), step=Num(n=3)), ctx=Load()))])"
        <<< l[::]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=None, step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[:2:]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=Num(n=2), step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[:2:3]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=Num(n=2), step=Num(n=3)), ctx=Load()))])"
        <<< l[::3]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=None, step=Num(n=3)), ctx=Load()))])"
        """
        count = len(st)
        if count == 1 and st[0].text == ":" :
            return ast.Slice(lineno=st.srow, col_offset=st.scol,
                             lower=None, upper=None, step=None)
        elif count == 1 :
            return ast.Index(lineno=st.srow, col_offset=st.scol,
                             value=self.do(st[0], ctx))
        elif count == 4 :
            return ast.Slice(lineno=st.srow, col_offset=st.scol,
                             lower=self.do(st[0], ctx),
                             upper=self.do(st[2], ctx),
                             step=self.do(st[3], ctx))
        elif count == 3 and st[-1].symbol == "test" :
            return ast.Slice(lineno=st.srow, col_offset=st.scol,
                             lower=self.do(st[0], ctx),
                             upper=self.do(st[2], ctx),
                             step=None)
        elif count == 3 and st[0].text == ":" :
            return ast.Slice(lineno=st.srow, col_offset=st.scol,
                             lower=None,
                             upper=self.do(st[1], ctx),
                             step=self.do(st[2], ctx))
        elif count == 3 :
            return ast.Slice(lineno=st.srow, col_offset=st.scol,
                             lower=self.do(st[0], ctx),
                             upper=None,
                             step=self.do(st[2], ctx))
        elif count == 2 and st[-1].symbol == "sliceop" :
            return ast.Slice(lineno=st.srow, col_offset=st.scol,
                             lower=None,
                             upper=None,
                             step=self.do(st[1], ctx))
        elif count == 2 and st[0].text == ":" :
            return ast.Slice(lineno=st.srow, col_offset=st.scol,
                             lower=None,
                             upper=self.do(st[1], ctx),
                             step=None)
        else :
            return ast.Slice(lineno=st.srow, col_offset=st.scol,
                             lower=self.do(st[0], ctx),
                             upper=None,
                             step=None)
    def do_sliceop (self, st, ctx=ast.Load) :
        """sliceop: ':' [test]
        -> ast.AST

        <<< l[1::]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=Num(n=1), upper=None, step=Name(id='None', ctx=Load())), ctx=Load()))])"
        <<< l[::3]
        "Module(body=[Expr(value=Subscript(value=Name(id='l', ctx=Load()), slice=Slice(lower=None, upper=None, step=Num(n=3)), ctx=Load()))])"
        """
        if len(st) == 1 :
            return ast.Name(lineno=st.srow, col_offset=st.scol,
                            id="None", ctx=ctx())
        else :
            return self.do(st[1], ctx)
    def do_exprlist (self, st, ctx=ast.Load) :
        """exprlist: star_expr (',' star_expr)* [',']
        -> ast.AST+

        <<< del x
        "Module(body=[Delete(targets=[Name(id='x', ctx=Del())])])"
        <<< del x, y
        "Module(body=[Delete(targets=[Name(id='x', ctx=Del()), Name(id='y', ctx=Del())])])"
        """
        tree = self.do_testlist(st, ctx)
        tree.st = st
        return tree
    def do_testlist (self, st, ctx=ast.Load) :
        """testlist: test (',' test)* [',']
        -> ast.AST | ast.Tuple

        <<< 1
        'Module(body=[Expr(value=Num(n=1))])'
        <<< 1, 2
        'Module(body=[Expr(value=Tuple(elts=[Num(n=1), Num(n=2)], ctx=Load()))])'
        """
        lst = [self.do(child, ctx) for child in st[::2]]
        if len(lst) == 1 :
            return lst[0]
        else :
            return ast.Tuple(lineno=st.srow, col_offset=st.scol,
                             elts=lst, ctx=ctx())
    def do_dictorsetmaker (self, st, ctx=ast.Load) :
        """dictorsetmaker: ( (test ':' test (comp_for | (',' test ':' test)* [','])) |
                  (test (comp_for | (',' test)* [','])) )
        -> ast.Dict | ast.DictComp | ast.Set | ast.SetComp

        <<< {1, 2, 3}
        'Module(body=[Expr(value=Set(elts=[Num(n=1), Num(n=2), Num(n=3)]))])'
        <<< {x for x in l}
        "Module(body=[Expr(value=SetComp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[])]))])"
        <<< {1:2, 3:4}
        'Module(body=[Expr(value=Dict(keys=[Num(n=1), Num(n=3)], values=[Num(n=2), Num(n=4)]))])'
        <<< {x:y for x, y in l}
        "Module(body=[Expr(value=DictComp(key=Name(id='x', ctx=Load()), value=Name(id='y', ctx=Load()), generators=[comprehension(target=Tuple(elts=[Name(id='x', ctx=Store()), Name(id='y', ctx=Store())], ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[])]))])"
        """
        if st[1].text == ":" :
            if st[3].text == "," :
                return ast.Dict(lineno=st.srow, col_offset=st.scol,
                                keys=[self.do(child, ctx)
                                      for child in st[::4]],
                                values=[self.do(child, ctx)
                                        for child in st[2::4]])
            else :
                return ast.DictComp(lineno=st.srow, col_offset=st.scol,
                                    key=self.do(st[0], ctx),
                                    value=self.do(st[2], ctx),
                                    generators=self.do(st[3], ctx)[0])
        else :
            loop, elts, atom = self.do_testlist_comp(st, ctx)
            if loop is None :
                return ast.Set(lineno=st.srow, col_offset=st.scol,
                               elts=elts)
            else :
                return ast.SetComp(lineno=st.srow, col_offset=st.scol,
                                   elt=loop, generators=elts)
    def do_classdef (self, st, ctx=ast.Load) :
        """classdef: 'class' NAME ['(' [arglist] ')'] ':' suite
        -> ast.ClassDef

        <<< class c : pass
        "Module(body=[ClassDef(name='c', bases=[], keywords=[], starargs=None, kwargs=None, body=[Pass()], decorator_list=[])])"
        <<< class c () : pass
        "Module(body=[ClassDef(name='c', bases=[], keywords=[], starargs=None, kwargs=None, body=[Pass()], decorator_list=[])])"
        <<< class c (object, foo=bar) : pass
        "Module(body=[ClassDef(name='c', bases=[Name(id='object', ctx=Load())], keywords=[keyword(arg='foo', value=Name(id='bar', ctx=Load()))], starargs=None, kwargs=None, body=[Pass()], decorator_list=[])])"
        """
        if len(st) <= 6 :
            return ast.ClassDef(lineno=st.srow, col_offset=st.scol,
                                name=st[1].text,
                                bases=[],
                                keywords=[],
                                starargs=None,
                                kwargs=None,
                                body=self.do(st[-1], ctx),
                                decorator_list=[])
        else :
            args, keywords, starargs, kwargs = self.do(st[3], ctx)
            return ast.ClassDef(lineno=st.srow, col_offset=st.scol,
                                name=st[1].text,
                                bases=args,
                                keywords=keywords,
                                starargs=starargs,
                                kwargs=kwargs,
                                body=self.do(st[-1], ctx),
                                decorator_list=[])
    def do_arglist (self, st, ctx=ast.Load) :
        """arglist: (argument ',')* (argument [',']
                         |'*' test (',' argument)* [',' '**' test]
                         |'**' test)
        -> args=ast.AST*, keywords=ast.keyword*, starargs=ast.AST?, kwargs=ast.AST?

        <<< f(x)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[Name(id='x', ctx=Load())], keywords=[], starargs=None, kwargs=None))])"
        <<< f(x, *l, y=2)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[Name(id='x', ctx=Load())], keywords=[keyword(arg='y', value=Num(n=2))], starargs=Name(id='l', ctx=Load()), kwargs=None))])"
        <<< f(x, *l, y=2, **d)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[Name(id='x', ctx=Load())], keywords=[keyword(arg='y', value=Num(n=2))], starargs=Name(id='l', ctx=Load()), kwargs=Name(id='d', ctx=Load())))])"
        <<< f(*l)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[], keywords=[], starargs=Name(id='l', ctx=Load()), kwargs=None))])"
        <<< f(**d)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[], keywords=[], starargs=None, kwargs=Name(id='d', ctx=Load())))])"
        <<< f(x=1, y=2, x=3)
        Traceback (most recent call last):
          ...
        ParseError: ... keyword argument repeated
        """
        args = []
        keywords = []
        allkw = set()
        starargs = None
        kwargs = None
        nodes = [n for n in st if n.text != ","]
        while nodes :
            if nodes[0].text == "*" :
                starargs = self.do(nodes[1], ctx)
                del nodes[:2]
            elif nodes[0].text == "**" :
                kwargs = self.do(nodes[1], ctx)
                del nodes[:2]
            else :
                arg = self.do(nodes[0], ctx)
                if isinstance(arg, ast.keyword) :
                    if arg.arg in allkw :
                        raise ParseError(nodes[0].text,
                                         reason="keyword argument repeated")
                    keywords.append(arg)
                    allkw.add(arg.arg)
                elif starargs is not None :
                    raise ParseError(nodes[0].text, reason="only named"
                                     " arguments may follow *expression")
                else :
                    args.append(arg)
                del nodes[0]
        return args, keywords, starargs, kwargs
    def do_argument (self, st, ctx=ast.Load) :
        """argument: test [comp_for] | test '=' test
        -> ast.keyword | ast.GeneratorExp

        <<< f(x)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[Name(id='x', ctx=Load())], keywords=[], starargs=None, kwargs=None))])"
        <<< f(x=1)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[], keywords=[keyword(arg='x', value=Num(n=1))], starargs=None, kwargs=None))])"
        <<< f(x for x in l)
        "Module(body=[Expr(value=Call(func=Name(id='f', ctx=Load()), args=[GeneratorExp(elt=Name(id='x', ctx=Load()), generators=[comprehension(target=Name(id='x', ctx=Store()), iter=Name(id='l', ctx=Load()), ifs=[])])], keywords=[], starargs=None, kwargs=None))])"
        """
        test = self.do(st[0], ctx)
        if len(st) == 1 :
            return test
        elif len(st) == 3 :
            if not isinstance(test, ast.Name) :
                raise ParseError(st[0].text, reason="keyword can't be an"
                                 " expression")
            return ast.keyword(lineno=st.srow, col_offset=st.scol,
                               arg=test.id,
                               value=self.do(st[2], ctx))
        else :
            comp, ifs = self.do(st[1], ctx)
            return ast.GeneratorExp(lineno=st.srow, col_offset=st.scol,
                                    elt=test, generators=comp)
    def do_comp_iter (self, st, ctx=ast.Load) :
        """comp_iter: comp_for | comp_if
        -> comprehension*, ast.AST*

        <<< [a for b in c if d if e for f in g if h]
        "Module(body=[Expr(value=ListComp(elt=Name(id='a', ctx=Load()), generators=[comprehension(target=Name(id='b', ctx=Store()), iter=Name(id='c', ctx=Load()), ifs=[Name(id='d', ctx=Load()), Name(id='e', ctx=Load())]), comprehension(target=Name(id='f', ctx=Store()), iter=Name(id='g', ctx=Load()), ifs=[Name(id='h', ctx=Load())])]))])"
        """
        return self.do(st[0], ctx)
    def do_comp_for (self, st, ctx=ast.Load) :
        """comp_for: 'for' exprlist 'in' or_test [comp_iter]
        -> comprehension+, []

        <<< [a for b in c if d if e for f in g if h]
        "Module(body=[Expr(value=ListComp(elt=Name(id='a', ctx=Load()), generators=[comprehension(target=Name(id='b', ctx=Store()), iter=Name(id='c', ctx=Load()), ifs=[Name(id='d', ctx=Load()), Name(id='e', ctx=Load())]), comprehension(target=Name(id='f', ctx=Store()), iter=Name(id='g', ctx=Load()), ifs=[Name(id='h', ctx=Load())])]))])"
        """
        if len(st) == 4 :
            return [ast.comprehension(lineno=st.srow, col_offset=st.scol,
                                      target=self.do(st[1], ast.Store),
                                      iter=self.do(st[3], ctx),
                                      ifs=[])], []
        else :
            comp, ifs = self.do(st[4], ctx)
            return [ast.comprehension(lineno=st.srow, col_offset=st.scol,
                                      target=self.do(st[1], ast.Store),
                                      iter=self.do(st[3], ctx),
                                      ifs=ifs)] + comp, []
    def do_comp_if (self, st, ctx=ast.Load) :
        """comp_if: 'if' test_nocond [comp_iter]
        -> comprehension*, ast.AST+

        <<< [a for b in c if d if e for f in g if h]
        "Module(body=[Expr(value=ListComp(elt=Name(id='a', ctx=Load()), generators=[comprehension(target=Name(id='b', ctx=Store()), iter=Name(id='c', ctx=Load()), ifs=[Name(id='d', ctx=Load()), Name(id='e', ctx=Load())]), comprehension(target=Name(id='f', ctx=Store()), iter=Name(id='g', ctx=Load()), ifs=[Name(id='h', ctx=Load())])]))])"
        """
        if len(st) == 2 :
            return [], [self.do(st[1], ctx)]
        else :
            comp, ifs = self.do(st[2], ctx)
            return comp, [self.do(st[1], ctx)] + ifs
    def do_yield_expr (self, st, ctx=ast.Load) :
        """yield_expr: 'yield' [testlist]
        -> ast.Yield

        <<< yield
        'Module(body=[Expr(value=Yield(value=None))])'
        <<< yield 42
        'Module(body=[Expr(value=Yield(value=Num(n=42)))])'
        <<< yield 42, 43
        'Module(body=[Expr(value=Yield(value=Tuple(elts=[Num(n=42), Num(n=43)], ctx=Load())))])'
        """
        if len(st) == 2 :
            return ast.Yield(lineno=st.srow, col_offset=st.scol,
                             value=self.do(st[1], ctx))
        else :
            return ast.Yield(lineno=st.srow, col_offset=st.scol,
                             value=None)
    @classmethod
    def parse (cls, expr, mode="exec", filename="<string>") :
        tree = cls(cls.parser.parseString(expr.strip() + "\n",
                                          filename=filename)).ast
        if mode == "exec" :
            return tree
        elif mode == "eval" :
            if len(tree.body) > 1 or not isinstance(tree.body[0], ast.Expr) :
                raise ParseError(None, reason="invalid syntax")
            return ast.Expression(body=tree.body[0].value)
        elif mode == "single" :
            return ast.Interactive(body=tree.body)
        else :
            raise ValueError("arg 2 must be 'exec', 'eval' or 'single'")

parse = Translator.parse

class ParseTestParser (doctest.DocTestParser) :
    _EXAMPLE_RE = re.compile(r'''
        # Source consists of a PS1 line followed by zero or more PS2 lines.
        (?P<source>
            (?:^(?P<indent> [ ]*) <<<    .*)    # PS1 line
            (?:\n           [ ]*  \.\.\. .*)*)  # PS2 lines
        \n?
        # Want consists of any non-blank lines that do not start with PS1.
        (?P<want> (?:(?![ ]*$)    # Not a blank line
                     (?![ ]*<<<)  # Not a line starting with PS1
                     .*$\n?       # But any other line
                  )*)
        ''', re.MULTILINE | re.VERBOSE)
    def __init__ (self, translator) :
        self.Translator = translator
    def parse (self, string, name="<string>") :
        examples = doctest.DocTestParser.parse(self, string, name)
        try :
            rule = name.split(".do_", 1)[1]
        except :
            rule = None
        for i, exple in enumerate(examples) :
            if isinstance(exple, str) :
                continue
            elif name.split(".")[1] not in self.Translator.__dict__ :
                examples[i] = ("skipping example for another language: %r"
                               % exple.source)
                continue
            if rule is not None :
                source = exple.source.strip() + "\n"
                try :
                    tree = self.Translator.ParseTree(self.Translator.parser.parseString(source))
                except :
                    print("could not parse %r at %s:%s" % (source, name,
                                                           exple.lineno))
                    raise
                if not tree.involve(self.Translator.parser.stringMap[rule]) :
                    print(("test at %s:%s does not involve rule %s"
                           % (name, exple.lineno, rule)))
                    examples[i] = "<test skipped>"
                    continue
            examples[i] = doctest.Example(
                source=("ast.dump(parse(%r))") % exple.source,
                want=exple.want,
                exc_msg=exple.exc_msg,
                lineno=exple.lineno,
                indent=exple.indent,
                options=exple.options)
        return examples

def testparser (translator) :
    for rule in translator.parser.stringMap :
        try :
            assert "<<<" in getattr(translator, "do_" + rule).__doc__
        except AttributeError :
            print("missing handler for rule %r" % rule)
            continue
        except TypeError :
            print("missing doc for rule %r" % rule)
            continue
        except AssertionError :
            print("missing test for rule %r" % rule)
            continue
    finder = doctest.DocTestFinder(parser=ParseTestParser(translator))
    runner = doctest.DocTestRunner(optionflags=doctest.NORMALIZE_WHITESPACE
                                   | doctest.ELLIPSIS)
    for name, method in inspect.getmembers(translator, inspect.ismethod) :
        if not name.startswith("do_") :
            continue
        for test in finder.find(method, "%s.%s" % (translator.__name__, name)) :
            runner.run(test)
    runner.summarize()

if __name__ == "__main__" :
    testparser(Translator)
