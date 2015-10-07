import sys, optparse, os.path, webbrowser
import pdb, traceback
import snakes.plugins
from snakes.utils.andy import CompilationError, DeclarationError
from snakes.utils.andy.simul import Simulator, AndySimulator
from snakes.utils.andy.andy import andy2snakes
from snakes.utils.simul.html import json

##
## error messages
##

options = None

ERR_ARG = 1
ERR_OPT = 2
ERR_IO = 3
ERR_PARSE = 4
ERR_PLUGIN = 5
ERR_COMPILE = 6
ERR_OUTPUT = 7
ERR_BUG = 255

def log (message) :
    sys.stdout.write("andy: %s\n" % message.strip())
    sys.stdout.flush()

def err (message) :
    sys.stderr.write("andy: %s\n" % message.strip())
    sys.stderr.flush()

def die (code, message=None) :
    global options
    if message :
        err(message)
    if options.debug :
        pdb.post_mortem(sys.exc_info()[2])
    else :
        sys.exit(code)

def bug () :
    global options
    sys.stderr.write("""
    ********************************************************************
    *** An unexpected error ocurred. Please report this bug to       ***
    *** <franck.pommereau@gmail.com>, together with the execution    ***
    *** trace below and, if possible, a stripped-down version of the ***
    *** ABCD source code that caused this bug. Thank you for your    ***
    *** help in improving SNAKES!                                    ***
    ********************************************************************

""")
    traceback.print_exc()
    if options.debug :
        pdb.post_mortem(sys.exc_info()[2])
    else :
        sys.exit(ERR_BUG)

##
## options parsing
##

gv_engines = ("dot", "neato", "twopi", "circo", "fdp")

opt = optparse.OptionParser(prog="andy",
                            usage="%prog [OPTION]... FILE")
opt.add_option("-l", "--load",
               dest="plugins", action="append", default=[],
               help="load plugin (this option can be repeated)",
               metavar="PLUGIN")
opt.add_option("-p", "--pnml",
               dest="pnml", action="store", default=None,
               help="save net as PNML",
               metavar="OUTFILE")
for engine in gv_engines :
    opt.add_option("-" + engine[0], "--" + engine,
                   dest="gv" + engine, action="store", default=None,
                   help="draw net using '%s' (from GraphViz)" % engine,
                   metavar="OUTFILE")
opt.add_option("--debug",
               dest="debug", action="store_true", default=False,
               help="launch debugger on compiler error (default: no)")
opt.add_option("-s", "--simul",
               dest="simul", action="store_true", default=False,
               help="launch interactive code simulator")
opt.add_option("--headless",
               dest="headless", action="store", default=None,
               help="headless code simulator, with saved parameters",
               metavar="JSONFILE")
opt.add_option("--port",
               dest="port", action="store", default=8000, type=int,
               help="port on which the simulator server runs",
               metavar="PORT")

def getopts (args) :
    global options, andy, tmp
    (options, args) = opt.parse_args(args)
    plugins = []
    for p in options.plugins :
        plugins.extend(t.strip() for t in p.split(","))
    if "labels" not in plugins :
        plugins.append("labels")
    for engine in gv_engines :
        gvopt = getattr(options, "gv%s" % engine)
        if gvopt and "gv" not in plugins :
            plugins.append("gv")
            break
    if (options.simul) and "gv" not in plugins :
        plugins.append("gv")
    options.plugins = plugins
    if len(args) < 1 :
        err("no input file provided")
        opt.print_help()
        die(ERR_ARG)
    elif len(args) > 1 :
        err("more than one input file provided")
        opt.print_help()
        die(ERR_ARG)
    andy = args[0]
    if options.pnml == andy :
        err("input file also used as output (--pnml)")
        opt.print_help()
        die(ERR_ARG)
    for engine in gv_engines :
        if getattr(options, "gv%s" % engine) == andy :
            err("input file also used as output (--%s)" % engine)
            opt.print_help()
            die(ERR_ARG)

##
## drawing nets
##

def draw (net, target, engine="dot") :
    try :
        return net.draw(target, engine=engine)
    except :
        die(ERR_OUTPUT, str(sys.exc_info()[1]))

##
## save pnml
##

def save_pnml (net, target) :
    try :
        out = open(target, "w")
        out.write(snk.dumps(net))
        out.close()
    except :
        die(ERR_OUTPUT, str(sys.exc_info()[1]))

##
## simulator (not standalone)
##

def simulate (entities, potential, obligatory, filename='<string>') :
    global options, snk
    getopts(["--simul", filename])
    snk = snakes.plugins.load(options.plugins, "snakes.nets", "snk")
    net = andy2snakes(snk, entities, potential, obligatory)
    net.label(srcfile=filename, snakes=snk)
    return AndySimulator(net)

##
## main
##

def main (args=sys.argv[1:]) :
    global options, snk
    # get options
    try:
        getopts(args)
    except SystemExit :
        raise
    except :
        die(ERR_OPT, str(sys.exc_info()[1]))
    # read andy spec
    try:
        env = {}
        execfile(andy, env)
        del env['__builtins__']
    except:
        die(ERR_IO, "could not read input file %r" % andy)
    # compile to net
    dirname = os.path.dirname(andy)
    if dirname and dirname not in sys.path :
        sys.path.append(dirname)
    elif "." not in sys.path :
        sys.path.append(".")
    try :
        snk = snakes.plugins.load(options.plugins, "snakes.nets", "snk")
    except :
        die(ERR_PLUGIN, str(sys.exc_info()[1]))

    try:
        net = andy2snakes(snk, env['entities'], env['potential'],
                          env['obligatory'])
    except:
        bug()

    # output
    if options.pnml :
        save_pnml(net, options.pnml)
    for engine in gv_engines :
        target = getattr(options, "gv%s" % engine)
        if target :
            draw(net, target, engine)
    trace, lineno = [], None
    if options.simul :
        try :
            simul = Simulator(net, options.port)
        except :
            bug()
        simul.start()
        if options.headless :
            with open(options.headless, "w") as out :
                out.write(json({"res" : "%sr" % simul.url,
                                "url" : simul.url,
                                "key" : simul.server.httpd.key,
                                "host" : "127.0.0.1",
                                "port" : simul.port}))
        else :
            webbrowser.open(simul.url)
        simul.wait()
    elif trace :
        if lineno is None :
            print("unsafe execution:")
        else :
            asserts = dict((a.lineno, a) for a in net.label("asserts"))
            print("line %s, %r failed:"
                  % (lineno, asserts[lineno].st.source()))
        for trans, mode in trace :
            print("  %s %s" % (trans, mode))
    return net

if __name__ == "__main__" :
    main()
