from snakes.utils.simul import BaseSimulator, BaseHTTPSimulator

class AndySimulator (BaseSimulator) :
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

#class Simulator (BaseHTTPSimulator) :
#    def __init__ (self, **system) :
#        simul = AndySimulator(**system)
#        BaseHTTPSimulator.__init__(self, simulator=simul)

class Simulator (BaseHTTPSimulator) :
    def __init__ (self, net, port) :
        simul = AndySimulator(net)
        BaseHTTPSimulator.__init__(self, net, simulator=simul, port=port)
#    def init_model (self) :
#        return self.res["model.html"] % self.simul.info
#    def init_ui (self) :
#        return BaseHTTPSimulator.init_ui(self)[:-1] + [{
#            "label" : "Show net",
#            "id" : "ui-shownet",
#            "href" : "#",
#            "script" : "dialog($('#model .petrinet').html())"
#            }]

