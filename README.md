SNAKES is the Net Algebra Kit for Editors and Simulators
========================================================

SNAKES is a Python library that provides all the necessary to define
and execute many sorts of Petri nets, in particular algebras of Petri
nets. SNAKES' main aim is to be a general Petri net library, being
able to cope with most Petri nets models, and providing the researcher
with a tool to quickly prototype new ideas.

A key feature of SNAKES is the ability to use arbitrary Python objects
as tokens and arbitrary Python expressions in many points, for
instance in transitions guards or arcs outgoing of transitions. This
provides out of the box a great flexibility.

Another important feature of SNAKES is the plugin system that allows
to extend the features, for instance to work with specialised classes
of Petri nets (e.g., plugins are provided to draw nets, or to compose
them using the various control-flows operations). Plugins are another
way to introduce flexibility but requiring some involvement.

Next step to use SNAKES should be to read the tutorial that describes
installation and first steps.

Useful links
------------

* SNAKES homepage (documentation, tutorial, API reference, ...)
  http://www.ibisc.univ-evry.fr/~fpommereau/SNAKES/
* SNAKES development page (source repository, history, bug reports,
  feature requests, ...)
  https://github.com/fpom/snakes
  and its mirror at
  https://forge.ibisc.univ-evry.fr/fpom/snakes
* Follow [@SNAKESlib](https://twitter.com/SNAKESlib) on Twitter

Copyright / Licence
-------------------

(C) 2007-2014 [Franck Pommereau](mailto:franck.pommereau@ibisc.univ-evry.fr)

This library is free software; you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation; either version 2.1 of the
License, or (at your option) any later version.

This library is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
USA.
