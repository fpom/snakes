"""This module allows to save and load objects in PNML. The standard
is correctly handled for low-level nets, ie, nets with only `True`
guards and black tokens. However, module `snakes.pnml` was actually
created long before the PNML standard was extended to handle
high-level nets (in particular coloured variants) and so the standard
is not respected in this case. Consequently, in the following, we
abuse the term PNML for the XML produced and read by SNAKES.

@warning: this module will be replaced in a future version of SNAKES,
    so its documentation will be kept minimal.
"""

import xml.dom.minidom
import pickle
import sys, inspect, os, os.path, imp, pkgutil
import snakes, snakes.plugins
from snakes import SnakesError
from snakes.compat import *
if PY3 :
    import ast

try :
    builtins = sys.modules["__builtin__"]
except KeyError :
    builtins = sys.modules["builtins"]

def _snk_import (name) :
    "Properly import a module, including a plugin"
    if name.startswith("snakes.plugins.") :
        return snakes.plugins.load(name, "snakes.nets")
    else :
        return __import__(name, fromlist=["__name__"])

def _snk_modules () :
    "List all SNAKES' modules"
    queue = ["snakes"]
    while len(queue) > 0 :
        modname = queue.pop(0)
        try :
            mod = _snk_import(modname)
        except :
            continue
        yield modname, mod
        importer = pkgutil.ImpImporter(mod.__path__[0])
        for name, ispkg in importer.iter_modules(prefix=mod.__name__ + ".") :
            if ispkg :
                queue.append(name)
            else :
                try :
                    yield name, _snk_import(name)
                except :
                    pass

def _snk_tags () :
    "Lists all PNML tags found in SNAKES"
    for modname, mod in _snk_modules() :
        for clsname, cls in inspect.getmembers(mod, inspect.isclass) :
            if cls.__module__ == modname and "__pnmltag__" in cls.__dict__ :
                yield cls.__pnmltag__, modname, clsname

class _set (object) :
    """Set where items are iterated by order of insertion
    """
    def __init__ (self, elements=[]) :
        """
        >>> _set([4, 5, 1, 2, 4])
        _set([4, 5, 1, 2])
        """
        self._data = {}
        self._last = 0
        for e in elements :
            self.add(e)
    def __repr__ (self) :
        """
        >>> _set([4, 5, 1, 2, 4])
        _set([4, 5, 1, 2])
        """
        return "%s([%s])" % (self.__class__.__name__,
                             ", ".join(repr(x) for x in self))
    def add (self, element) :
        """
        >>> s = _set([4, 5, 1, 2, 4])
        >>> s.add(0)
        >>> s
        _set([4, 5, 1, 2, 0])
        >>> s.add(5)
        >>> s
        _set([4, 5, 1, 2, 0])
        """
        if element not in self._data :
            self._data[element] = self._last
            self._last += 1
    def __contains__ (self, element) :
        """
        >>> 4 in _set([4, 5, 1, 2, 4])
        True
        >>> 0 in _set([4, 5, 1, 2, 4])
        False
        """
        return element in self._data
    def _2nd (self, pair) :
        """
        >>> _set()._2nd((1, 2))
        2
        """
        return pair[1]
    def __iter__ (self) :
        """
        >>> list(_set([4, 5, 1, 2, 4]))
        [4, 5, 1, 2]
        """
        return (k for k, v in sorted(self._data.items(), key=self._2nd))
    def discard (self, element) :
        """
        >>> s = _set([4, 5, 1, 2, 4])
        >>> s.discard(0)
        >>> s.discard(4)
        >>> s
        _set([5, 1, 2])
        """
        if element in self._data :
            del self._data[element]
    def remove (self, element) :
        """
        >>> s = _set([4, 5, 1, 2, 4])
        >>> s.remove(0)
        Traceback (most recent call last):
         ...
        KeyError: ...
        >>> s.remove(4)
        >>> s
        _set([5, 1, 2])
        """
        del self._data[element]
    def copy (self) :
        """
        >>> _set([4, 5, 1, 2, 4]).copy()
        _set([4, 5, 1, 2])
        """
        return self.__class__(self)
    def __iadd__ (self, other) :
        """
        >>> s = _set([4, 5, 1, 2, 4])
        >>> s += range(7)
        >>> s
        _set([4, 5, 1, 2, 0, 3, 6])
        """
        for element in other :
            self.add(element)
        return self
    def __add__ (self, other) :
        """
        >>> _set([4, 5, 1, 2, 4]) + range(7)
        _set([4, 5, 1, 2, 0, 3, 6])
        """
        result = self.copy()
        result += other
        return result
    def __len__ (self) :
        """
        >>> len(_set([4, 5, 1, 2, 4]))
        4
        """
        return len(self._data)

# apidoc skip
class Tree (object) :
    """Abstraction of a PNML tree

    >>> Tree('tag', 'data', Tree('child', None), attr='attribute value')
    <?xml version="1.0" encoding="utf-8"?>
    <pnml>
     <tag attr="attribute value">
      <child/>
      data
     </tag>
    </pnml>
    """
    def __init__ (self, _name, _data, *_children, **_attributes) :
        """Initialize a PNML tree

        >>> Tree('tag', 'data',
        ...      Tree('first_child', None),
        ...      Tree('second_child', None),
        ...      first_attr='attribute value',
        ...      second_attr='another value')
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <tag first_attr="attribute value" second_attr="another value">
          <first_child/>
          <second_child/>
          data
         </tag>
        </pnml>

        Note: parameters names start with a '_' in order to allow for
        using them as attributes.

        @param _name: the name of the tag
        @type _name: `str`
        @param _data: the text held by the tag or `None`
        @type _data: `str` or `None`
        @param _children: children nodes
        @type _children: `Tree`
        @param _attributes: attributes and values of the tag
        @type _attributes: `str`
        """
        self.name = _name
        if _data is not None and _data.strip() == "" :
            _data = None
        self.data = _data
        self.children = list(_children)
        self.attributes = _attributes
    @classmethod
    def _load_tags (_class) :
        if not hasattr(_class, "_tags") :
            _class._tags = {}
            for tag, mod, cls in _snk_tags() :
                if tag not in _class._tags :
                    _class._tags[tag] = (mod, cls)
    def _update_node (self, doc, node) :
        for key, val in self.attributes.items() :
            node.setAttribute(key, val)
        for child in self.children :
            node.appendChild(child._to_dom(doc))
        if self.data is not None :
            node.appendChild(doc.createTextNode(self.data))
    def _to_dom (self, doc) :
        result = doc.createElement(self.name)
        self._update_node(doc, result)
        return result
    def to_pnml (self) :
        """Dumps a PNML tree to an XML string

        >>> print(Tree('tag', 'data', Tree('child', None), attr='value').to_pnml())
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <tag attr="value">
          <child/>
          data
         </tag>
        </pnml>

        @return: the XML string that represents the PNML tree
        @rtype: `str`
        """
        if self.name == "pnml" :
            tree = self
        else :
            tree = self.__class__("pnml", None, self)
        try :
            plugins = _set(self.__plugins__)
        except AttributeError :
            plugins = _set()
        for node in self.nodes() :
            if hasattr(node, "_plugins") :
                plugins += node._plugins
        if len(plugins) > 0 :
            tree.children.insert(0, Tree("snakes", None,
                                         Tree("plugins", None,
                                              Tree.from_obj(tuple(plugins))),
                                         version=snakes.version))
        impl = xml.dom.minidom.getDOMImplementation()
        doc = impl.createDocument(None, "pnml", None)
        node = tree._to_dom(doc)
        tree._update_node(doc, doc.documentElement)
        if len(plugins) > 0 :
            del tree.children[0]
        r = doc.toprettyxml(indent=" ",
                            encoding=snakes.defaultencoding).strip()
        if PY3 :
            return r.decode()
        else :
            return r
    @classmethod
    def from_dom (cls, node) :
        """Load a PNML tree from an XML DOM representation

        >>> src = Tree('object', '42', type='int').to_pnml()
        >>> dom = xml.dom.minidom.parseString(src)
        >>> Tree.from_dom(dom.documentElement)
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <object type="int">
          42
         </object>
        </pnml>

        @param node: the DOM node to load
        @type node: `xml.dom.minidom.Element`
        @return: the loaded PNML tree
        @rtype: `Tree`
        """
        result = cls(node.tagName, node.nodeValue)
        for i in range(node.attributes.length) :
            name = node.attributes.item(i).localName
            result[name] = str(node.getAttribute(name))
        if node.hasChildNodes() :
            for child in node.childNodes :
                if child.nodeType == child.TEXT_NODE :
                    result.add_data(str(child.data))
                elif child.nodeType == child.ELEMENT_NODE :
                    result.add_child(cls.from_dom(child))
        return result
    @classmethod
    def from_pnml (cls, source, plugins=[]) :
        """Load a PNML tree from an XML string representation

        >>> src = Tree('object', '42', type='int').to_pnml()
        >>> Tree.from_pnml(src)
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <object type="int">
          42
         </object>
        </pnml>

        @param source: the XML string to load or an opened file that
            contains it
        @type source: `str` or `file`
        @return: the loaded PNML tree
        @rtype: `Tree`
        """
        try :
            doc = xml.dom.minidom.parse(source)
        except :
            doc = xml.dom.minidom.parseString(source)
        result = cls.from_dom(doc.documentElement)
        plugins = _set(plugins)
        cls._load_tags()
        tag2obj = {}
        trash = []
        for node in result.nodes() :
            node._tag2obj = tag2obj
            if node.has_child("snakes") :
                snk = node.child("snakes")
                trash.append((node, snk))
                plugins += snk.child("plugins").child("object").to_obj()
            if node.name in cls._tags :
                modname, clsname = cls._tags[node.name]
                if modname.startswith("snakes.plugins.") :
                    plugins.add(modname)
                elif node.name not in tag2obj :
                    tag2obj[node.name] = getattr(_snk_import(modname), clsname)
        for parent, child in trash :
            parent.children.remove(child)
        plugins.discard("snakes.nets")
        nets = snakes.plugins.load(plugins, "snakes.nets")
        for name, obj in inspect.getmembers(nets, inspect.isclass) :
            # Skip classes that cannot be serialised to PNML
            try :
                tag = obj.__pnmltag__
            except AttributeError :
                continue
            # Get the last class in the hierarchy that has the same
            # "__pnmltag__" and is in the same module. This is useful
            # for instance for snakes.typing.Type and its subclasses:
            # the former should be called used of the laters because
            # it dispatches the call to "__pnmlload__" according to
            # "__pnmltype__".
            bases = [obj] + [c for c in inspect.getmro(obj)
                             if (c.__module__ == obj.__module__)
                             and hasattr(c, "__pnmltag__")
                             and c.__pnmltag__ == tag]
            tag2obj[tag] = bases[-1]
        return result
    def nodes (self) :
        """Iterate over all the nodes (top-down) in a tree

        >>> t = Tree('foo', None,
        ...          Tree('bar', None),
        ...          Tree('egg', None,
        ...               Tree('spam', None)))
        >>> for node in t.nodes() :
        ...     print(str(node))
        <PNML tree 'foo'>
        <PNML tree 'bar'>
        <PNML tree 'egg'>
        <PNML tree 'spam'>

        @return: an iterator on all the nodes in the tree, including
            this one
        @rtype: `generator`
        """
        yield self
        for child in self.children :
            for node in child.nodes() :
                yield node
    def update (self, other) :
        """Incorporates children, attributes and data from another PNML
        tree

        >>> t = Tree('foo', 'hello',
        ...          Tree('bar', None),
        ...          Tree('egg', None,
        ...               Tree('spam', None)))
        >>> o = Tree('foo', 'world',
        ...          Tree('python', None),
        ...          attr='value')
        >>> t.update(o)
        >>> t
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <foo attr="value">
          <bar/>
          <egg>
           <spam/>
          </egg>
          <python/>
          hello
          world
         </foo>
        </pnml>
        >>> o = Tree('oops', None,
        ...          Tree('hello', None),
        ...          attr='value')
        >>> try : t.update(o)
        ... except SnakesError : print(sys.exc_info()[1])
        tag mismatch 'foo', 'oops'

        @param other: the other tree to get data from
        @type other: `Tree`
        @raise SnakesError: when `other` has not the same tag as
            `self`
        """
        if self.name != other.name :
            raise SnakesError("tag mismatch '%s', '%s'" % (self.name, other.name))
        self.children.extend(other.children)
        self.attributes.update(other.attributes)
        self.add_data(other.data)
    def add_child (self, child) :
        """Add a child to a PNML tree

        >>> t = Tree('foo', None)
        >>> t.add_child(Tree('bar', None))
        >>> t
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <foo>
          <bar/>
         </foo>
        </pnml>

        @param child: the PNML tree to append
        @type child: `Tree`
        """
        self.children.append(child)
    def add_data (self, data, sep='\n') :
        """Appends data to the current node

        >>> t = Tree('foo', None)
        >>> t.add_data('hello')
        >>> t
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <foo>
          hello
         </foo>
        </pnml>
        >>> t.add_data('world')
        >>> t
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <foo>
          hello
          world
         </foo>
        </pnml>
        >>> t.add_data('!', '')
        >>> t
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <foo>
          hello
          world!
         </foo>
        </pnml>

        @param data: the data to add
        @type data: `str`
        @param sep: separator to insert between pieces of data
        @type sep: `str`
        """
        try :
            data = data.strip()
            if data != "" :
                if self.data is None :
                    self.data = data
                else :
                    self.data += sep + data
        except :
            pass
    def __getitem__ (self, name) :
        """Returns one attribute

        >>> Tree('foo', None, x='egg', y='spam')['x']
        'egg'
        >>> Tree('foo', None, x='egg', y='spam')['z']
        Traceback (most recent call last):
          ...
        KeyError: 'z'

        @param name: the name of the attribute
        @type name: `str`
        @return: the value of the attribute
        @rtype: `str`
        @raise KeyError: if no such attribute is found
        """
        return self.attributes[name]
    def __setitem__ (self, name, value) :
        """Sets an attribute

        >>> t = Tree('foo', None)
        >>> t['egg'] = 'spam'
        >>> t
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <foo egg="spam"/>
        </pnml>

        @param name: the name of the attribute
        @type name: `str`
        @param value: the value of the attribute
        @type value: `str`
        """
        self.attributes[name] = value
    def __iter__ (self) :
        """Iterate over children nodes

        >>> [str(node) for node in Tree('foo', None,
        ...                             Tree('egg', None),
        ...                             Tree('spam', None,
        ...                                  Tree('bar', None)))]
        ["<PNML tree 'egg'>", "<PNML tree 'spam'>"]

        @return: an iterator over direct children of the node
        @rtype: `generator`
        """
        return iter(self.children)
    def has_child (self, name) :
        """Test if the tree has the given tag as a direct child

        >>> t = Tree('foo', None,
        ...          Tree('egg', None),
        ...          Tree('spam', None,
        ...               Tree('bar', None)))
        >>> t.has_child('egg')
        True
        >>> t.has_child('bar')
        False
        >>> t.has_child('python')
        False

        @param name: tag name to search for
        @type name: `str`
        @return: a Boolean value indicating wether such a child was
            found or not
        @rtype: `bool`
        """
        for child in self :
            if child.name == name :
                return True
        return False
    def child (self, name=None) :
        """Return the direct child that as the given tag

        >>> t = Tree('foo', None,
        ...          Tree('egg', 'first'),
        ...          Tree('egg', 'second'),
        ...          Tree('spam', None,
        ...               Tree('bar', None)))
        >>> t.child('spam')
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <spam>
          <bar/>
         </spam>
        </pnml>
        >>> try : t.child('python')
        ... except SnakesError : print(sys.exc_info()[1])
        no child 'python'
        >>> try : t.child('bar')
        ... except SnakesError : print(sys.exc_info()[1])
        no child 'bar'
        >>> try : t.child('egg')
        ... except SnakesError : print(sys.exc_info()[1])
        multiple children 'egg'
        >>> try : t.child()
        ... except SnakesError : print(sys.exc_info()[1])
        multiple children

        @param name: name of the tag to search for, if `None`, the
            fisrt child is returned if it is the only child
        @type name: `str` or `None`
        @return: the only child with the given name, or the only child
            if no name is given
        @rtype: `Tree`
        @raise SnakesError: when no child or more than one child could
            be returned
        """
        result = None
        for child in self :
            if name is None or child.name == name :
                if result is None :
                    result = child
                elif name is None :
                    raise SnakesError("multiple children")
                else :
                    raise SnakesError("multiple children '%s'" % name)
        if result is None :
            raise SnakesError("no child '%s'" % name)
        return result
    def get_children (self, name=None) :
        """Iterates over direct children having the given tag

        >>> t = Tree('foo', None,
        ...          Tree('egg', 'first'),
        ...          Tree('egg', 'second'),
        ...          Tree('spam', None,
        ...               Tree('bar', None)))
        >>> [str(n) for n in t.get_children()]
        ["<PNML tree 'egg'>", "<PNML tree 'egg'>", "<PNML tree 'spam'>"]
        >>> [str(n) for n in t.get_children('egg')]
        ["<PNML tree 'egg'>", "<PNML tree 'egg'>"]
        >>> [str(n) for n in t.get_children('python')]
        []
        >>> [str(n) for n in t.get_children('bar')]
        []

        @param name: tag to search for or `None`
        @type name: `str` or `None`
        @return: iterator over all the children if `name` is `None`,
            or over the children with tag `name` otherwise
        @rtype: `generator`
        """
        for child in self :
            if name is None or child.name == name :
                yield child
    def __str__ (self) :
        """Return a simple string representation of the node

        >>> str(Tree('foo', None, Tree('child', None)))
        "<PNML tree 'foo'>"

        @return: simple string representation of the node
        @rtype: `str`
        """
        return "<PNML tree %r>" % self.name
    def __repr__ (self) :
        """Return a detailed representation of the node.

        This is actually the XML text that corresponds to the `Tree`,
        as returned by `Tree.to_pnml`.

        >>> print(repr(Tree('foo', None, Tree('child', None))))
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <foo>
          <child/>
         </foo>
        </pnml>

        @return: XML string representation of the node
        @rtype: `str`
        """
        return self.to_pnml()
    _elementary = set(("str", "int", "float", "bool"))
    _collection = set(("list", "tuple", "set"))
    @classmethod
    def from_obj (cls, obj) :
        """Builds a PNML tree from an object.

        Objects defined in SNAKES usually have a method `__pnmldump__`
        that handles the conversion, for instance:

        >>> import snakes.nets
        >>> Tree.from_obj(snakes.nets.Place('p'))
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <place id="p">
          <type domain="universal"/>
          <initialMarking>
           <multiset/>
          </initialMarking>
         </place>
        </pnml>

        Most basic Python classes are handled has readable XML:

        >>> Tree.from_obj(42)
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <object type="int">
          42
         </object>
        </pnml>
        >>> Tree.from_obj([1, 2, 3])
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <object type="list">
          <object type="int">
           1
          </object>
          <object type="int">
           2
          </object>
          <object type="int">
           3
          </object>
         </object>
        </pnml>

        Otherwise, the object is serialised using module `pickle`,
        which allows to embed almost anything into PNML.

        >>> import re
        >>> Tree.from_obj(re.compile('foo|bar')) # serialized data replaced with '...'
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <object type="pickle">
          ...
         </object>
        </pnml>

        @param obj: the object to convert to PNML
        @type obj: `object`
        @return: the corresponding PNML tree
        @rtype: `Tree`
        """
        try :
            result = obj.__pnmldump__()
            result._tag2obj = {result.name : obj}
            if hasattr(obj, "__plugins__") :
                result._plugins = obj.__plugins__
            return result
        except AttributeError :
            pass
        result = Tree("object", None)
        _type = type(obj)
        _name = _type.__name__
        if _name in cls._elementary :
            handler = result._set_elementary
        elif _name in cls._collection :
            handler = result._set_collection
        elif inspect.ismethod(obj) :
            handler = result._set_method
            _name = "method"
        elif inspect.isclass(obj) :
            handler = result._set_class
            _name = "class"
        elif inspect.isroutine(obj) :
            handler = result._set_function
            _name = "function"
        elif inspect.ismodule(obj) :
            handler = result._set_module
            _name = "module"
        else :
            try :
                handler = getattr(result, "_set_" + _name)
            except AttributeError :
                handler = result._set_pickle
                _name = "pickle"
        result["type"] = _name
        handler(obj)
        return result
    def _set_NoneType (self, value) :
        pass
    def _get_NoneType (self) :
        pass
    def _set_elementary (self, value) :
        self.data = str(value)
    def _get_elementary (self) :
        if self["type"] == "bool" :
            return self.data.strip() == "True"
        return getattr(builtins, self["type"])(self.data)
    def _set_collection (self, value) :
        for v in value :
            self.add_child(self.from_obj(v))
    def _get_collection (self) :
        return getattr(builtins, self["type"])(child.to_obj()
                                               for child in self)
    def _set_dict (self, value) :
        for k, v in value.items() :
            self.add_child(Tree("item", None,
                                Tree("key", None, self.from_obj(k)),
                                Tree("value", None, self.from_obj(v))))
    def _get_dict (self) :
        return dict((child.child("key").child("object").to_obj(),
                     child.child("value").child("object").to_obj())
                    for child in self)
    def _native (self, obj) :
        try :
            if (obj.__module__ in ("__builtin__", "__builtins__", "builtins")
                or obj.__module__ == "snakes"
                or obj.__module__.startswith("snakes")
                or inspect.isbuiltin(obj)) :
                return True
        except :
            pass
        try :
            lib = os.path.dirname(inspect.getfile(inspect.getfile))
            if os.path.isfile(lib) :
                lib = os.path.dirname(lib)
            lib += os.sep
            try :
                path = inspect.getfile(obj)
            except :
                path = inspect.getmodule(obj).__file__
            return path.startswith(lib)
        except :
            return False
    def _name (self, obj) :
        try :
            name = obj.__module__
        except :
            name = inspect.getmodule(obj).__name__
        if name in ("__builtin__", "__builtins__", "builtins") :
            return obj.__name__
        else :
            return name + "." + obj.__name__
    def _set_class (self, value) :
        if self._native(value) :
            self["name"] = self._name(value)
        else :
            self._set_pickle(value)
    def _get_class (self) :
        if self.data :
            return self._get_pickle()
        elif "." in self["name"] :
            module, name = self["name"].rsplit(".", 1)
            return getattr(__import__(module, fromlist=[name]), name)
        else :
            return getattr(builtins, self["name"])
    def _set_function (self, value) :
        self._set_class(value)
    def _get_function (self) :
        return self._get_class()
    def _set_method (self, value) :
        self._set_function(value)
        self["name"] = "%s.%s" % (self["name"], value.__name__)
    def _get_method (self) :
        if self.data :
            return self._get_pickle()
        module, cls, name = self["name"].rsplit(".", 2)
        cls = getattr(__import__(module, fromlist=[name]), name)
        return getattr(cls, name)
    def _set_module (self, value) :
        self["name"] = value.__name__
    def _get_module (self) :
        return __import__(self["name"], fromlist=["__name__"])
    def _set_pickle (self, value) :
        self["type"] = "pickle"
        self.data = pickle.dumps(value)
        if PY3 :
            self.data = repr(self.data)
    def _get_pickle (self) :
        if PY3 :
            return pickle.loads(ast.literal_eval(self.data))
        else :
            return pickle.loads(self.data)
    def to_obj (self) :
        """Build an object from its PNML representation

        This is just the reverse as `Tree.from_obj`, objects that have
        a `__pnmldump__` method should also have a `__pnmlload__`
        class method to perform the reverse operation, together with
        an attribute `__pnmltag__`. Indeed, when a PNML node with tag
        name 'foo' has to be converted to an object, a class `C` such
        that `C.__pnmltag__ == 'foo'` is searched in module
        `snakes.nets` and `C.__pnmlload__(tree)` is called to rebuild
        the object.

        Standard Python objects and pickled ones are also recognised
        and correctly rebuilt.

        >>> import snakes.nets
        >>> Tree.from_obj(snakes.nets.Place('p')).to_obj()
        Place('p', MultiSet([]), tAll)
        >>> Tree.from_obj(42).to_obj()
        42
        >>> Tree.from_obj([1, 2, 3]).to_obj()
        [1, 2, 3]
        >>> import re
        >>> Tree.from_obj(re.compile('foo|bar')).to_obj()
        <... object at ...>

        @return: the Python object encoded by the PNML tree
        @rtype: `object`
        """
        if self.name == "pnml" :
            if len(self.children) == 0 :
                raise SnakesError("empty PNML content")
            elif len(self.children) == 1 :
                return self.child().to_obj()
            else :
                return tuple(child.to_obj() for child in self.children
                             if child.name != "snakes")
        elif self.name == "object" :
            if self["type"] in self._elementary :
                handler = self._get_elementary
            elif self["type"] in self._collection :
                handler = self._get_collection
            else :
                try :
                    handler = getattr(self, "_get_" + self["type"])
                except AttributeError :
                    handler = self._get_pickle
            return handler()
        elif self.name != "snakes" :
            try :
                if self.name in self._tag2obj :
                    return self._tag2obj[self.name].__pnmlload__(self)
            except AttributeError :
                pass
        raise SnakesError("unsupported PNML tag '%s'" % self.name)

def dumps (obj) :
    """Dump an object to a PNML string, any Python object may be
    serialised this way (resorting to pickling when the object does
    not support serialisation to PNML).

    >>> print(dumps(42))
    <?xml version="1.0" encoding="utf-8"?>
    <pnml>
     <object type="int">
      42
     </object>
    </pnml>

    @param obj: the object to dump
    @type obj: `object`
    @return: the PNML that represents the object
    @rtype: `str`
    """
    return Tree.from_obj(obj).to_pnml()

def loads (source, plugins=[]) :
    """Load an object from a PNML string

    >>> loads(dumps(42))
    42

    @param source: the data to parse
    @type source: `str`
    @return: the object represented by the source
    @rtype: `object`
    """
    return Tree.from_pnml(source, plugins).to_obj()
