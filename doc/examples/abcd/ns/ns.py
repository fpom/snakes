import snakes.plugins
snakes.plugins.load("status", "snakes.nets", "nets")
from nets import *
from dolev_yao import Nonce

ns = loads(",ns.pnml")
states = StateGraph(ns)

for s in states :
    m = states.net.get_marking()
    # skip non final markings
    if "bob.x" not in m or "alice.x" not in m :
        continue
    # get Alice's and Bob's peers ids
    bp = list(m["bob.peer"])[0]
    ap = list(m["alice.peer"])[0]
    # violation of mutual authentication
    if bp == 1 and ap != 2 :
        print(s, "A(1) <=> %s ; B(2) <=> %s" % (ap, bp))
        print(m)

print(len(states), "states")
