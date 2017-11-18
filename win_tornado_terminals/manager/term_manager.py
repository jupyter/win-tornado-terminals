# -*- coding: utf-8 -*-

"""Term manager."""

from __future__ import unicode_literals

from concurrent.futures import ThreadPoolExecutor
import itertools
import os

from tornado import gen, ioloop


WINDOWS = os.name == 'nt'

if WINDOWS:
    from winpty.ptyprocess import PtyProcess
else:
    from ptyprocess import PtyProcessUnicode as PtyProcess


class TermReader(object):
    """This class allows to read continously from a terminal stream."""

    def __init__(self, tty, socket):
        """Terminal reader constructor."""
        self.tty = tty
        self.socket = socket
        if WINDOWS:
            self.p_callback = ioloop.PeriodicCallback(self.read_data,
                                                  callback_time=10)
            self.p_callback.start()
        else:
            current = ioloop.IOLoop.current()
            current.add_handler(tty.fd, self.read_data, ioloop.READ)

    @gen.coroutine
    def read_data(self):
        """Consume data from stream."""
        try:
            if self.tty.isalive():
                _in = self.tty.read(1000)
                if _in:
                    self.socket.notify(_in)
            else:
                self.socket.on_pty_died()
        except Exception:
            pass


class TermManager(object):
    """Wrapper around pexpect to execute local commands."""

    def __init__(self, shell_command=None, extra_env=None):
        """Main terminal handler constructor."""
        self.cmd = shell_command
        self.extra_env = extra_env or dict()
        self.sockets = {}
        self.terminals = {}
        self.pool = ThreadPoolExecutor(max_workers=5)

    @gen.coroutine
    def new_named_terminal(self, rows=40, cols=80, cwd=None):
        """Create a new virtual terminal."""
        name = self._next_available_name()
        dimensions = (rows, cols)
        env = os.environ.copy()
        env.update(self.extra_env)
        tty = PtyProcess.spawn(self.cmd, cwd=cwd, env=env,
            dimensions=dimensions)
        self.terminals[name] = {'tty': tty, 'read': None}
        raise gen.Return(name)

    @gen.coroutine
    def start_term(self, name, socket):
        """Start reading a virtual terminal."""
        term = self.terminals[name]
        self.sockets[name] = socket
        term['read'] = TermReader(term['tty'], socket)

    @gen.coroutine
    def terminate(self, name, force=False):
        """Stop and close terminal."""
        tty = self.terminals[name]['tty']
        if not WINDOWS:
            future = self.pool.submit(tty.terminate, force=force)
            yield future
        else:
            tty.close()
        del self.terminals[name]
        del self.sockets[name]

    @gen.coroutine
    def execute(self, name, cmd):
        """Write characters to terminal."""
        tty = self.terminals[name]['tty']
        tty.write(cmd)

    @gen.coroutine
    def resize_term(self, name, rows, cols):
        """Resize terminal."""
        tty = self.terminals[name]['tty']
        tty.setwinsize(rows, cols)

    name_template = "%d"

    def _next_available_name(self):
        for n in itertools.count(start=1):
            name = self.name_template % n
            if name not in self.terminals:
                return name
