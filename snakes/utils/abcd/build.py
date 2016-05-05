import sys, operator, inspect, re, collections
from snakes.utils.abcd import CompilationError, DeclarationError
from snakes.lang.abcd.parser import ast
from snakes.lang import unparse
import snakes.utils.abcd.transform as transform
from snakes.data import MultiSet
from snakes import *

class Decl (object) :
    OBJECT = "object"
    TYPE = "type"
    BUFFER = "buffer"
    SYMBOL = "symbol"
    CONST = "const"
    NET = "net"
    TASK = "task"
    IMPORT = "import"
    def __init__ (self, node, kind=None, **data) :
        self.node = node
        classname = node.__class__.__name__
        if kind is not None :
            self.kind = kind
        elif classname == "AbcdTypedef" :
            self.kind = self.TYPE
        elif classname == "AbcdBuffer" :
            self.kind = self.BUFFER
        elif classname == "AbcdSymbol" :
            self.kind = self.SYMBOL
        elif classname == "AbcdConst" :
            self.kind = self.CONST
        elif classname == "AbcdNet" :
            self.kind = self.NET
        elif classname == "AbcdTask" :
            self.kind = self.TASK
        elif classname in ("Import", "ImportFrom") :
            self.kind = self.IMPORT
        else :
            self.kind = self.OBJECT
        for key, val in data.items() :
            setattr(self, key, val)

class GetInstanceArgs (object) :
    """Bind arguments for a net instance
    """
    def __init__ (self, node) :
        self.argspec = []
        self.arg = {}
        self.buffer = {}
        self.net = {}
        self.task = {}
        seen = set()
        for a in node.args.args + node.args.kwonlyargs :
            if a.arg in seen :
                self._raise(CompilationError,
                            "duplicate argument %r" % a.arg)
            seen.add(a.arg)
            if a.annotation is None :
                self.argspec.append((a.arg, "arg"))
            else :
                self.argspec.append((a.arg, a.annotation.id))
    def __call__ (self, *args) :
        self.arg.clear()
        self.buffer.clear()
        self.net.clear()
        self.task.clear()
        for (name, kind), value in zip(self.argspec, args) :
            getattr(self, kind)[name] = value
        return self.arg, self.buffer, self.net, self.task

class Builder (object) :
    def __init__ (self, snk, path=[], up=None) :
        self.snk = snk
        self.path = path
        self.up = up
        self.env = {"True": Decl(None, kind=Decl.CONST, value=True),
                    "False": Decl(None, kind=Decl.CONST, value=False),
                    "None": Decl(None, kind=Decl.CONST, value=None),
                    "dot": Decl(None, kind=Decl.CONST, value=self.snk.dot),
                    "BlackToken": Decl(None, kind=Decl.TYPE,
                                       type=self.snk.Instance(self.snk.BlackToken))}
        self.stack = []
        if up :
            self.globals = up.globals
        else :
            self.globals = snk.Evaluator(dot=self.snk.dot,
                                         BlackToken=self.snk.BlackToken)
        self.instances = MultiSet()
    # utilities
    def _raise (self, error, message) :
        """raise an exception with appropriate location
        """
        if self.stack :
            try :
                pos = "[%s:%s]: " % (self.stack[-1].lineno,
                                     self.stack[-1].col_offset)
            except :
                pos = ""
        else :
            pos = ""
        raise error(pos+message)
    def _eval (self, expr, *largs, **kwargs) :
        env = self.globals.copy()
        if isinstance(expr, ast.AST) :
            expr = unparse(expr)
        return env(expr, dict(*largs, **kwargs))
    # declarations management
    def __setitem__ (self, name, value) :
        if name in self.env :
            self._raise(DeclarationError, "duplicated declaration of %r" % name)
        self.env[name] = value
    def __getitem__ (self, name) :
        if name in self.env :
            return self.env[name]
        elif self.up is None :
            self._raise(DeclarationError, "%r not declared" % name)
        else :
            return self.up[name]
    def __contains__ (self, name) :
        if name in self.env :
            return True
        elif self.up is None :
            return False
        else :
            return name in self.up
    def goto (self, name) :
        if name in self.env :
            return self
        elif self.up is None :
            self._raise(DeclarationError, "%r not declared" % name)
        else :
            return self.up.goto(name)
    def get_buffer (self, name) :
        if name not in self :
            self._raise(DeclarationError,
                        "buffer %r not declared" % name)
        decl = self[name]
        if decl.kind != Decl.BUFFER :
            self._raise(DeclarationError,
                        "%r declared as %s but used as buffer"
                        % (name, decl.kind))
        elif decl.capacity is not None :
            pass
            #self._raise(NotImplementedError, "capacities not (yet) supported")
        return decl
    def get_net (self, name) :
        if name not in self :
            self._raise(DeclarationError,
                        "net %r not declared" % name)
        decl = self[name]
        if decl.kind != Decl.NET :
            self._raise(DeclarationError,
                        "%r declared as %s but used as net"
                        % (name, decl.kind))
        return decl
    def get_task (self, name) :
        if name not in self :
            self._raise(DeclarationError,
                        "task %r not declared" % name)
        decl = self[name]
        if decl.kind != Decl.TASK :
            self._raise(DeclarationError,
                        "%r declared as %s but used as task"
                        % (name, decl.kind))
        return decl
    # main compiler entry point
    def build (self, node, prefix="", fallback=None) :
        self.stack.append(node)
        if prefix :
            prefix += "_"
        method = "build_" + prefix + node.__class__.__name__
        visitor = getattr(self, method, fallback or self.build_fail)
        try :
            return visitor(node)
        finally :
            self.stack.pop(-1)
    def build_fail (self, node) :
        self._raise(CompilationError, "do not know how to compile %s"
                    % node.__class__.__name__)
    def build_arc (self, node) :
        return self.build(node, "arc", self.build_arc_expr)
    # specification
    def build_AbcdSpec (self, node) :
        for decl in node.context :
            self.build(decl)
        tasks = [self._build_TaskNet(decl.node)
                 for name, decl in self.env.items()
                 if decl.kind == Decl.TASK and decl.used]
        net = reduce(operator.or_, tasks, self.build(node.body))
        # set local buffers marking, and hide them
        for name, decl in ((n, d) for n, d in self.env.items()
                           if d.kind == Decl.BUFFER) :
            status = self.snk.buffer(name)
            for place in net.status(status) :
                place = net.place(place)
                try :
                    place.reset(decl.marking)
                except ValueError as err :
                    self._raise(CompilationError,
                                "invalid initial marking (%s)" % err)
                if decl.capacity is None :
                    cap = None
                else :
                    #cap = [c.n if c else None for c in decl.capacity]
                    # TODO: accept more than integers as capacities
                    cap = []
                    for c in decl.capacity :
                        if c is None :
                            cap.append(None)
                        else :
                            try :
                                cap.append(self._eval(c))
                            except :
                                err = sys.exc_info()[1]
                                self._raise(CompilationError,
                                            "could not evaluate %r, %s"
                                            % (unparse(c), err))
                place.label(path=self.path,
                            capacity=cap)
                # TODO: check capacity
            net.hide(status)
        if self.up is None :
            # set entry marking
            for place in net.status(self.snk.entry) :
                net.place(place).reset(self.snk.dot)
            # rename nodes
            self._rename_nodes(net)
            # copy global declarations
            net.globals.update(self.globals)
            # add info about source file
            net.label(srcfile=str(node.st.text.filename))
            # add assertions
            net.label(asserts=node.asserts)
        return net
    def _build_TaskNet (self, node) :
        self._raise(NotImplementedError, "tasks not (yet) supported")
    def _rename_nodes (self, net) :
        # generate unique names
        total = collections.defaultdict(int)
        count = collections.defaultdict(int)
        def ren (node) :
            if net.has_transition(node.name) :
                status = node.label("srctext")
            else :
                if node.status == self.snk.entry :
                    status = "e"
                elif node.status == self.snk.internal :
                    status = "i"
                elif node.status == self.snk.exit :
                    status = "x"
                else :
                    status = node.label("buffer")
            name = ".".join(node.label("path") + [status])
            if total[name] > 1 :
                count[name] += 1
                name = "%s#%s" % (name, count[name])
            return name
        # count occurrences of each name base
        _total = collections.defaultdict(int)
        for node in net.node() :
            _total[ren(node)] += 1
        total = _total
        # rename nodes using a depth-first traversal
        done = set(net.status(self.snk.entry))
        todo = [net.node(n) for n in done]
        while todo :
            node = todo.pop(-1)
            new = ren(node)
            if new != node.name :
                net.rename_node(node.name, new)
            done.add(new)
            for n in net.post(new) - done :
                todo.append(net.node(n))
                done.add(n)
        # rename isolated nodes
        for letter, method in (("p", net.place), ("t", net.transition)) :
            for node in method() :
                if node.name not in done :
                    net.rename_node(node.name, ren(node))
    # declarations
    def build_AbcdTypedef (self, node) :
        """
        >>> import snakes.nets
        >>> b = Builder(snakes.nets)
        >>> b.build(ast.AbcdTypedef(name='number', type=ast.UnionType(types=[ast.NamedType(name='int'), ast.NamedType(name='float')])))
        >>> b.env['number'].type
        (Instance(int) | Instance(float))
        >>> b.build(ast.ImportFrom(module='inspect', names=[ast.alias(name='isbuiltin')]))
        >>> b.build(ast.AbcdTypedef(name='builtin', type=ast.NamedType(name='isbuiltin')))
        >>> b.env['builtin'].type
        TypeCheck(inspect.isbuiltin)
        """
        self[node.name] = Decl(node, type=self.build(node.type))
    def build_AbcdBuffer (self, node) :
        self[node.name] = Decl(node,
                               type=self.build(node.type),
                               capacity=node.capacity,
                               marking=self._eval(node.content))
    def build_AbcdSymbol (self, node) :
        for name in node.symbols :
            value = self.snk.Symbol(name, False)
            self[name] = Decl(node, value=value)
            self.globals[name] = value
    def build_AbcdConst (self, node) :
        value = self._eval(node.value)
        self[node.name] = Decl(node, value=value)
        self.globals[node.name] = value
    def build_AbcdNet (self, node) :
        self[node.name] = Decl(node, getargs=GetInstanceArgs(node))
    def build_AbcdTask (self, node) :
        self._raise(NotImplementedError, "tasks not (yet) supported")
        self[node.name] = Decl(node, used=False)
    def build_Import (self, node) :
        for alias in node.names :
            self[alias.asname or alias.name] = Decl(node)
        self.globals.declare(unparse(node))
    def build_ImportFrom (self, node) :
        self.build_Import(node)
    # processes
    def build_AbcdAction (self, node) :
        if node.guard is True :
            return self._build_True(node)
        elif node.guard is False :
            return self._build_False(node)
        else :
            return self._build_action(node)
    def _build_True (self, node) :
        net = self.snk.PetriNet("true")
        e = self.snk.Place("e", [], self.snk.tBlackToken,
                           status=self.snk.entry)
        e.label(path=self.path)
        net.add_place(e)
        x = self.snk.Place("x", [], self.snk.tBlackToken,
                           status=self.snk.exit)
        x.label(path=self.path)
        net.add_place(x)
        t = self.snk.Transition("t")
        t.label(srctext=node.st.source(),
                srcloc=(node.st.srow, node.st.scol,
                        node.st.erow, node.st.ecol),
                path=self.path)
        net.add_transition(t)
        net.add_input("e", "t", self.snk.Value(self.snk.dot))
        net.add_output("x", "t", self.snk.Value(self.snk.dot))
        return net
    def _build_False (self, node) :
        net = self.snk.PetriNet("false")
        e = self.snk.Place("e", [], self.snk.tBlackToken,
                           status=self.snk.entry)
        e.label(path=self.path)
        net.add_place(e)
        x = self.snk.Place("x", [], self.snk.tBlackToken,
                           status=self.snk.exit)
        x.label(path=self.path)
        net.add_place(x)
        return net
    def _build_action (self, node) :
        net = self.snk.PetriNet("flow")
        e = self.snk.Place("e", [], self.snk.tBlackToken,
                           status=self.snk.entry)
        e.label(path=self.path)
        net.add_place(e)
        x = self.snk.Place("x", [], self.snk.tBlackToken,
                           status=self.snk.exit)
        x.label(path=self.path)
        net.add_place(x)
        t = self.snk.Transition("t", self.snk.Expression(unparse(node.guard)),
                                status=self.snk.tick("action"))
        t.label(srctext=node.st.source(),
                srcloc=(node.st.srow, node.st.scol,
                        node.st.erow, node.st.ecol),
                path=self.path)
        net.add_transition(t)
        net.add_input("e", "t", self.snk.Value(self.snk.dot))
        net.add_output("x", "t", self.snk.Value(self.snk.dot))
        net = reduce(operator.or_, [self.build(a) for a in node.accesses],
                     net)
        net.hide(self.snk.tick("action"))
        return net
    def build_AbcdFlowOp (self, node) :
        return self.build(node.op)(self.build(node.left),
                                   self.build(node.right))
    def _get_instance_arg (self, arg) :
        if arg.__class__.__name__ == "Name" and arg.id in self :
            return self[arg.id]
        else :
            try :
                self._eval(arg)
            except :
                self._raise(CompilationError,
                            "could not evaluate argument %r"
                            % arg.st.source())
            return arg
    def build_AbcdInstance (self, node) :
        if node.net not in self :
            self._raise(DeclarationError, "%r not declared" % node.net)
        elif node.starargs :
            self._raise(CompilationError, "* argument not allowed here")
        elif node.kwargs :
            self._raise(CompilationError, "** argument not allowed here")
        decl = self[node.net]
        if decl.kind != Decl.NET :
            self._raise(DeclarationError,
                        "%r declared as %s but used as net"
                        % (name, decl.kind))
        # unpack args
        posargs, kwargs = [], {}
        for arg in node.args :
            posargs.append(self._get_instance_arg(arg))
        for kw in node.keywords :
            kwargs[kw.arg] = self._get_instance_arg(kw.value)
        # bind args
        try :
            args, buffers, nets, tasks = decl.getargs(*posargs, **kwargs)
        except TypeError :
            c, v, t = sys.exc_info()
            self._raise(CompilationError, str(v))
        for d, kind in ((buffers, Decl.BUFFER),
                        (nets, Decl.NET),
                        (tasks, Decl.TASK)) :
            for k, v in d.items() :
                if v.kind != kind :
                    self._raise(DeclarationError,
                                "%r declared as %s but used as %s"
                                % (k, v.kind, kind))
                d[k] = v.node.name
        # build sub-net
        binder = transform.ArgsBinder(args, buffers, nets, tasks)
        spec = binder.visit(decl.node.body)
        if node.asname :
            name = str(node.asname)
        else :
            name = node.st.source()
        if name in self.instances :
            name = "%s#%s" % (name, self.instances(name))
        self.instances.add(name)
        path = self.path + [name]
        builder = self.__class__(self.snk, path, self)
        net = builder.build(spec)
        src = (node.st.source(),
               node.st.srow, node.st.scol,
               node.st.erow, node.st.ecol)
        for trans in net.transition() :
            try :
                lbl = trans.label("instances")
                trans.label(instances=[src] + lbl)
            except KeyError :
                trans.label(instances=[src])
        for place in net.place() :
            if place.status == self.snk.Status(None) :
                try :
                    lbl = place.label("instances")
                    place.label(instances=[src] + lbl)
                except KeyError :
                    place.label(instances=[src])
        return net
    # control flow operations
    def build_Sequence (self, node) :
        return self.snk.PetriNet.__and__
    def build_Choice (self, node) :
        return self.snk.PetriNet.__add__
    def build_Parallel (self, node) :
        return self.snk.PetriNet.__or__
    def build_Loop (self, node) :
        return self.snk.PetriNet.__mul__
    # accesses :
    def build_SimpleAccess (self, node) :
        decl = self.get_buffer(node.buffer)
        net = self.snk.PetriNet("access")
        net.add_transition(self.snk.Transition("t", status=self.snk.tick("action")))
        b = self.snk.Place(str(node.buffer), [], decl.type,
                           status=self.snk.buffer(node.buffer))
        b.label(path=self.path,
                buffer=str(node.buffer),
                srctext=decl.node.st.source(),
                srcloc=(decl.node.st.srow, decl.node.st.scol,
                        decl.node.st.erow, decl.node.st.ecol))
        net.add_place(b)
        self.build(node.arc)(net, node.buffer, "t", self.build_arc(node.tokens))
        return net
    def build_FlushAccess (self, node) :
        decl = self.get_buffer(node.buffer)
        net = self.snk.PetriNet("access")
        net.add_transition(self.snk.Transition("t", status=self.snk.tick("action")))
        b = self.snk.Place(str(node.buffer), [], decl.type,
                           status=self.snk.buffer(node.buffer))
        b.label(path=self.path,
                buffer=str(node.buffer),
                srctext=decl.node.st.source(),
                srcloc=(decl.node.st.srow, decl.node.st.scol,
                        decl.node.st.erow, decl.node.st.ecol))
        net.add_place(b)
        net.add_input(node.buffer, "t", self.snk.Flush(node.target))
        return net
    def build_SwapAccess (self, node) :
        decl = self.get_buffer(node.buffer)
        net = self.snk.PetriNet("access")
        net.add_transition(self.snk.Transition("t", status=self.snk.tick("action")))
        b = self.snk.Place(node.buffer, [], decl.type,
                           status=self.snk.buffer(node.buffer))
        b.label(path=self.path,
                buffer=str(node.buffer),
                srctext=decl.node.st.source(),
                srcloc=(decl.node.st.srow, decl.node.st.scol,
                        decl.node.st.erow, decl.node.st.ecol))
        net.add_place(b)
        net.add_input(node.buffer, "t", self.build_arc(node.target))
        net.add_output(node.buffer, "t", self.build_arc(node.tokens))
        return net
    def build_Spawn (self, node) :
        self._raise(NotImplementedError, "tasks not (yet) supported")
    def build_Wait (self, node) :
        self._raise(NotImplementedError, "tasks not (yet) supported")
    def build_Suspend (self, node) :
        self._raise(NotImplementedError, "tasks not (yet) supported")
    def build_Resume (self, node) :
        self._raise(NotImplementedError, "tasks not (yet) supported")
    # arc labels
    def build_arc_Name (self, node) :
        if node.id in self :
            decl = self[node.id]
            if decl.kind in (Decl.CONST, Decl.SYMBOL) :
                return self.snk.Value(decl.value)
        return self.snk.Variable(node.id)
    def build_arc_Num (self, node) :
        return self.snk.Value(node.n)
    def build_arc_Str (self, node) :
        return self.snk.Value(node.s)
    def build_arc_Tuple (self, node) :
        return self.snk.Tuple([self.build_arc(elt) for elt in node.elts])
    def build_arc_expr (self, node) :
        return self.snk.Expression(unparse(node))
    # arcs
    def build_Produce (self, node) :
        def arc (net, place, trans, label) :
            net.add_output(place, trans, label)
        return arc
    def build_Test (self, node) :
        def arc (net, place, trans, label) :
            net.add_input(place, trans, self.snk.Test(label))
        return arc
    def build_Consume (self, node) :
        def arc (net, place, trans, label) :
            net.add_input(place, trans, label)
        return arc
    def build_Fill (self, node) :
        def arc (net, place, trans, label) :
            net.add_output(place, trans, self.snk.Flush(str(label)))
        return arc
    # types
    def build_UnionType (self, node) :
        return reduce(operator.or_, (self.build(child)
                                     for child in node.types))
    def build_IntersectionType (self, node) :
        return reduce(operator.and_, (self.build(child)
                                      for child in node.types))
    def build_CrossType (self, node) :
        return self.snk.CrossProduct(*(self.build(child)
                                       for child in node.types))
    def build_ListType (self, node) :
        return self.snk.List(self.build(node.items))
    def build_TupleType (self, node) :
        return self.snk.Collection(self.snk.Instance(tuple),
                                   (self.build(node.items)))
    def build_SetType (self, node) :
        return self.snk.Set(self.build(node.items))
    def build_DictType (self, node) :
        return self.snk.Mapping(keys=self.build(node.keys),
                                items=self.build(node.items),
                                _dict=self.snk.Instance(self.snk.hdict))
    def build_EnumType (self, node) :
        return self.snk.OneOf(*(self._eval(child) for child in node.items))
    def build_NamedType (self, node) :
        name = node.name
        if name in self and self[name].kind == Decl.TYPE :
            return self[name].type
        elif name in self.globals :
            obj = self.globals[name]
            if inspect.isclass(obj) :
                return self.snk.Instance(obj)
            elif inspect.isroutine(obj) :
                return self.snk.TypeCheck(obj)
        elif hasattr(sys.modules["__builtin__"], name) :
            obj = getattr(sys.modules["__builtin__"], name)
            if inspect.isclass(obj) :
                return self.snk.Instance(obj)
            elif inspect.isroutine(obj) :
                return self.snk.TypeCheck(obj)
        self._raise(CompilationError,
                    "invalid type %r" % name)

if __name__ == "__main__" :
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE
                    | doctest.REPORT_ONLY_FIRST_FAILURE
                    | doctest.ELLIPSIS)
    from snakes.lang.abcd.parser import parse
    node = parse(open(sys.argv[1]).read())
    import snakes.plugins
    snk = snakes.plugins.load(["ops", "gv", "labels"], "snakes.nets", "snk")
    build = Builder(snk)
    net = build.build(node)
    net.draw(sys.argv[1] + ".png")
