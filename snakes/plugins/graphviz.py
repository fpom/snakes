"""Draw Petri nets using GraphViz

 - depends on the plugin C{pos} to have a position for the nodes

 - adds a method C{draw} to C{PetriNet} and C{StateGraph} that creates
   a drawing of the object in a file.

@warning: this module makes use of C{os.system} to call C{dot} and
C{neato} in order to render the images. It is easy for a malicious
script to run arbitrary commands. Take care before to run a script
that you did not write yourself.

>>> import snakes.plugins
>>> snakes.plugins.load('graphviz', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> n = PetriNet('N')
>>> n.add_place(Place('p00', [0]))
>>> n.add_transition(Transition('t10', pos=(1, 0)))
>>> n.add_place(Place('p11', pos=(1, 1)))
>>> n.add_transition(Transition('t01', pos=(0, 1)))
>>> n.add_input('p00', 't10', Variable('x'))
>>> n.add_output('p11', 't10', Expression('x+1'))
>>> n.add_input('p11', 't01', Variable('y'))
>>> n.add_output('p00', 't01', Expression('y-1'))
>>> n.draw(',test-graphviz-net.png')

>>> for engine in ('neato', 'dot', 'circo', 'twopi', 'fdp') :
...     n.draw(',test-graphviz-%s.png' % engine, layout=True, engine=engine)

>>> s = StateGraph(n)
>>> s.draw(',test-graphviz-graph.png')

The last command should produce the expected drawing but also prints
two warnings about the size of the nodes.
"""

import os, os.path
import snakes.plugins

@snakes.plugins.plugin("snakes.nets",
                       depends=["snakes.plugins.pos"])
def extend (module) :
    class PetriNet (module.PetriNet) :
        "An extension with a method C{draw}"
        def draw (self, filename, scale=72.0, nodesize=0.5,
                  engine="neato", layout=False,
                  print_trans=None, print_place=None,
                  print_arc=None, print_tokens=None) :
            if print_trans is None :
                def print_trans (trans, net) :
                    if str(trans.guard) == "True" :
                        return trans.name
                    else :
                        return "%s\\n%s" % (trans.name, str(trans.guard))
            if print_place is None :
                def print_place (place, net) :
                    if str(place.checker()) == "tAll" :
                        return place.name
                    else :
                        return "%s\\n%s" % (place.name, str(place.checker()))
            if print_arc is None :
                def print_arc (label, place, trans, input, net) :
                    if str(label) == "dot" :
                        return ""
                    else :
                        return str(label)
            if print_tokens is None :
                def print_tokens (tokens, place, net) :
                    if tokens.size() == 0 :
                        return ""
                    else :
                        return str(tokens)
            name, format = os.path.splitext(os.path.basename(filename))
            format = format.lstrip(".")
            if format == "eps" :
                format = "ps"
            if format == "dot" :
                out = open(filename, "w")
            else :
                out = open(filename + ".dot", "w")
            print >>out, 'digraph "(%s)" {' % self.name
            for place in self.place() :
                print >>out, '"%s" [' % place.name
                print >>out, '  label     = "%s"' % (print_tokens(place.tokens,
                                                                  place, self))
                print >>out, '  shape     = "circle"'
                print >>out, '  height    = "%s"' % nodesize
                print >>out, '  width     = "%s"' % nodesize
                print >>out, '  fixedsize = "true"'
                if not layout :
                    print >>out, '  pin       = "true"'
                    print >>out, '  pos       = "%s,%s"' % (scale * place.pos.x,
                                                            scale * place.pos.y)
                print >>out, ']'
                print >>out, '"%s" -> "%s" [' % (place.name, place.name)
                print >>out, '  taillabel     = "%s"' % (print_place(place, self))
                print >>out, '  color         = "transparent"'
                print >>out, '  labeldistance = "1.6"'
                print >>out, '  labelangle    = "45"'
                print >>out, ']'
            for trans in self.transition() :
                print >>out, '"%s" [' % trans.name
                print >>out, '  label     = "%s"' % (print_trans(trans, self))
                print >>out, '  shape     = "rectangle"'
                print >>out, '  height    = "%s"' % nodesize
                print >>out, '  width     = "%s"' % nodesize
                print >>out, '  fixedsize = "true"'
                if not layout :
                    print >>out, '  pin       = "true"'
                    print >>out, '  pos       = "%s,%s"' % (scale * trans.pos.x,
                                                            scale * trans.pos.y)
                print >>out, ']'
                for place, label in trans.output() :
                    print >>out, '"%s" -> "%s" [' % (trans.name, place.name)
                    print >>out, '  label      = "%s"' % (print_arc(label, place,
                                                                    trans, False,
                                                                    self))
                    print >>out, ']'
                for place, label in trans.input() :
                    print >>out, '"%s" -> "%s" [' % (place.name, trans.name)
                    print >>out, '  label      = "%s"' % (print_arc(label, place,
                                                                    trans, True,
                                                                    self))
                    print >>out, ']'
            print >>out, '}'
            out.close()
            if format != "dot" :
                if layout :
                    command = "%s -q -T%s -o %s %s"
                else :
                    command = "%s -q -n -T%s -o %s %s"
                if os.system(command
                             % (engine, format, filename, out.name)) == 0 :
                    os.remove("%s.dot" % filename)
    class StateGraph (module.StateGraph) :
        "An extension with a method C{draw}"
        def draw (self, filename, scale=72.0, nodesize=0.5, landscape=True,
                  engine="dot", print_state=None, print_arc=None) :
            if print_state is None :
                def print_state (state, graph) :
                    return "%u\\n%s" % (state, str(graph.net.get_marking()))
            if print_arc is None :
                def print_arc (source, target, trans, mode, graph) :
                    return "%s\\n%s" % (trans, str(mode))
            self.build()
            name, format = os.path.splitext(os.path.basename(filename))
            format = format.lstrip(".")
            if format == "eps" :
                format = "ps"
            if format == "dot" :
                out = open(filename, "w")
            else :
                out = open(filename + ".dot", "w")
            print >>out, 'digraph "(%s)" {' % self.net.name
            if landscape :
                print >>out, "rankdir=LR"
            else :
                print >>out, "rankdir=BT"
            for state in self :
                print >>out, '"%u" [' % state
                print >>out, '  label     = "%s"' % (print_state(state, self))
                print >>out, '  shape     = "rectangle"'
                print >>out, ']'
                for num, (trans, mode) in self.successors().items() :
                    print >>out, '"%u" -> "%u" [' % (state, num)
                    print >>out, '  label      = "%s"' % (print_arc(state, num,
                                                                    trans, mode,
                                                                    self))
                    print >>out, ']'
            print >>out, '}'
            out.close()
            if format != "dot" :
                if os.system("%s -q -T%s -o %s %s"
                             % (engine, format, filename, out.name)) == 0 :
                    os.remove("%s.dot" % filename)
    return PetriNet, StateGraph
