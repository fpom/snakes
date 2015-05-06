from snakes.utils.simul import BaseSimulator, BaseHTTPSimulator
import snakes.utils.abcd.html as html

class ABCDSimulator (BaseSimulator) :
    def __init__ (self, node, net, gv) :
        BaseSimulator.__init__(self, net)
        a2html = html.ABCD2HTML(node)
        n2html = html.Net2HTML(net, gv, a2html)
        self.info = {"filename" :  node.st.filename,
                     "abcd" : a2html.html(),
                     "tree" : n2html.html(),
                     "net" : n2html.svg()}
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
    def init (self, state=-1) :
        res = BaseSimulator.init(self, state)
        res.update(self.info)
        res["help"] = self.init_help()
        return res
    def init_help (self) :
        help = BaseSimulator.init_help(self)
        help.update({
            "#model .abcd" : {
                "title" : "Source",
                "content" : "ABCD source code"
            },
            "#model .tree" : {
                "title" : "State",
                "content" : "hierarchy of ABCD objects",
            },
            "#model .petrinet" : {
                "title" : "Net",
                "content" : "Petri nets semantics"
            }})
        return help
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
    def __init__ (self, node, net, gv, port) :
        simul = ABCDSimulator(node, net, gv)
        BaseHTTPSimulator.__init__(self, net, simulator=simul, port=port)
    def init_model (self) :
        return self.res["model.html"] % self.simul.info
    def init_ui (self) :
        return BaseHTTPSimulator.init_ui(self)[:-1] + [{
            "label" : "Show net",
            "id" : "ui-shownet",
            "href" : "#",
            "script" : "dialog($('#model .petrinet').html())"
            }]
