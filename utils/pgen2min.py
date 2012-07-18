"""Lists unreachable non-terminals in a pgen grammar

Usage: python pgen2min.py INFILE
"""

import sys, string, os.path
import snakes.lang.pgen as pgen
import collections

if len(sys.argv) < 2 :
    print("Usage: python pgen2dot.py INFILE")
    sys.exit(1)

root = None
nodes = set()
edges = collections.defaultdict(set)

def walk (st, lex, rule=None) :
    global root
    tok, children = st
    if tok == pgen.PgenParser.RULE :
        rule = children[0][0]
        if root is None :
            root = rule
        nodes.add(rule)
        for child in children[1:] :
            walk(child, lex, rule)
    elif isinstance(tok, str) and tok.strip() and tok[0] in string.ascii_lowercase :
        nodes.add(tok)
        if rule is not None :
            edges[rule].add(tok)
    else :
        for child in children :
            walk(child, lex, rule)

st, lex = pgen.PgenParser.parse(sys.argv[1])
walk(st, lex)

reached = set()
next = set([root])
while not next.issubset(reached) :
    reached.update(next)
    prev = next
    next = set()
    for n in prev :
        next.update(edges[n])

for node in sorted(nodes - reached) :
    print(node)
