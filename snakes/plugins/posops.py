"""A plugin to combine positions and nets operations

>>> import snakes.plugins
>>> snakes.plugins.load(['posops', 'graphviz'], 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> from snakes.plugins.status import entry, internal, exit, buffer
>>> basic = PetriNet('basic')
>>> basic.add_place(Place('e', status=entry, pos=(0, 2)))
>>> basic.add_place(Place('x', status=exit, pos=(0, 0)))
>>> basic.add_transition(Transition('t', pos=(0, 1)))
>>> basic.add_input('e', 't', Value(1))
>>> basic.add_output('x', 't', Value(2))

>>> (basic | basic).draw(',test-parallel.png')
>>> (basic & (basic | basic)).draw(',test-sequence.png')
>>> (basic + (basic | basic)).draw(',test-choice.png')
>>> (basic * (basic | basic)).draw(',test-iteration.png')
"""

from snakes.data import cross
from snakes.plugins.status import entry, exit
import snakes.plugins

@snakes.plugins.plugin("snakes.nets",
                       depends=["snakes.plugins.pos",
                                "snakes.plugins.ops"])
def extend (module) :
    "Build the extended module"
    class PetriNet (module.PetriNet) :
        def __or__ (self, other) :
            "Parallel"
            (xmin1, ymin1), (xmax1, ymax1) = self.bbox()
            (xmin2, ymin2), (xmax2, ymax2) = other.bbox()
            xshift = xmax1 - xmin2 + 1
            yshift = (ymin1 + ymax1 - ymin2 - ymax2)/2.0
            other = other.copy()
            other.shift(xshift, yshift)
            return module.PetriNet.__or__(self, other)
        def __and__ (self, other) :
            "Sequence"
            (xmin1, ymin1), (xmax1, ymax1) = self.bbox()
            (xmin2, ymin2), (xmax2, ymax2) = other.bbox()
            xshift = (xmin1 + xmax1 - xmin2 - xmax2)/2.0
            yshift = ymin2 - ymax1
            other = other.copy()
            other.shift(xshift, yshift)
            result = module.PetriNet.__and__(self, other)
            places = ["[%s&%s]" % (x, e) for x, e in
                      cross((self.status(exit), other.status(entry)))]
            start = (xmin1 + xmax1)/2.0 - (len(places)-1)/2.0
            for shift, place in enumerate(places) :
                result._place[place].pos.moveto(start+shift, ymin1)
            return result
        def __add__ (self, other) :
            "Choice"
            (xmin1, ymin1), (xmax1, ymax1) = self.bbox()
            (xmin2, ymin2), (xmax2, ymax2) = other.bbox()
            xshift = xmax1 - xmin2 + 1
            yshift = (ymin1 + ymax1 - ymin2 - ymax2)/2.0
            other = other.copy()
            other.shift(xshift, yshift)
            result = module.PetriNet.__add__(self, other)
            places = ["[%s+%s]" % (e1, e2) for e1, e2 in
                      cross((self.status(entry), other.status(entry)))]
            y = max(ymax1, ymax2)
            start = xmax1 - xmin2 + 1.0 - (len(places)-1)/2.0
            for shift, place in enumerate(places) :
                result._place[place].pos.moveto(start+shift, y)
            places = ["[%s+%s]" % (x1, x2) for x1, x2 in
                      cross((self.status(exit), other.status(exit)))]
            y = max(ymin1, ymin2)
            start = xmax1 - xmin2 + 1.0 - (len(places)-1)/2.0
            for shift, place in enumerate(places) :
                result._place[place].pos.moveto(start+shift, y)
            return result
        def __mul__ (self, other) :
            "Iteration"
            (xmin1, ymin1), (xmax1, ymax1) = self.bbox()
            (xmin2, ymin2), (xmax2, ymax2) = other.bbox()
            xshift = xmin1 - xmax2 - 1.0
            yshift = ymin1 - ymax2
            places = ["[%s,%s*%s]" % (e1, x1, e2) for e1, x1, e2 in
                      cross((self.status(entry), self.status(exit),
                             other.status(entry)))]
            other = other.copy()
            other.shift(xshift, yshift)
            result = module.PetriNet.__mul__(self, other)
            width = len(places) - 1.0
            if width > xmax2 - xmin2 :
                xstart = xmax2 + xshift - width
            else :
                xstart = xmin2 + xshift
            ystart = ymax2 + yshift
            for shift, place in enumerate(places) :
                result._place[place].pos.moveto(xstart+shift, ystart+shift)
            return result
    return PetriNet
