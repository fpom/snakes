from snakes.lang.ctlstar.parser import parse
from snakes.lang.ctlstar import asdl as ast
from snakes.lang import bind
import _ast

class SpecError (Exception) :
    def __init__ (self, node, reason) :
        Exception.__init__(self, "[line %s] %s" % (node.lineno, reason))

def astcopy (node) :
    if not isinstance(node, _ast.AST) :
        return node
    attr = {}
    for name in node._fields + node._attributes :
        value = getattr(node, name)
        if isinstance(value, list) :
            attr[name] = [astcopy(child) for child in value]
        else :
            attr[name] = astcopy(value)
    return node.__class__(**attr)

class Builder (object) :
    def __init__ (self, spec) :
        self.spec = spec
        self.decl = {}
        for node in spec.atoms + spec.properties :
            if node.name in self.decl :
                raise SpecError(node, "%r already declare line %s"
                                % (name.name, self.decl[name.name].lineno))
            self.decl[node.name] = node
        self.main = spec.main
    def build (self, node) :
        node = astcopy(node)
        return self._build(node, {})
    def _build (self, node, ctx) :
        if isinstance(node, ast.atom) :
            try :
                builder = getattr(self, "_build_%s" % node.__class__.__name__)
            except AttributeError :
                node.atomic = True
            else :
                node = builder(node, ctx)
                node.atomic = True
        elif isinstance(node, ast.CtlBinary) :
            node.left = self._build(node.left, ctx)
            node.right = self._build(node.right, ctx)
            node.atomic = (isinstance(node.op, (ast.boolop, ast.Imply,
                                                ast.Iff))
                           and node.left.atomic
                           and node.right.atomic)
        elif isinstance(node, ast.CtlUnary) :
            node.child = self._build(node.child, ctx)
            node.atomic = (isinstance(node.op, ast.Not)
                           and node.child.atomic)
        else :
            raise SpecError(node, "not a CTL* formula")
        return node
    def _build_place (self, param, ctx) :
        if isinstance(param, ast.Parameter) :
            if param.name not in ctx :
                raise SpecError(param, "place %r should be instantiated"
                                % param.name)
            return ctx[param.name]
        else :
            return param
    def _build_InPlace (self, node, ctx) :
        node.data = [bind(child, ctx) for child in node.data]
        node.place = self._build_place(node.place, ctx)
        return node
    def _build_NotInPlace (self, node, ctx) :
        return self._build_InPlace(node, ctx)
    def _build_EmptyPlace (self, node, ctx) :
        node.place = self._build_place(node.place, ctx)
        return node
    def _build_MarkedPlace (self, node, ctx) :
        return self._build_EmptyPlace(node, ctx)
    # skip Deadlock and Boolean: nothing to do
    def _build_Quantifier (self, node, ctx) :
        node.place = self._build_place(node.place, ctx)
        ctx = ctx.copy()
        for name in node.vars :
            ctx[name] = ast.Token(name, node.place.place)
        node.child = self._build(node.child, ctx)
        return node
    def _build_Instance (self, node, ctx) :
        if node.name not in self.decl :
            raise SpecError(node, "undeclared object %r" % node.name)
        ctx = ctx.copy()
        decl = self.decl[node.name]
        for arg in decl.args :
            ctx[arg.name] = arg
        if isinstance(decl, ast.Property) :
            return self._build_Instance_Property(node, decl, ctx)
        else :
            return self._build_Instance_Atom(node, decl, ctx)
    def _build_Instance_Property (self, node, prop, ctx) :
        bound = set(a.name for a in prop.args)
        args = dict((a.arg, a.annotation) for a in node.args)
        for param in prop.params :
            if param.name in bound :
                raise SpecError(node, "argument %r already bound"
                                % param.name)
            elif param.name in args :
                arg = args.pop(param.name)
                bound.add(param.name)
            else :
                raise SpecError(node, "missing argument %r" % param.name)
            if param.type == "place" :
                if not isinstance(arg, ast.Place) :
                    raise SpecError(node, "expected place for %r"
                                    % param.name)
                arg.name = param.name
            ctx[param.name] = arg
        if args :
            raise SpecError(node, "too many arguments (%s)"
                            % ", ".join(repr(a) for a in args))
        return self._build(astcopy(prop.body), ctx)
    def _build_Instance_Atom (self, node, atom, ctx) :
        bound = set(a.name for a in atom.args)
        args = dict((a.arg, a.annotation) for a in node.args)
        new = astcopy(atom)
        for param in atom.params :
            if param.name in bound :
                raise SpecError(node, "argument %r already bound"
                                % param.name)
            elif param.name in args :
                arg = args.pop(param.name)
                bound.add(param.name)
            else :
                raise SpecError(node, "missing argument %r" % param.name)
            if param.type == "place" :
                if not isinstance(arg, ast.Place) :
                    raise SpecError(node, "expected place for %r"
                                    % param.name)
                arg.name = param.name
            else :
                arg = ast.Argument(name=param.name,
                                   value=arg,
                                   type=param.type)
            new.args.append(arg)
        if args :
            raise SpecError(node, "too many arguments (%s)"
                            % ", ".join(repr(a) for a in args))
        del new.params[:]
        return new

def build (spec) :
    if isinstance(spec, str) :
        spec = parse(spec)
    return Builder(spec).build(spec.main)
