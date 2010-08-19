from snakes.nets import *

n = loads(",railroad.pnml")
g = StateGraph(n)
for s in g :
    m = g.net.get_marking()
    if ("train().crossing" in m
        and True in m["train().crossing"]
        and "closed" not in m["gate().state"]) :
        print s, m
print "checked", len(g), "states"
