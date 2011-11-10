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
from snakes.lang.ctlstar.pgen import parser
import snakes.lang.ctlstar.asdl as ast

_symbols = parser.tokenizer.tok_name.copy()
# next statement overrides 'NT_OFFSET' entry with 'single_input'
# (this is desired)
_symbols.update(parser.symbolMap)

def skip (token) :
    if token.kind == token.lexer.COMMENT :
        words = token.strip().split()
        if words[:2] == ["#", "coding="] :
            snakes.defaultencoding = words[2]
        elif words[:3] == ["#", "-*-", "coding:"] :
            snakes.defaultencoding = words[3]

parser.tokenizer.skip_token = skip

class ParseTree (PyParseTree) :
    _symbols = _symbols

class Translator (PyTranslator) :
    ParseTree = ParseTree
    parser = parser
    ST = ast
    def do_file_input (self, st, ctx) :
        """file_input: (NEWLINE | ctl_atomdef | ctl_propdef)* [ ctl_formula ] NEWLINE* ENDMARKER
        -> ast.Spec

        <<< atom foo () : return True
        ... prop bar () : True
        ... has('my place', x)
        "Spec(atoms=[AtomDef(name='foo', args=[], body=[Return(value=Name(id='True', ctx=Load()))])], properties=[Property(name='bar', args=[], body=Boolean(val=True))], main=InPlace(data=[Name(id='x', ctx=Load())], place=Place(name=None, place='my place')))"
        """
        atoms, props, main = [], [], None
        for i, child in enumerate(st) :
            if child.symbol == "ctl_atomdef" :
                atoms.append(self.do(child, ctx))
            elif child.symbol == "ctl_propdef" :
                props.append(self.do(child, ctx))
            elif child.symbol == "ctl_formula" :
                main = self.do(child, ctx)
            elif child.symbol in ("NEWLINE", "ENDMARKER") :
                pass
            else :
                raise ParseError(child.text, reason="unexpected token")
        return self.ST.Spec(lineno=st.srow, col_offset=st.scol,
                            atoms=atoms, properties=props, main=main)
    def do_ctl_atomdef (self, st, ctx) :
        """ctl_atomdef: 'atom' NAME '(' [ctl_parameters] ')' ':' suite
        -> ast.AtomDef

        <<< atom foo () : return True
        "Spec(atoms=[AtomDef(name='foo', args=[], body=[Return(value=Name(id='True', ctx=Load()))])], properties=[], main=None)"
        <<< atom bar () :
        ...     return True
        "Spec(atoms=[AtomDef(name='bar', args=[], body=[Return(value=Name(id='True', ctx=Load()))])], properties=[], main=None)"
        <<< atom egg (p = 'my place', x : int, q : place) :
        ...     return x in p and x in q
        "Spec(atoms=[AtomDef(name='egg', args=[Place(name='p', place='my place'), Parameter(name='x', type='int'), Parameter(name='q', type='place')], body=[Return(value=BoolOp(op=And(), values=[Compare(left=Name(id='x', ctx=Load()), ops=[In()], comparators=[Name(id='p', ctx=Load())]), Compare(left=Name(id='x', ctx=Load()), ops=[In()], comparators=[Name(id='q', ctx=Load())])]))])], properties=[], main=None)"
        """
        if len(st) == 7 :
            return self.ST.AtomDef(lineno=st.srow, col_offset=st.scol,
                                   name=st[1].text,
                                   args=self.do(st[3], ctx),
                                   body=self.do(st[-1], ctx))
        else :
            return self.ST.AtomDef(lineno=st.srow, col_offset=st.scol,
                                   name=st[1].text,
                                   args=[],
                                   body=self.do(st[-1], ctx))
    def do_ctl_propdef (self, st, ctx) :
        """ctl_propdef: 'prop' NAME '(' [ctl_parameters] ')' ':' ctl_suite
        -> ast.Property

        <<< prop foo () : True
        "Spec(atoms=[], properties=[Property(name='foo', args=[], body=Boolean(val=True))], main=None)"
        <<< prop bar (p = 'my place', x : int, q : place) : True
        "Spec(atoms=[], properties=[Property(name='bar', args=[Place(name='p', place='my place'), Parameter(name='x', type='int'), Parameter(name='q', type='place')], body=Boolean(val=True))], main=None)"
        <<< prop egg (p = 'my place', x : int, q : place) : True
        "Spec(atoms=[], properties=[Property(name='egg', args=[Place(name='p', place='my place'), Parameter(name='x', type='int'), Parameter(name='q', type='place')], body=Boolean(val=True))], main=None)"
        """
        if len(st) == 7 :
            return self.ST.Property(lineno=st.srow, col_offset=st.scol,
                                    name=st[1].text,
                                    args=self.do(st[3], ctx),
                                    body=self.do(st[-1], ctx))
        else :
            return self.ST.Property(lineno=st.srow, col_offset=st.scol,
                                    name=st[1].text,
                                    args=[],
                                    body=self.do(st[-1], ctx))
    def do_ctl_suite (self, st, ctx) :
        """ctl_suite: ( ctl_formula NEWLINE | NEWLINE INDENT ctl_formula DEDENT )
        -> ast.form

        <<< prop foo () : True
        "Spec(atoms=[], properties=[Property(name='foo', args=[], body=Boolean(val=True))], main=None)"
        <<< prop bar () :
        ...    True
        "Spec(atoms=[], properties=[Property(name='bar', args=[], body=Boolean(val=True))], main=None)"
        """
        if len(st) == 2 :
            return self.do(st[0], ctx)
        else :
            return self.do(st[2], ctx)
    def do_ctl_parameters (self, st, ctx) :
        """ctl_parameters: (ctl_param ',')* ctl_param
        -> [ast.ctlarg]

        <<< prop foo (p = 'my place', q : place, x : int, r : place) : True
        "Spec(atoms=[], properties=[Property(name='foo', args=[Place(name='p', place='my place'), Parameter(name='q', type='place'), Parameter(name='x', type='int'), Parameter(name='r', type='place')], body=Boolean(val=True))], main=None)"
        <<< prop bar (x : int) : True
        "Spec(atoms=[], properties=[Property(name='bar', args=[Parameter(name='x', type='int')], body=Boolean(val=True))], main=None)"
        <<< prop egg (p = 'my place') : True
        "Spec(atoms=[], properties=[Property(name='egg', args=[Place(name='p', place='my place')], body=Boolean(val=True))], main=None)"
        """
        return [self.do(child, ctx) for child in st[::2]]
    def do_ctl_param (self, st, ctx) :
        """ctl_param: NAME ( '=' STRING+ | ':' NAME )
        -> ast.ctlarg

        <<< prop foo (p = 'my place', q : place, x : int, r : place) : True
        "Spec(atoms=[], properties=[Property(name='foo', args=[Place(name='p', place='my place'), Parameter(name='q', type='place'), Parameter(name='x', type='int'), Parameter(name='r', type='place')], body=Boolean(val=True))], main=None)"
        <<< prop bar (x : int) : True
        "Spec(atoms=[], properties=[Property(name='bar', args=[Parameter(name='x', type='int')], body=Boolean(val=True))], main=None)"
        <<< prop egg (p = 'my place') : True
        "Spec(atoms=[], properties=[Property(name='egg', args=[Place(name='p', place='my place')], body=Boolean(val=True))], main=None)"
        """
        if st[1].text == "=" :
            return self.ST.Place(lineno=st.srow, col_offset=st.scol,
                                 name=st[0].text,
                                 place="".join(self.ST.literal_eval(c.text)
                                               for c in st[2:]))
        else :
            return self.ST.Parameter(lineno=st.srow, col_offset=st.scol,
                                     name=st[0].text,
                                     type=st[2].text)
    def do_ctl_arguments (self, st, ctx) :
        """ctl_arguments: (NAME '=' test ',')* NAME '=' test
        -> [(str, ast.expr)]

        <<< foo(x=3, p='my place')
        "Spec(atoms=[], properties=[], main=AtomInstance(name='foo', args=[arg(arg='x', annotation=Num(n=3)), arg(arg='p', annotation=Str(s='my place'))]))"
        <<< foo(x=3)
        "Spec(atoms=[], properties=[], main=AtomInstance(name='foo', args=[arg(arg='x', annotation=Num(n=3))]))"
        <<< foo(p='my place')
        "Spec(atoms=[], properties=[], main=AtomInstance(name='foo', args=[arg(arg='p', annotation=Str(s='my place'))]))"
        """
        return [self.ST.arg(name.text, self.do(value, ctx))
                for name, value in zip(st[::4], st[2::4])]
    def do_ctl_formula (self, st, ctx) :
        """ctl_formula: ctl_or_formula [ ctl_connector ctl_or_formula ]
        -> ast.form

        <<< True
        'Spec(atoms=[], properties=[], main=Boolean(val=True))'
        <<< False => True
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Imply(), left=Boolean(val=False), right=Boolean(val=True)))'
        <<< False <=> False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Iff(), left=Boolean(val=False), right=Boolean(val=False)))'
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return self.ST.CtlBinary(lineno=st.srow, col_offset=st.scol,
                                     op=self.do_ctl_connector(st[1], ctx),
                                     left=self.do(st[0], ctx),
                                     right=self.do(st[2], ctx))
    def do_ctl_connector (self, st, ctx) :
        """ctl_connector: ( '=' '>' | '<=' '>' )
        -> ast.ctlbinary

        <<< False => True
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Imply(), left=Boolean(val=False), right=Boolean(val=True)))'
        <<< False <=> False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Iff(), left=Boolean(val=False), right=Boolean(val=False)))'
        """
        op = "".join(child.text for child in st)
        return self._ctl_binary_op[op](lineno=st.srow,
                                       col_offset=st.scol)

    def do_ctl_or_formula (self, st, ctx) :
        """ctl_or_formula: ctl_and_formula [ 'or' ctl_and_formula ]
        -> ast.form

        <<< True or False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Or(), left=Boolean(val=True), right=Boolean(val=False)))'
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            op = self._ctl_binary_op[st[1].text](lineno=st[1].srow,
                                                 col_offset=st[1].scol)
            return self.ST.CtlBinary(lineno=st.srow, col_offset=st.scol,
                                     op=op,
                                     left=self.do(st[0], ctx),
                                     right=self.do(st[2], ctx))
    def do_ctl_and_formula (self, st, ctx) :
        """ctl_and_formula: ctl_not_formula [ 'and' ctl_not_formula ]
        -> ast.form

        <<< True and False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=And(), left=Boolean(val=True), right=Boolean(val=False)))'
        """
        return self.do_ctl_or_formula(st, ctx)
    def do_ctl_not_formula (self, st, ctx) :
        """ctl_not_formula: ('not' ctl_not_formula | ctl_binary_formula)
        -> ast.form

        <<< True
        'Spec(atoms=[], properties=[], main=Boolean(val=True))'
        <<< not True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Not(), child=Boolean(val=True)))'
        <<< not not True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Not(), child=CtlUnary(op=Not(), child=Boolean(val=True))))'
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return self.ST.CtlUnary(lineno=st.srow, col_offset=st.scol,
                                    op=self.ST.Not(lineno=st[0].srow,
                                                   col_offset=st[0].scol),
                                    child=self.do(st[1], ctx))
    def do_ctl_binary_formula (self, st, ctx) :
        """ctl_binary_formula: ctl_unary_formula [ ctl_binary_op ctl_unary_formula ]
        -> ast.form

        <<< True U False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Until(), left=Boolean(val=True), right=Boolean(val=False)))'
        <<< True W False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=WeakUntil(), left=Boolean(val=True), right=Boolean(val=False)))'
        <<< True R False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Release(), left=Boolean(val=True), right=Boolean(val=False)))'
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        else :
            return self.ST.CtlBinary(lineno=st.srow, col_offset=st.scol,
                                     op=self.do(st[1], ctx),
                                     left=self.do(st[0], ctx),
                                     right=self.do(st[2], ctx))
    def do_ctl_unary_formula (self, st, ctx) :
        """ctl_unary_formula: [ ctl_unary_op ] (ctl_atom_formula | '(' ctl_formula ')')
        -> ast.form

        <<< True
        'Spec(atoms=[], properties=[], main=Boolean(val=True))'
        <<< X True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Next(), child=Boolean(val=True)))'
        <<< A True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=All(), child=Boolean(val=True)))'
        <<< G True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Globally(), child=Boolean(val=True)))'
        <<< F True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Future(), child=Boolean(val=True)))'
        <<< E True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Exists(), child=Boolean(val=True)))'
        <<< (True or False)
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Or(), left=Boolean(val=True), right=Boolean(val=False)))'
        <<< X (True or False)
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Next(), child=CtlBinary(op=Or(), left=Boolean(val=True), right=Boolean(val=False))))'
        """
        if len(st) == 1 :
            return self.do(st[0], ctx)
        elif len(st) == 2 :
            return self.ST.CtlUnary(lineno=st.srow, col_offset=st.scol,
                                    op=self.do(st[0], ctx),
                                    child=self.do(st[1], ctx))
        elif len(st) == 3 :
            return self.do(st[1], ctx)
        else :
            return self.ST.CtlUnary(lineno=st.srow, col_offset=st.scol,
                                    op=self.do(st[0], ctx),
                                    child=self.do(st[2], ctx))
    _ctl_unary_op = {"A" : ast.All,
                     "E" : ast.Exists,
                     "X" : ast.Next,
                     "F" : ast.Future,
                     "G" : ast.Globally}
    def do_ctl_unary_op (self, st, ctx) :
        """ctl_unary_op: ('A' | 'G' | 'F' | 'E' | 'X')
        -> ast.ctlunary

        <<< X True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Next(), child=Boolean(val=True)))'
        <<< A True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=All(), child=Boolean(val=True)))'
        <<< G True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Globally(), child=Boolean(val=True)))'
        <<< F True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Future(), child=Boolean(val=True)))'
        <<< E True
        'Spec(atoms=[], properties=[], main=CtlUnary(op=Exists(), child=Boolean(val=True)))'
        """
        return self._ctl_unary_op[st[0].text](lineno=st.srow,
                                              col_offset=st.scol)
    _ctl_binary_op = {"=>"  : ast.Imply,
                      "<=>" : ast.Iff,
                      "and" : ast.And,
                      "or"  : ast.Or,
                      "U"   : ast.Until,
                      "W"   : ast.WeakUntil,
                      "R"   : ast.Release}
    def do_ctl_binary_op (self, st, ctx) :
        """ctl_binary_op: ('R' | 'U' | 'W')
        -> ast.ctlbinary

        <<< True R False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Release(), left=Boolean(val=True), right=Boolean(val=False)))'
        <<< True U False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=Until(), left=Boolean(val=True), right=Boolean(val=False)))'
        <<< True W False
        'Spec(atoms=[], properties=[], main=CtlBinary(op=WeakUntil(), left=Boolean(val=True), right=Boolean(val=False)))'
        """
        return self._ctl_binary_op[st[0].text](lineno=st[0].srow,
                                               col_offset=st[0].scol)
    def do_ctl_atom_formula (self, st, ctx) :
        """ctl_atom_formula: ( 'empty' '(' ctl_place ')'
                   | 'marked' '(' ctl_place ')'
		   | 'has' ['not'] '(' ctl_place ',' test (',' test)* ')'
		   | 'deadlock' | 'True' | 'False'
		   | NAME '(' ctl_arguments ')'
		   | 'forall' [ 'distinct' ] NAME (',' NAME)*
                     'in' ctl_place '(' ctl_atom_formula ')'
		   | 'exists' [ 'distinct' ] NAME (',' NAME)*
                     'in' ctl_place '(' ctl_atom_formula ')' )
        -> ast.atom

        <<< empty(p)
        "Spec(atoms=[], properties=[], main=EmptyPlace(place=Parameter(name='p', type='place')))"
        <<< empty('my' 'place')
        "Spec(atoms=[], properties=[], main=EmptyPlace(place=Place(name=None, place='myplace')))"
        <<< marked(p)
        "Spec(atoms=[], properties=[], main=MarkedPlace(place=Parameter(name='p', type='place')))"
        <<< marked('my place')
        "Spec(atoms=[], properties=[], main=MarkedPlace(place=Place(name=None, place='my place')))"
        <<< has(p, x)
        "Spec(atoms=[], properties=[], main=InPlace(data=[Name(id='x', ctx=Load())], place=Parameter(name='p', type='place')))"
        <<< has not(p, x, y)
        "Spec(atoms=[], properties=[], main=NotInPlace(data=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load())], place=Name(id='x', ctx=Load())))"
        <<< deadlock
        'Spec(atoms=[], properties=[], main=Deadlock())'
        <<< True
        'Spec(atoms=[], properties=[], main=Boolean(val=True))'
        <<< False
        'Spec(atoms=[], properties=[], main=Boolean(val=False))'
        <<< myprop(x=1, p='my place')
        "Spec(atoms=[], properties=[], main=AtomInstance(name='myprop', args=[arg(arg='x', annotation=Num(n=1)), arg(arg='p', annotation=Str(s='my place'))]))"
        <<< forall x in p (has(q, y))
        "Spec(atoms=[], properties=[], main=Quantifier(op=All(), vars=['x'], place=Parameter(name='p', type='place'), child=InPlace(data=[Name(id='y', ctx=Load())], place=Parameter(name='q', type='place')), distinct=False))"
        <<< forall x, y in p (has(q, x+y, x-y))
        "Spec(atoms=[], properties=[], main=Quantifier(op=All(), vars=['x', 'y'], place=Parameter(name='p', type='place'), child=InPlace(data=[BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load())), BinOp(left=Name(id='x', ctx=Load()), op=Sub(), right=Name(id='y', ctx=Load()))], place=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load()))), distinct=False))"
        <<< forall distinct x, y in p (has(q, x+y, x-y))
        "Spec(atoms=[], properties=[], main=Quantifier(op=All(), vars=['x', 'y'], place=Parameter(name='p', type='place'), child=InPlace(data=[BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load())), BinOp(left=Name(id='x', ctx=Load()), op=Sub(), right=Name(id='y', ctx=Load()))], place=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load()))), distinct=True))"
        <<< exists x in p (has(q, y))
        "Spec(atoms=[], properties=[], main=Quantifier(op=Exists(), vars=['x'], place=Parameter(name='p', type='place'), child=InPlace(data=[Name(id='y', ctx=Load())], place=Parameter(name='q', type='place')), distinct=False))"
        <<< exists x, y in p (has(q, x+y, x-y))
        "Spec(atoms=[], properties=[], main=Quantifier(op=Exists(), vars=['x', 'y'], place=Parameter(name='p', type='place'), child=InPlace(data=[BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load())), BinOp(left=Name(id='x', ctx=Load()), op=Sub(), right=Name(id='y', ctx=Load()))], place=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load()))), distinct=False))"
        <<< exists distinct x, y in p (has(q, x+y, x-y))
        "Spec(atoms=[], properties=[], main=Quantifier(op=Exists(), vars=['x', 'y'], place=Parameter(name='p', type='place'), child=InPlace(data=[BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load())), BinOp(left=Name(id='x', ctx=Load()), op=Sub(), right=Name(id='y', ctx=Load()))], place=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Name(id='y', ctx=Load()))), distinct=True))"
        """
        if st[0].text in ("True", "False") :
            return self.ST.Boolean(lineno=st.srow, col_offset=st.scol,
                                   val=(st[0].text  == "True"))
        elif st[0].text == "deadlock" :
            return self.ST.Deadlock(lineno=st.srow, col_offset=st.scol)
        elif st[0].text in ("empty", "marked") :
            node = (self.ST.EmptyPlace if st[0].text == "empty"
                    else self.ST.MarkedPlace)
            return node(lineno=st.srow, col_offset=st.scol,
                        place=self.do(st[2], ctx))
        elif st[0].text == "has" :
            if st[1].text == "not" :
                node = self.ST.NotInPlace
                start = 5
            else :
                node = self.ST.InPlace
                start = 4
            return node(lineno=st.srow, col_offset=st.scol,
                        data=[self.do(c, ctx) for c in st[start::2]],
                        place=self.do(st[-4], ctx))
        elif st[0].text in ("forall", "exists") :
            op = (self.ST.All if st[0].text == "forall"
                  else self.ST.Exists)
            distinct = st[1].text == "distinct"
            start = 2 if distinct else 1
            return self.ST.Quantifier(lineno=st.srow, col_offset=st.scol,
                                      op=op(),
                                      vars=[c.text for c in st[start:-5:2]],
                                      place=self.do(st[-4], ctx),
                                      child=self.do(st[-2], ctx),
                                      distinct=distinct)
        else :
            return self.ST.AtomInstance(lineno=st.srow, col_offset=st.scol,
                                        name=st[0].text,
                                        args=self.do(st[2], ctx))
    def do_ctl_place (self, st, ctx) :
        """ctl_place: STRING+ | NAME
        -> ast.ctlarg

        <<< has('my place', x)
        "Spec(atoms=[], properties=[], main=InPlace(data=[Name(id='x', ctx=Load())], place=Place(name=None, place='my place')))"
        <<< has('another' 'place', y)
        "Spec(atoms=[], properties=[], main=InPlace(data=[Name(id='y', ctx=Load())], place=Place(name=None, place='anotherplace')))"
        <<< has('my place', x, y)
        "Spec(atoms=[], properties=[], main=InPlace(data=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load())], place=Name(id='x', ctx=Load())))"
        <<< has not('my place', x)
        "Spec(atoms=[], properties=[], main=NotInPlace(data=[Name(id='x', ctx=Load())], place=Place(name=None, place='my place')))"
        <<< has not('my place', x, y)
        "Spec(atoms=[], properties=[], main=NotInPlace(data=[Name(id='x', ctx=Load()), Name(id='y', ctx=Load())], place=Name(id='x', ctx=Load())))"
        """
        if st[0].symbol == "NAME" :
            return self.ST.Parameter(lineno=st.srow, col_offset=st.scol,
                                     name=st[0].text,
                                     type="place")
        else :
            return self.ST.Place(lineno=st.srow, col_offset=st.scol,
                                 name=None,
                                 place="".join(self.ST.literal_eval(c.text)
                                               for c in st))

parse = Translator.parse

if __name__ == "__main__" :
    testparser(Translator)
