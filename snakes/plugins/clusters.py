"""
@todo: revise (actually make) documentation
"""

import snakes.plugins
from snakes.plugins import new_instance
from snakes.pnml import Tree
from snakes.data import iterate

class Cluster (object) :
    def __init__ (self, nodes=[], children=[]) :
        """
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
    def __str__ (self) :
        return "cluster_%s" % str(id(self)).replace("-", "m")
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
        """
        >>> Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])]).get_path('C')
        [1, 0]
        """
        if name in self._nodes :
            return []
        else :
            for num, child in enumerate(self._children) :
                if name in child :
                    return [num] + child.get_path(name)
    def add_node (self, name, path=None) :
        """
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
        """
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
        """
        if name in self._cluster :
            self._cluster[name].remove_node(name)
        else :
            self._nodes.remove(name)
    def rename_node (self, old, new) :
        """
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
        """
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
        """
        if cluster is None :
            cluster = Cluster()
        self._cluster.update(cluster._cluster)
        for node in cluster._nodes :
            self._cluster[node] = cluster
        self._children.append(cluster)
    def nodes (self, all=False) :
        """
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
        """
        if all :
            result = set()
            for cluster in self :
                result.update(cluster.nodes())
            return result
        else :
            return set(self._nodes)
    def children (self) :
        """
        >>> Cluster(['a', 'b'],
        ...         [Cluster(['1', '2'],
        ...                  [Cluster(['A'])]),
        ...          Cluster(['3', '4', '5'],
        ...                  [Cluster(['C', 'D'])])]).children()
        (Cluster(['...', '...'],
                 [Cluster(['A'], [])]),
         Cluster(['...', '...', '...'],
                 [Cluster(['...', '...'], [])]))
        """
        return tuple(self._children)
    def __contains__ (self, name) :
        """
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
        """
        if name in self._nodes :
            return True
        for child in self._children :
            if name in child :
                return True
        return False
    def __iter__ (self) :
        """
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
        def add_place (self, place, **options) :
            path = options.pop("cluster", None)
            module.PetriNet.add_place(self, place, **options)
            self.clusters.add_node(place.name, path)
        def remove_place (self, name, **options) :
            module.PetriNet.remove_place(self, name, **options)
            self.clusters.remove_node(name)
        def add_transition (self, trans, **options) :
            path = options.pop("cluster", None)
            module.PetriNet.add_transition(self, trans, **options)
            self.clusters.add_node(trans.name, path)
        def remove_transition (self, name, **options) :
            module.PetriNet.remove_transition(self, name, **options)
            self.clusters.remove_node(name)
        def rename_node (self, old, new, **options) :
            module.PetriNet.rename_node(self, old, new, **options)
            self.clusters.rename_node(old, new)
    return PetriNet, Cluster
