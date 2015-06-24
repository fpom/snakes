import sys, os.path, httplib, cgi, urlparse, functools, mimetypes
import os, traceback, random, base64, inspect
import BaseHTTPServer
from snakes.utils.simul import logger as log
from snakes.utils.simul.html import json, utf8

##
##
##

class HTTPError (Exception) :
    def __init__ (self, code, reason=None, debug=None, headers={}) :
        self.answer = httplib.responses[code]
        if reason is None :
            message = self.answer
        else :
            message = "%s (%s)" % (self.answer, reason)
        Exception.__init__(self, message)
        self.code = code
        self.reason = reason
        self.debug = debug
        self.headers = headers

##
##
##

encoders = {"application/json" : json,
            "application/binary" : str,
            "text/plain" : utf8,
            "text/html" : utf8,
            }

def http (content_type=None, **types) :
    def decorator (method) :
        @functools.wraps(method)
        def wrapper (*larg, **karg) :
            try :
                args = inspect.getcallargs(method, *larg, **karg)
                for a, t in types.items() :
                    if a in args :
                        args[a] = t(args[a])
            except :
                raise HTTPError(httplib.BAD_REQUEST, "invalid arguments")
            try :
                if content_type is None :
                    return method(**args)
                else :
                    encode = encoders.get(content_type, str)
                    return content_type, encode(method(**args))
            except HTTPError :
                raise
            except :
                raise HTTPError(httplib.INTERNAL_SERVER_ERROR,
                                debug=sys.exc_info())
        return wrapper
    return decorator

class Node (object) :
    def __init__ (self, **children) :
        for child, node in children.items() :
            setattr(self, child, node)
    def __getitem__ (self, path) :
        path = path.strip("/")
        if "/" in path :
            head, tail = path.split("/", 1)
            child = getattr(self, head, None)
            if isinstance(child, Node) :
                return child[tail]
            else :
                raise KeyError(tail)
        elif path == "" and hasattr(self, "__call__") :
            return self.__call__
        elif hasattr(self, path) :
            return getattr(self, path)
        else :
            raise KeyError(path)

class DirNode (Node) :
    def __init__ (self, path) :
        self.root = os.path.realpath(path)
    def __getitem__ (self, path) :
        path = os.path.join(self.root, path.lstrip("./"))
        if not os.path.isfile(path) :
            raise HTTPError(httplib.NOT_FOUND)
        ct = mimetypes.guess_type(path)[0] or "application/octet-stream"
        @http(ct)
        def handler () :
            return open(path).read()
        return handler

class ResourceNode (Node) :
    def __init__ (self, data, dirs) :
        self.data = data
        self.dirs = dirs
        self.ct = dict((path, mimetypes.guess_type(path)[0]
                        or "application/octet-stream")
                       for path in self.data)
    def __getitem__ (self, path) :
        if path in self.data :
            @http(self.ct[path])
            def handler () :
                return self.data[path]
            return handler
        else :
            try :
                base, child = path.split("/", 1)
                return self.dirs[base][child]
            except :
                raise HTTPError(httplib.NOT_FOUND)


##
##
##

class HTTPRequestHandler (BaseHTTPServer.BaseHTTPRequestHandler) :
    def do_GET (self) :
        url = self.geturl()
        self.do(url, url.query)
    def do_POST (self) :
        content_len = int(self.headers.getheader('content-length'))
        data = self.rfile.read(content_len)
        self.do(self.geturl(), data)
    def geturl (self) :
        try :
            return urlparse.urlparse(self.path)
        except :
            raise HTTPError(httplib.BAD_REQUEST, "invalid URL")
    def do (self, url, data) :
        try :
            # warning: parse_qs returns lists for values => use parse_qsl
            query = dict(cgi.parse_qsl(data))
            # jQuery may add _ in query for cache control, let's drop it
            query.pop("_", None)
        except :
            raise HTTPError(httplib.BAD_REQUEST, "invalid query")
        try :
            try :
                handler = self.server[url.path]
            except KeyError :
                raise HTTPError(httplib.NOT_FOUND)
            content_type, data = handler(**query)
            self.send_response(httplib.OK)
            self.send_header("Content-type", content_type)
            self.send_header("Content-length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except HTTPError :
            c, v, t = sys.exc_info()
            self.send_response(v.code)
            self.send_header("Content-type", "text/html")
            for hname, hdata in v.headers.iteritems() :
                self.send_header(hname, hdata)
            self.end_headers()
            self.wfile.write("<html><title>%s</title></head>"
                             "<body><p>%s</p></body>" % (v.answer, v.message))
            if v.code == 500 :
                traceback.print_exception(*v.debug)
    def log_request (self, code="-", size="-") :
        code = str(code or "-")
        method, path, version = self.requestline.split()
        if code[0] in "45" :
            logger = log.warn
        else :
            path = path.split("/", 2)[-1]
            if len(path) > 28 :
                path = "..." + path[-28:]
            logger = log.debug
        logger("%s %s => %s" % (method, path, code), "httpd")
    def log_message (self, format, *args) :
        log.info(format % args, "httpd")
    def log_error (self, format, *args) :
        log.error(format % args, "httpd")

class HTTPServer (BaseHTTPServer.HTTPServer):
    def __init__ (self, server_address, root):
        BaseHTTPServer.HTTPServer.__init__(self, server_address,
                                           HTTPRequestHandler)
        self.root = root
        self.key = "".join(base64.b64encode(
            "".join(chr(random.getrandbits(8)) for i in range(15)),
            "-_").split())
    def __getitem__ (self, path) :
        try :
            key, path = path.lstrip("/").split("/", 1)
        except :
            raise HTTPError(httplib.FORBIDDEN)
        if key != self.key :
            raise HTTPError(httplib.FORBIDDEN)
        return self.root[path]

##
##
##

if __name__ == '__main__':
    class HelloNode (Node) :
        @http("text/plain")
        def hello (self, first, last) :
            return "Hello %s %s!" % (first.capitalize(), last.capitalize())
    try :
        httpd = HTTPServer(('', 1234), HelloNode(r=DirNode(".")))
        httpd.serve_forever()
    except KeyboardInterrupt :
        print "\rGoobye"
