"""An example plugin that allows instances of `PetriNet` to
say hello. The source code can be used as a starting
example."""

import snakes.plugins

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    "Extends `module`"
    class PetriNet (module.PetriNet) :
        "Extension of the class `PetriNet` in `module`"
        def __init__ (self, name, **args) :
            """Add new keyword argument `hello`

            >>> PetriNet('N').hello()
            Hello from N
            >>> PetriNet('N', hello='Hi! This is %s...').hello()
            Hi! This is N...

            @param args: plugin options
            @keyword hello: the message to print, with
                `%s` where the net name should appear.
            @type hello: `str`
            """
            self._hello = args.pop("hello", "Hello from %s")
            module.PetriNet.__init__(self, name, **args)
        def hello (self) :
            "Ask the net to say hello"
            print(self._hello % self.name)
    return PetriNet
