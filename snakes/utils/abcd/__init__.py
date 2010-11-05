import compiler.ast, operator, optparse, sys, inspect, pdb, subprocess, os
import snakes, snakes.plugins, snakes.pnml
from snakes.utils.abcd.compyler import PlyLexer, PlyParser, Tree, AstPrinter

debug = False

class Lexer (PlyLexer) :
    def t_QUESTION (self, t) :
        r"\?"
        return t
    def t_NET (self, t) :
        "net\s"
        t.value = t.value.strip()
        return t
    def t_BUFFER (self, t) :
        "buffer\s"
        t.value = t.value.strip()
        return t

class Parser (PlyParser) :
    lexer = Lexer
    start = "abcd"
    tabmodule = "snakes.utils.abcd.parsetab"
    precedence = (("left", "VBAR"),
                  ("left", "PLUS"),
                  ("left", "SEMI"),
                  ("left", "SLASH"),
                  ("left", "AMPER"),
                  ("left", "COLON"))
    def p_error (self, toks) :
        if toks.type != "NEWLINE" :
            PlyParser.p_error(self, toks)
        self.parser.errok()
    def p_abcd (self, toks) :
        """abcd : abcd_decl abcd_expr
                | abcd_decl abcd_expr ENDMARKER"""
        toks[0] = Tree("abcd", toks[1], expr=toks[2], lineno=toks.lineno(1))
    def p_abcd_decl_rec (self, toks) :
        """abcd_decl : abcd_decl_net abcd_decl
                     | abcd_decl_buf abcd_decl
                     | abcd_decl_def abcd_decl
                     | abcd_decl_import abcd_decl"""
        toks[0] = (toks[1],) + toks[2]
    def p_abcd_decl_empty (self, toks) :
        "abcd_decl : "
        toks[0] = ()
    def p_abcd_decl_def (self, toks) :
        "abcd_decl_def : funcdef"
        toks[0] = Tree("pydef", stmt=toks[1][0])
    def p_abcd_decl_import (self, toks) :
        "abcd_decl_import : import_stmt"
        toks[0] = Tree("pydef", stmt=toks[1][0])
    def p_abcd_decl_net (self, toks) :
        "abcd_decl_net : NET NAME parameters COLON INDENT abcd DEDENT"
        if toks[3].flags != 0 :
            raise SyntaxError, self._format_error("'*' or '**' parameters"
                                                  " not supported",
                                                  toks.lineno(1))
        toks[0] = Tree("net", (toks[6],), args=toks[3],
                       ident=toks[2], lineno=toks.lineno(1))
    def p_abcd_decl_buf (self, toks) :
        "abcd_decl_buf : BUFFER NAME COLON abcd_type EQUAL testlist NEWLINE"
        toks[0] = Tree("buffer", ident=toks[2], type=toks[4], init=toks[6],
                       lineno=toks.lineno(1))
    def p_abcd_type_name (self, toks) :
        "abcd_type : NAME"
        toks[0] = Tree("name", value=toks[1], lineno=toks.lineno(1))
    def p_abcd_type_enum (self, toks) :
        "abcd_type : IN LPAR testlist RPAR"
        toks[0] = Tree("enum", values=toks[3], lineno=toks.lineno(1))
    def p_abcd_type_or (self, toks) :
        "abcd_type : abcd_type VBAR abcd_type"
        toks[0] = Tree("union", (toks[1], toks[3]), lineno=toks.lineno(2))
    def p_abcd_type_and (self, toks) :
        "abcd_type : abcd_type AMPER abcd_type"
        toks[0] = Tree("intersection", (toks[1], toks[3]), lineno=toks.lineno(2))
    def p_abcd_type_list (self, toks) :
        "abcd_type : LSQB abcd_type RSQB"
        toks[0] = Tree("list", (toks[2],), lineno=toks.lineno(1))
    def p_abcd_type_cross (self, toks) :
        "abcd_type : LPAR abcd_type COMMA abcd_type_cross RPAR"
        toks[0] = Tree("cross", (toks[2],) + toks[4], lineno=toks.lineno(1))
    def p_abcd_type_cross_one (self, toks) :
        "abcd_type : LPAR abcd_type COMMA RPAR"
        toks[0] = Tree("cross", (toks[2],), lineno=toks.lineno(1))
    def p_abcd_type_cross_rec (self, toks) :
        "abcd_type_cross : abcd_type COMMA abcd_type_cross"
        toks[0] = (toks[1],) + toks[3]
    def p_abcd_type_cross_end (self, toks) :
        "abcd_type_cross : abcd_type"
        toks[0] = (toks[1],)
    def p_abcd_type_dict (self, toks) :
        "abcd_type : abcd_type COLON abcd_type"
        toks[0] = Tree("dict", (toks[1], toks[3]), lineno=toks.lineno(2))
    def p_abcd_type_set (self, toks) :
        "abcd_type : LBRACE abcd_type RBRACE"
        toks[0] = Tree("set", (toks[2],), lineno=toks.lineno(1))
    def p_abcd_type_nest (self, toks) :
        "abcd_type : LPAR abcd_type RPAR"
        toks[0] = toks[2]
    def p_abcd_expr_action (self, toks) :
        "abcd_expr : abcd_action"
        toks[0] = toks[1]
    def p_abcd_action_true (self, toks) :
        "abcd_action : LSQB abcd_access_list RSQB"
        toks[0] = Tree("action", toks[2],
                       test=True, net=None, lineno=toks.lineno(1))
    def p_abcd_action_if (self, toks) :
        "abcd_action : LSQB abcd_access_list IF testlist RSQB"
        toks[0] = Tree("action", toks[2],
                       test=toks[4], net=None, lineno=toks.lineno(1))
    def p_abcd_action_trivial (self, toks) :
        "abcd_action : LSQB NAME RSQB"
        if toks[2] == "True" :
            toks[0] = Tree("action", test=True, net=None, lineno=toks.lineno(1))
        elif toks[2] == "False" :
            toks[0] = Tree("action", test=False, net=None, lineno=toks.lineno(1))
        else :
            raise SyntaxError, self._format_error("invalid action '[%s]'"
                                                  % toks[2], toks.lineno(1))
    def p_abcd_action_net_params (self, toks) :
        "abcd_action : NAME LPAR arglist RPAR"
        if (toks[3].star_args, toks[3].dstar_args) != (None, None) :
            raise SyntaxError, self._format_error("'*' or '**' parameters"
                                                  " not supported",
                                                  toks.lineno(1))
        toks[0] = Tree("action", test=None, net=toks[1], args=toks[3],
                       lineno=toks.lineno(1), tag=None)
    def p_abcd_action_net_params_tagged (self, toks) :
        "abcd_action : NAME COLON COLON NAME LPAR arglist RPAR"
        if (toks[6].star_args, toks[6].dstar_args) != (None, None) :
            raise SyntaxError, self._format_error("'*' or '**' parameters"
                                                  " not supported",
                                                  toks.lineno(1))
        toks[0] = Tree("action", test=None, net=toks[4], args=toks[6],
                       lineno=toks.lineno(1), tag=toks[1])
    def p_abcd_action_net (self, toks) :
        "abcd_action : NAME LPAR RPAR"
        toks[0] = Tree("action", test=None, net=toks[1], args=None,
                       lineno=toks.lineno(1), tag=None)
    def p_abcd_action_net_tagged (self, toks) :
        "abcd_action : NAME COLON COLON NAME LPAR RPAR"
        toks[0] = Tree("action", test=None, net=toks[4], args=None,
                       lineno=toks.lineno(1), tag=toks[1])
    def p_abcd_access_list_rec (self, toks) :
        "abcd_access_list : abcd_access COMMA abcd_access_list"
        toks[0] = (toks[1],) + toks[3]
    def p_abcd_access_list_end (self, toks) :
        "abcd_access_list : abcd_access"
        toks[0] = (toks[1],)
    def p_abcd_access (self, toks) :
        """abcd_access : NAME PLUS LPAR testlist RPAR
                       | NAME MINUS LPAR testlist RPAR
                       | NAME QUESTION LPAR testlist RPAR
                       | NAME LEFTSHIFT LPAR testlist RPAR
                       | NAME RIGHTSHIFT LPAR testlist RPAR"""
        toks[0] = Tree("access", buffer=toks[1], mode=toks[2], param=toks[4],
                       lineno=toks.lineno(1))
    def p_abcd_expr_loop (self, toks) :
        "abcd_expr : abcd_expr STAR abcd_expr"
        toks[0] = Tree("loop", (toks[1], toks[3]), lineno=toks.lineno(2))
    def p_abcd_expr_seq (self, toks) :
        "abcd_expr : abcd_expr SEMI abcd_expr"
        toks[0] = Tree("sequence", (toks[1], toks[3]), lineno=toks.lineno(2))
    def p_abcd_expr_choice (self, toks) :
        "abcd_expr : abcd_expr PLUS abcd_expr"
        toks[0] = Tree("choice", (toks[1], toks[3]), lineno=toks.lineno(2))
    def p_abcd_expr_parall (self, toks) :
        "abcd_expr : abcd_expr VBAR abcd_expr"
        toks[0] = Tree("parallel", (toks[1], toks[3]), lineno=toks.lineno(2))
    def p_abcd_expr_scope (self, toks) :
        "abcd_expr : abcd_expr SLASH NAME"
        toks[0] = Tree("scope", (toks[1], toks[3]), lineno=toks.lineno(2))
    def p_abcd_expr_nested (self, toks) :
        "abcd_expr : LPAR abcd_expr RPAR"
        toks[0] = toks[2]
    def p_atom_4 (self, toks):
        "atom : LSQB RSQB"
        toks[0] = compiler.ast.CallFunc(compiler.ast.Name("list"),
                                        [], None, None)
        self.locate(toks[0], toks.lineno(1))
    def p_atom_5 (self, toks):
        "atom : LSQB listmaker RSQB"
        toks[0] = compiler.ast.CallFunc(compiler.ast.Name("list"),
                                        [toks[2]], None, None)
        if not self.BACKWARDS_COMPATIBLE:
            self.locate(toks[0], toks.lineno(1))
    def p_atom12 (self, toks) :
        "atom : LBRACE listmaker RBRACE"
        toks[0] = compiler.ast.CallFunc(compiler.ast.Name("set"),
                                        [toks[2]], None, None)
        self.locate(toks[0], toks.lineno(2))

class Environment (object) :
    def __init__ (self, net=None, buf=None, pydef=None, tags=None) :
        self.net = net or {}
        self.buf = buf or {}
        self.tags = tags or set()
        self.pydef = pydef or set()
    def copy (self, other=None) :
        result = self.__class__(net=self.net.copy(),
                                buf=self.buf.copy(),
                                pydef=self.pydef.copy(),
                                tags=self.tags)
        if other is not None :
            result.update(other)
        return result
    def update (self, other) :
        self.net.update(other.net)
        self.buf.update(other.buf)
        self.pydef.update(other.pydef)
        self.tags.update(other.tags)
    def add_net (self, name, value) :
        self.net[name]  = value
    def add_buf (self, name, value) :
        self.buf[name]  = value
    def add_def (self, value) :
        self.pydef.add(value)
    def add_tag (self, name) :
        self.tags.add(name)

class Tagger (object) :
    def __init__ (self) :
        self._num = {}
    def __call__ (self, tag="") :
        num = self._num.get(tag, 0)
        self._num[tag] = num + 1
        return tag + str(num)

class CompilationError (Exception) :
    pass

class Compiler (object) :
    def __init__ (self, infile, symbols) :
        self.prn = AstPrinter()
        self.tag = Tagger()
        self.infile = infile
        self._eval_env = {"set" : nets.hset,
                          "list" : nets.hlist,
                          "dict" : nets.hdict}
        self._eval_env.update(nets.__dict__)
        self.symbols = set(symbols)
        for symb in self.symbols :
            self._eval_env[symb] = nets.Symbol(symb)
    def _eval (self, expr, env=None) :
        if isinstance(expr, compiler.ast.Node) :
            expr = self.prn[expr]
        _eval_env = self._eval_env.copy()
        if env is not None :
            for pydef in env.pydef :
                exec(pydef, _eval_env)
        return eval(expr, _eval_env)
    def error (self, msg, tree) :
        try :
            msg = "%s (%s:%s)" % (msg, self.infile, tree.lineno)
        except :
            pass
        raise CompilationError, msg
    def rename (self, net) :
        conflict = {}
        for place in net.place() :
            try :
                _net = place.label("net")
            except :
                _net = ""
            if place.status in (nets.entry, nets.exit, nets.internal) :
                name = ".".join([_net, str(place.status)])
                count = conflict[name] = conflict.get(name, 0) + 1
                name = "%s#%u" % (name, count)
            else :
                name = place.label("name")
                if name != place.name and net.has_place(name) :
                    count = conflict[name] = conflict.get(name, 0) + 1
                    name = "%s#%u" % (name, count)
            if name != place.name :
                net.rename_node(place.name, name)
        for trans in net.transition() :
            try :
                _net = trans.label("net")
            except :
                _net = ""
            name = ".".join([_net, trans.label("action")])
            if name == trans.name :
                continue
            elif net.has_transition(name) :
                count = conflict[name] = conflict.get(name, 0) + 1
                name = "%s#%u" % (name, count)
            net.rename_node(trans.name, name)
    def build (self, tree, env=Environment(), path="") :
        env = env.copy()
        local = []
        for decl in tree :
            if decl.name == "net" :
                _path = ".".join(p for p in [path, decl.ident] if p)
                env.add_net(decl.ident, (decl, env.copy(), _path))
            elif decl.name == "buffer" :
                env.add_buf(decl.ident,
                            (self.build_type(decl.type, env),
                             self.prn[decl.init]))
                local.append(decl.ident)
            elif decl.name == "pydef" :
                env.add_def(self.prn[decl.stmt])
            else :
                self.error("invalid declaration %r" % decl.name, decl)
        net = self.build_expr(tree.expr, env)
        for node in net.node() :
            try :
                node.label("net")
            except :
                node.label(net=path)
        for name in local :
            try :
                place = net.status(nets.buffer(name))[0]
            except IndexError :
                continue
            try :
                tokens = self._eval(env.buf[name][1], env)
                if not isinstance(tokens, tuple) :
                    tokens = [tokens]
                _place = net.place(place)
                _place.reset(tokens)
                _place.label(name=".".join(p for p in [path, name] if p))
            except :
                self.error("invalid initial marking", env.buf[name][1])
            newname = ".".join(p for p in [path, name] if p)
            if newname != place :
                net.rename_node(place, newname)
            net.hide(nets.buffer(name), nets.buffer(None))
        for symb in self.symbols :
            net.declare("Symbol(%r)" % symb)
        return net
    _type_map = {"union" : operator.or_,
                 "intersection" : operator.and_}
    def build_type (self, tree, env) :
        children = [self.build_type(t, env) for t in tree]
        if tree.name in self._type_map :
            return self._type_map[tree.name](*children)
        elif tree.name == "name" :
            try :
                return nets.Instance(self._eval(tree.value, env))
            except AttributeError :
                self.error("unknown type '%s'" % tree.value, tree)
        elif tree.name == "enum" :
            return nets.OneOf(*self._eval(tree.values, env))
        elif tree.name == "list" :
            return nets.Collection(nets.Instance(nets.hlist),
                                   children[0])
        elif tree.name == "cross" :
            return nets.CrossProduct(*children)
        elif tree.name == "dict" :
            return nets.Mapping(children[0], children[1], nets.hdict)
        elif tree.name == "set" :
            return nets.Collection(nets.Instance(nets.hset),
                                   children[0])
        self.error("invalid type '%s'" % tree.name, tree)
    _expr_map = {"loop" : operator.mul,
                 "sequence" : operator.and_,
                 "choice" : operator.add,
                 "parallel" : operator.or_,
                 "scope" : operator.div}
    def build_expr (self, tree, env) :
        if tree.name in self._expr_map :
            nets = []
            for i, t in enumerate(tree) :
                net = self.build_expr(t, env)
                nets.append(net)
                for trans in net.transition() :
                    trans.label("ops").append((tree.name, i))
            return self._expr_map[tree.name](*nets)
        elif tree.name == "action" :
            return self.build_action(tree, env)
        self.error("invalid expression '%s'" % tree.name, tree)
    def build_net (self, tree, path, env, ctx, name=None) :
        # build binding of args to params
        if ctx.args is None :
            params = ()
        else :
            params = ctx.args.args
        if len(params) > len(tree.args.argnames) :
            self.error("too much parameters in net instantiation", ctx)
        args = []
        bind = {}
        for  p, a in zip(tree.args.argnames, params) :
            bind[p] = a
            args.append("%s=%s" % (p, self.prn[a]))
        for p, d in zip(reversed(tree.args.argnames),
                        reversed(tree.args.defaults)) :
            if p not in bind :
                bind[p] = d
                args.append("%s=%s" % (p, self.prn[a]))
        if len(bind) < len(tree.args.argnames) :
            self.error("missing parameters in net instantiation", ctx)
        # bind tree and build net
        if not name :
            name = path + "(%s)" % ",".join(args)
        return self.build(self._bind(tree[0], bind), env, name)
    def _bind (self, tree, bind) :
        if isinstance(tree, Tree) and tree.name == "access" :
            if tree.buffer in bind :
                buf = bind[tree.buffer].name
            else :
                buf = tree.buffer
            return Tree("access", buffer=buf, mode=tree.mode,
                        param=self._bind(tree.param, bind),
                        lineno=tree.lineno)
        elif isinstance(tree, Tree) :
            attrs = dict((n, self._bind(v, bind)) for n, v
                         in tree.attributes.iteritems())
            return tree.__class__(tree.name,
                                  [self._bind(x, bind) for x in tree],
                                  **attrs)
        elif isinstance(tree, compiler.ast.Name) :
            return bind.get(tree.name, tree)
        elif isinstance(tree, compiler.ast.Node) :
            args = []
            for argname in inspect.getargspec(tree.__class__.__init__)[0][1:] :
                handler = getattr(self,
                                  "_bind_%s_%s" % (tree.__class__.__name__,
                                                   argname),
                                  None)
                if handler is not None :
                    args.append(handler(tree, bind))
                elif isinstance(argname, str) :
                    args.append(self._bind(getattr(tree, argname), bind))
                else :
                    args.append([self._bind(getattr(tree, a), bind) for a in argname])
            return tree.__class__(*args)
        elif isinstance(tree, (tuple, list, set)) :
            return tree.__class__(self._bind(x, bind) for x in tree)
        elif isinstance(tree, dict) :
            return tree.__class__((self._bind(k, bind),
                                   self._bind(v, bind))
                                  for k, v in tree.iteritems())
        else :
            return tree
    def _bind_Add_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def _bind_Div_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def _bind_FloorDiv_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def _bind_LeftShift_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def _bind_Mod_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def _bind_Mul_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def _bind_Power_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def _bind_RightShift_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def _bind_Sub_leftright (self, tree, bind) :
        return [self._bind(tree.left, bind), self._bind(tree.right, bind)]
    def build_action (self, tree, env) :
        if tree.net is not None :
            try :
                _tree, _env, _path = env.net[tree.net]
            except KeyError :
                self.error("undeclared net '%s'" % tree.net, tree)
            if tree.tag and tree.tag in env.tags :
                self.error("duplicated instance name '%s'" % tree.tag, tree)
            env.add_tag(tree.tag)
            return self.build_net(_tree, _path, env.copy(_env), tree, tree.tag)
        net = nets.PetriNet("basic")
        for src in env.pydef :
            net.declare(src)
        for name, status in ((":e", nets.entry), (":x", nets.exit)) :
            net.add_place(nets.Place(name, status=status))
        if tree.test is False :
            return net
        if tree.test is True :
            guard = None
        else :
            guard = nets.Expression(self.prn[tree.test])
        trans = nets.Transition(":t", guard)
        trans.label(tag=self.tag("trans"))
        tree.attributes["tag"] = trans.label("tag")
        trans.label(ops=[])
        net.add_transition(trans)
        net.add_input(":e", ":t", nets.Value(nets.dot))
        net.add_output(":x", ":t", nets.Value(nets.dot))
        arcs = {}
        _action = []
        for access in tree :
            p, m, l = access.buffer, access.mode, access.param
            cls = l.__class__.__name__
            l = self.build_arc(l, m, env)
            if cls == "Const" :
                _action.append("%s%s(%r)" % (access.buffer, access.mode, l.value))
            else :
                _action.append("%s%s(%s)" % (access.buffer, access.mode, l))
            arcs.setdefault(p, {}).setdefault(m, []).append(l)
        trans.label(action="[%s if %s]" % (", ".join(_action), str(trans.guard)))
        for p in arcs :
            try :
                buf = env.buf[p][0]
            except KeyError :
                self.error("undeclared buffer '%s'" % p, tree)
            net.add_place(nets.Place(p, [], buf), status=nets.buffer(p))
            produce = []
            if ">>" in arcs[p] :
                if ("-" in arcs[p]) or ("?" in arcs[p]) :
                    raise CompilationError, "cannot mix flush arcs with others"
                elif len(arcs[p][">>"]) > 1 :
                    raise CompilationError, "cannot have multiple flush arcs"
                net.add_input(p, ":t", arcs[p][">>"][0])
            elif "-" in arcs[p] and "?" in arcs[p] :
                net.add_input(p, ":t", nets.MultiArc(arcs[p]["-"]
                                                     + arcs[p]["?"]))
                produce.extend(arcs[p]["?"])
            elif "?" in arcs[p] :
                if len(arcs[p]["?"]) == 1 :
                    lbl = nets.Test(arcs[p]["?"][0])
                else :
                    lbl = nets.Test(nets.MultiArc(arcs[p]["?"]))
                net.add_input(p, ":t", lbl)
            elif "-" in arcs[p] :
                if len(arcs[p]["-"]) == 1 :
                    net.add_input(p, ":t", arcs[p]["-"][0])
                else :
                    net.add_input(p, ":t", nets.MultiArc(arcs[p]["-"]))
            if "+" in arcs[p] :
                produce.extend(arcs[p]["+"])
            if "<<" in arcs[p] :
                produce.extend(arcs[p]["<<"])
            if len(produce) == 1 :
                net.add_output(p, ":t", produce[0])
            elif len(produce) > 1 :
                net.add_output(p, ":t", nets.MultiArc(produce))
        return net
    def build_arc (self, label, mode, env) :
        cls = label.__class__.__name__
        if cls == "Name" :
            if label.name in ("False", "True") :
                cls = "Const"
            elif label.name in self.symbols :
                cls = "Const"
        if cls == "Name" :
            if mode in ("<<", ">>") :
                return nets.Flush(label.name)
            else :
                return nets.Variable(label.name)
        elif cls == "Const" :
            return nets.Value(self._eval(label, env))
        elif cls == "Tuple" :
            return nets.Tuple([self.build_arc(l, mode, env) for l in label])
        else :
            if mode in ("<<", ">>") :
                return nets.Flush(self.prn[label])
            else :
                return nets.Expression(self.prn[label])

def draw_place (place, attr) :
    if len(place.tokens) == 0 :
        attr["label"] = " "
        attr["shape"] = "circle"
    elif place.tokens == nets.MultiSet([nets.dot]) :
        attr["label"] = "@"
        attr["shape"] = "circle"
    else :
        attr["label"] = str(place.tokens)
        if len(attr["label"]) > 4 :
            attr["shape"] = "ellipse"
    if place.status.name() == "buffer" :
        attr["label"] = "%s\\n%s" % (place.label("name"), attr["label"])
        attr["shape"] = "ellipse"
    attr["style"] = "filled"
    if place.status == nets.entry :
        attr["fillcolor"] = "green"
    elif place.status == nets.exit :
        attr["fillcolor"] = "yellow"
    elif place.status == nets.internal :
        attr["fillcolor"] = "white"
    else :
        attr["fillcolor"] = "lightblue"

def draw_trans (trans, attr) :
    attr["label"] = "%s\\n%s" % (trans.label("action"), trans.guard)

def draw_arc (label, attr) :
    if attr["label"].endswith("?") :
        attr["label"] = attr["label"][:-1]
        attr["arrowhead"] = "none"
    elif attr["label"].endswith("!") :
        attr["label"] = attr["label"][:-1]
        attr["arrowhead"] = "box"
    if attr["label"] == "dot" :
        del attr["label"]

def draw_cluster (cluster, attr) :
    pass
    #attr["style"] = "solid"
    #attr["color"] = "pink"

def main() :
    gv_engines = ("dot", "neato", "twopi", "circo", "fdp")
    opt = optparse.OptionParser(prog="abcd",
                                usage="%prog [OPTION]... FILE")
    opt.add_option("-l", "--load",
                   dest="plugins", action="append", default=[],
                   help="load plugin (this option can be repeated)",
                   metavar="PLUGIN")
    opt.add_option("--debug",
                   dest="debug", action="store_true", default=False,
                   help="run in debug mode")
    opt.add_option("-p", "--pnml",
                   dest="pnml", action="store", default=None,
                   help="save net as PNML",
                   metavar="OUTFILE")
    opt.add_option("-a", "--ast",
                   dest="ast", action="store_true", default=False,
                   help="include AST in PNML, requires '--pnml'")
    opt.add_option("--cpp",
                   dest="cpp", action="store_true", default=False,
                   help="process source through CPP before compulation")
    opt.add_option("-s", "--symbols",
                   dest="symbols", action="append", default=[],
                   help="define symbols (as comma separated list)")
    for engine in gv_engines :
        opt.add_option("-" + engine[0], "--" + engine,
                       dest="gv" + engine, action="store", default=None,
                       help="draw net using '%s' (from GraphViz)" % engine,
                       metavar="OUTFILE")
    (options, args) = opt.parse_args()
    global debug
    debug = options.debug
    if options.ast and not options.pnml :
        print ("%s: option '--ast' must be used together with '--pnml'\n"
               % opt.prog)
        opt.print_help()
        sys.exit(1)
    plugins = []
    for p in options.plugins :
        plugins.extend(t.strip() for t in p.split(","))
    if "ops" not in plugins :
        plugins.append("ops")
    if "labels" not in plugins :
        plugins.append("labels")
    for engine in gv_engines :
        gvopt = getattr(options, "gv%s" % engine)
        if gvopt and "gv" not in plugins :
            plugins.append("gv")
            break
    if len(args) != 1 :
        opt.print_help()
        sys.exit(1)
    infile = args[0]
    nets = snakes.plugins.load(plugins, "snakes.nets", "nets")
    try :
        if options.cpp :
            cpp = subprocess.Popen(["cpp", infile, infile + ".cpp"],
                                   stdout=subprocess.PIPE)
            ret = cpp.wait()
            if ret != 0 :
                raise CompilationError, "cpp: exited with code %s" % ret
            infile = infile + ".cpp"
        src = open(infile).read()
        abcd_parser = Parser()
        if options.symbols :
            symbols = reduce(list.__add__, ([s.upper() for s in l.split(",")]
                                            for l in options.symbols))
        else :
            symbols = []
        abcd_compiler = Compiler(infile, symbols)
        ast = abcd_parser.parse(src, infile)
        net = abcd_compiler.build(ast)
        abcd_compiler.rename(net)
        for name in net.status(nets.entry) :
            place = net.place(name)
            place.reset([nets.dot])
        for engine in gv_engines :
            gvopt = getattr(options, "gv%s" % engine)
            if gvopt :
                net.draw(gvopt, engine=engine,
                         place_attr=draw_place,
                         trans_attr=draw_trans,
                         arc_attr=draw_arc,
                         cluster_attr=draw_cluster)
        if options.pnml :
            pnml = snakes.pnml.Tree.from_obj(net)
            if options.ast :
                pnml.add_child(snakes.pnml.Tree.from_obj(ast))
            if options.pnml == "-" :
                output = sys.stdout
            else :
                output = open(options.pnml, "w")
            print >>output, pnml.to_pnml()
        if options.cpp :
            os.remove(infile)
    except ImportError, err :
        if debug : pdb.post_mortem(sys.exc_info()[2])
        opt.error("plugin error, " + str(err))
        sys.exit(2)
    except SyntaxError, err :
        if debug : pdb.post_mortem(sys.exc_info()[2])
        opt.error("syntax error, " + str(err))
        sys.exit(3)
    except IOError, err :
        if debug : pdb.post_mortem(sys.exc_info()[2])
        opt.error(str(err))
        sys.exit(3)
    except CompilationError, err :
        if debug : pdb.post_mortem(sys.exc_info()[2])
        opt.error("compilation error, " + str(err))
        sys.exit(4)
    except Exception, err :
        if debug : pdb.post_mortem(sys.exc_info()[2])
        opt.error("internal error (%s), %s"
                  % (err.__class__.__name__, str(err)))
        sys.exit(255)

nets = snakes.plugins.load(["ops", "labels", "gv"], "snakes.nets", "nets")
