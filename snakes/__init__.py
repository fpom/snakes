"""SNAKES library is organised into three parts:

  * the core library is package `snakes` and its modules, among which
    `snakes.nets` is the one to work with Petri nets while the others
    can be seen as auxiliary modules
  * the plugin system and the plugins themselves reside into package
    `snakes.plugins`
  * auxiliary tools are kept into other sub-packages: `snakes.lang`
    for all the material related to parsing Python and other
    languages, `snakes.utils` for various utilities like the ABCD
    compiler

@author: Franck Pommereau
@organization: University of Evry/Paris-Saclay
@copyright: (C) 2005-2013 Franck Pommereau
@license: GNU Lesser General Public Licence (aka. GNU LGPL), see the
    file `doc/COPYING` in the distribution or visit the [GNU web
    site](http://www.gnu.org/licenses/licenses.html#LGPL)
@contact: franck.pommereau@ibisc.univ-evry.fr
"""

version = "0.9.18"
defaultencoding = "utf-8"

"""## Module `snakes`

This module only provides the exceptions used throughout SNAKES.
"""

class SnakesError (Exception) :
    "Generic error in SNAKES"
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
