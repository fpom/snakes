from snakes.compat import io
from snakes.lang.abcd.parser import ast, parse
import os, tempfile, re, codecs, collections
try :
    from cgi import escape
except :
    from html import escape

template_css = u"""/* ABCD source code */
  .abcd { border:solid 1px #DDD; border-radius:5px; padding:5px 10px; margin:5px; background-color:#F4F4F4; overflow:auto; }
  .abcd .comment { color:#888; }
  .abcd .ident { color:#808; }
  .abcd .string { color:#088; }
  .abcd .kw { color:#800; font-weight:bold; }
  .abcd .flow { color:#800; font-weight:bold; }
  .abcd .buffer .decl { color:#080; font-weight:bold; }
  .abcd .net .decl { color:#008; font-weight:bold; }
  .abcd .instance .name { color:#008; }
  .abcd .action .delim { font-weight:bold; }
  .abcd .action .name { color:#080; }
  .abcd .highlight { background-color:yellow; }
/* Petri net picture */
  .petrinet { border:solid 1px #DDD; border-radius:5px; padding:5px 10px; margin:5px; background-color:#FFF; overflow:auto; clear:both; }
/* Objects tree */
  .tree { border:solid 1px #DDD; border-radius:5px; padding:5px 10px; margin:5px; background-color:#F4F4F4; overflow:auto; font-family:monospace; }
  .tree .kw { color:#800; font-weight:bold; }
  .tree .buffer { color:#080; font-weight:bold; }
  .tree .ident { color:#808; }
  .tree .instance .name { color:#008; }
  .tree .action .delim { font-weight:bold; }
  .tree .action .name { color:#080; }
  .tree .string { color:#088; }
  .tree .highlight { background-color:yellow; }
"""

template_html = u'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>%(filename)s</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<style type="text/css">%(css)s</style>
%(headers)s
%(jscode)s
</head><body>
<h1><tt>%(filename)s</tt></h1>
%(abcd)s
%(tree)s
%(svg)s
</body></html>
'''

template_tree = '''<div class="tree">%(tree)s</div>'''

template_headers = '''<script src="http://code.jquery.com/jquery-1.11.0.min.js" type="text/javascript"></script>'''

template_jscode = '''<script type="text/javascript">
var nodeColor;
function abcdon () {
  obj = jQuery(this);
  if (obj.attr("class") == "node") {
    node = obj.children().children().first();
    nodeColor = node.attr("fill");
    node.attr("fill", "yellow");
  } else {
    obj.addClass("highlight");
  }
  jQuery(obj.attr("data-abcd")).addClass("highlight");
};
function abcdoff () {
  obj = jQuery(this);
  if (obj.attr("class") == "node") {
    node = obj.children().children().first();
    node.attr("fill", nodeColor);
  } else {
    obj.removeClass("highlight");
  }
  jQuery(obj.attr("data-abcd")).removeClass("highlight");
};
function treeon () {
  obj = jQuery(this);
  if (obj.attr("class") != "node") {
    obj.addClass("highlight");
  }
  jQuery(obj.attr("data-tree")).addClass("highlight");
};
function treeoff () {
  obj = jQuery(this);
  if (obj.attr("class") != "node") {
    obj.removeClass("highlight");
  }
  jQuery(obj.attr("data-tree")).removeClass("highlight");
};
function neton () {
  obj = jQuery(this);
  jQuery(obj.attr("data-net")).each(function () {
      node = jQuery(this).children().children().first();
      nodeColor = node.attr("fill");
      node.attr("fill", "yellow");
  });
  obj.addClass("highlight");
};
function netoff () {
  obj = jQuery(this);
  jQuery(obj.attr("data-net")).each(function () {
      node = jQuery(this).children().children().first();
      node.attr("fill", nodeColor);
  });
  obj.removeClass("highlight");
};
function setwidth () {
  abcd = jQuery(".abcd");
  tree = jQuery(".tree");
  width = (jQuery(".petrinet").outerWidth(true) / 2) - 35;
  console.log(width);
  height = Math.max(abcd.height(), tree.height());
  abcd.css({float: "left", width: width, height: height});
  tree.css({float: "right", width: width, height: height});
}
jQuery(document).ready(function() {
  jQuery("[data-abcd]").hover(abcdon, abcdoff);
  jQuery("[data-tree]").hover(treeon, treeoff);
  jQuery("[data-net]").hover(neton, netoff);
  jQuery(".tree .instance, .tree .action").each(function () {
    obj = jQuery(this);
    obj.html(jQuery(obj.attr("data-abcd")).html());
  });
  setwidth();
  jQuery(window).resize(setwidth);
});
</script>'''

class Span (object) :
    def __init__ (self, cls=[], id=None, net=[], abcd=[], tree=[]) :
        self.cls = set([cls]) if isinstance(cls, str) else set(cls)
        self.id = id
        self.net = set([net]) if isinstance(net, str) else set(net)
        self.abcd = set([abcd]) if isinstance(abcd, str) else set(abcd)
        self.tree = set([tree]) if isinstance(tree, str) else set(tree)
    def copy (self, **attr) :
        span = self.__class__(cls=self.cls, id=self.id, net=self.net,
                              abcd=self.abcd, tree=self.tree)
        for k, v in attr.items() :
            if isinstance(getattr(span, k), set) :
                v = set(v)
            setattr(span, k, v)
        return span
    def __bool__ (self) :
        return self.__nonzero__()
    def __nonzero__ (self) :
        return bool(self.cls or self.id or self.net or self.abcd
                    or self.tree)
    def span (self) :
        attr = []
        for src, dst in (("cls", "class"), ("id", "id"),
                         ("net", "data-net"), ("abcd", "data-abcd"),
                         ("tree", "data-tree")) :
            val = getattr(self, src)
            if not val :
                continue
            elif isinstance(val, str) :
                attr.append("%s=%r" % (dst, val))
            elif dst.startswith("data-") :
                attr.append("%s=%r" % (dst, ", ".join("#" + v for v in val)))
            else :
                attr.append("%s=%r" % (dst, ", ".join(val)))
        return "<span %s>" % " ".join(attr)
    def __str__ (self) :
        return self.span()

keywords = {"False", "True", "and", "as", "assert", "buffer", "const",
            "else", "enum", "for", "from", "if", "import", "in", "is",
            "lambda", "net", "not", "or", "symbol", "task", "typedef"}

class ABCD2HTML (ast.NodeVisitor) :
    def __init__ (self, tree) :
        self.tree = tree
        self.x = "%%0%uX" % len("%x" % (tree.st.erow + 1))
        self.st = {}
        self.path = []
        self.nets = {}
        self.visit(tree)
    def __getitem__ (self, id) :
        cls = id.__class__.__name__
        if cls in ("Place", "Transition") :
            x, y, _, _ = id.label("srcloc")
            c = "B" if cls == "Place" else "A"
            id = self.newid(c, x, y)
        elif isinstance(id, tuple) :
            id = self.newid(*id)
        if isinstance(self.st[id], Span) :
            return self.st[id]
        else :
            return self.st[id].span
    def newid (self, c, x, y) :
        return "".join([c[0].upper(), self.x % x, "%X" % y])
    def setspan (self, cls, node, **args) :
        if isinstance(node, ast.AST) :
            node = node.st
        if cls in ("action", "buffer", "instance", "net") :
            x, y = node.srow, node.scol
            ident = self.newid(cls, x, y)
            ident = args.pop("id", ident)
            span = node.span = Span(cls=cls.lower(), id=ident, **args)
            self.st[ident] = node
        elif node is None :
            span = Span(cls=cls.lower(), **args)
            if "id" in args :
                self.st[args["id"]] = span
        else :
            span = node.span = Span(cls=cls.lower(), **args)
            if "id" in args :
                self.st[args["id"]] = node
        return span
    def visit_AbcdBuffer (self, node) :
        t = node.st
        while t.symbol != "abcd_buffer" :
            t = t[0]
        self.setspan("decl", t[1])
        self.setspan("buffer", node)
        self.generic_visit(node)
    def visit_AbcdNet (self, node) :
        t = node.st
        while t.symbol != "abcd_net" :
            t = t[0]
        self.setspan("decl", t[1])
        self.setspan("body", node.body)
        span = self.setspan("net", node)
        self.setspan("proto", None, id="P" + span.id)
        self.nets[".".join(self.path + [node.name])] = span.id
        self.path.append(node.name)
        self.generic_visit(node)
        self.path.pop(-1)
    def visit_AbcdInstance (self, node) :
        t = node.st
        while t.symbol != "abcd_instance" :
            t = t[0]
        self.setspan("name", t[0])
        pid = "P" + self.nets[".".join(self.path + [node.net])]
        span = self.setspan("instance", node, abcd=[pid])
        self[pid].abcd.add(span.id)
        self.generic_visit(node)
    def visit_AbcdAction (self, node) :
        t = node.st
        while t[0].text != '[' :
            t = t[0]
        span = self.setspan("action", node)
        self.setspan("delim", t[0], id="L" + span.id)
        self.setspan("delim", t[-1], id="R" + span.id)
        self.generic_visit(node)
    def visit_AbcdFlowOp (self, node) :
        t = node.st
        while len(t) == 1 :
            t = t[0]
            while t[0].text == '(' :
                t = t[1]
        for op in t[1::2] :
            self.setspan("flow", op)
        self.generic_visit(node)
    def visit_SimpleAccess (self, node) :
        self.setspan("name", node.st[0])
        self.setspan("access", node)
        self.generic_visit(node)
    def visit_FlushAccess (self, node) :
        self.visit_SimpleAccess(node)
    def visit_SwapAccess (self, node) :
        self.visit_SimpleAccess(node)
    def escape (self, text) :
        return escape(text)
    def build (self, st) :
        # collect text skipped during parsing (blanks and comments)
        output = io.StringIO()
        if st.srow > self.row :
            for line in st.text.lexer.lines[self.row-1:st.srow-1] :
                output.write(line[self.col:])
                self.col = 0
            output.write(st.text.lexer.lines[st.srow-1][:st.scol])
        elif st.scol > self.col :
            output.write(st.text.lexer.lines[self.row-1][self.col:st.scol])
        # insert skipped text with comments rendering
        for line in output.getvalue().splitlines(True) :
            if "#" in line :
                left, right = line.split("#", 1)
                self.output.write("%s<span class=%r>%s</span>"
                                  % (self.escape(left),
                                     "comment",
                                     self.escape("#" + right)))
            else :
                self.output.write(self.escape(line))
        # adjust current position in source code
        self.row, self.col = st.srow, st.scol
        # close span for net declaration
        span = getattr(st, "span", Span())
        if "body" in (c.lower() for c in span.cls) :
            self.output.write("</span>")
        # generate <span ...> if necessary
        if span :
            self.output.write(str(span))
        # generate span for net declaration
        if (span.id or "").startswith("N") :
            self.output.write(str(self["P" + span.id]))
        # render tree or its children
        if len(st) :
            for child in st :
                # add span tags on special elements
                if not hasattr(child, "span") :
                    if child.symbol == "NAME" :
                        if child.text in keywords :
                            self.setspan("kw", child)
                        else :
                            self.setspan("ident", child)
                    elif child.symbol == "STRING" :
                        self.setspan("string", child)
                    elif child.symbol == "COLON" :
                        self.setspan("kw", child)
                self.build(child)
        else :
            if st.symbol not in ("DEDENT", "ENDMARKER") :
                self.output.write(self.escape(st.text))
            self.row, self.col = st.erow, st.ecol
        # generate </span> if necessary
        if span :
            self.output.write("</span>")
    def html (self) :
        self.output = io.StringIO()
        self.indent, self.row, self.col = False, 1, 0
        self.build(self.tree.st)
        return "<pre class='abcd'>%s</pre>" % self.output.getvalue()

def Tree () :
    return collections.defaultdict(Tree)

class TreeInfo (object) :
    def __init__ (self, span, name) :
        self.span, self.name = span, name
    def __hash__ (self) :
        return hash(self.name)
    def __eq__ (self, other) :
        try :
            return self.name == other.name
        except :
            return False
    def __ne__ (self, other) :
        return not self.__eq__(other)
    def __iter__ (self) :
        yield self.span
        yield self.name

_svgclean = [(re.compile(r, re.I), s) for r, s in
             [(r"<[?!][^>]*>\n*", ""),
              (r"<title>[^<>]*</title>\n*", ""),
              (r"<g [^<>]*></g>\n*", ""),
              ]]

class Net2HTML (object) :
    def __init__ (self, net, gv, abcd) :
        self.gv = gv
        self.abcd = abcd
        self.tree = Tree()
        self.n2a = collections.defaultdict(set)
        self.n2t = {}
        snk = net.label("snakes")
        self.count = collections.defaultdict(int)
        for place in net.place() :
            nid = gv.nodemap[place.name]
            if place.status in (snk.entry, snk.internal, snk.exit) :
                for char, trans in ([("R", net.transition(t))
                                     for t in place.pre]
                                    + [("L", net.transition(t))
                                       for t in place.post]) :
                    span = abcd[trans]
                    self.n2a[nid].add(char + span.id)
            else :
                self.addtree(0, "buffer", place)
        for trans in net.transition() :
            self.addtree(10, "action", trans)
    def addtree (self, weight, kind, node) :
        nid = self.gv.nodemap[node.name]
        aid = self.abcd[node]
        tid = aid.copy(id=("T%X" % self.count[aid.id]) + aid.id,
                       tree=[], abcd=[aid.id], net=[nid])
        self.count[aid.id] += 1
        aid.tree.add(tid.id)
        aid.net.add(nid)
        self.n2a[nid].add(aid.id)
        self.n2t[nid] = tid.id
        pos = self.tree
        path = node.label("path")
        try :
            inst = node.label("instances")
        except :
            inst = [None] * len(path)
        for name, (_, srow, scol, _, _) in zip(path, inst) :
            a = self.abcd["I", srow, scol]
            t = a.copy(id=("T%X" % self.count[a.id]) + a.id,
                       tree=[], abcd=[a.id], net=[])
            self.count[a.id] += 1
            a.tree.add(t.id)
            pos = pos[((20, srow, scol), "instance", TreeInfo(t, name))]
        prefix = sum(len(p) for p in path) + len(path)
        srow, scol, _, _ = node.label("srcloc")
        pos[((weight, srow, scol), kind, (node, node.name[prefix:]))] = tid
    def _tree (self, tree, indent="") :
        yield indent + "<ul>"
        for (_, kind, data), child in sorted(tree.items()) :
            if kind == "instance" :
                yield indent + "<li>%s%s</span>" % tuple(data)
                for item in self._tree(child, indent + "  ") :
                    yield item
                yield indent + "</li>"
            else :
                node, name = data
                if kind == "buffer" :
                    content = ("<span class='kw'>buffer</span> "
                               "<span class='name'>%s</span> = "
                               "<span class='content'>%s</span>"
                               % (name, node.tokens))
                    yield indent + "<li>%s%s</span></li>" % (child, content)
                elif kind == "action" :
                    content = name
                    yield (indent + "<li>%s%s</span><ul class='modes'>"
                           + "</ul></li>") % (child, content)
                else :
                    raise ValueError("unexpected data %r" % kind)
        yield indent + "</ul>"
    def html (self) :
        return template_tree % {"tree" : "\n".join(self._tree(self.tree))}
    def svg (self) :
        # load SVG file
        with tempfile.NamedTemporaryFile(suffix=".svg") as tmp :
            self.gv.render(tmp.name)
            with codecs.open(tmp.name, "r", "utf-8") as infile :
                svg = infile.read()
        for r, s in _svgclean :
            svg = r.sub(s, svg)
        for node, abcd in self.n2a.items() :
            abcd = ", ".join("#" + t for t in abcd)
            if node in self.n2t :
                svg = svg.replace(' id="%s" ' % node,
                                  ' id="%s" data-abcd="%s" data-tree="#%s" '
                                  % (node, abcd, self.n2t[node]))
            else :
                svg = svg.replace(' id="%s" ' % node,
                                  ' id="%s" data-abcd="%s" ' % (node, abcd))
        return u"<div class='petrinet'>%s</div>" % svg

def build (abcd, node, net, gv, outfile, tpl=template_html, **args) :
    abcd = ABCD2HTML(node)
    pnet = Net2HTML(net, gv, abcd)
    d = {"filename" : node.st.filename,
         "css" : template_css,
         "jscode" : template_jscode,
         "headers" : template_headers,
         "abcd" : abcd.html(),
         "tree" : pnet.html(),
         "svg" : pnet.svg()}
    d.update(args)
    if tpl is not None and outfile :
        with codecs.open(outfile, "w", "utf-8") as out :
            out.write(tpl % d)
    return d
