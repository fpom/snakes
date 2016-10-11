import sys, optparse, os.path, webbrowser
import pdb, traceback
import snakes.plugins
from snakes.utils.abcd.build import Builder
from snakes.lang.abcd.parser import parse
from snakes.lang.pgen import ParseError
from snakes.utils.abcd import CompilationError, DeclarationError
from snakes.utils.abcd.simul import Simulator, ABCDSimulator
from snakes.utils.abcd.checker import Checker
from snakes.utils.abcd.html import build as html
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
    sys.stdout.write("abcd: %s\n" % message.strip())
    sys.stdout.flush()

def err (message) :
    sys.stderr.write("abcd: %s\n" % message.strip())
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

opt = optparse.OptionParser(prog="abcd",
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
opt.add_option("-a", "--all-names",
               dest="allnames", action="store_true", default=False,
               help="draw control-flow places names (default: hide)")
opt.add_option("--debug",
               dest="debug", action="store_true", default=False,
               help="launch debugger on compiler error (default: no)")
opt.add_option("--progress",
               dest="progress", action="store_true", default=False,
               help="show progression during long operations (default: no)")
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
opt.add_option("-H", "--html",
               dest="html", action="store", default=None,
               help="save net as HTML",
               metavar="OUTFILE")
opt.add_option("--check",
               dest="check", action="store_true", default=False,
               help="check assertions")

def getopts (args) :
    global options, abcd, tmp
    (options, args) = opt.parse_args(args)
    plugins = []
    for p in options.plugins :
        plugins.extend(t.strip() for t in p.split(","))
    if "ops" not in options.plugins :
        plugins.append("ops")
    if "labels" not in plugins :
        plugins.append("labels")
    for engine in gv_engines :
        gvopt = getattr(options, "gv%s" % engine)
        if gvopt and "gv" not in plugins :
            plugins.append("gv")
            break
    if (options.html or options.simul) and "gv" not in plugins :
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
    abcd = args[0]
    if options.pnml == abcd :
        err("input file also used as output (--pnml)")
        opt.print_help()
        die(ERR_ARG)
    if options.html == abcd :
        err("input file also used as output (--html)")
        opt.print_help()
        die(ERR_ARG)
    for engine in gv_engines :
        if getattr(options, "gv%s" % engine) == abcd :
            err("input file also used as output (--%s)" % engine)
            opt.print_help()
            die(ERR_ARG)

##
## drawing nets
##

def place_attr (place, attr) :
    # fix color
    if place.status == snk.entry :
        attr["fillcolor"] = "green"
    elif place.status == snk.internal :
        pass
    elif place.status == snk.exit :
        attr["fillcolor"] = "orange"
    else :
        attr["fillcolor"] = "lightblue"
    # fix shape
    if (not options.allnames
        and place.status in (snk.entry, snk.internal, snk.exit)) :
        attr["shape"] = "circle"
    # render marking
    if place._check == snk.tBlackToken :
        count = len(place.tokens)
        if count == 0 :
            marking = " "
        elif count == 1 :
            marking = "&#8226;"
        else :
            marking = "%s&#8226;" % count
    else :
        marking = str(place.tokens)
    # node label
    if (options.allnames
        or place.status not in (snk.entry, snk.internal, snk.exit)) :
        attr["label"] = "%s\\n%s" % (place.name, marking)
    else :
        attr["label"] = "%s" % marking

def trans_attr (trans, attr) :
    pass

def arc_attr (label, attr) :
    if label == snk.Value(snk.dot) :
        del attr["label"]
    elif isinstance(label, snk.Test) :
        attr["arrowhead"] = "none"
        attr["label"] = " %s " % label._annotation
    elif isinstance(label, snk.Flush) :
        attr["arrowhead"] = "box"
        attr["label"] = " %s " % label._annotation


def draw (net, target, engine="dot") :
    try :
        return net.draw(target, engine=engine,
                        place_attr=place_attr,
                        trans_attr=trans_attr,
                        arc_attr=arc_attr)
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

def simulate (source, filename="<string>") :
    global options, snk
    getopts(["--simul", filename])
    node = parse(source, filename=filename)
    snk = snakes.plugins.load(options.plugins, "snakes.nets", "snk")
    build = Builder(snk)
    net = build.build(node)
    net.label(srcfile=filename, snakes=snk)
    return ABCDSimulator(node, net, draw(net, None))

##
## main
##

def main (args=sys.argv[1:], src=None) :
    global options, snk
    # get options
    try:
        if src is None :
            getopts(args)
        else :
            getopts(list(args) + ["<string>"])
    except SystemExit :
        raise
    except :
        die(ERR_OPT, str(sys.exc_info()[1]))
    # read source
    if src is not None :
        source = src
    else :
        try :
            source = open(abcd).read()
        except :
            die(ERR_IO, "could not read input file %r" % abcd)
    # parse
    try :
        node = parse(source, filename=abcd)
    except ParseError :
        die(ERR_PARSE, str(sys.exc_info()[1]))
    except :
        bug()
    # compile
    dirname = os.path.dirname(abcd)
    if dirname and dirname not in sys.path :
        sys.path.append(dirname)
    elif "." not in sys.path :
        sys.path.append(".")
    try :
        snk = snakes.plugins.load(options.plugins, "snakes.nets", "snk")
    except :
        die(ERR_PLUGIN, str(sys.exc_info()[1]))
    build = Builder(snk)
    try :
        net = build.build(node)
        net.label(srcfile=abcd, snakes=snk)
    except (CompilationError, DeclarationError) :
        die(ERR_COMPILE, str(sys.exc_info()[1]))
    except :
        bug()
    # output
    if options.pnml :
        save_pnml(net, options.pnml)
    for engine in gv_engines :
        target = getattr(options, "gv%s" % engine)
        if target :
            draw(net, target, engine)
    if options.html :
        try :
            html(abcd, node, net, draw(net, None), options.html)
        except :
            bug()
    trace, lineno = [], None
    if options.check :
        states, lineno, trace = Checker(net, options.progress).run()
        if options.progress :
            print("%s states explored" % states)
    if options.simul :
        engine = "dot"
        for eng in gv_engines :
            if getattr(options, "gv%s" % eng) :
                engine = eng
                break
        try :
            simul = Simulator(node, net, draw(net, None, engine), options.port)
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
