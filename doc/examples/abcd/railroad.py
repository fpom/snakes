import sys

import snakes.plugins
snakes.plugins.load("gv", "snakes.nets", "snk")
from snk import *

n = loads(sys.argv[1])
g = StateGraph(n)
for s in g :
    m = g.net.get_marking()
    # safety property: train present => gates closed
    if ("train().crossing" in m
        and True in m["train().crossing"]
        and "closed" not in m["gate().state"]) :
        print("%s %s" % (s, m))
print("checked %s states" % len(g))

g.draw(sys.argv[1].rsplit(".", 1)[0] + "-states.png")
