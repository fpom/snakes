class Nonce (object) :
    def __init__ (self, agent) :
        self._agent = agent
    def __eq__ (self, other) :
        try :
            return self._agent == other._agent
        except :
            return False
    def __ne__ (self, other) :
        return not self.__eq__(other)
    def __str__ (self) :
        return self.__repr__()
    def __repr__ (self) :
        return "Nonce(%s)" % self._agent

def _cross (sets) :
    if len(sets) == 0 :
        pass
    elif len(sets) == 1 :
        for item in sets[0] :
            yield (item,)
    else :
        for item in sets[0] :
            for others in _cross(sets[1:]) :
                yield (item,) + others


class Spy (object) :
    keywords = set(["crypt", "pub", "priv", "secret", "hash"])
    def __init__ (self, *types) :
        """
        >>> s = Spy(str, int, (str, int, (float, object)))
        >>> s
        <Spy>
        >>> s._subtypes == set([str, int, float, object,
        ...                     (float, object),
        ...                     (str, int, (float, object))])
        True
        """
        self._types = set(types)
        self._subtypes = set()
        todo = set(self._types)
        while len(todo) > 0 :
            t = todo.pop()
            self._subtypes.add(t)
            if isinstance(t, tuple) :
                todo.update(t)
    def __str__ (self) :
        """
        >>> str(Spy(str, int))
        '<Spy>'
        """
        return "<%s>" % self.__class__.__name__
    def __repr__ (self) :
        """
        >>> str(Spy(str, int))
        '<Spy>'
        """
        return self.__str__()
    def __eq__ (self, other) :
        """
        >>> Spy(str, int) == Spy(int, str)
        True
        >>> Spy(str, int) == Spy(int, str, float)
        False
        """
        return self._types == other._types
    def __ne__ (self, other) :
        """
        >>> Spy(str, int) != Spy(int, str, float)
        True
        >>> Spy(str, int) != Spy(int, str)
        False
        """
        return not self.__eq__(other)
    def __hash__ (self) :
        """
        >>> hash(Spy(str, int)) == hash(Spy(int, str))
        True
        >>> hash(Spy(str, int)) == hash(Spy(int, str, float))
        False
        """
        return hash(tuple(sorted(self._types)))
    @classmethod
    def get_type (cls, obj) :
        """
        >>> Spy().get_type(('hello', ('foo', 4), 5))
        (<type 'str'>, (<type 'str'>, <type 'int'>), <type 'int'>)
        """
        t = type(obj)
        if t is tuple :
            if len(obj) > 0 and obj[0] in cls.keywords :
                return (obj[0],) + tuple(cls.get_type(o) for o in obj[1:])
            else :
                return tuple(cls.get_type(o) for o in obj)
        else :
            return t
    @classmethod
    def match (cls, obj, pattern) :
        """
        >>> Spy.match(('hello', 42, (1, 2, 3.4)), (str, int, (1, 2, float)))
        True
        >>> Spy.match(('hello', 42, (1, 2, 3.4)), ('hello', int, (1, 2, float)))
        True
        >>> Spy.match(('hello', 42, (1, 2, 3)), (str, int, (1, 2, float)))
        False
        >>> Spy.match(('hello', 42, (1, 2, 3, 4)), (str, int, (1, 2, float)))
        False
        >>> Spy.match(('hello', 42, (1, 2, 3.4)), ('foo', int, (1, 2, float)))
        False
        """
        if type(obj) == tuple == type(pattern) :
            if len(obj) != len(pattern) :
                return False
            for o, p in zip(obj, pattern) :
                if not cls.match(o, p) :
                    return False
            return True
        elif type(pattern) is type :
            return isinstance(obj, pattern)
        else :
            return obj == pattern
    def message (self, obj) :
        """
        >>> Spy(str, int).message('hello')
        True
        >>> Spy(str, int).message(42)
        True
        >>> Spy(str, int).message((1, 2))
        False
        >>> Spy(str, int).message(3.14)
        False
        """
        return self.get_type(obj) in self._types
    def fragment (self, obj) :
        """
        >>> s = Spy(str, int, (str, int, (float, list)))
        >>> s.fragment('hello')
        True
        >>> s.fragment(3.14)
        True
        >>> s.fragment((3.14, []))
        True
        >>> s.fragment(('hello', 1, (3.14, [])))
        True
        >>> s.fragment((1, 2))
        False
        >>> s.fragment({})
        False
        """
        return self.get_type(obj) in self._subtypes
    def can_decrypt (self, message, knowledge) :
        try :
            if message[0] != "crypt" :
                return False
            key = message[1]
            if key[0] == "pub" :
                return ("priv", key[1]) in knowledge
            elif key[0] == "priv" :
                return ("pub", key[1]) in knowledge
            elif key[0] == "secret" :
                return key in knowledge
        except :
            pass
        return False
    def can_decompose (self, message) :
        try :
            if not isinstance(message, tuple) :
                return False
            elif message[0] not in self.keywords :
                return True
        except :
            pass
        return False
    def learn (self, msg, knowledge) :
        """
        >>> s = Spy((int, int, str), (int, int, (str, str)))
        >>> k = set()
        >>> k = s.learn((1, 2, 'hello'), k)
        >>> for m in sorted(k) :
        ...     print m
        1
        2
        hello
        (1, 1, 'hello')
        (1, 1, ('hash', 'hello'))
        (1, 1, ('hello', 'hello'))
        (1, 2, 'hello')
        (1, 2, ('hash', 'hello'))
        (1, 2, ('hello', 'hello'))
        (2, 1, 'hello')
        (2, 1, ('hash', 'hello'))
        (2, 1, ('hello', 'hello'))
        (2, 2, 'hello')
        (2, 2, ('hash', 'hello'))
        (2, 2, ('hello', 'hello'))
        ('hash', 'hello')
        ('hello', 'hello')
        >>> k = s.learn((2, 3, ('hello', 'world')), k)
        >>> for m in sorted(k) :
        ...     print m
        1
        2
        3
        hello
        world
        (1, 1, 'hello')
        (1, 1, 'world')
        (1, 1, ('hash', 'hello'))
        (1, 1, ('hash', 'world'))
        (1, 1, ('hello', 'hello'))
        (1, 1, ('hello', 'world'))
        (1, 1, ('world', 'hello'))
        (1, 1, ('world', 'world'))
        (1, 2, 'hello')
        (1, 2, 'world')
        (1, 2, ('hash', 'hello'))
        (1, 2, ('hash', 'world'))
        (1, 2, ('hello', 'hello'))
        (1, 2, ('hello', 'world'))
        (1, 2, ('world', 'hello'))
        (1, 2, ('world', 'world'))
        (1, 3, 'hello')
        (1, 3, 'world')
        (1, 3, ('hash', 'hello'))
        (1, 3, ('hash', 'world'))
        (1, 3, ('hello', 'hello'))
        (1, 3, ('hello', 'world'))
        (1, 3, ('world', 'hello'))
        (1, 3, ('world', 'world'))
        (2, 1, 'hello')
        (2, 1, 'world')
        (2, 1, ('hash', 'hello'))
        (2, 1, ('hash', 'world'))
        (2, 1, ('hello', 'hello'))
        (2, 1, ('hello', 'world'))
        (2, 1, ('world', 'hello'))
        (2, 1, ('world', 'world'))
        (2, 2, 'hello')
        (2, 2, 'world')
        (2, 2, ('hash', 'hello'))
        (2, 2, ('hash', 'world'))
        (2, 2, ('hello', 'hello'))
        (2, 2, ('hello', 'world'))
        (2, 2, ('world', 'hello'))
        (2, 2, ('world', 'world'))
        (2, 3, 'hello')
        (2, 3, 'world')
        (2, 3, ('hash', 'hello'))
        (2, 3, ('hash', 'world'))
        (2, 3, ('hello', 'hello'))
        (2, 3, ('hello', 'world'))
        (2, 3, ('world', 'hello'))
        (2, 3, ('world', 'world'))
        (3, 1, 'hello')
        (3, 1, 'world')
        (3, 1, ('hash', 'hello'))
        (3, 1, ('hash', 'world'))
        (3, 1, ('hello', 'hello'))
        (3, 1, ('hello', 'world'))
        (3, 1, ('world', 'hello'))
        (3, 1, ('world', 'world'))
        (3, 2, 'hello')
        (3, 2, 'world')
        (3, 2, ('hash', 'hello'))
        (3, 2, ('hash', 'world'))
        (3, 2, ('hello', 'hello'))
        (3, 2, ('hello', 'world'))
        (3, 2, ('world', 'hello'))
        (3, 2, ('world', 'world'))
        (3, 3, 'hello')
        (3, 3, 'world')
        (3, 3, ('hash', 'hello'))
        (3, 3, ('hash', 'world'))
        (3, 3, ('hello', 'hello'))
        (3, 3, ('hello', 'world'))
        (3, 3, ('world', 'hello'))
        (3, 3, ('world', 'world'))
        ('hash', 'hello')
        ('hash', 'world')
        ('hello', 'hello')
        ('hello', 'world')
        ('world', 'hello')
        ('world', 'world')

        >>> s = Spy(('crypt', ('pub', int), str))
        >>> pub, priv = ('pub', 1), ('priv', 1)
        >>> k = set([pub])
        >>> k = s.learn(('crypt', priv, 'hello'), k)
        >>> 'hello' in k
        True
        >>> k = s.learn(('crypt', pub, 'secret message'), k)
        >>> 'secret message' in k
        False
        >>> k.add(priv)
        >>> k = s.learn(('crypt', pub, 'secret message'), k)
        >>> 'secret message' in k
        True
        """
        k = set(knowledge)
        # learn from new message
        # add new message to knowledge
        k.add(msg)
        # hash new message if useful
        h = ("hash", msg)
        if self.fragment(h) :
            k.add(h)
        # try to decrypt new message
        if self.can_decrypt(msg, k) :
            for m in msg[2:] :
                if m not in k :
                    k.update(self.learn(m, k))
        # try to decompose new message
        elif self.can_decompose(msg) :
            for m in msg :
                if m not in k :
                    k.update(self.learn(m, k))
        self._learn_(msg, k)
        # compose new messages from fragments
        for sub in (s for s in sorted(self._subtypes, key=self._size)
                    if type(s) is tuple) :
            sets = []
            for t in sub :
                sets.append([x for x in k|self.keywords if self.match(x, t)])
            k.update(_cross(sets))
        return k
    @classmethod
    def _size (cls, obj) :
        if isinstance(obj, tuple) :
            return (len(obj),) + tuple(cls._size(o) for o in obj)
        else :
            return 1
    def _learn_ (self, m, k) :
        for attr in (a for a in dir(self) if a.startswith("learn_")) :
            getattr(self, attr)(m, k)

class SpyKS (Spy) :
    def can_decrypt (self, message, knowledge) :
        try :
            if message[1][0] == "priv" :
                knowledge.add(("pub", message[1][1]))
        except :
            pass
        return Spy.can_decrypt(self, message, knowledge)

if __name__ == "__main__" :
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
