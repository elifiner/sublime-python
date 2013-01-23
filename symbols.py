import os
import sys
import ast

class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self._parents = []

    def print_symbol(self, name, type, line):
        print "symbol(name='%s', type='%s', filename='%s', line=%d)" % (name, type, self.filename, line)

    def visit_FunctionDef(self, node):
        if not (node.name.startswith('__') and node.name.endswith('__')):
            if isinstance(self._parents[-1], ast.ClassDef):
                self.print_symbol(node.name, 'method', node.lineno)
            else:
                self.print_symbol(node.name, 'function', node.lineno)
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.print_symbol(node.name, 'class', node.lineno)
        return self.generic_visit(node)

    def visit_Assign(self, node):
        parent = self._parents[-1]

        # globals variables
        if isinstance(parent, ast.Module):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.print_symbol(target.id, 'global-attr', node.lineno)

        # instance variables
        if isinstance(parent, ast.FunctionDef) and parent.name == '__init__':
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    self.print_symbol(target.attr, 'object-attr', node.lineno)
                    
        # class variables
        elif isinstance(parent, ast.ClassDef):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    self.print_symbol(target.attr, 'class-attr', node.lineno)

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

def walk(dirs):
    for dir in dirs:
        for root, dirs, files in os.walk(dir):
            for file in files:
                yield os.path.join(root, file)

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
    paths = [p for p in paths if p.endswith('.py') and "/.git/" not in p]

    percent = 0
    for i, path in enumerate(paths):
        new_percent = (i+1) * 100 / len(paths)
        if new_percent > percent:
            percent = new_percent
            print "progress(%d)" % percent

        print_symbols(path)
