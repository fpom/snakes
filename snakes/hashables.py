"""This module proposes hashable version of the mutable containers
`list`, `dict` and `set`, called respectively `hlist`, `hdict` and
`hset`.

After one object has been hashed, it becomes not mutable and raises a
`ValueError` if a method which changes the object (let call a
_mutation_ such a method) is invoqued. The object can be then
un-hashed by calling `unhash` on it so that it becomes mutable again.
Notice that this may cause troubles if the object is stored in a set
or dict which uses its hashcode to locate it. Notice also that
hashable containers cannot be hashed if they contain non hashable
objects.

>>> l = hlist(range(5))
>>> l
hlist([0, 1, 2, 3, 4])
>>> _ = hash(l)
>>> l.append(5)
Traceback (most recent call last):
...
ValueError: hashed 'hlist' object is not mutable
>>> unhash(l)
>>> l.append(5)
>>> l
hlist([0, 1, 2, 3, 4, 5])

Testing if a `hlist` is in a `set`, `dict`, `hset` or `hdict` causes
its hashing. If this is not desirable, you should either compensate
with a call to `unhash`, or test if a copy is in the set:

>>> s = set()
>>> s.add(list(range(4)))
Traceback (most recent call last):
...
TypeError: ...
>>> s.add(hlist(range(4)))
>>> l = hlist(range(3))
>>> l in s
False
>>> l.append(3)
Traceback (most recent call last):
...
ValueError: hashed 'hlist' object is not mutable
>>> unhash(l)
>>> l.append(3)
>>> l[:] in s
True
>>> l.append(4)
"""

import inspect
from operator import xor
from snakes.compat import *

def unhash (obj) :
    """Make the object mutable again. This should be used with
    caution, especially if the object is stored in a dict or a set.

    >>> l = hlist(range(3))
    >>> _ = hash(l)
    >>> l.append(3)
    Traceback (most recent call last):
    ...
    ValueError: hashed 'hlist' object is not mutable
    >>> unhash(l)
    >>> l.append(3)

    @param obj: any object
    @type obj: `object`
    """
    try :
        del obj._hash
    except :
        pass

# apidoc skip
def hashable (cls) :
    """Wrap methods in a class in order to make it hashable.
    """
    classname, bases, classdict = cls.__name__, cls.__bases__, cls.__dict__
    for name, attr in classdict.items() :
        try :
            doc = inspect.getdoc(attr)
            if doc is None :
                attr.__doc__ = getattr(bases[0], name).__doc__
            else :
                attr.__doc__ = "\n".join([inspect.getdoc(getattr(bases[0],
                                                                 name)),
                                          doc])
        except :
            pass
    def __hash__ (self) :
        if not hasattr(self, "_hash") :
            self._hash = self.__hash__.HASH(self)
        return self._hash
    __hash__.HASH = classdict["__hash__"]
    __hash__.__doc__ = classdict["__hash__"].__doc__
    cls.__hash__ = __hash__
    def __mutable__ (self) :
        "Raise `ValueError` if the %s has been hashed."
        if self.hashed() :
            raise ValueError("hashed '%s' object is not mutable" % classname)
    try :
        __mutable__.__doc__ = __mutable__.__doc__ % classname
    except :
        pass
    cls.__mutable__ = __mutable__
    def hashed (self) :
        "Return 'True' if the %s has been hashed, 'False' otherwise."
        return hasattr(self, "_hash")
    try :
        hashed.__doc__ = hashed.__doc__ % classname
    except :
        pass
    cls.hashed = hashed
    def mutable (self) :
        "Return 'True' if the %s is not hashed, 'False' otherwise."
        return not self.hashed()
    try :
        mutable.__doc__ = mutable.__doc__ % classname
    except :
        pass
    cls.mutable = mutable
    return cls

class hlist (list) :
    """Hashable lists. They support all standard methods from `list`.

    >>> l = hlist(range(5))
    >>> l
    hlist([0, 1, 2, 3, 4])
    >>> l.append(5)
    >>> l
    hlist([0, 1, 2, 3, 4, 5])
    >>> _ = hash(l)
    >>> l.append(6)
    Traceback (most recent call last):
    ...
    ValueError: hashed 'hlist' object is not mutable
    >>> unhash(l)
    >>> l.append(6)
    """
    # apidoc stop
    def __add__ (self, other) :
        return self.__class__(list.__add__(self, other))
    def __delitem__ (self, item) :
        self.__mutable__()
        list.__delitem__(self, item)
    def __delslice__ (self, *l, **d) :
        self.__mutable__()
        list.__delslice__(self, *l, **d)
    def __getslice__ (self, first, last) :
        return self.__class__(list.__getslice__(self, first, last))
    def __getitem__ (self, item) :
        ret = list.__getitem__(self, item)
        if ret.__class__ is list :
            return self.__class__(ret)
        return ret
    def __hash__ (self) :
        return hash(tuple(self))
    def __iadd__ (self, other) :
        return self.__class__(list.__iadd__(self, other))
    def __imul__ (self, n) :
        return self.__class__(list.__imul__(self, n))
    def __mul__ (self, n) :
        return self.__class__(list.__mul__(self, n))
    def __repr__ (self) :
        """
        >>> repr(hlist(range(3)))
        'hlist([0, 1, 2])'
        """
        return "%s(%s)" % (self.__class__.__name__, list.__repr__(self))
    def __rmul__ (self, n) :
        return self._class__(list.__rmul__(self, n))
    def __setitem__ (self, index, item) :
        self.__mutable__()
        list.__setitem__(self, index, item)
    def __setslice__ (self, first, last, item) :
        self.__mutable__()
        list.__setslice__(self, first, last, item)
    def append (self, item) :
        self.__mutable__()
        list.append(self, item)
    def extend (self, iterable) :
        self.__mutable__()
        list.extend(self, iterable)
    def insert (self, index, item) :
        self.__mutable__()
        list.insert(self, index, item)
    def pop (self, index=-1) :
        self.__mutable__()
        return list.pop(self, index)
    def remove (self, item) :
        self.__mutable__()
        list.remove(self, item)
    def reverse (self) :
        self.__mutable__()
        list.reverse(self)
    def sort (self, cmp=None, key=None, reverse=False) :
        self.__mutable__()
        list.sort(self, cmp, key, reverse)

hlist = hashable(hlist)

class hdict (dict) :
    """Hashable dictionnaries. They support all standard methods from
    `dict`.

    >>> l = hlist(range(5))
    >>> d = hdict([(l, 0)])
    >>> d
    hdict({hlist([0, 1, 2, 3, 4]): 0})
    >>> l in d
    True
    >>> [0, 1, 2, 3, 4] in d
    Traceback (most recent call last):
    ...
    TypeError: ...
    >>> hlist([0, 1, 2, 3, 4]) in d
    True
    >>> d[hlist([0, 1, 2, 3, 4])]
    0
    >>> l.append(5)
    Traceback (most recent call last):
    ...
    ValueError: hashed 'hlist' object is not mutable
    >>> _ = hash(d)
    >>> d.pop(l)  # any mutation would produce the same error
    Traceback (most recent call last):
    ...
    ValueError: hashed 'hdict' object is not mutable
    >>> unhash(d)
    >>> d.pop(l)
    0
    """
    # apidoc stop
    def __delitem__ (self, key) :
        self.__mutable__()
        dict.__delitem__(self, key)
    def __hash__ (self) :
        """
        >>> _ = hash(hdict(a=1, b=2))
        """
        # 252756382 = hash("snakes.hashables.hlist")
        return reduce(xor, (hash(i) for i in self.items()), 252756382)
    def __repr__ (self) :
        """
        >>> repr(hdict(a=1))
        "hdict({'a': 1})"
        """
        return "%s(%s)" % (self.__class__.__name__, dict.__repr__(self))
    def __setitem__ (self, key, item) :
        self.__mutable__()
        dict.__setitem__(self, key, item)
    def clear (self) :
        self.__mutable__()
        dict.clear(self)
    def copy (self) :
        return self.__class__(dict.copy(self))
    @classmethod
    def fromkeys (_class, *args) :
        return _class(dict.fromkeys(*args))
    def pop (self, *args) :
        self.__mutable__()
        return dict.pop(self, *args)
    def popitem (self) :
        self.__mutable__()
        return dict.popitem(self)
    def setdefault (self, key, item=None) :
        self.__mutable__()
        return dict.setdefault (self, key, item)
    def update (self, other, **more) :
        self.__mutable__()
        return dict.update(self, other, **more)

hdict = hashable(hdict)

class hset (set) :
    """Hashable sets. They support all standard methods from `set`.

    >>> s = hset()
    >>> l = hlist(range(5))
    >>> s.add(l)
    >>> s
    hset([hlist([0, 1, 2, 3, 4])])
    >>> l in s
    True
    >>> [0, 1, 2, 3, 4] in s
    Traceback (most recent call last):
    ...
    TypeError: ...
    >>> hlist([0, 1, 2, 3, 4]) in s
    True
    >>> l.append(5)
    Traceback (most recent call last):
    ...
    ValueError: hashed 'hlist' object is not mutable
    >>> _ = hash(s)
    >>> s.discard(l)  # any mutation would produce the same error
    Traceback (most recent call last):
    ...
    ValueError: hashed 'hset' object is not mutable
    >>> unhash(s)
    >>> s.discard(l)
    """
    # apidoc stop
    def __and__ (self, other) :
        return self.__class__(set.__and__(self, other))
    def __hash__ (self) :
        """
        >>> _ = hash(hset([1, 2, 3]))
        >>> _ = hash(hset(range(5)) - set([0, 4]))
        """
        # 196496309 = hash("snakes.hashables.hset")
        return reduce(xor, (hash(x) for x in self), 196496309)
    def __iand__ (self, other) :
        return self.__class__(set.__iand__(self, other))
    def __ior__ (self, other) :
        return self.__class__(set.__ior__(self, other))
    def __isub__ (self, other) :
        return self.__class__(set.__isub__(self, other))
    def __ixor__ (self, other) :
        return self.__class__(set.__ixor__(self, other))
    def __or__ (self, other) :
        return self.__class__(set.__or__(self, other))
    def __rand__ (self, other) :
        return self.__class__(set.__rand__(self, other))
    def __repr__ (self) :
        """
        >>> repr(hset([1]))
        'hset([1])'
        """
        return "%s([%s])" % (self.__class__.__name__,
                             set.__repr__(self)[6:-2])
    def __ror__ (self, other) :
        return self.__class__(set.__ror__(self, other))
    def __rsub__ (self, other) :
        return self.__class__(set.__rsub__(self, other))
    def __rxor__ (self, other) :
        return self.__class__(set.__rxor__(self, other))
    def __str__ (self) :
        return self.__class__.__name__ + "(" + set.__str__(self).split("(", 1)[1]
    def __sub__ (self, other) :
        return self.__class__(set.__sub__(self, other))
    def __xor__ (self, other) :
        return self.__class__(set.__xor__(self, other))
    def add (self, item) :
        self.__mutable__()
        set.add(self, item)
    def clear (self) :
        self.__mutable__()
        set.clear(self)
    def copy (self) :
        return self.__class__(set.copy(self))
    def difference (self, other) :
        return self.__class__(set.difference(self, other))
    def difference_update (self, other) :
        self.__mutable__()
        set.difference_update(self, other)
    def discard (self, item) :
        self.__mutable__()
        set.discard(self, item)
    def intersection (self, other) :
        return self._class__(set.intersection(self, other))
    def intersection_update (self, other) :
        self.__mutable__()
        set.intersection_update(self, other)
    def pop (self) :
        self.__mutable__()
        return set.pop(self)
    def remove (self, item) :
        self.__mutable__()
        set.remove(self, item)
    def symmetric_difference (self, other) :
        self.__mutable__()
        set.symmetric_difference(self, other)
    def symmetric_difference_update (self, other) :
        self.__mutable__()
        set.symmetric_difference_update(self, other)
    def union (self, other) :
        return self.__class__(set.union(self, other))
    def update (self, other) :
        self.__mutable__()
        set.update(self, other)

hset = hashable(hset)
