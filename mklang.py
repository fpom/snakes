import glob, os, os.path

for src in glob.glob("snakes/lang/*/*.pgen") :
    tgt = os.path.join(os.path.dirname(src), "pgen.py")
    if not os.path.isfile(tgt) or os.path.getmtime(src) > os.path.getmtime(tgt) :
        print("python snakes/lang/pgen.py --output=%s %s" % (tgt, src))
        os.system("python snakes/lang/pgen.py --output=%s %s" % (tgt, src))

for src in glob.glob("snakes/lang/*/*.asdl") :
    tgt = os.path.join(os.path.dirname(src), "asdl.py")
    if not os.path.isfile(tgt) or os.path.getmtime(src) > os.path.getmtime(tgt) :
        print("python snakes/lang/asdl.py --output=%s %s" % (tgt, src))
        os.system("python snakes/lang/asdl.py --output=%s %s" % (tgt, src))
