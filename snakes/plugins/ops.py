"""A plugin to compose nets.

The compositions are based on place status and automatically merge
some nodes (buffers and variables, tick transitions).

>>> import snakes.plugins
>>> snakes.plugins.load('ops', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> from snakes.plugins.status import entry, internal, exit, buffer
>>> basic = PetriNet('basic')
>>> basic.add_place(Place('e', status=entry))
>>> basic.add_place(Place('x', status=exit))
>>> basic.add_transition(Transition('t'))
>>> basic.add_input('e', 't', Value(1))
>>> basic.add_output('x', 't', Value(2))
>>> basic.add_place(Place('b', [1], status=buffer('buf')))

>>> n = basic.copy()
>>> n.hide(entry)
>>> n.node('e').status
Status(None)
>>> n.hide(buffer('buf'), buffer(None))
>>> n.node('b').status
Buffer('buffer')

>>> n = basic / 'buf'
>>> n.node('[b/buf]').status
Buffer('buffer')

>>> n = basic & basic
>>> n.status(internal)
('[x&e]',)
>>> n.place('[x&e]').pre
{'[t&]': Value(2)}
>>> n.place('[x&e]').post
{'[&t]': Value(1)}
>>> n.status(buffer('buf'))
('[b&b]',)

>>> n = basic + basic
>>> n.status(entry)
('[e+e]',)
>>> list(sorted(n.place('[e+e]').post.items()))
[('[+t]', Value(1)), ('[t+]', Value(1))]
>>> n.status(exit)
('[x+x]',)
>>> list(sorted(n.place('[x+x]').pre.items()))
[('[+t]', Value(2)), ('[t+]', Value(2))]

>>> n = basic * basic
>>> n.status(entry)
('[e,x*e]',)
>>> n.place('[e,x*e]').post
{'[t*]': Value(1), '[*t]': Value(1)}
>>> n.place('[e,x*e]').pre
{'[t*]': Value(2)}

>>> n1 = basic.copy()
>>> n1.declare('global x; x=1')
>>> n2 = basic.copy()
>>> n2.globals['y'] = 2
>>> n = n1 + n2
>>> n.globals['x'], n.globals['y']
(1, 2)
>>> n._declare
['global x; x=1']
"""

import snakes.plugins
from snakes.plugins.status import Status, entry, exit, internal
from snakes.data import cross
from snakes.plugins.clusters import Cluster

def _glue (op, one, two) :
    result = one.__class__("(%s%s%s)" % (one.name, op, two.name))
    def new (name) :
        return "[%s%s]" % (name, op)
    for net in (one, two) :
        result.clusters.add_child(Cluster())
        result._declare = list(set(result._declare) | set(net._declare))
        result.globals.update(net.globals)
        for place in net.place() :
            result.add_place(place.copy(new(place.name)),
                             cluster=[-1]+net.clusters.get_path(place.name))
        for trans in net.transition() :
            result.add_transition(trans.copy(new(trans.name)),
                                  cluster=[-1]+net.clusters.get_path(trans.name))
            for place, label in trans.input() :
                result.add_input(new(place.name),
                                 new(trans.name),
                                 label.copy())
            for place, label in trans.output() :
                result.add_output(new(place.name),
                                  new(trans.name),
                                  label.copy())
        def new (name) :
            return "[%s%s]" % (op, name)
    for status in result.status :
        result.status.merge(status)
        new = result.status(status)
        if len(new) == 1 :
            name  = "[%s%s%s]" % (",".join(sorted(one.status(status))),
                                  op,
                                  ",".join(sorted(two.status(status))))
            if name != new[0] :
                result.rename_node(new[0], name)
    return result

@snakes.plugins.plugin("snakes.nets",
                       depends=["snakes.plugins.clusters",
                                "snakes.plugins.status"])
def extend (module) :
    "Build the extended module"
    class PetriNet (module.PetriNet) :
        def __or__ (self, other) :
            "Parallel"
            return _glue("|", self, other)
        def __and__ (self, other) :
            "Sequence"
            result = _glue("&", self, other)
            remove = set()
            for x, e in cross((self.status(exit), other.status(entry))) :
                new = "[%s&%s]" % (x, e)
                new_x, new_e = "[%s&]" % x, "[&%s]" % e
                result.merge_places(new, (new_x, new_e), status=internal)
                remove.update((new_x, new_e))
            for p in remove :
                result.remove_place(p)
            return result
        def __add__ (self, other) :
            "Choice"
            result = _glue("+", self, other)
            for status in (entry, exit) :
                remove = set()
                for l, r in cross((self.status(status),
                                   other.status(status))) :
                    new = "[%s+%s]" % (l, r)
                    new_l, new_r = "[%s+]" % l, "[+%s]" % r
                    result.merge_places(new, (new_l, new_r), status=status)
                    remove.update((new_l, new_r))
                for p in remove :
                    result.remove_place(p)
            return result
        def __mul__ (self, other) :
            "Iteration"
            result = _glue("*", self, other)
            remove = set()
            for e1, x1, e2 in cross((self.status(entry),
                                     self.status(exit),
                                     other.status(entry))) :
                new = "[%s,%s*%s]" % (e1, x1, e2)
                new_e1, new_x1 = "[%s*]" % e1, "[%s*]" % x1
                new_e2 = "[*%s]" % e2
                result.merge_places(new, (new_e1, new_x1, new_e2),
                                    status=entry)
                remove.update((new_e1, new_x1, new_e2))
            for p in remove :
                result.remove_place(p)
            return result
        def hide (self, old, new=None) :
            if new is None :
                new = Status(None)
            for node in self.status(old) :
                self.set_status(node, new)
        def __div__ (self, name) :
            result = self.copy()
            for node in result.node() :
                result.rename_node(node.name, "[%s/%s]" % (node, name))
            for status in result.status :
                if status._value == name :
                    result.hide(status, status.__class__(status._name, None))
            return result
    return PetriNet
