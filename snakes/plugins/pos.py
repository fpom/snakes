"""A plugin to add positions to the nodes.

  * `Place` and `Transition` constructors are added an optional argument
    `pos=(x,y)` to set their position
  * `Place` and `Transition` are added an attribute `pos` that is pair
    of numbers with attributes `x` and `y` and methods `shift(dx, dy)`
    and `moveto(x, y)`
  * Petri nets are added methods `bbox()` that returns a pair of
    extrema `((xmin, ymin), (xmax, ymax))`, a method `shift(dx, dy)`
   that shift all the nodes, and a method `transpose()` that rotates
   the net in such a way that the top-down direction becomes
   left-right

>>> import snakes.plugins
>>> snakes.plugins.load('pos', 'snakes.nets', 'nets')
<module ...>
>>> from nets import PetriNet, Place, Transition
>>> n = PetriNet('N')
>>> n.add_place(Place('p00'))
>>> n.add_transition(Transition('t10', pos=(1, 0)))
>>> n.add_place(Place('p11', pos=(1, 1)))
>>> n.add_transition(Transition('t01', pos=(0, 1)))
>>> n.node('t10').pos
Position(1, 0)
>>> n.node('t10').pos.x
1
>>> n.node('t10').pos.y
0
>>> n.node('t10').pos.y = 1
Traceback (most recent call last):
  ...
AttributeError: readonly attribute
>>> n.node('t10').pos()
(1, 0)
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

@todo: revise documentation
"""

from snakes import SnakesError
from snakes.compat import *
from snakes.plugins import plugin, new_instance
from snakes.pnml import Tree

class Position (object) :
    "The position of a node"
    def __init__ (self, x, y) :
        self.__dict__["x"] = x
        self.__dict__["y"] = y
    def __str__ (self) :
        return "(%s, %s)" % (str(self.x), str(self.y))
    def __repr__ (self) :
        return "Position(%s, %s)" % (str(self.x), str(self.y))
    def __setattr__ (self, name, value) :
        if name in ("x", "y") :
            raise AttributeError("readonly attribute")
        else :
            self.__dict__[name] = value
    def moveto (self, x, y) :
        self.__init__(x, y)
    def shift (self, dx, dy) :
        self.__init__(self.x + dx, self.y + dy)
    def __getitem__ (self, rank) :
        if rank == 0 :
            return self.x
        elif rank == 1 :
            return self.y
        else :
            raise IndexError("Position index out of range")
    def __iter__ (self) :
        yield self.x
        yield self.y
    def __call__ (self) :
        return (self.x, self.y)

@plugin("snakes.nets")
def extend (module) :
    class Place (module.Place) :
        def __init__ (self, name, tokens=[], check=None, **args) :
            x, y = args.pop("pos", (0, 0))
            self.pos = Position(x, y)
            module.Place.__init__(self, name, tokens, check, **args)
        def copy (self, name=None, **args) :
            x, y = args.pop("pos", self.pos())
            result = module.Place.copy(self, name, **args)
            result.pos.moveto(x, y)
            return result
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
            x, y = args.pop("pos", (0, 0))
            self.pos = Position(x, y)
            module.Transition.__init__(self, name, guard, **args)
        def copy (self, name=None, **args) :
            x, y = args.pop("pos", self.pos())
            result = module.Transition.copy(self, name, **args)
            result.pos.moveto(x, y)
            return result
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
            if "pos" in args :
                x, y = args.pop("pos")
                place.pos.moveto(x, y)
            module.PetriNet.add_place(self, place, **args)
        def add_transition (self, trans, **args) :
            if "pos" in args :
                x, y = args.pop("pos")
                trans.pos.moveto(x, y)
            module.PetriNet.add_transition(self, trans, **args)
        def merge_places (self, target, sources, **args) :
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
            for node in self.node() :
                node.pos.shift(dx, dy)
        def transpose (self) :
            for node in self.node() :
                x, y = node.pos()
                node.pos.moveto(-y, x)
    return Place, Transition, PetriNet, Position
