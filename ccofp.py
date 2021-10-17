__all__ = ['CCOFP']
import os
import sys
import tokenize
import ast
import threading
from collections import defaultdict

class ASTVisitor():
    def __init__(self):
        self.node = None
        self._cache = {}

    def dispatch(self, node, *args):
        self.node = node
        klass = node.__class__
        meth = self._cache.get(klass)
        if meth is None:
            className = klass.__name__
            meth = getattr(self.visitor, 'visit' + className, self.default)
            self._cache[klass] = meth
        return meth(node, *args)

    def preorder(self, tree, visitor, *args):
        self.visitor = visitor
        visitor.visit = self.dispatch
        self.dispatch(tree, *args)


class PathNode(object):
    def __init__(self, name, look='circle'):
        self.name = name
        self.look = look

    def dot_id(self):
        return id(self)


class PathGraph(object):
    def __init__(self, name, entity, lineno, column=0):
        self.name = name
        self.entity = entity
        self.lineno = lineno
        self.column = column
        self.nodes = defaultdict(list)

    def connect(self, n1, n2):
        self.nodes[n1].append(n2)
        self.nodes[n2] = []

    def complexity(self):
        num_edges = sum([len(n) for n in self.nodes.values()])
        num_nodes = len(self.nodes)
        return num_edges - num_nodes + 2


class PathGraphingAstVisitor(ASTVisitor):

    def __init__(self):
        super().__init__()
        self.classname = ''
        self.graphs = {}
        self.reset()

    def reset(self):
        self.graph = None
        self.tail = None

    def dispatch_list(self, node_list):
        for node in node_list:
            self.dispatch(node)

    def visitFunctionDef(self, node):

        if self.classname:
            entity = f'{self.classname}, {node.name}'

        else:
            entity = node.name

        name = f'{node.lineno}, {node.col_offset}, {entity}'

        if not self.graph:
            # closure
            pathnode = self.appendPathNode(name)
            self.tail = pathnode
            self.dispatch_list(node.body)
            bottom = PathNode('', look='point')
            self.graph.connect(self.tail, bottom)
            self.graph.connect(pathnode, bottom)
            self.tail = bottom
        else:
            self.graph = PathGraph(name, entity, node.lineno, node.col_offset)
            pathnode = PathNode(name)
            self.tail = pathnode
            self.dispatch_list(node.body)
            self.graphs[f'{self.classname}-{node.name}'] = self.graph
            self.reset()

    visitAsyncFunctionDef = visitFunctionDef

    def visitClassDef(self, node):
        old_classname = self.classname
        self.classname += node.name + '.'
        self.dispatch_list(node.body)
        self.classname = old_classname

    def appendPathNode(self, name):
        if not self.tail:
            return
        pathnode = PathNode(name)
        self.graph.connect(self.tail, pathnode)
        self.tail = pathnode
        return pathnode

    def visitSimpleStatement(self, node):
        if node.lineno is None:
            lineno = 0
        else:
            lineno = node.lineno
        name = f'ss {node.lineno}'
        self.appendPathNode(name)

    def default(self, node, *args):
        if isinstance(node, ast.stmt):
            self.visitSimpleStatement(node)
        else:
            super(PathGraphingAstVisitor, self).default(node, *args)

    def visitLoop(self, node):
        name = f'loop {node.lineno}'
        self._subgraph(node, name)

    visitAsyncFor = visitFor = visitWhile = visitLoop

    def visitIf(self, node):
        name = f'if {node.lineno}'
        self._subgraph(node, name)

    def _subgraph(self, node, name, extra_blocks=()):
        if self.graph is None:
            # global loop
            self.graph = PathGraph(name, name, node.lineno, node.col_offset)
            pathnode = PathNode(name)
            self._subgraph_parse(node, pathnode, extra_blocks)
            self.graphs[f'{self.classname}-{name}'] = self.graph
            self.reset()
        else:
            pathnode = self.appendPathNode(name)
            self._subgraph_parse(node, pathnode, extra_blocks)

    def _subgraph_parse(self, node, pathnode, extra_blocks):
        loose_ends = []
        self.tail = pathnode
        self.dispatch_list(node.body)
        loose_ends.append(self.tail)
        for extra in extra_blocks:
            self.tail = pathnode
            self.dispatch_list(extra.body)
            loose_ends.append(self.tail)
        if node.orelse:
            self.tail = pathnode
            self.dispatch_list(node.orels)
            loose_ends.append(self.tail)
        else:
            loose_ends.append(pathnode)
        if pathnode:
            bottom = PathNode('', look='point')
            for le in loose_ends:
                self.graph.connect(le, bottom)
            self.tail = bottom


class CCOFP():
    def __init__(self, file_path):
        assert file_path and type(file_path, str)
        self.file_path = file_path
    max_complexity = -1

    def __init__(self, filename):
        self.file_name = filename

    def run(self):
        if self.max_complexity < 0:
            return
        visitor = PathGraphingAstVisitor()
        visitor.preorder(self.tree, visitor)
        for graph in visitor.graphs.values():
            if graph.complexity() > self.max_complexity:
                text = self._error_tmpl % (graph.entity, graph.complexity())
                yield graph.lineno, graph.column, text, type(self)


class MyThread(threading.Thread):  # TODO: user thread to calculate cc for directory

    def __init__(self, func, args=()):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args
        self.result = None

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception as e:
            return None


def get_code_complexity(code, threshold=7, filename=''):
    assert filename
    try:
        tree = compile(code, filename, 'exec', ast.PyCF_ONLY_AST)
    except SyntaxError:
        e = sys.exc_info()[1]
        print(f'Unable to parse {filename}, becoz {e}')
        return 0

    complx = []
    CCOFP.max_complexity = threshold
    for lineno, offset, text, check in CCOFP(tree, filename).run():
        complx.append(f'{filename}:{lineno}:1:{text}')

    if len(complx) == 0:
        return 0
    print('\n'.join(complx))
    return len(complx)


def _read(filename):
    if (2, 5) < sys.version_info < (3, 0):
        with open(filename, 'rU') as f:
            return f.read()
    elif (3, 0) <= sys.version_info < (4, 0):
        """Read the source code."""
        try:
            with open(filename, 'rb') as f:
                (encoding, _) = tokenize.detect_encoding(f.readline)
        except (LookupError, SyntaxError, UnicodeError):
            # Fall back if file encoding is improperly declared
            with open(filename, encoding='latin-1') as f:
                return f.read()
        with open(filename, 'r', encoding=encoding) as f:
            return f.read()


def get_module_complexity(module_path, threshold=7):
    assert os.path.isdir(module_path)

    t = []
    result = {}
    for dir,folder,file in os.walk(module_path):
        code = _read(file)
        th = MyThread(get_code_complexity, args=(code, threshold, file))
        t.append(th)
        th.start()
        th.join()
        result[file] = th.get_result()
    return result





