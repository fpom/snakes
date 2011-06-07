"""Python 2 and 3 compatibility layer
"""

import sys

try :
    xrange
except NameError :
    xrange = range

try :
    reduce
except NameError :
    from functools import reduce

try :
    import StringIO as io
except ImportError :
    import io

try :
    next
except NameError :
    def next (obj) :
        return obj.next()

PY3 = sys.version > "3"
