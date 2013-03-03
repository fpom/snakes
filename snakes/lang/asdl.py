import sys, datetime
from snakes.lang.pylib import asdl
from collections import defaultdict
from functools import partial

class memoize(object):
    def __init__(self, function):
        self.function = function
        self.memoized = {}

    def __call__(self, *args):
        try:
            return self.memoized[args]
        except KeyError:
            call = self.function(*args)
            self.memoized[args] = call
            return call

    def __get__(self, obj, objtype):
        """Support instance methods.
        """
        return partial(self.__call__, obj)

def component_has_cycle(node, graph, proceeding, visited):
    if node in visited:
        return False
    if node in proceeding:
        proceeding.append(node) # populate trace
        return True
    proceeding.append(node)
    if node in graph:
        for successor in graph[node]:
            if component_has_cycle(successor, graph, proceeding, visited):
                return True
    proceeding.remove(node)
    visited.add(node)
    return False

def has_cycle(graph):
    visited = set()
    proceeding = list()
    todo = set(graph.keys())

    while todo:
        node = todo.pop()
        if component_has_cycle(node, graph, proceeding, visited):
            i = proceeding.index(proceeding[-1])
            return proceeding[i:]
        todo.difference_update(visited)
    return []

class CyclicDependencies(Exception):
    def __init__(self, seq):
        self.seq = seq

    def __str__(self):
        return "cyclic dependencies: {}".format(" -> ".join(self.seq))

def remove_duplicates(l):
    d = {}
    nl = []
    for e in l:
        if not e in d:
            d[e] = 1
            nl.append(e)
    return nl

class CodeGen (asdl.VisitorBase) :

    def __init__(self, node):
        asdl.VisitorBase.__init__(self)

        self.starting_node = None
        self.current_node = None
        self.hierarchy = defaultdict(list)
        self.hierarchy['_AST'] = []
        self.fields = defaultdict(list)
        self.attributes = defaultdict(list)
        self.code = defaultdict(list)

        self.visit(node)
        ret = has_cycle(self.hierarchy)
        if ret:
            raise CyclicDependencies(ret)
        self._gen_code(node)

    def visitModule(self, node):
        for name, child in node.types.items():
            if not self.starting_node:
                self.starting_node = str(name)
            self.current_node = str(name)
            self.hierarchy[name]
            self.visit(child)

    def visitSum(self, node):
        if hasattr(node, "fields"):
            self.fields[self.current_node] = node.fields
        else:
            self.fields[self.current_node] = []
        if hasattr(node, "attributes"):
            self.attributes[self.current_node] = node.attributes
        else:
            self.attributes[self.current_node] = []

        for child in node.types:
            self.visit(child)

    def visitConstructor (self, node):
        if str(node.name) in self.fields:
            #print >> sys.stderr, "constructor '{!s}' appears twice !".format(node.name)
            #exit(0)
            return
        self.fields[str(node.name)].extend(node.fields)
        self.hierarchy[str(node.name)].append(self.current_node)

    def visitProduct(self, node):
        self.fields[self.current_node].extend(node.fields)

    @memoize
    def _get_fields(self, name):
        if self.fields.has_key(name):
            fields = map(lambda f : f.name, self.fields[name])
            for parent in self.hierarchy[name]:
                fields.extend(self._get_fields(parent))
            return fields
        else:
            return []

    @memoize
    def _get_attributes(self, name):
        if name == '_AST':
            return []
        attributes = map(lambda a : a.name, self.attributes[name])
        for parent in self.hierarchy[name]:
            attributes.extend(self._get_attributes(parent))
        return attributes

    def _gen_code(self, node):
        is_methods = []
        for name in sorted(self.hierarchy):
            if name != '_AST':
                is_methods.extend(["",
                                   "def is{!s}(self):".format(name),
                                   ["return False"]
                                  ])
        cls = ["class _AST (ast.AST):",
               ["_fields = ()",
                "_attributes = ()",
                "",
                "def __init__ (self, **ARGS):",
                ["ast.AST.__init__(self)",
                 "for k, v in ARGS.items():",
                 ["setattr(self, k, v)"]
                ]
               ] + is_methods
              ]
        self.code['_AST'] = cls

        for name, parents in self.hierarchy.iteritems():
            if name == '_AST':
                continue
            if not parents:
                parents = ['_AST']
            fields = self.fields[name]
            args = []
            assign = []
            body = []
            _fields = remove_duplicates(self._get_fields(name))
            _attributes = remove_duplicates(self._get_attributes(name))

            body = []
            cls = ["class {!s} ({!s}):".format(name, ", ".join(parents)), body]

            non_default_args = []
            default_args = []
            for f in fields:
                if f.name.value == 'ctx':
                    f.opt = True

                if f.opt:
                    default_args.append("{!s}=None".format(f.name))
                    assign.append("self.{0!s} = {0!s}".format(f.name))
                elif f.seq:
                    default_args.append("{!s}=[]".format(f.name))
                    assign.append("self.{0!s} = list({0!s})".format(f.name))
                else:
                    non_default_args.append("{!s}".format(f.name))
                    assign.append("self.{0!s} = {0!s}".format(f.name))

            args = non_default_args + default_args

            body.append("_fields = {!r}".format( tuple(map(repr, _fields))))
            body.append("_attributes = {!r}".format( tuple(map(repr, _attributes))))
            body.append("")
            # ctor
            args_str = ", ".join(args)
            if args_str != "":
                args_str += ", "
            body.append("def __init__ (self, {!s} **ARGS):".format(args_str))
            ctor_body = []
            body.append(ctor_body)
            ctor_body.extend(map(lambda base : "{!s}.__init__(self, **ARGS)".format(base), parents))
            ctor_body.extend(assign)

            body.extend(["", "def is{}(self):".format(name), ["return True"]])

            self.code[name] = cls

    @memoize
    def _cost(self, name):
        # print "call cost {}".format(name)
        if name == '_AST':
            return 0
        parents = self.hierarchy[name]
        return reduce(lambda acc, x: acc + self._cost(x), parents, 1)

    @property
    def python(self):

        classes = self.hierarchy.keys()
        classes.sort(lambda a, b: self._cost(a) - self._cost(b))

        code = ["from snakes.lang import ast",
                "from ast import *",
                ""]

        for cls in classes:
            code.extend(self.code[cls])
            code.append("")

        def python (code, indent) :
            for line in code :
                if isinstance(line, str) :
                    yield (4*indent) * " " + line
                else :
                    for sub in python(line, indent+1) :
                        yield sub
        return "\n".join(python(code, 0))

def compile_asdl(infilename, outfilename):
    """Helper function to compile asdl files.
    """

    infile = open(infilename, 'r')
    outfile = open(outfilename, 'w')

    scanner = asdl.ASDLScanner()
    parser = asdl.ASDLParser()
    tokens = scanner.tokenize(infile.read())
    node = parser.parse(tokens)

    outfile.write(("# this file has been automatically generated running:\n"
                   "# %s\n# timestamp: %s\n\n") % (" ".join(sys.argv),
                                                   datetime.datetime.now()))
    outfile.write(CodeGen(node).python)
    outfile.close()
    infile.close()

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
        sys.stderr.write("%s: %s\n" % (__file__, sys.exc_info()[1]))
        sys.exit(1)
    for (flag, arg) in opts :
        if flag in ("-h", "--help") :
            print("""usage: %s [OPTIONS] INFILE
    Options:
        -h, --help         print this help and exit
        --output=OUTPUT    set output file""" % __file__)
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
    try:
        outfile.write(CodeGen(node).python)
    except CyclicDependencies as cycle:
        msg = "[E] {!s}".format(cycle)
        outfile.write(msg)
        if outfile != sys.stdout:
            print >> sys.stderr, msg
    outfile.close()
