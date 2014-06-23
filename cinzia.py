import snakes.nets as snk
from snakes.utils.simul import BaseSimulator, BaseHTTPSimulator

class CinziaSimulator (BaseSimulator) :
    def __init__ (self, **system) :
        net = snk.PetriNet("counter machine")
        for var, spec in system.items() :
            init, expr = spec.split(":", 1)
            system[var] = snk.Expression(expr)
            net.add_place(snk.Place(var, [int(init)]))
        for var, expr in system.items() :
            trans = "update_" + var
            net.add_transition(snk.Transition(trans))
            for v in set(expr.vars() + [var]) :
                net.add_input(v, trans, snk.Variable(v))
                if v == var :
                    net.add_output(v, trans, expr)
                else :
                    net.add_output(v, trans, snk.Variable(v))
        BaseSimulator.__init__(self, net)
    def getstate (self, state) :
        ret = BaseSimulator.getstate(self, state)
        marking = self.states[state]
        ret["variables"] = dict((place, tokens.items()[0])
                                for place, tokens in marking.items())
        ret["groups"] = ["timed", "even", "odd"]
        modes = []
        for i, (trans, binding) in enumerate(marking.modes) :
            if (state + i) % 5 == 0 :
                groups = ["timed"]
            else :
                groups = []
            modes.append(
                {"state" : state,
                 "mode" : i,
                 "html" : "%s (%s)" % (trans.name[7:], binding),
                 "groups" : groups + ["odd" if (state % 2) else "even"]
                })
        ret["modes"] = [{"select": "#modes", "items": modes}]
        return ret

class CinziaHTTPSimulator (BaseHTTPSimulator) :
    def __init__ (self, **system) :
        simul = CinziaSimulator(**system)
        BaseHTTPSimulator.__init__(self, simulator=simul)

if __name__ == "__main__" :
    import sys, webbrowser
    system = dict(a.split("=", 1) for a in sys.argv[1:])
    simul = CinziaHTTPSimulator(**system)
    simul.start()
    webbrowser.open(simul.url)
    simul.wait()
