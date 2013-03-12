"""This package implements SNAKES plugin system. SNAKES plugins
themselves are available as modules within the package.

Examples below are based on plugin `hello` that is distributed with
SNAKES to be used as an exemple of how to build a plugin. It extends
class `PetriNet` adding a method `hello` that says hello displaying
the name of the net.

## Loading plugins ##

The first example shows how to load a plugin: we load
`snakes.plugins.hello` and plug it into `snakes.nets`, which results
in a new module that is actually `snakes.nets` extended by
`snakes.plugins.hello`.

>>> import snakes.plugins as plugins
>>> hello_nets = plugins.load('hello', 'snakes.nets')
>>> n = hello_nets.PetriNet('N')
>>> n.hello()
Hello from N
>>> n = hello_nets.PetriNet('N', hello='Hi, this is %s!')
>>> n.hello()
Hi, this is N!

The next example shows how to simulate the effect of `import module`:
we give to `load` a thrid argument that is the name of the created
module, from which it becomes possible to import names or `*`.

>>> plugins.load('hello', 'snakes.nets', 'another_version')
<module ...>
>>> from another_version import PetriNet
>>> n = PetriNet('another net')
>>> n.hello()
Hello from another net
>>> n = PetriNet('yet another net', hello='Hi, this is %s!')
>>> n.hello()
Hi, this is yet another net!

The last example shows how to load several plugins at once, instead of
giving one plugin name, we just need to give a list of plugin names.

>>> plugins.load(['hello', 'pos'], 'snakes.nets', 'mynets')
<module ...>
>>> from mynets import PetriNet
>>> n = PetriNet('a net')
>>> n.hello()  # works thanks to plugin `hello`
Hello from a net
>>> n.bbox()   # works thanks to plugin `pos`
((0, 0), (0, 0))
"""

import imp, sys, inspect
from functools import wraps

# apidoc skip
def update (module, objects) :
    """Update a module content
    """
    for obj in objects :
        if isinstance(obj, tuple) :
            try :
                n, o = obj
            except :
                raise ValueError("expected (name, object) and got '%r'" % obj)
            setattr(module, n, o)
        elif inspect.isclass(obj) or inspect.isfunction(obj) :
            setattr(module, obj.__name__, obj)
        else :
            raise ValueError("cannot plug '%r'" % obj)

def load (plugins, base, name=None) :
    """Load plugins, `plugins` can be a single plugin name, a module
    or a list of such values. If `name` is not `None`, the extended
    module is loaded as `name` in `sys.modules` as well as in the
    global environment from which `load` was called.

    @param plugins: the module that implements the plugin, or its
        name, or a collection (eg, list, tuple) of such values
    @type plugins: `object`
    @param base: the module being extended or its name
    @type base: `object`
    @param name: the name of the created module
    @type name: `str`
    @return: the extended module
    @rtype: `module`
    """
    if type(base) is str :
        result = __import__(base, fromlist=["__name__"])
    else :
        result = base
    if isinstance(plugins, str) :
        plugins = [plugins]
    else :
        try :
            plugins = list(plugins)
        except TypeError :
            plugins = [plugins]
    for i, p in enumerate(plugins) :
        if isinstance(p, str) and not p.startswith("snakes.plugins.") :
            plugins[i] = "snakes.plugins." + p
    for plug in plugins :
        if type(plug) is str :
            plug = __import__(plug, fromlist=["__name__"])
        result = plug.extend(result)
    if name is not None :
        result.__name__ = name
        sys.modules[name] = result
        inspect.stack()[1][0].f_globals[name] = result
    return result

"""## Creating plugins ###

We show now how to develop a plugin that allows instances of
`PetriNet` to say hello: a new method `PetriNet.hello` is added and
the constructor `PetriNet.__init__` is added a keyword argument
`hello` for the message to print when calling method `hello`.

Defining a plugins required to write a module with a function called
`extend` that takes as its single argument the module to be extended.
Inside this function, extensions of the classes in the module are
defined as normal sub-classes. Function `extend` returns the extended
classes. A decorator called `plugin` must be used, it also allows to
resolve plugin dependencies and conflicts.
"""

# apidoc include "hello.py" lang="python"

"""Note that, when extending an existing method like `__init__` above,
we have to take care that you may be working on an already extended
class, consequently, we cannot know how its arguments have been
changed already. So, we must always use those from the unextended
method plus `**args`. Then, we remove from the latter what your plugin
needs and pass the remaining to the method of the base class if we
need to call it (which is usually the case). """

def plugin (base, depends=[], conflicts=[]) :
    """Decorator for extension functions

    @param base: name of base module (usually 'snakes.nets') that the
        plugin extends
    @type base: `str`
    @param depends: list of plugin names (as `str`) this one depends
        on, prefix `snakes.plugins.` may be omitted
    @type depends: `list`
    @param conflicts: list of plugin names with which this one
        conflicts
    @type conflicts: `list`
    @return: the appropriate decorator
    @rtype: `decorator`
    """
    def wrapper (fun) :
        @wraps(fun)
        def extend (module) :
            try :
                loaded = set(module.__plugins__)
            except AttributeError :
                loaded = set()
            for name in depends :
                if name not in loaded :
                    module = load(name, module)
                    loaded.update(module.__plugins__)
            conf = set(conflicts) & loaded
            if len(conf) > 0 :
                raise ValueError("plugin conflict (%s)" % ", ".join(conf))
            objects = fun(module)
            if type(objects) is not tuple :
                objects = (objects,)
            return build(fun.__module__, module, *objects)
        module = sys.modules[fun.__module__]
        module.__test__ = {"extend" : extend}
        objects = fun(__import__(base, fromlist=["__name__"]))
        if type(objects) is not tuple :
            objects = (objects,)
        update(module, objects)
        return extend
    return wrapper

# apidoc skip
def new_instance (cls, obj) :
    """Create a copy of `obj` which is an instance of `cls`
    """
    result = object.__new__(cls)
    result.__dict__.update(obj.__dict__)
    return result

# apidoc skip
def build (name, module, *objects) :
    """Builds an extended module.

    The parameter `module` is exactly that taken by the function
    `extend` of a plugin. This list argument `objects` holds all the
    objects, constructed in `extend`, that are extensions of objects
    from `module`. The resulting value should be returned by `extend`.

    @param name: the name of the constructed module
    @type name: `str`
    @param module: the extended module
    @type module: `module`
    @param objects: the sub-objects
    @type objects: each is a class object
    @return: the new module
    @rtype: `module`
    """
    result = imp.new_module(name)
    result.__dict__.update(module.__dict__)
    update(result, objects)
    result.__plugins__ = (module.__dict__.get("__plugins__",
                                              (module.__name__,))
                          + (name,))
    for obj in objects :
        if inspect.isclass(obj) :
            obj.__plugins__ = result.__plugins__
    return result
