"""An example plugin that allows instances class C{PetriNet} to say hello.

A new method C{hello} is added. The constructor is added a keyword
argument C{hello} that must be the C{str} to print when calling
C{hello}, with one C{%s} that will be replaced by the name of the net
when C{hello} is called.

Defining a plugins need writing a module with a single function called
C{extend} that takes a single argument that is the module to be
extended.

Inside the function, extensions of the classes in the module are
defined as normal sub-classes.

The function C{extend} should return the extended module created by
C{snakes.plugins.build} that takes as arguments: the name of the
extended module, the module taken as argument and the sub-classes
defined (expected as a list argument C{*args} in no special order).

If the plugin depends on other plugins, for instance C{foo} and
C{bar}, the function C{extend} should be decorated by
C{@depends('foo', 'bar')}.

Read the source code of this module to have an example
"""

import snakes.plugins

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    """Extends C{module}
    """
    class PetriNet (module.PetriNet) :
        """Extension of the class C{PetriNet} in C{module}
        """
        def __init__ (self, name, **args) :
            """When extending an existing method, take care that you
            may be working on an already extended class, so you so not
            know how its arguments have been changed. So, always use
            those from the unextended class plus C{**args}, remove
            from it what your plugin needs and pass it to the method
            of the extended class if you need to call it.

            >>> PetriNet('N').hello()
            Hello from N
            >>> PetriNet('N', hello='Hi! This is %s...').hello()
            Hi! This is N...

            @param args: plugin options
            @keyword hello: the message to print, with C{%s} where the
              net name should appear.
            @type hello: C{str}
            """
            self._hello = args.pop("hello", "Hello from %s")
            module.PetriNet.__init__(self, name, **args)
        def hello (self) :
            """A new method C{hello}

            >>> n = PetriNet('N')
            >>> n.hello()
            Hello from N
            """
            print(self._hello % self.name)
    return PetriNet
