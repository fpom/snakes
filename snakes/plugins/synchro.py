"""An implementation of the M-nets synchronisation.

This plugins extends the basic Petri net model in order to provide an
action-based synchronisation scheme that implements that of M-nets.
The plugin proposes a generalisation of the M-nets synchronisation in
that it does not impose a fixed correspondence between action names
and action arities.

 - class C{Action} corresponds to a synchronisable action, it has a
   name, a send/receive flag and a list of parameters. Actions have no
   predetermined arities, only conjugated actions with the same arity
   will be able to synchronise.

 - class C{MultiAction} corresponds to a multiset of actions. It is
   forbidden to build a multiaction that holds a pair of conjugated
   actions (this leads to infinite nets when synchronising).

 - Transition.__init__ accepts a parameter C{actions} that is a
   collection of instances of C{Action}, this multiaction is added in
   the attribute C{actions} of the transition.

 - PetriNet is given new methods: C{synchronise(action_name)} to
   perform the M-net synchronisation, C{restrict(action_name)} to
   perform the restriction and C{scope(action_name)} for the scoping.

B{Remark:} the instances of C{Substitution} used in this plugins must
map variable names to instances of C{Variable} or C{Value}, but not to
other variable names.

>>> import snakes.plugins
>>> snakes.plugins.load('synchro', 'snakes.nets', 'nets')
<module ...>
>>> from nets import PetriNet, Place, Transition, Expression
>>> n = PetriNet('N')
>>> n.add_place(Place('e1'))
>>> n.add_place(Place('x1'))
>>> n.add_transition(Transition('t1', guard=Expression('x!=y'),
...                             actions=[Action('a', True, [Variable('x'), Value(2)]),
...                                      Action('a', True, [Value(3), Variable('y')]),
...                                      Action('b', False, [Variable('x'), Variable('y')])]))
>>> n.add_input('e1', 't1', Variable('x'))
>>> n.add_output('x1', 't1', Variable('z'))
>>> n.add_place(Place('e2'))
>>> n.add_place(Place('x2'))
>>> n.add_transition(Transition('t2', guard=Expression('z>0'),
...                             actions=[Action('a', False, [Variable('w'), Variable('y')]),
...                                      Action('c', False, [Variable('z')])]))
>>> n.add_input('e2', 't2', Variable('w'))
>>> n.add_output('x2', 't2', Variable('z'))
>>> n.transition('t1').vars() == set(['x', 'y', 'z'])
True
>>> n.transition('t2').copy().vars() == set(['w', 'y', 'z'])
True
>>> n.synchronise('a')
>>> for t in sorted(n.transition(), key=str) :
...     print t, t.guard
...     for place, label in sorted(t.input(), key=str) :
...         print '   ', place, '>>', label
...     for place, label in sorted(t.output(), key=str) :
...         print '   ', place, '<<', label
((t1{...}+t2{...})[a(...)]{...}+t2{...})[a(...)] (...)
...
t2 z>0
   e2 >> w
   x2 << z
>>> n.restrict('a')
>>> [t.name for t in sorted(n.transition(), key=str)]
['((t1{...}+t2{...})[a(...)]{...}+t2{...})[a(...)]',
 '((t1{...}+t2{...})[a(...)]{...}+t2{...})[a(...)]']
"""

from snakes import ConstraintError
from snakes.data import Substitution, WordSet, iterate
from snakes.nets import Value, Variable
from snakes.pnml import Tree
import snakes.plugins
from snakes.plugins import new_instance

class Action (object) :
    def __init__ (self, name, send, params) :
        """
        @param name: the name of the action
        @type name: C{str}
        @param send: a flag indicating whether this is a send or
           receive action
        @type send: C{bool}
        @param params: the list of parameters
        @type params: C{list} of C{Variable} or C{Value}
        """
        self.name = name
        self.send = send
        self.params = list(params)
    __pnmltag__ = "action"
    def __pnmldump__ (self) :
        """
        >>> Action('a', True, [Value(1), Variable('x')]).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>...
         <action name="a" send="True">
          <value>
           <object type="int">
            1
           </object>
          </value>
          <variable>
           x
          </variable>
         </action>
        </pnml>
        """
        result = Tree(self.__pnmltag__, None,
                      name=self.name,
                      send=str(self.send))
        for param in self.params :
            result.add_child(Tree.from_obj(param))
        return result
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
        """Return the number of parameters, aka the arity of the
        action.

        >>> len(Action('a', True, [Value(1), Variable('x')]))
        2

        @return: the arity of the action
        @rtype: non negative C{int}
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
        @type other: C{Action}
        @return: C{True} if the two actions are equal, C{False}
          otherwise
        @rtype: C{bool}
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

        @param subst: if not C{None}, a substitution to apply to the
          parameters of the copy
        @type subst: C{None} or C{Substitution} mapping variables
          names to C{Value} or C{Variable}
        @return: a copy of the action, substituted by C{subst} if not
          C{None}
        @rtype: C{Action}
        """
        result = self.__class__(self.name, self.send,
                                [p.copy() for p in self.params])
        if subst is not None :
            result.substitute(subst)
        return result
    def substitute (self, subst) :
        """Substitute the parameters according to C{subst}

        >>> a = Action('a', True, [Variable('x'), Value(2)])
        >>> a.substitute(Substitution(x=Value(3)))
        >>> a
        Action('a', True, [Value(3), Value(2)])

        @param subst: a substitution to apply to the parameters
        @type subst: C{Substitution} mapping variables names to
          C{Value} or C{Variable}
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
        @rtype: C{set} of C{str}
        """
        return set(p.name for p in self.params if isinstance(p, Variable))
    def __and__ (self, other) :
        """Compute an unification of two conjugated actions.

        An unification is a C{Substitution} that maps variable names
        to C{Variable} or C{Values}. If both actions are substituted
        by this unification, their parameters lists become equal. If
        no unification can be found, C{ConstraintError} is raised (or,
        rarely, C{DomainError} depending on the cause of the failure).

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
        >>> s & r
        Traceback (most recent call last):
          ...
        ConstraintError: incompatible values
        >>> r = Action('a', False, [Value(2), Value(2), Variable('t')])
        >>> s & r
        Traceback (most recent call last):
          ...
        ConstraintError: arities do not match
        >>> r = Action('b', False, [Value(3), Value(2), Variable('t'), Variable('z')])
        >>> s & r
        Traceback (most recent call last):
          ...
        ConstraintError: actions not conjugated
        >>> r = Action('a', True, [Value(3), Value(2), Variable('t'), Variable('z')])
        >>> s & r
        Traceback (most recent call last):
          ...
        ConstraintError: actions not conjugated

        @param other: the other action to unify with
        @type other: C{Action}
        @return: a substitution that unify both actions
        @rtype: C{Substitution}
        """
        if (self.name != other.name) or (self.send == other.send) :
            raise ConstraintError, "actions not conjugated"
        elif len(self) != len(other) :
            raise ConstraintError, "arities do not match"
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
                    raise ConstraintError, "incompatible values"
            elif isinstance(x, Variable) and isinstance(y, Value) :
                result += Substitution({x.name : y.copy()})
            elif isinstance(x, Value) and isinstance(y, Variable) :
                result += Substitution({y.name : x.copy()})
            elif isinstance(x, Variable) and isinstance(y, Variable) :
                if x.name != y.name :
                    result += Substitution({x.name : y.copy()})
            else :
                raise ConstraintError, "unexpected action parameter"
        return result

class MultiAction (object) :
    def __init__ (self, actions) :
        """
        >>> MultiAction([Action('a', True, [Variable('x')]),
        ...              Action('a', False, [Value(2)])])
        Traceback (most recent call last):
          ...
        ConstraintError: conjugated actions in the same multiaction

        @param actions: a collection of actions with no conjugated
          actions in it
        @type actions: C{list} of C{Action}
        """
        self._actions = []
        self._sndrcv = {}
        self._count = {}
        for act in actions :
            self.add(act)
    __pnmltag__ = "multiaction"
    def __pnmldump__ (self) :
        """
        >>> MultiAction([Action('a', True, [Variable('x')]),
        ...              Action('b', False, [Variable('y'), Value(2)])
        ...             ]).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>...
         <multiaction>
          <action name="a" send="True">
           <variable>
            x
           </variable>
          </action>
          <action name="b" send="False">
           <variable>
            y
           </variable>
           <value>
            <object type="int">
             2
            </object>
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
        """Returns the send flag of the action C{name} in this
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

        This may raise C{ConstraintError} if the added action is
        conjugated to one that already belongs to the multiaction.

        @param action: the action to add
        @type action: C{Action}
        """
        if self._sndrcv.get(action.name, action.send) != action.send :
            raise ConstraintError, "conjugated actions in the same multiaction"
        self._sndrcv[action.name] = action.send
        self._count[action.name] = self._count.get(action.name, 0) + 1
        self._actions.append(action)
    def remove (self, action) :
        """Remove an action from the multiaction.

        This may raise C{ValueError} if the removed action does
        belongs to the multiaction.

        @param action: the action to remove
        @type action: C{Action}
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
        @rtype: non negative C{int}
        """
        return len(self._actions)
    def substitute (self, subst) :
        """Substitute bu C{subt} all the actions in the multiaction.

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
        """ Copy the multiaction (and the actions is contains)
        optionally substituting it.

        @param subst: if not C{None}, the substitution to apply to the
          copy.
        @type subst: C{None} or C{Substitution}
        @return: a copy of the multiaction, optionally substituted
        @rtype: C{MultiAction}
        """
        result = self.__class__(act.copy() for act in self._actions)
        if subst is not None :
            result.substitute(subst)
        return result
    def __contains__ (self, action) :
        """Search an action in the multiaction.

        The searched action may be a complete C{Action}, just an
        action name, or a pair C{(name, send_flag)}.

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
        @type action: C{Action} or C{str} or C{tuple(str, bool)}
        @return: C{True} if the specified action was found, C{False}
          otherwise
        @rtype: C{bool}
        """
        if isinstance(action, Action) :
            return action in self._actions
        elif isinstance(action, tuple) and len(action) == 2 :
            return (action[0] in self._sndrcv
                    and self._sndrcv[action[0]] == action[1])
        elif isinstance(action, str) :
            return action in self._count
        else :
            raise ValueError, "invalid action specification"
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
        @type other: C{MultiAction} or C{Action}
        @return: the concatenated multiaction
        @rtype: C{MultiAction}
        """
        if isinstance(other, Action) :
            other = self.__class__([other])
        result = self.copy()
        for action in other._actions :
            result.add(action)
        return result
    def __sub__ (self, other) :
        """Create a multiaction by substracting the actions of two others.

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
        @type other: C{MultiAction} or C{Action}
        @return: the resulting multiaction
        @rtype: C{MultiAction}
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
        @rtype: C{set} of C{str}
        """
        result = set()
        for action in self._actions :
            result.update(action.vars())
        return result
    def synchronise (self, other, name) :
        """Search all the possible synchronisation on an action name
        with another multiaction.

        This method returns an iterator that yields for each possible
        synchronisation a 4-tuple whose components are:

        1. The sending action that did synchronise, it is already
           unified, so the corresponding receiving action is just the
           same with the reversed send flag.

        2. The multiaction resulting from the synchronisation that is
           also unified.

        3. The substitution that must be applied to the transition
           that provided the sending action.

        4. The substitution that must be applied to the transition
           that provided the receiving action.

        >>> m = MultiAction([Action('a', True, [Variable('x'), Value(2)]),
        ...                  Action('a', True, [Value(3), Variable('y')]),
        ...                  Action('b', False, [Variable('x'), Variable('y')])])
        >>> n = MultiAction([Action('a', False, [Variable('w'), Variable('y')]),
        ...                  Action('c', False, [Variable('y')])])
        >>> for a, x, u, v in m.synchronise(n, 'a') :
        ...    print str(a), str(x), list(sorted(u.items())), list(sorted(v.items()))
        a!(w,2) [a!(3,y), b?(w,y), c?(a)] [('a', Value(2)), ('x', Variable('w'))] [('a', Value(2)), ('x', Variable('w')), ('y', Variable('a'))]
        a!(3,a) [a!(x,2), b?(x,a), c?(a)] [('w', Value(3)), ('y', Variable('a'))] [('w', Value(3)), ('y', Variable('a'))]

        @param other: the other multiaction to synchronise with
        @type other: C{MultiAction}
        @param name: the name of the action to synchronise on
        @type name: C{str}
        @return: an iterator over the possible synchronisations
        @rtype: iterator of C{tuple(Action, MultiAction, Substitution, Substitution)}
        """
        renamer = Substitution()
        common = self.vars() & other.vars()
        if len(common) > 0 :
            names = WordSet(common)
            for var in common :
                renamer += Substitution({var : Variable(names.fresh(add=True))})
        for left in (act for act in self._actions if act.name == name) :
            for right in (act for act in other._actions if act.name == name
                          if act.send != left.send) :
                _right = right.copy(renamer)
                try :
                    unifier = left & _right
                except :
                    continue
                _unifier = unifier * renamer
                _self = self - left
                _self.substitute(unifier)
                _other = other - right
                _other.substitute(_unifier)
                yield left.copy(unifier), _self + _other, unifier, _unifier

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    class Transition (module.Transition) :
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
                <variable>
                 x
                </variable>
               </action>
               <action name="b" send="False">
                <variable>
                 y
                </variable>
                <value>
                 <object type="int">
                  2
                 </object>
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
                            new = _snd.actions.synchronise(_rcv.actions, name)
                        except ConstraintError :
                            continue
                        for a, m, s, r in new :
                            t = self._synchronise(_snd, s, _rcv, r, m, a)
                            if (name, True) in t.actions :
                                snd.append(t)
                                loop = True
                            elif (name, False) in t.actions :
                                rcv.append(t)
                                loop = True
                        done.add((_snd.name, _rcv.name))
        def _synchronise (self, snd, s, rcv, r, actions, sync) :
            collect = []
            varset = WordSet()
            for trans, subst in ((snd, s), (rcv, r)) :
                new = "%s%s" % (trans.name, str(subst))
                self.copy_transition(trans.name, new)
                collect.append(new)
                new = self.transition(new)
                nv = new.vars()
                for v in varset & nv :
                    new.substitute(Substitution({v : varset.fresh(add=True)}))
                varset.update(nv)
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
            merged = "(%s%s+%s%s)[%s]" % (snd.name, str(s), rcv.name, str(s),
                                          str(sync).replace("?", "").replace("!", ""))
            self.merge_transitions(merged, collect, actions=actions)
            for name in collect :
                self.remove_transition(name)
            return self.transition(merged)
        def restrict (self, action) :
            removed = [trans.name for trans in self.transition()
                       if action in trans.actions]
            for trans in removed :
                self.remove_transition(trans)
        def scope (self, action) :
            self.synchronise(action)
            self.restrict(action)
        def merge_transitions (self, target, sources, **args) :
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
