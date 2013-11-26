"""A plugin to record for each not to which modules it belongs.

Modules are arbitrary values, each `PetriNet`, `Place` or transition
is attached a set of modules. These modules can be given at
construction time, as a single value or a collection of values.
Moreover, when nodes are attached to a net, they inherit the modules
from this net. When nodes are merged, their sets of modules is added
to build the set of modules of the new node.

The plugin implements a very basic notion of modules, un particular,
it does not support hierarchy and when a module is attached to a node,
it is not possible to remove it. So modules are only a way to remember
where a node comes from and to tag nodes as we aggregate nets, e.g.,
through compositions (see plugin `ops`).

Internally, modules are stored in a label called `"modules"` (see
plugin `snakes.plugins.labels`).

>>> import snakes.plugins
>>> snakes.plugins.load(["ops", "modules"], "snakes.nets", "snk")
<module 'snk' ...>
>>> from snk import *
>>> n1 = PetriNet("n1", modules="hello")
>>> n1.add_place(Place("p"))
>>> n1.place("p").modules()
set(['hello'])
>>> n1.add_place(Place("q"))
>>> n2 = PetriNet("n2", modules="world")
>>> n2.add_place(Place("r"))
>>> n2.add_place(Place("s", modules="spam"))
>>> n = n1|n2
>>> list(sorted((p.name, list(sorted(p.modules()))) for p in n.place()))
[('[p|]', ['hello']),
 ('[q|]', ['hello']),
 ('[|r]', ['world']),
 ('[|s]', ['spam', 'world'])]
>>> n.modules("egg")
>>> list(sorted((p.name, list(sorted(p.modules()))) for p in n.place()))
[('[p|]', ['egg', 'hello']),
 ('[q|]', ['egg', 'hello']),
 ('[|r]', ['egg', 'world']),
 ('[|s]', ['egg', 'spam', 'world'])]
"""

from snakes.plugins import plugin, new_instance
from snakes.data import iterate
from snakes.pnml import Tree

@plugin("snakes.nets",
        depends=["snakes.plugins.labels"])
def extend (module) :
    class Transition (module.Transition) :
        def __init__ (self, name, guard=None, **options) :
            mod = set(iterate(options.pop("modules", [])))
            module.Transition.__init__(self, name, guard, **options)
            self.modules(mod)
        def modules (self, modules=None) :
            if modules is None :
                return self.label("modules")
            else :
                self.label(modules=set(iterate(modules)))
    class Place (module.Place) :
        def __init__ (self, name, tokens=[], check=None, **options) :
            mod = set(iterate(options.pop("modules", [])))
            module.Place.__init__(self, name, tokens, check, **options)
            self.modules(mod)
        def modules (self, modules=None) :
            if modules is None :
                return self.label("modules")
            else :
                self.label(modules=set(iterate(modules)))
    class PetriNet (module.PetriNet) :
        def __init__ (self, name, **options) :
            mod = set(iterate(options.pop("modules", [])))
            module.PetriNet.__init__(self, name, **options)
            self.modules(mod)
        def modules (self, modules=None) :
            if modules is None :
                return self.label("modules")
            mod = set(iterate(modules))
            self.label(modules=mod)
            for node in self.node() :
                node.modules(mod | node.modules())
        def add_place (self, place, **options) :
            mod = set(iterate(options.pop("modules", self.modules())))
            module.PetriNet.add_place(self, place, **options)
            place.modules(place.modules() | mod)
        def add_transition (self, trans, **options) :
            mod = set(iterate(options.pop("modules", self.modules())))
            module.PetriNet.add_transition(self, trans, **options)
            trans.modules(trans.modules() | mod)
        def merge_places (self, target, sources, **options) :
            mod = set(iterate(options.pop("modules", self.modules())))
            module.PetriNet.merge_places(self, target, sources, **options)
            new = self.place(target)
            new.modules(reduce(set.__or__,
                               (self.place(p).lmodules()
                                for p in sources),
                               mod))
        def merge_transitions (self, target, sources, **options) :
            mod = set(iterate(options.pop("modules", self.modules())))
            module.PetriNet.merge_transitions(self, target, sources, **options)
            new = self.transition(target)
            new.modules(reduce(set.__or__,
                               (self.place(p).modules()
                                for p in sources),
                               mod))
    return Transition, Place, PetriNet
