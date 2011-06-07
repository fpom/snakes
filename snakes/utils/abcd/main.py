import sys, optparse, os.path
import pdb, traceback
import snakes.plugins
from snakes.utils.abcd.build import Builder
from snakes.lang.abcd.parser import parse
from snakes.lang.pgen import ParseError
from snakes.utils.abcd import CompilationError, DeclarationError
from snakes.compat import io

##
## error messages
##

ERR_ARG = 1
ERR_OPT = 2
ERR_IO = 3
ERR_PARSE = 4
ERR_PLUGIN = 5
ERR_COMPILE = 6
ERR_OUTPUT = 7
ERR_BUG = 255

stderr = sys.stderr
stdout = sys.stdout
options = None

def err (message) :
    global stderr
    stderr.write("abcd: %s\n" % message.strip())

def die (code, message=None) :
    global options
    if message :
        err(message)
    c, e, t = sys.exc_info()
    if options is not None and options.debug and t is not None :
        pdb.post_mortem(t)
    else :
        sys.exit(code)

def bug () :
    global stderr, options
    stderr.write("""
    ********************************************************************
    *** An unexpected error ocurred. Please report this bug to       ***
    *** <franck.pommereau@gmail.com>, together with the execution    ***
    *** trace below and, if possible, a stripped-down version of the ***
    *** ABCD source code that caused this bug. Thank you for your    ***
    *** help in improving SNAKES!                                    ***
    ********************************************************************

""")
    traceback.print_exc(None, stderr)
    if options is not None and options.debug :
        pdb.post_mortem(sys.exc_info()[2])
    else :
        sys.exit(ERR_BUG)

##
## options parsing
##

def print_help_and_exit (option, opt, value, parser, exitcode=None) :
    global stdout, stderr
    if exitcode is None :
        parser.print_help(stdout)
    elif exitcode == 0 :
        parser.print_help(stdout)
        sys.exit(0)
    else :
        parser.print_help(stderr)
        sys.exit(exitcode)

gv_engines = ("dot", "neato", "twopi", "circo", "fdp")

opt = optparse.OptionParser(prog="abcd",
                            add_help_option=False,
                            usage="%prog [OPTION]... FILE")
opt.add_option("-h", "--help",
               help="print this help and exit",
               action="callback",
               callback=print_help_and_exit,
               callback_args=(0,))
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
               help="lanch debugger on compiler error (default: no)")

def getopts (args) :
    global options, abcd, stderr
    (options, args) = opt.parse_args(list(args))
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
    options.plugins = plugins
    if len(args) < 1 :
        err("no input file provided")
        opt.print_help(stderr)
        die(ERR_ARG)
    elif len(args) > 1 :
        err("more than one input file provided")
        opt.print_help(stderr)
        die(ERR_ARG)
    abcd = args[0]
    if options.pnml == abcd :
        err("input file also used as output (--pnml)")
        opt.print_help(stderr)
        die(ERR_ARG)
    for engine in gv_engines :
        if getattr(options, "gv%s" % engine) == abcd :
            err("input file also used as output (--%s)" % engine)
            opt.print_help(stderr)
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
        attr["fillcolor"] = "yellow"
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
            marking = "@"
        else :
            marking = "%s@" % count
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

def draw (net, engine, target) :
    try :
        net.draw(target, engine=engine,
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
## main
##

def main (args=sys.argv[1:]) :
    global snk, net, node
    # get options
    try:
        getopts(args)
    except SystemExit :
        raise
    except :
        bug()
    # read source
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
    try :
        snk = snakes.plugins.load(options.plugins, "snakes.nets", "snk")
    except :
        die(ERR_PLUGIN, str(sys.exc_info()[1]))
    build = Builder(snk)
    try :
        net = build.build(node)
        net.label(srcfile=abcd)
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
            draw(net, engine, target)

##
## wrap main to call it from programs
##

class AbcdError (Exception) :
    def __init__ (self, message, cls, err, tb) :
        Exception.__init__(self, message)
        self.original = (cls, err, tb)

def run (*args) :
    global stdout, sdterr, node, net
    output = io.StringIO()
    try :
        stdout = output
        stderr = output
        main(args)
        return snk, node, net
    except SystemExit :
        raise AbcdError(output.getvalue(),
                        *sys.exc_info())
    finally :
        stdout = sys.stdout
        stderr = sys.stderr

if __name__ == "__main__" :
    main()
