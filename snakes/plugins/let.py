"""A dirty trick to allow side effects in expressions

Assignement takes place when method `bind` of the expression is
called. Assigned variables are then stored in the `Substitution`
passed to `bind`. This is useful in some cases when you want to
repeat a computation in several output arcs: you do it once in the
guard and then use the bounded variable on the output arcs.

>>> import snakes.plugins
>>> snakes.plugins.load('let', 'snakes.nets', 'snk')
<module ...>
>>> from snk import *
>>> n = PetriNet('n')
>>> t = Transition('t', Expression('x is not None and let("egg, spam = iter(str(foo))", foo=42, __raise__=True)'))
>>> n.add_transition(t)
>>> n.add_place(Place('p', [dot]))
>>> n.add_input('p', 't', Variable('x'))
>>> t.modes() == [Substitution(x=dot, foo=42, egg='4', spam='2')]
True

@param args: a list of `name=value` to assign
@return: `True` if assignment could be made, `False` otherwise
@rtype: `bool`
@warning: use with care, sides effects are nasty tricks, you may
  get unexpected results while playing with `let`
"""

import inspect
import snakes.plugins

from snakes.lang.python.parser import ast, parse
from snakes.lang import unparse

class DropLet (ast.NodeTransformer) :
    def __init__ (self, names) :
        ast.NodeTransformer.__init__(self)
        self.names = set(names)
        self.calls = []
    def visit_Call (self, node) :
        func = node.func
        if func.__class__.__name__ == "Name" and func.id in self.names :
            self.calls.append((func.id,
                               node.args and node.args[0].s or None,
                               [(k.arg, unparse(k.value))
                                for k in node.keywords]))
            return ast.Name(id="True")
        return node

class DropTrue (ast.NodeTransformer) :
    def visit_BoolOp (self, node) :
        if node.op.__class__.__name__ == "And" :
            values = [self.visit(v) for v in node.values
                      if v.__class__.__name__ != "Name" or v.id != "True"]
            if values :
                node.values[:] = values
                return node
            else :
                return ast.Name(id="True")
        else :
            return self.visit(node)

def unlet (expr, *names) :
    if not names :
        names = ["let"]
    drop = DropLet(names)
    new = DropTrue().visit(drop.visit(parse(expr)))
    return unparse(new), drop.calls

class MakeLet (object) :
    def __init__ (self, globals) :
        self.globals = globals
    def match (self, match, binding) :
        env = dict(binding)
        env.update(iter(self.globals))
        exec("", env)
        old = set(env)
        exec(match, env)
        for name in set(env) - old :
            binding[name] = env[name]
    def __call__ (__self__, __match__=None, __raise__=False, **args) :
        try :
            __binding__ = inspect.stack()[1][0].f_locals["__binding__"]
            for name, value in args.items() :
                __binding__[name] = value
            if __match__ :
                __self__.match(__match__, __binding__)
        except :
            if __raise__ :
                raise
            return False
        return True

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    class PetriNet (module.PetriNet) :
        def __init__ (self, name, **args) :
            module.PetriNet.__init__(self, name, **args)
            self.globals["let"] = MakeLet(self.globals)
    return PetriNet, unlet
