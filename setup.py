#!/usr/bin/env python

from distutils.core import setup

def doc_files () :
    import os, os.path
    result = {}
    for root, dirs, files in os.walk("doc") :
        target_dir = os.path.join("share/doc/python-snakes",
                                  *root.split(os.sep)[1:])
        for name in files :
            if target_dir not in result :
                result[target_dir] = []
            result[target_dir].append(os.path.join(root, name))
    return list(result.items())

def resources (root) :
    collected = ["*.txt", "*.html", "*.css", "*.js", "*.png", "*.jpg",
                 "*.ttf", "*.eot", "*.woff", "*.svg" ,"*.map"]
    import fnmatch, os, os.path
    result = []
    baselen = len(root.rstrip(os.sep).rsplit(os.sep, 1)[0]) + len(os.sep)
    def addfiles (dirname, filenames) :
        for name in filenames :
            for glob in collected :
                if fnmatch.fnmatch(name, glob) :
                    result.append(os.path.join(dirname[baselen:], name))
                    break
    for dirname, _, files in os.walk(root) :
        addfiles(dirname, files)
    return result

try :
    long_description=open("README").read()
except :
    long_description="""SNAKES is a general purpose Petri net Python
library allowing to define and execute most classes of Petri
nets. It features a plugin system to allow its extension. In
particular, plugins are provided to implement the operations
usually found in the PBC and M-nets family."""

if __name__ == "__main__" :
    emacs = [("share/emacs/site-lisp", ["utils/abcd-mode.el",
                                        "utils/abcd-mode.elc"])]
    setup(name="SNAKES",
          version=open("VERSION").read().strip(),
          description="SNAKES is the Net Algebra Kit for Editors and Simulators",
          long_description=long_description,
          author="Franck Pommereau",
          author_email="franck.pommereau@univ-evry.fr",
          maintainer="Franck Pommereau",
          maintainer_email="franck.pommereau@univ-evry.fr",
          url="http://snakes.ibisc.univ-evry.fr/",
          scripts=["bin/abcd",
                   "bin/snkc",
                   "bin/snkd",
                   ],
          packages=["snakes",
                    "snakes.lang",
                    "snakes.lang.abcd",
                    "snakes.lang.ctlstar",
                    "snakes.lang.pylib",
                    "snakes.lang.python",
                    "snakes.plugins",
                    "snakes.utils",
                    "snakes.utils.abcd",
                    "snakes.utils.ctlstar",
                    "snakes.utils.simul",
                    ],
          package_data={"snakes.utils.abcd": resources("snakes/utils/abcd/resources/"),
                        "snakes.utils.simul": resources("snakes/utils/simul/resources/"),
                    },
          data_files=doc_files() + emacs,
          classifiers=[
              "Intended Audience :: Science/Research",
              "Development Status :: 5 - Production/Stable",
              "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
              "Operating System :: OS Independent",
              "Programming Language :: Python",
              "Topic :: Scientific/Engineering",
              "Topic :: Software Development :: Libraries :: Python Modules",
          ],
          )
