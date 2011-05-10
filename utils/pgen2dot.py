"""Draws a dependency graph of non-terminals in a pgen grammar
(pygraphviz required).

Usage: python pgen2dot.py INFILE OUTFILE [ENGINE [OPTION=VAL]...]
"""

import sys, string, os.path
import pygraphviz as gv
import snakes.lang.pgen as pgen

if len(sys.argv) < 3 :
    print("Usage: python pgen2dot.py INFILE OUTFILE [ENGINE [OPTION=VAL]...]")
    sys.exit(1)
elif len(sys.argv) >= 4 :
    engine = sys.argv[3]
else :
    engine = "dot"

nodes = set()
edges = set()

def walk (st, lex, rule=None) :
    tok, children = st
    if tok == pgen.PgenParser.RULE :
        rule = children[0][0]
        nodes.add(rule)
        for child in children[1:] :
            walk(child, lex, rule)
    elif isinstance(tok, str) and tok.strip() and tok[0] in string.ascii_lowercase :
        nodes.add(tok)
        if rule is not None :
            edges.add((rule, tok))
    else :
        for child in children :
            walk(child, lex, rule)

st, lex = pgen.PgenParser.parse(sys.argv[1])
walk(st, lex)

g = gv.AGraph(directed=True)
g.add_edges_from(edges)
g.graph_attr["overlap"] = "false"
g.graph_attr["splines"] = "true"
for arg in sys.argv[4:] :
    key, val = arg.split("=", 1)
    g.graph_attr[key] = val
g.draw(sys.argv[2], prog=engine)
