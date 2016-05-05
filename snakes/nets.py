"""This is SNAKES' main module, it holds the various Petri net
elements: arcs, places, transitions, markings, nets themselves and
marking graphs.
"""

import re, operator, inspect
from snakes import *
from snakes.compat import *
from snakes.pnml import *
from snakes.data import *
from snakes.lang import *
from snakes.hashables import *
from snakes.typing import *

"""
## Auxiliary definitions ##
"""

class Evaluator (object) :
    """Evaluate expression or execute statements in shareable
    namespace. Instances of this class can be found in particular as
    attribute `globals` of many objects among which `PetriNet`.
    """
    def __init__ (self, *larg, **karg) :
        """Initialize like a dict
        """
        self._env = dict(*larg, **karg)
        self.attached = []
    def __call__ (self, expr, locals={}) :
        """Evaluate an expression, this is somehow equivalent to
        `eval(expr, self, locals)`

        @param expr: an expression suitable to `eval`
        @type expr: `str`
        @param locals: additional environment for local names
        @type locals: `dict`
        @return: the result of the evaluation
        @rtype: `object`
        """
        return eval(expr, self._env, locals)
    def declare (self, stmt, locals=None) :
        """Execute a statement, this is somehow equivalent to
        `exec(stmt, self, locals)`

        @param stmt: a statement suitable to `exec`
        @type stmt: `str`
        @param locals: additional environment for local names
        @type locals: `dict`
        """
        exec(stmt, self._env, locals)
    # apidoc skip
    def attach (self, other) :
        """Make this instance use the namespaces of another

        All the instances attached to this will also share the same
        namespace.
        """
        self._env = other._env
        other.attached.append(self)
        # FIXME: should not need to use list() to remove infinite recursion
        for e in list(self.attached) :
            e.attach(self)
    # apidoc skip
    def detach (self, other) :
        """Make this instance namespace independent
        """
        self._env = self._env.copy()
        other.attached.remove(self)
    def update (self, other) :
        """Update namespace from another evaluator or a dict

        @param other: another evaluator or a dict
        @type other: `Evaluator`
        """
        self._env.update(other._env)
    def copy (self) :
        """Copy the evaluator and its namespace

        @return: a copy of the evaluator
        @rtype: `Evaluator`
        """
        return self.__class__(self._env)
    def __contains__ (self, name) :
        """Test if a name is declared, like `dict.__contains__`
        """
        return name in self._env
    def __getitem__ (self, key) :
        """Return an item from namespace, like `dict.__getitem__` but
        keys must be strings (because they are names)
        """
        return self._env[key]
    def __setitem__ (self, key, val) :
        """Set an item in namespace, like `dict.__setitem__` but keys
        must be strings (because they are names)
        """
        self._env[key] = val
    def __iter__ (self) :
        """Iterate over namespace items (key/value pairs), like
        `dict.items`
        """
        return iter(self._env.items())
    def __eq__ (self, other) :
        """Test for equality of namespaces
        """
        return self._env == other._env
    def __ne__ (self, other) :
        """Test for inequality of namespaces
        """
        return not self.__eq__(other)

##
## net element
##


class NetElement (object) :
    """The base class for Petri net elements. This class is abstract
    and should not be instanciated.
    """
    # apidoc stop
    def __init__ (self) :
        """Abstract method

        >>> try : NetElement()
        ... except NotImplementedError : print(sys.exc_info()[1])
        abstract class
        """
        raise NotImplementedError("abstract class")
    def lock (self, name, owner, value=None) :
        """Lock the attribute `name` that becomes writeable only by
        `owner`, set its value if `value` is not `None`.

        @param name: the name of the attribute
        @type name: `str`
        @param owner: any value, usually the object instance that
            locks the attribute
        @type owner: `object`
        @param value: the value to assign to the attribute of `None`
            if no assignment is required
        @type value: `object`
        """
        if "_locks" not in self.__dict__ :
            self.__dict__["_locks"] = {"_locks" : self}
#         if name in self._locks and self._locks[name] is not owner :
#             raise ConstraintError, "'%s' already locked" % name
#         else :
#             self._locks[name] = owner
        if value is not None :
            self.__dict__[name] = value
    def unlock (self, name, owner, remove=False, value=None) :
        """Release a locked attribute, making it assignable or deletable
        from everywhere.

        @param name: the name of the attribute
        @type name: `str`
        @param owner: the value that was used to lock the attribute
        @type owner: `object`
        @param remove: `True` if the attribute as to be deleted once
            unlocked, `False` to keep it in the object
        @type remove: `bool`
        @param value: the value to assign to the attribute are `None`
            to do nothing special
        @type value: `object`
        """
        if "_locks" not in self.__dict__ :
            self.__dict__["_locks"] = {"_locks" : self}
#         if name in self._locks :
#             if self._locks[name] is not owner :
#                 raise ConstraintError, "wrong owner for '%s'" % name
#             else :
#                 del self._locks[name]
#                 if remove :
#                     del self.__dict__[name]
#                 if value is not None :
#                     self.__dict__[name] = value
#         else :
#             raise ConstraintError, "'%s' not locked" % name
    def __setattr__ (self, name, value) :
        """Assign attribute, taking care of locks

        Check whether the assignment is allowed or not, the owner may
        re-assign the attribute by using `lock` with its parameter
        `value` instead of a direct assignment.

        @param name: name of the attribute
        @type name: `str`
        @param value: value of the attribute
        @type value: `object`
        """
        if "_locks" in self.__dict__ and name in self._locks :
            raise AttributeError("'%s' locked" % name)
        else :
            self.__dict__[name] = value
    def __delattr__ (self, name) :
        """Delete attribute, taking care of locks

        Check whether the deletion is allowed or not, the owner may
        delete the attribute by using `unlock` with its parameter
        `remove` set to `True` instead of a direct deletion.

        @param name: name of the attribute
        @type name: `str`
        """
        if "_locks" in self.__dict__ and name in self._locks :
            raise AttributeError("'%s' locked" % name)
        else :
            del self.__dict__[name]

##
## tokens
##

class Token (NetElement) :
    """A container for one token value. This class is intended for
    internal use only in order to avoid some confusion when inserting
    arbitrary values in a place. End users will probably never need to
    use it directly.
    """
    def __init__ (self, value) :
        """Initialise the token

        >>> Token(42)
        Token(42)

        @param value: value of the token
        @type value: `object`
        """
        self.value = value
    # apidoc stop
    def __str__ (self) :
        """Simple string representation (that of the value)

        >>> str(Token(42))
        '42'

        @return: simple string representation
        @rtype: `str`
        """
        return str(self.value)
    def __repr__ (self) :
        """String representation suitable for `eval`

        >>> repr(Token(42))
        'Token(42)'

        @return: precise string representation
        @rtype: `str`
        """
        return "%s(%s)" % (self.__class__.__name__, repr(self.value))
    def __eq__ (self, other) :
        """Test token equality

        >>> Token(42) == Token(10)
        False
        >>> Token(42) == Token(42)
        True

        @param other: second argument of equality
        @type other: `Token`
        @return: `True` if token values are equal, `False` otherwise
        @rtype: `bool`
        """
        try :
            return self.value == other.value
        except AttributeError :
            return False
    def __ne__ (self, other) :
        """Test token inequality

        >>> Token(42) != Token(10)
        True
        >>> Token(42) != Token(42)
        False

        @param other: second argument of inequality
        @type other: `Token`
        @return: `True` if token values differ, `False` otherwise
        @rtype: `bool`
        """
        return not self.__eq__(other)
    def __hash__ (self) :
        """Hash a token

        This is done by hashing the value stored in the token

        >>> hash(Token(42)) == hash(42)
        True

        @return: hash value for the token
        @rtype: `int`
        """
        return hash(self.value)

class BlackToken (Token) :
    """The usual black token, an instance is available as member `dot`
    of module `snakes.nets`, which is also its string representation.
    Another object `tBlackToken` is available to be used as a place
    type.

    >>> BlackToken()
    dot
    >>> tBlackToken
    Instance(BlackToken)
    """
    # apidoc stop
    def __init__ (self) :
        """Initialise the token

        >>> BlackToken()
        dot
        """
        self.value = None
    def __repr__ (self) :
        """String representation suitable for `eval`

        Since `snakes.nets` sets `dot = BlackToken()`, the string
        representation is `'dot'`.

        >>> repr(BlackToken())
        'dot'

        @return: precise string representation
        @rtype: `str`
        """
        return "dot"
    def __str__ (self) :
        """Simple string representation (that of the value)

        Since `snakes.nets` sets `dot = BlackToken()`, the string
        representation is `'dot'`.

        >>> str(BlackToken())
        'dot'

        @return: simple string representation
        @rtype: `str`
        """
        return "dot"
    __pnmltag__ = "token"
    def __pnmldump__ (self) :
        """Dumps value to PNML tree

        >>> BlackToken().__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <token/>
        </pnml>
        """
        return Tree(self.__pnmltag__, None)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Load from a PNML tree

        >>> t = BlackToken().__pnmldump__()
        >>> BlackToken.__pnmlload__(t)
        dot
        """
        return cls()

dot = BlackToken()
tBlackToken = Instance(BlackToken)

"""
## Arcs annotations ##
"""

class ArcAnnotation (NetElement) :
    """An annotation on an arc.

    On input arcs (from a place to a transition), annotations may be
    values or variables, potentially nested in tuples. On output arcs
    (from a transition to a place), expressions are allowed, which
    corresponds to a computation.

    A class attribute `input_allowed` is set to `True` or `False`
    according to whether an annotation is allowed on input arcs.

    This class is abstract and should not be instantiated.
    """
    input_allowed = False
    def copy (self) :
        "Return a copy of the annotation."
        raise NotImplementedError("abstract method")
    def substitute (self, binding) :
        """Substitutes the variables in the annotation.

        @param binding: the substitution to apply
        @type binding: `Substitution`
        """
        raise NotImplementedError("abstract method")
    def replace (self, old, new) :
        """Returns a copy of the annotation in which the `old` annotation
        has been replaced by the `new` one.

        With non composite annotation, this will return a copy of the
        annotation if it is not the same as `old` otherwise it returns
        `new`. Composite annotations will replace there components.

        >>> Value(2).replace(Variable('x'), Value(5))
        Value(2)
        >>> Variable('x').replace(Variable('x'), Value(5))
        Value(5)
        >>> MultiArc([Value(2), Variable('x')]).replace(Variable('x'), Value(5))
        MultiArc((Value(2), Value(5)))
        >>> Test(Value(2)).replace(Variable('x'), Value(5))
        Test(Value(2))
        >>> Test(Variable('x')).replace(Variable('x'), Value(5))
        Test(Value(5))

        @param old: the annotation to be replaced
        @type old: `ArcAnnotation`
        @param new: the annotation to use instead of `old`
        @type new: `ArcAnnotation`
        """
        if old == self :
            return new
        else :
            return self.copy()
    def vars (self) :
        "Return the list of variables involved in the annotation."
        raise NotImplementedError("abstract method")
    # apidoc skip
    def __eq__ (self, other) :
        """Check for equality.

        @param other: the other object to compare with
        @type other: `ArcAnnotation`
        """
        raise NotImplementedError("abstract method")
    # apidoc skip
    def __hash__ (self) :
        """Computes a hash of the annotation

        Warning: must be consistent with equality, ie, two equal
        values must have the same hash.
        """
        raise NotImplementedError("abstract method")
    # apidoc skip
    def __ne__ (self, other) :
        """Check for difference.

        @param other: the other object to compare with
        @type other: `ArcAnnotation`
        """
        return not (self == other)
    def bind (self, binding) :
        """Return the value of the annotation evaluated through
        `binding`.

        >>> Expression('x+1').bind(Substitution(x=2))
        Token(3)

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a value
        """
        raise NotImplementedError("abstract method")
    def flow (self, binding) :
        """Return the flow of tokens implied by the annotation evaluated
        through `binding`.

        >>> Value(1).flow(Substitution(x=2))
        MultiSet([1])

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a multiset of values
        """
        return MultiSet(v.value for v in iterate(self.bind(binding)))
    def modes (self, values) :
        """Return the list of modes under which an arc with the
        annotation may flow the tokens in `values`. Each mode is a
        substitution indicating how to bind the annotation.

        >>> Variable('x').modes([1, 2, 3])
        [Substitution(x=1), Substitution(x=2), Substitution(x=3)]

        @param values: a collection of values
        @type values: `collection`
        @return: a list of substitutions
        """
        raise NotImplementedError("abstract method")

class Value (ArcAnnotation) :
    """A single token value.
    """
    input_allowed = True
    def __init__ (self, value) :
        """Initialise with the encapsulated value.

        @param value: the value of the token.
        @type value: `object`
        """
        self.value = value
    def copy (self) :
        """Return a copy of the value.

        >>> Value(5).copy()
        Value(5)

        @return: a copy of the value
        @rtype: `Value`
        """
        return self.__class__(self.value)
    __pnmltag__ = "value"
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump a `Value` as a PNML tree

        >>> Value(3).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
          <value>
            <object type="int">
              3
            </object>
          </value>
        </pnml>

        @return: PNML tree
        @rtype: `pnml.Tree`
        """
        return Tree(self.__pnmltag__, None, Tree.from_obj(self.value))
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create a `Value` from a PNML tree

        >>> t = Value(3).__pnmldump__()
        >>> Value.__pnmlload__(t)
        Value(3)

        @param tree: the tree to convert
        @type tree: `pnml.Tree`
        @return: the value built
        @rtype: `Value`
        """
        return cls(tree.child().to_obj())
    # apidoc skip
    def __str__ (self) :
        """Concise string representation

        This is the string representation of the encapsulated value.

        >>> print(str(Value(42)))
        42
        >>> print(str(Value('hello')))
        'hello'

        @return: concise string representation
        @rtype: `str`
        """
        if isinstance(self.value, str) :
            return repr(self.value)
        else :
            return str(self.value)
    # apidoc skip
    def __repr__ (self) :
        """String representation suitable for `eval`

        >>> print(repr(Value(42)))
        Value(42)
        >>> print(repr(Value('hello')))
        Value('hello')

        @return: precise string representation
        @rtype: `str`
        """
        return "%s(%s)" % (self.__class__.__name__, repr(self.value))
    def vars (self) :
        """Return the list of variables involved in the value (empty).

        >>> Value(42).vars()
        []

        @return: empty list
        @rtype: `list`
        """
        return []
    # apidoc skip
    def __eq__ (self, other) :
        """Test for equality

        This tests the equality of encapsulated values

        >>> Value(42) == Value(42)
        True
        >>> Value(42) == Value(4)
        False

        @param other: second operand of the equality
        @type other: `Value`
        @return: `True` if encapsulated values are equal, `False`
            otherwise
        @rtype: `str`
        """
        try :
            return self.value == other.value
        except AttributeError :
            return False
    # apidoc skip
    def __hash__ (self) :
        return hash(self.value)
    def bind (self, binding) :
        """Return the value evaluated through `binding` (which is the
        value itself).

        >>> Value(1).bind(Substitution(x=2))
        Token(1)

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a value
        """
        return Token(self.value)
    def modes (self, values) :
        """Return an empty binding (no binding needed for values) iff the
        value is in `values`, raise ModeError otherwise.

        >>> Value(1).modes([1, 2, 3])
        [Substitution()]
        >>> try : Value(1).modes([2, 3, 4])
        ... except ModeError : print(sys.exc_info()[1])
        no match for value

        @param values: a collection of values
        @type values: `collection`
        @return: a list of substitutions
        @rtype: `list`
        @raise ModeError: when no suitable mode can be found
        """
        if self.value in values :
            return [Substitution()]
        else :
            raise ModeError("no match for value")
    def substitute (self, binding) :
        """Bind the value (nothing to do).

        >>> v = Value(5)
        >>> v.substitute(Substitution(x=5))
        >>> v
        Value(5)

        @param binding: a substitution
        @type binding: `Substitution`
        """
        pass

class Variable (ArcAnnotation) :
    "A variable which may be bound to a token."
    input_allowed = True
    syntax = re.compile("^[a-zA-Z]\w*$")
    def __init__ (self, name) :
        """Variable names must start with a letter and may continue with
        any alphanumeric character.

        >>> Variable('x')
        Variable('x')
        >>> try : Variable('_test')
        ... except ValueError: print(sys.exc_info()[1])
        not a variable name '_test'

        @param name: the name of the variable
        @type name: `str`
        """
        if not self.__class__.syntax.match(name) :
            raise ValueError("not a variable name '%s'" % name)
        self.name = name
    def copy (self) :
        """Return a copy of the variable.

        >>> Variable('x').copy()
        Variable('x')

        @return: a copy of the variable
        @rtype: `Variable`
        """
        return self.__class__(self.name)
    __pnmltag__ = "variable"
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump a `Variable` as a PNML tree

        >>> Variable('x').__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
          <variable>
            x
          </variable>
        </pnml>

        @return: PNML tree
        @rtype: `pnml.Tree`
        """
        return Tree(self.__pnmltag__, self.name)
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create a `Variable` from a PNML tree

        >>> t = Variable('x').__pnmldump__()
        >>> Variable.__pnmlload__(t)
        Variable('x')

        @param tree: the tree to convert
        @type tree: `pnml.Tree`
        @return: the variable built
        @rtype: `Variable`
        """
        return cls(tree.data)
    def rename (self, name) :
        """Change the name of the variable.

        >>> v = Variable('x')
        >>> v.rename('y')
        >>> v
        Variable('y')

        @param name: the new name of the variable
        @type name: `str`
        """
        self.__init__(name)
    # apidoc skip
    def __str__ (self) :
        """Concise string representation

        This is the name of the variable

        >>> str(Variable('x'))
        'x'

        @return: concise string representation
        @rtype: `str`
        """
        return self.name
    # apidoc skip
    def __repr__ (self) :
        """String representation suitable for `eval`

        >>> Variable('x')
        Variable('x')

        @return: precise string representation
        @rtype: `str`
        """
        return "Variable(%s)" % repr(self.name)
    def modes (self, values) :
        """Return the the list of substitutions mapping the name of the
        variable to each value in `values`.

        >>> Variable('x').modes(range(3))
        [Substitution(x=0), Substitution(x=1), Substitution(x=2)]

        @param values: a collection of values
        @type values: `collection`
        @return: a list of substitutions
        @rtype: `list`
        @raise ModeError: when no suitable mode can be found
        """
        result = [Substitution({self.name : v}) for v in values]
        if len(result) == 0 :
            raise ModeError("no value to bind")
        return result
    def bind (self, binding) :
        """Return the value of the variable evaluated through `binding`.

        >>> Variable('x').bind(Substitution(x=3))
        Token(3)
        >>> try : Variable('x').bind(Substitution(z=3))
        ... except DomainError : print(sys.exc_info()[1])
        unbound variable 'x'

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a value
        """
        return Token(binding[self.name])
    def substitute (self, binding) :
        """Change the name according to `binding`.

        >>> v = Variable('x')
        >>> v.substitute(Substitution(x='y'))
        >>> v
        Variable('y')
        >>> v.substitute(Substitution(x='z'))
        >>> v
        Variable('y')
        >>> v.rename('z')
        >>> v
        Variable('z')

        @param binding: a substitution
        @type binding: `Substitution`
        """
        self.rename(binding(self.name))
    def vars (self) :
        """Return variable name in a list.

        >>> Variable('x').vars()
        ['x']

        @return: a list holding the name of the variable
        @rtype: `list`
        """
        return [self.name]
    # apidoc skip
    def __eq__ (self, other) :
        """Test for equality

        >>> Variable('x') == Variable('x')
        True
        >>> Variable('x') == Variable('y')
        False

        @param other: right operand of equality
        @type other: `Variable`
        @return: `True` if variables have the same name, `False`
            otherwise
        @rtype: `bool`
        """
        try :
            return self.name == other.name
        except AttributeError :
            return False
    # apidoc skip
    def __hash__ (self) :
        return hash(self.name)

class Expression (ArcAnnotation) :
    """An arbitrary Python expression which may be evaluated.

    Each expression has its private namespace which can be extended or
    changed.
    """
    input_allowed = False
    def __init__ (self, expr) :
        """The expression is compiled so its syntax is checked.

        @param expr: a Python expression suitable for `eval`
        @type expr: `str`
        """
        self._expr = compile(expr, "<string>", "eval")
        self._str = expr.strip()
        self._true = (expr.strip() == "True")
        self.globals = Evaluator()
    def copy (self) :
        "Return a copy of the expression."
        return self.__class__(self._str)
    __pnmltag__ = "expression"
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump an `Expression` as a PNML tree

        @return: PNML tree
        @rtype: `pnml.Tree`

        >>> Expression('x+1').__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
          <expression>
            x+1
          </expression>
        </pnml>
        """
        return Tree(self.__pnmltag__, self._str)
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create an `Expression` from a PNML tree

        @param tree: the tree to convert
        @type tree: `pnml.Tree`
        @return: the expression built
        @rtype: `Expression`

        >>> t = Expression('x+1').__pnmldump__()
        >>> Expression.__pnmlload__(t)
        Expression('x+1')
        """
        return cls(tree.data)
    # apidoc skip
    def __str__ (self) :
        return self._str
    # apidoc skip
    def __repr__ (self) :
        return "%s(%s)" % (self.__class__.__name__, repr(self._str))
    def bind (self, binding) :
        """Evaluate the expression through `binding`.

        >>> e = Expression('x*(y-1)')
        >>> e.bind(Substitution(x=2, y=3))
        Token(4)
        >>> e.bind(Substitution(x=2))
        Traceback (most recent call last):
          ...
        NameError: name 'y' is not defined

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a value
        @raise NameError: when the domain of the substitution does not
            allow to bind all the names in the expression (so it
            cannot be evaluated)
        """
        if self._true :
            return Token(True)
        else :
            env = binding._dict
            env["__binding__"] = binding._dict
            try :
                return Token(self.globals(self._expr, env))
            finally :
                del env["__binding__"]
    def __call__ (self, binding) :
        """Returns the value from `bind` (but not encapsulated in a
        `Token`).
        """
        return self.bind(binding).value
    def substitute (self, binding) :
        """Substitute the variables according to 'binding'.

        >>> e = Expression('x+1*xy')
        >>> e.substitute(Substitution(x='y'))
        >>> e
        Expression('(y + (1 * xy))')

        As we can see, the substitution adds a lot of parentheses and
        spaces to the expression. But is really parses the expression
        and makes no confusion is a substritued name appears as a
        substrung of another name (like `y` that appears in `xy`
        above).

        @param binding: a substitution
        @type binding: `Substitution`
        """
        if not self._true :
            expr = rename(self._str, binding.dict())
            self._expr = compile(expr, "", "eval")
            self._str = expr.strip()
    def vars (self) :
        """Return the list of variable names involved in the expression.

        >>> list(sorted(Expression('x+y').vars()))
        ['x', 'y']

        @return: a list holding the names of the variables
        @rtype: `list`
        """
        return list(n for n in getvars(self._str) if n not in self.globals)
    def __and__ (self, other) :
        """Implement `&` to perform `and` between two expressions.

        >>> Expression('x==1') & Expression('y==2')
        Expression('(x==1) and (y==2)')

        Minor optimisation are implemented:

        >>> Expression('True') & Expression('x==y')
        Expression('x==y')
        >>> Expression('x==y') & Expression('True')
        Expression('x==y')

        @param other: an expression
        @type other: `Expression`
        @return: an expression
        @rtype: `Expression`
        @warning: it is not checked whether we combine boolean
            expressions or not (this is probably not implementable in
            a reasonable way)
        @note: unfortunately, Python does not let us override `and`
        """
        if self._true :
            return other.copy()
        elif other._true :
            return self.copy()
        else :
            result = self.__class__("(%s) and (%s)" % (self._str, other._str))
            result.globals.update(self.globals)
            result.globals.update(other.globals)
            return result
    def __or__ (self, other) :
        """Implement `|` to perform `or` between two expressions.

        >>> Expression('x==1') | Expression('y==2')
        Expression('(x==1) or (y==2)')

        Minor optimisation are implemented:

        >>> Expression('True') | Expression('x==y')
        Expression('True')
        >>> Expression('x==y') | Expression('True')
        Expression('True')

        @param other: an expression
        @type other: `Expression`
        @return: an expression
        @rtype: `Expression`
        @warning: it is not checked whether we combine boolean
            expressions or not (this is probably not implementable in
            a reasonable way)
        @note: unfortunately, Python does not let us override `or`
        """
        if self._true or other._true :
            return self.__class__("True")
        else :
            result = self.__class__("(%s) or (%s)" % (self._str, other._str))
            result.globals.update(self.globals)
            result.globals.update(other.globals)
            return result
    def __invert__ (self) :
        """Implement `~` to perform `not`.

        >>> ~Expression('x==1')
        Expression('not (x==1)')

        Minor optimisation are implemented:

        >>> ~Expression('True')
        Expression('False')
        >>> ~Expression('False')
        Expression('True')

        @return: an expression
        @rtype: `Expression`
        @warning: it is not checked whether we negate a boolean
            expression or not (this is probably not implementable in
            a reasonable way)
        @note: unfortunately, Python does not let us override `not`
        """
        if self._true :
            return self.__class__("False")
        elif self._str.strip() == "False" :
            return self.__class__("True")
        else :
            return self.__class__("not (%s)" % self._str)
    # apido skip
    def __eq__ (self, other) :
        try :
            return self._str.strip() == other._str.strip()
        except AttributeError :
            return False
    # apido skip
    def __hash__ (self) :
        return hash(self._str.strip())

class MultiArc (ArcAnnotation) :
    """A collection of other annotations, allowing to consume or produce
    several tokens at once.

    Such a collection is allowed on input arcs only if so are all its
    components.
    """
    input_allowed = False
    def __init__ (self, components) :
        """Initialise with the components of the tuple.

        >>> MultiArc((Value(1), Expression('x+1')))
        MultiArc((Value(1), Expression('x+1')))
        >>> MultiArc((Value(1), Expression('x+1'))).input_allowed
        False
        >>> MultiArc((Value(1), Variable('x'))).input_allowed
        True

        @param components: a list of components
        @type components: `collection`
        """
        if len(components) == 0 :
            raise ConstraintError("missing tuple components")
        self.input_allowed = reduce(operator.and_,
                                    [c.input_allowed for c in components])
        self._components = tuple(components)
        for c in components :
            if hasattr(c, "globals") :
                if not hasattr(self, "globals") :
                    self.globals = Evaluator()
                c.globals.attach(self.globals)
    def copy (self) :
        "Return a copy of the multi-arc."
        return self.__class__(tuple(x.copy() for x in self))
    __pnmltag__ = "multiarc"
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump a `MultiArc` as a PNML tree

        >>> MultiArc([Value(3), Expression('x+1')]).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
          <multiarc>
            <value>
              <object type="int">
                3
              </object>
            </value>
            <expression>
              x+1
            </expression>
          </multiarc>
        </pnml>

        @return: PNML tree
        @rtype: `pnml.Tree`
        """
        return Tree(self.__pnmltag__, None, *(Tree.from_obj(child)
                                              for child in self._components))
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create a `MultiArc` from a PNML tree

        >>> t = MultiArc((Value(3), Expression('x+1'))).__pnmldump__()
        >>> MultiArc.__pnmlload__(t)
        MultiArc((Value(3), Expression('x+1')))

        @param tree: the tree to convert
        @type tree: `pnml.Tree`
        @return: the multiarc built
        @rtype: `MultiArc`
        """
        return cls([child.to_obj() for child in tree])
    def __iter__ (self) :
        "Iterate over the components."
        return iter(self._components)
    def __len__ (self) :
        "Return the number of components"
        return len(self._components)
    # apidoc skip
    def __eq__ (self, other) :
        """
        >>> m = MultiArc([Value(dot), Value(dot)])
        >>> m == MultiArc([Value(dot), Value(dot)])
        True
        """
        try :
            if len(self._components) != len(other._components) :
                return False
        except AttributeError :
            return False
        return set(self._components) == set(other._components)
    # apidoc skip
    def __hash__ (self) :
        # 1575269934 = hash("snakes.nets.MultiArc")
        return reduce(operator.xor, (hash(c) for c in self._components),
                      1575269934)
    def __contains__ (self, item) :
        """Test if an item is part of the multi-arc
        """
        return item in self._components
    # apidoc skip
    def __str__ (self) :
        """
        >>> str(MultiArc((Value(1), Variable('x'))))
        '(1, x)'
        """
        if len(self._components) == 1 :
            return "(%s,)" % str(self._components[0])
        else :
            return "(%s)" % ", ".join(str(c) for c in self)
    # apidoc skip
    def __repr__ (self) :
        """
        >>> repr(MultiArc((Value(1), Variable('x'))))
        "MultiArc((Value(1), Variable('x')))"
        """
        if len(self._components) == 1 :
            return "%s((%s,))" % (self.__class__.__name__,
                                  repr(self._components[0]))
        else :
            return "%s((%s))" % (self.__class__.__name__,
                                 ", ".join(repr(c) for c in self))
    def flow (self, binding) :
        return reduce(MultiSet.__add__,
                      (c.flow(binding) for c in self._components))
    def bind (self, binding) :
        """Return the value of the annotation evaluated through
        `binding`.

        >>> t = MultiArc((Value(1), Variable('x'), Variable('y')))
        >>> t.bind(Substitution(x=2, y=3))
        (Token(1), Token(2), Token(3))

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a tuple of value
        """
        return tuple(c.bind(binding) for c in self)
    def modes (self, values) :
        """Return the list of modes under which an arc with the
        annotation may flow the tokens in `values`. Each mode is a
        substitution indicating how to bind the annotation.

        >>> t = MultiArc((Value(1), Variable('x'), Variable('y')))
        >>> m = t.modes([1, 2, 3])
        >>> len(m)
        2
        >>> Substitution(y=3, x=2) in m
        True
        >>> Substitution(y=2, x=3) in m
        True

        @param values: a collection of values
        @type values: `collection`
        @return: a list of substitutions
        """
        parts = []
        for x in self :
            m = x.modes(values)
            parts.append(m)
        vals = MultiSet(values)
        result = []
        for p in cross(parts) :
            try :
                sub = reduce(Substitution.__add__, p)
                if self.flow(sub) <= vals :
                    result.append(sub)
            except DomainError :
                pass
        return result
    def substitute (self, binding) :
        """Substitute each component according to 'binding'.

        >>> t = MultiArc((Value(1), Variable('x'), Variable('y')))
        >>> t.substitute(Substitution(x='z'))
        >>> t
        MultiArc((Value(1), Variable('z'), Variable('y')))

        @param binding: a substitution
        @type binding: `Substitution`
        """
        for x in self :
            x.substitute(binding)
    def vars (self) :
        """Return the list of variables involved in the components.

        >>> t = MultiArc((Value(1), Variable('x'), Variable('y')))
        >>> list(sorted(t.vars()))
        ['x', 'y']

        @return: the set of variables
        @rtype: `set`
        """
        result = set()
        for x in self :
            result.update(set(var for var in x.vars()))
        return list(result)
    def replace (self, old, new) :
        """Returns a copy of the annotation in which the `old` annotation
        has been replaced by the `new` one.

        With `MultiArc`, replaces each occurrence of `old` by `new`

        @param old: the annotation to be replaced
        @type old: `ArcAnnotation`
        @param new: the annotation to use instead of `old`
        @type new: `ArcAnnotation`
        """
        return self.__class__([x.replace(old, new) for x in self])

class Tuple (MultiArc) :
    """An annotation that that is a tuple of other annotations. This
    is a subclass of `MultiArc` only for programming convenience,
    actually, a `Tuple` instance carry a single token that is a
    `tuple`.

    >>> t = Tuple((Value(1), Variable('x'), Variable('y')))
    >>> m = t.modes([1, 2, (1, 2, 3), (3, 4, 5), (1, 2), (1, 2, 3, 4)])
    >>> m == [Substitution(x=2, y=3)]
    True

    As we can see, this binds the variables inside the tuple, but only
    token `(1, 2, 3)` is correct to match the annotation. Note that
    tuples may be nested arbitrarily.

    >>> pass
    >>> t = Tuple((Variable('x'), Value(3))).__pnmldump__()
    >>> t
    <?xml version="1.0" encoding="utf-8"?>
    <pnml>
     <tuple>
      <variable>
       x
      </variable>
      <value>
       <object type="int">
        3
       </object>
      </value>
     </tuple>
    </pnml>
    >>> Tuple.__pnmlload__(t)
    Tuple((Variable('x'), Value(3)))
    """
    __pnmltag__ = "tuple"
    # apidoc stop
    def modes (self, values) :
        result = []
        for tpl in values :
            if not isinstance(tpl, tuple) :
                continue
            elif len(tpl) != len(self._components) :
                continue
            try :
                modes = []
                for v, c in zip(tpl, self._components) :
                    modes.append(c.modes([v]))
                for p in cross(modes) :
                    try :
                        result.append(reduce(Substitution.__add__, p))
                    except DomainError :
                        pass
            except ModeError :
                pass
        if len(result) == 0 :
            raise ModeError("no mode found")
        return result
    def __str__ (self) :
        """
        >>> str(Tuple((Value(1), Variable('x'))))
        '(1, x)'
        """
        if len(self._components) == 1 :
            return "(%s,)" % str(self._components[0])
        else :
            return "(%s)" % ", ".join(str(c) for c in self)
    def flow (self, binding) :
        return MultiSet([tuple(p) for p in cross([x.flow(binding)
                                                  for x in self._components])])
    def bind (self, binding) :
        """Return the value of the annotation evaluated through
        `binding`.

        >>> t = Tuple((Value(1), Variable('x'), Variable('y')))
        >>> t.bind(Substitution(x=2, y=3))
        Token((1, 2, 3))

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a tuple of value
        """
        return Token(tuple(c.bind(binding).value for c in self))
    def __eq__ (self, other) :
        try :
            if len(self._components) != len(other._components) :
                return False
        except AttributeError :
            return False
        return self._components == other._components
    def __hash__ (self) :
        return hash(self._components)

class Test (ArcAnnotation) :
    """This is a test arc, that behaves like another arc annotation
    but never transport tokens. It is obtained by encapsulating the
    other annotation and behaves exactly like the encapsulated
    annotation except for method `flow` that always returns an empty
    multiset.
    """
    input_allowed = True
    def __init__ (self, annotation) :
        """Make a test arc from `annotation`.
        """
        self._annotation = annotation
        if hasattr(annotation, "globals") :
            self.globals = annotation.globals
    def copy (self) :
        "Return a copy of the test arc."
        return self.__class__(self._annotation)
    __pnmltag__ = "test"
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump a `Test` as a PNML tree

        @return: PNML tree
        @rtype: `pnml.Tree`

        >>> Test(Value(3)).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
          <test>
            <value>
              <object type="int">
                3
              </object>
            </value>
          </test>
        </pnml>
        """
        return Tree(self.__pnmltag__, None, Tree.from_obj(self._annotation))
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create a `Test` from a PNML tree

        @param tree: the tree to convert
        @type tree: `pnml.Tree`
        @return: the test arc built
        @rtype: `Test`

        >>> t = Test(Value(3)).__pnmldump__()
        >>> Test.__pnmlload__(t)
        Test(Value(3))
        """
        return cls(tree.child().to_obj())
    # apidoc skip
    def __str__ (self) :
        """
        >>> str(Test(Variable('x')))
        'x?'
        >>> str(Test(MultiArc((Variable('x'), Value(2)))))
        '(x, 2)?'
        >>> str(Test(Expression('x==1')))
        '(x==1)?'
        """
        s = str(self._annotation)
        if len(s) == 1 or (s[0] == "(" and s[-1] == ")"):
            return s + "?"
        else :
            return "(%s)?" % s
    # apidoc skip
    def __repr__ (self) :
        """
        >>> repr(Test(Variable('x')))
        "Test(Variable('x'))"
        >>> repr(Test(MultiArc((Variable('x'), Value(2)))))
        "Test(MultiArc((Variable('x'), Value(2))))"
        >>> repr(Test(Expression('x==1')))
        "Test(Expression('x==1'))"
        """
        return "%s(%s)" % (self.__class__.__name__, repr(self._annotation))
    # apidoc skip
    def substitute (self, binding) :
        """Substitutes the variables in the annotation.

        @param binding: the substitution to apply
        @type binding: `Substitution`
        """
        self._annotation.substitute(binding)
    # apidoc skip
    def vars (self) :
        "Return the list of variables involved in the annotation."
        return self._annotation.vars()
    # apidoc skip
    def __eq__ (self, other) :
        "Check for equality."
        try :
            return self._annotation == other._annotation
        except AttributeError :
            return False
    # apidoc skip
    def __hash__ (self) :
        return hash(("test", self._annotation))
    # apidoc skip
    def bind (self, binding) :
        """Return the value of the annotation evaluated through
        `binding`.

        >>> Test(Expression('x+1')).bind(Substitution(x=2))
        Token(3)

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a value
        """
        return self._annotation.bind(binding)
    def flow (self, binding) :
        """Return the flow of tokens implied by the annotation evaluated
        through `binding`. For test arcs, this is alwas empty.

        >>> Test(Value(1)).flow(Substitution())
        MultiSet([])

        @param binding: a substitution
        @type binding: `Substitution`
        @return: an empty multiset
        """
        return MultiSet()
    # apidoc skip
    def modes (self, values) :
        """Return the list of modes under which an arc with the
        annotation may flow the tokens in `values`. Each mode is a
        substitution indicating how to bind the annotation.

        >>> Test(Variable('x')).modes([1, 2, 3])
        [Substitution(x=1), Substitution(x=2), Substitution(x=3)]

        @param values: a collection of values
        @type values: `collection`
        @return: a list of substitutions
        """
        return self._annotation.modes(values)
    # apidoc skip
    def replace (self, old, new) :
        """Returns a copy of the annotation in which the `old` annotation
        has been replaced by the `new` one.

        With `Test`, always returns `Test(new)`

        @param old: the annotation to be replaced
        @type old: `ArcAnnotation`
        @param new: the annotation to use instead of `old`
        @type new: `ArcAnnotation`
        """
        return self.__class__(self._annotation.replace(old, new))

class Inhibitor (Test) :
    """This is an inhibitoir arc that forbids the presence of some
    tokens in a place.
    """
    input_allowed = True
    def __init__ (self, annotation, condition=None) :
        """Like `Test`, it works by encapsulating another annotation.
        Additionally, a condition may be given which allows to select
        the forbidden tokens more precisely. This is generally better
        to make this selection at this level rather that at the level
        of a transition guard: indeed, in the latter case, we may
        build many modes and reject most of them because of the guard;
        while in the former case, we will not build these modes at
        all.

        For instance:

          * `Inhibitor(Value(3))` ensures that there is no token whose
            value is `3` in the place when the transition is fired
          * `Inhibitor(Variable('x'))` ensures that there is no token
            at all in the place
          * `Inhibitor(Variable('x'), Expression('x<3'))` ensures that
            there is no token whose value is less that `3`
          * `Inhibitor(MultiArc([Variable('x'), Variable('y')]),
            Expression('x>y'))` ensures that there is no pair of
            tokens such that one is greater that the other
        """
        self._annotation = annotation
        if hasattr(annotation, "globals") :
            self.globals = annotation.globals
        if condition is None :
            condition = Expression("True")
        self._condition = condition
    # apidoc skip
    def copy (self) :
        "Return a copy of the inhibitor arc."
        return self.__class__(self._annotation, self._condition)
    __pnmltag__ = "inhibitor"
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump a `Inhibitor` as a PNML tree

        >>> Inhibitor(Value(3)).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <inhibitor>
          <annotation>
           <value>
            <object type="int">
             3
            </object>
           </value>
          </annotation>
          <condition>
           <expression>
            True
           </expression>
          </condition>
         </inhibitor>
        </pnml>

        @return: PNML tree
        @rtype: `pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree("annotation", None, Tree.from_obj(self._annotation)),
                    Tree("condition", None, Tree.from_obj(self._condition)))
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create a `Inhibitor` from a PNML tree

        >>> t = Inhibitor(Value(3)).__pnmldump__()
        >>> Inhibitor.__pnmlload__(t)
        Inhibitor(Value(3))
        >>> t = Inhibitor(Variable('x'), Expression('x>0')).__pnmldump__()
        >>> Inhibitor.__pnmlload__(t)
        Inhibitor(Variable('x'), Expression('x>0'))

        @param tree: the tree to convert
        @type tree: `pnml.Tree`
        @return: the inhibitor arc built
        @rtype: `Inhibitor`
        """
        return cls(tree.child("annotation").child().to_obj(),
                   tree.child("condition").child().to_obj())
    # apidoc skip
    def __str__ (self) :
        """
        >>> str(Inhibitor(Variable('x')))
        '{no x}'
        >>> str(Inhibitor(Variable('x'), Expression('x>0')))
        '{no x if x>0}'
        """
        if self._condition == Expression("True") :
            return "{no %s}" % self._annotation
        else :
            return "{no %s if %s}" % (self._annotation, self._condition)
    # apidoc skip
    def __repr__ (self) :
        """
        >>> repr(Inhibitor(Variable('x')))
        "Inhibitor(Variable('x'))"
        >>> repr(Inhibitor(Variable('x'), Expression('x>0')))
        "Inhibitor(Variable('x'), Expression('x>0'))"
        """
        if self._condition == Expression("True") :
            return "%s(%r)" % (self.__class__.__name__, self._annotation)
        else :
            return "%s(%r, %r)" % (self.__class__.__name__,
                                   self._annotation, self._condition)
    # apidoc skip
    def substitute (self, binding) :
        """Substitutes the variables in the annotation.

        @param binding: the substitution to apply
        @type binding: `Substitution`
        """
        self._annotation.substitute(binding)
        self._condition.substitute(binding)
    # apidoc skip
    def vars (self) :
        "Return the list of variables involved in the annotation."
        return list(set(self._annotation.vars()) | set(self._condition.vars()))
    # apidoc skip
    def __eq__ (self, other) :
        "Check for equality."
        try :
            return (self._annotation == other._annotation
                    and self._condition == other._condition)
        except AttributeError :
            return False
    # apidoc skip
    def __hash__ (self) :
        return hash(("inhibitor", self._annotation, self._condition))
    def bind (self, binding) :
        """Return no tokens since arc corresponds to an absence of tokens.
        Raise `ValueError` if this binding does not validate the
        condition.

        >>> Inhibitor(Expression('x+1'), Expression('x>0')).bind(Substitution(x=2))
        ()
        >>> try : Inhibitor(Expression('x+1'), Expression('x<0')).bind(Substitution(x=2))
        ... except ValueError : print(sys.exc_info()[1])
        condition not True for {x -> 2}

        @param binding: a substitution
        @type binding: `Substitution`
        @return: empty tuple

        """
        if self._condition(binding) :
            return ()
        else :
            raise ValueError("condition not True for %s" % str(binding))
    def modes (self, values) :
        """Return the list of modes under which an arc with the
        annotation may flow the tokens in `values`. Each mode is a
        substitution indicating how to bind the annotation.

        >>> try : Inhibitor(Value(1)).modes([1, 2, 3])
        ... except ModeError : print(sys.exc_info()[1])
        inhibited by {}
        >>> Inhibitor(Value(0)).modes([1, 2, 3])
        [Substitution()]
        >>> try : Inhibitor(Variable('x')).modes([1, 2, 3])
        ... except ModeError : print(sys.exc_info()[1])
        inhibited by {x -> 1}
        >>> Inhibitor(Variable('x'), Expression('x>3')).modes([1, 2, 3])
        [Substitution()]
        >>> try : Inhibitor(MultiArc([Variable('x'), Variable('y')]),
        ...                 Expression('x>y')).modes([1, 2, 3])
        ... except ModeError : print(sys.exc_info()[1])
        inhibited by {...}
        >>> Inhibitor(MultiArc([Variable('x'), Variable('y')]),
        ...           Expression('x==y')).modes([1, 2, 3])
        [Substitution()]

        @param values: a collection of values
        @type values: `collection`
        @return: a list of substitutions
        @rtype: `list`
        """
        try :
            modes = self._annotation.modes(values)
        except ModeError :
            return [Substitution()]
        for binding in modes :
            if self._condition(binding) :
                raise ModeError("inhibited by %s" % binding)
        return [Substitution()]
    # apidoc skip
    def replace (self, old, new) :
        """Returns a copy of the annotation in which the `old` annotation
        has been replaced by the `new` one.

        @param old: the annotation to be replaced
        @type old: `ArcAnnotation`
        @param new: the annotation to use instead of `old`
        @type new: `ArcAnnotation`
        """
        return self.__class__(self._annotation.replace(old, new),
                              self._condition.replace(old, new))

class Flush (ArcAnnotation) :
    """A flush arc used as on input arc will consume all the tokens in
    a place, binding this multiset to a variable. When used as an
    output arc, it will produce several tokens in the output place.
    """
    input_allowed = True
    def __init__ (self, expr) :
        """Build a flush arc from either a variable name or an
        expression. In the latter case, the annotation is only allowed
        to be used on output arcs.
        """
        try :
            self._annotation = Variable(expr)
        except :
            self._annotation = Expression(expr)
            self.globals = self._annotation.globals
        self.input_allowed = self._annotation.input_allowed
        self._expr = expr.strip()
    # apidoc skip
    def copy (self) :
        "Return a copy of the flush arc."
        return self.__class__(self._expr)
    # apidoc skip
    def __eq__ (self, other) :
        return ((isinstance(other, self.__class__)
                 or isinstance(self, other.__class__))
                and (self._expr == other._expr))
    # apidoc skip
    def __hash__ (self) :
        return hash(("flush", self._expr))
    __pnmltag__ = "flush"
    # apidoc skip
    def __pnmldump__ (self) :
        """
        >>> Flush('x').__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <flush>
          x
         </flush>
        </pnml>
        """
        return Tree(self.__pnmltag__, self._expr)
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> t = Flush('x').__pnmldump__()
        >>> Flush.__pnmlload__(t)
        Flush('x')
        """
        return cls(tree.data)
    # apidoc skip
    def __str__ (self) :
        """
        >>> str(Flush('x'))
        'x!'
        >>> str(Flush('x+x'))
        '(x+x)!'
        """
        s = str(self._annotation)
        if len(s) == 1 or (s[0] == "(" and s[-1] == ")"):
            return s + "!"
        else :
            return "(%s)!" % s
    # apidoc skip
    def __repr__ (self) :
        """
        >>> repr(Flush('x'))
        "Flush('x')"
        """
        return "%s(%s)" % (self.__class__.__name__, repr(self._expr))
    def modes (self, values) :
        """Return the list of modes under which an arc with the
        annotation may flow the tokens in `values`. Each mode is a
        substitution indicating how to bind the annotation. In the
        case of flush arcs, there will be only one mode that binds all
        the tokens in a multiset.

        >>> m = Flush('x').modes([1, 2, 3])
        >>> m
        [Substitution(x=MultiSet([...]))]
        >>> m[0]['x'] == MultiSet([1, 2, 3])
        True

        Take care that a flush arc allows to fire a transition by
        consuming no token in a place. This is different from usual
        arc annotation that require tokens to be present in input
        places.

        >>> Flush('x').modes([])
        [Substitution(x=MultiSet([]))]

        @param values: a collection of values
        @type values: `collection`
        @return: a list of substitutions
        @rtype: `list`
        """
        return [Substitution({self._annotation.name : MultiSet(values)})]
    def flow (self, binding) :
        """Return the flow of tokens implied by the annotation evaluated
        through `binding`.

        >>> Flush('x').flow(Substitution(x=MultiSet([1, 2, 3]))) == MultiSet([1, 2, 3])
        True

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a multiset
        """
        return MultiSet(self._annotation.bind(binding).value)
    def bind (self, binding) :
        """Return the value of the annotation evaluated through
        `binding`.

        >>> set(Flush('x').bind(Substitution(x=MultiSet([1, 2, 3])))) == set([Token(1), Token(2), Token(3)])
        True

        @param binding: a substitution
        @type binding: `Substitution`
        @return: a value
        """
        return tuple(Token(v) for v in self._annotation.bind(binding).value)
    # apidoc skip
    def vars (self) :
        """Return the list of variable names involved in the arc.

        >>> Flush('x').vars()
        ['x']

        @return: list of variable names
        @rtype: `list`
        """
        return self._annotation.vars()

"""
## Petri net nodes ##
"""


class Node (NetElement) :
    """A node in a Petri net.

    This class is abstract and should not be instanciated, use `Place`
    or `Transition` as concrete nodes.
    """
    def rename (self, name) :
        """Change the name of the node.

        >>> p = Place('p', range(3))
        >>> p.rename('egg')
        >>> p
        Place('egg', MultiSet([...]), tAll)
        >>> t = Transition('t', Expression('x==1'))
        >>> t.rename('spam')
        >>> t
        Transition('spam', Expression('x==1'))

        @param name: the new name of the node
        @type name: `str`
        """
        try :
            self.net.rename_node(self.name, name)
        except AttributeError :
            self.name = name

class Place (Node) :
    "A place of a Petri net."
    def __init__ (self, name, tokens=[], check=None) :
        """Initialise with name, tokens and typecheck. `tokens` may be
        a single value or an iterable object. `check` may be `None`
        (any token allowed) or a type from module `snakes.typing.

        >>> Place('p', range(3), tInteger)
        Place('p', MultiSet([...]), Instance(int))

        @param name: the name of the place
        @type name: `str`
        @param tokens: a collection of tokens that mark the place
        @type tokens: `collection`
        @param check: a constraint on the tokens allowed in the place
            (or `None` for no constraint)
        @type check: `Type`
        """
        self.name = name
        self.tokens = MultiSet()
        if check is None :
            self._check = tAll
        else :
            self._check = check
        self.add(tokens)
    def copy (self, name=None) :
        """Return a copy of the place, with no arc attached.

        >>> p = Place('p', range(3), tInteger)
        >>> n = p.copy()
        >>> n.name == 'p'
        True
        >>> n.tokens == MultiSet([0, 1, 2])
        True
        >>> n.checker()
        Instance(int)
        >>> n = p.copy('x')
        >>> n.name == 'x'
        True
        >>> n.tokens == MultiSet([0, 1, 2])
        True
        >>> n.checker()
        Instance(int)

        @param name: if not `None`, the name of the copy
        @type name: `str`
        @return: a copy of the place.
        @rtype: `Place`
        """
        if name is None :
            name = self.name
        return self.__class__(name, self.tokens, self._check)
    __pnmltag__ = "place"
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump a `Place` as a PNML tree

        >>> Place('p', [dot, dot], tBlackToken).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
          <place id="p">
            <initialMarking>
              <text>
                2
              </text>
            </initialMarking>
          </place>
        </pnml>
        >>> Place('p', [1, 2, 3], tNatural).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <place id="p">
          <type domain="intersection">
           <left>
            <type domain="instance">
             <object name="int" type="class"/>
            </type>
           </left>
           <right>
            <type domain="greatereq">
             <object type="int">
              0
             </object>
            </type>
           </right>
          </type>
          <initialMarking>
           <multiset>
           ...
           </multiset>
          </initialMarking>
         </place>
        </pnml>

        @return: PNML tree
        @rtype: `pnml.Tree`
        """
        result = Tree(self.__pnmltag__, None, id=self.name)
        if (isinstance(self._check, Instance)
            and self._check._class is BlackToken) :
            result.add_child(Tree("initialMarking", None,
                                  Tree("text", str(len(self.tokens)))))
        else :
            result.add_child(Tree.from_obj(self._check))
            result.add_child(Tree("initialMarking", None,
                                  Tree.from_obj(self.tokens)))
        return result
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> t = Place('p', [dot, dot], tBlackToken).__pnmldump__()
        >>> Place.__pnmlload__(t)
        Place('p', MultiSet([dot, dot]), Instance(BlackToken))
        >>> t = Place('p', [1, 2, 3], tNatural).__pnmldump__()
        >>> p = Place.__pnmlload__(t)
        >>> p
        Place('p', MultiSet([...]), (Instance(int) & GreaterOrEqual(0)))
        >>> p.tokens == MultiSet([1, 2, 3])
        True
        """
        if tree.has_child("type") :
            return cls(tree["id"],
                       tree.child("initialMarking").child().to_obj(),
                       tree.child("type").to_obj())
        try :
            toks = int(tree.child("initialMarking").child("text").data)
        except :
            toks = 0
        return cls(tree["id"], [dot] * toks, tBlackToken)
    def checker (self, check=None) :
        """Change or return the type of the place: if `check` is
        `None`, current type is returned, otherwise, it is assigned
        with the given value.

        >>> p = Place('p', range(3), tInteger)
        >>> p.checker()
        Instance(int)
        >>> p.checker(tAll)
        >>> p.checker()
        tAll

        @param check: the new constraint for the place or `None` to
            retreive the current constraint
        @type check: `Type`
        @return: the current constraint if `check` is `None` or `None`
            otherwise
        @rtype: `Type`
        """
        if check is None :
            return self._check
        else :
            self._check = check
    def __contains__ (self, token) :
        """Check if a token is in the place.

        >>> p = Place('p', range(3))
        >>> 1 in p
        True
        >>> 5 in p
        False

        @param token: a token value
        @type token: `object`
        @return: `True` if `token` is held by the place, `False`
            otherwise
        @rtype: `bool`
        """
        return token in self.tokens
    def __iter__ (self) :
        """Iterate over the tokens in the place, including
        repetitions.

        >>> p = Place('p', range(3)*2)
        >>> list(sorted([tok for tok in p]))
        [0, 0, 1, 1, 2, 2]

        @return: an iterator object
        """
        return iter(self.tokens)
    def is_empty (self) :
        """Check is the place is empty.

        >>> p = Place('p', range(3))
        >>> p.tokens == MultiSet([0, 1, 2])
        True
        >>> p.is_empty()
        False
        >>> p.tokens = MultiSet()
        >>> p.is_empty()
        True

        @return: `True` if the place is empty, `False` otherwise
        @rtype: `bool`
        """
        return self.tokens.size() == 0
    def check (self, tokens) :
        """Check if the `tokens` are allowed in the place. Exception
        `ValueError` is raised whenever a forbidden token is
        encountered.

        >>> p = Place('p', [], tInteger)
        >>> p.check([1, 2, 3])
        >>> try : p.check(['forbidden!'])
        ... except ValueError : print(sys.exc_info()[1])
        forbidden token 'forbidden!'

        @param tokens: an iterable collection of tokens or a single
            value
        @type tokens: `collection`
        @raise ValueError: when some of the checked tokens are not
            allowed in the place
        """
        for t in tokens :
            if not self._check(t) :
                raise ValueError("forbidden token '%s'" % (t,))
    # apidoc skip
    def __str__ (self) :
        """Return the name of the place.

        >>> p = Place('Great place!')
        >>> str(p)
        'Great place!'

        @return: the name of the place
        @rtype: `str`
        """
        return self.name
    # apidoc skip
    def __repr__ (self) :
        """Return a textual representation of the place.

        >>> repr(Place('p', range(3), tInteger))
        "Place('p', MultiSet([...]), Instance(int))"

        @return: a string suitable to `eval` representing the place
        @rtype: `str`
        """
        return "%s(%s, %s, %s)" % (self.__class__.__name__,
                                   repr(self.name),
                                   repr(self.tokens),
                                   repr(self._check))
    def add (self, tokens) :
        """Add tokens to the place.

        >>> p = Place('p')
        >>> p.tokens == MultiSet([])
        True
        >>> p.add(range(3))
        >>> p.tokens == MultiSet([0, 1, 2])
        True

        @param tokens: a collection of tokens to be added to the
            place, note that `str` are not considered as iterable and
            used a a single value instead of as a collection
        @type tokens: `collection`
        """
        self.check(iterate(tokens))
        self.tokens.add(iterate(tokens))
    def remove (self, tokens) :
        """Remove tokens from the place.

        >>> p = Place('p', list(range(3)) * 2)
        >>> p.tokens == MultiSet([0, 0, 1, 1, 2, 2])
        True
        >>> p.remove(range(3))
        >>> p.tokens == MultiSet([0, 1, 2])
        True

        @param tokens: a collection of tokens to be removed from the
            place, note that `str` are not considered as iterable and
            used a a single value instead of as a collection
        @type tokens: `collection`
        """
        self.tokens.remove(tokens)
    def empty (self) :
        """Remove all the tokens.

        >>> p = Place('p', list(range(3)) * 2)
        >>> p.tokens == MultiSet([0, 0, 1, 1, 2, 2])
        True
        >>> p.empty()
        >>> p.tokens == MultiSet([])
        True
        """
        self.tokens = MultiSet()
    def reset (self, tokens) :
        """Replace the marking with `tokens`.

        >>> p = Place('p', list(range(3)) * 2)
        >>> p.tokens == MultiSet([0, 0, 1, 1, 2, 2])
        True
        >>> p.reset(['a', 'b'])
        >>> p.tokens == MultiSet(['a', 'b'])
        True
        """
        self.check(iterate(tokens))
        self.tokens = MultiSet(tokens)

class Transition (Node) :
    "A transition in a Petri net."
    def __init__ (self, name, guard=None) :
        """Initialise with the name and the guard. If `guard` is
        `None`, `Expression('True')` is assumed instead:

        >>> Transition('t').guard
        Expression('True')

        @param name: the name of the transition
        @type name: `str`
        @param guard: the guard of the transition
        @type guard: `Expression`
        """
        self._input = {}
        self._output = {}
        if guard is None :
            self.guard = Expression("True")
        else :
            self.guard = guard
        self.name = name
    def copy (self, name=None) :
        """Return a copy of the transition, with no arc attached.

        >>> t = Transition('t', Expression('x==1'))
        >>> t.copy()
        Transition('t', Expression('x==1'))
        >>> t.copy('x')
        Transition('x', Expression('x==1'))

        @param name: if not `None`, the name if of the copy
        @type name: `str`
        @return: a copy of the transition.
        @rtype: `Transition`
        """
        if name is None :
            name = self.name
        return self.__class__(name, self.guard.copy())
    __pnmltag__ = "transition"
    # apidoc skip
    def __pnmldump__ (self) :
        """
        >>> Transition('t').__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <transition id="t"/>
        </pnml>
        >>> Transition('t', Expression('x==y')).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <transition id="t">
          <guard>
           <expression>
            x==y
           </expression>
          </guard>
         </transition>
        </pnml>
        """
        if self.guard == Expression("True") :
            return Tree(self.__pnmltag__, None, id=self.name)
        else :
            return Tree(self.__pnmltag__, None,
                        Tree("guard", None, Tree.from_obj(self.guard)),
                        id=self.name)
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> t = Transition('t').__pnmldump__()
        >>> Transition.__pnmlload__(t)
        Transition('t', Expression('True'))
        >>> t = Transition('t', Expression('x==y')).__pnmldump__()
        >>> Transition.__pnmlload__(t)
        Transition('t', Expression('x==y'))
        """
        try :
            return cls(tree["id"], tree.child("guard").child().to_obj())
        except SnakesError :
            return cls(tree["id"])
    # apidoc skip
    def __str__ (self) :
        """Return the name of the transition.

        >>> t = Transition('What a transition!')
        >>> str(t)
        'What a transition!'

        @return: the name of the transition
        @rtype: `str`
        """
        return self.name
    # apidoc skip
    def __repr__ (self) :
        """Return a textual representation of the transition.

        >>> repr(Transition('t', Expression('x==1')))
        "Transition('t', Expression('x==1'))"

        @return: a string suitable to `eval` representing the
            transition
        @rtype: `str`
        """
        return "%s(%s, %s)" % (self.__class__.__name__,
                               repr(self.name),
                               repr(self.guard))
    def add_input (self, place, label) :
        """Add an input arc from `place` labelled by `label`.

        >>> t = Transition('t')
        >>> t.add_input(Place('p'), Variable('x'))
        >>> t.input()
        [(Place('p', MultiSet([]), tAll), Variable('x'))]
        >>> try : t.add_input(Place('x'), Expression('x+y'))
        ... except ConstraintError : print(sys.exc_info()[1])
        'Expression' objects not allowed on input arcs

        @param place: the input place
        @type place: `Place`
        @param label: the arc label
        @type label: `ArcAnnotation`
        @raise ConstraintError: when an annotation is added on an
            input arcs where it is actually not allowed, or when there
            is already an arc from this place
        """
        if place in self._input :
            raise ConstraintError("already connected to '%s'" % place.name)
        elif not label.input_allowed :
            raise ConstraintError("'%s' objects not allowed on input arcs"
                                    % label.__class__.__name__)
        else :
            self._input[place] = label
    def remove_input (self, place) :
        """Remove the input arc from `place`.

        >>> t = Transition('t')
        >>> p = Place('p')
        >>> t.add_input(p, Variable('x'))
        >>> t.input()
        [(Place('p', MultiSet([]), tAll), Variable('x'))]
        >>> t.remove_input(p)
        >>> t.input()
        []

        @param place: the input place
        @type place: `Place`
        @raise ConstraintError: when there is no arc from this place
        """
        try :
            del self._input[place]
        except KeyError :
            raise ConstraintError("not connected to '%s'" % place.name)
    def input (self) :
        """Return the list of input arcs.

        >>> t = Transition('t')
        >>> t.add_input(Place('p'), Variable('x'))
        >>> t.input()
        [(Place('p', MultiSet([]), tAll), Variable('x'))]

        @return: a list of pairs (place, label).
        @rtype: `list`
        """
        return list(self._input.items())
    def add_output (self, place, label) :
        """Add an output arc from `place` labelled by `label`.

        >>> t = Transition('t')
        >>> t.add_output(Place('p'), Expression('x+1'))
        >>> t.output()
        [(Place('p', MultiSet([]), tAll), Expression('x+1'))]

        @param place: the output place
        @type place: `Place`
        @param label: the arc label
        @type label: `ArcAnnotation`
        @raise ConstraintError: when there is already an arc to this
            place
        """
        if place in self._output :
            raise ConstraintError("already connected to '%s'" % place.name)
        else :
            self._output[place] = label
    def remove_output (self, place) :
        """Remove the output arc to `place`.

        >>> t = Transition('t')
        >>> p = Place('p')
        >>> t.add_output(p, Variable('x'))
        >>> t.output()
        [(Place('p', MultiSet([]), tAll), Variable('x'))]
        >>> t.remove_output(p)
        >>> t.output()
        []

        @param place: the output place
        @type place: `Place`
        @raise ConstraintError: when there is no arc to this place
        """
        try :
            del self._output[place]
        except KeyError :
            raise ConstraintError("not connected to '%s'" % place.name)
    def output (self) :
        """Return the list of output arcs.

        >>> t = Transition('t')
        >>> t.add_output(Place('p'), Expression('x+1'))
        >>> t.output()
        [(Place('p', MultiSet([]), tAll), Expression('x+1'))]

        @return: a list of pairs (place, label).
        @rtype: `list`
        """
        return list(self._output.items())
    def _check (self, binding, tokens, input) :
        """Check `binding` against the guard and tokens flow.

        If `tokens` is `True`, check whether the flow of tokens can be
        provided by the input places. If `input` is `True`, check if
        the evaluation of the inputs arcs respect the types of the
        input places. In any case, this is checked for the output
        places.

        >>> t = Transition('t', Expression('x>0'))
        >>> p = Place('p', [], tInteger)
        >>> t.add_input(p, Variable('x'))
        >>> s = Substitution(x=1)
        >>> t._check(s, False, False)
        True
        >>> t._check(s, True, False)
        False
        >>> t._check(s, False, True)
        True
        >>> t._check(s, True, True)
        False
        >>> s = Substitution(x=3.14)
        >>> t._check(s, False, False)
        True
        >>> t._check(s, True, False)
        False
        >>> t._check(s, False, True)
        False
        >>> t._check(s, True, True)
        False

        @param binding: a valuation of the variables on the transition
        @type binding: `Substitution`
        @param tokens: whether it should be checked that input places
            hold enough tokens or not
        @type tokens: `bool`
        @param input: whether it should be checked that the types of
            the input places are respected or not
        @type input: `bool`
        @return: `True` if the binding is suitable, `False` otherwise
        """
        if not self.guard(binding) :
            return False
        if tokens :
            for place, label in self.input() :
                if not (label.flow(binding) <= place.tokens) :
                    return False
        if input :
            for place, label in self.input() :
                try :
                    place.check(v.value for v in iterate(label.bind(binding)))
                except ValueError :
                    return False
        for place, label in self.output() :
            try :
                place.check(v.value for v in iterate(label.bind(binding)))
            except ValueError :
                return False
        return True
    def activated (self, binding) :
        """Check if `binding` activates the transition. This is the
        case if the guard evaluates to `True` and if the types of the
        places are respected. Note that the presence of enough tokens
        is not required.

        >>> t = Transition('t', Expression('x>0'))
        >>> p = Place('p', [], tInteger)
        >>> t.add_input(p, Variable('x'))
        >>> t.activated(Substitution(x=1))
        True
        >>> t.activated(Substitution(x=-1))
        False
        >>> t.activated(Substitution(x=3.14))
        False

        @param binding: a valuation of the variables on the transition
        @type binding: `Substitution`
        """
        return self._check(binding, False, True)
    def enabled (self, binding) :
        """Check if `binding` enables the transition. This is the case
        if the transition is activated and if the input places hold
        enough tokens to allow the firing.

        >>> t = Transition('t', Expression('x>0'))
        >>> p = Place('p', [0], tInteger)
        >>> t.add_input(p, Variable('x'))
        >>> t.enabled(Substitution(x=1))
        False
        >>> p.add(1)
        >>> t.enabled(Substitution(x=1))
        True

        @param binding: a valuation of the variables on the transition
        @type binding: `Substitution`
        """
        return self._check(binding, True, True)
    def vars (self) :
        """Return the set of variables involved in the guard, input and
        output arcs of the transition.

        >>> t = Transition('t', Expression('z is not None'))
        >>> px = Place('px')
        >>> t.add_input(px, Variable('x'))
        >>> py = Place('py')
        >>> t.add_output(py, Variable('y'))
        >>> list(sorted(t.vars()))
        ['x', 'y', 'z']

        @return: the set of variables names
        @rtype: `set`
        """
        v = set(self.guard.vars())
        for place, label in self.input() :
            v.update(label.vars())
        for place, label in self.output() :
            v.update(label.vars())
        return v
    def substitute (self, binding) :
        """Substitute all the annotations arround the transition.
        `binding` is used to substitute the guard and all the labels
        on the arcs attached to the transition.

        >>> t = Transition('t', Expression('z is not None'))
        >>> px = Place('px')
        >>> t.add_input(px, Variable('x'))
        >>> py = Place('py')
        >>> t.add_output(py, Variable('y'))
        >>> t.substitute(Substitution(x='a', y='b', z='c'))
        >>> t
        Transition('t', Expression('(c is not None)'))
        >>> t.input()
        [(Place('px', MultiSet([]), tAll), Variable('a'))]
        >>> t.output()
        [(Place('py', MultiSet([]), tAll), Variable('b'))]

        @param binding: a substitution from variables to variables
            (not values)
        @type binding: `Substitution`
        """
        self.guard.substitute(binding)
        for place, label in self.input() :
            label.substitute(binding)
        for place, label in self.output() :
            label.substitute(binding)
    def modes (self) :
        """Return the list of bindings which enable the transition.
        Note that the modes are usually considered to be the list of
        bindings that _activate_ a transitions. However, this list may
        be infinite so we retricted ourselves to _actual modes_,
        taking into account only the tokens actually present in the
        input places.

        >>> t = Transition('t', Expression('x!=y'))
        >>> px = Place('px', range(2))
        >>> t.add_input(px, Variable('x'))
        >>> py = Place('py', range(2))
        >>> t.add_input(py, Variable('y'))
        >>> m = t.modes()
        >>> len(m)
        2
        >>> Substitution(y=0, x=1) in m
        True
        >>> Substitution(y=1, x=0) in m
        True

        Note also that modes cannot be computed with respect to output
        arcs: indeed, only input arcs allow for concretely associate
        values to variables; on the other hand, binding an output arc
        would require to solve the equation provided by the guard.

        >>> t = Transition('t', Expression('x!=y'))
        >>> px = Place('px', range(2))
        >>> t.add_input(px, Variable('x'))
        >>> py = Place('py')
        >>> t.add_output(py, Variable('y'))
        >>> t.modes()
        Traceback (most recent call last):
          ...
        NameError: name 'y' is not defined

        @return: a list of substitutions usable to fire the transition
        @rtype: `list`
        """
        parts = []
        try :
            for place, label in self.input() :
                m = label.modes(place.tokens)
                parts.append(m)
        except ModeError :
            return []
        result = []
        for x in cross(parts) :
            try :
                if len(x) == 0 :
                    sub = Substitution()
                else :
                    sub = reduce(Substitution.__add__, x)
                if self._check(sub, False, False) :
                    result.append(sub)
            except DomainError :
                pass
        return result
    def flow (self, binding) :
        """Return the token flow for a firing with `binding`. The flow
        is represented by a pair `(in, out)`, both being instances of
        the class `Marking`.

        >>> t = Transition('t', Expression('x!=1'))
        >>> px = Place('px', range(3))
        >>> t.add_input(px, Variable('x'))
        >>> py = Place('py')
        >>> t.add_output(py, Expression('x+1'))
        >>> t.flow(Substitution(x=0))
        (Marking({'px': MultiSet([0])}), Marking({'py': MultiSet([1])}))
        >>> try : t.flow(Substitution(x=1))
        ... except ValueError : print(sys.exc_info()[1])
        transition not enabled for {x -> 1}
        >>> t.flow(Substitution(x=2))
        (Marking({'px': MultiSet([2])}), Marking({'py': MultiSet([3])}))

        @param binding: a substitution from variables to values (not
            variables)
        @type binding: `Substitution`
        @return: a pair of marking to be respectively consumed or
            produced by the firing of the transition with `binding`
        @rtype: `tuple`
        @raise ValueError: when the provided binding does not enable
            the transition
        """
        if self.enabled(binding) :
            return (Marking((place.name, label.flow(binding))
                            for place, label in self.input()),
                    Marking((place.name, label.flow(binding))
                            for place, label in self.output()))
        else :
            raise ValueError("transition not enabled for %s" % binding)
    def fire (self, binding) :
        """Fire the transition with `binding`.

        >>> t = Transition('t', Expression('x!=1'))
        >>> px = Place('px', range(3))
        >>> t.add_input(px, Variable('x'))
        >>> py = Place('py')
        >>> t.add_output(py, Expression('x+1'))
        >>> t.fire(Substitution(x=0))
        >>> px.tokens == MultiSet([1, 2])
        True
        >>> py.tokens == MultiSet([1])
        True
        >>> try : t.fire(Substitution(x=1))
        ... except ValueError : print(sys.exc_info()[1])
        transition not enabled for {x -> 1}
        >>> t.fire(Substitution(x=2))
        >>> px.tokens == MultiSet([1])
        True
        >>> py.tokens == MultiSet([1, 3])
        True

        @param binding: a substitution from variables to values (not
            variables)
        @type binding: `Substitution`
        @raise ValueError: when the provided binding does not enable
            the transition
        """
        if self.enabled(binding) :
            for place, label in self.input() :
                place.remove(label.flow(binding))
            for place, label in self.output() :
                place.add(label.flow(binding))
        else :
            raise ValueError("transition not enabled for %s" % binding)

"""
## Marking, Petri nets and state graphs ##
"""

class Marking (hdict) :
    """A marking of a Petri net. This is basically a
    `snakes.hashables.hdict` mapping place names to multisets of
    tokens.

    The parameters for the constructor must be given in a form
    suitable for initialising a `hdict` with place names as keys and
    multisets as values. Places not given in the marking are assumed
    empty. A `Marking` object is independent of any Petri net and so
    its list of places is not related to the places actually present
    in a given net. This allows in particular to extract a `Marking`
    from one Petri net and to assign it to another.
    """
    __pnmltag__ = "marking"
    # apidoc skip
    def __pnmldump__ (self) :
        """
        >>> Marking(p1=MultiSet([1]), p2=MultiSet([2])).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <marking>
          <place id="p2">
           <tokens>
            <multiset>
             <item>
              <value>
               <object type="int">
                2
               </object>
              </value>
              <multiplicity>
               1
              </multiplicity>
             </item>
            </multiset>
           </tokens>
          </place>
          <place id="p1">
           <tokens>
            <multiset>
             <item>
              <value>
               <object type="int">
                1
               </object>
              </value>
              <multiplicity>
               1
              </multiplicity>
             </item>
            </multiset>
           </tokens>
          </place>
         </marking>
        </pnml>
        """
        return Tree(self.__pnmltag__, None,
                    *(Tree("place", None,
                           Tree("tokens", None, Tree.from_obj(self[place])),
                           id=place) for place in self))
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> t = Marking(p1=MultiSet([1]), p2=MultiSet([2])).__pnmldump__()
        >>> Marking.__pnmlload__(t)
        Marking({'p2': MultiSet([2]), 'p1': MultiSet([1])})
        """
        return cls(((child["id"], child.child("tokens").child().to_obj())
                    for child in tree.get_children("place")))
    def __str__ (self) :
        base = "{%s}" % ", ".join("%s=%s" % pair for pair in sorted(self.items()))
        return base.replace("={dot}", "")
    def __call__ (self, place) :
        """Return the marking of `place`. The empty multiset is
        returned if `place` is not explicitely given in the marking.

        >>> m = Marking(p1=MultiSet([1]), p2=MultiSet([2]))
        >>> m('p1')
        MultiSet([1])
        >>> m('p')
        MultiSet([])

        @param place: a place name
        @type place: `str`
        @return: the marking of `place`
        @rtype: `MultiSet`
        """
        try :
            return self[place]
        except KeyError :
            return MultiSet()
    def copy (self) :
        """Copy a marking

        >>> m = Marking(p1=MultiSet([1]), p2=MultiSet([2]))
        >>> m.copy() == Marking({'p2': MultiSet([2]), 'p1': MultiSet([1])})
        True
        """
        result = self.__class__()
        for place, tokens in self.items() :
            result[place] = tokens.copy()
        return result
    def __add__ (self, other) :
        """Addition of markings.

        >>> Marking(p1=MultiSet([1]), p2=MultiSet([2])) + Marking(p2=MultiSet([2]), p3=MultiSet([3])) == Marking({'p2': MultiSet([2, 2]), 'p3': MultiSet([3]), 'p1': MultiSet([1])})
        True

        @param other: another marking
        @type other: `Marking`
        @return: the addition of the two markings
        @rtype: `Marking`
        """
        result = self.copy()
        for place in other :
            if place in self :
                result[place].add(other[place])
            else :
                result[place] = other[place]
        return result
    def __sub__ (self, other) :
        """Substraction of markings.

        >>> Marking(p1=MultiSet([1]), p2=MultiSet([2, 2])) - Marking(p2=MultiSet([2]))
        Marking({'p2': MultiSet([2]), 'p1': MultiSet([1])})
        >>> try : Marking(p1=MultiSet([1]), p2=MultiSet([2])) - Marking(p2=MultiSet([2, 2]))
        ... except ValueError : print(sys.exc_info()[1])
        not enough occurrences
        >>> Marking(p1=MultiSet([1]), p2=MultiSet([2])) - Marking(p3=MultiSet([3]))
        Traceback (most recent call last):
          ...
        DomainError: 'p3' absent from the marking

        @param other: another marking
        @type other: `Marking`
        @return: the difference of the two markings
        @rtype: `Marking`
        """
        result = self.copy()
        for place in other :
            if place in result :
                result[place].remove(other[place])
                if result(place).size() == 0 :
                    del result[place]
            else :
                raise DomainError("'%s' absent from the marking" % place)
        return result
    __hash__ = hdict.__hash__
    # apidoc skip
    def __eq__ (self, other) :
        """Test for equality (same places with the same tokens).

        >>> Marking(p=MultiSet([1])) == Marking(p=MultiSet([1]))
        True
        >>> Marking(p=MultiSet([1])) == Marking(p=MultiSet([1, 1]))
        False
        >>> Marking(p1=MultiSet([1])) == Marking(p2=MultiSet([1]))
        False

        @param other: another marking
        @type other: `Marking`
        @return: `True` if the markings are equal, `False` otherwise
        @rtype: `bool`
        """
        if len(self) != len(other) :
            return False
        for place in self :
            try :
                if self[place] != other[place] :
                    return False
            except KeyError :
                return False
        return True
    # apidoc skip
    def __ne__ (self, other) :
        """Test if two markings differ.

        >>> Marking(p=MultiSet([1])) != Marking(p=MultiSet([1]))
        False
        >>> Marking(p=MultiSet([1])) != Marking(p=MultiSet([1, 1]))
        True
        >>> Marking(p1=MultiSet([1])) != Marking(p2=MultiSet([1]))
        True

        @param other: another marking
        @type other: `Marking`
        @return: `True` if the markings differ, `False` otherwise
        @rtype: `bool`
        """
        return not (self == other)
    def __ge__ (self, other) :
        """Test if the marking `self` is greater than or equal to
        `other`. This is the case when any place in `other` is also in
        `self` and is marked with a smaller or equal multiset of
        tokens.

        >>> Marking(p=MultiSet([1])) >= Marking(p=MultiSet([1]))
        True
        >>> Marking(p=MultiSet([1, 1])) >= Marking(p=MultiSet([1]))
        True
        >>> Marking(p=MultiSet([1]), r=MultiSet([2])) >= Marking(p=MultiSet([1]))
        True
        >>> Marking(p=MultiSet([1])) >= Marking(p=MultiSet([1, 2]))
        False
        >>> Marking(p=MultiSet([1]), r=MultiSet([2])) >= Marking(p=MultiSet([1, 1]))
        False

        @param other: another marking
        @type other: `Marking`
        @return: `True` if `self >= other`, `False` otherwise
        @rtype: `bool`
        """
        for place in other :
            if place not in self :
                return False
            elif not (self[place] >= other[place]) :
                return False
        return True
    def __gt__ (self, other) :
        """Test if the marking `self` is strictly greater than
        `other`. This is the case when any place in `other` is also in
        `self` and either one place in `other` is marked with a
        smaller multiset of tokens or `slef` has more places than
        `other`.

        >>> Marking(p=MultiSet([1])) > Marking(p=MultiSet([1]))
        False
        >>> Marking(p=MultiSet([1, 1])) > Marking(p=MultiSet([1]))
        True
        >>> Marking(p=MultiSet([1]), r=MultiSet([2])) > Marking(p=MultiSet([1]))
        True
        >>> Marking(p=MultiSet([1])) > Marking(p=MultiSet([1, 2]))
        False
        >>> Marking(p=MultiSet([1]), r=MultiSet([2])) > Marking(p=MultiSet([1, 1]))
        False

        @param other: another marking
        @type other: `Marking`
        @return: `True` if `self > other`, `False` otherwise
        @rtype: `bool`
        """
        more = False
        for place in other :
            if place not in self :
                return False
            elif not (self[place] >= other[place]) :
                return False
            elif self[place] > other[place] :
                more = True
        return more or len(self) > len(other)
    def __le__ (self, other) :
        """Test if the marking `self` is smaller than or equal to
        `other`. This is the case when any place in `self` is also in
        `other` and is marked with a smaller or equal multiset of
        tokens.

        >>> Marking(p=MultiSet([1])) <= Marking(p=MultiSet([1]))
        True
        >>> Marking(p=MultiSet([1])) <= Marking(p=MultiSet([1, 1]))
        True
        >>> Marking(p=MultiSet([1])) <= Marking(p=MultiSet([1]), r=MultiSet([2]))
        True
        >>> Marking(p=MultiSet([1, 2])) <= Marking(p=MultiSet([1]))
        False
        >>> Marking(p=MultiSet([1, 1])) <= Marking(p=MultiSet([1]), r=MultiSet([2]))
        False

        @param other: another marking
        @type other: `Marking`
        @return: `True` if `self <= other`, `False` otherwise
        @rtype: `bool`
        """
        for place in self :
            if place not in other :
                return False
            elif not (self[place] <= other[place]) :
                return False
        return True
    def __lt__ (self, other) :
        """Test if the marking `self` is strictly smaller than
        `other`. This is the case when any place in `self` is also in
        `other` and either one place in `self` marked in self with a
        strictly smaller multiset of tokens or `other` has more places
        than `self`.

        >>> Marking(p=MultiSet([1])) < Marking(p=MultiSet([1]))
        False
        >>> Marking(p=MultiSet([1])) < Marking(p=MultiSet([1, 1]))
        True
        >>> Marking(p=MultiSet([1])) < Marking(p=MultiSet([1]), r=MultiSet([2]))
        True
        >>> Marking(p=MultiSet([1, 2])) < Marking(p=MultiSet([1]))
        False
        >>> Marking(p=MultiSet([1, 1])) < Marking(p=MultiSet([1]), r=MultiSet([2]))
        False

        @param other: another marking
        @type other: `Marking`
        @return: `True` if `self < other`, `False` otherwise
        @rtype: `bool`
        """
        less = False
        for place in self :
            if place not in other :
                return False
            elif not (self[place] <= other[place]) :
                return False
            elif self[place] < other[place] :
                less = True
        return less or len(self) < len(other)

##
## Petri nets
##

class PetriNet (object) :
    """A Petri net. As soon as nodes are added to a `PetriNet`, they
    should be handled by name instead of by the `Place` or
    `Transition` instance. For instance:

    >>> n = PetriNet('N')
    >>> t = Transition('t')
    >>> n.add_transition(t)
    >>> n.has_transition('t') # use 't' and not t
    True
    >>> n.transition('t') is t
    True
    """
    def __init__ (self, name) :
        """Initialise with a name that may be an arbitrary string.

        >>> PetriNet('N')
        PetriNet('N')

        @param name: the name of the net
        @type name: `str`
        """
        self.name = name
        self._trans = {}
        self._place = {}
        self._node = {}
        self._declare = []
        self.globals = Evaluator()
    # apidoc skip
    def __hash__ (self) :
        # 1844414626 = hash("snakes.nets.PetriNet")
        return reduce(operator.xor,
                      (hash(self.name),)
                      + tuple(hash(n) for n in self._node), 1844414626)
    def copy (self, name=None) :
        """Return a complete copy of the net, including places,
        transitions, arcs and declarations.

        >>> PetriNet('N').copy()
        PetriNet('N')
        >>> PetriNet('N').copy('x')
        PetriNet('x')

        @param name: if not `None`, the name of the copy
        @type name: `str`
        @return: a copy of the net
        @rtype: `PetriNet`
        """
        if name is None :
            name = self.name
        result = self.__class__(name)
        result._declare = self._declare[:]
        result.globals = self.globals.copy()
        for place in self.place() :
            result.add_place(place.copy())
        for trans in self.transition() :
            result.add_transition(trans.copy())
            for place, label in trans.input() :
                result.add_input(place.name, trans.name, label.copy())
            for place, label in trans.output() :
                result.add_output(place.name, trans.name, label.copy())
        return result
    __pnmltag__ = "net"
    @classmethod
    def _pnml_dump_arc (cls, label) :
        """Dump an arc to PNML

        >>> PetriNet._pnml_dump_arc(Value(dot))
        (<?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <inscription>
          <text>
           1
          </text>
         </inscription>
        </pnml>,)
        >>> PetriNet._pnml_dump_arc(MultiArc([Value(dot), Value(dot)]))
        (<?xml version="1.0" encoding="utf-8"?>
         <pnml>
          <inscription>
           <text>
            2
           </text>
          </inscription>
         </pnml>,)
        >>> PetriNet._pnml_dump_arc(Value(1))
        (<?xml version="1.0" encoding="utf-8"?>
         <pnml>
          <inscription>
           <value>
            <object type="int">
             1
            </object>
           </value>
          </inscription>
         </pnml>,)
        >>> PetriNet._pnml_dump_arc(Variable('x'))
        (<?xml version="1.0" encoding="utf-8"?>
         <pnml>
          <inscription>
           <variable>
            x
           </variable>
          </inscription>
         </pnml>,)
        >>> PetriNet._pnml_dump_arc(MultiArc([Value(dot), Variable('y')]))
        (<?xml version="1.0" encoding="utf-8"?>
         <pnml>
          <inscription>
           <text>
            2
           </text>
          </inscription>
         </pnml>,)

        @param label: the arc label to dump
        @type label: `ArcAnnotation`
        @return: a tuple of PNML trees
        @rtype: `tuple`
        """
        if label == Value(dot) :
            return (Tree("inscription", None, Tree("text", "1"),),)
        elif isinstance(label, MultiArc) and reduce(operator.or_,
                                                  (x == Value(dot)
                                                   for x in label)) :
            return (Tree("inscription", None,
                         Tree("text", str(len(label)))),)
        return (Tree("inscription", None, Tree.from_obj(label)),)
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump a `PetriNet` as a PNML tree

        >>> n = PetriNet('N')
        >>> n.declare('x = "foo" + "bar"')
        >>> n.globals['y'] = 'egg'
        >>> for i, l in enumerate((Value(dot),
        ...                        MultiArc([Value(dot), Value(dot)]),
        ...                        Value(1))) :
        ...    n.add_place(Place('p%u' % i))
        ...    n.add_transition(Transition('t%u' % i))
        ...    n.add_input('p%u' % i, 't%u' % i, l)
        >>> n.__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <net id="N">
          <declare>
           x = &quot;foo&quot; + &quot;bar&quot;
          </declare>
          <global name="y">
           <object type="str">
            egg
           </object>
          </global>
          <place id="...">
          ...
          </place>
          <place id="...">
          ...
          </place>
          <place id="...">
          ...
          </place>
          <transition id="..."/>
          <transition id="..."/>
          <transition id="..."/>
          <arc id="..." source="..." target="...">
          ...
          </arc>
          <arc id="..." source="..." target="...">
          ...
          </arc>
          <arc id="..." source="..." target="...">
          ...
          </arc>
         </net>
        </pnml>

        @return: PNML tree
        @rtype: `pnml.Tree`
        """
        result = Tree(self.__pnmltag__, None, id=self.name)
        decl = {}
        exec("pass", decl)
        for stmt in self._declare :
            try :
                exec(stmt, decl)
                result.add_child(Tree("declare", stmt))
            except :
                pass
        for name, value in self.globals :
            if name not in decl :
                try :
                    result.add_child(Tree("global", None, Tree.from_obj(value),
                                          name=name))
                except :
                    pass
        for place in self.place() :
            result.add_child(Tree.from_obj(place))
        for trans in self.transition() :
            result.add_child(Tree.from_obj(trans))
        for trans in self.transition() :
            for place, label in trans.input() :
                result.add_child(Tree("arc", None,
                                      *(self._pnml_dump_arc(label)),
                                      **{"id" : "%s:%s" % (place.name,
                                                           trans.name),
                                         "source" : place.name,
                                         "target" : trans.name}))
            for place, label in trans.output() :
                result.add_child(Tree("arc", None,
                                      *(self._pnml_dump_arc(label)),
                                      **{"id" : "%s:%s" % (trans.name,
                                                           place.name),
                                         "source" : trans.name,
                                         "target" : place.name}))
        return result
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create a `PetriNet` from a PNML tree

        @param tree: the tree to convert
        @type tree: `pnml.Tree`
        @return: the net built
        @rtype: `PetriNet`

        >>> old = PetriNet('N')
        >>> old.declare('x = "foo" + "bar"')
        >>> old.globals['y'] = 'egg'
        >>> for i, l in enumerate((Value(dot),
        ...                        MultiArc([Value(dot), Value(dot)]),
        ...                        Value(1))) :
        ...    old.add_place(Place('p%u' % i))
        ...    old.add_transition(Transition('t%u' % i))
        ...    old.add_input('p%u' % i, 't%u' % i, l)
        >>> new = PetriNet.__pnmlload__(old.__pnmldump__())
        >>> new.globals == old.globals
        True
        >>> sorted(new.place(), key=lambda x: x.name)
        [Place('p0', MultiSet([]), tAll),
         Place('p1', MultiSet([]), tAll),
         Place('p2', MultiSet([]), tAll)]
        >>> sorted(new.transition(), key=lambda x: x.name)
        [Transition('t0', Expression('True')),
         Transition('t1', Expression('True')),
         Transition('t2', Expression('True'))]
        >>> for t in sorted(new.transition(), key=lambda x: x.name) :
        ...     print('%s %s' % (t.name, t.input()))
        t0 [(Place('p0', MultiSet([]), tAll), Value(dot))]
        t1 [(Place('p1', MultiSet([]), tAll), MultiArc((Value(dot), Value(dot))))]
        t2 [(Place('p2', MultiSet([]), tAll), Value(1))]
        """
        result = cls(tree["id"])
        for stmt in tree.get_children("declare") :
            result.declare(stmt.data)
        for glbl in tree.get_children("global") :
            result.globals[glbl["name"]] = glbl.child().to_obj()
        for branch in (tree,) + tuple(tree.get_children("page")) :
            for place in branch.get_children("place") :
                result.add_place(place.to_obj())
            for trans in branch.get_children("transition") :
                result.add_transition(trans.to_obj())
        for branch in (tree,) + tuple(tree.get_children("page")) :
            for arc in branch.get_children("arc") :
                if not arc.has_child("inscription") :
                    label = Value(dot)
                else :
                    lbl = arc.child("inscription")
                    if lbl.has_child("text") :
                        nbr = int(lbl.child("text").data)
                        if nbr == 0 :
                            label = None
                        elif nbr == 1 :
                            label = Value(dot)
                        else :
                            label = MultiArc([Value(dot)] * nbr)
                    else :
                        label = lbl.child().to_obj()
                if label is None :
                    pass
                elif result.has_place(arc["source"]) :
                    result.add_input(arc["source"], arc["target"], label)
                else :
                    result.add_output(arc["target"], arc["source"], label)
        return result
    # apidoc skip
    def __repr__ (self) :
        """Return a string suitable for `eval` to represent the net.

        >>> repr(PetriNet('N'))
        "PetriNet('N')"

        @return: the textual representation of the net
        @rtype: `str`
        """
        return "%s(%s)" % (self.__class__.__name__, repr(self.name))
    # apidoc skip
    def __str__ (self) :
        """Return the name of the net.

        >>> str(PetriNet('N'))
        'N'

        @return: the name if the net
        @rtype: `str`
        """
        return self.name
    def rename (self, name) :
        """Change the name of the net.

        >>> n = PetriNet('N')
        >>> n.rename('Long name!')
        >>> n
        PetriNet('Long name!')

        @param name: the new name
        @type name: `str`
        """
        self.name = name
    def has_place (self, name) :
        """Check if there is a place called `name` in the net.

        >>> n = PetriNet('N')
        >>> n.has_place('p')
        False
        >>> n.add_place(Place('p'))
        >>> n.has_place('p')
        True

        @param name: the name of the searched place
        @type name: `str`
        @return: `True` if a place called `name` is present in the
            net, `False` otherwise
        @rtype: `bool`
        """
        return name in self._place
    def has_transition (self, name) :
        """Check if there is a transition called `name` in the net.

        >>> n = PetriNet('N')
        >>> n.has_transition('t')
        False
        >>> n.add_transition(Transition('t'))
        >>> n.has_transition('t')
        True

        @param name: the name of the searched transition
        @type name: `str`
        @return: `True` if a transition called `name` is present in
            the net, `False` otherwise
        @rtype: `bool`
        """
        return name in self._trans
    def has_node (self, name) :
        """Check if there is a transition called `name` in the net.

        >>> n = PetriNet('N')
        >>> n.has_node('t')
        False
        >>> n.has_node('p')
        False
        >>> n.add_transition(Transition('t'))
        >>> n.add_place(Place('p'))
        >>> n.has_node('t')
        True
        >>> n.has_node('p')
        True

        @param name: the name of the searched node
        @type name: `str`
        @return: `True` if a node called `name` is present in the net,
            `False` otherwise
        @rtype: `bool`
        """
        return name in self._node
    def __contains__ (self, name) :
        """`name in net` is a shortcut for `net.has_node(name)`

        >>> n = PetriNet('N')
        >>> 't' in n
        False
        >>> 'p' in n
        False
        >>> n.add_transition(Transition('t'))
        >>> n.add_place(Place('p'))
        >>> 't' in n
        True
        >>> 'p' in n
        True

        @param name: the name of the searched node
        @type name: `str`
        @return: `True` if a node called `name` is present in the net,
            `False` otherwise
        @rtype: `bool`
        """
        return name in self._node
    def declare (self, statements, locals=None) :
        """Execute `statements` in the global dictionnary of the net.
        This has also on the dictionnarie of the instances of
        `Expression` in the net (guards of the transitions and labels
        on the arcs) so the declarations have an influence over the
        elements embedded in the net. If `locals` is given, most of
        the declared objects will be placed in it instead of the
        global dictionnary, see the documentation of Python for more
        details about local and global environments.

        >>> n = PetriNet('N')
        >>> t = Transition('t', Expression('x==0'))
        >>> n.add_transition(t)
        >>> t.guard(Substitution())
        Traceback (most recent call last):
          ...
        NameError: name 'x' is not defined
        >>> n.declare('x=0')
        >>> t.guard(Substitution())
        True
        >>> n.add_place(Place('p'))
        >>> n.add_output('p', 't', Expression('math.pi'))
        >>> t.fire(Substitution())
        Traceback (most recent call last):
          ...
        NameError: name 'math' is not defined
        >>> n.declare('import math')
        >>> t.fire(Substitution())
        >>> n.place('p')
        Place('p', MultiSet([3.14...]), tAll)

        @param statements: a Python instruction suitable to `exec`
        @type statements: `str`
        @param locals: a `dict` used as locals when `statements` is
            executed, or `None`
        @type locals: `dict`
        """
        self.globals.declare(statements, locals)
        self._declare.append(statements)
    def add_place (self, place) :
        """Add a place to the net. Each node in a net must have a name
        unique to this net, which is checked when it is added.

        >>> n = PetriNet('N')
        >>> n.place('p')
        Traceback (most recent call last):
          ...
        ConstraintError: place 'p' not found
        >>> n.add_place(Place('p', range(3)))
        >>> n.place('p')
        Place('p', MultiSet([...]), tAll)
        >>> n.place('p').tokens == MultiSet([0, 1, 2])
        True
        >>> n.add_place(Place('p'))
        Traceback (most recent call last):
          ...
        ConstraintError: place 'p' exists

        @param place: the place to add
        @type place: `Place`
        @raise ConstraintError: when a place with the same name exists
            already in the net
        """
        if place.name in self._place :
            raise ConstraintError("place '%s' exists" % place.name)
        elif place.name in self._trans :
            raise ConstraintError("a transition '%s' exists" % place.name)
        self._place[place.name] = place
        self._node[place.name] = place
        place.lock("name", self, place.name)
        place.lock("net", self, self)
        place.lock("pre", self, {})
        place.lock("post", self, {})
    def remove_place (self, name) :
        """Remove a place (given by its name) from the net.

        >>> n = PetriNet('N')
        >>> n.remove_place('p')
        Traceback (most recent call last):
          ...
        ConstraintError: place 'p' not found
        >>> n.add_place(Place('p', range(3)))
        >>> n.place('p')
        Place('p', MultiSet([...]), tAll)
        >>> n.remove_place('p')
        >>> n.place('p')
        Traceback (most recent call last):
          ...
        ConstraintError: place 'p' not found

        @param name: the name of the place to remove
        @type name: `str`
        @raise ConstraintError: when no place with this name exists
            in the net
        """
        try :
            place = self._place[name]
        except KeyError :
            raise ConstraintError("place '%s' not found" % name)
        for trans in list(place.post.keys()) :
            self.remove_input(name, trans)
        for trans in list(place.pre.keys()) :
            self.remove_output(name, trans)
        del self._place[name]
        del self._node[name]
        place.unlock("pre", self, remove=True)
        place.unlock("post", self, remove=True)
        place.unlock("name", self)
        place.unlock("net", self, remove=True)
    def add_transition (self, trans) :
        """Add a transition to the net. Each node in a net must have a
        name unique to this net, which is checked when it is added.

        >>> n = PetriNet('N')
        >>> n.transition('t')
        Traceback (most recent call last):
          ...
        ConstraintError: transition 't' not found
        >>> n.add_transition(Transition('t', Expression('x==1')))
        >>> n.transition('t')
        Transition('t', Expression('x==1'))
        >>> n.add_transition(Transition('t'))
        Traceback (most recent call last):
          ...
        ConstraintError: transition 't' exists

        @param trans: the transition to add
        @type trans: `Transition`
        @raise ConstraintError: when a transition with the same name
            exists already in the net
        """
        if trans.name in self._trans :
            raise ConstraintError("transition '%s' exists" % trans.name)
        elif trans.name in self._place :
            raise ConstraintError("a place '%s' exists" % trans.name)
        self._trans[trans.name] = trans
        self._node[trans.name] = trans
        trans.lock("name", self, trans.name)
        trans.lock("net", self, self)
        trans.lock("pre", self, {})
        trans.lock("post", self, {})
        trans.guard.globals.attach(self.globals)
    def remove_transition (self, name) :
        """Remove a transition (given by its name) from the net.

        >>> n = PetriNet('N')
        >>> n.remove_transition('t')
        Traceback (most recent call last):
          ...
        ConstraintError: transition 't' not found
        >>> n.add_transition(Transition('t', Expression('x==1')))
        >>> n.transition('t')
        Transition('t', Expression('x==1'))
        >>> n.remove_transition('t')
        >>> n.transition('t')
        Traceback (most recent call last):
          ...
        ConstraintError: transition 't' not found

        @param name: the name of the transition to remove
        @type name: `str`
        @raise ConstraintError: when no transition with this name
            exists in the net
        """
        try :
            trans = self._trans[name]
        except KeyError :
            raise ConstraintError("transition '%s' not found" % name)
        for place in list(trans.post.keys()) :
            self.remove_output(place, name)
        for place in list(trans.pre.keys()) :
            self.remove_input(place, name)
        del self._trans[name]
        del self._node[name]
        trans.unlock("pre", self, remove=True)
        trans.unlock("post", self, remove=True)
        trans.unlock("name", self)
        trans.unlock("net", self, remove=True)
        trans.guard.globals.detach(self.globals)
    def place (self, name=None) :
        """Return one (if `name` is not `None`) or all the places.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p1'))
        >>> n.add_place(Place('p2'))
        >>> n.place('p1')
        Place('p1', MultiSet([]), tAll)
        >>> n.place('p')
        Traceback (most recent call last):
          ...
        ConstraintError: place 'p' not found
        >>> n.place()
        [Place('p2', MultiSet([]), tAll), Place('p1', MultiSet([]), tAll)]

        @param name: the name of the place to retrieve or `None` to
            get the list of all the places in the net
        @type name: `str`
        @return: a place whose name is `name` or a list of places
        @rtype: `object`
        @raise ConstraintError: when a place requested does not exist
        """
        if name is None :
            return list(self._place.values())
        else :
            try :
                return self._place[name]
            except KeyError :
                raise ConstraintError("place '%s' not found" % name)
    def transition (self, name=None) :
        """Return one (if `name` is not `None`) or all the transitions.

        >>> n = PetriNet('N')
        >>> n.add_transition(Transition('t1'))
        >>> n.add_transition(Transition('t2'))
        >>> n.transition('t1')
        Transition('t1', Expression('True'))
        >>> n.transition('t')
        Traceback (most recent call last):
          ...
        ConstraintError: transition 't' not found
        >>> n.transition()
        [Transition('t2', Expression('True')),
         Transition('t1', Expression('True'))]

        @param name: the name of the transition to retrieve or `None`
            to get the list of all the transitions in the net
        @type name: `str`
        @return: a transition whose name is `name` or a list of
            transitions
        @rtype: `object`
        @raise ConstraintError: when a place requested does not exist
        """
        if name is None :
            return list(self._trans.values())
        else :
            try :
                return self._trans[name]
            except KeyError :
                raise ConstraintError("transition '%s' not found" % name)
    def node (self, name=None) :
        """Return one (if `name` is not `None`) or all the nodes.

        >>> n = PetriNet('N')
        >>> n.add_transition(Transition('t'))
        >>> n.add_place(Place('p'))
        >>> n.node('t')
        Transition('t', Expression('True'))
        >>> n.node('x')
        Traceback (most recent call last):
          ...
        ConstraintError: node 'x' not found
        >>> list(sorted(n.node(), key=str))
        [Place('p', MultiSet([]), tAll), Transition('t', Expression('True'))]

        @param name: the name of the node to retrieve or `None` to get
            the list of all the nodes in the net
        @type name: `str`
        @return: a node whose name is `name` or a list of nodes
        @rtype: `object`
        @raise ConstraintError: when a node requested does not exist
        """
        if name is None :
            return list(self._node.values())
        else :
            try :
                return self._node[name]
            except KeyError :
                raise ConstraintError("node '%s' not found" % name)
    def add_input (self, place, trans, label) :
        """Add an input arc between `place` and `trans` (nodes names).
        An input arc is directed from a place toward a transition.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', range(3)))
        >>> n.add_transition(Transition('t', Expression('x!=1')))
        >>> try : n.add_input('p', 't', Expression('2*x'))
        ... except ConstraintError : print(sys.exc_info()[1])
        'Expression' not allowed on input arcs
        >>> n.add_input('p', 't', Variable('x'))
        >>> (n.post('p'), n.pre('t')) == (set(['t']), set(['p']))
        True
        >>> n.transition('t').modes()
        [Substitution(x=0), Substitution(x=2)]
        >>> n.place('p').tokens == MultiSet([0, 1, 2])
        True
        >>> n.transition('t').fire(Substitution(x=0))
        >>> n.place('p').tokens == MultiSet([1, 2])
        True
        >>> try : n.add_input('p', 't', Value(42))
        ... except ConstraintError: print(sys.exc_info()[1])
        already connected to 'p'

        @param place: the name of the place to connect
        @type place: `str`
        @param trans: the name of the transition to connect
        @type trans: `str`
        @param label: the annotation of the arc
        @type label: `ArcAnnotation`
        @raise ConstraintError: in case of anything not allowed
        """
        if not label.input_allowed :
            raise ConstraintError("'%s' not allowed on input arcs" % label.__class__.__name__)
        try :
            p = self._place[place]
        except KeyError :
            raise NodeError("place '%s' not found" % place)
        try :
            t = self._trans[trans]
        except KeyError :
            raise NodeError("transition '%s' not found" % trans)
        t.add_input(p, label)
        p.post[trans] = label
        t.pre[place] = label
        if hasattr(label, "globals") :
            label.globals.attach(self.globals)
    def remove_input (self, place, trans) :
        """Remove an input arc between `place` and `trans` (nodes names).

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', range(3)))
        >>> n.add_transition(Transition('t', Expression('x!=1')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> (n.post('p'), n.pre('t')) == (set(['t']), set(['p']))
        True
        >>> n.remove_input('p', 't')
        >>> (n.post('p'), n.pre('t')) == (set([]), set([]))
        True
        >>> try : n.remove_input('p', 't')
        ... except ConstraintError : print(sys.exc_info()[1])
        not connected to 'p'

        @param place: the name of the place to disconnect
        @type place: `str`
        @param trans: the name of the transition to disconnect
        @type trans: `str`
        @raise ConstraintError: when this arc does not exist
        """
        try :
            p = self._place[place]
        except KeyError :
            raise NodeError("place '%s' not found" % place)
        try :
            t = self._trans[trans]
        except KeyError :
            raise NodeError("transition '%s' not found" % trans)
        t.remove_input(p)
        l = p.post[trans]
        del p.post[trans]
        del t.pre[place]
        if hasattr(l, "globals") :
            l.globals.detach(self.globals)
    def add_output (self, place, trans, label) :
        """Add an output arc between `place` and `trans` (nodes names).

        An output arc is directed from a transition toward a place.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p'))
        >>> n.add_transition(Transition('t'))
        >>> n.add_output('p', 't', Value(42))
        >>> (n.post('t'), n.pre('p')) == (set(['p']), set(['t']))
        True
        >>> n.place('p').tokens == MultiSet([])
        True
        >>> n.transition('t').fire(Substitution())
        >>> n.place('p').tokens == MultiSet([42])
        True
        >>> try : n.add_output('p', 't', Value(42))
        ... except ConstraintError : print(sys.exc_info()[1])
        already connected to 'p'

        @param place: the name of the place to connect
        @type place: `str`
        @param trans: the name of the transition to connect
        @type trans: `str`
        @param label: the annotation of the arc
        @type label: `ArcAnnotation`
        @raise ConstraintError: in case of anything not allowed
        """
        try :
            p = self._place[place]
        except KeyError :
            raise NodeError("place '%s' not found" % place)
        try :
            t = self._trans[trans]
        except KeyError :
            raise NodeError("transition '%s' not found" % trans)
        t.add_output(p, label)
        p.pre[trans] = label
        t.post[place] = label
        if hasattr(label, "globals") :
            label.globals.attach(self.globals)
    def remove_output (self, place, trans) :
        """Remove an output arc between `place` and `trans` (nodes
        names).

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p'))
        >>> n.add_transition(Transition('t'))
        >>> n.add_output('p', 't', Value(42))
        >>> (n.post('t'), n.pre('p')) == (set(['p']), set(['t']))
        True
        >>> n.remove_output('p', 't')
        >>> (n.post('t'), n.pre('p')) == (set([]), set([]))
        True
        >>> try : n.remove_output('p', 't')
        ... except ConstraintError : print(sys.exc_info()[1])
        not connected to 'p'

        @param place: the name of the place to disconnect
        @type place: `str`
        @param trans: the name of the transition to disconnect
        @type trans: `str`
        @raise ConstraintError: when this arc does not exist
        """
        try :
            p = self._place[place]
        except KeyError :
            raise NodeError("place '%s' not found" % place)
        try :
            t = self._trans[trans]
        except KeyError :
            raise NodeError("transition '%s' not found" % trans)
        t.remove_output(p)
        l = p.pre[trans]
        del p.pre[trans]
        del t.post[place]
        if hasattr(l, "globals") :
            l.globals.detach(self.globals)
    def pre (self, nodes) :
        """Return the set of nodes names preceeding `nodes`. `nodes`
        can be a single node name ot a list of nodes names.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p1'))
        >>> n.add_place(Place('p2'))
        >>> n.add_transition(Transition('t1'))
        >>> n.add_transition(Transition('t2'))
        >>> n.add_output('p1', 't1', Value(1))
        >>> n.add_output('p2', 't2', Value(2))
        >>> n.pre('p1') == set(['t1'])
        True
        >>> n.pre(['p1', 'p2']) == set(['t2', 't1'])
        True

        @param nodes: a single node name or a list of node names
        @type nodes: `list`
        @return: a set of node names
        @rtype: `set`
        """
        result = set()
        for node in iterate(nodes) :
            try :
                result.update(self._node[node].pre.keys())
            except KeyError :
                raise NodeError("node '%s' not found" % node)
        return result
    def post (self, nodes) :
        """Return the set of nodes names succeeding `nodes`. `nodes`
        can be a single node name ot a list of nodes names.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p1'))
        >>> n.add_place(Place('p2'))
        >>> n.add_transition(Transition('t1'))
        >>> n.add_transition(Transition('t2'))
        >>> n.add_output('p1', 't1', Value(1))
        >>> n.add_output('p2', 't2', Value(2))
        >>> n.post('t1') == set(['p1'])
        True
        >>> n.post(['t1', 't2']) == set(['p2', 'p1'])
        True

        @param nodes: a single node name or a list of node names
        @type nodes: `list`
        @return: a set of node names
        @rtype: `set`
        """
        result = set()
        for node in iterate(nodes) :
            try :
                result.update(self._node[node].post.keys())
            except KeyError :
                raise NodeError("node '%s' not found" % node)
        return result
    def get_marking (self) :
        """Return the current marking of the net, omitting empty places.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p0', range(0)))
        >>> n.add_place(Place('p1', range(1)))
        >>> n.add_place(Place('p2', range(2)))
        >>> n.add_place(Place('p3', range(3)))
        >>> n.get_marking() == Marking({'p2': MultiSet([0, 1]), 'p3': MultiSet([0, 1, 2]), 'p1': MultiSet([0])})
        True

        @return: the current marking
        @rtype: `Marking`
        """
        return Marking((name, place.tokens.copy())
                       for name, place in self._place.items()
                       if not place.is_empty())
    def _set_marking (self, marking) :
        """Assign a marking to the net.

        Places not listed in the marking are considered empty, the
        corresponding place in the net is thus emptied. If the marking
        has places that do not belong to the net, these are ignored
        (as in the last instruction below). If an error occurs during
        the assignment, the marking is left inconsistent. You should
        thus use `set_marking` unless you will have no error.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p0', range(5)))
        >>> n.add_place(Place('p1'))
        >>> n.add_place(Place('p2'))
        >>> n.add_place(Place('p3', [], tInteger))
        >>> n.get_marking() == Marking({'p0': MultiSet([0, 1, 2, 3, 4])})
        True
        >>> n._set_marking(Marking(p1=MultiSet([0]), p2=MultiSet([0, 1]), p3=MultiSet([0, 1, 2])))
        >>> n.get_marking() == Marking({'p2': MultiSet([0, 1]), 'p3': MultiSet([0, 1, 2]), 'p1': MultiSet([0])})
        True
        >>> n._set_marking(Marking(p=MultiSet([0])))
        >>> n.get_marking()
        Marking({})
        >>> try : n._set_marking(Marking(p2=MultiSet([1]), p3=MultiSet([3.14])))
        ... except ValueError : print(sys.exc_info()[1])
        forbidden token '3.14'
        >>> n.get_marking() # inconsistent
        Marking({'p2': MultiSet([1])})

        @param marking: the new marking
        @type marking: `Marking`
        """
        for name, place in self._place.items() :
            if name in marking :
                place.reset(marking[name])
            else :
                place.empty()
    def set_marking (self, marking) :
        """Assign a marking to the net. Places not listed in the
        marking are considered empty, the corresponding place in the
        net is thus emptied. If the marking has places that do not
        belong to the net, these are ignored (as in the last
        instruction below). If an error occurs during the assignment,
        the marking is left unchanged.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p0', range(5), tInteger))
        >>> n.add_place(Place('p1'))
        >>> n.add_place(Place('p2'))
        >>> n.add_place(Place('p3'))
        >>> n.get_marking() == Marking({'p0': MultiSet([0, 1, 2, 3, 4])})
        True
        >>> n.set_marking(Marking(p1=MultiSet([0]), p2=MultiSet([0, 1]), p3=MultiSet([0, 1, 2])))
        >>> n.get_marking() == Marking({'p2': MultiSet([0, 1]), 'p3': MultiSet([0, 1, 2]), 'p1': MultiSet([0])})
        True
        >>> n.set_marking(Marking(p=MultiSet([0])))
        >>> n.get_marking()
        Marking({})
        >>> try : n.set_marking(Marking(p2=MultiSet([1]), p0=MultiSet([3.14])))
        ... except ValueError : print(sys.exc_info()[1])
        forbidden token '3.14'
        >>> n.get_marking() # unchanged
        Marking({})

        @param marking: the new marking
        @type marking: `Marking`
        """
        old = self.get_marking()
        try :
            self._set_marking(marking)
        except :
            self._set_marking(old)
            raise
    def add_marking (self, marking) :
        """Add a marking to the current one. If an error occurs during
        the process, the marking is left unchanged. Places in the
        marking that do not belong to the net are ignored.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p1'))
        >>> n.add_place(Place('p2', range(3)))
        >>> n.get_marking() == Marking({'p2': MultiSet([0, 1, 2])})
        True
        >>> n.add_marking(Marking(p1=MultiSet(range(2)), p2=MultiSet([1])))
        >>> n.get_marking() == Marking({'p2': MultiSet([0, 1, 1, 2]), 'p1': MultiSet([0, 1])})
        True

        @param marking: the new marking
        @type marking: `Marking`
        """
        old = self.get_marking()
        try :
            for place, tokens in marking.items() :
                if place in self._place :
                    self._place[place].add(tokens)
        except :
            self._set_marking(old)
            raise
    def remove_marking (self, marking) :
        """Substract a marking from the current one. If an error
        occurs during the process, the marking is left unchanged.
        Places in the marking that do not belong to the net are
        ignored.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p1'))
        >>> n.add_place(Place('p2', range(3)))
        >>> n.get_marking() == Marking({'p2': MultiSet([0, 1, 2])})
        True
        >>> try : n.remove_marking(Marking(p1=MultiSet(range(2)), p2=MultiSet([1])))
        ... except ValueError : print(sys.exc_info()[1])
        not enough occurrences
        >>> n.get_marking() == Marking({'p2': MultiSet([0, 1, 2])})
        True
        >>> n.remove_marking(Marking(p2=MultiSet([1])))
        >>> n.get_marking() == Marking({'p2': MultiSet([0, 2])})
        True

        @param marking: the new marking
        @type marking: `Marking`
        """
        old = self.get_marking()
        try :
            for place, tokens in marking.items() :
                if place in self._place :
                    self._place[place].remove(tokens)
        except :
            self._set_marking(old)
            raise
    def rename_node (self, old, new) :
        """Change the name of a node.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p'))
        >>> n.add_transition(Transition('t'))
        >>> n.add_output('p', 't', Value(0))
        >>> list(sorted(n.node(), key=str))
        [Place('p', MultiSet([]), tAll), Transition('t', Expression('True'))]
        >>> n.post('t') == set(['p'])
        True
        >>> n.rename_node('p', 'new_p')
        >>> list(sorted(n.node(), key=str))
        [Place('new_p', MultiSet([]), tAll), Transition('t', Expression('True'))]
        >>> n.post('t') == set(['new_p'])
        True
        >>> try : n.rename_node('new_p', 't')
        ... except ConstraintError : print(sys.exc_info()[1])
        node 't' exists
        >>> try : n.rename_node('old_t', 'new_t')
        ... except ConstraintError : print(sys.exc_info()[1])
        node 'old_t' not found

        @param old: the current name of the node
        @type old: `str`
        @param new: the new name for the node
        @type new: `str`
        """
        if new in self._node :
            raise ConstraintError("node '%s' exists" % new)
        elif old not in self._node :
            raise ConstraintError("node '%s' not found" % old)
        node = self._node[old]
        del self._node[old]
        self._node[new] = node
        node.lock("name", self, new)
        if old in self._place :
            del self._place[old]
            self._place[new] = node
        else :
            del self._trans[old]
            self._trans[new] = node
        for name in node.pre :
            other = self._node[name]
            other.post[new] = other.post[old]
            del other.post[old]
        for name in node.post :
            other = self._node[name]
            other.pre[new] = other.pre[old]
            del other.pre[old]
    def copy_place (self, source, targets) :
        """Make copies of the `source` place (use place names).

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', range(3)))
        >>> n.add_transition(Transition('t'))
        >>> n.add_input('p', 't', Value(0))
        >>> n.copy_place('p', ['bis', 'ter'])
        >>> n.copy_place('bis', 'more')
        >>> list(sorted(n.place(), key=str))
        [Place('bis', MultiSet([...]), tAll),
         Place('more', MultiSet([...]), tAll),
         Place('p', MultiSet([...]), tAll),
         Place('ter', MultiSet([...]), tAll)]
        >>> list(sorted(n.pre('t'), key=str))
        ['bis', 'more', 'p', 'ter']

        @param source: the name of the place to copy
        @type source: `str`
        @param targets: a name or a list of names for the copie(s)
        @type targets: `str`
        """
        src = self.place(source)
        for target in iterate(targets) :
            self.add_place(src.copy(target))
            for trans, label in src.post.items() :
                self.add_input(target, trans, label.copy())
            for trans, label in src.pre.items() :
                self.add_output(target, trans, label.copy())
    def copy_transition (self, source, targets) :
        """Make copies of the `source` transition (use transition names).

        >>> n = PetriNet('N')
        >>> n.add_transition(Transition('t', Expression('x==1')))
        >>> n.add_place(Place('p'))
        >>> n.add_input('p', 't', Value(0))
        >>> n.copy_transition('t', ['bis', 'ter'])
        >>> n.copy_transition('bis', 'more')
        >>> list(sorted(n.transition(), key=str))
        [Transition('bis', Expression('x==1')),
         Transition('more', Expression('x==1')),
         Transition('t', Expression('x==1')),
         Transition('ter', Expression('x==1'))]
        >>> list(sorted(n.post('p')))
        ['bis', 'more', 't', 'ter']

        @param source: the name of the transition to copy
        @type source: `str`
        @param targets: a name or a list of names for the copie(s)
        @type targets: `str`
        """
        src = self.transition(source)
        for target in iterate(targets) :
            self.add_transition(src.copy(target))
            for place, label in src.pre.items() :
                self.add_input(place, target, label.copy())
            for place, label in src.post.items() :
                self.add_output(place, target, label.copy())
    def merge_places (self, target, sources) :
        """Create a new place by merging those in `sources`. Markings
        are added, place types are 'or'ed and arcs labels are joinded
        into multi-arcs, the sources places are not removed. Use
        places names.

        >>> n = PetriNet('n')
        >>> n.add_place(Place('p1', [1], tInteger))
        >>> n.add_place(Place('p2', [2.0], tFloat))
        >>> n.add_transition(Transition('t1'))
        >>> n.add_transition(Transition('t2'))
        >>> n.add_output('p1', 't1', Value(1))
        >>> n.add_output('p2', 't2', Value(2.0))
        >>> n.add_output('p2', 't1', Value(2.0))
        >>> n.merge_places('p', ['p1', 'p2'])
        >>> (n.pre('p'), n.post('t1')) == (set(['t2', 't1']), set(['p2', 'p', 'p1']))
        True
        >>> list(sorted(n.node('p').pre.items()))
        [('t1', MultiArc((Value(1), Value(2.0)))),
         ('t2', Value(2.0))]
        >>> n.node('p').tokens == MultiSet([1, 2.0])
        True
        >>> n.node('p').checker()
        (Instance(int) | Instance(float))

        @param target: the name of the created place
        @type target: `str`
        @param sources: the list of places names to be merged (or a
            single place name)
        @type sources: `list`
        """
        srclist = [self.place(p) for p in iterate(sources)]
        new = srclist[0].__class__(target, srclist[0].tokens, srclist[0]._check)
        self.add_place(new)
        for place in srclist[1:] :
            new._check |= place._check
            new.tokens.add(place.tokens)
        post = {}
        for place in srclist :
            for trans, label in place.post.items() :
                if trans not in post :
                    post[trans] = []
                if label.__class__ is MultiArc :
                    post[trans].extend([x.copy() for x in label])
                else :
                    post[trans].append(label.copy())
        for trans, labels in post.items() :
            if len(labels) == 1 :
                self.add_input(target, trans, labels[0])
            else :
                self.add_input(target, trans, MultiArc(labels))
        pre = {}
        for place in srclist :
            for trans, label in place.pre.items() :
                if trans not in pre :
                    pre[trans] = []
                if label.__class__ is MultiArc :
                    pre[trans].extend([x.copy() for x in label])
                else :
                    pre[trans].append(label.copy())
        for trans, labels in pre.items() :
            if len(labels) == 1 :
                self.add_output(target, trans, labels[0])
            else :
                self.add_output(target, trans, MultiArc(labels))
    def merge_transitions (self, target, sources) :
        """Create a new transition by merging those in `sources`.
        Guards are 'and'ed and arcs labels are joinded into multi-
        arcs, the sources transitions are not removed. Use transitions
        names.

        >>> n = PetriNet('n')
        >>> n.add_place(Place('p1'))
        >>> n.add_place(Place('p2'))
        >>> n.add_transition(Transition('t1', Expression('x==1')))
        >>> n.add_transition(Transition('t2', Expression('y==2')))
        >>> n.add_output('p1', 't1', Value(1))
        >>> n.add_output('p2', 't2', Value(2.0))
        >>> n.add_output('p2', 't1', Value(2.0))
        >>> n.merge_transitions('t', ['t1', 't2'])
        >>> list(sorted(n.post('t'), key=str))
        ['p1', 'p2']
        >>> list(sorted(n.pre('p2'), key=str))
        ['t', 't1', 't2']
        >>> n.transition('t')
        Transition('t', Expression('(x==1) and (y==2)'))
        >>> n.node('t').post
        {'p2': MultiArc((Value(2.0), Value(2.0))), 'p1': Value(1)}

        @param target: the name of the created transition
        @type target: `str`
        @param sources: the list of transitions names to be merged (or
            a single transition name)
        @type sources: `list`
        """
        srclist = [self.transition(t) for t in iterate(sources)]
        new = srclist[0].__class__(target)
        for trans in srclist :
            new.guard &= trans.guard
        self.add_transition(new)
        pre = {}
        for trans in srclist :
            for place, label in trans.pre.items() :
                if place not in pre :
                    pre[place] = []
                #FIXME: not good! but breaks on Tuple
                if label.__class__ is MultiArc :
                    pre[place].extend([x.copy() for x in label])
                else :
                    pre[place].append(label.copy())
        for place, labels in pre.items() :
            if len(labels) == 1 :
                self.add_input(place, target, labels[0])
            else :
                self.add_input(place, target, MultiArc(labels))
        post = {}
        for trans in srclist :
            for place, label in trans.post.items() :
                if place not in post :
                    post[place] = []
                #FIXME: not good! but breaks on Tuple
                if label.__class__ is MultiArc :
                    post[place].extend([x.copy() for x in label])
                else :
                    post[place].append(label.copy())
        for place, labels in post.items() :
            if len(labels) == 1 :
                self.add_output(place, target, labels[0])
            else :
                self.add_output(place, target, MultiArc(labels))

##
## marking graph
##

class StateGraph (object) :
    "The graph of reachable markings of a net."
    def __init__ (self, net) :
        """Initialise with the net.

        >>> StateGraph(PetriNet('N')).net
        PetriNet('N')

        @param net: the Petri net whose graph has to be computed
        @type net: `PetriNet`
        """
        self.net = net.copy()
        self._todo = []
        self._done = set([])
        self._removed = set([])
        self._state = {}
        self._marking = {}
        self._succ = {}
        self._pred = {}
        self._last = -1
        self._create_state(net.get_marking(), None, None, None)
        self._current = 0
    def _create_state (self, marking, source, trans, mode) :
        self._last += 1
        self._marking[self._last] = marking
        self._state[marking] = self._last
        self._pred[self._last] = {}
        self._succ[self._last] = {}
        self._todo.append(self._last)
        return self._last
    def goto (self, state) :
        """Change the current state to another (given by its number).
        This also changes the marking of the net consistently. Notice
        that the state may not exist yet.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> try : g.goto(2)
        ... except ValueError : print(sys.exc_info()[1])
        unknown state
        >>> g.build()
        >>> g.goto(2)
        >>> g.net.get_marking()
        Marking({'p': MultiSet([2])})

        @param state: the number of the state to go to
        @type state: non-negative `int`
        """
        if state is None or state in self._removed :
            state = self.current()
        if state in self._marking :
            if self._current != state :
                self._current = state
                self.net.set_marking(self._marking[state])
        else :
            raise ValueError("unknown state")
    def current (self) :
        """Return the number of the current state.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> g.current()
        0

        @return: the number of the current state
        @rtype: non-negative `int`
        """
        if self._current in self._removed :
            if len(self._todo) > 0 :
                return self._todo[0]
            elif len(self._done) > 0 :
                return next(iter(self._done))
            else :
                raise ConstraintError("all states removed")
        else :
            return self._current
    def __getitem__ (self, state) :
        """Return a marking by its state number.
        """
        return self._marking[state]
    def _remove_state (self, state) :
        self._removed.add(state)
        self._done.discard(state)
        while True :
            try :
                self._todo.remove(state)
            except :
                break
        marking = self._marking.pop(state)
        del self._state[marking]
        if state in self._pred :
            for pred in self._pred[state].keys() :
                for label in self._pred[state][pred].copy() :
                    self._remove_edge(pred, state, label)
        if state in self._succ :
            for succ in self._succ[state].keys() :
                for label in self._succ[state][succ].copy() :
                    self._remove_edge(state, succ, label)
        if state == self._current :
            self.goto(None)
        return marking
    def _create_edge (self, source, target, label) :
        if target in self._succ[source] :
            self._succ[source][target].add(label)
        else :
            self._succ[source][target] = set([label])
        if source in self._pred[target] :
            self._pred[target][source].add(label)
        else :
            self._pred[target][source] = set([label])
    def _remove_edge (self, source, target, label) :
        self._succ[source][target].remove(label)
        if len(self._succ[source][target]) == 0 :
            del self._succ[source][target]
        self._pred[target][source].remove(label)
        if len(self._pred[target][source]) == 0 :
            del self._pred[target][source]
    def __contains__ (self, marking) :
        return marking in self._state
    def successors (self, state=None) :
        """Return the successors of the current state. The value
        returned is a dictionnary mapping the numbers of successor
        states to pairs `(trans, mode)` representing the name of the
        transition and the binding needed to reach the new state.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> g.build()
        >>> g.goto(2)
        >>> g.successors()
        {3: (Transition('t', Expression('x<5')), Substitution(x=2))}

        @return: the dictionnary of successors and transitions to them
        @rtype: `dict` mapping non-negative `int` to `tuple` holding a
            `str` and a `Substitution`
        """
        if state is None :
            state = self.current()
        self._process(state)
        return dict((succ, label) for succ in self._succ[state]
                     for label in self._succ[state][succ])
    def predecessors (self, state=None) :
        """Return the predecessors states. The returned value is as in
        `successors`. Notice that if the graph is not complete, this
        value may be wrong: states computed in the future may lead to
        the current one thus becoming one of its predecessors.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> g.build()
        >>> g.goto(2)
        >>> g.predecessors()
        {1: (Transition('t', Expression('x<5')), Substitution(x=1))}

        @return: the dictionnary of predecessors and transitions to
            them
        @rtype: `dict` mapping non-negative `int` to `tuple` holding a
            `str` and a `Substitution`
        """
        if state is None :
            state = self.current()
        return dict((pred, label) for pred in self._pred[state]
                     for label in self._pred[state][pred])
    def _fire (self, trans, mode) :
        "Fire trans with the given mode"
        trans.fire(mode)
    def _process (self, state) :
        current = self.current()
        for state in self._build(state) :
            pass
        self.goto(current)
    def _get_state (self, marking) :
        return self._state.get(marking, None)
    def _compute (self, state) :
        self._done.add(state)
        self.goto(state)
        marking = self.net.get_marking()
        for trans in self.net.transition() :
            for mode in trans.modes() :
                self._fire(trans, mode)
                new_marking = self.net.get_marking()
                target = self._get_state(new_marking)
                if target is None :
                    target = self._create_state(new_marking, state, trans, mode)
                if state in self._marking :
                    self._create_edge(state, target, (trans, mode))
                self.net.set_marking(marking)
                if state not in self._marking :
                    return
    def __len__ (self) :
        """Return the number of states currently reached.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> len(g)
        1
        >>> for state in g :
        ...     print('%s states known' % len(g))
        2 states known
        3 states known
        4 states known
        5 states known
        6 states known
        6 states known

        @return: the number of states generated at call time
        @rtype: `int`
        """
        return len(self._done) + len(self._todo)
    def __iter__ (self) :
        """Iterate over the reachable states (numbers). If needed, the
        successors of each state are computed just before it is yield.
        So, if the graph is not complete, getting the predecessors may
        be wrong during the iteration.

        **Warning:** the net may have an infinite state graph, which
        is not checked. So you may enter an infinite iteration.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> for state in g :
        ...     print('state %s is %r' % (state, g.net.get_marking()))
        state 0 is Marking({'p': MultiSet([0])})
        state 1 is Marking({'p': MultiSet([1])})
        state 2 is Marking({'p': MultiSet([2])})
        state 3 is Marking({'p': MultiSet([3])})
        state 4 is Marking({'p': MultiSet([4])})
        state 5 is Marking({'p': MultiSet([5])})
        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t'))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('(x+1) % 5'))
        >>> g = StateGraph(n)
        >>> for state in g :
        ...     print('state %s is %r' % (state, g.net.get_marking()))
        state 0 is Marking({'p': MultiSet([0])})
        state 1 is Marking({'p': MultiSet([1])})
        state 2 is Marking({'p': MultiSet([2])})
        state 3 is Marking({'p': MultiSet([3])})
        state 4 is Marking({'p': MultiSet([4])})
        """
        current = self.current()
        for state in sorted(self._done) :
            self.goto(state)
            yield state
        for state in self._build() :
            self.goto(state)
            yield state
        self.goto(current)
    def _build (self, stop=None) :
        """Build the complete reachability graph.

        The graph is build using a breadth first exploration as the
        newly computed states are put in a queue.

        **Warning:** this may be infinite! No check of this is
        performed.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> len(g)
        1
        >>> g.build()
        >>> len(g)
        6
        """
        while len(self._todo) > 0 and (stop is None or self._todo[0] <= stop) :
            state = self._todo.pop(0)
            self._compute(state)
            yield state
    def build (self) :
        for state in self._build() :
            pass
    def completed (self) :
        """Check if all the reachable markings have been explored.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> for state in g :
        ...     print('%s %s' % (state, g.completed()))
        0 False
        1 False
        2 False
        3 False
        4 False
        5 True

        @return: `True` if the graph has been completely computed,
            `False` otherwise
        @rtype: `bool`
        """
        return len(self._todo) == 0
    def todo (self) :
        """Return the number of states whose successors are not yet
        computed.

        >>> n = PetriNet('N')
        >>> n.add_place(Place('p', [0]))
        >>> n.add_transition(Transition('t', Expression('x<5')))
        >>> n.add_input('p', 't', Variable('x'))
        >>> n.add_output('p', 't', Expression('x+1'))
        >>> g = StateGraph(n)
        >>> for state in g :
        ...     print('%s %s' % (state, g.todo()))
        0 1
        1 1
        2 1
        3 1
        4 1
        5 0

        @return: the number of pending states
        @rtype: `int`
        """
        return len(self._todo)
