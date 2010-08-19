import inspect, compiler, compiler.ast, os, os.path, sys
from snakes import ParseError
from snakes.utils.abcd import python_lex, python_yacc,  lex, yacc
from snakes.pnml import Tree as pnmlTree

class PlyLexer (object) :
    """Python lexer class based on PLY

    This lexer encapsulates that from python4ply and can be easily
    extended. For instance, a token '?' can be added as:

    >>> class TestLexer (PlyLexer) :
    ...     def t_QUESTION (self, tok) :
    ...         r'\?'
    ...         return tok
    >>> lexer = TestLexer()
    >>> lexer.input('hello world?')
    >>> for tok in lexer:
    ...     print tok
    LexToken(NAME,'hello',1,0)
    LexToken(NAME,'world',1,6)
    LexToken(QUESTION,'?',1,11)
    LexToken(ENDMARKER,None,1,-100)
    """
    tokens = list(python_lex.tokens)
    def __init__ (self) :
        """Initializes an instance of C{PlyLexer}

        >>> lex = PlyLexer()

        @return: an instance of C{PlyLexer}
        @rtype: C{PlyLexer}
        """
        self.tokens = self.tokens[:]
        for name, method in inspect.getmembers(self, inspect.ismethod) :
            if name.startswith("t_") and not (name.startswith("t_begin_")
                                              or name.endswith("_ignore")
                                              or name.endswith("_error")
                                              or name.startswith("_end")) :
                self.tokens.append(name[2:])
        for name, obj in inspect.getmembers(python_lex) :
            if not hasattr(self, name) :
                setattr(self, name, obj)
        self.lexer = python_lex.PythonLexer(lexer=lex.lex(module=self))
    def __iter__ (self) :
        """Iterates over recognized tokens

        >>> lex = PlyLexer()
        >>> lex.input('x+1')
        >>> list(lex)
        [LexToken(NAME,'x',1,0),
         LexToken(PLUS,'+',1,1),
         LexToken(NUMBER,(1, '1'),1,2),
         LexToken(ENDMARKER,None,1,-100)]

        @return: an iterator over recognized tokens
        @rtype: C{generator}
        """
        return iter(self.lexer)
    def input (self, data, filename="<string>"):
        """Feed the lexer with data

        >>> lex = PlyLexer()
        >>> lex.input('x+1')
        >>> list(lex)
        [LexToken(NAME,'x',1,0),
         LexToken(PLUS,'+',1,1),
         LexToken(NUMBER,(1, '1'),1,2),
         LexToken(ENDMARKER,None,1,-100)]

        @param data: the source code to analyse
        @type data: C{str}
        @param filename: the name of the file being analyzed
        @type filename: C{str}
        @return: nothing
        @rtype: C{None}
        """
        if os.linesep != "\n" :
            # python4ply only handles \n
            data = data.replace(os.linesep, "\n")
        self.lexer.input(data, filename)
    def token (self) :
        """Recognize and return one token

        >>> lex = PlyLexer()
        >>> lex.input('x+1')
        >>> lex.token()
        LexToken(NAME,'x',1,0)
        >>> lex.token()
        LexToken(PLUS,'+',1,1)

        @return: the next token recognized, each call to the method
          consumes one token in the input stream
        @rtype: C{LexToken}
        """
        return self.lexer.token()

class PlyParser (object) :
    """Python parser class based on PLY

    This parse encapsulates that from python4ply and can be easily
    extended. For instance, a set construct can be added as a single
    rule:

    >>> class TestParser (PlyParser) :
    ...     def p_atom_12 (self, p) :
    ...         'atom : LBRACE listmaker RBRACE'
    ...         p[0] = compiler.ast.CallFunc(compiler.ast.Name('set'),
    ...                                      [p[2]], None, None)
    ...         self.locate(p[0], p[2].lineno)
    >>> eval(AstPrinter(TestParser)('{1, 2, 3, 4, 4}'))
    set([1, 2, 3, 4])
    """
    lexer = PlyLexer
    start = "file_input"
    tabmodule = None
    outputdir = None
    def __init__ (self) :
        """Initialize a C{PlyParser}

        >>> yacc = PlyParser()

        @return: an instance of C{PlyParser}
        @rtype: C{PlyParser}
        """
        self.lexer = self.lexer()
        self.tokens = self.lexer.tokens
        for name, obj in inspect.getmembers(python_yacc) :
            if not hasattr(self, name) :
                setattr(self, name, obj)
        if self.tabmodule is None :
            self.tabmodule = "%s_%s" % (self.__module__.replace(".", "_"),
                                        self.__class__.__name__)
        if self.outputdir is None :
            self.outputdir=os.path.dirname(__file__)
        self.parser = yacc.yacc(module=self, start=self.start,
                                tabmodule=self.tabmodule,
                                outputdir=self.outputdir)
    def parse (self, source, filename="<string>") :
        """Parse a fragment of Pytjon source code

        >>> PlyParser().parse('x = x+1')
        Module(None, Stmt([Assign([AssName('x', 'OP_ASSIGN')],
                           Add((Name('x'), Const(1))))]))

        @param source: the souce code to parse
        @type source: C{str}
        @param filename: the name of the analysed source file
        @type filename: C{str}
        @return: the recognized AST
        @rtype: C{compiler.ast.Node}
        """
        try :
            # python4ply raises SyntaxError if the source code does
            # not end with \n
            self._data = source.rstrip() + "\n"
            self.filename = filename
            ast = self.parser.parse(self._data, lexer=self.lexer)
            try :
                ast.filename = filename
            except :
                pass
            return ast
        except SyntaxError, err :
            try :
                token = err.message
                if token.value is None :
                    value = token.type
                else :
                    value = repr(token.value)
                error = ParseError(self._format_error("unexpected symbol %s"
                                                      % value,
                                                      token.lineno))
            except Exception, e:
                error = err
            raise error
    def _format_error (self, msg, lineno=0) :
        return "[%s:%s] %s" % (self.filename, lineno, msg.strip())
    def p_error (self, arg, *largs, **kargs) :
        """Report a parsing error

        This function is not intended to be called by the end used.
        """
        python_yacc.p_error(arg, *largs, **kargs)

class NativeParser (object) :
    """The native Python parser
    """
    def parse (self, expr) :
        """Parse Python source code

        >>> NativeParser().parse('1+2')
        Module(None, Stmt([Discard(Add((Const(1), Const(2))))]))

        @param expr: a fragment of Python source code
        @type expr: C{str}
        @return: the corresponding AST
        @rtype: C{compiler.ast.Node}
        """
        return compiler.parse(expr)

class AstPrinter (object) :
    """The base class for converting a Python AST to source code.
    """
    unsupported = ()
    def __init__ (self, parser=None) :
        """Initialisation a an C{AstPrinter}

        >>> AstPrinter(NativeParser)
        <...>
        >>> AstPrinter(PlyParser)
        <...>

        @param parser: the parse class to use
        @type parser: C{NativeParser} or C{PlyParser} or any subclass
        @return: initialized C{AstPrinter} instance
        @rtype: C{AstPrinter}
        """
        if parser is None :
            parser = NativeParser
        self.parser = parser()
    def __call__ (self, expr) :
        """Parse a Python statement.

        >>> AstPrinter()('x = 1+2')
        'x = (1) + (2)'

        @param expr: the expression or statement to parse
        @type expr: C{str}
        @return: the result of the parsing in canonical form
        @rtype: C{str}
        """
        ast = self.parser.parse(expr)
        return self[ast]
    def __getitem__ (self, node) :
        """Return the representation of a node

        @param node: an AST node
        @type node: C{compiler.ast.Node}
        @return: the string representation of C{node}
        @rtype: C{str}
        """
        name = node.__class__.__name__
        _name_ = "_%s_" % name
        if not hasattr(self, _name_) :
            raise ParseError, "unsupported construct '%s'" % name
        elif name in self.unsupported :
            doc = getattr(self, _name_).__doc__.splitlines()[0].strip()
            raise ParseError, "%s not supported" % doc
        return getattr(self, "_%s_" % name)(node)
    def indent (self, lines) :
        """Indent lines of source code

        >>> AstPrinter().indent('x = 1+2\\ny = x+3')
        '    x = 1+2\\n    y = x+3'

        @param lines: a fragment of Python source code
        @type lines: C{str}
        @return: the same source indented by four spaces
        @rtype: C{str}
        """
        return "\n".join("    " + l for l in lines.splitlines())
    def _Add_ (self, node) :
        """addition
        # Add attributes
        #     left             left operand
        #     right            right operand
        >>> print AstPrinter()('x+y')
        (x) + (y)
        """
        return "(%s) + (%s)" % (self[node.left], self[node.right])
    def _And_ (self, node) :
        """boolean and
        # And attributes
        #     nodes            list of operands
        >>> print AstPrinter()('a and b and c')
        (a) and (b) and (c)
        """
        return " and ".join("(%s)" % self[n] for n in node.nodes)
    def _AssAttr_ (self, node) :
        """attribute assignement
        # AssAttr attributes
        #     expr             expression on the left-hand side of the dot
        #     attrname         the attribute name, a string
        #     flags            XXX
        >>> print AstPrinter()('a.x = 2')
        a.x = 2
        """
        return "%s.%s" % (self[node.expr], node.attrname)
    def _AssList_ (self, node) :
        """list assignment
        # AssList attributes
        #     nodes            list of list elements being assigned to
        >>> print AstPrinter()('[x, y] = 1, 2')
        [x, y] = ((1), (2))
        """
        return "[%s]" % ", ".join(self[n] for n in node.nodes)
    def _Assert_ (self, node) :
        """assertion
        # Assert attributes
        #     test             the expression to be tested
        #     fail             the value of the AssertionError
        >>> print AstPrinter()('assert x, y')
        assert x, y
        """
        return "assert %s, %s" % (self[node.test], self[node.fail])
    def _Assign_ (self, node) :
        """assignment
        # Assign attributes
        #     nodes            a list of assignment targets, one per equal sign
        #     expr             the value being assigned
        >>> print AstPrinter()('x=y=z')
        x = y = z
        """
        return "%s = %s" % (" = ".join(self[n] for n in node.nodes),
                            self[node.expr])
    def _AssName_ (self, node) :
        """assignment
        # AssName attributes
        #     name             name being assigned to
        #     flags            XXX
        >>> print AstPrinter()('x=1')
        x = 1
        """
        return node.name
    def _AssTuple_ (self, node) :
        """tuple assignment
        # AssTuple attributes
        #     nodes            list of tuple elements being assigned to
        >>> print AstPrinter()('x, y = 1, 2')
        x, y = ((1), (2))
        """
        return ", ".join(self[n] for n in node.nodes)
    def _AugAssign_ (self, node) :
        """augmented assignment
        # AugAssign attributes
        #     node
        #     op
        #     expr
        >>> print AstPrinter()('x += 1')
        x += 1
        """
        return " ".join([self[node.node], node.op, self[node.expr]])
    def _Backquote_ (self, node) :
        """back-quotes
        # Backquote attributes
        #     expr
        >>> print AstPrinter()('`5`')
        `5`
        """
        return "`%s`" % self[node.expr]
    def _Bitand_ (self, node) :
        """binary and
        # Bitand attributes
        #     nodes
        >>> print AstPrinter()('x & y & z')
        (x) & (y) & (z)
        """
        return " & ".join("(%s)" % self[n] for n in node.nodes)
    def _Bitor_ (self, node) :
        """binary or
        # Bitor attributes
        #     nodes
        >>> AstPrinter()('x | y | z')
        '(x) | (y) | (z)'
        """
        return " | ".join("(%s)" % self[n] for n in node.nodes)
    def _Bitxor_ (self, node) :
        """binary xor
        # Bitxor attributes
        #     nodes
        >>> print AstPrinter()('x ^ y ^ z')
        (x) ^ (y) ^ (z)
        """
        return " ^ ".join("(%s)" % self[n] for n in node.nodes)
    def _Break_ (self, node) :
        """break
        # Break attributes
        >>> print AstPrinter()('break')
        break
        """
        return "break"
    def _CallFunc_ (self, node) :
        """function call
        # CallFunc attributes
        #     node             expression for the callee
        #     args             a list of arguments
        #     star_args        the extended *-arg value
        #     dstar_args       the extended **-arg value
        >>> print AstPrinter()('f(x, y)')
        (f)(x, y)
        >>> print AstPrinter()('f(x, *y)')
        (f)(x, *y)
        >>> print AstPrinter()('f(x, **y)')
        (f)(x, **y)
        >>> print AstPrinter()('f(x, *y, **z)')
        (f)(x, *y, **z)
        """
        args = [self[n] for n in node.args]
        if node.star_args is not None :
            args.append("*" + self[node.star_args])
        if node.dstar_args is not None :
            args.append("**" + self[node.dstar_args])
        return "(%s)(%s)" % (self[node.node], ", ".join(args))
    def _Class_ (self, node) :
        """class definition
        # Class attributes
        #     name             the name of the class, a string
        #     bases            a list of base classes
        #     doc              doc string, a string or None
        #     code             the body of the class statement
        >>> print AstPrinter()('class hello(foo, bar):\\n'
        ...                    '    "hello class"\\n'
        ...                    '    attr = 4\\n'
        ...                    '    def __init__ (self) :\\n'
        ...                    '        "method hello.__init__"\\n'
        ...                    '        self.attr = self.__class__.attr')
        class hello (foo, bar):
            'hello class'
            attr = 4
            def __init__ (self):
                'method hello.__init__'
                self.attr = ((self).__class__).attr
        """
        if len(node.bases) == 0 :
            parts = ["class %s:" % node.name]
        else :
            parts = ["class %s (%s):"
                     % (node.name,
                        ", ".join(self[b] for b in node.bases))]
        if node.doc is not None :
            parts.append(self.indent(repr(node.doc)))
        parts.append(self.indent(self[node.code]))
        return "\n".join(parts)
    def _Compare_ (self, node) :
        """comparison
        # Compare attributes
        #     expr
        #     ops
        >>> print AstPrinter()('x <= y < z')
        (x) <= (y) < (z)
        """
        parts = ["(%s)" % self[node.expr]]
        for op, expr in node.ops :
            parts.append("%s (%s)" % (op, self[expr]))
        return " ".join(parts)
    def _Const_ (self, node) :
        """constant
        # Const attributes
        #     value
        >>> print AstPrinter()('5')
        5
        """
        return repr(node.value)
    def _Continue_ (self, node) :
        """continue
        # Continue attributes
        >>> print AstPrinter()('continue')
        continue
        """
        return 'continue'
    def _Decorators_ (self, node) :
        """decorators
        # Decorators attributes
        #     nodes
        #>>> AstPrinter()('@x\\n@y\\ndef f(): pass')
        """
        return "\n".join(self[n] for n in node.nodes)
    def _Dict_ (self, node) :
        """dictionnary
        # Dict attributes
        #     items
        >>> print AstPrinter()('{1: 2, "a":"b"}')
        {1: 2, 'a': 'b'}
        """
        return "{%s}" % ", ".join("%s: %s" % (self[key], self[val])
                                  for key, val in node.items)
    def _Discard_ (self, node) :
        """function call (discarding result)
        # Discard attributes
        #     expr
        >>> print AstPrinter()('f(x)')
        (f)(x)
        """
        return self[node.expr]
    def _Div_ (self, node) :
        """division
        # Div attributes
        #     left
        #     right
        >>> print AstPrinter()('x/y')
        (x) / (y)
        """
        return "(%s) / (%s)" % (self[node.left], self[node.right])
    def _Ellipsis_ (self, node) :
        """ellipsis
        # Ellipsis attributes
        >>> print AstPrinter()('l[...]')
        (l)[...]
        """
        return '...'
    def _Exec_ (self, node) :
        """exec statement
        # Exec attributes
        #     expr
        #     locals
        #     globals
        >>> print AstPrinter()('exec c')
        exec c
        >>> print AstPrinter()('exec c in l')
        exec c in l
        >>> print AstPrinter()('exec c in l, g')
        exec c in l, g
        """
        parts = ["exec %s" % self[node.expr]]
        if node.locals is not None :
            parts.append(" in %s" % self[node.locals])
        if node.globals is not None :
            parts.append(", %s" % self[node.globals])
        return "".join(parts)
    def _For_ (self, node) :
        """for loop
        # For attributes
        #     assign
        #     list
        #     body
        #     else_
        >>> print AstPrinter()('for x, y in l:\\n'
        ...                    '    a += x + y')
        for x, y in l:
            a += (x) + (y)
        >>> print AstPrinter()('for x, y in l:\\n'
        ...                    '    a += x + y\\n'
        ...                    'else:\\n'
        ...                    '    a = 0')
        for x, y in l:
            a += (x) + (y)
        else:
            a = 0
        """
        parts = ["for %s in %s:" % (self[node.assign], self[node.list]),
                 self.indent(self[node.body])]
        if node.else_ is not None :
            parts.extend(["else:",
                          self.indent(self[node.else_])])
        return "\n".join(parts)
    def _From_ (self, node) :
        """from import
        # From attributes
        #     modname
        #     names
        >>> print AstPrinter()('from foo import egg, spam')
        from foo import egg, spam
        >>> print AstPrinter()('from foo import *')
        from foo import *
        >>> print AstPrinter()('from foo import egg as bar, spam')
        from foo import egg as bar, spam
        """
        names = []
        for old, new in node.names :
            if new is None :
                names.append(old)
            else :
                names.append("%s as %s" % (old, new))
        return "from %s import %s" % (node.modname, ", ".join(names))
    def _print_args (self, argnames, defaults, flags) :
        "format arguments from a function definition"
        argnames = argnames[:]
        larg, karg = [], []
        if flags & compiler.ast.CO_VARKEYWORDS :
            karg = ["**" + argnames.pop(-1)]
        if flags & compiler.ast.CO_VARARGS :
            larg = ["*" + argnames.pop(-1)]
        args = argnames[:len(argnames) - len(defaults)]
        args.extend("%s=%s" % (a, self[d])
                    for a, d in reversed(zip(reversed(argnames),
                                             reversed(defaults))))
        args.extend(larg + karg)
        return ", ".join(args)
    def _Function_ (self, node) :
        """function definition
        # Function attributes
        #     name             name used in def, a string
        #     argnames         list of argument names, as strings
        #     defaults         list of default values
        #     flags            xxx
        #     doc              doc string, a string or <code>None</code>
        #     code             the body of the function
        >>> print AstPrinter()('def f (x, y) :\\n'
        ...                    '    "hello"\\n'
        ...                    '    return x + y')
        def f (x, y):
            'hello'
            return (x) + (y)
        >>> print AstPrinter()('def f (x, y=1, z=2) :\\n'
        ...                    '    "hello"\\n'
        ...                    '    return x + y')
        def f (x, y=1, z=2):
            'hello'
            return (x) + (y)
        >>> print AstPrinter()('def f (x, y=1, z=2, *l) :\\n'
        ...                    '    "hello"\\n'
        ...                    '    return x + y')
        def f (x, y=1, z=2, *l):
            'hello'
            return (x) + (y)
        >>> print AstPrinter()('def f (x, y=1, z=2, **d) :\\n'
        ...                    '    "hello"\\n'
        ...                    '    return x + y')
        def f (x, y=1, z=2, **d):
            'hello'
            return (x) + (y)
        >>> print AstPrinter()('def f (x, y=1, z=2, *l, **d) :\\n'
        ...                    '    "hello"\\n'
        ...                    '    return x + y')
        def f (x, y=1, z=2, *l, **d):
            'hello'
            return (x) + (y)
        """
        args = self._print_args(node.argnames, node.defaults, node.flags)
        parts = ["def %s (%s):" % (node.name, args)]
        if node.doc is not None :
            parts.append(self.indent(repr(node.doc)))
        parts.append(self.indent(self[node.code]))
        return "\n".join(parts)
    def _GenExpr_ (self, node) :
        """generator expression
        # GenExpr attributes
        #    code
        >>> print AstPrinter()('(x**2 for x in l if x % 2)')
        ([(x) ** (2) for x in (l) if ((x) % (2))])
        """
        return "(%s)" % self[node.code]
    def _GenExprInner_ (self, node) :
        """generator expression (body)
        # GenExprInner attributes
        #     expr
        #     quals
        >>> print AstPrinter()('(x**2 for x in l if x % 2)')
        ([(x) ** (2) for x in (l) if ((x) % (2))])
        """
        return "[%s %s]" % (self[node.expr],
                            " ".join(self[q] for q in node.quals))
    def _GenExprFor_ (self, node) :
        """generator expression (loop)
        # GenExprFor attributes
        #     assign
        #     iter
        #     ifs
        >>> print AstPrinter()('(x**2 for x in l if x % 2)')
        ([(x) ** (2) for x in (l) if ((x) % (2))])
        """
        if len(node.ifs) == 0 :
            return "for %s in (%s)" % (self[node.assign], self[node.iter])
        else :
            return "for %s in (%s) %s" % (self[node.assign],
                                          self[node.iter],
                                          " ".join(self[i] for i in node.ifs))
    def _GenExprIf_ (self, node) :
        """generator expression (condition)
        # GenExprIf attributes
        #     test
        >>> print AstPrinter()('(x**2 for x in l if x % 2)')
        ([(x) ** (2) for x in (l) if ((x) % (2))])
        """
        return "if (%s)" % self[node.test]
    def _Getattr_ (self, node) :
        """attribute lookup
        # Getattr attributes
        #     expr
        #     attrname
        >>> print AstPrinter()('a.x')
        (a).x
        """
        return "(%s).%s" % (self[node.expr], node.attrname)
    def _Global_ (self, node) :
        """global statement
        # Global attributes
        #     names
        >>> print AstPrinter()('global x, y')
        global x, y
        """
        return "global " + ", ".join(node.names)
    def _If_ (self, node) :
        """if statement
        # If attributes
        #     tests
        #     else_
        >>> print AstPrinter()('if x: y')
        if x:
            y
        >>> print AstPrinter()('if x: y\\nelse: z')
        if x:
            y
        else:
            z
        >>> print AstPrinter()('if x: y\\nelif a:b\\nelse: z')
        if x:
            y
        elif a:
            b
        else:
            z
        """
        _if = "if"
        parts = []
        for c, s in node.tests :
            parts.extend(["%s %s:" % (_if, self[c]),
                          self.indent(self[s])])
            _if = "elif"
        if node.else_ is not None :
            parts.extend(["else:",
                          self.indent(self[node.else_])])
        return "\n".join(parts)
    def _IfExp_ (self, node) :
        """conditional expression
        # IfExp attributes
        #     test
        #     then
        #     else_
        >>> print AstPrinter()('1 if x else 2')
        1 if x else 2
        """
        return "%s if %s else %s" % (self[node.then],
                                     self[node.test],
                                     self[node.else_])
    def _Import_ (self, node) :
        """import statement
        # Import attributes
        #     names
        >>> print AstPrinter()('import foo, bar')
        import foo, bar
        >>> print AstPrinter()('import foo as bar')
        import foo as bar
        """
        parts = []
        for old, new in node.names :
            if new is None :
                parts.append(old)
            else :
                parts.append("%s as %s" % (old, new))
        return "import " + ", ".join(parts)
    def _Invert_ (self, node) :
        """binary negation
        # Invert attributes
        #     expr
        >>> print AstPrinter()('~0')
        ~(0)
        """
        return "~(%s)" % self[node.expr]
    def _Keyword_ (self, node) :
        """keyword parameter
        # Keyword attributes
        #     name
        #     expr
        >>> print AstPrinter()('f(x=2, y=3)')
        (f)(x=(2), y=(3))
        """
 	return "%s=(%s)" % (node.name, self[node.expr])
    def _Lambda_ (self, node) :
        """lambda expression
        # Lambda attributes
        #     argnames
        #     defaults
        #     flags
        #     code
        >>> print AstPrinter()('lambda x, y: 0')
        lambda x, y: 0
        >>> print AstPrinter()('lambda x, y=1: 0')
        lambda x, y=1: 0
        >>> print AstPrinter()('lambda x, *y: 0')
        lambda x, *y: 0
        >>> print AstPrinter()('lambda x, **y: 0')
        lambda x, **y: 0
        >>> print AstPrinter()('lambda x, *y, **z: 0')
        lambda x, *y, **z: 0
        """
        return "lambda %s: %s" % (self._print_args(node.argnames,
                                                   node.defaults,
                                                   node.flags),
                                  self[node.code])
    def _LeftShift_ (self, node) :
        """binary left shift
        # LeftShift attributes
        #     left
        #     right
        >>> print AstPrinter()('x << y')
        (x) << (y)
        """
 	return "(%s) << (%s)" % (self[node.left], self[node.right])
    def _List_ (self, node) :
        """list
        # List attributes
        #     nodes
        >>> print AstPrinter()('[1, 2, 3]')
        [(1), (2), (3)]
        """
        return "[%s]" % ", ".join("(%s)" % self[n] for n in node.nodes)
    def _ListComp_ (self, node) :
        """list comprehension
        # ListComp attributes
        #     expr
        #     quals
        >>> print AstPrinter()('[x+1 for x in range(10)]')
        [(x) + (1) for x in ((range)(10))]
        >>> print AstPrinter()('[x+y for x in range(10) for y in range(5)]')
        [(x) + (y) for x in ((range)(10)) for y in ((range)(5))]
        >>> print AstPrinter()('[x+1 for x in range(10) if x % 2]')
        [(x) + (1) for x in ((range)(10)) if ((x) % (2))]
        """
        return "[%s %s]" % (self[node.expr],
                            " ".join(self[q] for q in node.quals))
    def _ListCompFor_ (self, node) :
        """loop (in list comprehension)
        # ListCompFor attributes
        #     assign
        #     list
        #     ifs
        >>> print AstPrinter()('[x+1 for x in range(10)]')
        [(x) + (1) for x in ((range)(10))]
        >>> print AstPrinter()('[x+1 for x in range(10) if x % 2]')
        [(x) + (1) for x in ((range)(10)) if ((x) % (2))]
        """
        if len(node.ifs) == 0 :
            return "for %s in (%s)" % (self[node.assign], self[node.list])
        else :
            return "for %s in (%s) %s" % (self[node.assign],
                                          self[node.list],
                                          " ".join(self[i] for i in node.ifs))
    def _ListCompIf_ (self, node) :
        """test (in list comprehension)
        # ListCompIf attributes
        #     test
        >>> print AstPrinter()('[x+1 for x in range(10) if x % 2]')
        [(x) + (1) for x in ((range)(10)) if ((x) % (2))]
        >>> print AstPrinter()('[x+1 for x in range(10) if x % 2 if x % 3]')
        [(x) + (1) for x in ((range)(10)) if ((x) % (2)) if ((x) % (3))]
        """
        return "if (%s)" % self[node.test]
    def _Mod_ (self, node) :
        """modulo
        # Mod attributes
        #     left
        #     right
        >>> print AstPrinter()('x % y')
        (x) % (y)
        """
        return "(%s) %% (%s)" % (self[node.left], self[node.right])
    def _Module_ (self, node) :
        """module content
        # Module attributes
        #     doc              doc string, a string or None
        #     node             body of the module, a Stmt
        >>> print AstPrinter()('x=2')
        x = 2
        >>> print AstPrinter()('"hello"\\nx=2')
        'hello'
        x = 2
        """
        if node.doc is None :
            return self[node.node]
        else :
            return "%r\n%s" % (node.doc, self[node.node])
    def _Mul_ (self, node) :
        """multiplication
        # Mul attributes
        #     left
        #     right
        >>> print AstPrinter()('1 * 2')
        (1) * (2)
        """
        return "(%s) * (%s)" % (self[node.left], self[node.right])
    def _Name_ (self, node) :
        """variable name
        # Name attributes
        #     name
        >>> print AstPrinter()('x')
        x
        """
        return node.name
    def _Not_ (self, node) :
        """boolean negation
        # Not attributes
        #     expr
        >>> print AstPrinter()('not b')
        not (b)
        """
        return "not (%s)" % self[node.expr]
    def _Or_ (self, node) :
        """boolean or
        # Or attributes
        #     nodes
        >>> print AstPrinter()('a or b or c')
        (a) or (b) or (c)
        """
        return " or ".join("(%s)" % self[n] for n in node.nodes)
    def _Pass_ (self, node) :
        """pass statement
        # Pass attributes
        >>> print AstPrinter()('pass')
        pass
        """
        return "pass"
    def _Power_ (self, node) :
        """exponentiation
        # Power attributes
        #     left
        #     right
        >>> print AstPrinter()('1 ** 2')
        (1) ** (2)
        """
        return "(%s) ** (%s)" % (self[node.left], self[node.right])
    def _Print_ (self, node) :
        """print statement
        # Print attributes
        #     nodes
        #     dest
        >>> print AstPrinter()('print hello, world,')
        print hello, world,
        >>> print AstPrinter()('print >>stream, hello, world,')
        print >>stream, hello, world,
        """
        return self._Printnl_(node) + ","
    def _Printnl_ (self, node) :
        """print statement
        # Printnl attributes
        #     nodes
        #     dest
        >>> print AstPrinter()('print hello, world')
        print hello, world
        >>> print AstPrinter()('print >>stream, hello, world')
        print >>stream, hello, world
        """
        if node.dest is None :
            prnt = "print"
        else :
            prnt = "print >>%s," % self[node.dest]
        return "%s %s" % (prnt, ", ".join(self[n] for n in node.nodes))
    def _Raise_ (self, node) :
        """raise statement
        # Raise attributes
        #     expr1
        #     expr2
        #     expr3
        >>> print AstPrinter()('raise Exception')
        raise Exception
        >>> print AstPrinter()('raise Exception, msg')
        raise Exception, msg
        >>> print AstPrinter()('raise Exception, msg, tb')
        raise Exception, msg, tb
        """
        parts = []
        for expr in (node.expr1, node.expr2, node.expr3) :
            if expr is None :
                break
            parts.append(self[expr])
        return "raise " + ", ".join(parts)
    def _Return_ (self, node) :
        """return statement
        # Return attributes
        #     value
        >>> print AstPrinter()('return 1')
        return 1
        >>> print AstPrinter()('return')
        return None
        """
        return "return %s" % self[node.value]
    def _RightShift_ (self, node) :
        """binary right shift
        # RightShift attributes
        #     left
        #     right
        >>> print AstPrinter()('x >> y')
        (x) >> (y)
        """
 	return "(%s) >> (%s)" % (self[node.left], self[node.right])
    def _Slice_ (self, node) :
        """simple list slice
        # Slice attributes
        #     expr
        #     flags
        #     lower
        #     upper
        >>> print AstPrinter()('l[:]')
        (l)[:]
        >>> print AstPrinter()('l[x:]')
        (l)[x:]
        >>> print AstPrinter()('l[:x]')
        (l)[:x]
        >>> print AstPrinter()('l[x:y]')
        (l)[x:y]
        """
        if (node.lower is None) and (node.upper is None) :
            return "(%s)[:]" % self[node.expr]
        elif node.upper is None :
            return "(%s)[%s:]" % (self[node.expr], self[node.lower])
        elif node.lower is None :
            return "(%s)[:%s]" % (self[node.expr], self[node.upper])
        else :
            return "(%s)[%s:%s]" % (self[node.expr],
                                    self[node.lower],
                                    self[node.upper])
    def _Sliceobj_ (self, node) :
        """extended list slice
        # Sliceobj attributes
        #     nodes            list of statements
        >>> print AstPrinter()('l[1:2:3]')
        (l)[1:2:3]
        >>> print AstPrinter()('l[:2:3]')
        (l)[:2:3]
        >>> print AstPrinter()('l[1::3]')
        (l)[1::3]
        >>> print AstPrinter()('l[::3]')
        (l)[::3]
        >>> print AstPrinter()('l[:2:]')
        (l)[:2:]
        """
        parts = []
        for x in node.nodes :
            if isinstance(x, compiler.ast.Const) and x.value is None :
                parts.append("")
            else :
                parts.append(self[x])
        return ":".join(parts)
    def _Stmt_ (self, node) :
        """statement
        # Stmt attributes
        #     nodes
        >>> print AstPrinter()('x=1; y=2')
        x = 1
        y = 2
        """
        return "\n".join(self[n] for n in node.nodes)
    def _Sub_ (self, node) :
        """substraction
        # Sub attributes
        #     left
        #     right
        >>> print AstPrinter()('1 - 2')
        (1) - (2)
        """
        return "(%s) - (%s)" % (self[node.left], self[node.right])
    def _Subscript_ (self, node) :
        """container lookup
        # Subscript attributes
        #     expr
        #     flags
        #     subs
        >>> print AstPrinter()('l[0]')
        (l)[0]
        >>> print AstPrinter()('l[0, 1]')
        (l)[(0), (1)]
        """
        if len(node.subs) > 1 :
            return "(%s)[%s]" % (self[node.expr],
                                 ", ".join("(%s)" % self[s] for s in node.subs))
        else :
            return "(%s)[%s]" % (self[node.expr], self[node.subs[0]])
    def _TryExcept_ (self, node) :
        """try/except statement
        # TryExcept attributes
        #     body
        #     handlers
        #     else_
        >>> print AstPrinter()('try: hello\\n'
        ...                    'except NameError: pass\\n'
        ...                    'except TypeError, err: pass\\n'
        ...                    'except: pass\\n'
        ...                    'else: pass')
        try:
            hello
        except NameError:
            pass
        except TypeError, err:
            pass
        except:
            pass
        else:
            pass
        """
        parts = ["try:", self.indent(self[node.body])]
        for exc, name, stmt in node.handlers :
            if exc is None :
                parts.append("except:")
            elif name is None :
                parts.append("except %s:" % self[exc])
            else :
                parts.append("except %s, %s:" % (self[exc], self[name]))
            parts.append(self.indent(self[stmt]))
        if node.else_ is not None :
            parts.extend(["else:", self.indent(self[node.else_])])
        return "\n".join(parts)
    def _TryFinally_ (self, node) :
        """try/finally statement
        # TryFinally attributes
        #     body
        #     final
        >>> print AstPrinter()('try:\\n'
        ...                    '    hello\\n'
        ...                    'finally:\\n'
        ...                    '    pass')
        try:
            hello
        finally:
            pass
        """
        return "\n".join(["try:",
                          self.indent(self[node.body]),
                          "finally:",
                          self.indent(self[node.final])])
    def _Tuple_ (self, node) :
        """tuple
        # Tuple attributes
        #     nodes
        >>> AstPrinter()('(1,)')
        '((1),)'
        >>> AstPrinter()('(1, 2)')
        '((1), (2))'
        >>> AstPrinter()('()')
        '()'
        """
        if len(node.nodes) == 0 :
            return "()"
        elif len(node.nodes) == 1 :
            return "((%s),)" % self[node.nodes[0]]
        else :
            return "(%s)" % ", ".join("(%s)" % self[n] for n in node.nodes)
    def _UnaryAdd_ (self, node) :
        """arithmetic positive
        # UnaryAdd attributes
        #     expr
        >>> print AstPrinter()('+2')
        +(2)
        """
        return "+(%s)" % self[node.expr]
    def _UnarySub_ (self, node) :
        """arithmetic negation
        # UnarySub attributes
        #     expr
        >>> print AstPrinter()('-2')
        -(2)
        """
        return "-(%s)" % self[node.expr]
    def _While_ (self, node) :
        """while loop
        # While attributes
        #     test
        #     body
        #     else_
        >>> print AstPrinter()('while x == 0:\\n'
        ...                    '    print x\\n'
        ...                    'else:\\n'
        ...                    '    pass')
        while (x) == (0):
            print x
        else:
            pass
        """
        parts = ["while %s:" % self[node.test],
                 self.indent(self[node.body])]
        if node.else_ is not None :
            parts.extend(["else:",
                          self.indent(self[node.else_])])
        return "\n".join(parts)
    def _Yield_ (self, node) :
        """yield statement
        # Yield attributes
        #     value
        >>> print AstPrinter()('yield 5')
        yield 5
        """
        return "yield %s" % self[node.value]

class AstExpressionPrinter (AstPrinter) :
    """Parser that returns a text representation of the parsed source
    """
    def __call__ (self, expr) :
        """
        >>> print AstExpressionPrinter()('x + 1')
        (x) + (1)
        >>> print AstExpressionPrinter()('x = 1')
        Traceback (most recent call last):
          ...
        ParseError: not an expression 'x = 1'

        @param expr: expression to parse
        @type expr: C{str}
        @return: the same expression that has been parsed and reprinted
        @rtype: C{str}
        """
        ast = self.parser.parse(expr)
        if (len(ast.node.nodes) != 1
            or not isinstance(ast.node.nodes[-1], compiler.ast.Discard)) :
            raise ParseError, "not an expression %r" % expr
        return self[ast.node.nodes[0]]

def Renamer (convert, printer=AstPrinter) :
    """Construct a C{Printer} that allows for renaming variables.

    >>> r = Renamer({'x':'y'})
    >>> print r('x + yxy')
    (y) + (yxy)
    >>> print r('x = x+1')
    y = (y) + (1)
    >>> print r('class x : pass')
    class y:
        pass
    >>> print r('class C (x): pass')
    class C (y):
        pass
    >>> print r('from x import z')
    from y import z
    >>> print r('from z import x')
    from z import y
    >>> print r('def f(x): pass')
    def f (y):
        pass
    >>> print r('def x(): pass')
    def y ():
        pass
    >>> print r('global x, z')
    global y, z
    >>> print r('import x as z')
    import y as z
    >>> print r('import z as x')
    import z as y
    >>> print r('f(x=1)')
    (f)(y=(1))
    >>> print r('lambda x: x+1')
    lambda y: (y) + (1)

    @param convert: the dictionnary for renamings
    @type convert: C{{str: str}}
    """
    class AstRenamer (printer) :
        def _Name_ (self, node) :
            node.name =convert.get(node.name, node.name)
            return printer._Name_(self, node)
        def _AssName_ (self, node) :
            node.name =convert.get(node.name, node.name)
            return printer._AssName_(self, node)
        def _Class_ (self, node) :
            node.name = convert.get(node.name, node.name)
            return printer._Class_(self, node)
        def _From_ (self, node) :
            node.names = [(convert.get(old, old), convert.get(new, new))
                          for old, new in node.names]
            node.modname = convert.get(node.modname, node.modname)
            return printer._From_(self, node)
        def _Function_ (self, node) :
            node.argnames = [convert.get(n, n) for n in node.argnames]
            node.name = convert.get(node.name, node.name)
            return printer._Function_(self, node)
        def _Global_ (self, node) :
            node.names = [convert.get(n, n) for n in node.names]
            return printer._Global_(self, node)
        def _Import_ (self, node) :
            node.names = [(convert.get(old, old), convert.get(new, new))
                          for old, new in node.names]
            return printer._Import_(self, node)
        def _Keyword_ (self, node) :
            node.name = convert.get(node.name, node.name)
            return printer._Keyword_(self, node)
        def _Lambda_ (self, node) :
            node.argnames = [convert.get(n, n) for n in node.argnames]
            return printer._Lambda_(self, node)
    return AstRenamer()

def Names (printer=AstPrinter) :
    """Construct a C{Printer} that searches for variables.

    >>> n = Names()
    >>> n('x + y')
    set(['y', 'x'])
    >>> n('y = x+1')
    set(['y', 'x'])
    >>> n('class x : pass')
    set(['x'])
    >>> n('class C (x): pass')
    set(['x', 'C'])
    >>> n('from x import y')
    set(['y'])
    >>> n('from x import y as z')
    set(['z'])
    >>> n('def f(x, z=0): pass')
    set(['x', 'z', 'f'])
    >>> n('global x, y')
    set(['y', 'x'])
    >>> n('import x')
    set(['x'])
    >>> n('import x as y')
    set(['y'])
    >>> n('f(x=1)')
    set(['x', 'f'])
    >>> n('lambda x: x+y')
    set(['y', 'x'])

    @param printer: the Ast printer to use, default to C{AstPrinter}
    @type printer: C{AstPrinter}
    @return: a sub class of C{printer} that collects names
    @rtype: subclass of C{AstPrinter}
    """
    class AstNames (printer) :
        def _Name_ (self, node) :
            if node.name not in ("True", "False", "None") :
                self._vars.add(node.name)
            return printer._Name_(self, node)
        def _AssName_ (self, node) :
            self._vars.add(node.name)
            return printer._AssName_(self, node)
        def _Class_ (self, node) :
            self._vars.add(node.name)
            return printer._Class_(self, node)
        def _From_ (self, node) :
            self._vars.update(new or old for old, new in node.names)
            return printer._From_(self, node)
        def _Function_ (self, node) :
            self._vars.update(node.argnames)
            self._vars.add(node.name)
            return printer._Function_(self, node)
        def _Global_ (self, node) :
            self._vars.update(node.names)
            return printer._Global_(self, node)
        def _Import_ (self, node) :
            self._vars.update(new or old for old, new in node.names)
            return printer._Import_(self, node)
        def _Keyword_ (self, node) :
            self._vars.add(node.name)
            return printer._Keyword_(self, node)
        def _Lambda_ (self, node) :
            self._vars.update(node.argnames)
            return printer._Lambda_(self, node)
        def __call__ (self, expr) :
            self._vars = set()
            printer.__call__(self, expr)
            return self._vars
    return AstNames()

class Tree (object) :
    def __init__ (self, name, children=(), **attributes) :
        if "attributes" in attributes :
            raise ValueError, "reserved attribute"
        self.name = name
        self.children = list(children)
        self.attributes = dict(attributes)
        for attr, value in attributes.iteritems() :
            setattr(self, attr, value)
        self._prn = AstPrinter()
    def _ast2pnml (self, ast) :
        try :
            name = ast.__class__.__name__
            doc = inspect.getdoc(getattr(AstPrinter, "_%s_" % name))
            result = pnmlTree("python", None)
            result["class"] = name
            for line in (l.strip() for l in doc.splitlines()) :
                if line.startswith("#") :
                    parts = line.split()
                    if parts[1] == name :
                        continue
                    attr = getattr(ast, parts[1])
                    if isinstance(attr, (int, str, float, bool, type(None))) :
                        result[parts[1]] = repr(attr)
                    elif isinstance(attr, compiler.ast.Node) :
                        result.add_child(pnmlTree("attribute", None,
                                                  self._ast2pnml(attr),
                                                  name=parts[1]))
                    else :
                        result.add_child(pnmlTree("attribute", repr(attr),
                                                  name=parts[1]))
            return result
        except AttributeError :
            return pnmlTree("python", repr(ast))
    __pnmltag__ = "ast"
    def __pnmldump__ (self) :
        result = pnmlTree(self.__pnmltag__, None, name=self.name)
        for child in self.children :
            if isinstance(child, compiler.ast.Node) :
                tree = self._ast2pnml(child)
            else :
                tree = pnmlTree.from_obj(child)
            result.add_child(tree)
        for name, value in self.attributes.iteritems() :
            if isinstance(value, (int, str, float, bool, type(None))) :
                result[name] = str(value)
            elif isinstance(value, compiler.ast.Node) :
                result.add_child(pnmlTree("attribute", None,
                                          self._ast2pnml(value), name=name))
            else :
                result.add_child(pnmlTree("attribute", None,
                                          pnmlTree.from_obj(value), name=name))
        return result
    def copy (self) :
        return self.__class__(self.name, *self.children, **self.attributes)
    def __add__ (self, other) :
        result = self.copy()
        result.children = result.children + (other.copy(),)
        return result
    def __iter__ (self) :
        return iter(self.children)
    def __getitem__ (self, idx) :
        return self.children[idx]
    def __len__ (self) :
        return len(self.children)
    def __repr__ (self) :
        return "%s(%r, [%s], %s)" % (self.__class__.__name__, self.name,
                                     ", ".join(repr(c) for c in self.children),
                                     ", ".join("%s=%r" % a for a in self.attributes.iteritems()))

if __name__ == "__main__" :
    import doctest, sys, time
    print "*** building PlyParser LALR table"
    PlyParser()
    print "*** testing PlyParser"
    NativeParser = PlyParser
    start = time.time()
    doctest.testmod()
    stop = time.time()
    print "*** execution time:", stop - start, "second(s)"
