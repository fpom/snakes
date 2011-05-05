import sys, itertools
import snakes.apix, snakes.nets

apix = snakes.apix.Module(snakes.nets)

count, doc, test, api = 0, 0, 0, 0

for f in itertools.chain(apix.functions,
                         itertools.chain(*(c.proper_methods
                                           for c in apix.classes))) :
    count += 1
    if f.doc is not None :
        doc += 1
        if f.epydoc.doctest is not None :
            test += 1
        elif "notest" in f.comments or (hasattr(f, "container") and
                                        "notest" in f.container.comments) :
            test += 1
        else :
            print >>sys.stderr, f, "no test"
        if len(f.epydoc.type) > 0 :
            api += 1
        elif "noapi" in f.comments or (hasattr(f, "container") and
                                       "noapi" in f.container.comments) :
            api += 1
        else :
            print >>sys.stderr, f, "no api"
    elif "nodoc" in f.comments or (hasattr(f, "container") and
                                   "nodoc" in f.container.comments) :
        doc += 1
        test += 1
        api += 1
    else :
        print >>sys.stderr, f, "no doc"

print "Methods or functions:", count
print " + doc:  %u\t%.0f%%" % (doc, float(doc)/count*100)
print " + test: %u\t%.0f%%" % (test, float(test)/count*100)
print " + api:  %u\t%.0f%%" % (api, float(api)/count*100)

count, pnml, doc = 0, 0, 0

for c in apix.classes :
    count += 1
    if "__pnmldump__" in c._obj.__dict__ :
        pnml += 1
    elif "__pnmltag__" in c._obj.__dict__ :
        pnml += 1
    elif "nopnml" in c.comments :
        pnml += 1
    else :
        print >>sys.stderr, c, "no pnml"
    if c.doc is not None :
        doc += 1
    elif "nodoc" in c.comments  :
        doc += 1
    else :
        print >>sys.stderr, c, "no doc"

print "Classes:", count
print " + pnml: %u\t%.0f%%" % (count, float(pnml)/count*100)
print " + doc:  %u\t%.0f%%" % (doc, float(doc)/count*100)
