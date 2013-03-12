"""
@todo: revise (actually make) documentation
"""

from snakes.plugins import plugin
from snakes.pnml import Tree, loads, dumps
import imp, sys, socket, traceback, operator

class QueryError (Exception) :
    pass

class Query (object) :
    def __init__ (self, name, *larg, **karg) :
        self._name = name
        self._larg = tuple(larg)
        self._karg = dict(karg)
    __pnmltag__ = "query"
    def __pnmldump__ (self) :
        """
        >>> Query('set', 'x', 42).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <query name="set">
          <argument>
           <object type="str">
            x
           </object>
          </argument>
          <argument>
           <object type="int">
            42
           </object>
          </argument>
         </query>
        </pnml>
        >>> Query('test', x=1).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <query name="test">
          <keyword name="x">
           <object type="int">
            1
           </object>
          </keyword>
         </query>
        </pnml>
        >>> Query('test', 'x', 42, y=1).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <query name="test">
          <argument>
           <object type="str">
            x
           </object>
          </argument>
          <argument>
           <object type="int">
            42
           </object>
          </argument>
          <keyword name="y">
           <object type="int">
            1
           </object>
          </keyword>
         </query>
        </pnml>
        >>> Query('set', 'x', Query('call', 'x.upper')).__pnmldump__()
        <?xml version="1.0" encoding="utf-8"?>
        <pnml>
         <query name="set">
          <argument>
           <object type="str">
            x
           </object>
          </argument>
          <argument>
           <query name="call">
            <argument>
             <object type="str">
              x.upper
             </object>
            </argument>
           </query>
          </argument>
         </query>
        </pnml>
        """
        children = []
        for arg in self._larg :
            children.append(Tree("argument", None,
                                 Tree.from_obj(arg)))
        for name, value in self._karg.items() :
            children.append(Tree("keyword", None,
                                 Tree.from_obj(value),
                                 name=name))
        return Tree(self.__pnmltag__, None, *children, **{"name": self._name})
    @classmethod
    def __pnmlload__ (cls, tree) :
        """
        >>> Tree._tag2obj = {'query': Query}
        >>> t = Query('test', 'x', 42, y=1).__pnmldump__()
        >>> q = Query.__pnmlload__(t)
        >>> q._name
        'test'
        >>> q._larg
        ('x', 42)
        >>> q._karg
        {'y': 1}
        """
        larg = (child.child().to_obj()
                for child in tree.get_children("argument"))
        karg = dict((child["name"], child.child().to_obj())
                    for child in tree.get_children("keyword"))
        return cls(tree["name"], *larg, **karg)
    def run (self, envt) :
        """
        >>> import imp
        >>> env = imp.new_module('environment')
        >>> Query('set', 'x', 'hello').run(env)
        >>> env.x
        'hello'
        >>> Query('set', 'x', Query('call', 'x.upper')).run(env)
        >>> env.x
        'HELLO'
        >>> Query('test', 1, 2, 3).run(env)
        Traceback (most recent call last):
         ...
        QueryError: unknown query 'test'
        """
        try :
            handler = getattr(self, "_run_%s" % self._name)
        except AttributeError :
            raise QueryError("unknown query %r" % self._name)
        self._envt = envt
        larg = tuple(a.run(envt) if isinstance(a, self.__class__) else a
                     for a in self._larg)
        karg = dict((n, v.run(envt) if isinstance(v, self.__class__) else v)
                    for n, v in self._karg.items())
        try :
            return handler(*larg, **karg)
        except TypeError :
            cls, val, tb = sys.exc_info()
            try :
                fun, msg = str(val).strip().split("()", 1)
            except :
                raise val
            if fun.startswith("_run_") and hasattr(self, fun) :
                raise TypeError(fun[5:] + "()" + msg)
            raise val
    def _get_object (self, path) :
        obj = self._envt
        for n in path :
            obj = getattr(obj, n)
        return obj
    def _run_set (self, name, value) :
        """
        >>> import imp
        >>> env = imp.new_module('environment')
        >>> Query('set', 'x', 1).run(env)
        >>> env.x
        1
        """
        path = name.split(".")
        setattr(self._get_object(path[:-1]), path[-1], value)
    def _run_get (self, name) :
        """
        >>> import imp
        >>> env = imp.new_module('environment')
        >>> env.x = 2
        >>> Query('get', 'x').run(env)
        2
        """
        path = name.split(".")
        return self._get_object(path)
    def _run_del (self, name) :
        """
        >>> import imp
        >>> env = imp.new_module('environment')
        >>> env.x = 2
        >>> Query('del', 'x').run(env)
        >>> env.x
        Traceback (most recent call last):
         ...
        AttributeError: 'module' object has no attribute 'x'
        """
        path = name.split(".")
        delattr(self._get_object(path[:-1]), path[-1])
    def _run_call (self, fun, *larg, **karg) :
        """
        >>> import imp
        >>> env = imp.new_module('environment')
        >>> env.x = 'hello'
        >>> Query('call', 'x.center', 7).run(env)
        ' hello '
        >>> env.__dict__.update(__builtins__)
        >>> Query('call', Query('call', 'getattr',
        ...                     Query('call', 'x.center', 7),
        ...                     'upper')).run(env)
        ' HELLO '
        """
        if isinstance(fun, str) :
            fun = self._get_object(fun.split("."))
        return fun(*larg, **karg)

@plugin("snakes.nets")
def extend (module) :
    class UDPServer (object) :
        def __init__ (self, port, size=2**20, verbose=0) :
            self._size = size
            self._verbose = verbose
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.bind(("", port))
            self._env = imp.new_module("snk")
            self._env.__dict__.update(__builtins__)
            self._env.__dict__.update(operator.__dict__)
            self._env.__dict__.update(module.__dict__)
        def recvfrom (self) :
            return self._sock.recvfrom(self._size)
        def sendto (self, data, address) :
            self._sock.sendto(data.strip() + "\n", address)
        def run (self) :
            while True :
                data, address = self.recvfrom()
                data = data.strip()
                if self._verbose :
                    print("# query from %s:%u" % address)
                try :
                    if self._verbose > 1 :
                        print(data)
                    res = loads(data).run(self._env)
                    if res is None :
                        res = Tree("answer", None, status="ok")
                    else :
                        res = Tree("answer", None, Tree.from_obj(res),
                                   status="ok")
                except :
                    cls, val, tb = sys.exc_info()
                    res = Tree("answer", str(val).strip(),
                               error=cls.__name__, status="error")
                    if self._verbose > 1 :
                        print("# error")
                        for entry in traceback.format_exception(cls, val, tb) :
                            for line in entry.splitlines() :
                                print("## %s" % line)
                if self._verbose :
                    if self._verbose > 1 :
                        print("# answer")
                        print(res.to_pnml())
                    elif res["status"] == "error" :
                        print("# answer: %s: %s" % (res["error"], res.data))
                    else :
                        print("# answer: %s" % res["status"])
                self.sendto(res.to_pnml(), address)
    class TCPServer (UDPServer) :
        def __init__ (self, port, size=2**20, verbose=0) :
            self._size = size
            self._verbose = verbose
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.bind(("", port))
            self._sock.listen(1)
            self._env = imp.new_module("snk")
            self._env.__dict__.update(__builtins__)
            self._env.__dict__.update(operator.__dict__)
            self._env.__dict__.update(module.__dict__)
            self._connection = {}
        def recvfrom (self) :
            connection, address = self._sock.accept()
            self._connection[address] = connection
            parts = []
            while True :
                parts.append(connection.recv(self._size))
                if len(parts[-1]) < self._size :
                    break
            return "".join(parts), address
        def sendto (self, data, address) :
            self._connection[address].send(data.rstrip() + "\n")
            self._connection[address].close()
            del self._connection[address]
    return Query, UDPServer, TCPServer
