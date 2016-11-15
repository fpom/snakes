import heapq, time
from snakes.nets import StateGraph
import snakes.lang
import snkast as ast

class Checker (object) :
    def __init__ (self, net, progress) :
        self.p = progress
        self.g = StateGraph(net)
        self.f = [self.build(f) for f in net.label("asserts")]
        if progress :
            if len(self.f) == 0 :
                print("WARNING: no assertion given (computing the state space anyway)")
            elif len(self.f) == 1 :
                print("checking 1 assertion")
            else :
                print("checking %s assertions" % len(self.f))
    def build (self, tree) :
        src = """
def check (_) :
    return %s
""" % tree.st.source()[7:]
        ctx = dict(self.g.net.globals)
        ctx["bounded"] = self.bounded
        ctx["dead"] = self.dead
        exec(src, ctx)
        fun = ctx["check"]
        fun.lineno = tree.lineno
        return fun
    def bounded (self, marking, max) :
        return all(len(marking(p)) == 1 for p in marking)
    def dead (self) :
        for _ in self.g.successors() :
            return False
        return True
    def run (self) :
        start = last = time.time()
        for state in self.g :
            marking = self.g.net.get_marking()
            for place in marking :
                if max(marking(place).values()) > 1 :
                    return len(self.g), None, self.trace(state)
            for check in self.f :
                try :
                    if not check(marking) :
                        return len(self.g), check.lineno, self.trace(state)
                except :
                    pass
            if self.p and time.time() - last >= 5 :
                last = time.time()
                print(" ... %s states explored so far in %.0f seconds"
                      % (len(self.g), last - start))
        return len(self.g), None, None
    def path (self, tgt, src=0) :
        q = [(0, src, ())]
        visited = set()
        while True :
            (c, v1, path) = heapq.heappop(q)
            if v1 not in visited :
                path = path + (v1,)
                if v1 == tgt :
                    return path
                visited.add(v1)
                for v2 in self.g.successors(v1) :
                    if v2 not in visited :
                        heapq.heappush(q, (c+1, v2, path))
    def trace (self, state) :
        path = self.path(state)
        return tuple(self.g.successors(i)[j]
                     for i, j in zip(path[:-1], path[1:]))
