"""Extract SNAKES docstrings and generate API documentation from them
in Markdown format (one file for each Python file). This is both a
Python module and a command-line tool:

    :::console
    $ python -m snakes.utils.apidoc
    [error] Usage: python -m snakes.utils.apidoc TARGET [EXCLUDE...]
            TARGET   target directory to write files
            EXCLUDE  pattern to exclude modules (not file names)
    $ python -m snakes.utils.apidoc api snakes.lang.*
    [info] snakes -> 'api/index.md'
    ...

With respect to existing API extractors, this one takes into account
the structure of SNAKES, in particular, documentation for plugins is
correctly searched within functions `extend` and rendered accordingly.
Moreover, `apidoc` considers all the strings within modules or classes
as docstrings, which is particularly useful to document modules.

There is no real user manual for `apidoc`, in particular about its
syntax and usage, the best source of information is probably to look
at SNAKES source code. However, let's note a few points:

  * most Epydoc fields are supported: `@param`, `@type`, `@note`, ...
  * directive `# apidoc skip` allow not to include the next object in
    the generated documentation
  * directive `# apidoc stop` allow to stop the processing of current
    object (module or class)
  * directive `# apidoc include 'filename' lang='language'` allow to
    include the content of a file as a block of source code in the
    specified language
  * when statement `pass` is found in a doctest, the rest of the
    doctest is skipped, this is useful when this doctest is for test
    purpose only but does not provide useful documentation in itself
  * the syntax is that supported by Markdown Python module, with no
    extensions other that Epydoc fields
  * `apidoc` is intended to be simple and so does not support many
    options nor customisation, however, it is quite flexible already
    by the way it handles documentation

@note: in the example above we do not build doc for the sub-modules of
    `snakes.lang` because some of them are programmed for distinct
    versions of Python with incompatible syntaxes. So `apidoc` will
    fail for sure on one or another of these modules. Fortunately,
    most of the documentation for `snakes.lang` is in the package
    itself.
@note: for better rendering, `apidoc` uses [Python
    Markdown](http://pythonhosted.org/Markdown), however, it will
    handle situations when it is not installed
@warning: `apidoc` has been tested _only_ with SNAKES source, I guess
    it should work in other cases but this may required some work
"""

import sys, os, os.path
import inspect, fnmatch, collections, re, shlex
import textwrap, doctest
import snakes
from snakes.lang import unparse
from snakes.lang.python.parser import parse, ast

try :
    import markdown
except :
    markdown = None

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

# apidoc skip
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

# apidoc skip
def info (message, eol=True) :
    log("[info] ", BLUE, False)
    log(message, eol=eol)

# apidoc skip
def warn (message, eol=True) :
    log("[warn] ", YELLOW, False)
    log(message, eol=eol)

# apidoc skip
def err (message, eol=True) :
    log("[error] ", RED, False)
    log(message, eol=eol)

# apidoc skip
def die (message, code=1) :
    err(message)
    sys.exit(code)

##
## extract doc
##

class DocExtract (object) :
    """The class that extracts documentation and renders it
    """
    def __init__ (self, inpath, outpath, exclude=[]) :
        """
        @param inpath: directory where the source code is searched for
        @type inpath: `str`
        @param outpath: directory where the documentation is generated
        @type outpath: `str`
        @param exclude: a list of glob patterns to exclude modules
            (not file names, but Python modules names)
        @type exclude: `list`
        """
        self.path = inpath.rstrip(os.sep)
        self.outpath = outpath
        self.out = None
        self.exclude = exclude
        self._last = "\n\n"
    def md (self, text, inline=True) :
        """Return the Markdow rendering of `text`, include `<p>` if
        `inline` is `False`. If Python Markdown module is not
        installed, `text` is returned unchanged.

        @param text: the text to be rendered
        @type text: `str`
        @param inline: `True` if this text is part of a larger
            paragraph, `False` if this is a paragraph by itself
        @type inline: `bool`
        @return: HTML text
        @rtype: `str`
        """
        if markdown is None :
            return text
        elif inline :
            return re.sub("</?p>", "\n", markdown.markdown(text), re.I)
        else :
            return markdown.markdown(text)
    def openout (self, path) :
        """Open in `self.out` the output file where the conversion of
        input file `path` will be rendered. If `self.out` is already
        opened, it is first closed.

        Return a Boolean indicating if `path` should be ignored, in
        which case the output file is not opened. This occurs either
        if `path` correspond to a module that has been excluded or if
        the output file exists and is newer than the input file.

        @param path: input file to be converted
        @type path: `str`
        @return: `True` is output file is open and ready, `False` if
            input file should be skipped
        @rtype: `bool`
        @note: package files called `__init__.py` are converted to
            files called `index.md` so that when converted to HTML,
            this will yield a file called `index.html`
        """
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
        if os.path.exists(outpath) :
            if os.stat(path).st_mtime <= os.stat(outpath).st_mtime :
                return False
        self.inpath = path
        info("%s -> %r" % (self.module, outpath))
        if not os.path.exists(outdir) :
            os.makedirs(outdir)
        self.out = open(outpath, "w")
        self.classname = None
        return True
    def write (self, text) :
        """Write `text` to output file

        @param text: the text to write
        @type text: `str`
        """
        if len(text) > 1 :
            self._last = text[-2:]
        elif len(text) > 0 :
            self._last = self._last[-1] + text[-1]
        else :
            return
        self.out.write(text)
    def newline (self) :
        """Write a blank line to output file, never more than one
        blank line is written so there is no need to be carefull about
        how many successive times `newline` is called (which would be
        complicated when multiple calls are made from different
        locations).
        """
        if self._last != "\n\n" :
            self.write("\n")
    def writeline (self, text="") :
        """Write a line of text to output file, ensuring there is a
        end-of-line character at the end (and removing those that may
        exist in `text`).

        @param text: the text to write
        @type text: `str`
        """
        self.write(text.rstrip() + "\n")
    def writetext (self, text, **args) :
        """Write some `text` to output file, with line wrapping.

        @param text: the text to write
        @type text: `str`
        @param args: additional arguments to `textwrap.wrap`
        """
        br = args.pop("break_on_hyphens", False)
        for line in textwrap.wrap(text, break_on_hyphens=br, **args) :
            self.writeline(line)
    def writelist (self, text, bullet="  * ", **args) :
        """Write one list item to output file, wrapping the text
        properly.

        @param text: the text within the item
        @type text: `str`
        @param bullet: list marker
        @type bullet: `str`
        @param args: additional arguments to `textwrap.wrap`
        """
        br = args.pop("break_on_hyphens", False)
        for line in textwrap.wrap(text, break_on_hyphens=br,
                                  initial_indent=bullet,
                                  subsequent_indent=" "*len(bullet),
                                  **args) :
            self.writeline(line)
    def process (self) :
        """Main method that process input directory and write
        converted files to output directory.

        Each input file is parsed using `snakes.lang.python` to an AST
        that is then traversed for processing.
        """
        for dirpath, dirnames, filenames in os.walk(self.path) :
            for name in sorted(filenames) :
                if not name.endswith(".py") or name.startswith(".") :
                    continue
                path = os.path.join(dirpath, name)
                if not self.openout(path) :
                    continue
                node = parse(open(path).read())
                if ".plugins." in self.module :
                    self.visit_plugin(node)
                else :
                    self.visit_module(node)
    def _pass (self, node) :
        pass
    def directive (self, node) :
        """Return directives (skip, stop, include) for this node, or
        `None`

        @param node: an AST node
        @type node: `AST`
        """
        lines = node.st.text.lexer.lines
        num = node.st.srow - 2
        while num >= 0 and (not lines[num].strip()
                            or lines[num].strip().startswith("@")) :
            num -= 1
        if num >= 0 and lines[num].strip().startswith("#") :
            dirline = lines[num].lstrip("# \t").rstrip()
            items = shlex.split(dirline)
            if len(items) >= 2 and items[0].lower() == "apidoc" :
                if len(items) == 2 and items[1].lower() in ("skip", "stop") :
                    return items[1]
                elif items[1].lower() == "include" :
                    path = items[2]
                    try :
                        args = dict(i.split("=", 1) for i in items[3:])
                    except :
                        err("invalid directive %r (line %s)"
                            % (dirline, num+1))
                    self.write_include(path, **args)
                else :
                    err("unknown directive %r (line %s)"
                        % (items[1], num+1))
                    return None
    def children (self, node) :
        """Iterates over the children of `node`

        @param node: an AST node
        @type node: `AST`
        @return: all the children but the `skip`ped ones, until the
            end of `stop` directive is found
        @rtype: `generator`
        """
        for child in ast.iter_child_nodes(node) :
            directive = self.directive(child)
            if directive == "skip" :
                continue
            elif directive == "stop" :
                break
            yield child
    def visit (self, node) :
        """Generic visit of a node that actually dispatch to the
        appropriate method `visit_...`
        """
        name = getattr(node, "name", "__")
        if (name.startswith("_") and not (name.startswith("__")
                                          and name.endswith("__"))) :
            return
        try :
            getattr(self, "visit_" + node.__class__.__name__,
                    self._pass)(node)
        except :
            src = node.st.source()
            if len(src) > 40 :
                src = src[:40] + "..."
            err("line %s source %r" % (node.lineno, src))
            raise
    def visit_module (self, node) :
        """Visit a node that is a module
        """
        self.write_module()
        for child in self.children(node) :
            self.visit(child)
    def visit_plugin (self, node) :
        """Visit a node that is a plugin
        """
        self.write_module()
        extend = None
        for child in self.children(node) :
            if (getattr(child, "name", None) == "extend"
                and isinstance(child, ast.FunctionDef)) :
                extend = child
            else :
                self.visit(child)
        self.write_plugin()
        for child in self.children(extend) :
            self.visit(child)
    def visit_ClassDef (self, node) :
        """Visit a node that is a class definition
        """
        self.write_class(node)
        self.classname = node.name
        for child in self.children(node) :
            self.visit(child)
        self.classname = None
    def visit_FunctionDef (self, node) :
        """Visit a node that is a function definition
        """
        self.write_function(node)
        self.args = [n.arg for n in node.args.args]
        if self.args and self.args[0] == "self" :
            del self.args[0]
        if node.args.vararg :
            self.args.append(node.args.vararg)
        if node.args.kwarg :
            self.args.append(node.args.kwarg)
        self.visit(node.body[0])
        self.args = []
    def visit_Expr (self, node) :
        """Visit a node that is an expression
        """
        self.visit(node.value)
    def visit_Str (self, node) :
        """Visit a node that is a string literal
        """
        self.write_doc(inspect.cleandoc(node.s))
    def write_module (self) :
        """Write the documentation about a module (not its content),
        which is just a title. The module name is in `self.module` and
        there is also a Boolean `self.package` to indicate if this
        module is a actually package.
        """
        if self.package :
            self.writeline("# Package `%s` #" % self.module)
        else :
            self.writeline("# Module `%s` #" % self.module)
        self.newline()
    def write_plugin (self) :
        """Write the documentation about function `extend` in a plugin
        (not its content), which is just a title
        """
        self.writeline("## Extensions ##")
        self.newline()
    def write_function (self, node) :
        """Write the documentation about a function or method (which
        can be differentiated by looking if `self.classname` is not
        None)
        """
        self.newline()
        if self.classname :
            self.writeline("#### Method `%s.%s` ####"
                           % (self.classname, node.name))
        else :
            self.writeline("### Function `%s` ###" % node.name)
        self.newline()
        self.write_def(node)
    def write_class (self, node) :
        """Write the documentation about a class
        """
        self.newline()
        self.writeline("### Class `%s` ###" % node.name)
        self.write_def(node)
    def write_def (self, node) :
        """Write the documentation about a function or method
        definition (parameters, decorators, etc.)
        """
        indent = node.st.scol
        if node.st[0].symbol == "decorated" :
            srow, scol = node.st[0][0][0][0].srow, node.st[0][0][0][0].scol
            erow, ecol = node.st[0][1][-2].erow, node.st[0][1][-2].ecol
        else :
            srow, scol = node.st[0].srow, node.st[0].scol
            erow, ecol = node.st[0][-2].erow, node.st[0][-2].ecol
        lines = node.st.text.lexer.lines
        if srow == erow :
            source = [lines[srow-1][scol:ecol+1]]
        else :
            source = lines[srow-1:erow]
            source[0] = source[0][scol:]
            source[1:-1] = [s[indent:] for s in source[1:-1]]
            source[-1] = source[-1][indent:ecol+1].rstrip() + " ..."
        self.newline()
        self.writeline("    :::python")
        for line in source :
            self.writeline("    " + line)
        self.newline()
    parse = doctest.DocTestParser().parse
    def write_doc (self, doc) :
        """Write the content of a docstring that is parsed to extract
        doctests, Epydoc fields and plain text
        """
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
                        self.writetext("<!-- this comment avoids a bug in"
                                       " Markdown parsing -->")
                        self.writeline("    :::pycon")
                    for i, line in enumerate(doc.source.splitlines()) :
                        if i > 0 :
                            self.writeline("    ... %s" % line)
                        else :
                            self.writeline("    >>> %s" % line)
                    for line in doc.want.splitlines() :
                        self.writeline("    %s" % line)
    def write_epydoc (self, doc) :
        """Write a block of epydoc fields
        """
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
            self.writeline('<ul id="api-info">')
            for tag in ("author", "organization", "contact",
                        "copyright", "license", ) :
                if tag in info :
                    self.writeline('<li id="api-%s">' % tag)
                    self.writetext('<span class="api-title">%s:</span> %s'
                                   % (tag.capitalize(),
                                      self.md(info[tag])),
                                   subsequent_indent="  ")
                    self.writeline('</li>')
            self.writeline('</ul>')
        if any(info[k] for k in
               ("todo", "note", "attention", "bug", "warning")) :
            self.newline()
            self.writeline('<div id="api-remarks">')
            for tag in ("note", "todo", "attention", "bug", "warning") :
                for text in info[tag] :
                    self.writeline('<div class="api-%s">' % tag)
                    self.writetext('<span class="api-title">%s:</span> %s'
                                   % (tag.capitalize(), self.md(text)),
                                   subsequent_indent="  ")
                    self.writeline('</div>')
            self.writeline('</div>')
        if (any(info[k] for k in ("param", "type", "keyword"))
            or any(k in info for k in ("return", "rtype"))) :
            self.newline()
            self.writeline("##### Call API #####")
            self.newline()
            for arg in self.args :
                if arg in info["param"] :
                    self.writelist("`%s %s`: %s"
                                   % (info["type"].get(arg, "object").strip("`"),
                                      arg,
                                      info["param"][arg]))
                else :
                    self.writelist("`%s %s`"
                                   % (info["type"].get(arg, "object").strip("`"),
                                      arg))
            for kw, text in sorted(info["keyword"].items()) :
                self.writelist("keyword `%s`: %s" % (kw, text))
            if any(k in info for k in ("return", "rtype")) :
                if "return" in info :
                    self.writelist("`return %s`: %s"
                                   % (info.get("rtype", "object").strip("`"),
                                      info["return"]))
                else :
                    self.writelist("`return %s`"
                                   % (info.get("rtype", "object").strip("`")))
        if info["raise"] :
            self.newline()
            self.writeline("##### Exceptions #####")
            self.newline()
            for exc, reason in sorted(info["raise"].items()) :
                self.writelist("`%s`: %s" % (exc, reason))
            self.newline()
    def write_include (self, name, lang="python", first=1, last=-1) :
        """Write a block of source code included through directive
        `apidoc include ...`
        """
        first, last = int(first), int(last)
        if os.path.exists(name) :
            path = name
        else :
            path = os.path.join(os.path.dirname(self.inpath), name)
        if not os.path.exists(path) :
            err("include file %r not found" % name)
        with open(path) as infile :
            self.newline()
            self.writeline("    :::%s" % lang)
            for i, line in enumerate(infile) :
                if first <= i+1 and (last == -1 or i+1 <= last) :
                    self.writeline("    " + line.rstrip())
            self.newline()

def main (finder, args, source=None) :
    """Main function of `apidoc`. Source directory may be given
    explicitly, otherwise it is computed as follows:

        :::python
        import snakes
        source = os.path.dirname(snakes.__file__)

    So it is important to set `PYTHONPATH` or `sys.path` if you want
    to use a non-standard location for SNAKES.

    @param finder: `DocExtract` or a subclass of it to perform the
        processing
    @type finder: `class`
    @param args: command line arguments
    @type args: `list`
    @param source: the source directory for the code to be documented,
        or `None` to extract documentation from SNAKES
    @type source: `str`
    """
    try :
        if source is None :
            source = os.path.dirname(snakes.__file__)
        target = args[0]
        exclude = args[1:]
        if not os.path.isdir(source) :
            raise Exception("could not find SNAKES sources")
        elif not os.path.isdir(target) :
            raise Exception("no directory %r" % target)
    except (ValueError, IndexError) :
        die("""Usage: python -m snakes.utils.apidoc TARGET [EXCLUDE...]
        TARGET   target directory to write files
        EXCLUDE  pattern to exclude modules (not file names)""")
    except Exception as error :
        die(str(error))
    finder(source, target, exclude).process()

if __name__ == "__main__" :
    main(DocExtract, sys.argv[1:])
