import tempfile, anydbm, os
from snakes.utils.simul import *
import snakes.utils.abcd.html as html

class ABCDSimulator (BaseSimulator) :
    def __init__ (self, net, a2html, n2html, gv) :
        BaseSimulator.__init__(self, net)
        self.tree = {}
        for node in net.node() :
            nid = gv.nodemap[node.name]
            if nid in n2html.n2t :
                self.tree[node.name] = "#" + n2html.n2t[nid]
        self.places = [place.name for place in net.place()
                       if place.name in self.tree]
        self.abcd = {}
        self.transid = []
        for trans in net.transition() :
            nid = gv.nodemap[trans.name]
            self.transid.append(self.tree[trans.name])
            if nid in n2html.n2a :
                self.abcd[trans.name] = ", ".join("#" + i for i in
                                                  n2html.n2a[nid])
    def getstate (self, state) :
        marking = self.states[state]
        modes = dict((t, []) for t in self.transid)
        for i, (trans, mode) in enumerate(marking.modes) :
            modes[self.tree[trans.name]].append({"state" : state,
                                                 "mode" : i,
                                                 "html" : str(mode)})
        return {"id" : state,
                "states" :
                [{"do" : "dropclass",
                  "select" : "#model .active",
                  "class" : "active"}]
                + [{"do" : "addclass",
                    "select" : self.abcd[trans.name],
                    "class" : "active"} for trans, mode in marking.modes]
                + [{"do" : "addclass",
                    "select" : self.tree[trans.name],
                    "class" : "active"} for trans, mode in marking.modes]
                + [{"do" : "settext",
                    "select" : "%s .content" % self.tree[place],
                    "text" : "{}"} for place in self.places
                   if place not in marking]
                + [{"do" : "settext",
                    "select" : "%s .content" % self.tree[place],
                    "text" : str(marking[place])} for place in marking
                   if place in self.tree],
                "modes" : [{"select" : "%s + .modes" % trans,
                            "items" : items}
                           for trans, items in modes.items()],
                }

class Simulator (BaseHTTPSimulator) :
    def __init__ (self, abcd, node, net, gv) :
        a2html = html.ABCD2HTML(node)
        n2html = html.Net2HTML(net, gv, a2html)
        simul = ABCDSimulator(net, a2html, n2html, gv)
        BaseHTTPSimulator.__init__(self, net, simulator=simul)
        self.info = {"filename" :  node.st.filename,
                     "abcd" : a2html.html(),
                     "tree" : n2html.html(),
                     "net" : n2html.svg()}
    def init_model (self) :
        return self.res["model.html"] % self.info
    def init_ui (self) :
        return BaseHTTPSimulator.init_ui(self)[:-1] + [{
            "label" : "Show net",
            "id" : "ui-shownet",
            "href" : "#",
            "script" : "dialog($('#model .petrinet').html())"
            }]
    def init_help (self) :
        help = BaseHTTPSimulator.init_help(self)
        help.update({"#model .abcd" : "ABCD source code",
                     "#model .tree" : "hierarchy of ABCD objects",
                     "#model .petrinet" : "Petri nets semantics"})
        return help
