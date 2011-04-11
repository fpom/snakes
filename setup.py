#!/usr/bin/env python

import sys, os
from distutils.core import setup

def doc_files() :
    import os, os.path
    result = {}
    for root, dirs, files in os.walk("doc") :
        target_dir = os.path.join("share/doc/python-snakes",
                                  *root.split(os.sep)[1:])
        for name in files :
            if target_dir not in result :
                result[target_dir] = []
            result[target_dir].append(os.path.join(root, name))
    result["share/doc/python-snakes"] = ["NEWS",
                                         "README",
                                         "TODO",
                                         "VERSION",
                                         ]
    return result.items()

print "Compiling Emacs files..."
os.system("emacs -batch -f batch-byte-compile utils/abcd-mode.el")

setup(name="SNAKES",
      version=open("VERSION").read().strip(),
      description="SNAKES is the Net Algebra Kit for Editors and Simulators",
      long_description="""SNAKES is a general purpose Petri net Python
      library allowing to define and execute most classes of Petri
      nets. It features a plugin system to allow its extension. In
      particular, plugins are provided to implement the operations
      usually found in the PBC and M-nets family.""",
      author="Franck Pommereau",
      author_email="pommereau@univ-paris12.fr",
      maintainer="Franck Pommereau",
      maintainer_email="pommereau@univ-paris12.fr",
      url="http://lacl.univ-paris12.fr/pommereau/soft/snakes",
      scripts=["bin/abcd",
               "bin/snkc",
               "bin/snkd",
               ],
      packages=["snakes",
                "snakes.lang",
                "snakes.lang.pylib",
                "snakes.lang.python",
                "snakes.lang.abcd",
                "snakes.plugins",
                "snakes.utils",
                "snakes.utils.abcd",
                ],
      data_files=(doc_files()
                  + [("share/emacs/site-lisp", ["utils/abcd-mode.el",
                                                "utils/abcd-mode.elc"])]),
      )
