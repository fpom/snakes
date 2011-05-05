"""A plugins system.

The first example shows how to load a plugin: we load
C{snakes.plugins.hello} and plug it into C{snakes.nets}, which results
in a new module that actually C{snakes.nets} extended by
C{snakes.plugins.hello}.

>>> import snakes.plugins as plugins
>>> hello_nets = plugins.load('hello', 'snakes.nets')
>>> n = hello_nets.PetriNet('N')
>>> n.hello()
Hello from N
>>> n = hello_nets.PetriNet('N', hello='Hi, this is %s!')
>>> n.hello()
Hi, this is N!

The next example shows how to simulate the effect of C{import module}:
we give to C{load} a thrid argument that is the name of the created
module, from which it becomes possible to import names or C{*}.

B{Warning:} this feature will not work C{load} is not called from the
module where we then do the C{from ... import ...}. This is exactly
the same when, from a module C{foo} that you load a module C{bar}: if
C{bar} loads other modules they will not be imported in C{foo}.

>>> plugins.load('hello', 'snakes.nets', 'another_version')
<module ...>
>>> from another_version import PetriNet
>>> n = PetriNet('another net')
>>> n.hello()
Hello from another net
>>> n = PetriNet('yet another net', hello='Hi, this is %s!')
>>> n.hello()
Hi, this is yet another net!

How to define a plugin is explained in the example C{hello}.
"""

import imp, sys, inspect
from functools import wraps

def update (module, objects) :
    """Update a module content
    """
    for obj in objects :
        if isinstance(obj, tuple) :
            try :
                n, o = obj
            except :
                raise ValueError, "expected (name, object) and got '%s'" % repr(obj)
            setattr(module, n, o)
        elif inspect.isclass(obj) or inspect.isfunction(obj) :
            setattr(module, obj.__name__, obj)
        else :
            raise ValueError, "cannot plug '%s'" % repr(obj)

def build (name, module, *objects) :
    """Builds an extended module.

    The parameter C{module} is exactly that taken by the function
    C{extend} of a plugin. This list argument C{objects} holds all the
    objects, constructed in C{extend}, that are extensions of objects
    from C{module}. The resulting value should be returned by
    C{extend}.

    @param name: the name of the constructed module
    @type name: C{str}
    @param module: the extended module
    @type module: C{module}
    @param objects: the sub-objects
    @type objects: each is a class object
    @return: the new module
    @rtype: C{module}
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

def load (plugins, base, name=None) :
    """Load plugins.

    C{plugins} can be a single plugin name or module or a list of such
    values. If C{name} is not C{None}, the extended module is loaded
    ad C{name} in C{sys.modules} as well as in the global environment
    from which C{load} was called.

    @param plugins: the module that implements the plugin, or its name,
      or a collection of such values
    @type plugins: C{str} or C{module}, or a C{list}/C{tuple}/... of
      such values
    @param base: the module being extended or its name
    @type base: C{str} or C{module}
    @param name: the name of the created module
    @type name: C{str}
    @return: the extended module
    @rtype: C{module}
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

def plugin (base, depends=[], conflicts=[]) :
    """Decorator for extension functions

    @param base: name of base module (usually 'snakes.nets')
    @type base: str
    @param depends: list of plugins on which this one depends
    @type depends: list of str
    @param conflicts: list of plugins with which this one conflicts
    @type conflicts: list of str
    @return: the appropriate decorator
    @rtype: function
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
                raise ValueError, "plugin conflict (%s)" % ", ".join(conf)
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

def new_instance (cls, obj) :
    """Create a copy of C{obj} which is an instance of C{cls}
    """
    result = object.__new__(cls)
    result.__dict__.update(obj.__dict__)
    return result
