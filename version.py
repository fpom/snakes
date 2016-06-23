import sys, os
sys.path.insert(0, ".")
import snakes

def check () :
    VERSION = open("VERSION").read().strip()
    if VERSION == snakes.version :
        sys.exit(0)
    else :
        print("VERSION=%s / snakes.version=%s" % (VERSION, snakes.version))
        sys.exit(1)

def next () :
    old = snakes.version
    ver = [int(v) for v in old.split(".")]
    ver[-1] += 1
    new = ".".join(str(v) for v in ver)
    with open("VERSION", "w") as out :
        out.write("%s\n" % new)
    os.system("sed -i.bak 's/%s/%s/' snakes/__init__.py" % (old, new))

if __name__ == "__main__" :
    if sys.argv[1:] == ["check"] :
        check()
    elif sys.argv[1:] == ["next"] :
        next()
    else :
        print("usage: python version.py [check|next]")
        sys.exit(255)
