import os
import sys
import ast

def walk(dirs):
    for dir in dirs:
        for root, dirs, files in os.walk(dir):
            for file in files:
                yield os.path.join(root, file)

class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self._parents = []

    def print_symbol(self, name, line):
        print "symbol(symbol='%s', filename='%s', line=%d)" % (name, self.filename, line)

    def visit_FunctionDef(self, node):
        if not (node.name.startswith('__') and node.name.endswith('__')):
            self.print_symbol(node.name, node.lineno)
        super(SymbolVisitor, self).generic_visit(node)

    def visit_ClassDef(self, node):
        self.print_symbol(node.name, node.lineno)
        super(SymbolVisitor, self).generic_visit(node)

    def visit_Assign(self, node):
        parent = self._parents[-1]

        # instance variables
        if isinstance(parent, ast.FunctionDef) and parent.name == '__init__':
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    self.print_symbol(node.name, node.lineno)
                    
        # class variables
        elif isinstance(parent, ast.ClassDef):
            for target in node.targets:
                self.print_symbol(node.id, node.lineno)

    def generic_visit(self, node):
        self._parents.append(node)
        super(SymbolVisitor, self).generic_visit(node)
        del self._parents[-1]

def print_symbols(filename):
    try:
        tree = ast.parse(open(filename).read())
    except SyntaxError, e:
        print >>sys.stderr, "error: %s in '%s'" % (str(e), filename)
    else:
        SymbolVisitor(filename).visit(tree)

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser(usage="%prog [options]", description="Prints symbols found in Python files")
    parser.add_option("-f", "--file", metavar="FILE", dest="files", action="append", help="parse FILE")
    parser.add_option("-d", "--dir", metavar="DIR", dest="dirs", action="append", help="recursively read files from DIR")
    (options, args) = parser.parse_args()

    if not options.dirs and not options.files:
        parser.print_help()
        sys.exit(1)

    paths = list(walk(options.dirs or []))
    paths.extend(options.files or [])

    percent = 0
    for i, path in enumerate(paths):
        new_percent = (i+1) * 100 / len(paths)
        if new_percent > percent:
            percent = new_percent
            print "progress(%d)" % percent

        if path.endswith(".py") and "/.git/" not in path:
            print_symbols(path)
