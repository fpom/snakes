"""An example plugin that allows instances class `PetriNet` to say hello.

A new method `hello` is added. The constructor is added a keyword
argument `hello` that must be the `str` to print when calling `hello`,
with one `%s` that will be replaced by the name of the net when
`hello` is called.

Defining a plugins need writing a module with a single function called
`extend` that takes a single argument that is the module to be
extended.

Inside the function, extensions of the classes in the module are
defined as normal sub-classes.

The function `extend` should return the extended module created by
`snakes.plugins.build` that takes as arguments: the name of the
extended module, the module taken as argument and the sub-classes
defined (expected as a list argument `*args` in no special order).

If the plugin depends on other plugins, for instance `foo` and `bar`,
the function `extend` should be decorated by `@depends('foo', 'bar')`.

Read the source code of this module to have an example
"""

import snakes.plugins

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    """Extends `module`
    """
    class PetriNet (module.PetriNet) :
        """Extension of the class `PetriNet` in `module`
        """
        def __init__ (self, name, **args) :
            """When extending an existing method, take care that you may
            be working on an already extended class, so you so not
            know how its arguments have been changed. So, always use
            those from the unextended class plus `**args`, remove from
            it what your plugin needs and pass it to the method of the
            extended class if you need to call it.
            
            >>> PetriNet('N').hello()
            Hello from N
            >>> PetriNet('N', hello='Hi! This is %s...').hello()
            Hi! This is N...
            
            @param args: plugin options
            @keyword hello: the message to print, with `%s` where the
                net name should appear.
            @type hello: `str`
            """
            self._hello = args.pop("hello", "Hello from %s")
            module.PetriNet.__init__(self, name, **args)
        def hello (self) :
            """A new method `hello`
            
            >>> n = PetriNet('N')
            >>> n.hello()
            Hello from N
            """
            print(self._hello % self.name)
    return PetriNet
