"""This package is dedicated to parse and work with various languages,
in particular Python itself and ABCD. These are mainly utilities for
internal use in SNAKES, however, they may be of general interest
independently of SNAKES.

@todo: add documentation about how to use parsing and similar services
"""

import sys
if sys.version_info[:2] in ((2, 6), (2, 7)) :
    import ast
elif sys.version_info[0] == 3 :
    import ast
elif hasattr(sys, "pypy_version_info") :
    import astpypy as ast
elif hasattr(sys, "JYTHON_JAR") :
    import astjy25 as ast
elif sys.version_info[:2] == (2, 5) :
    import astpy25 as ast
else :
    raise NotImplementedError("unsupported Python version")

sys.modules["snkast"] = ast

"""### Module `ast` ###

The module `ast` exported by `snakes.lang` is similar to Python's
standard `ast` module (starting from version 2.6) but is available and
uniform on every implementation of Python supported by SNAKES: CPython
from 2.5, Jython and PyPy. (In general, these modules are available in
these implementation - except CPython 2.5 - but with slight
differences, so using `snakes.lang.ast` can be seen as a portable
implementation.)

Notice that this module is _not_ available for direct import but is
exposed as a member of `snakes.lang`. Moreover, when `snakes.lang` is
loaded, this module `ast` is also loaded as `snkast` in `sys.modules`,
this allows to have both versions from Python and SNAKES
simultaneously.

>>> import snakes.lang.ast as ast
ImportError ...
 ...
ImportError: No module named ast
>>> from snakes.lang import ast
>>> import snkast
"""

from . import unparse as _unparse
from snakes.compat import *

# apidoc skip
class Names (ast.NodeVisitor) :
    def __init__ (self) :
        ast.NodeVisitor.__init__(self)
        self.names = set()
    def visit_Name (self, node) :
        self.names.add(node.id)

def getvars (expr) :
    """Return the set of variables (or names in general) involved in a
    Python expression.

    >>> list(sorted(getvars('x+y<z')))
    ['x', 'y', 'z']
    >>> list(sorted(getvars('x+y<z+f(3,t)')))
    ['f', 't', 'x', 'y', 'z']

    @param expr: a Python expression
    @type expr: `str`
    @return: the set of variable names as strings
    @rtype: `set`
    """
    names = Names()
    names.visit(ast.parse(expr))
    return names.names - set(['None', 'True', 'False'])

# apidoc skip
class Unparser(_unparse.Unparser) :
    boolops = {"And": 'and', "Or": 'or'}
    def _Interactive (self, tree) :
        for stmt in tree.body :
            self.dispatch(stmt)
    def _Expression (self, tree) :
        self.dispatch(tree.body)
    def _ClassDef(self, tree):
        self.write("\n")
        for deco in tree.decorator_list:
            self.fill("@")
            self.dispatch(deco)
        self.fill("class "+tree.name)
        if tree.bases:
            self.write("(")
            for a in tree.bases:
                self.dispatch(a)
                self.write(", ")
            self.write(")")
        self.enter()
        self.dispatch(tree.body)
        self.leave()

# apidoc skip
def unparse (st) :
    output = io.StringIO()
    Unparser(st, output)
    return output.getvalue().strip()

# apidoc skip
class Renamer (ast.NodeTransformer) :
    def __init__ (self, map_names) :
        ast.NodeTransformer.__init__(self)
        self.map = [map_names]
    def visit_ListComp (self, node) :
        bind = self.map[-1].copy()
        for comp in node.generators :
            for name in getvars(comp.target) :
                if name in bind :
                    del bind[name]
        self.map.append(bind)
        node.elt = self.visit(node.elt)
        self.map.pop(-1)
        return node
    def visit_SetComp (self, node) :
        return self.visit_ListComp(node)
    def visit_DictComp (self, node) :
        bind = self.map[-1].copy()
        for comp in node.generators :
            for name in getvars(comp.target) :
                if name in bind :
                    del bind[name]
        self.map.append(bind)
        node.key = self.visit(node.key)
        node.value = self.visit(node.value)
        self.map.pop(-1)
        return node
    def visit_Name (self, node) :
        return ast.copy_location(ast.Name(id=self.map[-1].get(node.id,
                                                              node.id),
                                          ctx=ast.Load()), node)

def rename (expr, map={}, **ren) :
    """Rename variables (ie, names) in a Python expression

    >>> rename('x+y<z', x='t')
    '((t + y) < z)'
    >>> rename('x+y<z+f(3,t)', f='g', t='z', z='t')
    '((x + y) < (t + g(3, z)))'
    >>> rename('[x+y for x in range(3)]', x='z')
    '[(x + y) for x in range(3)]'
    >>> rename('[x+y for x in range(3)]', y='z')
    '[(x + z) for x in range(3)]'

    @param expr: a Python expression
    @type expr: `str`
    @param map: a mapping from old to new names (`str` to `str`)
    @type map: `dict`
    @param ren: additional mapping of old to new names
    @type ren: `str`
    @return: the new expression
    @rtype: `str`
    """
    map_names = dict(map)
    map_names.update(ren)
    transf = Renamer(map_names)
    return unparse(transf.visit(ast.parse(expr)))

# apidoc skip
class Binder (Renamer) :
    def visit_Name (self, node) :
        if node.id in self.map[-1] :
            return self.map[-1][node.id]
        else :
            return node

def bind (expr, map={}, **ren) :
    """Replace variables (ie, names) in an expression with other
    expressions. The replacements should be provided as `ast` nodes,
    and so could be arbitrary expression.

    >>> bind('x+y<z', x=ast.Num(n=2))
    '((2 + y) < z)'
    >>> bind('x+y<z', y=ast.Num(n=2))
    '((x + 2) < z)'
    >>> bind('[x+y for x in range(3)]', x=ast.Num(n=2))
    '[(x + y) for x in range(3)]'
    >>> bind('[x+y for x in range(3)]', y=ast.Num(n=2))
    '[(x + 2) for x in range(3)]'

    @param expr: a Python expression
    @type expr: `str`
    @param map: a mapping from old to new names (`str` to `ast.AST`)
    @type map: `dict`
    @param ren: additional mapping of old to new names
    @type ren: `ast.AST`
    @return: the new expression
    @rtype: `str`
    """
    map_names = dict(map)
    map_names.update(ren)
    transf = Binder(map_names)
    return unparse(transf.visit(ast.parse(expr)))

if __name__ == "__main__" :
    import doctest
    doctest.testmod()
