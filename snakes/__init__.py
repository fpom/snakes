"""SNAKES is the Net Algebra Kit for Editors and Simulators

@author: Franck Pommereau
@organization: University of Paris 12
@copyright: (C) 2005 Franck Pommereau
@license: GNU Lesser General Public Licence (aka. GNU LGPL),
    see the file C{doc/COPYING} in the distribution or visit U{the GNU
    web site<http://www.gnu.org/licenses/licenses.html#LGPL>}
@contact: pommereau@univ-paris12.fr

SNAKES is a Python library allowing to model all sorts of Petri nets
and to execute them. It is very general as most Petri nets annotations
can be arbitrary Python expressions while most values can be arbitrary
Python objects.

SNAKES can be further extended with plugins, several ones being
already provided, in particular two plugins implement the Petri nets
compositions defined for the Petri Box Calculus and its successors.
"""

version = "0.9.13"
defaultencoding = "utf-8"

class SnakesError (Exception) :
    "An error in SNAKES"
    pass

class ConstraintError (SnakesError) :
    "Violation of a constraint"
    pass

class NodeError (SnakesError) :
    "Error related to a place or a transition"
    pass

class DomainError (SnakesError) :
    "Function applied out of its domain"
    pass

class ModeError (SnakesError) :
    "The modes of a transition cannot be found"
    pass

class PluginError (SnakesError) :
    "Error when adding a plugin"
    pass

class UnificationError (SnakesError) :
    "Error while unifying parameters"
    pass
