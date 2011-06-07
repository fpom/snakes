"""Basic data types and functions used in SNAKES"""

import operator, inspect
from snakes.compat import *
from snakes import DomainError
from snakes.hashables import hdict
from snakes.pnml import Tree

def cross (sets) :
    """Cross-product.

    >>> list(cross([[1, 2], [3, 4, 5]]))
    [(1, 3), (1, 4), (1, 5), (2, 3), (2, 4), (2, 5)]
    >>> list(cross([[1, 2], [3, 4, 5], [6, 7, 8, 9]]))
    [(1, 3, 6), (1, 3, 7), (1, 3, 8), (1, 3, 9), (1, 4, 6), (1, 4, 7),
     (1, 4, 8), (1, 4, 9), (1, 5, 6), (1, 5, 7), (1, 5, 8), (1, 5, 9),
     (2, 3, 6), (2, 3, 7), (2, 3, 8), (2, 3, 9), (2, 4, 6), (2, 4, 7),
     (2, 4, 8), (2, 4, 9), (2, 5, 6), (2, 5, 7), (2, 5, 8), (2, 5, 9)]
    >>> list(cross([[], [1]]))
    []

    @param sets: the sets of values to use
    @type sets: C{iterable(iterable(object))}
    @return: the C{list} of obtained tuples (lists are used to allow
      unhashable objects)
    @rtype: C{generator(tuple(object))}
    """
    if len(sets) == 0 :
        pass
    elif len(sets) == 1 :
        for item in sets[0] :
            yield (item,)
    else :
        for item in sets[0] :
            for others in cross(sets[1:]) :
                yield (item,) + others

def iterate (value) :
    """Like Python's builtin C{iter} but consider strings as atomic.

    >>> list(iter([1, 2, 3]))
    [1, 2, 3]
    >>> list(iterate([1, 2, 3]))
    [1, 2, 3]
    >>> list(iter('foo'))
    ['f', 'o', 'o']
    >>> list(iterate('foo'))
    ['foo']

    @param value: any object
    @type value: C{object}
    @return: an iterator on the elements of C{value} if is is iterable
        and is not string, an iterator on the sole C{value} otherwise
    @rtype: C{generator}
    """
    if isinstance(value, str) :
        return iter([value])
    else :
        try :
            return iter(value)
        except TypeError :
            return iter([value])

class WordSet (set) :
    """A set of words being able to generate fresh words."""
    def fresh (self, add=False, min=1, allowed="abcdefghijklmnopqrstuvwxyz",
               base="") :
        """Create a fresh word (ie, which is not in the set).

        >>> w = WordSet(['foo', 'bar'])
        >>> list(sorted(w))
        ['bar', 'foo']
        >>> w.fresh(True, 3)
        'aaa'
        >>> list(sorted(w))
        ['aaa', 'bar', 'foo']
        >>> w.fresh(True, 3)
        'baa'
        >>> list(sorted(w))
        ['aaa', 'baa', 'bar', 'foo']

        @param add: add the created word to the set if C{add=True}
        @type add: C{bool}
        @param min: minimal length of the new word
        @type min: C{int}
        @param allowed: characters allowed in the new word
        @type allowed: C{str}
        """
        if base :
            result = [base] + [allowed[0]] * max(0, min - len(base))
            if base in self :
                result.append(allowed[0])
                pos = len(result) - 1
            elif len(base) < min :
                pos = 1
            else :
                pos = 0
        else :
            result = [allowed[0]] * min
            pos = 0
        while "".join(result) in self :
            for c in allowed :
                try :
                    result[pos] = c
                except IndexError :
                    result.append(c)
                if "".join(result) not in self :
                    break
            pos += 1
        if add :
            self.add("".join(result))
        return "".join(result)

class MultiSet (hdict) :
    """Set with repetitions, ie, function from values to integers.

    MultiSets support various operations, in particular: addition
    (C{+}), substraction (C{-}), multiplication by a non negative
    integer (C{*k}), comparisons (C{<}, C{>}, etc.), length (C{len})"""
    def __init__ (self, values=[]) :
        """Initialise the multiset, adding values to it.

        >>> MultiSet([1, 2, 3, 1, 2])
        MultiSet([...])
        >>> MultiSet()
        MultiSet([])

        @param values: a single value or an iterable object holding
          values (strings are not iterated)
        @type values: any atomic object (C{str} included) or an
          iterable object
        """
        self.add(values)
    def copy (self) :
        """Copy a C{MultiSet}

        >>> MultiSet([1, 2, 3, 1, 2]).copy()
        MultiSet([...])

        @return: a copy of the multiset
        @rtype: C{MultiSet}
        """
        result = MultiSet()
        result.update(self)
        return result
    __pnmltag__ = "multiset"
    def __pnmldump__ (self) :
        """
        >>> MultiSet([1, 2, 3, 4, 1, 2]).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <multiset>
          <item>
           <value>
            <object type="int">
            ...
            </object>
           </value>
           <multiplicity>
           ...
           </multiplicity>
          </item>
          <item>
           <value>
            <object type="int">
            ...
            </object>
           </value>
           <multiplicity>
           ...
           </multiplicity>
          </item>
          <item>
           <value>
            <object type="int">
            ...
            </object>
           </value>
           <multiplicity>
           ...
           </multiplicity>
          </item>
          <item>
           <value>
            <object type="int">
            ...
            </object>
           </value>
           <multiplicity>
           ...
           </multiplicity>
          </item>
         </multiset>
        </pnml>
        """
        nodes = []
        for value in hdict.__iter__(self) :
            nodes.append(Tree("item", None,
                              Tree("value", None, Tree.from_obj(value)),
                              Tree("multiplicity", str(self[value]))))
        return Tree(self.__pnmltag__, None, *nodes)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Load a multiset from its PNML representation

        >>> t = MultiSet([1, 2, 3, 4, 1, 2]).__pnmldump__()
        >>> MultiSet.__pnmlload__(t)
        MultiSet([...])
        """
        result = cls()
        for item in tree :
            times = int(item.child("multiplicity").data)
            value = item.child("value").child().to_obj()
            result._add(value, times)
        return result
    def _add (self, value, times=1) :
        """Add a single value C{times} times.

        @param value: the value to add
        @type value: any object
        @param times: the number of times that C{value} has to be
          added
        @type times: non negative C{int}
        """
        if times < 0 :
            raise ValueError("negative values are forbidden")
        try :
            self[value] += times
        except KeyError :
            self[value] = times
    def add (self, values, times=1) :
        """Add values to the multiset.

        >>> m = MultiSet()
        >>> m.add([1, 2, 2, 3], 2)
        >>> list(sorted(m.items()))
        [1, 1, 2, 2, 2, 2, 3, 3]
        >>> m.add(5, 3)
        >>> list(sorted(m.items()))
        [1, 1, 2, 2, 2, 2, 3, 3, 5, 5, 5]

        @param values: the values to add or a single value to add
        @type values: any atomic object (C{str} included) or an
          iterable object
        @param times: the number of times each value should be added
        @type times: non negative C{int}"""
        self.__mutable__()
        for value in iterate(values) :
            self._add(value, times)
    def _remove (self, value, times=1) :
        """Remove a single value C{times} times.

        @param value: the value to remove
        @type value: any object
        @param times: the number of times that C{value} has to be
          removed
        @type times: non negative C{int}
        """
        if times < 0 :
            raise ValueError("negative values are forbidden")
        if times > self.get(value, 0) :
            raise ValueError("not enough occurrences")
        self[value] -= times
        if self[value] == 0 :
            del self[value]
    def remove (self, values, times=1) :
        """Remove values to the multiset.

        >>> m = MultiSet()
        >>> m.add([1, 2, 2, 3], 2)
        >>> list(sorted(m.items()))
        [1, 1, 2, 2, 2, 2, 3, 3]
        >>> m.remove(2, 3)
        >>> list(sorted(m.items()))
        [1, 1, 2, 3, 3]
        >>> m.remove([1, 3], 2)
        >>> list(sorted(m.items()))
        [2]

        @param values: the values to remove or a single value to remove
        @type values: any atomic object (C{str} included) or an
          iterable object
        @param times: the number of times each value should be removed
        @type times: non negative C{int}"""
        self.__mutable__()
        for value in iterate(values) :
            self._remove(value, times)
    def __call__ (self, value) :
        """Number of occurrences of C{value}.

        >>> m = MultiSet([1, 1, 2, 3, 3, 3])
        >>> m(1), m(2), m(3), m(4)
        (2, 1, 3, 0)

        @param value: the value the count
        @type value: C{object}
        @rtype: C{int}
        """
        return self.get(value, 0)
    def __iter__ (self) :
        """Iterate over the values (with repetitions).

        Use C{MultiSet.keys} to ignore repetitions.

        >>> list(sorted(iter(MultiSet([1, 2, 3, 1, 2]))))
        [1, 1, 2, 2, 3]

        @return: an iterator on the elements
        @rtype: C{iterator}"""
        for value in dict.__iter__(self) :
            for count in range(self[value]) :
                yield value
    def items (self) :
        """
        Return the list of items with repetitions. The list without
        repetitions can be retrieved with the C{key} method.

        >>> m = MultiSet([1, 2, 2, 3])
        >>> list(sorted(m.items()))
        [1, 2, 2, 3]
        >>> list(sorted(m.keys()))
        [1, 2, 3]

        @return: list of items with repetitions
        @rtype: C{list}"""
        return list(iter(self))
    def __str__ (self) :
        """Return a simple string representation of the multiset

        >>> str(MultiSet([1, 2, 2, 3]))
        '{...}'

        @return: simple string representation of the multiset
        @rtype: C{str}
        """
        return "{%s}" % ", ".join(repr(x) for x in self)
    def __repr__ (self) :
        """Return a string representation of the multiset that is
        suitable for C{eval}

        >>> repr(MultiSet([1, 2, 2, 3]))
        'MultiSet([...])'

        @return: precise string representation of the multiset
        @rtype: C{str}
        """
        return "MultiSet([%s])" % ", ".join(repr(x) for x in self)
    def __len__ (self) :
        """Return the number of elements, including repetitions.

        >>> len(MultiSet([1, 2] * 3))
        6

        @rtype: C{int}
        """
        if self.size() == 0 :
            return 0
        else :
            return reduce(operator.add, self.values())
    def size (self) :
        """Return the number of elements, excluding repetitions.

        >>> MultiSet([1, 2] * 3).size()
        2

        @rtype: C{int}
        """
        return dict.__len__(self)
    def __add__ (self, other) :
        """Adds two multisets.

        >>> MultiSet([1, 2, 3]) + MultiSet([2, 3, 4])
        MultiSet([...])

        @param other: the multiset to add
        @type other: C{MultiSet}
        @rtype: C{MultiSet}
        """
        result = self.copy()
        for value, times in dict.items(other) :
            result._add(value, times)
        return result
    def __sub__ (self, other) :
        """Substract two multisets.

        >>> MultiSet([1, 2, 3]) - MultiSet([2, 3])
        MultiSet([1])
        >>> MultiSet([1, 2, 3]) - MultiSet([2, 3, 4])
        Traceback (most recent call last):
        ...
        ValueError: not enough occurrences

        @param other: the multiset to substract
        @type other: C{MultiSet}
        @rtype: C{MultiSet}
        """
        result = self.copy()
        for value, times in dict.items(other) :
            result._remove(value, times)
        return result
    def __mul__ (self, other) :
        """Multiplication by a non-negative integer.

        >>> MultiSet([1, 2]) * 3
        MultiSet([...])

        @param other: the integer to multiply
        @type other: non-negative C{int}
        @rtype: C{MultiSet}
        """
        if other < 0 :
            raise ValueError("negative values are forbidden")
        elif other == 0 :
            return MultiSet()
        else :
            result = self.copy()
            for value in self.keys() :
                result[value] *= other
            return result
    __hash__ = hdict.__hash__
    def __eq__ (self, other) :
        """Test for equality.

        >>> MultiSet([1, 2, 3]*2) == MultiSet([1, 2, 3]*2)
        True
        >>> MultiSet([1, 2, 3]) == MultiSet([1, 2, 3, 3])
        False

        @param other: the multiset to compare with
        @type other: C{MultiSet}
        @rtype: C{bool}
        """
        if len(self) != len(other) :
            return False
        else :
            for val in self :
                try :
                    if self[val] != other[val] :
                        return False
                except (KeyError, TypeError) :
                    return False
        return True
    def __ne__ (self, other) :
        """Test for difference.

        >>> MultiSet([1, 2, 3]*2) != MultiSet([1, 2, 3]*2)
        False
        >>> MultiSet([1, 2, 3]) != MultiSet([1, 2, 3, 3])
        True

        @param other: the multiset to compare with
        @type other: C{MultiSet}
        @rtype: C{bool}
        """
        return not(self == other)
    def __lt__ (self, other) :
        """Test for strict inclusion.

        >>> MultiSet([1, 2, 3]) < MultiSet([1, 2, 3, 4])
        True
        >>> MultiSet([1, 2, 3]) < MultiSet([1, 2, 3, 3])
        True
        >>> MultiSet([1, 2, 3]) < MultiSet([1, 2, 3])
        False
        >>> MultiSet([1, 2, 3]) < MultiSet([1, 2])
        False
        >>> MultiSet([1, 2, 2]) < MultiSet([1, 2, 3, 4])
        False

        @param other: the multiset to compare with
        @type other: C{MultiSet}
        @rtype: C{bool}
        """
        if not set(self.keys()) <= set(other.keys()) :
            return False
        result = False
        for value, times in dict.items(self) :
            count = other(value)
            if times > count :
                return False
            elif times < count :
                result = True
        return result or (dict.__len__(self) < dict.__len__(other))
    def __le__ (self, other) :
        """Test for inclusion inclusion.

        >>> MultiSet([1, 2, 3]) <= MultiSet([1, 2, 3, 4])
        True
        >>> MultiSet([1, 2, 3]) <= MultiSet([1, 2, 3, 3])
        True
        >>> MultiSet([1, 2, 3]) <= MultiSet([1, 2, 3])
        True
        >>> MultiSet([1, 2, 3]) <= MultiSet([1, 2])
        False
        >>> MultiSet([1, 2, 2]) <= MultiSet([1, 2, 3, 4])
        False

        @param other: the multiset to compare with
        @type other: C{MultiSet}
        @rtype: C{bool}
        """
        if not set(self.keys()) <= set(other.keys()) :
            return False
        for value, times in dict.items(self) :
            count = other(value)
            if times > count :
                return False
        return True
    def __gt__ (self, other) :
        """Test for strict inclusion.

        >>> MultiSet([1, 2, 3, 4]) > MultiSet([1, 2, 3])
        True
        >>> MultiSet([1, 2, 3, 3]) > MultiSet([1, 2, 3])
        True
        >>> MultiSet([1, 2, 3]) > MultiSet([1, 2, 3])
        False
        >>> MultiSet([1, 2]) > MultiSet([1, 2, 3])
        False
        >>> MultiSet([1, 2, 3, 4]) > MultiSet([1, 2, 2])
        False

        @param other: the multiset to compare with
        @type other: C{MultiSet}
        @rtype: C{bool}
        """
        return other.__lt__(self)
    def __ge__ (self, other) :
        """Test for inclusion.

        >>> MultiSet([1, 2, 3, 4]) >= MultiSet([1, 2, 3])
        True
        >>> MultiSet([1, 2, 3, 3]) >= MultiSet([1, 2, 3])
        True
        >>> MultiSet([1, 2, 3]) >= MultiSet([1, 2, 3])
        True
        >>> MultiSet([1, 2]) >= MultiSet([1, 2, 3])
        False
        >>> MultiSet([1, 2, 3, 4]) >= MultiSet([1, 2, 2])
        False

        @param other: the multiset to compare with
        @type other: C{MultiSet}
        @rtype: C{bool}
        """
        return other.__le__(self)
    def domain (self) :
        """Return the domain of the multiset

        >>> list(sorted((MultiSet([1, 2, 3, 4]) + MultiSet([1, 2, 3])).domain()))
        [1, 2, 3, 4]

        @return: the set of values in the domain
        @rtype: C{set}
        """
        return set(self.keys())

class Substitution (object) :
    """Map names to values or names, equals the identity where not defined.

    Substitutions support the C{+} operation (union with consistency
    check between the two operands) and the C{*} operation which is
    the composition of functions (C{(f*g)(x)} is C{f(g(x))}).

    Several methods (eg, C{image}) return lists instead of sets, this
    avoids the restriction of having only hashable values in a
    substitution image.
    """
    def __init__ (self, *largs, **dargs) :
        """Initialise using a dictionnary as a mapping.

        The expected arguments are any ones acceptables for
        initializing a dictionnary.

        >>> Substitution()
        Substitution()
        >>> Substitution(x=1, y=2)
        Substitution(...)
        >>> Substitution([('x', 1), ('y', 2)])
        Substitution(...)
        >>> Substitution({'x': 1, 'y': 2})
        Substitution(...)
        """
        self._dict = dict(*largs, **dargs)
    def __hash__ (self) :
        """
        >>> hash(Substitution(x=1, y=2)) == hash(Substitution(y=2, x=1))
        True
        """
        # 153913524 = hash('snakes.data.Substitution')
        return reduce(operator.xor,
                      (hash(i) for i in self._dict.items()),
                      153913524)
    def __eq__ (self, other) :
        """
        >>> Substitution(x=1, y=2) == Substitution(y=2, x=1)
        True
        >>> Substitution(x=1, y=2) == Substitution(y=1, x=1)
        False
        """
        try :
            return self._dict == other._dict
        except :
            return False
    def __ne__ (self, other) :
        """
        >>> Substitution(x=1, y=2) != Substitution(y=2, x=1)
        False
        >>> Substitution(x=1, y=2) != Substitution(y=1, x=1)
        True
        """
        return not self.__eq__(other)
    __pnmltag__ = "substitution"
    def __pnmldump__ (self) :
        """Dumps a substitution to a PNML tree

        >>> Substitution(x=1, y=2).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <substitution>
          <item>
           <name>
           ...
           </name>
           <value>
            <object type="int">
            ...
            </object>
           </value>
          </item>
          <item>
           <name>
           ...
           </name>
           <value>
            <object type="int">
            ...
            </object>
           </value>
          </item>
         </substitution>
        </pnml>

        @return: PNML representation
        @rtype: C{snakes.pnml.Tree}
        """
        nodes = []
        for name, value in self._dict.items() :
            nodes.append(Tree("item", None,
                              Tree("name", name),
                              Tree("value", None,
                                   Tree.from_obj(value))))
        return Tree(self.__pnmltag__, None, *nodes)
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Load a substitution from its PNML representation

        >>> t = Substitution(x=1, y=2).__pnmldump__()
        >>> Substitution.__pnmlload__(t)
        Substitution(...)

        @param tree: the PNML tree to load
        @type tree: C{snakes.pnml.Tree}
        @return: the substitution loaded
        @rtype: C{Substitution}
        """
        result = cls()
        for item in tree :
            name = item.child("name").data
            value = item.child("value").child().to_obj()
            result._dict[name] = value
        return result
    def items (self) :
        """Return the list of pairs (name, value).

        >>> Substitution(x=1, y=2).items()
        [('...', ...), ('...', ...)]

        @return: a list of pairs (name, value) for each mapped name
        @rtype: C{list}
        """
        return list(self._dict.items())
    def domain (self) :
        """Return the set of mapped names.

        >>> list(sorted(Substitution(x=1, y=2).domain()))
        ['x', 'y']

        @return: the set of mapped names
        @rtype: C{set}
        """
        return set(self._dict.keys())
    def image (self) :
        """Return the set of values associated to the names.

        >>> list(sorted(Substitution(x=1, y=2).image()))
        [1, 2]

        @return: the set of values associated to names
        @rtype: C{set}
        """
        return set(self._dict.values())
    def __contains__ (self, name) :
        """Test if a name is mapped.

        >>> 'x' in Substitution(x=1, y=2)
        True
        >>> 'z' in Substitution(x=1, y=2)
        False

        @param name: the name to test
        @type name: C{str} (usually)
        @return: a Boolean indicating whether this name is in the
          domain or not
        @rtype: C{bool}
        """
        return name in self._dict
    def __iter__ (self) :
        """Iterate over the mapped names.

        >>> list(sorted(iter(Substitution(x=1, y=2))))
        ['x', 'y']

        @return: an iterator over the domain of the substitution
        @rtype: C{generator}
        """
        return iter(self._dict)
    def __str__ (self) :
        """Return a compact string representation.

        >>> str(Substitution(x=1, y=2))
        '{... -> ..., ... -> ...}'

        @return: a simple string representation
        @rtype: C{str}
        """
        return "{%s}" % ", ".join(["%s -> %r" % (str(var), val)
                                   for var, val in self.items()])
    def __repr__ (self) :
        """Return a string representation suitable for C{eval}.

        >>> repr(Substitution(x=1, y=2))
        'Substitution(...)'

        @return: a precise string representation
        @rtype: C{str}
        """
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join(("%s=%s" % (str(var), repr(val))
                                      for var, val in self.items())))
    def dict (self) :
        """Return the mapping as a dictionnary.

        >>> Substitution(x=1, y=2).dict()
        {'...': ..., '...': ...}

        @return: a dictionnary that does the same mapping as the
          substitution
        @rtype: C{dict}
        """
        return self._dict.copy()
    def copy (self) :
        """Copy the mapping.

        >>> Substitution(x=1, y=2).copy()
        Substitution(...)

        @return: a copy of the substitution
        @rtype: C{Substitution}
        """
        return Substitution(self.dict())
    def __setitem__ (self, var, value) :
        """Assign an entry to the substitution

        >>> s = Substitution()
        >>> s['x'] = 42
        >>> s
        Substitution(x=42)

        @param var: the name of the variable
        @type var: C{str}
        @param value: the value to which C{var} is bound
        @type value: C{object}
        """
        self._dict[var] = value
    def __getitem__ (self, var) :
        """Return the mapped value.

        Fails with C{DomainError} if C{var} is not mapped.

        >>> s = Substitution(x=1, y=2)
        >>> s['x']
        1
        >>> try : s['z']
        ... except DomainError : print(sys.exc_info()[1])
        unbound variable 'z'

        @param var: the name of the variable
        @type var: C{str} (usually)
        @return: the value that C{var} maps to
        @rtype: C{object}
        @raise DomainError: if C{var} does not belong to the domain
        """
        try :
            return self._dict[var]
        except KeyError :
            raise DomainError("unbound variable '%s'" % var)
    def __call__ (self, var) :
        """Return the mapped value.

        Never fails but return C{var} if it is not mapped.

        >>> s = Substitution(x=1, y=2)
        >>> s('x')
        1
        >>> s('z')
        'z'

        @param var: the name of the variable
        @type var: C{str} (usually)
        @return: the value that C{var} maps to or C{var} itself if it
          does not belong to the domain
        @rtype: C{object}
        """
        try :
            return self._dict[var]
        except KeyError :
            return var
    def __add__ (self, other) :
        """Add two substitution.

        Fails with C{DomainError} if the two substitutions map a same
        name to different values.

        >>> s = Substitution(x=1, y=2) + Substitution(y=2, z=3)
        >>> s('x'), s('y'), s('z')
        (1, 2, 3)
        >>> try : Substitution(x=1, y=2) + Substitution(y=4, z=3)
        ... except DomainError : print(sys.exc_info()[1])
        conflict on 'y'

        @param other: another substitution
        @type other: C{Substitution}
        @return: the union of the substitutions
        @rtype: C{Substitution}
        @raise DomainError: when one name is mapped to distinct values
        """
        for var in self :
            if var in other and (self[var] != other[var]) :
                raise DomainError("conflict on '%s'" % var)
        s = self.__class__(self.dict())
        s._dict.update(other.dict())
        return s
    def __mul__ (self, other) :
        """Compose two substitutions.

        The composition of f and g is such that (f*g)(x) = f(g(x)).

        >>> f = Substitution(a=1, d=3, y=5)
        >>> g = Substitution(b='d', c=2, e=4, y=6)
        >>> h = f*g
        >>> h('a'), h('b'), h('c'), h('d'), h('e'), h('y'), h('x')
        (1, 3, 2, 3, 4, 6, 'x')

        @param other: another substitution
        @type other: C{Substitution}
        @return: the composition of the substitutions
        @rtype: C{Substitution}
        """
        res = self.copy()
        for var in other :
            res._dict[var] = self(other(var))
        return res

class Symbol (object) :
    """A symbol that may be used as a constant
    """
    def __init__ (self, name, export=True) :
        """
        If C{export} is C{True}, the created symbol is exported under
        its name. If C{export} is C{False}, no export is made.
        Finally, if C{export} is a string, it specifies the name of
        the exported symbol.

        @param name: the name (or value of the symbol)
        @type name: C{str}
        @param export: the name under which the symbol is exported
        @type export: C{str} or C{bool} or C{None}

        >>> Symbol('foo')
        Symbol('foo')
        >>> foo
        Symbol('foo')
        >>> Symbol('egg', 'spam')
        Symbol('egg', 'spam')
        >>> spam
        Symbol('egg', 'spam')
        >>> Symbol('bar', False)
        Symbol('bar', False)
        >>> bar
        Traceback (most recent call last):
         ...
        NameError: ...

        """
        self.name = name
        if export is True :
            export = name
        self._export = export
        if export :
            inspect.stack()[1][0].f_globals[export] = self
    __pnmltag__ = "symbol"
    def __pnmldump__ (self) :
        """
        >>> Symbol('egg', 'spam').__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <symbol name="egg">
          <object type="str">
           spam
          </object>
         </symbol>
        </pnml>
        >>> Symbol('foo').__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <symbol name="foo"/>
        </pnml>
        >>> Symbol('bar', False).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <symbol name="bar">
          <object type="bool">
           False
          </object>
         </symbol>
        </pnml>
        """
        if self.name == self._export :
            children = []
        else :
            children = [Tree.from_obj(self._export)]
        return Tree(self.__pnmltag__, None, *children, **dict(name=self.name))
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> Symbol.__pnmlload__(Symbol('foo', 'bar').__pnmldump__())
        Symbol('foo', 'bar')
        >>> Symbol.__pnmlload__(Symbol('foo').__pnmldump__())
        Symbol('foo')
        >>> Symbol.__pnmlload__(Symbol('foo', False).__pnmldump__())
        Symbol('foo', False)
        """
        name = tree["name"]
        try :
            export = tree.child().to_obj()
        except :
            export = name
        return cls(name, export)
    def __eq__ (self, other) :
        """
        >>> Symbol('foo', 'bar') == Symbol('foo')
        True
        >>> Symbol('egg') == Symbol('spam')
        False
        """
        try :
            return (self.__class__.__name__ == other.__class__.__name__
                    and self.name == other.name)
        except AttributeError :
            return False
    def __ne__ (self, other) :
        """
        >>> Symbol('foo', 'bar') != Symbol('foo')
        False
        >>> Symbol('egg') != Symbol('spam')
        True
        """
        return not (self == other)
    def __hash__ (self) :
        """
        >>> hash(Symbol('foo', 'bar')) == hash(Symbol('foo'))
        True
        """
        return hash((self.__class__.__name__, self.name))
    def __str__ (self) :
        """
        >>> str(Symbol('foo'))
        'foo'
        """
        return self.name
    def __repr__ (self) :
        """
        >>> Symbol('foo')
        Symbol('foo')
        >>> Symbol('egg', 'spam')
        Symbol('egg', 'spam')
        >>> Symbol('bar', False)
        Symbol('bar', False)
        """
        if self._export == self.name :
            return "%s(%r)" % (self.__class__.__name__, self.name)
        else :
            return "%s(%r, %r)" % (self.__class__.__name__, self.name,
                                   self._export)
