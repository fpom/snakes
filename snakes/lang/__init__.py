import sys
if sys.version_info[:2] == (2, 6) :
    import ast
elif hasattr(sys, "pypy_version_info") :
    import astpypy as ast
elif hasattr(sys, "JYTHON_JAR") :
    import astjy25 as ast
elif sys.version_info[:2] == (2, 5) :
    import astpy25 as ast
else :
    raise NotImplementedError("unsupported Python version")

import unparse as _unparse
import StringIO

class Names (ast.NodeVisitor) :
    def __init__ (self) :
        ast.NodeVisitor.__init__(self)
        self.names = set()
    def visit_Name (self, node) :
        self.names.add(node.id)

def getvars (expr) :
    """
    >>> list(sorted(getvars('x+y<z')))
    ['x', 'y', 'z']
    >>> list(sorted(getvars('x+y<z+f(3,t)')))
    ['f', 't', 'x', 'y', 'z']
    """
    names = Names()
    names.visit(ast.parse(expr))
    return names.names - set(['None', 'True', 'False'])

class Unparser(_unparse.Unparser) :
    boolops = {ast.And: 'and', ast.Or: 'or'}
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

def unparse (st) :
    output = StringIO.StringIO()
    Unparser(st, output)
    return output.getvalue().strip()

class Renamer (ast.NodeTransformer) :
    def __init__ (self, map_names) :
        ast.NodeTransformer.__init__(self)
        self.map = map_names
    def visit_Name (self, node) :
        return ast.copy_location(ast.Name(id=self.map.get(node.id, node.id),
                                          ctx=ast.Load()), node)

def rename (expr, map={}, **ren) :
    """
    >>> rename('x+y<z', x='t')
    '((t + y) < z)'
    >>> rename('x+y<z+f(3,t)', f='g', t='z', z='t')
    '((x + y) < (t + g(3, z)))'
    """
    map_names = dict(map)
    map_names.update(ren)
    transf = Renamer(map_names)
    return unparse(transf.visit(ast.parse(expr)))

if __name__ == "__main__" :
    import doctest
    doctest.testmod()
