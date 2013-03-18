"""This plugin defines a data structure `Cluster` that allows to group
nodes hierarchically. This is used by plugin `gv` to improve the
graphical layout of Petri nets obtained using plugin `ops`.

In general, this plugin is probably not needed by anyone,
consequently, documentation will be very terse.
"""

import snakes.plugins
from snakes.plugins import new_instance
from snakes.pnml import Tree
from snakes.data import iterate

class Cluster (object) :
    """A hierarchical data structure to organise strings (intended to
    be node names).
    """
    def __init__ (self, nodes=[], children=[]) :
        """Create a cluster whose to-level nodes are `nodes` and with
        sub-clusters given in `children`.

        >>> Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])])
        Cluster(...)
        """
        self._nodes = set(nodes)
        self._children = []
        self._cluster = {}
        for child in children :
            self.add_child(child)
    __pnmltag__ = "clusters"
    # apidoc skip
    def __pnmldump__ (self) :
        """
        >>> Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])]).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>...
         <clusters>
          <node>
          ...
          </node>
          <node>
          ...
          </node>
          <clusters>
          ...
          </clusters>
         </clusters>
        </pnml>
        """
        result = Tree(self.__pnmltag__, None)
        for node in self._nodes :
            result.add_child(Tree("node", node))
        for child in self._children :
            result.add_child(Tree.from_obj(child))
        return result
    # apidoc skip
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> t = Cluster(['a', 'b'],
        ...             [Cluster(['1', '2'],
        ...                      [Cluster(['A'])]),
        ...              Cluster(['3', '4', '5'],
        ...                      [Cluster(['C', 'D'])])]).__pnmldump__()
        >>> Cluster.__pnmlload__(t)
        Cluster(['...', '...'],
                [Cluster(['...', '...'],
                         [Cluster(['A'], [])]),
                 Cluster(['...', '...', '...'],
                         [Cluster(['...', '...'], [])])])
        """

        result = cls()
        for child in tree.children :
            if child.name == "node" :
                result.add_node(child.data)
            else :
                result.add_child(child.to_obj())
        return result
    # apidoc skip
    def __str__ (self) :
        return "cluster_%s" % str(id(self)).replace("-", "m")
    # apidoc skip
    def __repr__ (self) :
        """
        >>> Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])])
        Cluster(['...', '...'],
                [Cluster(['...', '...'],
                         [Cluster(['A'], [])]),
                 Cluster(['...', '...', '...'],
                         [Cluster(['...', '...'], [])])])
        """
        return "%s([%s], [%s])" % (self.__class__.__name__,
                                   ", ".join(repr(n) for n in self.nodes()),
                                   ", ".join(repr(c) for c in self.children()))
    # apidoc skip
    def copy (self) :
        """
        >>> Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])]).copy()
        Cluster(['...', '...'],
                [Cluster(['...', '...'],
                         [Cluster(['A'], [])]),
                 Cluster(['...', '...', '...'],
                         [Cluster(['...', '...'], [])])])
        """
        return self.__class__(self._nodes,
                              (child.copy() for child in self._children))
    def get_path (self, name) :
        """Get the path of a name inside the cluster. This path is a
        list of indexes for each child-cluster within its parent.

        >>> Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])]).get_path('C')
        [1, 0]

        @param name: the searched name
        @type name: `str`
        @return: the list of indexes as `int` values
        @rtype: `list`
        """
        if name in self._nodes :
            return []
        else :
            for num, child in enumerate(self._children) :
                if name in child :
                    return [num] + child.get_path(name)
    def add_node (self, name, path=None) :
        """Add `name` to the cluster, optionally at a given position
        `path`.

        >>> c = Cluster(['a', 'b'],
        ...             [Cluster(['1', '2'],
        ...                      [Cluster(['A'])]),
        ...              Cluster(['3', '4', '5'],
        ...                      [Cluster(['C', 'D'])])])
        >>> c.add_node('c')
        Cluster([...'c'...], ...)
        >>> c.add_node('E', [1, 0])
        Cluster([...'E'...], [])
        >>> c
        Cluster([...'c'...],
                [Cluster(['...', '...'],
                         [Cluster(['A'], [])]),
                 Cluster(['...', '...', '...'],
                         [Cluster([...'E'...], [])])])

        @param name: name to add
        @type name: `str`
        @param path: position where `name`should be added, given as a
            list of indexes
        @type path: `list`
        """
        if path in (None, [], ()) :
            self._nodes.add(name)
            return self
        else :
            while len(self._children) <= path[0] :
                self._children.append(self.__class__())
            target = self._children[path[0]].add_node(name, path[1:])
            self._cluster[name] = target
            return target
    def remove_node (self, name) :
        """Remove a name from the cluster.

        >>> c = Cluster(['a', 'b'],
        ...             [Cluster(['1', '2'],
        ...                      [Cluster(['A'])]),
        ...              Cluster(['3', '4', '5'],
        ...                      [Cluster(['C', 'D'])])])
        >>> c.remove_node('4')
        >>> c
        Cluster(['...', '...'],
                [Cluster(['...', '...'],
                         [Cluster(['A'], [])]),
                 Cluster(['...', '...'],
                         [Cluster(['...', '...'], [])])])

        @param name: name to remove
        @type name: `str`
        """
        if name in self._cluster :
            self._cluster[name].remove_node(name)
        else :
            self._nodes.remove(name)
    def rename_node (self, old, new) :
        """Change a name in the cluster.

        >>> c = Cluster(['a', 'b'],
        ...             [Cluster(['1', '2'],
        ...                      [Cluster(['A'])]),
        ...              Cluster(['3', '4', '5'],
        ...                      [Cluster(['C', 'D'])])])
        >>> c.rename_node('4', '42')
        >>> c
        Cluster(['...', '...'],
                [Cluster(['...', '...'],
                         [Cluster(['A'], [])]),
                 Cluster([...'42'...],
                         [Cluster(['...', '...'], [])])])

        @param old: name to change
        @type old: `str`
        @param new: new name to replace `old`
        @type new: `str`
        """
        if old in self._cluster :
            self._cluster[old].rename_node(old, new)
            self._cluster[new] = self._cluster[old]
            del self._cluster[old]
        elif old in self._nodes :
            self._nodes.remove(old)
            self._nodes.add(new)
        else :
            for child in self.children() :
                child.rename_node(old, new)
    def add_child (self, cluster=None) :
        """Add a child cluster

        >>> c = Cluster(['a', 'b'],
        ...             [Cluster(['1', '2'],
        ...                      [Cluster(['A'])]),
        ...              Cluster(['3', '4', '5'],
        ...                      [Cluster(['C', 'D'])])])
        >>> c.add_child(c.copy())
        >>> c
        Cluster(['...', '...'],
                [Cluster(['...', '...'],
                         [Cluster(['A'], [])]),
                 Cluster(['...', '...', '...'],
                         [Cluster(['...', '...'], [])]),
                 Cluster(['...', '...'],
                         [Cluster(['...', '...'],
                                  [Cluster(['A'], [])]),
                          Cluster(['...', '...', '...'],
                                  [Cluster(['...', '...'], [])])])])

        @param cluster: the new child, if `None` is given, an empty
            child is added
        @type cluster: `Cluster`
        """
        if cluster is None :
            cluster = Cluster()
        self._cluster.update(cluster._cluster)
        for node in cluster._nodes :
            self._cluster[node] = cluster
        self._children.append(cluster)
    def nodes (self, all=False) :
        """Returns the nodes in the cluster: only the top-level ones
        is `all` is `False`, or all the nodes otherwise.

        >>> list(sorted(Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])]).nodes()))
        ['a', 'b']
        >>> list(sorted(Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])]).nodes(True)))
        ['1', '2', '3', '4', '5', 'A', 'C', 'D', 'a', 'b']

        @param all: whether all the nodes should be returned or only
            the top-level ones
        @type all: `bool`
        @return: list of nodes
        @rtype: `list`
        """
        if all :
            result = set()
            for cluster in self :
                result.update(cluster.nodes())
            return result
        else :
            return set(self._nodes)
    def children (self) :
        """Return the children of the cluster.

        >>> Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])]).children()
        (Cluster(['...', '...'],
                 [Cluster(['A'], [])]),
         Cluster(['...', '...', '...'],
                 [Cluster(['...', '...'], [])]))

        @return: the children of `self`
        @rtype: `tuple`
        """
        return tuple(self._children)
    def __contains__ (self, name) :
        """Test if a name is in the cluster.

        >>> c = Cluster(['a', 'b'],
        ...             [Cluster(['1', '2'],
        ...                      [Cluster(['A'])]),
        ...              Cluster(['3', '4', '5'],
        ...                      [Cluster(['C', 'D'])])])
        >>> 'a' in c
        True
        >>> 'x' in c
        False
        >>> '4' in c
        True

        @param name: the node to test
        @type name: `str`
        @return: whether `name` is in the cluster
        @rtype: `bool`
        """
        if name in self._nodes :
            return True
        for child in self._children :
            if name in child :
                return True
        return False
    def __iter__ (self) :
        """Iterate over the clusters and its children, yielding lists
        of nodes at each level.

        >>> c = Cluster(['a', 'b'],
        ...             [Cluster(['1', '2'],
        ...                      [Cluster(['A'])]),
        ...              Cluster(['3', '4', '5'],
        ...                      [Cluster(['C', 'D'])])])
        >>> for cluster in c :
        ...    print(list(sorted(cluster.nodes())))
        ['a', 'b']
        ['1', '2']
        ['A']
        ['3', '4', '5']
        ['C', 'D']
        """
        yield self
        for child in self._children :
            for item in child :
                yield item

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    class PetriNet (module.PetriNet) :
        """Class `PetriNet`is extended so that instances have an
        attribute `clusters` to which the nodes are added.
        """
        def add_place (self, place, **options) :
            """
            @param place: the place to add
            @type place: `Place`
            @param options: additional options for plugins
            @keyword cluster: position of the new place in the cluster
            """
            path = options.pop("cluster", None)
            module.PetriNet.add_place(self, place, **options)
            self.clusters.add_node(place.name, path)
        def add_transition (self, trans, **options) :
            """
            @param trans: the transition to add
            @type trans: `Transition`
            @param options: additional options for plugins
            @keyword cluster: position of the new transition in the
                cluster
            """
            path = options.pop("cluster", None)
            module.PetriNet.add_transition(self, trans, **options)
            self.clusters.add_node(trans.name, path)
        # apidoc stop
        def __init__ (self, name, **options) :
            module.PetriNet.__init__(self, name, **options)
            self.clusters = Cluster()
        def copy (self, name=None, **options) :
            result = module.PetriNet.copy(self, name, **options)
            result.clusters = self.clusters.copy()
            return result
        def __pnmldump__ (self) :
            result = module.PetriNet.__pnmldump__(self)
            result.add_child(Tree.from_obj(self.clusters))
            return result
        @classmethod
        def __pnmlload__ (cls, tree) :
            result = new_instance(cls, module.PetriNet.__pnmlload__(tree))
            result.clusters = tree.child(Cluster.__pnmltag__).to_obj()
            return result
        def remove_place (self, name, **options) :
            module.PetriNet.remove_place(self, name, **options)
            self.clusters.remove_node(name)
        def remove_transition (self, name, **options) :
            module.PetriNet.remove_transition(self, name, **options)
            self.clusters.remove_node(name)
        def rename_node (self, old, new, **options) :
            module.PetriNet.rename_node(self, old, new, **options)
            self.clusters.rename_node(old, new)
    return PetriNet, Cluster
