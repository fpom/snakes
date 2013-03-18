# -*- encoding: latin-1
"""A plugin to compose nets _à la_ Petri Box Calculus.

@note: this plugin depends on plugins `clusters` and `status` that are
    automatically loaded
"""

"""
## Control-flow and buffers places ##

When this module is used, places are equipped with statuses (see also
plugin `status` that provides this service). We distinguish in
particular:

  * _entry_ places marked at the initial state of the net
  * _exit_ places marked at a final state of the net
  * _internal_ places marked during the execution
  * all together, these places form the _control-flow places_ and can
    be marked only by black tokens (ie, they are typed `tBlackToken`
    and thus can hold only `dot` values)
  * _buffer_ places that may hold data of any type, each buffer place
    is given a name that is the name of the buffer modelled by the
    place

Plugin `ops` exports these statuses as Python objects:[^1] `entry`,
`internal` and `exit` are instances of class `Status` while `buffer`
is a function that returns an instance of `Buffer` (a subclass of
`Status`) when called with a name as its parameter.

[^1]: All these objects are actually defined in plugin `status`

Let's define a net with one entry place, one exit place and two buffer
places. Note how we use keyword argument `status` to the place
constructor to define the status of the created place:

>>> import snakes.plugins
>>> snakes.plugins.load('ops', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> basic = PetriNet('basic')
>>> basic.add_place(Place('e', status=entry))
>>> basic.add_place(Place('x', status=exit))
>>> basic.add_transition(Transition('t'))
>>> basic.add_input('e', 't', Value(dot))
>>> basic.add_output('x', 't', Value(dot))
>>> basic.add_place(Place('b1', [1], status=buffer('egg')))
>>> basic.add_place(Place('b2', [2], status=buffer('spam')))
>>> basic.add_input('b1', 't', Variable('x'))
>>> basic.add_output('b2', 't', Expression('x+1'))

The simplest operation is to change buffer names, let's do it on a
copy of our net. This operation is called `hide` because it is
basically used to hide a buffer:

>>> n = basic.copy()
>>> n.node('b1').status
Buffer('buffer','egg')
>>> n.hide(buffer('egg'))
>>> n.node('b1').status
Status(None)

As we can see, place `b1` now has a dummy status. But `hide` can
accept a second argument and allows to rename a buffer:

>>> n.node('b2').status
Buffer('buffer','spam')
>>> n.hide(buffer('spam'), buffer('ham'))
>>> n.node('b2').status
Buffer('buffer','ham')

A slighlty different way for hiding buffers is to use operator `/`,
which actually constructs a new net, changing the names of every node
in the original net to `'[.../egg]'`:

>>> n = basic / 'egg'
>>> n.node('[b1/egg]').status
Buffer('buffer')

As we can see, a buffer hidden using `/` still has a buffer status but
with no name associated. Such an anonymous buffer is treated in a
special way as we'll see later on.

The systematic renaming of nodes is something we should get used to
before to continue. When one or two nets are constructed through an
operation, the nodes of the operand nets are combined in one way or
another. For an arbitrary operation `A % B`, the resulting net will be
called `'[A.name%B.name]'` (if `A` and `B` are nets). Whenever a node
`a` from `A` is combined with a node `b` from `B`, the resulting node
will be called `'[a%b]'`. If only one node is copied in the resulting
net, it will be called `'[a%]'` or `'[%b]'` depending on wher it comes
from. This systematic renaming allows to ensure that even if `A` and
`B` have nodes with the same names, there will be no name clash in the
result, while, at the same time allowing users to predict the new name
of a node.

## Control-flow compositions ##

Using control-flow places, it becomes possible to build nets by
composing smaller nets through control flow operations. Let's start
with the _sequential composition_ `A & B`, basically, its combines the
exit places of net `A` with the entry places of net `B`, ensuring thus
that the resulting net behaves like if we execute `A` followed by `B`.
In the example below, we use method `status` of a net to get the
places with a given status:

>>> n = basic & basic
>>> n.status(internal)
('[x&e]',)
>>> n.place('[x&e]').pre
{'[t&]': Value(dot)}
>>> n.place('[x&e]').post
{'[&t]': Value(dot)}
>>> n.status(buffer('egg'))
('[b1&b1]',)
>>> n.status(buffer('spam'))
('[b2&b2]',)

We can see that `n` now has one internal place that is the combination
of the exit place of the left copy of `basic` with the entry place of
the right copy of `basic`. (Hence its name: `'[x&e]'`.) We can see
also how it is connected to the left/right copy of `t` as its
input/output. Last, we can see that buffer places from the two copies
of `basic` have been merged when they have had the same name. This
merging won't occur for anonymous buffers. For example, hiding
`'spam'` in the right net of the sequential composition will result in
two buffer places, one still named `'spam'` that is the copy of `'b2'`
from the left operand of `&`, another that is anonymous and is the
copy of `'[b2/spam]'` (ie, `'b2'`after its status was hidden) from the
right operand of `&`.

>>> n = basic & (basic / 'spam')
>>> n.status(buffer('spam'))
('[b2&]',)
>>> n.status(buffer(None))
('[&[b2/spam]]',)

The next operation is the _choice `A + B` that behave either as `A` or
as `B`. This is obtained by comining the entry places of both nets one
the one hand, and by combining their exit places on the other hand.

>>> n = basic + basic
>>> n.status(entry)
('[e+e]',)
>>> list(sorted(n.place('[e+e]').post.items()))
[('[+t]', Value(dot)), ('[t+]', Value(dot))]
>>> n.status(exit)
('[x+x]',)
>>> list(sorted(n.place('[x+x]').pre.items()))
[('[+t]', Value(dot)), ('[t+]', Value(dot))]

Another operation is the _iteration_ `A * B` that behaves by executing
`A` repeatedly (including no repetition) followed by one execution of
`B`. This is obtained by combining the entry and exit places of `A`
with the entry place of `B`.

>>> n = basic * basic
>>> n.status(entry)
('[e,x*e]',)
>>> n.place('[e,x*e]').post
{'[t*]': Value(dot), '[*t]': Value(dot)}
>>> n.place('[e,x*e]').pre
{'[t*]': Value(dot)}

Finally, there is the _parallel composition_ `A | B` that just
executes both nets in parallel. But because of the merging of buffer
places, they are able to communicate.

>>> n = basic | basic
>>> n.status(buffer('egg'))
('[b1|b1]',)
>>> n.status(buffer('spam'))
('[b2|b2]',)

>>> pass
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
    """Essentially, class `PetriNet` is extended to support the binary
    operations discussed above."""
    class PetriNet (module.PetriNet) :
        def __or__ (self, other) :
            "Parallel composition"
            return _glue("|", self, other)
        def __and__ (self, other) :
            "Sequential composition"
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
            "Status hiding and renaming"
            if new is None :
                new = Status(None)
            for node in self.status(old) :
                self.set_status(node, new)
        def __div__ (self, name) :
            "Buffer hiding"
            result = self.copy()
            for node in result.node() :
                result.rename_node(node.name, "[%s/%s]" % (node, name))
            for status in result.status :
                if status._value == name :
                    result.hide(status, status.__class__(status._name, None))
            return result
        # apidoc skip
        def __truediv__ (self, other) :
            return self.__div__(other)
    return PetriNet
