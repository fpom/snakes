import sys
import snakes.plugins

from collections import defaultdict
from snakes.nets import ConstraintError
from snakes.typing import Instance, CrossProduct, tNatural
from snakes.data import iterate, WordSet

# apidoc skip
class Pid (tuple) :
    def __new__(cls, *args):
        """
        >>> Pid(1, 2, 3)
        Pid(1, 2, 3)
        >>> Pid('1.2.3')
        Pid(1, 2, 3)
        >>> Pid('1.2', 3)
        Pid(1, 2, 3)
        >>> Pid([1, 2], [3])
        Pid(1, 2, 3)
        >>> Pid((1, 2), 3)
        Pid(1, 2, 3)
        """
        data = []
        for a in args :
            if isinstance(a, int) :
                data.append(a)
            elif isinstance(a, str) :
                data.extend(int(x) for x in a.strip(".").split("."))
            elif isinstance(a, cls) :
                data.extend(a)
            elif isinstance(a, (list, tuple)) :
                data.extend(int(x) for x in a)
            else :
                raise ValueError("invalid Pid fragment %r" % a)
        return super(Pid, cls).__new__(cls, data)
    def __repr__(self) :
        """
        >>> Pid(1, 2, 3)
        Pid(1, 2, 3)
        >>>
        """
        return "Pid(%s)" % ", ".join(str(x) for x in self)
    def __str__ (self) :
        """
        >>> str(Pid(1, 2, 3))
        '1.2.3'
        """
        return ".".join(str(x) for x in self)
    @classmethod
    def from_str (cls, data) :
        """
        >>> Pid.from_str('1.2.3')
        Pid(1, 2, 3)
        """
        return cls(data)
    @classmethod
    def from_list (cls, data) :
        """
        >>> Pid.from_str([1, 2, 3])
        Pid(1, 2, 3)
        """
        return cls(data)
    def copy (self) :
        """
        >>> p = Pid(1, 2, 3)
        >>> p.copy()
        Pid(1, 2, 3)
        >>> p == p.copy()
        True
        >>> p is p.copy()
        False
        """
        return self.__class__(*self)
    def __add__(self, frag):
        """
        >>> Pid(1, 2, 3) + 4
        Pid(1, 2, 3, 4)
        >>> Pid(1, 2, 3) + Pid(4, 5)
        Pid(1, 2, 3, 4, 5)
        >>> Pid(1, 2, 3) + [4, 5]
        Pid(1, 2, 3, 4, 5)
        """
        return self.__class__(self, frag)
    def at(self, i):
        """
        >>> Pid(1, 2, 3).at(1)
        2
        """
        return self[i]
    def __getitem__ (self, start, stop=None) :
        if stop is None :
            return tuple.__getitem__(self, start)
        else :
            return self.__getslice__(start, stop)
    def __getslice__ (self, start, stop=sys.maxint) :
        """
        >>> pid = Pid(1, 2, 3, 4)
        >>> pid[:]
        Pid(1, 2, 3, 4)
        >>> pid[1:]
        Pid(2, 3, 4)
        >>> pid[:-1]
        Pid(1, 2, 3)
        >>> pid[1:-1]
        Pid(2, 3)
        >>> pid[1:3]
        Pid(2, 3)
        """
        return self.__class__(tuple.__getslice__(self, start, stop))
    def subpid (self, start=0, stop=sys.maxint) :
        """
        >>> pid = Pid(1, 2, 3, 4)
        >>> pid.subpid(0)
        Pid(1, 2, 3, 4)
        >>> pid.subpid(1)
        Pid(2, 3, 4)
        >>> pid.subpid(0, -1)
        Pid(1, 2, 3)
        >>> pid.subpid(1, -1)
        Pid(2, 3)
        >>> pid.subpid(1, 3)
        Pid(2, 3)
        """
        return self[start:stop]
    def prefix(self):
        """
        >>> Pid(1, 2, 3).prefix()
        Pid(1, 2)
        """
        return self[:-1]
    def suffix(self):
        """
        >>> Pid(1, 2, 3).suffix()
        Pid(2, 3)
        """
        return self[1:]
    def ends_with(self):
        """
        >>> Pid(1, 2, 3).ends_with()
        3
        """
        return self[-1]
    def next(self, pid_component):
        """
        >>> Pid(1).next(0)
        Pid(1, 1)
        >>> Pid(1, 2).next('2').next(3)
        Pid(1, 2, 3, 4)
        """
        return self + [int(pid_component)+1]
    def parent(self, other):
        """
        >>> Pid(1, 1, 1).parent(Pid(1, 1, 1))
        False
        >>> Pid(1, 1, 1).parent(Pid(1, 1, 1, 3))
        True
        >>> Pid(1, 1, 1).parent(Pid(1, 1))
        False
        >>> Pid(1, 1, 1).parent(Pid(1, 1, 1, 2, 4))
        True
        """
        return len(self) < len(other) and other[:len(self)] == self
    def parent1(self, other):
        """
        >>> Pid(1, 1, 1).parent1(Pid(1, 1, 1))
        False
        >>> Pid(1, 1, 1).parent1(Pid(1, 1, 1, 3))
        True
        >>> Pid(1, 1, 1).parent1(Pid(1, 1))
        False
        >>> Pid(1, 1, 1).parent1(Pid(1, 1, 1, 2, 4))
        False
        """
        return len(self)+1 == len(other) and other[:-1] == self
    def sibling(self, other):
        """
        >>> Pid(1, 1, 1).sibling(Pid(1, 1, 1))
        False
        >>> Pid(1, 1, 1).sibling(Pid(1, 1, 1, 3))
        False
        >>> Pid(1, 1, 1).sibling(Pid(1, 1, 2))
        True
        >>> Pid(1, 1, 2).sibling(Pid(1, 1, 1))
        False
        >>> Pid(1, 1, 1).sibling(Pid(1, 1, 5))
        True
        """
        return self[:-1] == other[:-1] and self[-1] < other[-1]
    def sibling1(self, other):
        """
        >>> Pid(1, 1, 1).sibling1(Pid(1, 1, 1))
        False
        >>> Pid(1, 1, 1).sibling1(Pid(1, 1, 1, 3))
        False
        >>> Pid(1, 1, 1).sibling1(Pid(1, 1, 2))
        True
        >>> Pid(1, 1, 2).sibling1(Pid(1, 1, 1))
        False
        >>> Pid(1, 1, 1).sibling1(Pid(1, 1, 5))
        False
        """
        return self[:-1] == other[:-1] and self[-1]+1 == other[-1]

tPid = snakes.typing.Instance(Pid)
tNextPid = CrossProduct(tPid, tNatural)

# apidoc skip
class ChildPid (object) :
    def __init__ (self, parent) :
        self.parent = parent

# apidoc skip
class ParentPid (object) :
    def __init__ (self, name, env) :
        self.name = name
        self.env = env
        self.count = 0
    def kill (self) :
        self.env.killed.add(self.name)
    def new (self) :
        child = ChildPid(self)
        self.count += 1
        return child

# apidoc skip
class PidEnv (dict) :
    def __init__ (self, prog) :
        dict.__init__(self)
        self.killed = set()
        self.spawned = defaultdict(list)
        self.next = {}
        self._vars = set()
        self(prog)
    def __call__ (self, prog) :
        exec(prog, self)
        self._vars.update(self.killed)
        for l in self.spawned.values() :
            self._vars.update(l)
    def __getitem__ (self, name) :
        if name in self :
            return dict.__getitem__(self, name)
        else :
            pid = self[name] = ParentPid(name, self)
            return pid
    def __setitem__ (self, name, value) :
        if isinstance(value, ChildPid) :
            self.spawned[value.parent.name].append(name)
        dict.__setitem__(self, name, value)
    def vars (self) :
        return set(self._vars)

@snakes.plugins.plugin("snakes.nets",
                       depends=["snakes.plugins.let",
                                "snakes.plugins.status"])
def extend (module) :
    snk = module
    class Transition (snk.Transition) :
        def __init__ (self, name, guard=None, **args) :
            self.pids = PidEnv(args.pop("pids", ""))
            vars = WordSet(self.pids.vars())
            if self.pids.spawned :
                assign = []
                for parent, children in self.pids.spawned.items() :
                    pidcount = vars.fresh(add=True, base="next_%s" % parent)
                    self.pids.next[parent] = pidcount
                    for n, child in enumerate(children) :
                        assign.append("%s=%s.next(%s+%s)"
                                      % (child, parent, n, pidcount))
                if guard is None :
                    guard = snk.Expression("newpids(%s)" % ", ".join(assign))
                else :
                    guard = guard & snk.Expression("newpids(%s)"
                                                   % ", ".join(assign))
            snk.Transition.__init__(self, name, guard, **args)
        def vars (self) :
            return self.pids.vars() | snk.Transition.vars(self)
    class PetriNet (snk.PetriNet) :
        def __init__ (self, name, **args) :
            snk.PetriNet.__init__(self, name, **args)
            self.globals["newpids"] = self.globals["let"]
            self.nextpids, nextpids = None, args.pop("nextpids", "nextpids")
            self.add_place(snk.Place(nextpids, [], tNextPid,
                                     status=snk.buffer(nextpids)))
            self.nextpids = nextpids
        def copy (self, name=None) :
            if name is None :
                name = self.name
            result = self.__class__(name)
            result._declare = self._declare[:]
            result.globals = self.globals.copy()
            for place in self.place() :
                if place.name != self.nextpids :
                    result.add_place(place.copy())
            for trans in self.transition() :
                result.add_transition(trans.copy())
                for place, label in trans.input() :
                    result.add_input(place.name, trans.name, label.copy())
                for place, label in trans.output() :
                    result.add_output(place.name, trans.name, label.copy())
            return result
        def add_place (self, place, **args) :
            if place.name == self.nextpids :
                raise ConstraintError("reserved place name %r"
                                      % self.nextpids)
            snk.PetriNet.add_place(self, place, **args)
        def add_transition (self, trans, **args) :
            snk.PetriNet.add_transition(self, trans, **args)
            cons, prod = {}, {}
            for parent, children in trans.pids.spawned.items() :
                pidcount = trans.pids.next[parent]
                cons[parent] = snk.Tuple([snk.Variable(parent),
                                          snk.Variable(pidcount)])
                prod[parent] = snk.Tuple([snk.Variable(parent),
                                          snk.Expression("%s+%s" %
                                                         (pidcount,
                                                          len(children)))])
                for num, child in enumerate(children) :
                    prod[child] = snk.Tuple([snk.Variable(child),
                                             snk.Value(0)])
            for pid in trans.pids.killed :
                prod.pop(pid, None)
            if len(cons) > 1 :
                self.add_input(self.nextpids, trans.name,
                               snk.MultiArc(cons.values()))
            elif len(cons) == 1 :
                self.add_input(self.nextpids, trans.name,
                               iter(cons.values()).next())
            if len(prod) > 1 :
                self.add_output(self.nextpids, trans.name,
                                snk.MultiArc(prod.values()))
            elif len(cons) == 1 :
                self.add_output(self.nextpids, trans.name,
                                iter(prod.values()).next())
    return PetriNet, Transition, Pid, ("tPid", tPid), ("tNextPid", tNextPid)
