"""Typing system for places (and transitions guards). Types are
contraint checkers to verify whether a value is in the type or not.
For instance:

>>> 5 in tInteger
True
>>> 4.3 in tInteger
False

The typechecking of several values is possible using the type as a
function. It fails if one value is not in the type.

>>> tInteger(5, 4, 6)
True
>>> tInteger(5, 4, 6.0)
False

Types can be composed in order to build more complexe types. For
example:

>>> 8 in (tInteger & ~Range(1, 5))
True
>>> 3 in (tInteger & ~Range(1, 5))
False

The various compositions are the same as sets operations, plus the
complement: `&`, `|`, `-`, `^` and `~` (complement).

Various types are predefined (like `tInteger`) the others can be
constructed using the various classes in the module. Prefefined types
are:

  * `tAll`: any value is in the type
  * `tNothing`: empty type
  * `tString`: string values
  * `tList`: lists values
  * `tInteger`: integer values
  * `tNatural`: non-negative integers
  * `tPositive`: strictly positive integers
  * `tFloat`: float values
  * `tNumber`: integers or float values
  * `tDict`: Python's `dict` values
  * `tNone`: the single value `None`
  * `tBoolean`: `True` or `False`
  * `tTuple`: tuple values
  * `tPair`: tuples of length two

Types with finitely many elements can be iterated over:

>>> list(sorted(iter(CrossProduct(Range(0, 10, 2), tBoolean) & ~OneOf((4, True), (6, False)))))
[(0, False), (0, True), (2, False), (2, True), (4, False), (6, True), (8, False), (8, True)]
>>> list(iter(OneOf(1, 2, 3)))
[1, 2, 3]
>>> iter(tInteger)
Traceback (most recent call last):
...
TypeError: ... not iterable
>>> iter(~OneOf(1, 2, 3))
Traceback (most recent call last):
...
TypeError: ... not iterable
"""

import inspect, sys
from snakes.compat import *
from snakes.data import cross
from snakes.pnml import Tree

def _iterable (obj, *types) :
    for t in types :
        try :
            iter(t)
        except :
            def __iterable__ () :
                raise ValueError("iteration over non-sequence")
            obj.__iterable__ = __iterable__
            break

class Type (object) :
    """Base class for all types. Implements operations `&`, `|`, `-`,
    `^` and `~` to build new types. Also implement the typechecking of
    several values. All the subclasses should implement the method
    `__contains__` to typecheck a single object.

    This class is abstract and should not be instantiated.
    """
    # apidoc skip
    def __init__ (self) :
        """Abstract method

        >>> Type()
        Traceback (most recent call last):
         ...
        NotImplementedError: abstract class

        @raise NotImplementedError: when called
        """
        raise NotImplementedError("abstract class")
    # apidoc skip
    def __eq__ (self, other) :
        return (self.__class__ == other.__class__
                and self.__dict__ == other.__dict__)
    # apidoc skip
    def __hash__ (self) :
        return hash(repr(self))
    def __and__ (self, other) :
        """Intersection type.

        >>> Instance(int) & Greater(0)
        (Instance(int) & Greater(0))

        @param other: the other type in the intersection
        @type other: `Type`
        @return: the intersection of both types
        @rtype: `Type`
        """
        if other is self :
            return self
        else :
            return _And(self, other)
    def __or__ (self, other) :
        """Union type.

        >>> Instance(int) | Instance(bool)
        (Instance(int) | Instance(bool))

        @param other: the other type in the union
        @type other: `Type`
        @return: the union of both types
        @rtype: `Type`
        """
        if other is self :
            return self
        else :
            return _Or(self, other)
    def __sub__ (self, other) :
        """Substraction type.

        >>> Instance(int) - OneOf([0, 1, 2])
        (Instance(int) - OneOf([0, 1, 2]))

        @param other: the other type in the substraction
        @type other: `Type`
        @return: the type `self` minus the type `other`
        @rtype: `Type`
        """
        if other is self :
            return tNothing
        else :
            return _Sub(self, other)
    def __xor__ (self, other) :
        """Disjoint union type.

        >>> Greater(0) ^ Instance(float)
        (Greater(0) ^ Instance(float))

        @param other: the other type in the disjoint union
        @type other: `Type`
        @return: the disjoint union of both types
        @rtype: `Type`
        """
        if other is self :
            return tNothing
        else :
            return _Xor(self, other)
    def __invert__ (self) :
        """Complementary type.

        >>> ~ Instance(int)
        (~Instance(int))

        @return: the complementary type
        @rtype: `Type`
        """
        return _Invert(self)
    # apidoc skip
    def __iterable__ (self) :
        """Called to test if a type is iterable

        Should be replaced in subclasses that are not iterable

        @raise ValueError: if not iterable
        """
        pass
    def __call__ (self, *values) :
        """Typecheck values.

        >>> Instance(int)(3, 4, 5)
        True
        >>> Instance(int)(3, 4, 5.0)
        False

        @param values: values that have to be checked
        @type values: `object`
        @return: `True` if all the values are in the types, `False`
            otherwise
        @rtype: `bool`
        """
        for v in values :
            if v not in self :
                return False
        return True
    __pnmltag__ = "type"
    _typemap = None
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Load a `Type` from a PNML tree

        Uses the attribute `__pnmltype__` to know which type
        corresponds to a tag "<type domain='xxx'>"

        >>> s = List(tNatural | tBoolean).__pnmldump__()
        >>> Type.__pnmlload__(s)
        Collection(Instance(list),
                   ((Instance(int) & GreaterOrEqual(0))
                    | OneOf(True, False)))

        @param tree: the PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: the loaded type
        @rtype: `Type`
        """
        if cls._typemap is None :
            cls._typemap = {}
            for n, c in inspect.getmembers(sys.modules[cls.__module__],
                                           inspect.isclass) :
                try :
                    cls._typemap[c.__pnmltype__] = c
                except AttributeError :
                    pass
        return cls._typemap[tree["domain"]].__pnmlload__(tree)

class _BinaryType (Type) :
    """A type build from two other ones

    This class allows to factorize the PNML related code for various
    binary types.
    """
    def __pnmldump__ (self) :
        return Tree(self.__pnmltag__, None,
                    Tree("left", None, Tree.from_obj(self._left)),
                    Tree("right", None, Tree.from_obj(self._right)),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        return cls(tree.child("left").child().to_obj(),
                   tree.child("right").child().to_obj())

class _And (_BinaryType) :
    "Intersection of two types"
    __pnmltype__ = "intersection"
    def __init__ (self, left, right) :
        self._left = left
        self._right = right
        _iterable(self, left)
    def __repr__ (self) :
        return "(%s & %s)" % (repr(self._left), repr(self._right))
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return (value in self._left) and (value in self._right)
    def __iter__ (self) :
        self.__iterable__()
        for value in self._left :
            if value in self._right :
                yield value

class _Or (_BinaryType) :
    "Union of two types"
    __pnmltype__ = "union"
    def __init__ (self, left, right) :
        self._left = left
        self._right = right
        _iterable(self, left, right)
    def __repr__ (self) :
        return "(%s | %s)" % (repr(self._left), repr(self._right))
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return (value in self._left) or (value in self._right)
    def __iter__ (self) :
        self.__iterable__()
        for value in (self._left & self._right) :
            yield value
        for value in (self._left ^ self._right) :
            yield value

class _Sub (_BinaryType) :
    "Subtyping by difference"
    __pnmltype__ = "difference"
    def __init__ (self, left, right)  :
        self._left = left
        self._right = right
        _iterable(self, left)
    def __repr__ (self) :
        return "(%s - %s)" % (repr(self._left), repr(self._right))
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return (value in self._left) and (value not in self._right)
    def __iter__ (self) :
        self.__iterable__()
        for value in self._left :
            if value not in self._right :
                yield value

class _Xor (_BinaryType) :
    "Exclusive union of two types"
    __pnmltype__ = "xor"
    def __init__ (self, left, right) :
        self._left = left
        self._right = right
        _iterable(self, left, right)
    def __repr__ (self) :
        return "(%s ^ %s)" % (repr(self._left), repr(self._right))
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        if value in self._left :
            return value not in self._right
        else :
            return value in self._right
    def __iter__ (self) :
        self.__iterable__()
        for value in self._left :
            if value not in self._right :
                yield value
        for value in self._right :
            if value not in self._left :
                yield value

class _Invert (Type) :
    "Complement of a type"
    def __init__ (self, base) :
        self._base = base
        _iterable(self, None)
    def __repr__ (self) :
        return "(~%s)" % repr(self._base)
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return (value not in self._base)
    __pnmltype__ = "complement"
    def __pnmldump__ (self) :
        return Tree(self.__pnmltag__, None,
                    Tree.from_obj(self._base),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        return cls(tree.child().to_obj())

class _All (Type) :
    "A type allowing for any value"
    def __init__ (self) :
        pass
    def __and__ (self, other) :
        return other
    def __or__ (self, other) :
        return self
    def __sub__ (self, other) :
        return ~other
    def __xor__ (self, other) :
        return ~other
    def __invert__ (self) :
        return tNothing
    def __repr__ (self) :
        return "tAll"
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        @param value: the value to check
        @type value: `object`
        @return: `True`
        @rtype: `bool`
        """
        return True
    def __call__ (self, *values) :
        """Typecheck values.

        @param values: values that have to be checked
        @type values: `objet`
        @return: `True`
        """
        return True
    __pnmltype__ = "universal"
    def __pnmldump__ (self) :
        """
        >>> tAll.__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="universal"/>
        </pnml>
        """
        return Tree(self.__pnmltag__, None, domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> Type.__pnmlload__(tAll.__pnmldump__())
        tAll
        """
        return cls()

class _Nothing (Type) :
    "A types with no value"
    def __init__ (self) :
        pass
    def __and__ (self, other) :
        return self
    def __or__ (self, other) :
        return other
    def __sub__ (self, other) :
        return self
    def __xor__ (self, other) :
        return other
    def __invert__ (self) :
        return tAll
    def __repr__ (self) :
        return "tNothing"
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        @param value: the value to check
        @type value: `object`
        @return: `False`
        @rtype: `bool`
        """
        return False
    def __call__ (self, *values) :
        """Typecheck values.

        @param values: values that have to be checked
        @type values: `objet`
        @return: `False`
        """
        return False
    def __iter__ (self) :
        pass
    __pnmltype__ = "empty"
    def __pnmldump__ (self) :
        return Tree(self.__pnmltag__, None, domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        return cls()

class Instance (Type) :
    """A type whose values are all instances of one class.

    >>> [1, 2] in Instance(list)
    True
    >>> (1, 2) in Instance(list)
    False
    """
    def __init__ (self, _class) :
        """Initialize the type

        >>> Instance(int)
        Instance(int)

        @param _class: the class of instance
        @type _class: `class`
        @return: initialized object
        @rtype: `Instance`
        """
        self._class = _class
    # apidoc stop
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> 5 in Instance(int)
        True
        >>> 5.0 in Instance(int)
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return isinstance(value, self._class)
    def __repr__ (self) :
        """String representation of the type, suitable for `eval`

        >>> repr(Instance(str))
        'Instance(str)'

        @return: precise string representation
        @rtype: `str`
        """
        return "Instance(%s)" % self._class.__name__
    __pnmltype__ = "instance"
    def __pnmldump__ (self) :
        """Dump a type to a PNML tree

        >>> Instance(int).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="instance">
          <object name="int" type="class"/>
         </type>
        </pnml>

        @return: the PNML representation of the type
        @rtype: `str`
        """
        return Tree(self.__pnmltag__, None,
                    Tree.from_obj(self._class),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Builds a type from its PNML representation

        >>> t = Instance(int).__pnmldump__()
        >>> Instance.__pnmlload__(t)
        Instance(int)

        @param tree: the PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: the loaded type
        @rtype: `Instance`
        """
        return cls(tree.child().to_obj())

def _full_name (fun) :
    if fun.__module__ is None :
        funname = fun.__name__
        for modname in sys.modules :
            try :
                if sys.modules[modname].__dict__.get(funname, None) is fun :
                    return ".".join([modname, funname])
            except :
                pass
        return funname
    else :
        return ".".join([fun.__module__, fun.__name__])

class TypeCheck (Type) :
    """A type whose values are accepted by a given function.

    >>> def odd (val) :
    ...     return type(val) is int and (val % 2) == 1
    >>> 3 in TypeCheck(odd)
    True
    >>> 4 in TypeCheck(odd)
    False
    >>> 3.0 in TypeCheck(odd)
    False
    """
    def __init__ (self, checker, iterate=None) :
        """Initialize the type, optionally, a function to iterate over
        the elements may be provided.

        >>> import operator
        >>> TypeCheck(operator.truth)
        TypeCheck(...truth)
        >>> list(TypeCheck(operator.truth))
        Traceback (most recent call last):
          ...
        ValueError: type not iterable
        >>> def true_values () : # enumerates only choosen values
        ...     yield True
        ...     yield 42
        ...     yield '42'
        ...     yield [42]
        ...     yield (42,)
        ...     yield {True: 42}
        >>> TypeCheck(operator.truth, true_values)
        TypeCheck(...truth, snakes.typing.true_values)
        >>> list(TypeCheck(operator.truth, true_values))
        [True, 42, '42', [42], (42,), {True: 42}]

        @param checker: a function that checks one value and returns
            `True` if it is in te type and `False` otherwise
        @type checker: `callable`
        @param iterate: `None` or an iterator over the values of the
            type
        @type iterate: `generator`
        """
        self._check = checker
        self._iterate = iterate
    # apidoc stop
    def __iter__ (self) :
        """
        >>> def odd (val) :
        ...     return type(val) is int and (val % 2) == 1
        >>> i = iter(TypeCheck(odd))
        Traceback (most recent call last):
          ...
        ValueError: type not iterable
        >>> def odd_iter () :
        ...     i = 1
        ...     while True :
        ...         yield i
        ...         yield -i
        ...         i += 2
        >>> i = iter(TypeCheck(odd, odd_iter))
        >>> next(i), next(i), next(i)
        (1, -1, 3)
        """
        try :
            return iter(self._iterate())
        except TypeError :
            raise ValueError("type not iterable")
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> def odd (val) :
        ...     return type(val) is int and (val % 2) == 1
        >>> 3 in TypeCheck(odd)
        True
        >>> 4 in TypeCheck(odd)
        False
        >>> 3.0 in TypeCheck(odd)
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return self._check(value)
    def __repr__ (self) :
        """
        >>> def odd (val) :
        ...     return type(val) is int and (val % 2) == 1
        >>> repr(TypeCheck(odd))
        'TypeCheck(snakes.typing.odd)'
        >>> def odd_iter () :
        ...     i = 1
        ...     while True :
        ...         yield i
        ...         yield -i
        ...         i += 2
        >>> repr(TypeCheck(odd, odd_iter))
        'TypeCheck(snakes.typing.odd, snakes.typing.odd_iter)'
        """
        if self._iterate is None :
            return "%s(%s)" % (self.__class__.__name__,
                               _full_name(self._check))
        else :
            return "%s(%s, %s)" % (self.__class__.__name__,
                                   _full_name(self._check),
                                   _full_name(self._iterate))
    __pnmltype__ = "checker"
    def __pnmldump__ (self) :
        """Dump type to a PNML tree

        >>> import operator
        >>> TypeCheck(operator.truth).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="checker">
          <checker>
           ...
          </checker>
          <iterator>
           <object type="NoneType"/>
          </iterator>
         </type>
        </pnml>
        >>> def true_values () : # enumerates only choosen values
        ...     yield True
        ...     yield 42
        ...     yield '42'
        ...     yield [42]
        ...     yield (42,)
        ...     yield {True: 42}
        >>> TypeCheck(operator.truth, true_values).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="checker">
          <checker>
           ...
          </checker>
          <iterator>
           <object name="snakes.typing.true_values" type="function"/>
          </iterator>
         </type>
        </pnml>

        Note that this last example would not work as `true_value` as
        been defined inside a docstring. In order to allow it to be
        re-loaded from PNML, it should be defined at module level.

        @return: the type serialized to PNML
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree("checker", None, Tree.from_obj(self._check)),
                    Tree("iterator", None, Tree.from_obj(self._iterate)),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Build type from a PNML tree

        >>> import operator
        >>> TypeCheck.__pnmlload__(TypeCheck(operator.truth).__pnmldump__())
        TypeCheck(....truth)
        >>> def true_values () : # enumerates only choosen values
        ...     yield True
        ...     yield 42
        ...     yield '42'
        ...     yield [42]
        ...     yield (42,)
        ...     yield {True: 42}

        @param tree: the PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: the loaded type
        @rtype: `TypeChecker`
        """
        return cls(tree.child("checker").child().to_obj(),
                   tree.child("iterator").child().to_obj())

class OneOf (Type) :
    """A type whose values are explicitely enumerated.

    >>> 3 in OneOf(1, 2, 3, 4, 5)
    True
    >>> 0 in OneOf(1, 2, 3, 4, 5)
    False
    """
    # apidoc stop
    def __init__ (self, *values) :
        """
        @param values: the enumeration of the values in the type
        @type values: `object`
        """
        self._values = values
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> 3 in OneOf(1, 2, 3, 4, 5)
        True
        >>> 0 in OneOf(1, 2, 3, 4, 5)
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return value in self._values
    def __repr__ (self) :
        """
        >>> repr(OneOf(1, 2, 3, 4, 5))
        'OneOf(1, 2, 3, 4, 5)'
        """
        return "OneOf(%s)" % ", ".join([repr(val) for val in self._values])
    def __iter__ (self) :
        """
        >>> list(iter(OneOf(1, 2, 3, 4, 5)))
        [1, 2, 3, 4, 5]
        """
        return iter(self._values)
    __pnmltype__ = "enum"
    def __pnmldump__ (self) :
        """Dump type to its PNML representation

        >>> OneOf(1, 2, 3, 4, 5).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="enum">
          <object type="int">
           1
          </object>
          <object type="int">
           2
          </object>
          <object type="int">
           3
          </object>
          <object type="int">
           4
          </object>
          <object type="int">
           5
          </object>
         </type>
        </pnml>

        @return: PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    *(Tree.from_obj(val) for val in self._values),
                    **dict(domain=self.__pnmltype__))
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Build type from its PNML representation

        >>> OneOf.__pnmlload__(OneOf(1, 2, 3, 4, 5).__pnmldump__())
        OneOf(1, 2, 3, 4, 5)

        @param tree: PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: loaded type
        @rtype: `OneOf`
        """
        return cls(*(child.to_obj() for child in tree.children))

class Collection (Type) :
    """A type whose values are a given container, holding items of a
    given type and ranging in a given interval.

    >>> [0, 1.1, 2, 3.3, 4] in Collection(Instance(list), tNumber, 3, 10)
    True
    >>> [0, 1.1] in Collection(Instance(list), tNumber, 3, 10) #too short
    False
    >>> [0, '1.1', 2, 3.3, 4] in Collection(Instance(list), tNumber, 3, 10) #wrong item
    False
    """
    def __init__ (self, collection, items, min=None, max=None) :
        """Initialise the type

        >>> Collection(Instance(list), tNumber, 3, 10)
        Collection(Instance(list), (Instance(int) | Instance(float)), min=3, max=10)

        @param collection: the collection type
        @type collection: `Type`
        @param items: the type of the items
        @type items: `Type`
        @param min: the smallest allowed value
        @type min: `object`
        @param max: the greatest allowed value
        @type max: `object`
        """
        self._collection = collection
        self._class = collection._class
        self._items = items
        self._max = max
        self._min = min
    # apidoc stop
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> [0, 1.1, 2, 3.3, 4] in Collection(Instance(list), tNumber, 3, 10)
        True
        >>> [0, 1.1] in Collection(Instance(list), tNumber, 3, 10) #too short
        False
        >>> [0, '1.1', 2, 3.3, 4] in Collection(Instance(list), tNumber, 3, 10) #wrong item
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        if value not in self._collection :
            return False
        try :
            len(value)
            iter(value)
        except TypeError :
            return False
        if (self._min is not None) and (len(value) < self._min) :
            return False
        if (self._max is not None) and (len(value) > self._max) :
            return False
        for item in value :
            if item not in self._items :
                return False
        return True
    def __repr__ (self) :
        """
        >>> repr(Collection(Instance(list), tNumber, 3, 10))
        'Collection(Instance(list), (Instance(int) | Instance(float)), min=3, max=10)'
        """
        if (self._min is None) and (self._max is None) :
            return "Collection(%s, %s)" % (repr(self._collection),
                                           repr(self._items))
        elif self._min is None :
            return "Collection(%s, %s, max=%s)" % (repr(self._collection),
                                                   repr(self._items),
                                                   repr(self._max))
        elif self._max is None :
            return "Collection(%s, %s, min=%s)" % (repr(self._collection),
                                                   repr(self._items),
                                                   repr(self._min))
        else :
            return "Collection(%s, %s, min=%s, max=%s)" % (repr(self._collection),
                                                           repr(self._items),
                                                           repr(self._min),
                                                           repr(self._max))
    __pnmltype__ = "collection"
    def __pnmldump__ (self) :
        """Dump type to a PNML tree

        >>> Collection(Instance(list), tNumber, 3, 10).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="collection">
          <container>
           <type domain="instance">
            <object name="list" type="class"/>
           </type>
          </container>
          <items>
           <type domain="union">
            <left>
             <type domain="instance">
              <object name="int" type="class"/>
             </type>
            </left>
            <right>
             <type domain="instance">
              <object name="float" type="class"/>
             </type>
            </right>
           </type>
          </items>
          <min>
           <object type="int">
            3
           </object>
          </min>
          <max>
           <object type="int">
            10
           </object>
          </max>
         </type>
        </pnml>

        @return: the PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree("container", None, Tree.from_obj(self._collection)),
                    Tree("items", None, Tree.from_obj(self._items)),
                    Tree("min", None, Tree.from_obj(self._min)),
                    Tree("max", None, Tree.from_obj(self._max)),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Load type from its PNML representation

        >>> t = Collection(Instance(list), tNumber, 3, 10).__pnmldump__()
        >>> Collection.__pnmlload__(t)
        Collection(Instance(list), (Instance(int) | Instance(float)),
                   min=3, max=10)

        @param tree: the PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: the loaded type
        @rtype: `Collection`
        """
        return cls(tree.child("container").child().to_obj(),
                   tree.child("items").child().to_obj(),
                   tree.child("min").child().to_obj(),
                   tree.child("max").child().to_obj())

def List (items, min=None, max=None) :
    """Shorthand for instantiating `Collection`

    >>> List(tNumber, min=3, max=10)
    Collection(Instance(list), (Instance(int) | Instance(float)), min=3, max=10)

    @param items: the type of the elements in the collection
    @type items: `Type`
    @param min: the minimum number of elements in the collection or
        `None`
    @type min: `int`
    @param max: the maximum number of elements in the collection or
        `None`
    @type max: `int`
    @return: a type that checks the given constraints
    @rtype: `Collection`
    """
    return Collection(Instance(list), items, min, max)

def Tuple (items, min=None, max=None) :
    """Shorthand for instantiating `Collection`

    >>> Tuple(tNumber, min=3, max=10)
    Collection(Instance(tuple), (Instance(int) | Instance(float)), min=3, max=10)

    @param items: the type of the elements in the collection
    @type items: `Type`
    @param min: the minimum number of elements in the collection or
        `None`
    @type min: `int`
    @param max: the maximum number of elements in the collection or
        `None`
    @type max: `int`
    @return: a type that checks the given constraints
    @rtype: `Collection`
    """
    return Collection(Instance(tuple), items, min, max)

def Set (items, min=None, max=None) :
    """Shorthand for instantiating `Collection`

    >>> Set(tNumber, min=3, max=10)
    Collection(Instance(set), (Instance(int) | Instance(float)), min=3, max=10)

    @param items: the type of the elements in the collection
    @type items: `Type`
    @param min: the minimum number of elements in the collection or
        `None`
    @type min: `int`
    @param max: the maximum number of elements in the collection or
        `None`
    @type max: `int`
    @return: a type that checks the given constraints
    @rtype: `Collection`
    """
    return Collection(Instance(set), items, min, max)

class Mapping (Type) :
    """A type whose values are mapping (eg, `dict`)

    >>> {'Yes': True, 'No': False} in Mapping(tString, tAll)
    True
    >>> {True: 1, False: 0} in Mapping(tString, tAll)
    False
    """
    def __init__ (self, keys, items, _dict=Instance(dict)) :
        """Initialise a mapping type

        >>> Mapping(tInteger, tFloat)
        Mapping(Instance(int), Instance(float), Instance(dict))
        >>> from snakes.data import hdict
        >>> Mapping(tInteger, tFloat, Instance(hdict))
        Mapping(Instance(int), Instance(float), Instance(hdict))

        @param keys: the type for the keys
        @type keys: `Type`
        @param items: the type for the items
        @type items: `Type`
        @param _dict: the class that mapping must be instances of
        @type _dict: `dict`
        """
        self._keys = keys
        self._items = items
        self._dict = _dict
    # apidoc stop
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> {'Yes': True, 'No': False} in Mapping(tString, tAll)
        True
        >>> {True: 1, False: 0} in Mapping(tString, tAll)
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        if not self._dict(value) :
            return False
        for key, item in value.items() :
            if key not in self._keys :
                return False
            if item not in self._items :
                return True
        return True
    def __repr__ (self) :
        """Return a string representation of the type suitable for `eval`

        >>> repr(Mapping(tString, tAll))
        'Mapping(Instance(str), tAll, Instance(dict))'

        @return: precise string representation
        @rtype: `str`
        """
        return "Mapping(%s, %s, %s)" % (repr(self._keys),
                                        repr(self._items),
                                        repr(self._dict))
    __pnmltype__ = "mapping"
    def __pnmldump__ (self) :
        """Dump type to a PNML tree

        >>> from snakes.hashables import hdict
        >>> Mapping(tString, tAll, Instance(hdict)).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="mapping">
          <keys>
           <type domain="instance">
            <object name="str" type="class"/>
           </type>
          </keys>
          <items>
           <type domain="universal"/>
          </items>
          <container>
           <type domain="instance">
            <object name="snakes.hashables.hdict" type="class"/>
           </type>
          </container>
         </type>
        </pnml>

        @return: PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree("keys", None, Tree.from_obj(self._keys)),
                    Tree("items", None, Tree.from_obj(self._items)),
                    Tree("container", None, Tree.from_obj(self._dict)),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Load type from its PNML representation

        >>> from snakes.hashables import hdict
        >>> t = Mapping(tString, tAll, Instance(hdict)).__pnmldump__()
        >>> Mapping.__pnmlload__(t)
        Mapping(Instance(str), tAll, Instance(hdict))

        @param tree: PNML representation of the type
        @type tree: `snakes.pnml.Tree`
        @return: the loaded type
        @rtype: `Mapping`
        """
        return cls(tree.child("keys").child().to_obj(),
                   tree.child("items").child().to_obj(),
                   tree.child("container").child().to_obj())

class Range (Type) :
    """A type whose values are in a given range

    Notice that ranges are not built into the memory so that huge
    values can be used.

    >>> 3 in Range(1, 2**128, 2)
    True
    >>> 4 in Range(1, 2**128, 2)
    False
    """
    def __init__ (self, first, last, step=1) :
        """The values are those that the builtin `range(first, last,
        step)` would return.

        >>> Range(1, 10)
        Range(1, 10)
        >>> Range(1, 10, 2)
        Range(1, 10, 2)

        @param first: first element in the range
        @type first: `int`
        @param last: upper bound of the range, not belonging to it
        @type last: `int`
        @param step: step between elements in the range
        @type step: `int`
        """
        self._first, self._last, self._step = first, last, step
    # apidoc stop
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> 1 in Range(1, 10, 2)
        True
        >>> 2 in Range(1, 10, 2)
        False
        >>> 9 in Range(1, 10, 2)
        True
        >>> 10 in Range(1, 10, 2)
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return ((self._first <= value < self._last)
                and ((value - self._first) % self._step == 0))
    def __repr__ (self) :
        """Return a string representation of the type suitable for `eval`

        >>> repr(Range(1, 2**128, 2))
        'Range(1, 340282366920938463463374607431768211456, 2)'

        @return: precise string representation
        @rtype: `str`
        """
        if self._step == 1 :
            return "Range(%s, %s)" % (self._first, self._last)
        else :
            return "Range(%s, %s, %s)" % (self._first, self._last, self._step)
    def __iter__ (self) :
        """Iterate over the elements of the type

        >>> list(iter(Range(1, 10, 3)))
        [1, 4, 7]

        @return: an iterator over the values belonging to the range
        @rtype: `generator`
        """
        return iter(xrange(self._first, self._last, self._step))
    __pnmltype__ = "range"
    def __pnmldump__ (self) :
        """Dump type to a PNML tree

        >>> Range(1, 10, 2).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="range">
          <first>
           <object type="int">
            1
           </object>
          </first>
          <last>
           <object type="int">
            10
           </object>
          </last>
          <step>
           <object type="int">
            2
           </object>
          </step>
         </type>
        </pnml>

        @return: PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree("first", None, Tree.from_obj(self._first)),
                    Tree("last", None, Tree.from_obj(self._last)),
                    Tree("step", None, Tree.from_obj(self._step)),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Build type from its PNML representation

        >>> Range.__pnmlload__(Range(1, 10, 2).__pnmldump__())
        Range(1, 10, 2)

        @param tree: PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: the loaded type
        @rtype: `Range`
        """
        return cls(tree.child("first").child().to_obj(),
                   tree.child("last").child().to_obj(),
                   tree.child("step").child().to_obj())

class Greater (Type) :
    """A type whose values are greater than a minimum.

    The minimum and the checked values can be of any type as soon as
    they can be compared with `>`.

    >>> 6 in Greater(3)
    True
    >>> 3 in Greater(3)
    False
    """
    def __init__ (self, min) :
        """Initialises the type

        >>> Greater(5)
        Greater(5)

        @param min: the greatest value not included in the type
        @type min: `object`
        """
        self._min = min
    # apidoc stop
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> 5 in Greater(3)
        True
        >>> 5 in Greater(3.0)
        True
        >>> 3 in Greater(3.0)
        False
        >>> 1.0 in Greater(5)
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        try :
            return value > self._min
        except :
            return False
    def __repr__ (self) :
        """Return a string representation of the type suitable for `eval`

        >>> repr(Greater(3))
        'Greater(3)'

        @return: precise string representation
        @rtype: `str`
        """
        return "Greater(%s)" % repr(self._min)
    __pnmltype__ = "greater"
    def __pnmldump__ (self) :
        """Dump type to its PNML representation

        >>> Greater(42).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="greater">
          <object type="int">
           42
          </object>
         </type>
        </pnml>

        @return: PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree.from_obj(self._min),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Build type from its PNLM representation

        >>> Greater.__pnmlload__(Greater(42).__pnmldump__())
        Greater(42)

        @param tree: PNML representation to load
        @type tree: `snakes.pnml.Tree`
        @return: loaded type
        @rtype: `Greater`
        """
        return cls(tree.child().to_obj())

class GreaterOrEqual (Type) :
    """A type whose values are greater or equal than a minimum.

    See the description of `Greater`
    """
    def __init__ (self, min) :
        """Initialises the type

        >>> GreaterOrEqual(5)
        GreaterOrEqual(5)

        @param min: the minimal allowed value
        @type min: `object`
        """
        self._min = min
    # apidoc stop
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> 5 in GreaterOrEqual(3)
        True
        >>> 5 in GreaterOrEqual(3.0)
        True
        >>> 3 in GreaterOrEqual(3.0)
        True
        >>> 1.0 in GreaterOrEqual(5)
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        try :
            return value >= self._min
        except :
            False
    def __repr__ (self) :
        """Return a strign representation of the type suitable for `eval`

        >>> repr(GreaterOrEqual(3))
        'GreaterOrEqual(3)'

        @return: precise string representation
        @rtype: `str`
        """
        return "GreaterOrEqual(%s)" % repr(self._min)
    __pnmltype__ = "greatereq"
    def __pnmldump__ (self) :
        """Dump type to its PNML representation

        >>> GreaterOrEqual(42).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="greatereq">
          <object type="int">
           42
          </object>
         </type>
        </pnml>

        @return: PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree.from_obj(self._min),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Build type from its PNLM representation

        >>> GreaterOrEqual.__pnmlload__(GreaterOrEqual(42).__pnmldump__())
        GreaterOrEqual(42)

        @param tree: PNML representation to load
        @type tree: `snakes.pnml.Tree`
        @return: loaded type
        @rtype: `GreaterOrEqual`
        """
        return cls(tree.child().to_obj())

class Less (Type) :
    """A type whose values are less than a maximum.

    See the description of `Greater`
    """
    def __init__ (self, max) :
        """Initialises the type

        >>> Less(5)
        Less(5)

        @param min: the smallest value not included in the type
        @type min: `object`
        """
        self._max = max
    # apidoc stop
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> 5.0 in Less(5)
        False
        >>> 4.9 in Less(5)
        True
        >>> 4 in Less(5.0)
        True

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return value < self._max
    def __repr__ (self) :
        """Return a string representation of the type suitable for `eval`

        >>> repr(Less(3))
        'Less(3)'

        @return: precise string representation
        @rtype: `str`
        """
        return "Less(%s)" % repr(self._max)
    __pnmltype__ = "less"
    def __pnmldump__ (self) :
        """Dump type to its PNML representation

        >>> Less(3).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="less">
          <object type="int">
           3
          </object>
         </type>
        </pnml>

        @return: PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree.from_obj(self._max),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Build type from its PNML representation

        >>> Less.__pnmlload__(Less(3).__pnmldump__())
        Less(3)

        @param tree: PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: loaded type
        @rtype: `Less`
        """
        return cls(tree.child().to_obj())

class LessOrEqual (Type) :
    """A type whose values are less than or equal to a maximum.

    See the description of `Greater`
    """
    def __init__ (self, max) :
        """Initialises the type

        >>> LessOrEqual(5)
        LessOrEqual(5)

        @param min: the greatest value the type
        @type min: `object`
        """

        self._max = max
    # apidoc stop
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> 5 in LessOrEqual(5.0)
        True
        >>> 5.1 in LessOrEqual(5)
        False
        >>> 1.0 in LessOrEqual(5)
        True

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        return value <= self._max
    def __repr__ (self) :
        """Return a string representation of the type suitable for `eval`

        >>> repr(LessOrEqual(3))
        'LessOrEqual(3)'

        @return: precise string representation
        @rtype: `str`
        """
        return "LessOrEqual(%s)" % repr(self._max)
    __pnmltype__ = "lesseq"
    def __pnmldump__ (self) :
        """Dump type to its PNML representation

        >>> LessOrEqual(4).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="lesseq">
          <object type="int">
           4
          </object>
         </type>
        </pnml>

        @return: PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    Tree.from_obj(self._max),
                    domain=self.__pnmltype__)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Build type from its PNML representation

        >>> LessOrEqual.__pnmlload__(LessOrEqual(4).__pnmldump__())
        LessOrEqual(4)

        @param tree: PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: loaded type
        @rtype: `LessOrEqual`
        """
        return cls(tree.child().to_obj())

class CrossProduct (Type) :
    """A type whose values are tuples, each component of them being in
    given types. The resulting type is the cartesian cross product of
    the compound types.

    >>> (1, 3, 5) in CrossProduct(Range(1, 10), Range(1, 10, 2), Range(1, 10))
    True
    >>> (2, 4, 6) in CrossProduct(Range(1, 10), Range(1, 10, 2), Range(1, 10))
    False
    """
    def __init__ (self, *types) :
        """Initialise the type

        >>> CrossProduct(Instance(int), Instance(float))
        CrossProduct(Instance(int), Instance(float))

        @param types: the types of each component of the allowed
            tuples
        @type types: `Type`
        """
        self._types = types
        _iterable(self, *types)
    # apidoc stop
    def __repr__ (self) :
        """Return a string representation of the type suitable for `eval`

        >>> repr(CrossProduct(Range(1, 10), Range(1, 10, 2), Range(1, 10)))
        'CrossProduct(Range(1, 10), Range(1, 10, 2), Range(1, 10))'

        @return: precise string representation
        @rtype: `str`
        """
        return "CrossProduct(%s)" % ", ".join([repr(t) for t in self._types])
    def __contains__ (self, value) :
        """Check wether a value is in the type.

        >>> (1, 3, 5) in CrossProduct(Range(1, 10), Range(1, 10, 2), Range(1, 10))
        True
        >>> (2, 4, 6) in CrossProduct(Range(1, 10), Range(1, 10, 2), Range(1, 10))
        False

        @param value: the value to check
        @type value: `object`
        @return: `True` if `value` is in the type, `False` otherwise
        @rtype: `bool`
        """
        if not isinstance(value, tuple) :
            return False
        elif len(self._types) != len(value) :
            return False
        for item, t in zip(value, self._types) :
            if not item in t :
                return False
        return True
    def __iter__ (self) :
        """A cross product is iterable if so are all its components.

        >>> list(iter(CrossProduct(Range(1, 3), Range(3, 5))))
        [(1, 3), (1, 4), (2, 3), (2, 4)]
        >>> iter(CrossProduct(Range(1, 100), tAll))
        Traceback (most recent call last):
        ...
        ValueError: iteration over non-sequence

        @return: an iterator over the values in the type
        @rtype: `generator`
        @raise ValueError: when one component is not iterable
        """
        self.__iterable__()
        return cross(self._types)
    __pnmltype__ = "crossproduct"
    def __pnmldump__ (self) :
        """Dumps type to its PNML representation

        >>> CrossProduct(Instance(int), Instance(float)).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <type domain="crossproduct">
          <type domain="instance">
           <object name="int" type="class"/>
          </type>
          <type domain="instance">
           <object name="float" type="class"/>
          </type>
         </type>
        </pnml>

        @return: PNML representation of the type
        @rtype: `snakes.pnml.Tree`
        """
        return Tree(self.__pnmltag__, None,
                    *(Tree.from_obj(t) for t in self._types),
                    **dict(domain=self.__pnmltype__))
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Build type from its PNML representation

        >>> t = CrossProduct(Instance(int), Instance(float)).__pnmldump__()
        >>> CrossProduct.__pnmlload__(t)
        CrossProduct(Instance(int), Instance(float))

        @param tree: PNML tree to load
        @type tree: `snakes.pnml.Tree`
        @return: loaded type
        @rtype: `CrossProduct`
        """
        return cls(*(child.to_obj() for child in tree.children))

tAll        = _All()
tNothing    = _Nothing()
tString     = Instance(str)
tList       = List(tAll)
tInteger    = Instance(int)
tNatural    = tInteger & GreaterOrEqual(0)
tPositive   = tInteger & Greater(0)
tFloat      = Instance(float)
tNumber     = tInteger|tFloat
tDict       = Instance(dict)
tNone       = OneOf(None)
tBoolean    = OneOf(True, False)
tTuple      = Tuple(tAll)
tPair       = Tuple(tAll, min=2, max=2)
