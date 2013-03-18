"""A plugin to add labels to nodes and nets. Labels are names (valid
Python identifiers) associated to arbitrary objects.

>>> import snakes.plugins
>>> snakes.plugins.load('labels', 'snakes.nets', 'nets')
<module ...>
>>> from nets import *
>>> t = Transition('t')
>>> t.label(foo='bar', spam=42)
>>> t.label('foo')
'bar'
>>> t.label('spam')
42

Note that when nodes in a Petri net are merged, their labels are
merged too, but in an arbitrary order. So, for example:

>>> n = PetriNet('N')
>>> n.add_place(Place('p1'))
>>> n.place('p1').label(foo='bar', spam='ham')
>>> n.add_place(Place('p2'))
>>> n.place('p2').label(hello='world', spam='egg')
>>> n.merge_places('p', ['p1', 'p2'])
>>> n.place('p').label('hello')
'world'
>>> n.place('p').label('foo')
'bar'
>>> n.place('p').label('spam') in ['ham', 'egg']
True

In the latter statement, we cannot know whether the label will be one
or the other value because merging has been done in an arbitrary
order.
"""

from snakes.plugins import plugin, new_instance
from snakes.pnml import Tree

@plugin("snakes.nets")
def extend (module) :
    class Transition (module.Transition) :
        def label (self, *get, **set) :
            """Get and set labels for the transition. The labels given
            in `get` will be returned as a `tuple` and the labels
            assigned in `set` will be changed accordingly. If a label
            is given both in `get`and `set`, the returned value is
            that it had at the beginning of the call, ie, before it is
            set by the call.

            @param get: labels which values have to be returned
            @type get: `str`
            @param set: labels which values have to be changed
            @type set: `object`
            @return: the tuples of values corresponding to `get`
            @rtype: `tuple`
            @raise KeyError: when a label given in `get` has not been
                assigned previouly
            """
            if not hasattr(self, "_labels") :
                self._labels = {}
            result = tuple(self._labels[g] for g in get)
            self._labels.update(set)
            if len(get) == 1 :
                return result[0]
            elif len(get) > 1 :
                return result
            elif len(set) == 0 :
                return self._labels.copy()
        def has_label (self, name, *names) :
            """Check is a label has been assigned to the transition.

            @param name: the label to check
            @type name: `str`
            @param names: additional labels to check, if used, the
                return value is a `tuple` of `bool` instead of a
                single `bool`
            @return: a Boolean indicating of the checked labels are
                present or not in the transitions
            @rtype: `bool`
            """
            if len(names) == 0 :
                return name in self._labels
            else :
                return tuple(n in self._labels for n in (name,) + names)
        # apidoc stop
        def copy (self, name=None, **options) :
            if not hasattr(self, "_labels") :
                self._labels = {}
            result = module.Transition.copy(self, name, **options)
            result._labels = self._labels.copy()
            return result
        def __pnmldump__ (self) :
            """
            >>> t = Transition('t')
            >>> t.label(foo='bar', spam=42)
            >>> t.__pnmldump__()
            <?xml version="1.0" encoding="utf-8"?>
            <pnml>
             <transition id="t">
              <label name="foo">
               <object type="str">
                bar
               </object>
              </label>
              <label name="spam">
               <object type="int">
                42
               </object>
              </label>
             </transition>
            </pnml>
            """
            t = module.Transition.__pnmldump__(self)
            if hasattr(self, "_labels") :
                for key, val in self._labels.items() :
                    t.add_child(Tree("label", None,
                                     Tree.from_obj(val),
                                     name=key))
            return t
        @classmethod
        def __pnmlload__ (cls, tree) :
            """
            >>> old = Transition('t')
            >>> old.label(foo='bar', spam=42)
            >>> p = old.__pnmldump__()
            >>> new = Transition.__pnmlload__(p)
            >>> new
            Transition('t', Expression('True'))
            >>> new.__class__
            <class 'snakes.plugins.labels.Transition'>
            >>> new.label('foo', 'spam')
            ('bar', 42)
            """
            t = new_instance(cls, module.Transition.__pnmlload__(tree))
            t._labels = dict((lbl["name"], lbl.child().to_obj())
                             for lbl in tree.get_children("label"))
            return t
    class Place (module.Place) :
        def label (self, *get, **set) :
            "See documentation for `Transition.label` above"
            if not hasattr(self, "_labels") :
                self._labels = {}
            result = tuple(self._labels[g] for g in get)
            self._labels.update(set)
            if len(get) == 1 :
                return result[0]
            elif len(get) > 1 :
                return result
            elif len(set) == 0 :
                return self._labels.copy()
        def has_label (self, name, *names) :
            "See documentation for `Transition.has_label` above"
            if len(names) == 0 :
                return name in self._labels
            else :
                return tuple(n in self._labels for n in (name,) + names)
        # apidoc stop
        def copy (self, name=None, **options) :
            if not hasattr(self, "_labels") :
                self._labels = {}
            result = module.Place.copy(self, name, **options)
            result._labels = self._labels.copy()
            return result
        def __pnmldump__ (self) :
            """
            >>> p = Place('p')
            >>> p.label(foo='bar', spam=42)
            >>> p.__pnmldump__()
            <?xml version="1.0" encoding="utf-8"?>
            <pnml>
             <place id="p">
              <type domain="universal"/>
              <initialMarking>
               <multiset/>
              </initialMarking>
              <label name="foo">
               <object type="str">
                bar
               </object>
              </label>
              <label name="spam">
               <object type="int">
                42
               </object>
              </label>
             </place>
            </pnml>
            """
            t = module.Place.__pnmldump__(self)
            if hasattr(self, "_labels") :
                for key, val in self._labels.items() :
                    t.add_child(Tree("label", None,
                                     Tree.from_obj(val),
                                     name=key))
            return t
        @classmethod
        def __pnmlload__ (cls, tree) :
            """
            >>> old = Place('p')
            >>> old.label(foo='bar', spam=42)
            >>> p = old.__pnmldump__()
            >>> new = Place.__pnmlload__(p)
            >>> new
            Place('p', MultiSet([]), tAll)
            >>> new.__class__
            <class 'snakes.plugins.labels.Place'>
            >>> new.label('foo', 'spam')
            ('bar', 42)
            """
            p = new_instance(cls, module.Place.__pnmlload__(tree))
            p._labels = dict((lbl["name"], lbl.child().to_obj())
                             for lbl in tree.get_children("label"))
            return p
    class PetriNet (module.PetriNet) :
        def label (self, *get, **set) :
            "See documentation for `Transition.label` above"
            if not hasattr(self, "_labels") :
                self._labels = {}
            result = tuple(self._labels[g] for g in get)
            self._labels.update(set)
            if len(get) == 1 :
                return result[0]
            elif len(get) > 1 :
                return result
            elif len(set) == 0 :
                return self._labels.copy()
        def has_label (self, name, *names) :
            "See documentation for `Transition.has_label` above"
            if len(names) == 0 :
                return name in self._labels
            else :
                return tuple(n in self._labels for n in (name,) + names)
        # apidoc stop
        def copy (self, name=None, **options) :
            if not hasattr(self, "_labels") :
                self._labels = {}
            result = module.PetriNet.copy(self, name, **options)
            result._labels = self._labels.copy()
            return result
        def __pnmldump__ (self) :
            """
            >>> n = PetriNet('n')
            >>> n.label(foo='bar', spam=42)
            >>> n.__pnmldump__()
            <?xml version="1.0" encoding="utf-8"?>
            <pnml>
             <net id="n">
              <label name="foo">
               <object type="str">
                bar
               </object>
              </label>
              <label name="spam">
               <object type="int">
                42
               </object>
              </label>
             </net>
            </pnml>
            """
            t = module.PetriNet.__pnmldump__(self)
            if hasattr(self, "_labels") :
                for key, val in self._labels.items() :
                    t.add_child(Tree("label", None,
                                     Tree.from_obj(val),
                                     name=key))
            return t
        @classmethod
        def __pnmlload__ (cls, tree) :
            """
            >>> old = PetriNet('n')
            >>> old.label(foo='bar', spam=42)
            >>> p = old.__pnmldump__()
            >>> new = PetriNet.__pnmlload__(p)
            >>> new
            PetriNet('n')
            >>> new.__class__
            <class 'snakes.plugins.labels.PetriNet'>
            >>> new.label('foo', 'spam')
            ('bar', 42)
            """
            n = new_instance(cls, module.PetriNet.__pnmlload__(tree))
            n._labels = dict((lbl["name"], lbl.child().to_obj())
                             for lbl in tree.get_children("label"))
            return n
        def merge_places (self, target, sources, **options) :
            module.PetriNet.merge_places(self, target, sources, **options)
            new = self.place(target)
            for place in sources :
                new.label(**dict(self.place(place).label()))
        def merge_transitions (self, target, sources, **options) :
            module.PetriNet.merge_transitions(self, target, sources, **options)
            new = self.transition(target)
            for trans in sources :
                new.label(**dict(self.transition(trans).label()))
    return Transition, Place, PetriNet
