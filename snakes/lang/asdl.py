import sys, inspect, datetime
from snakes.lang.pylib import asdl
from snakes.lang import ast

class CodeGen (asdl.VisitorBase) :
    def __init__ (self) :
        asdl.VisitorBase.__init__(self)
        self.code = ["from snakes.lang import ast",
                     "from ast import *",
                     "",
                     "class _AST (ast.AST):",
                     ["def __init__ (self, **ARGS):",
                      ["ast.AST.__init__(self)",
                       "for k, v in ARGS.iteritems():",
                       ["setattr(self, k, v)"]]],
                     ""]
        self.base = ["_AST"]
        self.fields = []
        self.attributes = []
    def visitModule (self, node) :
        for name, child in node.types.iteritems() :
            self.base.append(name)
            self.visit(child)
            self.base.pop()
    def visitSum (self, node) :
        if hasattr(node, "fields") :
            self.fields.extend(node.fields)
        self.attributes.extend(node.attributes)
        self.code.extend(["class %s (%s):"
                          % (self.base[-1], self.base[-2]),
                          ["pass"],
                          ""])
        for child in node.types :
            self.visit(child)
        if hasattr(node, "fields") :
            del self.fields[-len(node.fields):]
        del self.attributes[-len(node.attributes):]
    def _init (self, fields, base) :
        args = []
        assign = []
        pos = 0
        fields = self.fields + fields + self.attributes
        names = tuple(str(f.name) for f in fields)
        for f in fields :
            if str(f.name) == "ctx" :
                f.opt = 1
            if str(f.name) in ("lineno", "col_offset") :
                args.append("%s=0" % f.name)
                assign.append("self.%s = int(%s)" % (f.name, f.name))
            elif f.opt :
                args.append("%s=None" % f.name)
                assign.append("self.%s = %s" % (f.name, f.name))
            elif f.seq :
                args.append("%s=[]" % f.name)
                assign.append("self.%s = list(%s)" % (f.name, f.name))
            else :
                args.insert(pos, str(f.name))
                pos += 1
                assign.append("self.%s = %s" % (f.name, f.name))
        if args :
            return ["def __init__ (self, %s, **ARGS):" % ", ".join(args),
                    ["%s.__init__(self, **ARGS)" % base],
                    assign]
        else :
            return []
    def _f_a (self, fields) :
        return ["_fields = %r" % (tuple(str(f.name) for f
                                        in fields + self.fields),),
                "_attributes = %r" % (tuple(str(f.name) for f
                                            in self.attributes),)]
    def visitConstructor (self, node) :
        init = self._init(node.fields, self.base[-1])
        self.code.extend(["class %s (%s):"
                          % (node.name, self.base[-1]),
                          self._f_a (node.fields) + init,
                          ""])
    def visitProduct (self, node) :
        init = self._init(node.fields, self.base[-2])
        self.code.extend(["class %s (%s):"
                          % (self.base[-1], self.base[-2]),
                          self._f_a(node.fields) + init,
                          ""])
    def python (self, node) :
        self.visit(node)
        def python (code, indent) :
            for line in code :
                if isinstance(line, str) :
                    yield (4*indent) * " " + line
                else :
                    for sub in python(line, indent+1) :
                        yield sub
        return "\n".join(python(self.code, 0))

if __name__ == "__main__":
    # a simple CLI
    import getopt
    outfile = sys.stdout
    try :
        opts, args = getopt.getopt(sys.argv[1:], "ho:",
                                   ["help", "output="])
        if ("-h", "") in opts or ("--help", "") in opts :
            opts = [("-h", "")]
            args = [None]
        elif not args :
            raise getopt.GetoptError("no input file provided"
                                     " (try -h to get help)")
        elif len(args) > 1 :
            raise getopt.GetoptError("more than one input file provided")
    except getopt.GetoptError :
        print >>sys.stderr, "%s: %s" % (__file__, sys.exc_info()[1])
        sys.exit(1)
    for (flag, arg) in opts :
        if flag in ("-h", "--help") :
            print """usage: %s [OPTIONS] INFILE
    Options:
        -h, --help         print this help and exit
        --output=OUTPUT    set output file""" % __file__
            sys.exit(0)
        elif flag in ("-o", "--output") :
            outfile = open(arg, "w")
    scanner = asdl.ASDLScanner()
    parser = asdl.ASDLParser()
    tokens = scanner.tokenize(open(args[0]).read())
    node = parser.parse(tokens)
    outfile.write(("# this file has been automatically generated running:\n"
                   "# %s\n# timestamp: %s\n\n") % (" ".join(sys.argv),
                                                   datetime.datetime.now()))
    outfile.write(CodeGen().python(node))
    outfile.close()
