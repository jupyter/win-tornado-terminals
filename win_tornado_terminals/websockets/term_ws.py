# -*- coding: iso-8859-15 -*-

"""Websocket handling class."""

import json
import logging

import tornado.escape
import tornado.websocket


class MainSocket(tornado.websocket.WebSocketHandler):
    """Handles long polling communication between xterm.js and server."""

    def initialize(self, term_manager=None, close_future=None, logger=None):
        """Base class initialization."""
        self.term_manager = term_manager or self.application.term_manager
        self.close_future = close_future
        self.logger = logger or logging.getLogger(__name__)

    def open(self, pid):
        """Open a Websocket associated to a console."""
        self.logger.debug("WebSocket opened: {0}".format(pid))
        self.pid = pid
        self.term_manager.start_term(pid, self)
        self.logger.debug("TTY On!")
        self.send_json_message(["setup", {}])

    def on_close(self):
        """Close console communication."""
        self.logger.debug("WebSocket closed: {0}".format(self.pid))
        if self.close_future is not None:
            self.logger.debug('TTY Off!')
            self.term_manager.terminate(self.pid)
            self.close_future.set_result(("Done!"))

    def notify(self, message):
        """Write stdout/err to client."""
        message = json.dumps(['stdout', message])
        self.write_message(message)

    def send_json_message(self, content):
        json_msg = json.dumps(content)
        self.write_message(json_msg)

    def on_message(self, message):
        """Handle incoming websocket message

        We send JSON arrays, where the first element is a string indicating
        what kind of message this is. Data associated with the message follows.
        """
        command = json.loads(message)
        msg_type = command[0]

        if msg_type == "stdin":
            self.term_manager.execute(self.pid, command[1])
        elif msg_type == "set_size":
            rows = command[1]
            cols = command[2]
            self.term_manager.resize_term(self.pid, rows, cols)

    def on_pty_died(self):
        """Terminal closed: tell the frontend, and close the socket.
        """
        self.send_json_message(['disconnect', 1])
        self.close()
