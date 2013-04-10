"""This package features the ABCD compiler, this is mainly a
command-line tool but it can be called also from Python. The API is
very simple and mimics the command line interface

### Function `snakes.utils.abcd.main.main` ###

    :::python
    def main (args=sys.argv[1:], src=None) : ...

Entry point of the compiler

##### Call API #####

  * `list args`:
  * `str src`:
  * `return PetriNet`:

##### Exceptions #####

  * `DeclarationError`: when
  * `CompilationError`: when

"""

# apidoc stop
from snakes import SnakesError

class CompilationError (SnakesError) :
    pass

class DeclarationError (SnakesError) :
    pass
