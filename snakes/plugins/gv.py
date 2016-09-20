"""Adds methods to draw `PetriNet` and `StateGraph` instances using
GraphViz.

For example, let's first define a Petri net:

>>> import snakes.plugins
>>> snakes.plugins.load('gv', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> n = PetriNet('N')
>>> n.add_place(Place('p00', [0]))
>>> n.add_transition(Transition('t10'))
>>> n.add_place(Place('p11'))
>>> n.add_transition(Transition('t01'))
>>> n.add_input('p00', 't10', Variable('x'))
>>> n.add_output('p11', 't10', Expression('x+1'))
>>> n.add_input('p11', 't01', Variable('y'))
>>> n.add_output('p00', 't01', Expression('y-1'))

Thanks to plugin `gv`, we can draw it using the various engines of
GraphViz; we can also draw the state graph:

>>> for engine in ('neato', 'dot', 'circo', 'twopi', 'fdp') :
...     n.draw(',test-gv-%s.png' % engine, engine=engine)
>>> s = StateGraph(n)
>>> s.build()
>>> s.draw(',test-gv-graph.png')

The plugin also allows to layout the nodes without drawing the net
(this is only available for `PetriNet`, not for `StateGraph`). We
first move every node to position `(-100, -100)`; then, we layout the
net; finally, we check that every node has indeed been moved away from
where we had put it:

>>> for node in n.node() :
...     node.pos.moveto(-100, -100)
>>> all(node.pos.x == node.pos.y == -100 for node in n.node())
True
>>> n.layout()
>>> any(node.pos.x == node.pos.y == -100 for node in n.node())
False

@note: setting nodes position has no influence on how a net is drawn:
    GraphViz will redo the layout in any case. Method `layout` is here
    just in the case you would need a layout of your nets.
@note: this plugin depens on plugins `pos` and `clusters` (that are
    automatically loaded)
"""

import os, os.path, subprocess, collections, codecs
import snakes.plugins
from snakes.plugins.clusters import Cluster
from snakes.compat import *

# apidoc skip
class Graph (Cluster) :
    def __init__ (self, attr) :
        Cluster.__init__(self)
        self.attributes = {}
        self.attr = dict(style="invis")
        self.attr.update(attr)
        self.edges = collections.defaultdict(list)
    def add_node (self, node, attr) :
        self.attributes[node] = attr
        Cluster.add_node(self, node)
    def add_edge (self, src, dst, attr) :
        self.edges[src, dst].append(attr)
    def has_edge (self, src, dst) :
        if (src, dst) in self.edges :
            return True
        for child in self.children() :
            if child.has_edge(src, dst) :
                return True
        return False
    def _dot_attr (self, attr, tag=None) :
        if tag is None :
            tag = ""
        else :
            tag = "%s " % tag
        return (["%s[" % tag,
                 ["%s=%s" % (key, self.escape(unicode(val)))
                  for key, val in attr.items()],
                 "];"])
    def _dot (self) :
        body = []
        lines = ["subgraph %s {" % self, self._dot_attr(self.attr, "graph"),
                 body, "}"]
        for node in self.nodes() :
            body.append(node)
            body.append(self._dot_attr(self.attributes[node]))
        for child in self.children() :
            body.extend(child._dot())
        for (src, dst), lst in self.edges.items() :
            for attr in lst :
                body.append("%s -> %s" % (src, dst))
                body.append(self._dot_attr(attr))
        return lines
    def _dot_text (self, lines, indent=0) :
        for l in lines :
            if isinstance(l, (str, unicode)) :
                yield " "*indent*2 + l
            else :
                for x in self._dot_text(l, indent+1) :
                    yield x
    def dot (self) :
        self.done = set()
        return "\n".join(self._dot_text(["digraph {",
#                                         'charset="UTF-8"',
                                         ['node [label="N",'
                                          ' fillcolor="#FFFFFF",'
                                          ' fontcolor="#000000",'
                                          ' style=filled];',
                                          'edge [style="solid"];',
                                          'graph [splines="true",'
                                          ' overlap="false"];'],
                                         self._dot(),
                                         "}"]))
    def escape (self, text) :
        if text.startswith("<") and text.endswith(">") :
            return text
        else :
            return '"%s"' % text.replace('"', r'\"')
    def render (self, filename, engine=None, debug=False) :
        if engine is None :
            engine = getattr(self, "engine", "dot")
        if engine not in ("dot", "neato", "twopi", "circo", "fdp") :
            raise ValueError("unknown GraphViz engine %r" % engine)
        with codecs.open(filename + ".dot", "w", "utf-8") as outfile :
            outfile.write(self.dot())
        if debug :
            dot = subprocess.Popen([engine, "-T" + filename.rsplit(".", 1)[-1],
                                    "-o" + filename, outfile.name],
                                   stdin=subprocess.PIPE)
        else :
            dot = subprocess.Popen([engine, "-T" + filename.rsplit(".", 1)[-1],
                                    "-o" + filename, outfile.name],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        stdout, stderr = dot.communicate()
        if not debug :
            os.unlink(outfile.name)
        if dot.returncode != 0 :
            if (stdout or "").strip() + (stderr or "").strip() :
                stdout = "\n*** Original error message follows ***\n " + stdout
            raise IOError("%s exited with status %s%s"
                          % (engine, dot.returncode, stdout))
    def layout (self, engine="dot", debug=False) :
        if engine not in ("dot", "neato", "twopi", "circo", "fdp") :
            raise ValueError("unknown GraphViz engine %r" % engine)
        if debug :
            dot = subprocess.Popen([engine, "-Tplain"],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        else :
            dot = subprocess.Popen([engine, "-Tplain"],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        if PY3 :
            out, err = dot.communicate(bytes(self.dot(),
                                             snakes.defaultencoding))
            out = out.decode(snakes.defaultencoding)
        else :
            out, err = dot.communicate(self.dot())
        if dot.returncode != 0 :
            raise IOError("%s exited with status %s"
                          % (engine, dot.returncode))
        for line in (l.strip() for l in out.splitlines()
                     if l.strip().startswith("node")) :
            node, name, x, y, rest = line.split(None, 4)
            yield name, float(x), float(y)

@snakes.plugins.plugin("snakes.nets",
                       depends=["snakes.plugins.clusters",
                                "snakes.plugins.pos"])
def extend (module) :
    class PetriNet (module.PetriNet) :
        "An extension with methods `draw` and `layout`"
        def draw (self, filename, engine="dot", debug=False,
                  graph_attr=None, cluster_attr=None,
                  place_attr=None, trans_attr=None, arc_attr=None) :
            """Draw the Petri net to a picture file. How the net is
            rendered can be controlled using the arguments `..._attr`.
            For instance, to draw place in red with names in
            uppercase, and hide True guards, we can proceed as
            follows:

            >>> import snakes.plugins
            >>> snakes.plugins.load('gv', 'snakes.nets', 'nets')
            <module ...>
            >>> from nets import *
            >>> n = PetriNet('N')
            >>> n.add_place(Place('p'))
            >>> n.add_transition(Transition('t'))
            >>> n.add_input('p', 't', Value(dot))
            >>> def draw_place (place, attr) :
            ...     attr['label'] = place.name.upper()
            ...     attr['color'] = '#FF0000'
            >>> def draw_transition (trans, attr) :
            ...     if str(trans.guard) == 'True' :
            ...         attr['label'] = trans.name
            ...     else :
            ...         attr['label'] = '%s\\n%s' % (trans.name, trans.guard)
            >>> n.draw(',net-with-colors.png',
            ...        place_attr=draw_place, trans_attr=draw_transition)

            @param filename: the name of the image file to create
            @type filename: `str`
            @param engine: the layout engine to use: `'dot'` (default),
                `'neato'`, `'circo'`, `'twopi'` or `'fdp'`
            @type engine: `str`
            @param place_attr: a function to format places, it will be
                called with the place and its attributes dict as
                parameters
            @type place_attr: `callable`
            @param trans_attr: a function to format transitions, it
                will be called with the transition and its attributes
                dict as parameters
            @type trans_attr: `callable`
            @param arc_attr: a function to format arcs, it will be
                called with the label and its attributes dict as
                parameters
            @type arc_attr: `callable`
            @param cluster_attr: a function to format clusters of
                nodes, it will be called with the cluster and its
                attributes dict as parameters
            @type cluster_attr: `callable`
            """
            nodemap = dict((node.name, "node_%s" % num)
                           for num, node in enumerate(self.node()))
            g = self._copy(nodemap, self.clusters, cluster_attr,
                           place_attr, trans_attr)
            g.engine = engine
            self._copy_edges(nodemap, g, arc_attr)
            if graph_attr :
                graph_attr(self, g.attr)
            if filename is not None :
                g.render(filename, engine, debug)
            g.nodemap = nodemap
            return g
        def _copy (self, nodemap, sub, cluster_attr, place_attr, trans_attr) :
            attr = dict(style="invis")
            if cluster_attr :
                cluster_attr(sub, attr)
            graph = Graph(attr)
            for name in sub.nodes() :
                if self.has_place(name) :
                    node = self.place(name)
                    attr = dict(shape="ellipse",
                                label="%s\\n%s" % (node.name, node.tokens))
                    if place_attr :
                        place_attr(node, attr)
                else :
                    node = self.transition(name)
                    attr = dict(shape="rectangle",
                                label="%s\\n%s" % (node.name, str(node.guard)))
                    if trans_attr :
                        trans_attr(node, attr)
                attr["tooltip"] = node.name
                attr["id"] = nodemap[name]
                graph.add_node(nodemap[name], attr)
            for child in sub.children() :
                graph.add_child(self._copy(nodemap, child, cluster_attr,
                                           place_attr, trans_attr))
            return graph
        def _copy_edges (self, nodemap, graph, arc_attr) :
            for trans in self.transition() :
                for place, label in trans.input() :
                    attr = dict(arrowhead="normal",
                                label=" %s " % label)
                    if arc_attr :
                        arc_attr(label, attr)
                    graph.add_edge(nodemap[place.name], nodemap[trans.name],
                                   attr)
                for place, label in trans.output() :
                    attr = dict(arrowhead="normal",
                                label=" %s " % label)
                    if arc_attr :
                        arc_attr(label, attr)
                    graph.add_edge(nodemap[trans.name], nodemap[place.name],
                                   attr)
        def layout (self, xscale=1.0, yscale=1.0, engine="dot",
                    debug=False, graph_attr=None, cluster_attr=None,
                    place_attr=None, trans_attr=None, arc_attr=None) :
            """Layout the nodes of the Petri net by calling GraphViz
            and reading back the picture it creates. The effect is to
            change attributes `pos` (see plugin `pos`) for every node
            according to the positions calculated by GraphViz.

            @param xscale: how much the image is scaled in the
                horizontal axis after GraphViz has done the layout
            @type xscale: `float`
            @param yscale: how much the image is scaled in the
                vertical axis after GraphViz has done the layout
            @type yscale: `float`
            @param filename: the name of the image file to create
            @type filename: `str`
            @param engine: the layout engine to use: `'dot'` (default),
                `'neato'`, `'circo'`, `'twopi'` or `'fdp'`
            @type engine: `str`
            @param place_attr: a function to format places, it will be
                called with the place and its attributes dict as
                parameters
            @type place_attr: `callable`
            @param trans_attr: a function to format transitions, it
                will be called with the transition and its attributes
                dict as parameters
            @type trans_attr: `callable`
            @param arc_attr: a function to format arcs, it will be
                called with the label and its attributes dict as
                parameters
            @type arc_attr: `callable`
            @param cluster_attr: a function to format clusters of
                nodes, it will be called with the cluster and its
                attributes dict as parameters
            @type cluster_attr: `callable`
            """
            g = self.draw(None, engine, debug, graph_attr, cluster_attr,
                          place_attr, trans_attr, arc_attr)
            node = dict((v, k) for k, v in g.nodemap.items())
            for n, x, y in g.layout(engine, debug) :
                self.node(node[n]).pos.moveto(x*xscale, y*yscale)
    class StateGraph (module.StateGraph) :
        "An extension with a method `draw`"
        def draw (self, filename, engine="dot", debug=False,
                  node_attr=None, edge_attr=None, graph_attr=None) :
            """Draw the state graph to a picture file.

            @param filename: the name of the image file to create or
                `None` if only the computed graph is needed
            @type filename: `None` or `str`
            @param engine: the layout engine to use: 'dot' (default),
                'neato', 'circo', 'twopi' or 'fdp'
            @type engine: `str`
            @param node_attr: a function to format nodes, it will be
                called with the state number, the `StateGraph` object
                and attributes dict as parameters
            @type node_attr: `callable`
            @param edge_attr: a function to format edges, it will be
                called with the transition, its mode and attributes
                dict as parameters
            @type trans_attr:
                `callable`
            @param graph_attr: a function to format grapg, it will be
                called with the state graphe and attributes dict as
                parameters
            @type graph_attr: `callable`
            """
            attr = dict(style="invis",
                        splines="true")
            if graph_attr :
                graph_attr(self, attr)
            graph = Graph(attr)
            for state in self._done :
                self.goto(state)
                attr = dict(shape="rectangle")
                if state == 0 :
                    attr["shape"] = ""
                if node_attr :
                    node_attr(state, self, attr)
                graph.add_node(str(state), attr)
                for succ, (trans, mode) in self.successors().items() :
                    attr = dict(arrowhead="normal",
                                label="%s\\n%s" % (trans.name, mode))
                    if edge_attr :
                        edge_attr(trans, mode, attr)
                    graph.add_edge(str(state), str(succ), attr)
            if filename is None :
                return graph
            else :
                graph.render(filename, engine, debug)
    return PetriNet, StateGraph
