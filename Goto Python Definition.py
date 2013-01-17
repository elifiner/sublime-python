import os
import threading

import sublime
import sublime_plugin

"""
TODO

* sometimes hangs
* support multiple windows with different projects
* support switching project in same window
* rescan directory when adding to project (using timeout)
* class variables, globals and instance vars don't work
* add configuration: ignore directories, python location
* find better name for plugin

"""

PYTHON = '/usr/bin/python2.7'
APPDIR = os.path.abspath(os.path.split(__file__)[0])

def error(message):
    sublime.error_message("Goto Python Definition\n\n" + message)

class Symbols(object):
    THREAD_NAME = "c50d5e10-60de-11e2-bcfd-0800200c9a66"
    def __init__(self):
        self._symbols = []
        self._lock = threading.RLock()
        self._thread = None
        self.loaded = False

    def get_symbols(self):
        with self._lock:
            return self._symbols[:]

    def scan_all(self):
        oldThreads = [t for t in threading.enumerate() if t.name == self.THREAD_NAME]
        if not self._thread and oldThreads:
            # old threads running (after plugin reload), try again a bit later
            sublime.set_timeout(self.scan_all, 1000)
            return
        if self._thread and self._thread.is_alive():
            # already running, ignore
            return
        self._thread = threading.Thread(target=self._scan_all_thread, name=self.THREAD_NAME)
        self._thread.start()

    def scan_single(self, filename):
        if not self.loaded:
            return
        symbols = self._load_symbols(['-f', filename])
        print len(symbols), len(self._symbols)
        with self._lock:
            # remove previous symbols for this filename
            self._symbols = [sym for sym in self._symbols if sym[1] != filename]
            self._symbols.extend(symbols)

    def _scan_all_thread(self):
        directories = sublime.active_window().folders()
        symbols = []
        def add_symbol(symbol, filename, line):
            symbols.append((symbol, filename, line))
        def show_progress(percent):
            sublime.status_message("scanning python symbols (%d%% done)..." % percent)
        options = []
        for directory in directories:
            options.append('-d')
            options.append(directory)
        symbols = self._load_symbols(options)
        with self._lock:
            self._symbols = symbols
        self.loaded = True
        self._single_file = None

    def _load_symbols(self, options):
        import subprocess
        symbols = []
        def add_symbol(symbol, filename, line):
            symbols.append((symbol, filename, line))
        def show_progress(percent):
            sublime.status_message("scanning python symbols (%d%% done)..." % percent)
        process = subprocess.Popen([PYTHON, '-u', '%s/symbols.py' % APPDIR] + options, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            line = process.stdout.readline()
            if not line:
                break
            eval(line, dict(
                progress=show_progress,
                symbol=add_symbol
            ))
        # errors = process.stderr.read()
        # if errors:
        #     print errors
        sublime.status_message("")
        return symbols

class GoToPythonDefinitionDialogCommand(sublime_plugin.WindowCommand):
    def run(self):
        if not SYMBOLS.loaded:
            error("Symbols haven't been loaded yet, please wait.")
            return
        symbols = sorted(SYMBOLS.get_symbols())
        symbols = [[sym[0], '%s:%d' % (sym[1], sym[2])]  for sym in symbols]
        if not symbols:
            error("No symbols found.")
        def goto_symbol(index):
            if index == -1:
                return
            self.window.open_file(symbols[index][1]+':0', sublime.ENCODED_POSITION)
        self.window.show_quick_panel(symbols, goto_symbol)

class GoToPythonDefinitionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if not SYMBOLS.loaded:
            error("Symbols haven't been loaded yet, please wait.")
            return
        word = self.view.substr(self.view.word(self.view.sel()[0]))
        if not word:
            return
        symbols = SYMBOLS.get_symbols()
        matches = [[sym[0], '%s:%d' % (sym[1], sym[2])] for sym in symbols if word == sym[0]]
        def goto_match(index):
            if index == -1:
                return
            self.view.window().open_file(matches[index][1]+':0', sublime.ENCODED_POSITION)
        if len(matches) > 1:
            self.view.window().show_quick_panel(matches, goto_match)
        elif matches:
            goto_match(0)
        else:
            error("Can't find definition for '%s'." % word)

class ParsePythonSymbolsCommand(sublime_plugin.WindowCommand):
    def run(self):
        SYMBOLS.scan_all()

class GotoSymbolListener(sublime_plugin.EventListener):
    def on_load(self, view):
        SYMBOLS.scan_single(view.file_name())

    def on_post_save(self, view):
        SYMBOLS.scan_single(view.file_name())

SYMBOLS = Symbols()
SYMBOLS.scan_all()
