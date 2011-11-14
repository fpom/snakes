import doctest, sys, os, glob

retcode = 0

import snakes
version = open("VERSION").read().strip()
if snakes.version != version :
    print("Mismatched versions:")
    print("  snakes.version = %r" % snakes.version)
    print("  VERSION = %r" % version)
    sys.exit(1)

def test (module) :
    print("  Testing '%s'" % module.__name__)
    f, t = doctest.testmod(module, #verbose=True,
                           optionflags=doctest.NORMALIZE_WHITESPACE
                           | doctest.REPORT_ONLY_FIRST_FAILURE
                           | doctest.ELLIPSIS)
    return f

modules = ["snakes",
           "snakes.hashables",
           "snakes.lang",
           "snakes.lang.python.parser",
           "snakes.lang.abcd.parser",
           "snakes.lang.ctlstar.parser",
           "snakes.data",
           "snakes.typing",
           "snakes.nets",
           "snakes.pnml",
           "snakes.plugins",
           "snakes.plugins.pos",
           "snakes.plugins.status",
           "snakes.plugins.ops",
           "snakes.plugins.synchro",
           "snakes.plugins.hello",
           "snakes.plugins.gv",
           "snakes.plugins.clusters",
           "snakes.plugins.labels",
           "snakes.utils.abcd.build",
           ]

stop = False
if len(sys.argv) > 1 :
    if sys.argv[1] == "--stop" :
        stop = True
        del sys.argv[1]

doscripts = True
if len(sys.argv) > 1 :
    modules = sys.argv[1:]
    doscripts = False

for modname in modules :
    try :
        __import__(modname)
        retcode = max(retcode, test(sys.modules[modname]))
        if retcode and stop :
            break
    except :
        print("  Could not test %r:" % modname)
        c, e, t = sys.exc_info()
        print("    %s: %s" % (c.__name__, e))

if doscripts :
    for script in (glob.glob("test-scripts/test*.sh")
                   + glob.glob("test-scripts/test*.py")) :
        print("  Running '%s'" % script)
        retcode = max(retcode, os.system(script))
        if retcode and stop :
            break

sys.exit(retcode)
