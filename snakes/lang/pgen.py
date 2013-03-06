"""A Python implementation of CPython's parser

This module is largely based on Jonathan Riehl's PyPgen included in
the Basil framework (http://code.google.com/p/basil).
"""

from snakes import SnakesError
from snakes.lang import ast
import tokenize, string, pprint, warnings, inspect, os.path
from snakes.compat import *

def warn (message) :
    """Issue a warning message.
    """
    warnings.warn(message, stacklevel=2)

class Token (str) :
    """A token from the lexer.

    Behaves as a string that is either the token value (if not empty),
    or the token name. Additional attributes allow to extract various
    information:

     - self.kind: token number (like tokenize.ENDMARKER)
       also available as int(self)
     - self.text: token text
     - self.srow: start row
     - self.scol: start column
     - self.erow: end row
     - self.ecol: end column
     - self.line: full line of text from which the token comes
     - self.name: token name (ie, tokenize.tok_name[self.kind])
     - self.lexer: the Tokenizer instance than produced this token
     - self.filename: input file from which the token comes (or
       '<string>' if None available)
    """
    def __new__ (cls, token, lexer) :
        """Create a new instance.

        __new__ is used instead of __init__ because str is a
        non-mutable object and this __init__ could not assign a str
        content. For more information see:

        http://docs.python.org/reference/datamodel.html#object.__new__
        """
        kind = token[0]
        text = token[1]
        name = lexer.tok_name[kind]
        self = str.__new__(cls, text or name)
        self.kind = kind
        self.text = text
        self.srow, self.scol = token[2]
        self.erow, self.ecol = token[3]
        self.line = token[4]
        self.name = name
        self.lexer = lexer
        try :
            self.filename = lexer.infile.name
        except :
            self.filename = "<string>"
        return self
    def __int__ (self) :
        """Coercion to int (return self.kind).
        """
        return self.kind

class Location (str) :
    """A position in a parsed file

    Used to aggregate the positions of all the tokens is a parse
    (sub)tree. The following attributes are available:

     - self.srow: start row
     - self.scol: start column
     - self.erow: end row
     - self.ecol: end column
     - self.filename: input file from which the token comes (or
       '<string>' if None available)
    """
    def __new__ (cls, first, last) :
        """Create a new instance

        Expected arguments:
         - first: the first Token or Location instance in the region
         - last: the last one
        """
        self = str.__new__(cls, "%s[%s:%s-%s:%s]"
                           % (first.filename, first.srow, first.scol,
                              last.erow, last.ecol))
        self.srow, self.scol = first.srow, first.scol
        self.erow, self.ecol = last.erow, last.ecol
        self.filename = first.filename
        self.lexer = first.lexer
        return self

class ParseError (SnakesError) :
    """Exception raised when parsing fails.

    It's better not to use SyntaxError because this soes not allows to
    distinguish when the text being parser has a syntax error from
    when because the parser itself has a syntax error.
    """
    def __init__ (self, token, expected=None, reason=None) :
        """Initialize a new instance.

        Expected arguments are:
         - token: the erroneous token (a Token instance)
         - expected: either a Token instance or a token kind (like
           tokenize.NAME) to indicated what was expected instead
        """
        self.token = token
        if expected is not None :
            expected = int(expected)
        self.expected = expected
        if token is None :
            pos = ""
        else :
            pos = "%s[%s:%s]: " % (token.filename, token.srow, token.scol)
        if reason is not None :
            msg = reason
        elif self.expected is not None :
            msg = ("expected %s but found %r" %
                   (token.lexer.tok_name[expected], token))
        else :
            msg = "unexpected token %r" % token
        SnakesError.__init__(self, pos + msg)

class Tokenizer (object) :
    """A simple lexical analyser based on Python's tokenize module.

    The differences with tokenize module are:
     - new simple tokens may be added (just strings, no regexps)
     - Python's token may be not included
     - tokens may be automatically skipped (removed from the output)
     - tokenize.OP kind is refined (eg, ':' gets kind tokenize.COLON)

    This class replaces two PyPgen elements:
     - module basil.lang.python.TokenUtils
     - module basil.lang.python.StdTokenizer
    """
    _pyopmap = {
        '(' : tokenize.LPAR,
        ')' : tokenize.RPAR,
        '[' : tokenize.LSQB,
        ']' : tokenize.RSQB,
        ':' : tokenize.COLON,
        ',' : tokenize.COMMA,
        ';' : tokenize.SEMI,
        '+' : tokenize.PLUS,
        '+=' : tokenize.PLUSEQUAL,
        '-' : tokenize.MINUS,
        '-=' : tokenize.MINEQUAL,
        '*' : tokenize.STAR,
        '**' : tokenize.DOUBLESTAR,
        '**=' : tokenize.DOUBLESTAREQUAL,
        '*=' : tokenize.STAREQUAL,
        '/' : tokenize.SLASH,
        '//' : tokenize.DOUBLESLASH,
        '//=' : tokenize.DOUBLESLASHEQUAL,
        '/=' : tokenize.SLASHEQUAL,
        '|' : tokenize.VBAR,
        '|=' : tokenize.VBAREQUAL,
        '&' : tokenize.AMPER,
        '&=' : tokenize.AMPEREQUAL,
        '<' : tokenize.LESS,
        '<=' : tokenize.LESSEQUAL,
        '<<' : tokenize.LEFTSHIFT,
        '<<=' : tokenize.LEFTSHIFTEQUAL,
        '>' : tokenize.GREATER,
        '>=' : tokenize.GREATEREQUAL,
        '>>' : tokenize.RIGHTSHIFT,
        '>>=' : tokenize.RIGHTSHIFTEQUAL,
        '=' : tokenize.EQUAL,
        '==' : tokenize.EQEQUAL,
        '.' : tokenize.DOT,
        '%' : tokenize.PERCENT,
        '%=' : tokenize.PERCENTEQUAL,
        '{' : tokenize.LBRACE,
        '}' : tokenize.RBRACE,
        '^' : tokenize.CIRCUMFLEX,
        '^=' : tokenize.CIRCUMFLEXEQUAL,
        '~' : tokenize.TILDE,
        '!=' : tokenize.NOTEQUAL,
        '<>' : tokenize.NOTEQUAL,
        '@' : tokenize.AT
        }
    def __init__ (self, python=True, opmap={}, skip=None, **extra) :
        """Initialize a new instance.

        Expected arguments are:
         - python: a bool to indicate whether to include or not
           Python's tokens (default to True)
         - opmap: a dict to map litteral tokens (given as '...' in the
           grammar) to token kinds (default to {}). This parameter is
           useful only to redefine Python's mapping
         - skip: a collection of tokens that the tokenizer will
           automatically skip (default to [COMMENT, NL])
         - additional keywords arguments allow to define new tokens,
           for instance, providing DOLLAR='$' defines a new token
           called 'DOLLAR' (its kind will be automatically computed)

        An instance of Tokenizer has the following attributes:
         - self.opmap: a dict mapping operators token literals to the
           corresponding kind, for instance, ':' is mapped to
           tokenize.COLON (this can be overridden using argument
           opmap)
         - self.tok_name: a replacement of tokenize.tok_name that also
           include the user-defined tokens
         - for each token called FOO (including user-defined ones), an
           attribute self.FOO hols the corresponding kind
        """
        self._python = python
        self._opmap = opmap.copy()
        if python :
            self.opmap = self._pyopmap.copy()
            self.opmap.update(opmap)
        else :
            self.opmap = opmap.copy()
        self.tok_name = {}
        self._extra = {}
        if python :
            for kind, name in tokenize.tok_name.items() :
                self.tok_name[kind] = name
                setattr(self, name, kind)
        if not hasattr(self, "NT_OFFSET") :
            self.NT_OFFSET = 256
        last = max(n for n in self.tok_name if n != self.NT_OFFSET)
        for shift, (name, txt) in enumerate(sorted(extra.items())) :
            #WARNING: sorted above is required to guaranty that extra
            # tokens will always get the same number (dict order is
            # not guaranteed)
            kind = last + shift
            if kind >= self.NT_OFFSET :
                raise TypeError("too many new tokens")
            self.tok_name[kind] = name
            setattr(self, name, kind)
            self._extra[txt] = kind
        self.opmap.update(self._extra)
        if skip is None :
            skip = [self.COMMENT, self.NL]
        self._skip = set(skip)
    def __repr__ (self) :
        """Encodes an instance as Python source code.

        Non-default arguments provided to the constructor are included
        so that exactly the same Tokenizer instance can be recovered
        from the returned source code.

        >>> print repr(Tokenizer())
        Tokenizer()
        >>> print repr(Tokenizer(DOLLAR='$'))
        Tokenizer(DOLLAR='$')
        >>> print repr(Tokenizer(skip=[], DOLLAR='$'))
        Tokenizer(skip=[], DOLLAR='$')
        """
        args = []
        if not self._python :
            args.append("python=%s" % self._python)
        if self._opmap :
            args.append("opmap=%r" % self._opmap)
        if self._skip != set([self.COMMENT, self.NL]) :
            args.append("skip=%r" % list(self._skip))
        args.extend("%s=%r" % (self.tok_name[kind], txt) for txt, kind
                    in self._extra.items())
        return "%s(%s)" % (self.__class__.__name__, ", ".join(args))
    def tokenize (self, stream) :
        """Break an input stream into tokens.

        Expected argument is:
         - stream: a file-like object (with a method readline)

        Return a generator of Token instances, ParseError is raised
        whenever an erroneous token is encountered.

        This is basically the same as tokenize.generate_tokens but:
         - the appropriate tokens are skipped
         - OP kind is converted according to self.opmap
         - user-defined tokens are handled

        During the iteration, two more attributes can be used:
         - self.last: last recognized token (ie, last yielded)
         - self.infile: the input stream passed to method tokenize
        """
        self.infile = stream
        self.last = None
        self.lines = []
        def readline () :
            self.lines.append(stream.readline())
            return self.lines[-1]
        err = self.ERRORTOKEN
        for token in tokenize.generate_tokens(readline) :
            if token[0] == err :
                try :
                    token = (self._extra[token[1]],) + token[1:]
                except :
                    raise ParseError(Token(token, self))
            elif token[0] in self._skip :
                try:
                    self.skip_token(Token(token, self))
                except :
                    pass
                continue
            elif token[0] == self.OP :
                token = (self.opmap[token[1]],) + token[1:]
            self.last = Token(token, self)
            yield self.last
    def skip_token (self, token) :
        pass

try :
    Tokenizer._pyopmap['`'] = tokenize.BACKQUOTE
except AttributeError :
    pass

class PgenParser (object) :
    """A parser for pgen files.

    The following grammar is used:

        mstart : ( rule | NEWLINE | newtok )* ENDMARKER
        newtok : '$' NAME STRING NEWLINE
        rule : NAME COLON rhs NEWLINE
        rhs := alt ( VBAR alt )*
        alt : item+
        item : LSQB rhs RSQB | atom ( STAR | PLUS )?
        atom : LPAR rhs RPAR | NAME | STRING

    With respect to PyPgen, an additional rule 'newtok' has been added
    to allow for user-defined tokens.

    This class is adapted from module basil.parsing.PgenParser, it has
    attributes MSTART, ..., provinding to the symbol numbers for the
    corresponding rules.
    """
    MSTART = 256
    RULE = 257
    RHS = 258
    ALT = 259
    ITEM = 260
    ATOM = 261
    NEWTOK = 262
    def __init__ (self) :
        self.lexer = Tokenizer(NEWTOK='$')
    def expect (self, expected, found) :
        if expected != found.kind :
            raise ParseError(found, expected=expected)
    @classmethod
    def parse (cls, filename) :
        """Parse a pgen file.

        Expected argument is:
         - filename: path of pgen file to be parsed

        Return a 2-tuple (G, T) where:
         - G is the grammar's syntax tree
         - T is a Tokenizer instance to be used with the parser
           generated from this grammar (ie, including all the required
           user-defined tokens)

        This is basically the only method that is needed:

        >>> mygrammar = PgenParser.parse('myfile.pgen')
        """
        return cls().parse_file(filename)
    def parse_file (self, filename) :
        """Parse a pgen file.

        Expected argument is:
         - filename: path of pgen file to be parsed

        Return a 2-tuple (g, t):
         - g: is the grammar's syntax tree
         - t: is a Tokenizer instance to be used with the parser
           generated from this grammar (ie, including all the required
           user-defined tokens)

        Recognize mstart : ( rule | NEWLINE )* ENDMARKER

        Like in PyPgen, the parser is recursive descendent, each rule
        'X' being recognized by a dedicated method 'handleX' (except
        for 'mstart'). Each such method expects a current token (or
        None if it has to be fetched from the tokenizer) and returns a
        2-tuple (R, T) where:
         - R is the resulting syntax tree
         - T is the new current token (or None)
        """
        self.infile = open(filename)
        self.tokens = self.lexer.tokenize(self.infile)
        extra = {}
        children = []
        current = next(self.tokens)
        while current.kind != self.lexer.ENDMARKER :
            if current.kind == self.lexer.NEWLINE :
                children.append((current, []))
                current = None
            elif current.kind == self.lexer.NEWTOK :
                name, text = self.handleNewtok(current)
                current = None
                extra[name] = text
            else :
                ruleResult, current = self.handleRule(current)
                children.append(ruleResult)
            if current is None :
                current = next(self.tokens)
        children.append((current, []))
        return (self.MSTART, children), Tokenizer(**extra)
    def handleNewtok (self, current=None) :
        """Recognize newtok : '$' NAME STRING NEWLINE

        Unlike the other 'handleX' methods, this one does not return a
        syntax tree because it implements a parsing directive.
        Instead, it returns a 2-tuple (N, S) where:
         - N is the user-defined token name
         - S is the token string value
        """
        if current is None :
            current = next(self.tokens)
        self.expect(self.lexer.NEWTOK, current)
        name = next(self.tokens)
        self.expect(self.lexer.NAME, name)
        text = next(self.tokens)
        self.expect(self.lexer.STRING, text)
        nl = next(self.tokens)
        self.expect(self.lexer.NEWLINE, nl)
        return name, compile(text, "<string>", "eval",
                             ast.PyCF_ONLY_AST).body.s
    def handleRule (self, current=None) :
        """Recognize rule : NAME COLON rhs NEWLINE
        """
        children = []
        if current is None :
            current = next(self.tokens)
        self.expect(self.lexer.NAME, current)
        children.append((current, []))
        current = next(self.tokens)
        self.expect(self.lexer.COLON, current)
        children.append((current, []))
        rhsResult, current = self.handleRhs()
        children.append(rhsResult)
        if current is None :
            current = next(self.tokens)
        self.expect(self.lexer.NEWLINE, current)
        children.append((current, []))
        result = (self.RULE, children)
        return result, None
    def handleRhs (self, current=None) :
        """Recognize rhs : alt ( VBAR alt )*
        """
        children = []
        altResult, current = self.handleAlt(current)
        children.append(altResult)
        if current is None :
            current = next(self.tokens)
        while current.kind == self.lexer.VBAR :
            children.append((current, []))
            altResult, current = self.handleAlt()
            children.append(altResult)
            if current is None :
                current = next(self.tokens)
        result = (self.RHS, children)
        return result, current
    def handleAlt (self, current=None) :
        """ Recognize alt : item+
        """
        children = []
        itemResult, current = self.handleItem(current)
        children.append(itemResult)
        if current is None :
            current = next(self.tokens)
        while current.kind in (self.lexer.LSQB, self.lexer.LPAR,
                               self.lexer.NAME, self.lexer.STRING) :
            itemResult, current = self.handleItem(current)
            children.append(itemResult)
            if current is None :
                current = next(self.tokens)
        return (self.ALT, children), current
    def handleItem (self, current=None) :
        """Recognize item : LSQB rhs RSQB | atom ( STAR | PLUS )?
        """
        children = []
        if current is None :
            current = next(self.tokens)
        if current.kind == self.lexer.LSQB :
            children.append((current, []))
            rhsResult, current = self.handleRhs()
            children.append(rhsResult)
            if current is None :
                current = next(self.tokens)
            self.expect(self.lexer.RSQB, current)
            children.append((current, []))
            current = None
        else :
            atomResult, current = self.handleAtom(current)
            children.append(atomResult)
            if current is None :
                current = next(self.tokens)
            if current.kind in (self.lexer.STAR, self.lexer.PLUS) :
                children.append((current, []))
                current = None
        return (self.ITEM, children), current
    def handleAtom (self, current=None) :
        """Recognize atom : LPAR rhs RPAR | NAME | STRING
        """
        children = []
        if current is None :
            current = next(self.tokens)
        tokType = current.kind
        if tokType == self.lexer.LPAR :
            children.append((current, []))
            rhsResult, current = self.handleRhs()
            children.append(rhsResult)
            if current is None :
                current = next(self.tokens)
            self.expect(self.lexer.RPAR, current)
            children.append((current, []))
        elif tokType == self.lexer.STRING :
            children.append((current, []))
        else :
            self.expect(self.lexer.NAME, current)
            children.append((current, []))
        return (self.ATOM, children), None

class Parser (object) :
    """A LL1 parser for a generated grammar.

    This class aggregates two elements from PyPgen:
     - module basil.lang.python.DFAParser
     - class basil.parsing.PyPgen.PyPgenParser

    The main differences are:
     - simplified interface
     - adapt to handle Token instances instead of 3-tuples (kind,
       text, lineno)
     - remove functions arguments that can now be retreived as
       instance attributes
     - use Python warnings instead of print statements
     - many minor code edits (for my own understanding)

    Docstrings are provided only for methods that did not have an
    equivalent in PyPgen or that have been changed in a significant
    way.
    """
    def __init__ (self, grammar, tokenizer) :
        """Initialize a new instance.

        Expected arguments are:
         - grammar: the gramar object as returned by PyPgen.grammar()
         - tokenizer: a Tokenizer instance suitable for this grammar
           (eg, that passed to PyPgen's constructor)
        """
        self.grammar = grammar
        self.start = grammar[2]
        self.stringMap = {}
        for dfa in self.grammar[0] :
            dfaType, dfaName = dfa[:2]
            self.stringMap[dfaName] = dfaType
        self.symbolMap = {}
        for dfa in self.grammar[0] :
            dfaType, dfaName = dfa[:2]
            self.symbolMap[dfaType] = dfaName
        self.tokenizer = tokenizer
        self.addAccelerators()
    def parseTokens (self, tokens, start=None) :
        """Parse a series of tokens.

        Expected arguments:
         - tokens: a generator of Token instances
         - start: the start symbol to be recognized (or None to use
           the default one)

        The token generator should provide only tokens that are
        compatible with the tokenizer passed to the Parser's
        constructor. Otherwise, ParseError will be raised as unknown
        tokens will be issued.
        """
        self.tokens = tokens
        return self._parse(start)
    def parseFile (self, filename, start=None) :
        """Parse a text file provided by its path.

        Expected arguments:
         - filename: a file name
         - start: the start symbol to be recognized (or None to use
           the default one)

        The start symbol may be provided by its number (int) or its
        name (str) as specified in the grammar.
        """
        self.tokens = self.tokenizer.tokenize(open(filename))
        return self._parse(start)
    def parseStream (self, stream, start=None) :
        """Parse text from an opened file.

        Expected arguments:
         - stream: a file-like object (with a method readline)
         - start: the start symbol to be recognized (or None to use
           the default one)

        The start symbol may be provided by its number (int) or its
        name (str) as specified in the grammar.
        """
        self.tokens = self.tokenizer.tokenize(stream)
        return self._parse(start)
    def parseString (self, text, start=None, filename="<string>") :
        """Parse text given as a string.

        Expected arguments:
         - text: a string-like object
         - start: the start symbol to be recognized (or None to use
           the default one)

        The start symbol may be provided by its number (int) or its
        name (str) as specified in the grammar.
        """
        data = io.StringIO(text)
        data.name = filename
        self.tokens = self.tokenizer.tokenize(data)
        return self._parse(start)
    def _parse (self, start=None) :
        """Main parsing method.

        Expected argument:
         - start: the start symbol to be recognized (or None to use
           the default one)

        The start symbol may be provided by its number (int) or its
        name (str) as specified in the grammar.
        """
        if start is None :
            start = self.start
        elif start in self.stringMap :
            start = self.stringMap[start]
        elif start not in self.symbolMap :
            raise ValueError("unknown start symbol %r" % start)
        tokens = self.tokens
        # initialize the parsing stack
        rootNode = ((start, None, 0), [])
        dfa = self.findDFA(start)
        self.stack = [(dfa[3][dfa[2]], dfa, rootNode)]
        # parse all of it
        result = self._LL1_OK
        while result == self._LL1_OK :
            result, expected = self.addToken(next(tokens))
        if result == self._LL1_DONE :
            return self._fix_locations(rootNode)
        elif result == self._LL1_SYNTAX :
            raise ParseError(self.tokenizer.last, expected=expected)
    def _tostrings (self, st) :
        """Substitute symbol numbers by strings in a syntax tree.

        Expected argument:
         - st: a syntax tree as returned by the parser
        """
        (kind, token, lineno), children = st
        if kind >= self.tokenizer.NT_OFFSET :
            name = self.symbolMap
        else :
            name = self.tokenizer.tok_name
        return ((name[kind], token, lineno),
                [self._tostrings(c) for c in children])
    def _fix_locations (self, st) :
        """Replaces None in non-terminal nodes by a Location instance.

        Expected argument:
         - st: a syntax tree as returned by the parser
        """
        (kind, token, lineno), children = st
        children = [self._fix_locations(c) for c in children]
        if kind >= self.tokenizer.NT_OFFSET :
            token = Location(children[0][0][1], children[-1][0][1])
        return ((kind, token, lineno), children)
    def pprint (self, st) :
        """Return a human-readable representation of a syntax tree.

        Expected argument:
         - st: a syntax tree as returned by the parser

        All symbol numbers are substituted by the corresponding names
        and the text is indented appropriately.
        """
        return pprint.pformat(self._tostrings(st))
    # the rest of the class has not changed too much
    def addAccelerators (self) :
        if self.grammar[-1] : # already has accelerators
            return
        dfas, labels, start, accel = self.grammar
        def handleState (state) :
            arcs, accel, accept = state
            accept = 0
            labelCount = len(labels)
            accelArray = [-1] * labelCount
            for arc in arcs :
                labelIndex, arrow = arc
                kind = labels[labelIndex][0]
                if arrow >= 128 :
                    warn("too many states (%d >= 128)!" % arrow)
                    continue
                if kind >= self.tokenizer.NT_OFFSET :
                    targetFirstSet = self.findDFA(kind)[4]
                    if kind - self.tokenizer.NT_OFFSET >= 128 :
                        warn("nonterminal too high (%d >= %d)!" %
                             (kind, 128 + self.tokenizer.NT_OFFSET))
                        continue
                    for ibit in range(labelCount) :
                        if self.testbit(targetFirstSet, ibit) :
                            accelVal = (arrow | 128 |
                                        ((kind - self.tokenizer.NT_OFFSET) << 8))
                            oldVal = accelArray[ibit]
                            if oldVal != -1 :
                                # XXX Make this error reporting more better.
                                oldType = oldVal >> 8
                                # FIXME: bug in the original source
                                #warn("ambiguity at bit %d (for %d: was to %x,"
                                #     " now to %x)."
                                #     % (ibit, states.index(state),
                                #        oldVal, accelVal))
                                warn("ambiguity at bit %d" % ibit)
                            accelArray[ibit] = (arrow | 128 |
                                                ((kind - self.tokenizer.NT_OFFSET) << 8))
                elif labelIndex == 0 :
                    accept = 1
                elif labelIndex >= 0 and labelIndex < labelCount :
                    accelArray[labelIndex] = arrow
            # Now compute the upper and lower bounds.
            accelUpper = labelCount
            while accelUpper > 0 and accelArray[accelUpper-1] == -1 :
                accelUpper -= 1
            accelLower = 0
            while accelLower < accelUpper and accelArray[accelLower] == -1 :
                accelLower += 1
            accelArray = accelArray[accelLower:accelUpper]
            return (arcs, (accelUpper, accelLower, accelArray), accept)
        def handleDFA (dfa) :
            kind, name, initial, states, first = dfa
            return (kind, name, initial, list(map(handleState, states)))
        self.grammar = (list(map(handleDFA, dfas)), labels, start, 1)
    _LL1_OK = 0   # replaced E_ prefix with _LL1_ to prevent potential
    _LL1_DONE = 1 # conflicts with grammar symbols
    _LL1_SYNTAX = 2
    def testbit (self, bitstr, ibit) :
        return (ord(bitstr[ibit >> 3]) & (1 << (ibit & 0x7))) != 0
    def classify (self, token) :
        labels = self.grammar[1]
        if token.kind == self.tokenizer.NAME :
            for i, label in enumerate(labels) :
                if (token.kind, token) == label :
                    return i
        for i, label in enumerate(labels) :
            if (token.kind == label[0]) and (label[1] is None) :
                return i
        return -1
    def findDFA (self, start) :
        return self.grammar[0][start - self.tokenizer.NT_OFFSET]
    def addToken (self, token) :
        stack = self.stack
        ilabel = self.classify(token)
        while True :
            state, dfa, parent = stack[-1]
            # Perform accelerator
            arcs, (accelUpper, accelLower, accelTable), accept = state
            if accelLower <= ilabel < accelUpper :
                accelResult = accelTable[ilabel - accelLower]
                if accelResult != -1 :
                    # Handle accelerator result
                    if accelResult & 128 :
                        # Push non-terminal
                        nt = (accelResult >> 8) + self.tokenizer.NT_OFFSET
                        arrow = accelResult & 127
                        nextDFA = self.findDFA(nt)
                        # INLINE PUSH
                        newAstNode = ((nt, None, token.srow), [])
                        parent[1].append(newAstNode)
                        stack[-1] = (dfa[3][arrow], dfa, parent)
                        stack.append((nextDFA[3][nextDFA[2]], nextDFA,
                                      newAstNode))
                        continue
                    # INLINE SHIFT
                    parent[1].append(((token.kind, token, token.srow), []))
                    nextState = dfa[3][accelResult]
                    stack[-1] = (nextState, dfa, parent)
                    state = nextState
                    while state[2] and len(state[0]) == 1 :
                        # INLINE POP
                        stack.pop(-1)
                        if not stack :
                            return self._LL1_DONE, None
                        else :
                            state, dfa, parent = stack[-1]
                    return self._LL1_OK, None
            if accept :
                stack.pop(-1)
                if not stack :
                    return self._LL1_SYNTAX, self.tokenizer.ENDMARKER
                continue
            if ((accelUpper < accelLower) and
                (self.grammar[1][accelLower][1] is not None)) :
                expected = self.grammar[1][accelLower][1]
            else :
                expected = None
            return self._LL1_SYNTAX, expected

class PyPgen (object) :
    """A grammar generator.

    This class aggregates two elements from PyPgen:
     - class basil.parsing.PyPgen.PyPgen
     - function basil.parsing.PyPgen.buildParser
     - parts of function basil.parsing.PyPgen.parserMain

    The main differences are:
     - simplified interface
     - adapt to handle Token instances instead of 3-tuples (kind,
       text, lineno)
     - remove functions arguments that can now be retreived as
       instance attributes
     - use Python warnings instead of print statements
     - many minor code edits (for my own understanding)

    Docstrings are provided only for methods that did not have an
    equivalent in PyPgen or that have been changed in a significant
    way.
    """
    def __init__ (self, gst, tokenizer) :
        """Initialize a new instance.

        Expected arguments are:
         - gst: the grammar's syntax tree as returned by
           PgenParser.parse()
         - tokenizer: a Tokenizer instance suitable for this grammar,
           also returned by PgenParser.parse()
        """
        self.tokenizer = tokenizer
        self.EMPTY = self.tokenizer.ENDMARKER
        self.gst = gst
        self.nfaGrammar = self.dfaGrammar = None
        self.nfa = None
        self.crntKind = self.tokenizer.NT_OFFSET
        self.operatorMap = tokenizer.opmap
    def grammar (self) :
        """Generate and return the grammar object.
        """
        nfaGrammar = self.handleStart(self.gst)
        grammar = self.generateDfaGrammar(nfaGrammar)
        self.translateLabels(grammar)
        self.generateFirstSets(grammar)
        grammar[0] = list(map(tuple, grammar[0]))
        # Trick to add accelerators at generation time: it's easier to
        # do it this way than to extract the required elements from
        # class Parser.
        return Parser(tuple(grammar), self.tokenizer).grammar
    def python (self, pgen="pgen", inline=False) :
        """Build and return Python code for parsing module.

        Expected arguments are:
         - pgen: the name of module pgen in the generated source
           (default to 'pgen')
         - inline: a bool value to indicate whether to import or
           inline pgen module in the generated code

        If inline=True, the generated code is much bigger but does not
        depend on any non-standard module.
        """
        pysrc = ("%(pgen)s"
                 "tokenizer = %(prefix)s%(tokenizer)r\n"
                 "grammar = %(grammar)s\n"
                 "parser = %(prefix)sParser(grammar, tokenizer)\n\n"
                 "if __name__ == '__main__' :\n"
                 "    # just for test purpose\n"
                 "    import sys, pprint\n"
                 "    st = parser.parseStream(sys.stdin)\n"
                 "    print(parser.pprint(st))\n")
        format = {"grammar" : pprint.pformat(self.grammar()),
                  "prefix" : pgen + ".",
                  "tokenizer" : self.tokenizer,
                  "pgen" : "import tokenize, %s\n\n" % pgen,
                  "inline" : "",
                  }
        if inline :
            format["prefix"] = ""
            source = inspect.getsource(inspect.getmodule(self))
            source = source.rsplit("if __name__ == '__main__' :", 1)[0]
            format["pgen"] = ("### module '%s.py' inlined\n"
                              "%s\n### end of '%s.py'\n\n"
                              % (pgen, source.rstrip(), pgen))
        return pysrc % format
    @classmethod
    def translate (cls, src, tgt=None, pgen="pgen", inline=False) :
        """Translate a pgen file to a Python file that implements the
        corresponding parser.

        Expected arguments are:
         - src: path of the pgen file
         - tgt: path of target Python file, if None, its name is
           derived from src (replacing its extension by .py)
         - pgen, inline: like in PyPgen.python()

        Warning: the output file is silently overwritten if it already
        exist.
        """
        if tgt is None :
            tgt = os.path.splitext(src)[0] + ".py"
        gst, tokenizer = PgenParser.parse(src)
        self = PyPgen(gst, tokenizer)
        outfile = open(tgt, "w")
        outfile.write(("# this file has been automatically generated running:\n"
                       "# %s\n\n") % " ".join(sys.argv))
        outfile.write(self.python(pgen, inline))
        outfile.close()
    # the rest of the class has not changed too much
    def addLabel (self, labelList, tokKind, tokName) :
        labelTup = (tokKind, tokName)
        if labelTup in labelList :
            return labelList.index(labelTup)
        labelIndex = len(labelList)
        labelList.append(labelTup)
        return labelIndex
    def handleStart (self, gst) :
        self.nfaGrammar = [[],[(self.tokenizer.ENDMARKER, "EMPTY")]]
        self.crntKind = self.tokenizer.NT_OFFSET
        kind, children = gst
        for child in children :
            if int(child[0]) == PgenParser.RULE :
                self.handleRule(child)
        return self.nfaGrammar
    def handleRule (self, gst) :
        # NFA := [ type : Int, name : String, [ STATE ], start : Int,
        #         finish : Int ]
        # STATE := [ ARC ]
        # ARC := ( labelIndex : Int, stateIndex : Int )
        ####
        # build the NFA shell
        self.nfa = [self.crntKind, None, [], -1, -1]
        self.crntKind += 1
        # work on the AST node
        kind, children = gst
        name, colon, rhs, newline = children
        self.nfa[1] = name[0]
        if (self.tokenizer.NAME, name[0]) not in self.nfaGrammar[1] :
            self.nfaGrammar[1].append((self.tokenizer.NAME, name[0]))
        start, finish = self.handleRhs(rhs)
        self.nfa[3] = start
        self.nfa[4] = finish
        # append the NFA to the grammar
        self.nfaGrammar[0].append(self.nfa)
    def handleRhs (self, gst) :
        kind, children = gst
        start, finish = self.handleAlt(children[0])
        if len(children) > 1 :
            cStart = start
            cFinish = finish
            start = len(self.nfa[2])
            self.nfa[2].append([(self.EMPTY, cStart)])
            finish = len(self.nfa[2])
            self.nfa[2].append([])
            self.nfa[2][cFinish].append((self.EMPTY, finish))
            for child in children[2:] :
                if int(child[0]) == PgenParser.ALT :
                    cStart, cFinish = self.handleAlt(child)
                    self.nfa[2][start].append((self.EMPTY, cStart))
                    self.nfa[2][cFinish].append((self.EMPTY, finish))
        return start, finish
    def handleAlt (self, gst) :
        kind, children = gst
        start, finish = self.handleItem(children[0])
        if len(children) > 1 :
            for child in children[1:] :
                cStart, cFinish = self.handleItem(child)
                self.nfa[2][finish].append((self.EMPTY, cStart))
                finish = cFinish
        return start, finish
    def handleItem (self, gst) :
        nodeKind, children = gst
        if int(children[0][0]) == PgenParser.ATOM :
            start, finish = self.handleAtom(children[0])
            if len(children) > 1 :
                # Short out the child NFA
                self.nfa[2][finish].append((self.EMPTY, start))
                if children[1][0].kind == self.tokenizer.STAR :
                    finish = start
        else :
            start = len(self.nfa[2])
            finish = start + 1
            self.nfa[2].append([(self.EMPTY, finish)])
            self.nfa[2].append([])
            cStart, cFinish = self.handleRhs(children[1])
            self.nfa[2][start].append((self.EMPTY, cStart))
            self.nfa[2][cFinish].append((self.EMPTY, finish))
        return start, finish
    def handleAtom (self, gst) :
        nodeKind, children = gst
        tok = children[0][0]
        if tok.kind == self.tokenizer.LPAR :
            start, finish = self.handleRhs(children[1])
        elif tok.kind in (self.tokenizer.STRING, self.tokenizer.NAME) :
            start = len(self.nfa[2])
            finish = start + 1
            labelIndex = self.addLabel(self.nfaGrammar[1], tok.kind, tok)
            self.nfa[2].append([(labelIndex, finish)])
            self.nfa[2].append([])
        return start, finish
    def generateDfaGrammar (self, nfaGrammar, start=None) :
        # See notes in pgen.lang.python.DFAParser for output schema.
        dfas = []
        for nfa in nfaGrammar[0] :
            dfas.append(self.nfaToDfa(nfa))
        kind = dfas[0][0]
        if start is not None :
            found = False
            for dfa in dfas :
                if dfa[1] == start :
                    kind = dfa[0]
                    found = True
                    break
            if not found :
                warn("couldn't find nonterminal %r, "
                     "using %r instead." % (start, dfas[0][1]))
        return [dfas, nfaGrammar[1][:], kind, 0]
    def addClosure (self, stateList, nfa, istate) :
        stateList[istate] = True
        arcs = nfa[2][istate]
        for label, arrow in arcs :
            if label == self.EMPTY :
                self.addClosure(stateList, nfa, arrow)
    def nfaToDfa (self, nfa) :
        tempStates = []
        crntTempState = [[False] * len(nfa[2]), [], False]
        self.addClosure(crntTempState[0], nfa, nfa[3])
        crntTempState[2] = crntTempState[0][nfa[4]]
        if crntTempState[2] :
            warn("nonterminal %r may produce empty." % nfa[1])
        tempStates.append(crntTempState)
        index = 0
        while index < len(tempStates) :
            crntTempState = tempStates[index]
            for componentState in range(len(nfa[2])) :
                if not crntTempState[0][componentState] :
                    continue
                nfaArcs = nfa[2][componentState]
                for label, nfaArrow in nfaArcs :
                    if label == self.EMPTY :
                        continue
                    foundTempArc = False
                    for tempArc in crntTempState[1] :
                        if tempArc[0] == label :
                            foundTempArc = True
                            break
                    if not foundTempArc :
                        tempArc = [label, -1, [False] * len(nfa[2])]
                        crntTempState[1].append(tempArc)
                    self.addClosure(tempArc[2], nfa, nfaArrow)
            for arcIndex in range(len(crntTempState[1])) :
                label, arrow, targetStateList = crntTempState[1][arcIndex]
                targetFound = False
                arrow = 0
                for destTempState in tempStates :
                    if targetStateList == destTempState[0] :
                        targetFound = True
                        break
                    arrow += 1
                if not targetFound :
                    assert arrow == len(tempStates)
                    tempState = [targetStateList[:], [],
                                 targetStateList[nfa[4]]]
                    tempStates.append(tempState)
                # Write arrow value back to the arc
                crntTempState[1][arcIndex][1] = arrow
            index += 1
        tempStates = self.simplifyTempDfa(nfa, tempStates)
        return self.tempDfaToDfa(nfa, tempStates)
    def sameState (self, s1, s2) :
        if len(s1[1]) != len(s2[1]) or s1[2] != s2[2] :
            return False
        for arcIndex in range(len(s1[1])) :
            arc1 = s1[1][arcIndex]
            arc2 = s2[1][arcIndex]
            if arc1[:-1] != arc2[:-1] :
                return False
        return True
    def simplifyTempDfa (self, nfa, tempStates) :
        changes = True
        deletedStates = []
        while changes :
            changes = False
            for i in range(1, len(tempStates)) :
                if i in deletedStates :
                    continue
                for j in range(i) :
                    if j in deletedStates :
                        continue
                    if self.sameState(tempStates[i], tempStates[j]) :
                        deletedStates.append(i)
                        for k in range(len(tempStates)) :
                            if k in deletedStates :
                                continue
                            for arc in tempStates[k][1] :
                                if arc[1] == i :
                                    arc[1] = j
                        changes = True
                        break
        for stateIndex in deletedStates :
            tempStates[stateIndex] = None
        return tempStates
    def tempDfaToDfa (self, nfa, tempStates) :
        dfaStates = []
        dfa = [nfa[0], nfa[1], 0, dfaStates, None]
        stateMap = {}
        tempIndex = 0
        for tempState in tempStates :
            if tempState is not None :
                stateMap[tempIndex] = len(dfaStates)
                dfaStates.append(([], (0,0,()), 0))
            tempIndex += 1
        for tempIndex in stateMap.keys() :
            stateList, tempArcs, accepting = tempStates[tempIndex]
            dfaStateIndex = stateMap[tempIndex]
            dfaState = dfaStates[dfaStateIndex]
            for tempArc in tempArcs :
                dfaState[0].append((tempArc[0], stateMap[tempArc[1]]))
            if accepting :
                dfaState[0].append((self.EMPTY, dfaStateIndex))
        return dfa
    def translateLabels (self, grammar) :
        tokenNames = list(self.tokenizer.tok_name.values())
        # Recipe 252143 (remixed for laziness)
        tokenValues = dict(([v, k] for k, v in
                            self.tokenizer.tok_name.items()))
        labelList = grammar[1]
        for labelIndex, (kind, name) in enumerate(labelList) :
            if kind == self.tokenizer.NAME :
                isNonTerminal = False
                for dfa in grammar[0] :
                    if dfa[1] == name :
                        labelList[labelIndex] = (dfa[0], None)
                        isNonTerminal = True
                        break
                if not isNonTerminal :
                    if name in tokenNames :
                        labelList[labelIndex] = (tokenValues[name], None)
                    else :
                        warn("can't translate NAME label '%s'" % name)
            elif kind == self.tokenizer.STRING :
                assert name[0] == name[-1]
                sname = name[1:-1]
                if (sname[0] in string.letters) or (sname[0] == "_") :
                    labelList[labelIndex] = (self.tokenizer.NAME, sname)
                elif sname in self.operatorMap :
                    labelList[labelIndex] = (self.operatorMap[sname],
                                             None)
                else :
                    warn("can't translate STRING label %s" % name)
        return grammar
    def calcFirstSet (self, grammar, dfa) :
        if dfa[4] == -1 :
            warn("left-recursion for %r" % dfa[1])
            return
        if dfa[4] != None :
            warn("re-calculating FIRST set for %r" % dfa[1])
        dfa[4] = -1
        symbols = []
        result = 0
        state = dfa[3][dfa[2]]
        for arc in state[0] :
            sym = arc[0]
            if sym not in symbols :
                symbols.append(sym)
                kind = grammar[1][sym][0]
                if kind >= self.tokenizer.NT_OFFSET :
                    # Nonterminal
                    ddfa = grammar[0][kind - self.tokenizer.NT_OFFSET]
                    if ddfa[4] == -1 :
                        warn("left recursion below %r" % dfa[1])
                    else :
                        if ddfa[4] == None :
                            self.calcFirstSet(grammar, ddfa)
                        result |= ddfa[4]
                else :
                    result |= 1 << sym
        dfa[4] = result
    def generateFirstSets (self, grammar) :
        dfas = grammar[0]
        index = 0
        while index < len(dfas) :
            dfa = dfas[index]
            if None == dfa[4] :
                self.calcFirstSet(grammar, dfa)
            index += 1
        for dfa in dfas :
            set = dfa[4]
            result = []
            while set > 0 :
                crntBits = set & 0xff
                result.append(chr(crntBits))
                set >>= 8
            properSize = (len(grammar[1]) / 8) + 1
            if len(result) < properSize :
                result.append('\x00' * (properSize - len(result)))
            dfa[4] = "".join(result)
        return grammar

if __name__ == '__main__' :
    # a simple CLI
    import sys, getopt
    tgt, pgen, inline = None, "snakes.lang.pgen", False
    try :
        opts, args = getopt.getopt(sys.argv[1:], "h",
                                   ["help", "inline", "output=",
                                    "pgen=", "start="])
        if ("-h", "") in opts or ("--help", "") in opts :
            opts = [("-h", "")]
            args = [None]
        elif not args :
            raise getopt.GetoptError("no input file provided"
                                     " (try -h to get help)")
        elif len(args) > 1 :
            raise getopt.GetoptError("more than one input file provided")
    except getopt.GetoptError :
        sys.stderr.write("%s: %s\n" % (__file__, sys.exc_info()[1]))
        sys.exit(1)
    for (flag, arg) in opts :
        if flag in ("-h", "--help") :
            print("""usage: %s [OPTIONS] INFILE
    Options:
        -h, --help         print this help and exit
        --inline           inline 'pgen.py' in the generated file
        --output=OUTPUT    set output file
        --pgen=PGEN        name of 'pgen' module in output file""" % __file__)
            sys.exit(0)
        elif flag == "--inline" :
            inline = True
        elif flag == "--output" :
            tgt = arg
        elif flag == "--pgen" :
            pgen = arg
    PyPgen.translate(args[0], tgt=tgt, pgen=pgen, inline=inline)
