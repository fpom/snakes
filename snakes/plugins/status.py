"""A plugin to add nodes status.

Several status are defined by default: C{entry}, C{internal}, C{exit},
C{buffer}, C{safebuffer} for places and {tick} for transitions.

>>> import snakes.plugins
>>> snakes.plugins.load('status', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> import snakes.plugins.status as status
>>> n = PetriNet('N')
>>> n.add_place(Place('p1'), status=status.entry)
>>> n.place('p1')
Place('p1', MultiSet([]), tAll, status=Status('entry'))
"""

import operator, weakref
import snakes.plugins
from snakes.plugins import new_instance
from snakes import ConstraintError
from snakes.data import iterate
from snakes.pnml import Tree

class Status (object) :
    "The status of a node"
    def __init__ (self, name, value=None) :
        """Initialize with a status name and an optional value

        @param name: the name of the status
        @type name: C{str}
        @param value: an optional additional value to make a
        difference between status with te same name
        @type value: hashable
        """
        self._name = name
        self._value = value
    __pnmltag__ = "status"
    def __pnmldump__ (self) :
        """Dump a C{Status} as a PNML tree

        @return: PNML tree
        @rtype: C{pnml.Tree}

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
    @classmethod
    def __pnmlload__ (cls, tree) :
        """Create a C{Status} from a PNML tree

        @param tree: the tree to convert
        @type tree: C{pnml.Tree}
        @return: the status built
        @rtype: C{Status}

        >>> t = Status('foo', 42).__pnmldump__()
        >>> Status.__pnmlload__(t)
        Status('foo',42)
        """
        return cls(tree.child("name").data,
                   tree.child("value").child().to_obj())
    def copy (self) :
        """Return a copy of the status

        A status is normally never muted, so this may be useless,
        unless the user decides to store additional data in status.

        @return: a copy of the status
        @rtype: C{Status}
        """
        return self.__class__(self._name, self._value)
    def __str__ (self) :
        """Short textual representation

        >>> str(internal)
        'internal'
        >>> str(buffer('buf'))
        'buffer(buf)'

        @return: a textual representation
        @rtype: C{str}
        """
        if self._value is None :
            return str(self._name)
        else :
            return "%s(%s)" % (self._name, self._value)
    def __repr__ (self) :
        """Detailed textual representation

        >>> repr(internal)
        "Status('internal')"
        >>> repr(buffer('buf'))
        "Buffer('buffer','buf')"

        @return: a textual representation suitable for C{eval}
        @rtype: C{str}
        """
        if self._value is None :
            return "%s(%s)" % (self.__class__.__name__, repr(self._name))
        else :
            return "%s(%s,%s)" % (self.__class__.__name__,
                                  repr(self._name), repr(self._value))
    def __hash__ (self) :
        """Hash a status

        @return: the hash value
        @rtype: C{int}
        """
        return hash((self._name, self._value))
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
        @type other: C{Status}
        @return: C{True} is they are equal, C{False} otherwise
        @rtype: C{bool}
        """
        try :
            return (self._name, self._value) == (other._name, other._value)
        except :
            return False
    def __ne__ (self, other) :
        return not(self == other)
    def __add__ (self, other) :
        if self == other :
            return self.copy()
        else :
            raise ConstraintError, "incompatible status"
    def name (self) :
        return self._name
    def value (self) :
        return self._value
    def merge (self, net, nodes, name=None) :
        """Merge C{nodes} in C{net} into a new node called C{name}

        This does nothing by default, other status will refine this
        method. Merged nodes are removed, only the newly created one
        remains.

        @param net: the Petri net where nodes should be merged
        @type net: C{PetriNet}
        @param nodes: a collection of node names to be merged
        @type nodes: iterable of C{str}
        @param name: the name of the new node or C{Node} if it should
          be generated
        @type name: C{str}
        """
        pass

entry = Status('entry')
exit = Status('exit')
internal = Status('internal')

class Buffer (Status) :
    "A status for buffer places"
    def merge (self, net, nodes, name=None) :
        """Merge C{nodes} in C{net}

        Buffer places with the status status C{Buffer('buffer', None)}
        are not merged. Other buffer places are merged exactly has
        C{PetriNet.merge_places} does.

        If C{name} is C{None} the name generated is a concatenation of
        the nodes names separated by '+', with parenthesis outside.

        >>> import snakes.plugins
        >>> snakes.plugins.load('status', 'snakes.nets', 'nets')
        <module ...>
        >>> from nets import *
        >>> n = PetriNet('N')
        >>> import snakes.plugins.status as status
        >>> buf = status.buffer('buf')
        >>> n.add_place(Place('p3', range(2), status=buf))
        >>> n.add_place(Place('p4', range(3), status=buf))
        >>> n.status.merge(buf, 'b')
        >>> p = n.place('b')
        >>> p
        Place('b', MultiSet([...]), tAll, status=Buffer('buffer','buf'))
        >>> p.tokens == MultiSet([0, 0, 1, 1, 2])
        True

        @param net: the Petri net where places should be merged
        @type net: C{PetriNet}
        @param nodes: a collection of place names to be merged
        @type nodes: iterable of C{str}
        @param name: the name of the new place or C{Node} if it should
          be generated
        @type name: C{str}
        """
        if self._value is None :
            return
        if name is None :
            name = "(%s)" % "+".join(sorted(nodes))
        net.merge_places(name, nodes, status=self)
        for src in nodes :
            net.remove_place(src)

def buffer (name) :
    """Generate a buffer status called C{name}

    @param name: the name of the buffer
    @type name: C{str}
    @return: C{Buffer('buffer', name)}
    @rtype: C{Buffer}
    """
    return Buffer('buffer', name)

class Safebuffer (Buffer) :
    "A status for safe buffers (ie, variables) places"
    def merge (self, net, nodes, name=None) :
        """Merge C{nodes} in C{net}

        Safe buffers places with the status C{Safebuffer('safebuffer',
        None)} are not merged. Other safe buffers places are merged if
        they all have the same marking, which becomes the marking of
        the resulting place. Otherwise, C{ConstraintError} is raised.

        If C{name} is C{None} the name generated is a concatenation of
        the nodes names separated by '+', with parenthesis outside.

        >>> import snakes.plugins
        >>> snakes.plugins.load('status', 'snakes.nets', 'nets')
        <module ...>
        >>> from nets import *
        >>> import snakes.plugins.status as status
        >>> n = PetriNet('N')
        >>> var = status.safebuffer('var')
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

        @param net: the Petri net where places should be merged
        @type net: C{PetriNet}
        @param nodes: a collection of place names to be merged
        @type nodes: iterable of C{str}
        @param name: the name of the new place or C{Node} if it should
          be generated
        @type name: C{str}
        """
        if self._value is None :
            return
        marking = net.place(nodes[0]).tokens
        for node in nodes[1:] :
            if net.place(node).tokens != marking :
                raise ConstraintError, "incompatible markings"
        if name is None :
            name = "(%s)" % "+".join(sorted(nodes))
        net.merge_places(name, nodes, status=self)
        for src in nodes :
            net.remove_place(src)
        net.set_status(name, self)
        net.place(name).reset(marking)

def safebuffer (name) :
    """Generate a safebuffer status called C{name}

    @param name: the name of the safebuffer
    @type name: C{str}
    @return: C{Safebuffer('safebuffer', name)}
    @rtype: C{Safebuffer}
    """
    return Safebuffer('safebuffer', name)

class Tick (Status) :
    "A status for tick transition"
    def merge (self, net, nodes, name=None) :
        """Merge C{nodes} in C{net}

        Tick transitions are merged exactly as
        C{PetriNet.merge_transitions} does.

        If C{name} is C{None} the name generated is a concatenation of
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
        @type net: C{PetriNet}
        @param nodes: a collection of transition names to be merged
        @type nodes: iterable of C{str}
        @param name: the name of the new transition or C{Node} if it
          should be generated
        @type name: C{str}
        """
        if self._value is None :
            return
        if name is None :
            name = "(%s)" % "+".join(nodes)
        net.merge_transitions(name, nodes, status=self)
        for src in nodes :
            net.remove_transition(src)

def tick (name) :
    """Generate a tick status called C{name}

    @param name: the name of the tick
    @type name: C{str}
    @return: C{Tick('tick', name)}
    @rtype: C{Tick}
    """
    return Tick('tick', name)

class StatusDict (object) :
    "A container to access the nodes of a net by their status"
    def __init__ (self, net) :
        """
        @param net: the Petri net for which nodes will be recorded
        @type net: C{PetriNet}
        """
        self._nodes = {}
        self._net = weakref.ref(net)
    def copy (self, net=None) :
        """
        @param net: the Petri net for which nodes will be recorded
          (C{None} if it is the same as the copied object)
        @type net: C{PetriNet}
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
        """Called when C{node} is added to the net

        @param node: the added node
        @type node: C{Node}
        """
        if node.status not in self._nodes :
            self._nodes[node.status] = set([node.name])
        else :
            self._nodes[node.status].add(node.name)
    def remove (self, node) :
        """Called when C{node} is removed from the net

        @param node: the added node
        @type node: C{Node}
        """
        if node.status in self._nodes :
            self._nodes[node.status].discard(node.name)
            if len(self._nodes[node.status]) == 0 :
                del self._nodes[node.status]
    def __call__ (self, status) :
        """Return the nodes having C{status}

        @param status: the searched status
        @type status: C{Status}
        @return: the node names in the net having this status
        @rtype: C{tuple} of C{str}
        """
        return tuple(self._nodes.get(status, tuple()))
    def merge (self, status, name=None) :
        """Merge the nodes in the net having C{status}

        This is a shortcut to call C{status.merge} with the right
        parameters.

        @param status: the status for which nodes have to be merged
        """
        if status :
            nodes = self(status)
            if len(nodes) > 1 :
                status.merge(self._net(), nodes, name)

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    "Build the extended module"
    class Place (module.Place) :
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
        def __init__ (self, name, **args) :
            module.PetriNet.__init__(self, name, **args)
            self.status = StatusDict(self)
        @classmethod
        def __pnmlload__ (cls, tree) :
            t = new_instance(cls, module.PetriNet.__pnmlload__(tree))
            t.status = StatusDict(t)
            return t
        def copy (self, name=None, **args) :
            result = module.PetriNet.copy(self, name, **args)
            result.status = self.status.copy(result)
            return result
        def add_place (self, place, **args) :
            place.status = args.pop("status", place.status)
            module.PetriNet.add_place(self, place, **args)
            self.status.record(place)
        def remove_place (self, name, **args) :
            place = self.place(name)
            self.status.remove(place)
            module.PetriNet.remove_place(self, name, **args)
        def add_transition (self, trans, **args) :
            trans.status = args.pop("status", trans.status)
            module.PetriNet.add_transition(self, trans, **args)
            self.status.record(trans)
        def remove_transition (self, name, **args) :
            trans = self.transition(name)
            self.status.remove(trans)
            module.PetriNet.remove_transition(self, name, **args)
        def set_status (self, node, status) :
            node = self.node(node)
            self.status.remove(node)
            node.status = status
            self.status.record(node)
        def rename_node (self, old, new, **args) :
            old_node = self.node(old).copy()
            module.PetriNet.rename_node(self, old, new, **args)
            self.status.remove(old_node)
            self.status.record(self.node(new))
        def copy_place (self, source, targets, **args) :
            status = args.pop("status", self.place(source).status)
            module.PetriNet.copy_place(self, source, targets, **args)
            for new in iterate(targets) :
                self.set_status(new, status)
        def copy_transition (self, source, targets, **args) :
            status = args.pop("status", self.transition(source).status)
            module.PetriNet.copy_transition(self, source, targets, **args)
            for new in iterate(targets) :
                self.set_status(new, status)
        def merge_places (self, target, sources, **args) :
            if "status" in args :
                status = args.pop("status")
            else :
                status = reduce(operator.add,
                                (self.place(s).status for s in sources))
            module.PetriNet.merge_places(self, target, sources, **args)
            self.set_status(target, status)
        def merge_transitions (self, target, sources, **args) :
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
