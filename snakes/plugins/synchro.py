"""This plugin provides an implementation of the action-based
synchronisation from algebras of Petri nets. With respect to the usual
definition of synchronisation, the plugin is slightly more general in
that it does not impose a fixed arity for action. The extensions are
as follows:

  * class `Action` corresponds to a synchronisable action, it has a
    name, a send/receive flag and a list of parameters. Actions have
    no predetermined arities, only conjugated actions with the same
    arity will be able to synchronise
  * class `MultiAction` corresponds to a multiset of actions. It is
    forbidden to build a multiaction that holds a pair of conjugated
    actions because this leads to infinite nets upon synchronisation
  * the constructor of `Transition` accepts a parameter `actions` that
    is a collection of instances of `Action`, this multiaction is
    added in the attribute `actions` of the transition
  * PetriNet is given new methods: `synchronise` to perform the
    synchronisation, `restrict` to perform the restriction (ie, remove
    transitions with a given action) and `scope` for the scoping (ie,
    synchronisation followed by restriction)

### Example ###

Let's start with an example: we build a Petri net with two transitions
in parallel that will be synchronised later on.

>>> import snakes.plugins
>>> snakes.plugins.load('synchro', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> n = PetriNet('N')
>>> n.add_place(Place('e1'))
>>> n.add_place(Place('x1'))
>>> m1 = [Action('a', True, [Variable('x'), Value(2)]),
...       Action('b', True, [Value(3), Variable('y')]),
...       Action('c', False, [Variable('x'), Variable('y')])]
>>> print(', '.join(str(action) for action in m1))
a!(x,2), b!(3,y), c?(x,y)
>>> n.add_transition(Transition('t1', guard=Expression('x!=y'), actions=m1))
>>> n.add_input('e1', 't1', Variable('x'))
>>> n.add_output('x1', 't1', Variable('z'))
>>> n.add_place(Place('e2'))
>>> n.add_place(Place('x2'))
>>> m2 = [Action('a', False, [Variable('w'), Variable('y')]),
...       Action('d', False, [Variable('z')])]
>>> print(', '.join(str(action) for action in m2))
a?(w,y), d?(z)
>>> n.add_transition(Transition('t2', guard=Expression('z>0'), actions=m2))
>>> n.add_input('e2', 't2', Variable('w'))
>>> n.add_output('x2', 't2', Variable('z'))
>>> n.transition('t1').vars() == set(['x', 'y', 'z'])
True

On transition `t1`, we have put a multiaction that can be abbreviated
as `a!(x,2), a!(3,y), b?(x,y)` and can be interpreted as three
synchronous communication performed atomically and simultaneously when
`t1` fires:

  * `a!(x,2)` emits `(x,2)` on channel `a`
  * `b!(2,y)` emits `(2,y)` on channel `b`
  * `c?(x,y)` receives `(x,y)` on channel `c`

And similarly for transition `t2` that has two actions:

  * `a?(w,y)` receives `(w,y)` on channel `a`
  * `d?(z)` receives `z` on channel `d`

Thus, `t1` and `t2` hold _conjugated actions_, which are matching
emitting and receiving actions `a!(x,2)` and `a?(x,y)`. So we can
synchronise the net on `a` which builds a new transition whose firing
is exactly equivalent to the simultaneous firing of `t1` and `t2`
performing the communications over channel `a`.

>>> n.synchronise('a')
>>> t = [t for t in n.transition() if t.name not in ('t1', 't2')][0]
>>> print(t.name)
a(w,2)@(t1[x=w,y=e,z=f]+t2[y=2])
>>> print(t.guard)
((w != e)) and ((z > 0))
>>> print(', '.join(sorted(str(action) for action in t.actions)))
b!(3,e), c?(w,e), d?(z)

The second statement `t = ...` retrieves the new transition then we
print its name and guard. The names can be read as: this is the result
of execution action `a(w,2)` on `t1` substituted by `{x->w, y->e,
z->f}` and `t2` substituted by `{y->2}`. Indeed, both transitions have
variables `y` and `z`in common, so they are replaced in `t1` to avoid
names clashes, then, actions a can be `a!(x,2)` and `a?(w,y)` can be
matched by considering `x=w` and `y=2` which yields the rest of the
substitutions for the transitions. The resulting transition results
from the merging of the unified transitions, its guard is the `and` of
the guards of the merged transitions and its multiaction is the union
of the multiactions of the merged transitions minus the actions that
did synchronise.

The net now has three transitions: `t1`, `t2` and the new one
resulting from the synchronisation. This allows both synchronous and
asynchronous behaviour:

>>> for t in sorted(t.name for t in n.transition()) :
...     print(t)
a(w,2)@(t1[x=w,y=e,z=f]+t2[y=2])
t1
t2

If we want to force the synchronous behaviour, we have to restrict
over `'a'` which removes any transition that hold an action `a?(...)`
or `a!(...)`. In practice, this is what we want and so we may have
used method `n.scope('a')` to apply directly the synchronisation
followed by the restriction.

>>> n.restrict('a')
>>> for t in sorted(t.name for t in n.transition()) :
...     print(t)
a(w,2)@(t1[x=w,y=e,z=f]+t2[y=2])
"""

from snakes import ConstraintError
from snakes.data import Substitution, WordSet, iterate
from snakes.nets import Value, Variable
from snakes.pnml import Tree
import snakes.plugins
from snakes.plugins import new_instance
from snakes.compat import *

class Action (object) :
    """Models one action with a name, a direction (send or receive)
    and parameters.
    """
    def __init__ (self, name, send, params) :
        """Constructor. The direction is passed as a Boolean: `True`
        for a send action, `False` for a receive.

        @param name: the name of the action
        @type name: `str`
        @param send: a flag indicating whether this is a send or
            receive action
        @type send: `bool`
        @param params: the list of parameters that must me instances
            of `Variable` or `Value`
        @type params: `list`
        """
        self.name = name
        self.send = send
        self.params = list(params)
    __pnmltag__ = "action"
    # apidoc skip
    def __pnmldump__ (self) :
        """
        >>> Action('a', True, [Value(1), Variable('x')]).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>...
         <action name="a" send="True">
          <value>
           <object type="int">1</object>
          </value>
          <variable>x</variable>
         </action>
        </pnml>
        """
        result = Tree(self.__pnmltag__, None,
                      name=self.name,
                      send=str(self.send))
        for param in self.params :
            result.add_child(Tree.from_obj(param))
        return result
    # apidoc stop
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> t = Action('a', True, [Value(1), Variable('x')]).__pnmldump__()
        >>> Action.__pnmlload__(t)
        Action('a', True, [Value(1), Variable('x')])
        """
        params = [Tree.to_obj(child) for child in tree.children]
        return cls(tree["name"], tree["send"] == "True", params)
    def __str__ (self) :
        """
        >>> a = Action('a', True, [Value(1), Variable('x')])
        >>> str(a)
        'a!(1,x)'
        >>> a.send = False
        >>> str(a)
        'a?(1,x)'
        """
        if self.send :
            return "%s!(%s)" % (self.name, ",".join([str(p) for p in self]))
        else :
            return "%s?(%s)" % (self.name, ",".join([str(p) for p in self]))
    def __repr__ (self) :
        """
        >>> a = Action('a', True, [Value(1), Variable('x')])
        >>> repr(a)
        "Action('a', True, [Value(1), Variable('x')])"
        >>> a.send = False
        >>> repr(a)
        "Action('a', False, [Value(1), Variable('x')])"
        """
        return "%s(%s, %s, [%s])" % (self.__class__.__name__, repr(self.name),
                                     str(self.send),
                                     ", ".join([repr(p) for p in self]))
    def __len__ (self) :
        """Return the number of parameters, aka the arity of the action.

        >>> len(Action('a', True, [Value(1), Variable('x')]))
        2

        @return: the arity of the action
        @rtype: non negative `int`
        """
        return len(self.params)
    def __iter__ (self) :
        """Iterate on the parameters

        >>> list(Action('a', True, [Value(1), Variable('x')]))
        [Value(1), Variable('x')]
        """
        for action in self.params :
            yield action
    def __eq__ (self, other) :
        """Two actions are equal if they have the same name, same send
        flags and same parameters.

        >>> Action('a', True, [Value(1), Variable('x')]) == Action('a', True, [Value(1), Variable('x')])
        True
        >>> Action('a', True, [Value(1), Variable('x')]) == Action('b', True, [Value(1), Variable('x')])
        False
        >>> Action('a', True, [Value(1), Variable('x')]) == Action('a', False, [Value(1), Variable('x')])
        False
        >>> Action('a', True, [Value(1), Variable('x')]) == Action('a', True, [Value(2), Variable('x')])
        False
        >>> Action('a', True, [Value(1), Variable('x')]) == Action('a', True, [Value(1)])
        False

        @param other: the action to compare
        @type other: `Action`
        @return: `True` if the two actions are equal, `False`
            otherwise
        @rtype: `bool`
        """
        if self.name != other.name :
            return False
        elif self.send != other.send :
            return False
        elif len(self.params) != len(other.params) :
            return False
        for p, q in zip(self.params, other.params) :
            if p != q :
                return False
        return True
    def __ne__ (self, other) :
        return not (self == other)
    def copy (self, subst=None) :
        """Copy the action, optionally substituting its parameters.

        >>> a = Action('a', True, [Variable('x'), Value(2)])
        >>> a.copy()
        Action('a', True, [Variable('x'), Value(2)])
        >>> a = Action('a', True, [Variable('x'), Value(2)])
        >>> a.copy(Substitution(x=Value(3)))
        Action('a', True, [Value(3), Value(2)])

        @param subst: if not `None`, a substitution to apply to the
            parameters of the copy mapping variables names to `Value`
            or `Variable`
        @type subst: `Substitution`
        @return: a copy of the action, substituted by `subst` if not
            `None`
        @rtype: `Action`
        """
        result = self.__class__(self.name, self.send,
                                [p.copy() for p in self.params])
        if subst is not None :
            result.substitute(subst)
        return result
    def substitute (self, subst) :
        """Substitute the parameters according to `subst`

        >>> a = Action('a', True, [Variable('x'), Value(2)])
        >>> a.substitute(Substitution(x=Value(3)))
        >>> a
        Action('a', True, [Value(3), Value(2)])

        @param subst: a substitution to apply to the parameters,
            mapping variables names to `Value` or `Variable`
        @type subst: `Substitution`
        """
        for i, p in enumerate(self.params) :
            if isinstance(p, Variable) and p.name in subst :
                self.params[i] = subst(p.name)
    def vars (self) :
        """
        >>> Action('a', True, [Value(3), Variable('x'), Variable('y'), Variable('x')]).vars() == set(['x', 'y'])
        True

        @return: the set of variable names appearing in the parameters
            of the action
        @rtype: `set` of `str`
        """
        return set(p.name for p in self.params if isinstance(p, Variable))
    def __and__ (self, other) :
        """Compute an unification of two conjugated actions.

        An unification is a `Substitution` that maps variable names to
        `Variable` or `Values`. If both actions are substituted by
        this unification, their parameters lists become equal. If no
        unification can be found, `ConstraintError` is raised (or,
        rarely, `DomainError` depending on the cause of the failure).

        >>> s = Action('a', True, [Value(3), Variable('x'), Variable('y'), Variable('x')])
        >>> r = Action('a', False, [Value(3), Value(2), Variable('t'), Variable('z')])
        >>> u = s & r
        >>> u == Substitution(y=Variable('t'), x=Value(2), z=Value(2))
        True
        >>> s.substitute(u)
        >>> r.substitute(u)
        >>> s.params == r.params
        True
        >>> s.params
        [Value(3), Value(2), Variable('t'), Value(2)]
        >>> s = Action('a', True, [Value(2), Variable('x'), Variable('y'), Variable('x')])
        >>> r = Action('a', False, [Value(3), Value(2), Variable('t'), Variable('z')])
        >>> try : s & r
        ... except ConstraintError : print(sys.exc_info()[1])
        incompatible values
        >>> r = Action('a', False, [Value(2), Value(2), Variable('t')])
        >>> try : s & r
        ... except ConstraintError : print(sys.exc_info()[1])
        arities do not match
        >>> r = Action('b', False, [Value(3), Value(2), Variable('t'), Variable('z')])
        >>> try : s & r
        ... except ConstraintError : print(sys.exc_info()[1])
        actions not conjugated
        >>> r = Action('a', True, [Value(3), Value(2), Variable('t'), Variable('z')])
        >>> try : s & r
        ... except ConstraintError : print(sys.exc_info()[1])
        actions not conjugated

        @param other: the other action to unify with
        @type other: `Action`
        @return: a substitution that unify both actions
        @rtype: `Substitution`
        """
        if (self.name != other.name) or (self.send == other.send) :
            raise ConstraintError("actions not conjugated")
        elif len(self) != len(other) :
            raise ConstraintError("arities do not match")
        result = Substitution()
        for x, y in zip(self.params, other.params) :
            # apply the unifier already computed
            if isinstance(x, Variable) and x.name in result :
                x = result(x.name)
            if isinstance(y, Variable) and y.name in result :
                y = result(y.name)
            # unify the current pair of parameters
            if isinstance(x, Value) and isinstance(y, Value) :
                if x.value != y.value :
                    raise ConstraintError("incompatible values")
            elif isinstance(x, Variable) and isinstance(y, Value) :
                result += Substitution({x.name : y.copy()})
            elif isinstance(x, Value) and isinstance(y, Variable) :
                result += Substitution({y.name : x.copy()})
            elif isinstance(x, Variable) and isinstance(y, Variable) :
                if x.name != y.name :
                    result += Substitution({x.name : y.copy()})
            else :
                raise ConstraintError("unexpected action parameter")
        return result

class MultiAction (object) :
    """Models a multiset of actions.
    """
    def __init__ (self, actions) :
        """The only restriction when building a multiaction is to
        avoid putting two conjugated actions in it. Indeed, this may
        lead to infinite Petri nets upon synchronisation. For example,
        consider two transitions `t1` and `t2` with both `a?()` and
        `a!()` in their multiactions. We can synchronise say `a?()`
        from `t1` with `a!()` from `t2` yielding a transition whose
        multiaction has `a!()` from `t1` and `a?() from `t2` and thus
        can be synchronised with `t1` or `t2`, yielding a new
        transition with `a?()` and `a!()`, etc. Fortunately, it makes
        little sense to let a transition synchronise with itself, so
        this situation is simply forbidden.

        >>> try : MultiAction([Action('a', True, [Variable('x')]),
        ...                    Action('a', False, [Value(2)])])
        ... except ConstraintError : print(sys.exc_info()[1])
        conjugated actions in the same multiaction

        @param actions: a collection of `Action` instances with no
            conjugated actions in it
        @type actions: `iterable`
        """
        self._actions = []
        self._sndrcv = {}
        self._count = {}
        for act in actions :
            self.add(act)
    __pnmltag__ = "multiaction"
    # apidoc stop
    def __pnmldump__ (self) :
        """
        >>> MultiAction([Action('a', True, [Variable('x')]),
        ...              Action('b', False, [Variable('y'), Value(2)])
        ...             ]).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>...
         <multiaction>
          <action name="a" send="True">
           <variable>x</variable>
          </action>
          <action name="b" send="False">
           <variable>y</variable>
           <value>
            <object type="int">2</object>
           </value>
          </action>
         </multiaction>
        </pnml>
        """
        return Tree(self.__pnmltag__, None,
                    *(Tree.from_obj(action) for action in self._actions))
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> t = MultiAction([Action('a', True, [Variable('x')]),
        ...                  Action('b', False, [Variable('y'), Value(2)])
        ...                 ]).__pnmldump__()
        >>> MultiAction.__pnmlload__(t)
        MultiAction([Action('a', True, [Variable('x')]),
                     Action('b', False, [Variable('y'), Value(2)])])
        """
        return cls(child.to_obj() for child in tree.children)
    def __repr__ (self) :
        """
        >>> MultiAction([Action('a', True, [Variable('x')]),
        ...              Action('b', False, [Variable('y'), Value(2)])])
        MultiAction([Action('a', True, [Variable('x')]),
                     Action('b', False, [Variable('y'), Value(2)])])
        """
        return "%s([%s])" % (self.__class__.__name__,
                             ", ".join(repr(act) for act in self._actions))
    def __str__ (self) :
        """
        >>> str(MultiAction([Action('a', True, [Variable('x')]),
        ...                  Action('b', False, [Variable('y'), Value(2)])]))
        '[a!(x), b?(y,2)]'
        """
        return "[%s]" % ", ".join(str(act) for act in self._actions)
    def send (self, name) :
        """Returns the send flag of the action `name` in this
        multiaction.

        This value is unique as conjugated actions are forbidden in
        the same multiaction.

        >>> m = MultiAction([Action('a', True, [Variable('x')]),
        ...                  Action('b', False, [Variable('y'), Value(2)])])
        >>> m.send('a'), m.send('b')
        (True, False)
        """
        return self._sndrcv[name]
    def add (self, action) :
        """Add an action to the multiaction.

        This may raise `ConstraintError` if the added action is
        conjugated to one that already belongs to the multiaction.

        @param action: the action to add
        @type action: `Action`
        """
        if self._sndrcv.get(action.name, action.send) != action.send :
            raise ConstraintError("conjugated actions in the same multiaction")
        self._sndrcv[action.name] = action.send
        self._count[action.name] = self._count.get(action.name, 0) + 1
        self._actions.append(action)
    def remove (self, action) :
        """Remove an action from the multiaction.

        This may raise `ValueError` if the removed action does belongs
        to the multiaction.

        @param action: the action to remove
        @type action: `Action`
        """
        self._actions.remove(action)
        self._count[action.name] -= 1
        if self._count[action.name] == 0 :
            del self._count[action.name]
            del self._sndrcv[action.name]
    def __iter__ (self) :
        """Iterate over the actions in the multiaction.

        >>> list(MultiAction([Action('a', True, [Variable('x')]),
        ...                   Action('b', False, [Variable('y'), Value(2)])]))
        [Action('a', True, [Variable('x')]),
         Action('b', False, [Variable('y'), Value(2)])]
        """
        for action in self._actions :
            yield action
    def __len__ (self) :
        """Return the number of actions in a multiaction.

        >>> len(MultiAction([Action('a', True, [Variable('x')]),
        ...                  Action('b', False, [Variable('y'), Value(2)])]))
        2

        @return: the number of contained actions
        @rtype: non negative `int`
        """
        return len(self._actions)
    def substitute (self, subst) :
        """Substitute bu `subt` all the actions in the multiaction.

        >>> m = MultiAction([Action('a', True, [Variable('x')]),
        ...                  Action('b', False, [Variable('y'), Variable('x')])])
        >>> m.substitute(Substitution(x=Value(4)))
        >>> m
        MultiAction([Action('a', True, [Value(4)]),
                     Action('b', False, [Variable('y'), Value(4)])])
        """
        for action in self._actions :
            action.substitute(subst)
    def copy (self, subst=None) :
        """Copy the multiaction (and the actions is contains) optionally
        substituting it.

        @param subst: if not `None`, the substitution to apply to the
            copy.
        @type subst: `Substitution`
        @return: a copy of the multiaction, optionally substituted
        @rtype: `MultiAction`
        """
        return self.__class__(act.copy(subst) for act in self._actions)
    def __contains__ (self, action) :
        """Search an action in the multiaction.

        The searched action may be a complete `Action`, just an action
        name, or a pair `(name, send_flag)`.

        >>> m = MultiAction([Action('a', True, [Variable('x'), Value(2)]),
        ...                  Action('a', True, [Value(3), Variable('y')]),
        ...                  Action('b', False, [Variable('x'), Variable('y')])])
        >>> 'a' in m, 'b' in m, 'c' in m
        (True, True, False)
        >>> ('a', True) in m, ('a', False) in m
        (True, False)
        >>> Action('a', True, [Variable('x'), Value(2)]) in m
        True
        >>> Action('a', True, [Variable('x')]) in m
        False
        >>> Action('a', False, [Variable('x'), Value(2)]) in m
        False
        >>> Action('c', True, [Variable('x'), Value(2)]) in m
        False

        @param action: an complete action, or its name or its name and
            send flag
        @type action: `Action`
        @return: `True` if the specified action was found, `False`
            otherwise
        @rtype: `bool`
        """
        if isinstance(action, Action) :
            return action in self._actions
        elif isinstance(action, tuple) and len(action) == 2 :
            return (action[0] in self._sndrcv
                    and self._sndrcv[action[0]] == action[1])
        elif isinstance(action, str) :
            return action in self._count
        else :
            raise ValueError("invalid action specification")
    def __add__ (self, other) :
        """Create a multiaction by adding the actions of two others.

        >>> m = MultiAction([Action('a', True, [Variable('x'), Value(2)]),
        ...                  Action('a', True, [Value(3), Variable('y')]),
        ...                  Action('b', False, [Variable('x'), Variable('y')])])
        >>> m + m
        MultiAction([Action('a', True, [Variable('x'), Value(2)]),
                     Action('a', True, [Value(3), Variable('y')]),
                     Action('b', False, [Variable('x'), Variable('y')]),
                     Action('a', True, [Variable('x'), Value(2)]),
                     Action('a', True, [Value(3), Variable('y')]),
                     Action('b', False, [Variable('x'), Variable('y')])])
        >>> m + Action('c', True, [])
        MultiAction([Action('a', True, [Variable('x'), Value(2)]),
                     Action('a', True, [Value(3), Variable('y')]),
                     Action('b', False, [Variable('x'), Variable('y')]),
                     Action('c', True, [])])

        @param other: the other multiaction to combine or a single
            action
        @type other: `MultiAction` or `Action`
        @return: the concatenated multiaction
        @rtype: `MultiAction`
        """
        if isinstance(other, Action) :
            other = self.__class__([other])
        result = self.copy()
        for action in other._actions :
            result.add(action)
        return result
    def __sub__ (self, other) :
        """Create a multiaction by substracting the actions of two
        others.

        >>> m = MultiAction([Action('a', True, [Variable('x'), Value(2)]),
        ...                  Action('a', True, [Value(3), Variable('y')]),
        ...                  Action('b', False, [Variable('x'), Variable('y')])])
        >>> m - m
        MultiAction([])
        >>> m - Action('b', False, [Variable('x'), Variable('y')])
        MultiAction([Action('a', True, [Variable('x'), Value(2)]),
                     Action('a', True, [Value(3), Variable('y')])])

        @param other: the other multiaction to combine or a single
            action
        @type other: `MultiAction` or `Action`
        @return: the resulting multiaction
        @rtype: `MultiAction`
        """
        if isinstance(other, Action) :
            other = self.__class__([other])
        result = self.copy()
        for action in other._actions :
            result.remove(action)
        return result
    def vars (self) :
        """Return the set of variable names used in all the actions of
        the multiaction.

        >>> MultiAction([Action('a', True, [Variable('x'), Value(2)]),
        ...              Action('a', True, [Value(3), Variable('y')]),
        ...              Action('b', False, [Variable('x'), Variable('z')])]).vars() == set(['x', 'y', 'z'])
        True

        @return: the set of variable names
        @rtype: `set` of `str`
        """
        result = set()
        for action in self._actions :
            result.update(action.vars())
        return result
    def names (self) :
        """Return the set of action names used in the multiaction.

        >>> MultiAction([Action('a', True, [Variable('x'), Value(2)]),
        ...              Action('a', True, [Value(3), Variable('y')]),
        ...              Action('b', False, [Variable('x'), Variable('z')])]).names() == set(['a', 'b'])
        True

        @return: the set of variable names
        @rtype: `set` of `str`
        """
        return set([action.name for action in self._actions])
    def synchronise (self, other, name, common, allnames) :
        """Search all the possible synchronisation on an action name with
        another multiaction.

        This method returns an iterator that yields for each possible
        synchronisation a 4-tuple whose components are:


          * the sending action that did synchronise, it is already
            unified, so the corresponding receiving action is just
            the same with the reversed send flag
          * the multiaction resulting from the synchronisation that
            is also unified
          * the substitution that must be applied to the transition
            that provided the sending action
          * the substitution that must be applied to the transition
            that provided the receiving action

        >>> m = MultiAction([Action('a', True, [Variable('x'), Value(2)]),
        ...                  Action('a', True, [Value(3), Variable('y')]),
        ...                  Action('b', False, [Variable('x'), Variable('y')])])
        >>> n = MultiAction([Action('a', False, [Variable('w'), Variable('y')]),
        ...                  Action('c', False, [Variable('y')])])
        >>> _m, _n = m.vars(), n.vars()
        >>> for a, x, u, v in m.synchronise(n, 'a', _m & _n, _m | _n) :
        ...    print('%s %s' % (str(a), str(x)))
        ...    print(list(sorted(u.items())))
        ...    print(list(sorted(v.items())))
        a!(w,2) [a!(3,d), b?(w,d), c?(2)]
        [('x', Variable('w')), ('y', Variable('d'))]
        [('x', Variable('w')), ('y', Value(2))]
        a!(3,y) [a!(x,2), b?(x,y), c?(y)]
        [('d', Variable('y')), ('w', Value(3)), ('y', Variable('d'))]
        [('d', Variable('y')), ('w', Value(3))]

        @param other: the other multiaction to synchronise with
        @type other: `MultiAction`
        @param name: the name of the action to synchronise on
        @type name: `str`
        @param common: the set of names in common on both transitions
        @type common: `set`
        @param allnames: the set of all names involved in the transitions
        @type allnames: `set`
        @return: an iterator over the possible synchronisations
        @rtype: iterator of `tuple(Action, MultiAction, Substitution,
            Substitution)`
        """
        renamer = Substitution()
        if common :
            names = WordSet(set(allnames) | self.names() | other.names())
            for var in common :
                renamer += Substitution({var : Variable(names.fresh(add=True))})
        for left in (act for act in self._actions if act.name == name) :
            for right in (act for act in other._actions if act.name == name
                          if act.send != left.send) :
                _left = left.copy(renamer)
                try :
                    unifier = _left & right
                except :
                    continue
                _self = self.copy(renamer) - _left
                _self.substitute(unifier)
                _other = other - right
                _other.substitute(unifier)
                yield (_left.copy(unifier), _self + _other,
                       unifier * renamer, unifier)

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    class Transition (module.Transition) :
        """Class `Transition` is extended to allow a keyword argument
        `actions` in several of its methods `__init__` and `copy` (to
        replace a multiaction upon copy).
        """
        # apidoc stop
        def __init__ (self, name, guard=None, **args) :
            self.actions = MultiAction(args.pop("actions", []))
            module.Transition.__init__(self, name, guard, **args)
        def vars (self) :
            return module.Transition.vars(self) | self.actions.vars()
        def substitute (self, subst) :
            module.Transition.substitute(self, subst)
            self.actions.substitute(subst)
        def copy (self, name=None, **args) :
            actions = args.pop("actions", None)
            result = module.Transition.copy(self, name, **args)
            if actions is None :
                result.actions = self.actions.copy()
            else :
                result.actions = MultiAction(actions)
            return result
        def __pnmldump__ (self) :
            """
            >>> m = MultiAction([Action('a', True, [Variable('x')]),
            ...                  Action('b', False, [Variable('y'), Value(2)])])
            >>> Transition('t', actions=m).__pnmldump__()
            <?xml version="1.0" encoding="utf-8"?>
            <pnml>...
             <transition id="t">
              <multiaction>
               <action name="a" send="True">
                <variable>x</variable>
               </action>
               <action name="b" send="False">
                <variable>y</variable>
                <value>
                 <object type="int">2</object>
                </value>
               </action>
              </multiaction>
             </transition>
            </pnml>
            """
            result = module.Transition.__pnmldump__(self)
            result.add_child(Tree.from_obj(self.actions))
            return result
        @classmethod
        def __pnmlload__ (cls, tree) :
            """
            >>> m = MultiAction([Action('a', True, [Variable('x')]),
            ...                  Action('b', False, [Variable('y'), Value(2)])])
            >>> t = Transition('t', actions=m).__pnmldump__()
            >>> Transition.__pnmlload__(t).actions
            MultiAction([Action('a', True, [Variable('x')]),
                         Action('b', False, [Variable('y'), Value(2)])])
            """
            result = new_instance(cls, module.Transition.__pnmlload__(tree))
            result.actions = Tree.to_obj(tree.child(MultiAction.__pnmltag__))
            return result
    class PetriNet (module.PetriNet) :
        def synchronise (self, name) :
            """Synchronise the net wrt `name`.

            @param name: the action name to be synchronised
            @type name: `str`
            @return: the synchronised Petri net
            @rtype: `PetriNet`
            """
            snd = []
            rcv = []
            for trans in self.transition() :
                if (name, True) in trans.actions :
                    snd.append(trans)
                elif (name, False) in trans.actions :
                    rcv.append(trans)
            loop = True
            done = set()
            while loop :
                loop = False
                for _snd in snd :
                    for _rcv in rcv :
                        if (_snd.name, _rcv.name) in done :
                            continue
                        try :
                            _s, _r = _snd.vars(), _rcv.vars()
                            new = _snd.actions.synchronise(_rcv.actions,
                                                           name,
                                                           _s & _r, _s | _r)
                        except ConstraintError :
                            continue
                        for a, m, s, r in new :
                            t = self._synchronise(
                                _snd, s.restrict(_snd.vars()),
                                _rcv, r.restrict(_rcv.vars()),
                                m, a)
                            if (name, True) in t.actions :
                                snd.append(t)
                                loop = True
                            elif (name, False) in t.actions :
                                rcv.append(t)
                                loop = True
                        done.add((_snd.name, _rcv.name))
        def _synchronise (self, snd, s, rcv, r, actions, sync) :
            def _str (binding) :
                return ",".join("%s=%s" % i for i in sorted(binding.items()))
            collect = []
            for trans, subst in ((snd, s), (rcv, r)) :
                new = "%s[%s]" % (trans.name, _str(subst))
                self.copy_transition(trans.name, new)
                collect.append(new)
                new = self.transition(new)
                for var, val in subst.items() :
                    if isinstance(val, Variable) :
                        new.substitute(Substitution({var : val.name}))
                    for place, label in new.input() :
                        if var in label.vars() :
                            self.remove_input(place.name, new.name)
                            self.add_input(place.name, new.name,
                                           label.replace(Variable(var), val))
                    for place, label in new.output() :
                        if var in label.vars() :
                            self.remove_output(place.name, new.name)
                            self.add_output(place.name, new.name,
                                            label.replace(Variable(var), val))
                new.substitute(subst)
            merged = ("%s@(%s)" %
                      (str(sync).replace("?", "").replace("!", ""),
                       "+".join(collect)))
            self.merge_transitions(merged, collect, actions=actions)
            for name in collect :
                self.remove_transition(name)
            return self.transition(merged)
        def restrict (self, name) :
            """Restrict the net wrt `name`.

            @param name: the action name to be synchronised
            @type name: `str`
            @return: the synchronised Petri net
            @rtype: `PetriNet`
            """
            removed = [trans.name for trans in self.transition()
                       if name in trans.actions]
            for trans in removed :
                self.remove_transition(trans)
        def scope (self,  name) :
            """Scope the net wrt `name`, this is equivalent to apply
            synchronisation followed by restriction on the same
            `name`.

            @param name: the action name to be synchronised
            @type name: `str`
            @return: the synchronised Petri net
            @rtype: `PetriNet`
            """

            self.synchronise(name)
            self.restrict(name)
        def merge_transitions (self, target, sources, **args) :
            """Accepts a keyword parameter `actions` to change the
            multiaction of the resulting transition. If `actions` is
            not given, the multiaction of the new transition is the
            sum of the multiactions of the merged transition.

            @keyword actions: the multiaction of the transition
                resulting from the merge
            @type actions: `MultiAction`
            """
            actions = args.pop("actions", None)
            module.PetriNet.merge_transitions(self, target, sources, **args)
            if actions is None :
                actions = MultiAction()
                for src in sources :
                    actions += self.transition(src).actions
                self.transition(target).actions = actions
            else :
                self.transition(target).actions = MultiAction(actions)
        def copy_transition (self, source, targets, **args) :
            """Accepts a keyword parameter `actions` to change the
            multiaction of the resulting transition. If `actions` is
            not given, the multiaction of the new transition is the
            the same multiaction as the copied transition.

            @keyword actions: the multiaction of the transition
                resulting from the copy
            @type actions: `MultiAction`
            """
            actions = args.pop("actions", None)
            module.PetriNet.copy_transition(self, source, targets, **args)
            if actions is None :
                actions = self.transition(source).actions
            else :
                actions = MultiAction(actions)
            old = self.transition(source)
            for trans in iterate(targets) :
                self.transition(trans).actions = actions.copy()
    return PetriNet, Transition, Action, MultiAction
