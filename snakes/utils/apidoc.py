import sys, os, os.path
import inspect, fnmatch, collections
import textwrap, doctest, ast
import snakes
from snakes.lang import unparse

##
## console messages
##

CLEAR = "\033[0m"
BLUE = "\033[1;34m"
BOLD = "\033[1;38m"
GRAY = "\033[1;30m"
LIGHTGRAY = "\033[0;30m"
GREEN = "\033[1;32m"
CYAN = "\033[1;36m"
MAGENTA = "\033[1;35m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"

def log (message, color=None, eol=True) :
    if color :
        sys.stderr.write(color)
    if isinstance(message, (list, tuple)) :
        message = " ".join(str(m) for m in message)
    sys.stderr.write(message)
    if color :
        sys.stderr.write(CLEAR)
    if eol :
        sys.stderr.write("\n")
    sys.stderr.flush()

def debug (message, eol=True) :
    log("[debug] ", GRAY, eol=False)
    log(message, LIGHTGRAY, eol=eol)

def info (message, eol=True) :
    log("[info] ", BLUE, False)
    log(message, eol=eol)

def warn (message, eol=True) :
    log("[warn] ", YELLOW, False)
    log(message, eol=eol)

def err (message, eol=True) :
    log("[error] ", RED, False)
    log(message, eol=eol)

def die (message, code=1) :
    err(message)
    sys.exit(code)

##
## extract doc
##

class DocExtract (object) :
    def __init__ (self, inpath, outpath, exclude=[]) :
        self.path = inpath.rstrip(os.sep)
        self.outpath = outpath
        self.out = None
        self.exclude = exclude
        self._last = "\n\n"
    def openout (self, path) :
        if self.out is not None :
            self.out.close()
        relpath = path[len(os.path.dirname(self.path)):].strip(os.sep)
        parts = relpath.split(os.sep)
        relpath = os.path.dirname(relpath.split(os.sep, 1)[-1])
        self.package = (parts[-1] == "__init__.py")
        if self.package :
            self.module = ".".join(parts[:-1])
            target = "index.md"
        else :
            parts[-1] = os.path.splitext(parts[-1])[0]
            self.module = ".".join(parts)
            target =  parts[-1] + ".md"
        if any(fnmatch.fnmatch(self.module, glob) for glob in self.exclude) :
            warn("skip %s" % self.module)
            return False
        outdir = os.path.join(self.outpath, relpath)
        outpath = os.path.join(outdir, target)
        info("%s -> %r" % (self.module, outpath))
        if not os.path.exists(outdir) :
            os.makedirs(outdir)
        self.out = open(outpath, "w")
        self.classname = None
        return True
    def write (self, text) :
        if len(text) > 1 :
            self._last = text[-2:]
        elif len(text) > 0 :
            self._last = self._last[-1] + text[-1]
        else :
            return
        self.out.write(text)
    def newline (self) :
        if self._last != "\n\n" :
            self.write("\n")
    def writeline (self, text="") :
        self.write(text.rstrip() + "\n")
    def writetext (self, text, **args) :
        br = args.pop("break_on_hyphens", False)
        for line in textwrap.wrap(text, break_on_hyphens=br, **args) :
            self.writeline(line)
    def writelist (self, text, bullet="  * ", **args) :
        br = args.pop("break_on_hyphens", False)
        for line in textwrap.wrap(text, break_on_hyphens=br,
                                  initial_indent=bullet,
                                  subsequent_indent=" "*len(bullet),
                                  **args) :
            self.writeline(line)
    def process (self) :
        for dirpath, dirnames, filenames in os.walk(self.path) :
            for name in sorted(filenames) :
                if not name.endswith(".py") :
                    continue
                path = os.path.join(dirpath, name)
                if not self.openout(path) :
                    continue
                node = ast.parse(open(path).read())
                if ".plugins." in self.module :
                    self.visit_plugin(node)
                else :
                    self.visit_module(node)
    def _pass (self, node) :
        pass
    def visit (self, node) :
        name = getattr(node, "name", "__")
        if (name.startswith("_") and not (name.startswith("__")
                                          and name.endswith("__"))) :
            return
        try :
            getattr(self, "visit_" + node.__class__.__name__, self._pass)(node)
        except :
            src = unparse(node)
            if len(src) > 40 :
                src = src[:40] + "..."
            err("line %s source %r" % (node.lineno, src))
            raise
    def visit_module (self, node) :
        self.write_module()
        for child in ast.iter_child_nodes(node) :
            self.visit(child)
    def visit_plugin (self, node) :
        self.write_module()
        extend = None
        for child in ast.iter_child_nodes(node) :
            if (getattr(child, "name", None) == "extend"
                and isinstance(child, ast.FunctionDef)) :
                extend = child
            else :
                self.visit(child)
        self.write_plugin()
        for child in ast.iter_child_nodes(extend) :
            self.visit(child)
    def visit_ClassDef (self, node) :
        self.write_class(node)
        self.classname = node.name
        for child in ast.iter_child_nodes(node) :
            self.visit(child)
        self.classname = None
    def visit_FunctionDef (self, node) :
        self.write_function(node)
        self.args = [n.id for n in node.args.args]
        if self.args and self.args[0] == "self" :
            del self.args[0]
        if node.args.vararg :
            self.args.append(node.args.vararg)
        if node.args.kwarg :
            self.args.append(node.args.kwarg)
        self.visit(node.body[0])
        self.args = []
    def visit_Expr (self, node) :
        self.visit(node.value)
    def visit_Str (self, node) :
        self.write_doc(inspect.cleandoc(node.s))
    def write_module (self) :
        if self.package :
            self.writeline("# Package `%s` #" % self.module)
        else :
            self.writeline("# Module `%s` #" % self.module)
        self.newline()
    def write_plugin (self) :
        self.writeline("## Extensions ##")
        self.newline()
    def write_function (self, node) :
        self.newline()
        if self.classname :
            self.writeline("#### Method `%s.%s` ####"
                           % (self.classname, node.name))
        else :
            self.writeline("### Function `%s` ###" % node.name)
        self.newline()
        self.writeline("    :::python")
        for line in unparse(node).splitlines() :
            if line.startswith("def") :
                self.writeline("    %s ..." % line)
                break
            else :
                self.writeline("    " + line)
        self.newline
    def write_class (self, node) :
        self.newline()
        self.writeline("### Class `%s` ###" % node.name)
        self.newline()
        self.writeline("    :::python")
        for line in unparse(node).splitlines() :
            if line.startswith("class") :
                self.writeline("    %s ..." % line)
                break
            else :
                self.writeline("    " + line)
        self.newline
    parse = doctest.DocTestParser().parse
    def write_doc (self, doc) :
        if doc is None :
            return
        docs = self.parse(doc)
        test, skip = False, False
        for doc in docs :
            if isinstance(doc, str) :
                doc = doc.strip()
                if test :
                    if not doc :
                        continue
                    test, skip = False, False
                self.newline()
                lines = doc.strip().splitlines()
                for num, line in enumerate(lines) :
                    if line.startswith("@") :
                        self.write_epydoc("\n".join(lines[num:]))
                        break
                    self.writeline(line)
            elif not skip :
                if doc.source.strip() == "pass" :
                    skip = True
                else :
                    if not test :
                        test = True
                        self.newline()
                        self.writeline("    :::python")
                    for i, line in enumerate(doc.source.splitlines()) :
                        if i > 0 :
                            self.writeline("    ... %s" % line)
                        else :
                            self.writeline("    >>> %s" % line)
                    for line in doc.want.splitlines() :
                        self.writeline("    %s" % line)
    def write_epydoc (self, doc) :
        info = {"param" : {},
                "type" : {},
                "keyword" : {},
                "raise" : {},
                "todo" : [],
                "note" : [],
                "attention": [],
                "bug" : [],
                "warning" : [],
                }
        for item in doc.lstrip("@").split("\n@") :
            left, text = item.split(":", 1)
            left = left.split()
            assert 1 <= len(left) <= 2, "unsupported item %r" % item
            if len(left) == 1 :
                left.append(None)
            tag, name = [x.strip() if x else x for x in left]
            text = " ".join(text.strip().split())
            if isinstance(info.get(tag, None), list) :
                assert name is None, "unsupported item %r" % item
                info[tag].append(text)
            elif isinstance(info.get(tag, None), dict) :
                assert name is not None, "unsupported item %r" % item
                assert name not in info[tag], "duplicated item %r" % item
                info[tag][name] = text
            else :
                assert name is None, "unsupported item %r" % item
                assert tag not in info, "duplicated tag %r" % item
                info[tag] = text
        if any(k in info for k in ("author", "organization", "copyright",
                                   "license", "contact")) :
            self.newline()
            self.writeline('<div class="api-info">')
            for tag in ("author", "organization", "copyright",
                        "license", "contact") :
                if tag in info :
                    self.writeline('<div class="api-%s">' % tag)
                    self.writetext('<span class="api-title">%s:</span> %s'
                                   % (tag.capitalize(), info[tag]),
                                   subsequent_indent="  ")
                    self.writeline('</div>')
            self.writeline('</div>')
        if any(info[k] for k in
               ("todo", "note", "attention", "bug", "warning")) :
            self.newline()
            self.writeline('<div class="api-remarks">')
            self.writeline("##### Remarks #####")
            self.newline()
            for tag in ("note", "todo", "attention", "bug", "warning") :
                for text in info[tag] :
                    self.writeline('<div class="api-%s">' % tag)
                    self.writetext('<span class="api-title">%s:</span> %s'
                                   % (tag.capitalize(), text),
                                   subsequent_indent="  ")
                    self.writeline('</div>')
            self.writeline('</div>')
        if (any(info[k] for k in ("param", "type", "keyword"))
            or any(k in info for k in ("return", "rtype"))) :
            self.newline()
            self.writeline('<div class="api-call">')
            self.writeline("##### Call API #####")
            self.newline()
            for arg in self.args :
                if arg in info["param"] :
                    self.writelist("`%s` (%s): %s"
                                   % (arg,
                                      info["type"].get(arg, "`object`"),
                                      info["param"][arg]))
                else :
                    self.writelist("`%s` (%s)"
                                   % (arg,
                                      info["type"].get(arg, "`object`")))
            for kw, text in sorted(info["keyword"].items()) :
                self.writelist("`%s`: %s" % (kw, text))
            if any(k in info for k in ("return", "rtype")) :
                if "return" in info :
                    self.writelist("return %s: %s"
                                   % (info.get("rtype", "`object`"),
                                      info["return"]))
                else :
                    self.writelist("return %s"
                                   % (info.get("rtype", "`object`")))
            self.writeline('</div>')
        if info["raise"] :
            self.newline()
            self.writeline('<div class="api-errors">')
            self.writeline("##### Exceptions #####")
            self.newline()
            for exc, reason in sorted(info["raise"].items()) :
                self.writelist("`%s`: %s" % (exc, reason))
            self.writeline('</div>')

def main (finder, args) :
    try :
        source = os.path.dirname(snakes.__file__)
        target = args[0]
        exclude = args[1:]
        if not os.path.isdir(source) :
            raise Exception("could not find SNAKES sources")
        elif not os.path.isdir(target) :
            raise Exception("no directory %r" % target)
    except ValueError :
        die("""Usage: python %s TARGET [EXCLUDE...]
        TARGET   target directory to write files
        EXCLUDE  pattern to exclude modules (not file names)
        """ % __file__)
    except Exception as error :
        die(str(error))
    finder(source, target, exclude).process()

if __name__ == "__main__" :
    main(DocExtract, sys.argv[1:])
