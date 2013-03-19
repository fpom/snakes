"""This module features a parser for CTL* formula. Function `build`
parses the formula (see _concrete syntax_ below) and expands
sub-formulas; then it returns an abstract syntax tree (see _abstract
syntax_) below.

>>> from snakes.utils.ctlstar.build import *
>>> spec = '''
... atom even (x : int) :
...     return x % 2 == 0
... atom odd (x : int) :
...     return x % 2 == 1
... prop evenplace (p : place) :
...     exists tok in p (even(x=tok))
... prop oddplace (p : place) :
...     exists tok in p (odd(x=tok))
... A (G (evenplace(p=@'some_place') => F oddplace(p=@'another_place')))
... '''
>>> tree = build(spec)
>>> print ast.dump(tree)
CtlUnary(op=All(), child=CtlUnary(op=Globally(), child=CtlBinary(op=Imply(), ...

In the example above, `atom` allows to define parameterised atomic
propositions and `prop` allows to define sub-formulas. In the returned
syntax tree, all these objects are inlined and fully instantiated.

## Concrete syntax ##
"""

# apidoc include "../../lang/ctlstar/ctlstar.pgen" first=6 last=35 lang="text"

"""
## Abstract syntax ##
"""

# apidoc include "../../lang/ctlstar/ctlstar.asdl" first=3 last=59 lang="text"
pass
