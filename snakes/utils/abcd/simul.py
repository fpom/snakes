from snakes.utils.simul import *

class Simulator (BaseHTTPSimulator) :
    def __init__ (self, abcd, node, net, gv) :
        BaseHTTPSimulator.__init__(self, net)
        self.abcd = abcd
        self.node = node
        self.net = net
        self.gv = gv
    def getstate (self, state) :
        marking = self.states[state]
        # TODO: build HTML for places and modes, linked to the model
        places = {}
        modes = {}
        return {"id" : state,
                "states" : places,
                "modes" : modes}
    def init_model (self) :
        # TODO: build HTML for the model
        return "<h1><tt>%s</tt></h1>" % self.node.st.filename
    def init_ui (self) :
        return BaseHTTPSimulator.init_ui(self)[:-1]
    def init_help (self) :
        help = BaseHTTPSimulator.init_help(self)
        help.update({"#model .abcd" : "ABCD source code",
                     "#model .tree" : "hierarchy of ABCD objects",
                     "#model .net" : "Petri nets semantics"})
        return help

