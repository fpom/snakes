#-*- coding: latin-1
"""Add statuses to nodes: a status is a special kind of label that is
used to define Petri nets compositions _à la_ Petri Box Calculus. See
plugin `ops` to read more about how statuses are used in practice.

Several status are defined by default: `entry`, `internal`, `exit`,
`buffer`, `safebuffer` for places and `tick` for transitions.
Internally, a status is an instance of class `Status` or one of its
subclasses that is identified by a name and an optional value. For
instance the plugin defines:

    :::python
    entry = Status('entry')
    exit = Status('exit')
    internal = Status('internal')

The second parameter is omitted which means that there is no value for
these status. Buffer places have both a name and a value for their
status: the name is `'buffer'` and the value is used as the name of
the buffer.

Status can be added to nodes either when they are created or when they
are added to the net:

>>> import snakes.plugins
>>> snakes.plugins.load('status', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> n = PetriNet('N')
>>> n.add_place(Place('p1'), status=entry)
>>> n.place('p1')
Place('p1', MultiSet([]), tAll, status=Status('entry'))
>>> n.add_place(Place('p2', status=exit))
>>> n.place('p2')
Place('p2', MultiSet([]), tAll, status=Status('exit'))
"""

import operator, weakref
import snakes.plugins
from snakes import ConstraintError
from snakes.plugins import new_instance
from snakes.compat import *
from snakes.data import iterate
from snakes.pnml import Tree

class Status (object) :
    "The status of a node"
    def __init__ (self, name, value=None) :
        """Initialize with a status name and an optional value

        @param name: the name of the status
        @type name: `str`
        @param value: an optional additional value to make a
            difference between status with te same name
        @type value: `hashable`
        """
        self._name = name
        self._value = value
    __pnmltag__ = "status"
    # apidoc skip
    def __pnmldump__ (self) :
        """Dump a `Status` as a PNML tree

        @return: PNML tree
        @rtype: `pnml.Tree`

        >>> Status('foo', 42).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>...
         <status>
          <name>
           foo
          </name>
          <value>
           <object type="int">
            42
           </object>
          </value>
         </status>
        </pnml>
        """
        return Tree(self.__pnmltag__, None,
                    Tree("name", self._name),
                    Tree("value", None, Tree.from_obj(self._value)))
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create a `Status` from a PNML tree

        >>> t = Status('foo', 42).__pnmldump__()
        >>> Status.__pnmlload__(t)
        Status('foo',42)

        @param tree: the tree to convert
        @type tree: `pnml.Tree`
        @return: the status built
        @rtype: `Status`
        """
        return cls(tree.child("name").data,
                   tree.child("value").child().to_obj())
    # apidoc skip
    def copy (self) :
        """Return a copy of the status

        A status is normally never muted, so this may be useless,
        unless the user decides to store additional data in status.

        @return: a copy of the status
        @rtype: `Status`
        """
        return self.__class__(self._name, self._value)
    # apidoc skip
    def __str__ (self) :
        """Short textual representation

        >>> str(internal)
        'internal'
        >>> str(buffer('buf'))
        'buffer(buf)'

        @return: a textual representation
        @rtype: `str`
        """
        if self._value is None :
            return str(self._name)
        else :
            return "%s(%s)" % (self._name, self._value)
    # apidoc skip
    def __repr__ (self) :
        """Detailed textual representation

        >>> repr(internal)
        "Status('internal')"
        >>> repr(buffer('buf'))
        "Buffer('buffer','buf')"

        @return: a textual representation suitable for `eval`
        @rtype: `str`
        """
        if self._value is None :
            return "%s(%s)" % (self.__class__.__name__, repr(self._name))
        else :
            return "%s(%s,%s)" % (self.__class__.__name__,
                                  repr(self._name), repr(self._value))
    # apidoc skip
    def __hash__ (self) :
        """Hash a status

        @return: the hash value
        @rtype: `int`
        """
        return hash((self._name, self._value))
    # apidoc skip
    def __eq__ (self, other) :
        """Compares two status for equality

        They are equal if they have the same name and value

        >>> internal == Status('internal')
        True
        >>> Status('a', 1) == Status('a', 2)
        False
        >>> Status('a', 1) == Status('b', 1)
        False

        @param other: a status
        @type other: `Status`
        @return: `True` is they are equal, `False` otherwise
        @rtype: `bool`
        """
        try :
            return (self._name, self._value) == (other._name, other._value)
        except :
            return False
    # apidoc skip
    def __ne__ (self, other) :
        return not(self == other)
    # apidoc skip
    def __add__ (self, other) :
        if self == other :
            return self.copy()
        else :
            raise ConstraintError("incompatible status")
    # apidoc skip
    def name (self) :
        return self._name
    # apidoc skip
    def value (self) :
        return self._value
    # apidoc skip
    def merge (self, net, nodes, name=None) :
        """Merge `nodes` in `net` into a new node called `name`

        This does nothing by default, other status will refine this
        method. Merged nodes are removed, only the newly created one
        remains.

        @param net: the Petri net where nodes should be merged
        @type net: `PetriNet`
        @param nodes: a collection of node names to be merged
        @type nodes: iterable of `str`
        @param name: the name of the new node or `Node` if it should
            be generated
        @type name: `str`
        """
        pass

entry = Status('entry')
exit = Status('exit')
internal = Status('internal')

class Buffer (Status) :
    """Status for buffer places, it can be used to merge all the nodes
    with the same buffer name. For example:

    >>> import snakes.plugins
    >>> snakes.plugins.load('status', 'snakes.nets', 'nets')
    <module ...>
    >>> from nets import *
    >>> n = PetriNet('N')
    >>> n.add_place(Place('p3', range(2), status=buffer('buf')))
    >>> n.add_place(Place('p4', range(3), status=buffer('buf')))
    >>> n.status.merge(buffer('buf'), 'b')
    >>> p = n.place('b')
    >>> p
    Place('b', MultiSet([...]), tAll, status=Buffer('buffer','buf'))
    >>> p.tokens == MultiSet([0, 0, 1, 1, 2])
    True
    """
    # apidoc skip
    def merge (self, net, nodes, name=None) :
        """Merge `nodes` in `net`

        Buffer places with the status status `Buffer('buffer', None)`
        are not merged. Other buffer places are merged exactly has
        `PetriNet.merge_places` does.

        If `name` is `None` the name generated is a concatenation of
        the nodes names separated by '+', with parenthesis outside.

        @param net: the Petri net where places should be merged
        @type net: `PetriNet`
        @param nodes: a collection of place names to be merged
        @type nodes: iterable of `str`
        @param name: the name of the new place or `Node` if it should
            be generated
        @type name: `str`
        """
        if self._value is None :
            return
        if name is None :
            name = "(%s)" % "+".join(sorted(nodes))
        net.merge_places(name, nodes, status=self)
        for src in nodes :
            net.remove_place(src)

def buffer (name) :
    """Generate a buffer status called `name`

    >>> buffer('foo')
    Buffer('buffer','foo')

    @param name: the name of the buffer
    @type name: `str`
    @return: `Buffer('buffer', name)`
    @rtype: `Buffer`
    """
    return Buffer('buffer', name)

class Safebuffer (Buffer) :
    """A status for safe buffers (ie, variables) places. The only
    difference with `Buffer` status is that when buffer places with
    `SafeBuffer` status are merged, they must have all the same
    marking which also becomes the marking of the resulting place
    (instead of adding the markings of the merged places).

    >>> import snakes.plugins
    >>> snakes.plugins.load('status', 'snakes.nets', 'nets')
    <module ...>
    >>> from nets import *
    >>> n = PetriNet('N')
    >>> var = safebuffer('var')
    >>> n.add_place(Place('p5', [1], status=var))
    >>> n.add_place(Place('p6', [1], status=var))
    >>> n.add_place(Place('p7', [1], status=var))
    >>> n.status.merge(var, 'v')
    >>> n.place('v')
    Place('v', MultiSet([1]), tAll, status=Safebuffer('safebuffer','var'))
    >>> n.add_place(Place('p8', [3], status=var))
    >>> n.status.merge(var, 'vv')
    Traceback (most recent call last):
      ...
    ConstraintError: incompatible markings
    """
    # apidoc skip
    def merge (self, net, nodes, name=None) :
        """Merge `nodes` in `net`

        Safe buffers places with the status `Safebuffer('safebuffer',
        None)` are not merged. Other safe buffers places are merged if
        they all have the same marking, which becomes the marking of
        the resulting place. Otherwise, `ConstraintError` is raised.

        If `name` is `None` the name generated is a concatenation of
        the nodes names separated by '+', with parenthesis outside.

        @param net: the Petri net where places should be merged
        @type net: `PetriNet`
        @param nodes: a collection of place names to be merged
        @type nodes: iterable of `str`
        @param name: the name of the new place or `Node` if it should
          be generated
        @type name: `str`
        """
        if self._value is None :
            return
        marking = net.place(nodes[0]).tokens
        for node in nodes[1:] :
            if net.place(node).tokens != marking :
                raise ConstraintError("incompatible markings")
        if name is None :
            name = "(%s)" % "+".join(sorted(nodes))
        net.merge_places(name, nodes, status=self)
        for src in nodes :
            net.remove_place(src)
        net.set_status(name, self)
        net.place(name).reset(marking)

def safebuffer (name) :
    """Generate a safebuffer status called `name`

    >>> safebuffer('foo')
    Safebuffer('safebuffer','foo')

    @param name: the name of the safebuffer
    @type name: `str`
    @return: `Safebuffer('safebuffer', name)`
    @rtype: `Safebuffer`
    """
    return Safebuffer('safebuffer', name)

class Tick (Status) :
    """A status for tick transition. Ticks are to transitions what
    buffers are to places: they allow automatic merging of transitions
    with the same tick status when nets are composed. This is used to
    implement variants of the Petri Box Calculus with causal time.
    When transitions are merged, their guards are `and`-ed.
    """
    # apidoc skip
    def merge (self, net, nodes, name=None) :
        """Merge `nodes` in `net`

        Tick transitions are merged exactly as
        `PetriNet.merge_transitions` does.

        If `name` is `None` the name generated is a concatenation of
        the nodes names separated by '+', with parenthesis outside.

        >>> import snakes.plugins
        >>> snakes.plugins.load('status', 'snakes.nets', 'nets')
        <module ...>
        >>> from nets import *
        >>> import snakes.plugins.status as status
        >>> n = PetriNet('N')
        >>> tick = status.tick('tick')
        >>> n.add_transition(Transition('t1', Expression('x==1'), status=tick))
        >>> n.add_transition(Transition('t2', Expression('y==2'), status=tick))
        >>> n.add_transition(Transition('t3', Expression('z==3'), status=tick))
        >>> n.status.merge(tick, 't')
        >>> n.transition('t')
        Transition('t', Expression('((...) and (...)) and (...)'), status=Tick('tick','tick'))

        @param net: the Petri net where transitions should be merged
        @type net: `PetriNet`
        @param nodes: a collection of transition names to be merged
        @type nodes: iterable of `str`
        @param name: the name of the new transition or `Node` if it
          should be generated
        @type name: `str`
        """
        if self._value is None :
            return
        if name is None :
            name = "(%s)" % "+".join(nodes)
        net.merge_transitions(name, nodes, status=self)
        for src in nodes :
            net.remove_transition(src)

def tick (name) :
    """Generate a tick status called `name`

    >>> tick('spam')
    Tick('tick','spam')

    @param name: the name of the tick
    @type name: `str`
    @return: `Tick('tick', name)`
    @rtype: `Tick`
    """
    return Tick('tick', name)

# apidoc skip
class StatusDict (object) :
    "A container to access the nodes of a net by their status"
    def __init__ (self, net) :
        """
        @param net: the Petri net for which nodes will be recorded
        @type net: `PetriNet`
        """
        self._nodes = {}
        self._net = weakref.ref(net)
    def copy (self, net=None) :
        """
        @param net: the Petri net for which nodes will be recorded
          (`None` if it is the same as the copied object)
        @type net: `PetriNet`
        """
        if net is None :
            net = self._net()
        result = self.__class__(net)
        for status in self._nodes :
            result._nodes[status.copy()] = self._nodes[status].copy()
        return result
    def __iter__ (self) :
        return iter(self._nodes)
    def record (self, node) :
        """Called when `node` is added to the net

        @param node: the added node
        @type node: `Node`
        """
        if node.status not in self._nodes :
            self._nodes[node.status] = set([node.name])
        else :
            self._nodes[node.status].add(node.name)
    def remove (self, node) :
        """Called when `node` is removed from the net

        @param node: the added node
        @type node: `Node`
        """
        if node.status in self._nodes :
            self._nodes[node.status].discard(node.name)
            if len(self._nodes[node.status]) == 0 :
                del self._nodes[node.status]
    def __call__ (self, status) :
        """Return the nodes having `status`

        @param status: the searched status
        @type status: `Status`
        @return: the node names in the net having this status
        @rtype: `tuple` of `str`
        """
        return tuple(self._nodes.get(status, tuple()))
    def merge (self, status, name=None) :
        """Merge the nodes in the net having `status`

        This is a shortcut to call `status.merge` with the right
        parameters.

        @param status: the status for which nodes have to be merged
        """
        if status :
            nodes = self(status)
            if len(nodes) > 1 :
                status.merge(self._net(), nodes, name)

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    class Place (module.Place) :
        """`Place` is extended to allow `status` keyword argument in
        its constructor, which is later available as `status`
        attribute.
        """
        # apidoc stop
        def __init__ (self, name, tokens=[], check=None, **args) :
            self.status = args.pop("status", Status(None))
            module.Place.__init__(self, name, tokens, check, **args)
        def copy (self, name=None, **args) :
            result = module.Place.copy(self, name, **args)
            result.status = self.status.copy()
            return result
        def __repr__ (self) :
            if self.status == Status(None) :
                return module.Place.__repr__(self)
            else :
                return "%s, status=%s)" % (module.Place.__repr__(self)[:-1],
                                           repr(self.status))
        def __pnmldump__ (self) :
            """
            >>> p = Place('p', status=Status('foo', 42))
            >>> p.__pnmldump__()
            <?xml version="1.0" encoding="utf-8"?>
            <pnml>...
             <place id="p">
              <type domain="universal"/>
              <initialMarking>
               <multiset/>
              </initialMarking>
              <status>
               <name>
                foo
               </name>
               <value>
                <object type="int">
                 42
                </object>
               </value>
              </status>
             </place>
            </pnml>
            """
            t = module.Place.__pnmldump__(self)
            t.add_child(Tree.from_obj(self.status))
            return t
        @classmethod
        def __pnmlload__ (cls, tree) :
            """
            >>> t = Place('p', status=Status('foo', 42)).__pnmldump__()
            >>> Place.__pnmlload__(t).status
            Status('foo',42)
            """
            result = new_instance(cls, module.Place.__pnmlload__(tree))
            try :
                result.status = tree.child("status").to_obj()
            except SnakesError :
                result.status = Status(None)
            return result
    class Transition (module.Transition) :
        """`Transition` is extended to allow `status` keyword argument
        in its constructor, which is later available as `status`
        attribute.
        """
        # apidoc stop
        def __init__ (self, name, guard=None, **args) :
            self.status = args.pop("status", Status(None)).copy()
            module.Transition.__init__(self, name, guard, **args)
        def __pnmldump__ (self) :
            """
            >>> p = Transition('p', status=Status('foo', 42))
            >>> p.__pnmldump__()
            <?xml version="1.0" encoding="utf-8"?>
            <pnml>...
             <transition id="p">
              <status>
               <name>
                foo
               </name>
               <value>
                <object type="int">
                 42
                </object>
               </value>
              </status>
             </transition>
            </pnml>
            """
            t = module.Transition.__pnmldump__(self)
            t.add_child(Tree.from_obj(self.status))
            return t
        @classmethod
        def __pnmlload__ (cls, tree) :
            """
            >>> t = Transition('p', status=Status('foo', 42)).__pnmldump__()
            >>> Transition.__pnmlload__(t).status
            Status('foo',42)
            """
            result = new_instance(cls, module.Transition.__pnmlload__(tree))
            try :
                result.status = tree.child("status").to_obj()
            except SnakesError :
                result.status = Status(None)
            return result
        def copy (self, name=None, **args) :
            result = module.Transition.copy(self, name, **args)
            result.status = self.status.copy()
            return result
        def __repr__ (self) :
            if self.status == Status(None) :
                return module.Transition.__repr__(self)
            else :
                return "%s, status=%s)" % (module.Transition.__repr__(self)[:-1],
                                           repr(self.status))
    class PetriNet (module.PetriNet) :
        """`PetriNet` is extended to allow `status` keyword argument
        in several of its methods. An attributes `status` is also
        available to allow retreiving nodes (actually their names) by
        status or merge all the nodes with a given status.

        The exact way how merging is performed depends on the exact
        status: for exemple, as seen above, using `Buffer` or
        `Safebuffer` does not lead to merge place the same way.

        >>> import snakes.plugins
        >>> snakes.plugins.load('status', 'snakes.nets', 'nets')
        <module ...>
        >>> from nets import *
        >>> n = PetriNet('N')
        >>> n.add_place(Place('a', range(2), status=buffer('buf')))
        >>> n.add_place(Place('b', range(3), status=buffer('buf')))
        >>> n.add_place(Place('c', range(3), status=buffer('spam')))
        >>> list(sorted(n.status(buffer('buf'))))
        ['a', 'b']
        >>> n.status.merge(buffer('buf'), 'd')
        >>> list(sorted(n.status(buffer('buf'))))
        ['d']

        Note in this example how nodes merged by status are removed
        after being merge. This differs from the standard methods
        `PetriNet.merge_places` and `PetriNet.merge_transitions` that
        preserve the merged nodes and only add the new one.
        """
        # apidoc skip
        def __init__ (self, name, **args) :
            module.PetriNet.__init__(self, name, **args)
            self.status = StatusDict(self)
        # apidoc skip
        @classmethod
        def __pnmlload__ (cls, tree) :
            t = new_instance(cls, module.PetriNet.__pnmlload__(tree))
            t.status = StatusDict(t)
            return t
        # apidoc skip
        def copy (self, name=None, **args) :
            result = module.PetriNet.copy(self, name, **args)
            result.status = self.status.copy(result)
            return result
        def add_place (self, place, **args) :
            """Extended with `status` keyword argument.

            @keyword status: a status that is given to the node
            @type status: `Status`
            """
            place.status = args.pop("status", place.status)
            module.PetriNet.add_place(self, place, **args)
            self.status.record(place)
        # apidoc skip
        def remove_place (self, name, **args) :
            place = self.place(name)
            self.status.remove(place)
            module.PetriNet.remove_place(self, name, **args)
        def add_transition (self, trans, **args) :
            """Extended with `status` keyword argument.

            @keyword status: a status that is given to the node
            @type status: `Status`
            """
            trans.status = args.pop("status", trans.status)
            module.PetriNet.add_transition(self, trans, **args)
            self.status.record(trans)
        # apidoc skip
        def remove_transition (self, name, **args) :
            trans = self.transition(name)
            self.status.remove(trans)
            module.PetriNet.remove_transition(self, name, **args)
        def set_status (self, node, status) :
            """Assign a new status to a node.

            @param node: the name of the node
            @type node: `str`
            @param status: a status that is given to the node
            @type status: `Status`
            """
            node = self.node(node)
            self.status.remove(node)
            node.status = status
            self.status.record(node)
        # apidoc skip
        def rename_node (self, old, new, **args) :
            old_node = self.node(old).copy()
            module.PetriNet.rename_node(self, old, new, **args)
            self.status.remove(old_node)
            self.status.record(self.node(new))
        def copy_place (self, source, targets, **args) :
            """Extended with `status` keyword argument.

            @keyword status: a status that is given to the new node
            @type status: `Status`
            """
            status = args.pop("status", self.place(source).status)
            module.PetriNet.copy_place(self, source, targets, **args)
            for new in iterate(targets) :
                self.set_status(new, status)
        def copy_transition (self, source, targets, **args) :
            """Extended with `status` keyword argument.

            @keyword status: a status that is given to the new node
            @type status: `Status`
            """
            status = args.pop("status", self.transition(source).status)
            module.PetriNet.copy_transition(self, source, targets, **args)
            for new in iterate(targets) :
                self.set_status(new, status)
        def merge_places (self, target, sources, **args) :
            """Extended with `status` keyword argument.

            @keyword status: a status that is given to the new node
            @type status: `Status`
            """
            if "status" in args :
                status = args.pop("status")
            else :
                status = reduce(operator.add,
                                (self.place(s).status for s in sources))
            module.PetriNet.merge_places(self, target, sources, **args)
            self.set_status(target, status)
        def merge_transitions (self, target, sources, **args) :
            """Extended with `status` keyword argument.

            @keyword status: a status that is given to the new node
            @type status: `Status`
            """
            if "status" in args :
                status = args.pop("status")
            else :
                status = reduce(operator.add,
                                (self.place(s).status for s in sources))
            module.PetriNet.merge_transitions(self, target, sources, **args)
            self.set_status(target, status)
    return Place, Transition, PetriNet, Status, \
           ("entry", entry), ("exit", exit), ("internal", internal), \
           Buffer,  buffer, Safebuffer, safebuffer, Tick, tick
