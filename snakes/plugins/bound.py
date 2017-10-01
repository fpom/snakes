"""A plugin to implement boundedness on places.

When this plugin is loaded, `Place` constructor accepts a parameter
`bound` that allows to specify the minimal and maximal number of
tokens that the place is allowed to carry. (Repeated tokens count as
many times as they are repeated.) Exception `ConstraintError` is
raised whenever an operation (like a transition firing) leads to
violate any of a place bound. (But note that direct modifications of a
`Place.tokens` are not checked.)

>>> import snakes.plugins
>>> snakes.plugins.load('bound', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *

If parameter `bound` is given as a non-negative integer, this is the
upper bound of the place (and its lower bound is zero).

>>> n = PetriNet('N')
>>> p = Place('p', [dot], bound=3)
>>> n.add_place(p)
>>> put = Transition('put')
>>> n.add_transition(put)
>>> n.add_output('p', 'put', Value(dot))
>>> p.tokens
MultiSet([dot])
>>> put.fire(Substitution())
>>> p.tokens
MultiSet([dot, dot])
>>> put.fire(Substitution())
>>> p.tokens
MultiSet([dot, dot, dot])
>>> put.fire(Substitution())
Traceback (most recent call last):
  ...
ConstraintError: upper bound of place 'p' reached

If `bound` is given as a pair `(n, None)` where `n` is a non-negative
integer, then `n` is the lower bound of the place (and it has no upper
bound).

>>> n = PetriNet('N')
>>> p = Place('p', [dot, dot], bound=(1, None))
>>> n.add_place(p)
>>> put = Transition('put')
>>> n.add_transition(put)
>>> n.add_output('p', 'put', Value(dot))
>>> get =  Transition('get')
>>> n.add_transition(get)
>>> n.add_input('p', 'get', Value(dot))
>>> p.tokens
MultiSet([dot, dot])
>>> get.fire(Substitution())
>>> p.tokens
MultiSet([dot])
>>> get.fire(Substitution())
Traceback (most recent call last):
  ...
ConstraintError: lower bound of place 'p' reached
>>> for i in range(100) : # no upper bound
...     put.fire(Substitution())

If `bound` is given as a pair of non-negative integers `(n,m)` such
that `n <= m` then `n` is the lower bound of the place and `m` its
upper bound.

>>> n = PetriNet('N')
>>> p = Place('p', [dot, dot], bound=(1, 3))
>>> n.add_place(p)
>>> put = Transition('put')
>>> n.add_transition(put)
>>> n.add_output('p', 'put', Value(dot))
>>> get =  Transition('get')
>>> n.add_transition(get)
>>> n.add_input('p', 'get', Value(dot))
>>> p.tokens
MultiSet([dot, dot])
>>> put.fire(Substitution())
>>> p.tokens
MultiSet([dot, dot, dot])
>>> put.fire(Substitution())
Traceback (most recent call last):
  ...
ConstraintError: upper bound of place 'p' reached
>>> get.fire(Substitution())
>>> p.tokens
MultiSet([dot, dot])
>>> get.fire(Substitution())
>>> p.tokens
MultiSet([dot])
>>> get.fire(Substitution())
Traceback (most recent call last):
  ...
ConstraintError: lower bound of place 'p' reached

Any other value for bound is refused raising a `ValueError`.

"""

from snakes.data import iterate
from snakes import ConstraintError
import snakes.plugins

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    "Extends `module`"
    class Place (module.Place) :
        "Extend places with boundedness"
        def __init__ (self, name, tokens, check=None, **args) :
            """Add new keyword argument `bound`

            @param args: plugin options
            @keyword bound: the place boundaries
            @type bound: `int` or `(int, None)` or `(int, int)`
            """
            bound = args.pop("bound", (0, None))
            if isinstance(bound, int) and bound >= 0 :
                self._bound_min, self._bound_max = 0, bound
            elif (isinstance(bound, tuple) and len(bound) == 2
                  and isinstance(bound[0], int) and bound[0] >= 0
                  and ((isinstance(bound[1], int) and bound[1] >= bound[0])
                       or bound[1] is None)) :
                self._bound_min, self._bound_max = bound
            else :
                raise ValueError("invalid value for parameter 'bound'")
            module.Place.__init__(self, name, tokens, check, **args)
        def add (self, tokens) :
            """Add tokens to the place.

            @param tokens: a collection of tokens to be added to the
                place, note that `str` are not considered as iterable and
                used a a single value instead of as a collection
            @type tokens: `collection`
            """
            if (self._bound_max is not None
                and len(self.tokens) + len(list(iterate(tokens))) > self._bound_max) :
                raise ConstraintError("upper bound of place %r reached" % self.name)
            module.Place.add(self, tokens)
        def remove (self, tokens) :
            """Remove tokens from the place.

            @param tokens: a collection of tokens to be removed from the
                place, note that `str` are not considered as iterable and
                used a a single value instead of as a collection
            @type tokens: `collection`
            """
            if len(self.tokens) - len(list(iterate(tokens))) < self._bound_min :
                raise ConstraintError("lower bound of place %r reached" % self.name)
            module.Place.remove(self, tokens)
        def reset (self, tokens) :
            """Replace the marking with `tokens`.

            @param tokens: a collection of tokens to be removed from the
                place, note that `str` are not considered as iterable and
                used a a single value instead of as a collection
            @type tokens: `collection`
            """
            count = len(list(iterate(tokens)))
            bmax = count if self._bound_max is None else self._bound_max
            if not (self._bound_min <= count <= bmax) :
                raise ConstraintError("not within bounds of place %r" % self.name)
            module.Place.reset(self, tokens)
    return Place
