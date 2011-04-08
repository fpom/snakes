from snakes.lang.abcd.parser import ast

class NodeCopier (ast.NodeTransformer) :
    def copy (self, node, **replace) :
        args = {}
        for name in node._fields + node._attributes :
            old = getattr(node, name, None)
            if name in replace :
                new = replace[name]
            elif isinstance(old, list):
                new = []
                for val in old :
                    if isinstance(val, ast.AST) :
                        new.append(self.visit(val))
                    else :
                        new.append(val)
            elif isinstance(old, ast.AST):
                new = self.visit(old)
            else :
                new = old
            args[name] = new
        if hasattr(node, "st") :
            args["st"] = node.st
        return node.__class__(**args)
    def generic_visit (self, node) :
        return self.copy(node)

class ArgsBinder (NodeCopier) :
    def __init__ (self, args, buffers, nets, tasks) :
        NodeCopier.__init__(self)
        self.args = args
        self.buffers = buffers
        self.nets = nets
        self.tasks = tasks
    def visit_Name (self, node) :
        if node.id in self.args :
            return self.copy(self.args[node.id])
        else :
            return self.copy(node)
    def visit_Instance (self, node) :
        if node.net in self.nets :
            return self.copy(node, net=self.nets[node.net])
        else :
            return self.copy(node)
    def _visit_access (self, node) :
        if node.buffer in self.buffers :
            return self.copy(node, buffer=self.buffers[node.buffer])
        else :
            return self.copy(node)
    def visit_SimpleAccess (self, node) :
        return self._visit_access(node)
    def visit_FlushAccess (self, node) :
        return self._visit_access(node)
    def visit_SwapAccess (self, node) :
        return self._visit_access(node)
    def _visit_task (self, node) :
        if node.net in self.tasks :
            return self.copy(node, net=self.tasks[node.net])
        else :
            return self.copy(node)
    def visit_Spawn (self, node) :
        return self._visit_task(node)
    def visit_Wait (self, node) :
        return self._visit_task(node)
    def visit_Suspend (self, node) :
        return self._visit_task(node)
    def visit_Resume (self, node) :
        return self._visit_task(node)
    def visit_AbcdNet (self, node) :
        args = self.args.copy()
        buffers = self.buffers.copy()
        nets = self.nets.copy()
        tasks = self.tasks.copy()
        netargs = ([a.arg for a in node.args.args + node.args.kwonlyargs]
                   + [node.args.vararg, node.args.kwarg])
        copy = True
        for a in netargs :
            for d in (args, buffers, nets, tasks) :
                if a in d :
                    del d[a]
                    copy = False
        if copy :
            return self.copy(node)
        else :
            return self.__class__(args, buffers, nets, tasks).visit(node)

if __name__ == "__main__" :
    import doctest
    doctest.testmod()
