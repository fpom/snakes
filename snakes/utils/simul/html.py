import json as JSON

def _tag (name) :
    return name.lower().strip("_")

class Tag (object) :
    default = {"a" : {"href" : "#"}}
    noclose = set([None, "br"])
    def __init__ (self, name, *children, **attr) :
        if name is not None :
            self.name = name.lower()
        else :
            self.name = None
        self.attr = dict(self._cleanup(attr))
        self.children = list(children)
    def _cleanup (self, attr) :
        for key, value in attr.items() :
            yield _tag(key), value
    def __call__ (self, *children, **attr) :
        self.children.extend(children)
        self.attr.update(self._cleanup(attr))
        return self
    def add (self, *children) :
        self.children.extend(children)
        return self
    def join (self, children) :
        if self.name not in self.noclose :
            raise ValueError("cannot join with tag %r" % self.name)
        lst = [children[0]]
        for c in children[1:] :
            lst.extend([self, c])
        return self.__class__(None, *lst)
    def __setitem__ (self, key, value) :
        self(**{_tag(key): value})
    def __delitem__ (self, key) :
        self.attr.pop(_tag(key), None)
    def __contains__ (self, key) :
        return _tag(key) in self.attr
    def __str__ (self) :
        attr = self.attr.copy()
        for key, value in self.default.get(self.name, {}).items() :
            if key not in attr :
                attr[key] = value
        if self.name is None :
            return "".join(str(c) for c in self.children)
        elif attr :
            ret = "<%s %s>%s" % (
                self.name,
                " ".join("%s=%r" % a for a in attr.items()),
                "".join(str(c) for c in self.children))
        else :
            ret = "<%s>%s" % (
                self.name,
                "".join(str(c) for c in self.children))
        if self.children or self.name not in self.noclose :
            return ret + "</%s>" % self.name
        else :
            return ret[:-1] + "/>"
    def __repr__ (self) :
        return repr(str(self))

class Factory (object) :
    def __getattr__ (self, name) :
        return Tag(_tag(name))

H = Factory()

def utf8 (text) :
    return text.encode("utf-8")

class JSONEncoder(JSON.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Tag):
            return utf8(str(obj))
        elif isinstance(obj, (unicode, str)) :
            return utf8(obj)
        else :
            return JSON.JSONEncoder.default(self, obj)

json = JSONEncoder().encode
