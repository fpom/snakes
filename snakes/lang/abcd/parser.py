"""
>>> testparser(Translator)
"""

import operator, sys
import snakes
from snakes.lang.python.parser import (ParseTree, ParseTestParser,
                                       Translator as PyTranslator,
                                       ParseTree as PyParseTree,
                                       testparser)
from snakes.lang.pgen import ParseError
from snakes.lang.abcd.pgen import parser
import snakes.lang.abcd.asdl as ast

_symbols = parser.tokenizer.tok_name.copy()
# next statement overrides 'NT_OFFSET' entry with 'single_input'
# (this is desired)
_symbols.update(parser.symbolMap)

def skip (token) :
    if token.kind == token.lexer.COMMENT :
        words = token.strip().split()
        if words[:2] == ["#", "coding="] :
            coding = words[2]
        elif words[:3] == ["#", "-*-", "coding:"] :
            coding = words[3]
        else :
            return
        snakes.defaultencoding = coding

parser.tokenizer.skip_token = skip

class ParseTree (PyParseTree) :
    _symbols = _symbols

class Translator (PyTranslator) :
    ParseTree = ParseTree
    parser = parser
    ST = ast
    def do_file_input (self, st, ctx) :
        """file_input: abcd_main ENDMARKER
        -> ast.AbcdSpec

        <<< symbol FOO, BAR
        ... [egg+(spam) if spam == ham] ; [spam-(FOO, BAR)]
        "AbcdSpec(context=[AbcdSymbol(symbols=['FOO', 'BAR'])], body=AbcdFlowOp(left=AbcdAction(accesses=[SimpleAccess(buffer='egg', arc=Produce(), tokens=Name(id='spam', ctx=Load()))], guard=Compare(left=Name(id='spam', ctx=Load()), ops=[Eq()], comparators=[Name(id='ham', ctx=Load())])), op=Sequence(), right=AbcdAction(accesses=[SimpleAccess(buffer='spam', arc=Consume(), tokens=Tuple(elts=[Name(id='FOO', ctx=Load()), Name(id='BAR', ctx=Load())], ctx=Load()))], guard=Name(id='True', ctx=Load()))), asserts=[])"
        """
        return self.do(st[0])
    def do_abcd_main (self, st, ctx) :
        """abcd_main: (NEWLINE | abcd_global)* abcd_expr (abcd_prop)*
        -> ast.AbcdSpec

        <<< symbol FOO, BAR
        ... [egg+(spam) if spam == ham] ; [spam-(FOO, BAR)]
        "AbcdSpec(context=[AbcdSymbol(symbols=['FOO', 'BAR'])], body=AbcdFlowOp(left=AbcdAction(accesses=[SimpleAccess(buffer='egg', arc=Produce(), tokens=Name(id='spam', ctx=Load()))], guard=Compare(left=Name(id='spam', ctx=Load()), ops=[Eq()], comparators=[Name(id='ham', ctx=Load())])), op=Sequence(), right=AbcdAction(accesses=[SimpleAccess(buffer='spam', arc=Consume(), tokens=Tuple(elts=[Name(id='FOO', ctx=Load()), Name(id='BAR', ctx=Load())], ctx=Load()))], guard=Name(id='True', ctx=Load()))), asserts=[])"
        """
        expr = len(st)-1
        for i, child in enumerate(st) :
            if child.symbol == "abcd_expr" :
                expr = i
                break
        return self.ST.AbcdSpec(lineno=st.srow, col_offset=st.scol,
                                context=[self.do(child) for child in st[:expr]
                                         if child.kind != self.NEWLINE],
                                body=self.do(st[expr]),
                                asserts=[self.do(child) for child in st[expr+1:]])
    def do_abcd_prop (self, st, ctx) :
        """abcd_prop: 'assert' test (NEWLINE)*
        -> ast.test

        <<< [True]
        ... assert True
        ... assert False
        "AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[Name(id='True', ctx=Load()), Name(id='False', ctx=Load())])"
        """
        return self.do(st[1])
    def do_abcd_global (self, st, ctx) :
        """abcd_global: (import_stmt | abcd_symbol | abcd_typedef
               | abcd_const | abcd_decl)
        -> ast.AST

        <<< import module
        ... from module import content
        ... symbol EGG, SPAM, HAM
        ... typedef t : enum(EGG, SPAM, HAM)
        ... net Foo() : [True]
        ... buffer bar : t = ()
        ... [True]
        "AbcdSpec(context=[Import(names=[alias(name='module', asname=None)]), ImportFrom(module='module', names=[alias(name='content', asname=None)], level=0), AbcdSymbol(symbols=['EGG', 'SPAM', 'HAM']), AbcdTypedef(name='t', type=EnumType(items=[Name(id='EGG', ctx=Load()), Name(id='SPAM', ctx=Load()), Name(id='HAM', ctx=Load())])), AbcdNet(name='Foo', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[])), AbcdBuffer(name='bar', type=NamedType(name='t'), capacity=None, content=Tuple(elts=[], ctx=Load()))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        return self.do(st[0])
    def do_abcd_spec (self, st, ctx) :
        """abcd_spec: (NEWLINE | abcd_decl)* abcd_expr
        -> ast.AbcdSpec

        <<< net Foo () :
        ...     buffer bar : spam = ()
        ...     net Bar () : [False]
        ...     [True]
        ... Foo()
        "AbcdSpec(context=[AbcdNet(name='Foo', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[AbcdBuffer(name='bar', type=NamedType(name='spam'), capacity=None, content=Tuple(elts=[], ctx=Load())), AbcdNet(name='Bar', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=False), asserts=[]))], body=AbcdAction(accesses=[], guard=True), asserts=[]))], body=AbcdInstance(net='Foo', asname=None, args=[], keywords=[], starargs=None, kwargs=None), asserts=[])"
        """
        tree = self.do_abcd_main(st, ctx)
        tree.st = st
        return tree
    def do_abcd_decl (self, st, ctx) :
        """abcd_decl: abcd_net | abcd_task | abcd_buffer
        -> ast.AST

        <<< net Foo () :
        ...     buffer bar : spam = ()
        ...     net Bar () : [False]
        ...     [True]
        ... Foo()
        "AbcdSpec(context=[AbcdNet(name='Foo', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[AbcdBuffer(name='bar', type=NamedType(name='spam'), capacity=None, content=Tuple(elts=[], ctx=Load())), AbcdNet(name='Bar', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=False), asserts=[]))], body=AbcdAction(accesses=[], guard=True), asserts=[]))], body=AbcdInstance(net='Foo', asname=None, args=[], keywords=[], starargs=None, kwargs=None), asserts=[])"
        """
        tree = self.do_abcd_global(st, ctx)
        tree.st = st
        return tree
    def do_abcd_const (self, st, ctx) :
        """abcd_const: 'const' NAME '=' testlist
        -> ast.AbcdConst

        <<< const FOO = 5
        ... [True]
        "AbcdSpec(context=[AbcdConst(name='FOO', value=Num(n=5))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< const FOO = 1, 2, 3
        ... [True]
        "AbcdSpec(context=[AbcdConst(name='FOO', value=Tuple(elts=[Num(n=1), Num(n=2), Num(n=3)], ctx=Load()))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        return self.ST.AbcdConst(lineno=st.srow, col_offset=st.scol,
                                 name=st[1].text, value=self.do(st[3], ctx))
    def do_abcd_symbol (self, st, ctx) :
        """abcd_symbol: 'symbol' abcd_namelist
        -> ast.AbcdSymbol

        <<< symbol FOO
        ... [True]
        "AbcdSpec(context=[AbcdSymbol(symbols=['FOO'])], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< symbol FOO, BAR
        ... [True]
        "AbcdSpec(context=[AbcdSymbol(symbols=['FOO', 'BAR'])], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        return self.ST.AbcdSymbol(lineno=st.srow, col_offset=st.scol,
                                  symbols=self.do(st[1]))
    def do_abcd_namelist (self, st, ctx) :
        """abcd_namelist: NAME (',' NAME)*
        -> str+

        <<< symbol FOO
        ... [True]
        "AbcdSpec(context=[AbcdSymbol(symbols=['FOO'])], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< symbol FOO, BAR
        ... [True]
        "AbcdSpec(context=[AbcdSymbol(symbols=['FOO', 'BAR'])], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        return [child.text for child in st[::2]]
    def _do_flowop (self, st, op) :
        nodes = [self.do(child) for child in st[::2]]
        while len(nodes) > 1 :
            left = nodes.pop(0)
            right = nodes.pop(0)
            theop = op()
            theop.st = st[1]
            flow = self.ST.AbcdFlowOp(lineno=left.lineno,
                                      col_offset=left.col_offset,
                                      left=left, op=theop, right=right)
            flow.st = st
            nodes.insert(0, flow)
        return nodes[0]
    def do_abcd_expr (self, st, ctx) :
        """abcd_expr: abcd_choice_expr ('|' abcd_choice_expr)*
        -> ast.process

        <<< [True]
        'AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[])'
        <<< [True] | [False]
        'AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Parallel(), right=AbcdAction(accesses=[], guard=False)), asserts=[])'
        <<< [True] | [False] | [True]
        'AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Parallel(), right=AbcdAction(accesses=[], guard=False)), op=Parallel(), right=AbcdAction(accesses=[], guard=True)), asserts=[])'

        """
        return self._do_flowop(st, self.ST.Parallel)
    def do_abcd_choice_expr (self, st, ctx) :
        """abcd_choice_expr: abcd_iter_expr ('+' abcd_iter_expr)*
        -> ast.process

        <<< [True]
        'AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[])'
        <<< [True] + [False]
        'AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Choice(), right=AbcdAction(accesses=[], guard=False)), asserts=[])'
        <<< [True] + [False] + [True]
        'AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Choice(), right=AbcdAction(accesses=[], guard=False)), op=Choice(), right=AbcdAction(accesses=[], guard=True)), asserts=[])'
        """
        return self._do_flowop(st, self.ST.Choice)
    def do_abcd_iter_expr (self, st, ctx) :
        """abcd_iter_expr: abcd_seq_expr ('*' abcd_seq_expr)*
        -> ast.process

        <<< [True]
        'AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[])'
        <<< [True] * [False]
        'AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Loop(), right=AbcdAction(accesses=[], guard=False)), asserts=[])'
        <<< [True] * [False] * [True]
        'AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Loop(), right=AbcdAction(accesses=[], guard=False)), op=Loop(), right=AbcdAction(accesses=[], guard=True)), asserts=[])'
        """
        return self._do_flowop(st, self.ST.Loop)
    def do_abcd_seq_expr (self, st, ctx) :
        """abcd_seq_expr: abcd_base_expr (';' abcd_base_expr)*
        -> ast.process

        <<< [True]
        'AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[])'
        <<< [True] ; [False]
        'AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Sequence(), right=AbcdAction(accesses=[], guard=False)), asserts=[])'
        <<< [True] ; [False] ; [True]
        'AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Sequence(), right=AbcdAction(accesses=[], guard=False)), op=Sequence(), right=AbcdAction(accesses=[], guard=True)), asserts=[])'
        """
        return self._do_flowop(st, self.ST.Sequence)
    def do_abcd_base_expr (self, st, ctx) :
        """abcd_base_expr: (abcd_action | '(' abcd_expr ')') (NEWLINE)*
        -> ast.process

        <<< [True]
        'AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[])'
        <<< ([True])
        'AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[])'
        """
        if st[0].text == "(" :
            return self.do(st[1])
        else :
            return self.do(st[0])
    def do_abcd_action (self, st, ctx) :
        """abcd_action: ('[' 'True' ']' | '[' 'False' ']' |
                         '[' abcd_access_list ['if' test] ']' |
                         abcd_instance)
        -> ast.AbcdAction | ast.AbcdInstance

        <<< [True]
        'AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[])'
        <<< [False]
        'AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=False), asserts=[])'
        <<< Foo(1, 2)
        "AbcdSpec(context=[], body=AbcdInstance(net='Foo', asname=None, args=[Num(n=1), Num(n=2)], keywords=[], starargs=None, kwargs=None), asserts=[])"
        """
        if len(st) == 1 :
            return self.do(st[0])
        elif st[1].text == "True" :
            return self.ST.AbcdAction(lineno=st.srow, col_offset=st.scol,
                                      accesses=[], guard=True)
        elif st[1].text == "False" :
            return self.ST.AbcdAction(lineno=st.srow, col_offset=st.scol,
                                      accesses=[], guard=False)
        elif len(st) == 3 :
            return self.ST.AbcdAction(lineno=st.srow, col_offset=st.scol,
                                      accesses=self.do(st[1]),
                                      guard=self.ST.Name(lineno=st[-1].srow,
                                                         col_offset=st[-1].scol,
                                                         id="True",
                                                         ctx=self.ST.Load()))
        else :
            return self.ST.AbcdAction(lineno=st.srow, col_offset=st.scol,
                                      accesses=self.do(st[1]),
                                      guard=self.do(st[3]))
    def do_abcd_access_list (self, st, ctx) :
        """abcd_access_list: abcd_access (',' abcd_access)*
        -> ast.access+

        <<< [foo-(1)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[SimpleAccess(buffer='foo', arc=Consume(), tokens=Num(n=1))], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [foo-(1), bar+(2)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[SimpleAccess(buffer='foo', arc=Consume(), tokens=Num(n=1)), SimpleAccess(buffer='bar', arc=Produce(), tokens=Num(n=2))], guard=Name(id='True', ctx=Load())), asserts=[])"
        """
        return [self.do(child) for child in st[::2]]
    _arc = {"+" : ast.Produce,
            "-" : ast.Consume,
            "?" : ast.Test,
            "<<" : ast.Fill}
    def do_abcd_access (self, st, ctx) :
        """abcd_access: (NAME '+' '(' testlist ')' |
              NAME '?' '(' testlist ')' |
              NAME '-' '(' testlist ')' |
              NAME '<>' '(' testlist '=' testlist ')' |
              NAME '>>' '(' NAME ')' |
              NAME '<<' '(' testlist_comp ')' |
              NAME '.' NAME '(' test (',' test)* ')')
        -> ast.access

        <<< [egg+(x), spam-(y), ham?(z), foo<<(bar)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[SimpleAccess(buffer='egg', arc=Produce(), tokens=Name(id='x', ctx=Load())), SimpleAccess(buffer='spam', arc=Consume(), tokens=Name(id='y', ctx=Load())), SimpleAccess(buffer='ham', arc=Test(), tokens=Name(id='z', ctx=Load())), SimpleAccess(buffer='foo', arc=Fill(), tokens=Name(id='bar', ctx=Load()))], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [foo<<(spam(egg) for egg in ham)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[SimpleAccess(buffer='foo', arc=Fill(), tokens=ListComp(elt=Call(func=Name(id='spam', ctx=Load()), args=[Name(id='egg', ctx=Load())], keywords=[], starargs=None, kwargs=None), generators=[comprehension(target=Name(id='egg', ctx=Store()), iter=Name(id='ham', ctx=Load()), ifs=[])]))], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [bar-(l), foo<<(l)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[SimpleAccess(buffer='bar', arc=Consume(), tokens=Name(id='l', ctx=Load())), SimpleAccess(buffer='foo', arc=Fill(), tokens=Name(id='l', ctx=Load()))], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [bar-(l), foo<<(l,)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[SimpleAccess(buffer='bar', arc=Consume(), tokens=Name(id='l', ctx=Load())), SimpleAccess(buffer='foo', arc=Fill(), tokens=Tuple(elts=[Name(id='l', ctx=Load())], ctx=Load()))], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [spam>>(ham) if spam is egg]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[FlushAccess(buffer='spam', target='ham')], guard=Compare(left=Name(id='spam', ctx=Load()), ops=[Is()], comparators=[Name(id='egg', ctx=Load())])), asserts=[])"
        <<< [count<>(n = n+1)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[SwapAccess(buffer='count', target=Name(id='n', ctx=Load()), tokens=BinOp(left=Name(id='n', ctx=Load()), op=Add(), right=Num(n=1)))], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [foo.spawn(child, 1, 2, 3)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[Spawn(net='foo', pid=Name(id='child', ctx=Load()), args=[Num(n=1), Num(n=2), Num(n=3)])], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [foo.wait(child, y, z)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[Wait(net='foo', pid=Name(id='child', ctx=Load()), args=[Name(id='y', ctx=Load()), Name(id='z', ctx=Load())])], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [foo.suspend(pid)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[Suspend(net='foo', pid=Name(id='pid', ctx=Load()))], guard=Name(id='True', ctx=Load())), asserts=[])"
        <<< [foo.resume(pid)]
        "AbcdSpec(context=[], body=AbcdAction(accesses=[Resume(net='foo', pid=Name(id='pid', ctx=Load()))], guard=Name(id='True', ctx=Load())), asserts=[])"
        """
        if st[1].text in ("+", "?", "-") :
            return self.ST.SimpleAccess(lineno=st.srow, col_offset=st.scol,
                                        buffer=st[0].text,
                                        arc=self._arc[st[1].text](),
                                        tokens=self.do(st[3]))
        elif st[1].text == "<<" :
            loop, elts, atom = self.do(st[3], ctx)
            if atom is not None :
                args = atom
            elif loop is None :
                args = self.ST.Tuple(lineno=st.srow, col_offset=st.scol,
                                     elts=elts, ctx=ctx())
            else :
                args = self.ST.ListComp(lineno=st.srow, col_offset=st.scol,
                                        elt=loop, generators=elts)
            return self.ST.SimpleAccess(lineno=st.srow, col_offset=st.scol,
                                        buffer=st[0].text,
                                        arc=self._arc[st[1].text](),
                                        tokens=args)
        elif st[1].text == ">>" :
            return self.ST.FlushAccess(lineno=st.srow, col_offset=st.scol,
                                       buffer=st[0].text,
                                       target=st[3].text)
        elif st[1].text == "<>" :
            return self.ST.SwapAccess(lineno=st.srow, col_offset=st.scol,
                                      buffer=st[0].text,
                                      target=self.do(st[3]),
                                      tokens=self.do(st[5]))
        elif st[2].text in ("suspend", "resume") : # st[1].text == "."
            if len(st) > 6 :
                raise ParseError(st.text, reason="too many arguments for %s"
                                 % st[2].text)
            if st[2].text == "suspend" :
                tree = self.ST.Suspend
            else :
                tree = self.ST.Resume
            return tree(lineno=st.srow, col_offset=st.scol,
                        net=st[0].text,
                        pid=self.do(st[4]))
        elif st[2].text in ("spawn", "wait") : # st[1].text == "."
            if len(st) > 6 :
                args = [self.do(child) for child in st[6:-1:2]]
            else :
                args = []
            if st[2].text == "spawn" :
                tree = self.ST.Spawn
            else :
                tree = self.ST.Wait
            return tree(lineno=st.srow, col_offset=st.scol,
                        net=st[0].text,
                        pid=self.do(st[4]),
                        args=args)
        else :
            raise ParseError(st[2].text, reason=("expected 'spawn', 'wait', "
                             "'suspend' or 'resume', but found '%s'")
                             % st[2].text)
    def do_abcd_instance (self, st, ctx) :
        """abcd_instance: [NAME ':' ':'] NAME '(' [arglist] ')'
        -> ast.AbcdInstance

        <<< sub()
        "AbcdSpec(context=[], body=AbcdInstance(net='sub', asname=None, args=[], keywords=[], starargs=None, kwargs=None), asserts=[])"
        <<< sub(1, 2, 3)
        "AbcdSpec(context=[], body=AbcdInstance(net='sub', asname=None, args=[Num(n=1), Num(n=2), Num(n=3)], keywords=[], starargs=None, kwargs=None), asserts=[])"
        <<< sub(1, *l)
        "AbcdSpec(context=[], body=AbcdInstance(net='sub', asname=None, args=[Num(n=1)], keywords=[], starargs=Name(id='l', ctx=Load()), kwargs=None), asserts=[])"
        <<< sub(1, **d)
        "AbcdSpec(context=[], body=AbcdInstance(net='sub', asname=None, args=[Num(n=1)], keywords=[], starargs=None, kwargs=Name(id='d', ctx=Load())), asserts=[])"
        <<< sub(a=1, b=2)
        "AbcdSpec(context=[], body=AbcdInstance(net='sub', asname=None, args=[], keywords=[keyword(arg='a', value=Num(n=1)), keyword(arg='b', value=Num(n=2))], starargs=None, kwargs=None), asserts=[])"
        <<< foo::sub()
        "AbcdSpec(context=[], body=AbcdInstance(net='sub', asname='foo', args=[], keywords=[], starargs=None, kwargs=None), asserts=[])"
        <<< foo::sub(1, 2)
        "AbcdSpec(context=[], body=AbcdInstance(net='sub', asname='foo', args=[Num(n=1), Num(n=2)], keywords=[], starargs=None, kwargs=None), asserts=[])"
        """
        if len(st) in (3, 6) :
            args, keywords, starargs, kwargs = [], [], None, None
        else :
            args, keywords, starargs, kwargs = self.do(st[-2])
        if st[1].text == ':' :
            net = st[3].text
            asname = st[0].text
        else :
            net = st[0].text
            asname = None
        return self.ST.AbcdInstance(lineno=st.srow, col_offset=st.scol,
                                    net=net, asname=asname, args=args,
                                    keywords=keywords, starargs=starargs,
                                    kwargs=kwargs)
    def do_abcd_net (self, st, ctx) :
        """abcd_net: 'net' NAME parameters ':' abcd_suite
        -> ast.AbcdNet

        <<< net Foo () : [True]
        ... [False]
        "AbcdSpec(context=[AbcdNet(name='Foo', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[]))], body=AbcdAction(accesses=[], guard=False), asserts=[])"
        <<< net Foo (x, y) : [True]
        ... [False]
        "AbcdSpec(context=[AbcdNet(name='Foo', args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None)], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[]))], body=AbcdAction(accesses=[], guard=False), asserts=[])"
        """
        params = self.do(st[2])
        return self.ST.AbcdNet(lineno=st.srow, col_offset=st.scol,
                               name=st[1].text,
                               args=params,
                               body=self.do(st[4]))
    def do_abcd_task (self, st, ctx) :
        """abcd_task: 'task' NAME typelist '-' '>' typelist ':' abcd_suite
        -> ast.AbcdTask

        <<< task Foo (int) -> () : [True]
        ... [False]
        "AbcdSpec(context=[AbcdTask(name='Foo', body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[]), input=[NamedType(name='int')], output=[])], body=AbcdAction(accesses=[], guard=False), asserts=[])"
        """
        return self.ST.AbcdTask(lineno=st.srow, col_offset=st.scol,
                                name=st[1].text,
                                body=self.do(st[-1]),
                                input=self.do(st[2]),
                                output=self.do(st[5]))
    def do_typelist (self, st, ctx) :
        """typelist: '(' [abcd_type (',' abcd_type)*] ')'
        -> ast.abcdtype*

        <<< task Foo () -> (int, int, int|bool) : [True]
        ... [False]
        "AbcdSpec(context=[AbcdTask(name='Foo', body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[]), input=[], output=[NamedType(name='int'), NamedType(name='int'), UnionType(types=[NamedType(name='int'), NamedType(name='bool')])])], body=AbcdAction(accesses=[], guard=False), asserts=[])"
        """
        return [self.do(child) for child in st[1:-1:2]]
    def do_abcd_suite (self, st, ctx) :
        """abcd_suite: abcd_expr | NEWLINE INDENT abcd_spec DEDENT
        -> ast.AbcdSpec

        <<< net Foo () :
        ...    [True]
        ... [False]
        "AbcdSpec(context=[AbcdNet(name='Foo', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[]))], body=AbcdAction(accesses=[], guard=False), asserts=[])"
        <<< net Foo () : ([True]
        ...     + [False])
        ... [False]
        "AbcdSpec(context=[AbcdNet(name='Foo', args=arguments(args=[], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[], body=AbcdFlowOp(left=AbcdAction(accesses=[], guard=True), op=Choice(), right=AbcdAction(accesses=[], guard=False)), asserts=[]))], body=AbcdAction(accesses=[], guard=False), asserts=[])"
        """
        if len(st) == 1 :
            return self.ST.AbcdSpec(lineno=st.srow, col_offset=st.scol,
                                    context=[],
                                    body=self.do(st[0]))
        else :
            return self.do(st[2])
    def do_abcd_buffer (self, st, ctx) :
        """[ decorators ] 'buffer' NAME ['[' test ']'] ':' abcd_type '=' testlist
        -> ast.AbcdBuffer

        <<< buffer foo : int = ()
        ... [True]
        "AbcdSpec(context=[AbcdBuffer(name='foo', type=NamedType(name='int'), capacity=None, content=Tuple(elts=[], ctx=Load()))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< buffer foo : int = 1, 2
        ... [True]
        "AbcdSpec(context=[AbcdBuffer(name='foo', type=NamedType(name='int'), capacity=None, content=Tuple(elts=[Num(n=1), Num(n=2)], ctx=Load()))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< buffer foo : int|bool = ()
        ... [True]
        "AbcdSpec(context=[AbcdBuffer(name='foo', type=UnionType(types=[NamedType(name='int'), NamedType(name='bool')]), capacity=None, content=Tuple(elts=[], ctx=Load()))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< @capacity(max=5)
        ... buffer foo : int = ()
        ... [True]
        "AbcdSpec(context=[AbcdBuffer(name='foo', type=NamedType(name='int'), capacity=[None, Num(n=5)], content=Tuple(elts=[], ctx=Load()))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< @capacity(min=2)
        ... buffer foo : int = ()
        ... [True]
        "AbcdSpec(context=[AbcdBuffer(name='foo', type=NamedType(name='int'), capacity=[Num(n=2), None], content=Tuple(elts=[], ctx=Load()))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< @capacity(min=2, max=5)
        ... buffer foo : int = ()
        ... [True]
        "AbcdSpec(context=[AbcdBuffer(name='foo', type=NamedType(name='int'), capacity=[Num(n=2), Num(n=5)], content=Tuple(elts=[], ctx=Load()))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        if len(st) == 6 : # no decorator, no array
            return self.ST.AbcdBuffer(lineno=st.srow, col_offset=st.scol,
                                      name=st[1].text,
                                      type=self.do(st[3]),
                                      capacity=None,
                                      content=self.do(st[-1]))
        elif len(st) == 7 : # decorator, no array
            deco = self.do_buffer_decorators(st[0], ctx)
            return self.ST.AbcdBuffer(lineno=st.srow, col_offset=st.scol,
                                      name=st[2].text,
                                      type=self.do(st[4]),
                                      capacity=deco["capacity"],
                                      content=self.do(st[-1]))
        else :
            raise ParseError(st.text,
                             reason="arrays not (yet) supported")
    def do_buffer_decorators (self, st, ctx) :
        deco = {}
        for child in st :
            tree = self.do(child)
            if isinstance(tree, self.ST.Call) and tree.func.id == "capacity" :
                if tree.args or tree.starargs or tree.kwargs :
                    raise ParseError(child, reason="invalid parameters")
                min, max = None, None
                for kw in tree.keywords :
                    if kw.arg == "min" :
                        min = kw.value
                    elif kw.arg == "max" :
                        max = kw.value
                    else :
                        raise ParseError(child,
                                         reason="invalid parameter %r" % kw.arg)
                if min or max :
                    deco["capacity"] = [min, max]
                else :
                    deco["capacity"] = None
                continue
            raise ParseError(child, reason="invalid buffer decorator")
        return deco
    def do_abcd_typedef (self, st, ctx) :
        """abcd_typedef: 'typedef' NAME ':' abcd_type
        -> ast.AbcdTypedef

        <<< typedef foo : int
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=NamedType(name='int'))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        return self.ST.AbcdTypedef(lineno=st.srow, col_offset=st.scol,
                                   name=st[1].text,
                                   type=self.do(st[3]))
    def do_abcd_type (self, st, ctx) :
        """abcd_type: abcd_and_type ('|' abcd_and_type)*
        -> snakes.typing.Type

        <<< typedef foo : int
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=NamedType(name='int'))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< typedef foo : int | bool
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=UnionType(types=[NamedType(name='int'), NamedType(name='bool')]))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        if len(st) == 1 :
            return self.do(st[0])
        else :
            return self.ST.UnionType(lineno=st.srow, col_offset=st.scol,
                                     types=[self.do(child) for child in st[::2]])
    def do_abcd_and_type (self, st, ctx) :
        """abcd_and_type: abcd_cross_type ('&' abcd_cross_type)*
        -> snakes.typing.Type

        <<< typedef foo : int
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=NamedType(name='int'))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< typedef foo : int & bool
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=IntersectionType(types=[NamedType(name='int'), NamedType(name='bool')]))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        if len(st) == 1 :
            return self.do(st[0])
        else :
            return self.ST.IntersectionType(lineno=st.srow, col_offset=st.scol,
                                            types=[self.do(child) for child in st[::2]])
    def do_abcd_cross_type (self, st, ctx) :
        """abcd_cross_type: abcd_base_type ('*' abcd_base_type)*
        -> snakes.typing.Type

        <<< typedef foo : int
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=NamedType(name='int'))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< typedef foo : int * bool
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=CrossType(types=[NamedType(name='int'), NamedType(name='bool')]))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        if len(st) == 1 :
            return self.do(st[0])
        else :
            return self.ST.CrossType(lineno=st.srow, col_offset=st.scol,
                                     types=[self.do(child) for child in st[::2]])
    def do_abcd_base_type (self, st, ctx) :
        """abcd_base_type: (NAME ['(' abcd_type (',' abcd_type)* ')']
                 | 'enum' '(' test (',' test)* ')' | '(' abcd_type ')')
        -> snakes.typing.Type

        <<< typedef foo : list(int)
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=ListType(items=NamedType(name='int')))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< typedef foo : set(int)
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=SetType(items=NamedType(name='int')))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< typedef foo : dict(int, bool)
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=DictType(keys=NamedType(name='int'), values=NamedType(name='bool')))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< typedef foo : enum(1, 2, 3)
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=EnumType(items=[Num(n=1), Num(n=2), Num(n=3)]))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        <<< typedef foo : int
        ... [True]
        "AbcdSpec(context=[AbcdTypedef(name='foo', type=NamedType(name='int'))], body=AbcdAction(accesses=[], guard=True), asserts=[])"
        """
        if len(st) == 1 :
            return self.ST.NamedType(lineno=st.srow, col_offset=st.scol,
                                     name=st[0].text)
        elif len(st) == 3 :
            return self.do(st[1])
        elif st[0].text in ("list", "set", "tuple") :
            if len(st) > 4 :
                raise ParseError(st.text,
                                 reason="too many arguments for %s type"
                                 % st[0].text)
            if st[0].text == "list" :
                tree = self.ST.ListType
            elif st[0].text == "tuple" :
                tree = self.ST.TupleType
            else :
                tree = self.ST.SetType
            return tree(lineno=st.srow, col_offset=st.scol,
                        items=self.do(st[2]))
        elif st[0].text == "dict" :
            if len(st) > 6 :
                raise ParseError(st.text,
                                 reason="too many arguments for dict type")
            return self.ST.DictType(lineno=st.srow, col_offset=st.scol,
                                    keys=self.do(st[2]),
                                    values=self.do(st[4]))
        elif st[0].text == "enum" :
            return self.ST.EnumType(lineno=st.srow, col_offset=st.scol,
                                    items=[self.do(child) for child in st[2:-1:2]])
        else :
            raise ParseError(st[0].text,
                             reason=("expected 'enum', 'list', 'set' or"
                                     " 'dict' but found '%s'") % st[0].text)
    def do_tfpdef (self, st, ctx) :
        """tfpdef: NAME [':' ('net' | 'buffer' | 'task')]
        -> str, ast.AST?

        <<< net Foo (x, y, n:net, b:buffer, t:task) : [True]
        ... [False]
        "AbcdSpec(context=[AbcdNet(name='Foo', args=arguments(args=[arg(arg='x', annotation=None), arg(arg='y', annotation=None), arg(arg='n', annotation=Name(id='net', ctx=Load())), arg(arg='b', annotation=Name(id='buffer', ctx=Load())), arg(arg='t', annotation=Name(id='task', ctx=Load()))], vararg=None, varargannotation=None, kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=[], kw_defaults=[]), body=AbcdSpec(context=[], body=AbcdAction(accesses=[], guard=True), asserts=[]))], body=AbcdAction(accesses=[], guard=False), asserts=[])"
        """
        if len(st) == 1 :
            return st[0].text, None
        else :
            return st[0].text, self.ST.Name(lineno=st[2].srow,
                                            col_offset=st[2].scol,
                                            id=st[2].text,
                                            ctx=ctx())

parse = Translator.parse

if __name__ == "__main__" :
    testparser(Translator)
