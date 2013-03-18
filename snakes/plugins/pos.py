#-*- encoding: latin-1
"""A plugin to add positions to the nodes.

`Place` and `Transition` are added an optional argument for the
constructor `pos=(x,y)` to set their position. Moreover, these classes
are added an attribute `pos` that holds a pair of numbers with
attributes `x` and `y` and methods `shift(dx, dy)` and `moveto(x, y)`.
So, when the plugin is loaded, we can specify and retreive nodes
positions:

>>> import snakes.plugins
>>> snakes.plugins.load('pos', 'snakes.nets', 'nets')
<module ...>
>>> from nets import PetriNet, Place, Transition
>>> n = PetriNet('N')
>>> n.add_place(Place('p00'))
>>> t10 = Transition('t10', pos=(1, 0))
>>> n.add_transition(t10)
>>> n.add_place(Place('p11', pos=(1, 1)))
>>> n.add_transition(Transition('t01', pos=(0, 1)))
>>> t10.pos
Position(1, 0)
>>> t10.pos.x
1
>>> t10.pos.y
0
>>> t10.pos()
(1, 0)

Nodes positions is immutable, we must use method `moveto` to change
positions:

>>> t10.pos.y = 1
Traceback (most recent call last):
  ...
AttributeError: readonly attribute
>>> t10.pos.moveto(t10.pos.x, 1)
>>> t10.pos
Position(1, 1)

Petri nets are added methods `bbox()` that returns a pair of extrema
`((xmin, ymin), (xmax, ymax))`, a method `shift(dx, dy)` that shift
all the nodes, and a method `transpose()` that rotates the net in such
a way that the top-down direction becomes left-right:

>>> n.bbox()
((0, 0), (1, 1))
>>> n.shift(1, 2)
>>> n.bbox()
((1, 2), (2, 3))
>>> n.node('t01').copy().pos
Position(1, 3)
>>> n.transpose()
>>> n.node('t01').pos
Position(-3, 1)
"""

from snakes import SnakesError
from snakes.compat import *
from snakes.plugins import plugin, new_instance
from snakes.pnml import Tree

class Position (object) :
    "The position of a node"
    def __init__ (self, x, y) :
        """Constructor expects the Cartesian coordinates of the node,
        they can be provided as `float` or `int`.

        @param x: horizontal position
        @type x: `float`
        @param y: vertical position
        @type y: `float`
        """
        self.__dict__["x"] = x
        self.__dict__["y"] = y
    # apidoc skip
    def __str__ (self) :
        return "(%s, %s)" % (str(self.x), str(self.y))
    # apidoc skip
    def __repr__ (self) :
        return "Position(%s, %s)" % (str(self.x), str(self.y))
    # apidoc skip
    def __setattr__ (self, name, value) :
        if name in ("x", "y") :
            raise AttributeError("readonly attribute")
        else :
            self.__dict__[name] = value
    def moveto (self, x, y) :
        """Change current coordinates to the specified position

        @param x: horizontal position
        @type x: `float`
        @param y: vertical position
        @type y: `float`
        """
        self.__init__(x, y)
    def shift (self, dx, dy) :
        """Shift current coordinates by the specified amount.

        @param dx: horizontal shift
        @type dx: `float`
        @param dy: vertical shift
        @type dy: `float`
        """
        self.__init__(self.x + dx, self.y + dy)
    def __getitem__ (self, index) :
        """Access coordinates by index

        >>> Position(1, 2)[0]
        1
        >>> Position(1, 2)[1]
        2
        >>> Position(1, 2)[42]
        Traceback (most recent call last):
          ...
        IndexError: Position index out of range

        @param index: 0 for `x` coordinate, 1 for `y`
        @type index: `int`
        @raise IndexError: when `index not in {0, 1}`
        """
        if index == 0 :
            return self.x
        elif index == 1 :
            return self.y
        else :
            raise IndexError("Position index out of range")
    def __iter__ (self) :
        """Successively yield `x` and `y` coordinates

        >>> list(Position(1, 2))
        [1, 2]
        """
        yield self.x
        yield self.y
    def __call__ (self) :
        """Return the position as a pair of values

        >>> Position(1, 2.0)()
        (1, 2.0)

        @return: the pair of coordinates `(x, y)`
        @rtype: `tuple`
        """
        return (self.x, self.y)

@plugin("snakes.nets")
def extend (module) :
    class Place (module.Place) :
        def __init__ (self, name, tokens=[], check=None, **args) :
            """If no position is given `(0, 0)` is chosen

            >>> Place('p').pos
            Position(0, 0)
            >>> Place('p', pos=(1,2)).pos
            Position(1, 2)

            @keyword pos: the position of the new place
            @type pos: `tuple`
            """
            x, y = args.pop("pos", (0, 0))
            self.pos = Position(x, y)
            module.Place.__init__(self, name, tokens, check, **args)
        # apidoc skip
        def copy (self, name=None, **args) :
            x, y = args.pop("pos", self.pos())
            result = module.Place.copy(self, name, **args)
            result.pos.moveto(x, y)
            return result
        # apidoc skip
        def __pnmldump__ (self) :
            """
            >>> p = Place('p', pos=(1, 2))
            >>> p.__pnmldump__()
            <?xml version="1.0" encoding="utf-8"?>
            <pnml>
             <place id="p">
              <type domain="universal"/>
              <initialMarking>
               <multiset/>
              </initialMarking>
              <graphics>
               <position x="1" y="2"/>
              </graphics>
             </place>
            </pnml>
            """
            t = module.Place.__pnmldump__(self)
            try :
                gfx = t.child("graphics")
            except SnakesError :
                gfx = Tree("graphics", None)
                t.add_child(gfx)
            gfx.add_child(Tree("position", None,
                               x=str(self.pos.x),
                               y=str(self.pos.y)))
            return t
        # apidoc skip
        @classmethod
        def __pnmlload__ (cls, tree) :
            """
            >>> old = Place('p', pos=(1, 2))
            >>> p = old.__pnmldump__()
            >>> new = Place.__pnmlload__(p)
            >>> new.pos
            Position(1, 2)
            >>> new
            Place('p', MultiSet([]), tAll)
            >>> new.__class__
            <class 'snakes.plugins.pos.Place'>
            """
            result = new_instance(cls, module.Place.__pnmlload__(tree))
            try :
                p = tree.child("graphics").child("position")
                x, y = eval(p["x"]), eval(p["y"])
                result.pos = Position(x, y)
            except SnakesError :
                result.pos = Position(0, 0)
            return result
    class Transition (module.Transition) :
        def __init__ (self, name, guard=None, **args) :
            """If no position is given `(0, 0)` is chosen

            >>> Transition('t').pos
            Position(0, 0)
            >>> Transition('t', pos=(1,2)).pos
            Position(1, 2)

            @keyword pos: the position of the new transition
            @type pos: `tuple`
            """
            x, y = args.pop("pos", (0, 0))
            self.pos = Position(x, y)
            module.Transition.__init__(self, name, guard, **args)
        # apidoc skip
        def copy (self, name=None, **args) :
            x, y = args.pop("pos", self.pos())
            result = module.Transition.copy(self, name, **args)
            result.pos.moveto(x, y)
            return result
        # apidoc skip
        def __pnmldump__ (self) :
            """
            >>> t = Transition('t', pos=(2, 1))
            >>> t.__pnmldump__()
            <?xml version="1.0" encoding="utf-8"?>
            <pnml>
             <transition id="t">
              <graphics>
               <position x="2" y="1"/>
              </graphics>
             </transition>
            </pnml>
            """
            t = module.Transition.__pnmldump__(self)
            t.add_child(Tree("graphics", None,
                             Tree("position", None,
                                  x=str(self.pos.x),
                                  y=str(self.pos.y))))
            return t
        # apidoc skip
        @classmethod
        def __pnmlload__ (cls, tree) :
            """
            >>> old = Transition('t', pos=(2, 1))
            >>> p = old.__pnmldump__()
            >>> new = Transition.__pnmlload__(p)
            >>> new.pos
            Position(2, 1)
            >>> new
            Transition('t', Expression('True'))
            >>> new.__class__
            <class 'snakes.plugins.pos.Transition'>
            """
            result = new_instance(cls, module.Transition.__pnmlload__(tree))
            try :
                p = tree.child("graphics").child("position")
                x, y = eval(p["x"]), eval(p["y"])
                result.pos = Position(x, y)
            except SnakesError :
                result.pos = Position(0, 0)
            return result
    class PetriNet (module.PetriNet) :
        def add_place (self, place, **args) :
            """Position can be set also when a place is added to the
            net.

            >>> n = PetriNet('n')
            >>> n.add_place(Place('a', pos=(1, 2)))
            >>> n.node('a').pos
            Position(1, 2)
            >>> n.add_place(Place('b'), pos=(3,4))
            >>> n.node('b').pos
            Position(3, 4)
            >>> n.add_place(Place('c', pos=(42, 42)), pos=(5, 6))
            >>> n.node('c').pos
            Position(5, 6)

            @keyword pos: the position of the added place
            @type pos: `tuple`
            """
            if "pos" in args :
                x, y = args.pop("pos")
                place.pos.moveto(x, y)
            module.PetriNet.add_place(self, place, **args)
        def add_transition (self, trans, **args) :
            """Position can be set also when a transitions is added to
            the net. See method `add_place` above.

            @keyword pos: the position of the added transition
            @type pos: `tuple`
            """
            if "pos" in args :
                x, y = args.pop("pos")
                trans.pos.moveto(x, y)
            module.PetriNet.add_transition(self, trans, **args)
        def merge_places (self, target, sources, **args) :
            """When places are merged, the position of the new place
            is the barycentre of the positions of the merged nodes.
            Optionally, position can be specified in the call the
            `merge_places`.

            >>> n = PetriNet('n')
            >>> n.add_place(Place('a', pos=(1,2)))
            >>> n.add_place(Place('b', pos=(3,4)))
            >>> n.merge_places('c', ['a', 'b'])
            >>> n.node('c').pos
            Position(2.0, 3.0)
            >>> n.merge_places('d', ['a', 'b'], pos=(0, 0))
            >>> n.node('d').pos
            Position(0, 0)

            @keyword pos: the position of the added transition
            @type pos: `tuple`
            """
            pos = args.pop("pos", None)
            module.PetriNet.merge_places(self, target, sources, **args)
            if pos is None :
                pos = reduce(complex.__add__,
                             (complex(*self._place[name].pos())
                              for name in sources)) / len(sources)
                x, y = pos.real, pos.imag
            else :
                x, y = pos
            self._place[target].pos.moveto(x, y)
        def merge_transitions (self, target, sources, **args) :
            """See method `merge_places` above.
            """
            pos = args.pop("pos", None)
            module.PetriNet.merge_transitions(self, target, sources, **args)
            if pos is None :
                pos = reduce(complex.__add__,
                             (complex(*self._trans[name].pos())
                              for name in sources)) / len(sources)
                x, y = pos.real, pos.imag
            else :
                x, y = pos
            self._trans[target].pos.moveto(x, y)
        def bbox (self) :
            """The bounding box of the net, that is, the smallest
            rectangle that contains all nodes coordinates.

            @return: rectangle coordinates as `((xmin, ymin), (xmax,
                ymax))`
            @rtype: tuple
            """
            if len(self._node) == 0 :
                return (0, 0), (0, 0)
            else :
                nodes = iter(self._node.values())
                xmin, ymin = next(nodes).pos()
                xmax, ymax = xmin, ymin
                for n in nodes :
                    x, y = n.pos()
                    xmin = min(xmin, x)
                    xmax = max(xmax, x)
                    ymin = min(ymin, y)
                    ymax = max(ymax, y)
                return (xmin, ymin), (xmax, ymax)
        def shift (self, dx, dy) :
            """Shift every node by `(dx, dy)`

            @param dx: horizontal shift
            @type dx: `float`
            @param dy: vertical shift
            @type dy: `float`
            """
            for node in self.node() :
                node.pos.shift(dx, dy)
        def transpose (self) :
            """Perform a clockwise 90° rotation of node coordinates,
            ie, change every position `(x, y)` to `(-y, x)`
            """
            for node in self.node() :
                x, y = node.pos()
                node.pos.moveto(-y, x)
    return Place, Transition, PetriNet, Position
