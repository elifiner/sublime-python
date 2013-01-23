import os
import sys
import ast
import shelve

APPDIR = os.path.abspath(os.path.split(__file__)[0])

class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.symbols = []
        self._parents = []

    def add_symbol(self, name, type, line):
        self.symbols.append((name, type, self.filename, line))

    def visit_FunctionDef(self, node):
        if not (node.name.startswith('__') and node.name.endswith('__')):
            if isinstance(self._parents[-1], ast.ClassDef):
                self.add_symbol(node.name, 'method', node.lineno)
            else:
                self.add_symbol(node.name, 'function', node.lineno)
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.add_symbol(node.name, 'class', node.lineno)
        return self.generic_visit(node)

    def visit_Assign(self, node):
        parent = self._parents[-1]

        # globals variables
        if isinstance(parent, ast.Module):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.add_symbol(target.id, 'global-attr', node.lineno)

        # instance variables
        if isinstance(parent, ast.FunctionDef) and parent.name == '__init__':
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    self.add_symbol(target.attr, 'object-attr', node.lineno)
                    
        # class variables
        elif isinstance(parent, ast.ClassDef):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    self.add_symbol(target.attr, 'class-attr', node.lineno)

    def generic_visit(self, node):
        self._parents.append(node)
        super(SymbolVisitor, self).generic_visit(node)
        del self._parents[-1]

def parse_symbols(filename):
    try:
        tree = ast.parse(open(filename).read())
    except SyntaxError, e:
        print >>sys.stderr, "error: %s in '%s'" % (str(e), filename)
        return []
    else:
        visitor = SymbolVisitor(filename)
        visitor.visit(tree)
        return visitor.symbols

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
    parser.add_option("-x", "--exclude", metavar="DIR", dest="exclude", action="append", help="exclude files containing DIR in their paths")
    (options, args) = parser.parse_args()

    if not options.dirs and not options.files:
        parser.print_help()
        sys.exit(1)

    cache = shelve.open(os.path.join(APPDIR, '.symbols.cache'))

    # purge removed files from cache
    for path in cache.iterkeys():
        if not os.path.exists(path):
            del cache[path]

    # prepare a filtered list of files to scan
    paths = list(walk(options.dirs or []))
    paths.extend(options.files or [])
    filtered = []
    for path in paths:
        for ex in options.exclude or []:
            if ex in path:
                break
        else:
            if path.endswith('.py'):
                filtered.append(path)

    # scan the files
    percent = 0
    for i, path in enumerate(filtered):
        new_percent = (i+1) * 100 / len(filtered)
        if new_percent > percent:
            percent = new_percent
            print "progress(%d)" % percent

        last_modified = os.path.getmtime(path)
        if path in cache and cache[path]['last_modified'] == last_modified:
            symbols = cache[path]['symbols']
        else:
            symbols = parse_symbols(path)
            cache[path] = {
                'last_modified' : last_modified,
                'symbols' : symbols
            }
        for name, type, filename, line in symbols:
            print "symbol(name='%s', type='%s', filename='%s', line=%d)" % (name, type, filename, line)
