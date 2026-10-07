# SPDX-License-Identifier: GPL-2.0-or-later
"""In-process extension CLI runner for an experimental iPad Blender bundle.

File/network work runs in a worker. bpy is never imported here. No process is
spawned and no global stdout, argv or signal handlers are replaced.
"""
import importlib.util
from pathlib import Path
import queue
import sys
import threading
import time
import uuid


def command_output(args, use_idle, *, cli_path):
    messages = queue.Queue()
    cancelled = threading.Event()
    finished = threading.Event()
    done_sent = threading.Event()

    def emit(kind, data):
        messages.put((kind, data))
        if kind == 'DONE': done_sent.set()
        return cancelled.is_set()

    def worker():
        name = '_ipad_blender_ext_' + uuid.uuid4().hex
        try:
            spec = importlib.util.spec_from_file_location(name, str(cli_path))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            # Original standalone CLI alters sys.unraisablehook in notification
            # mode; that must not affect the host Blender process.
            module.force_exit_ok_enable = lambda: None
            module.msglog_from_args = lambda namespace: module.MessageLogger(emit)
            parser = module.argparse_create(prog='blender_ext_ipad')
            namespace = parser.parse_args([*args, '--output-type=JSON_0'])
            if not hasattr(namespace, 'func'):
                raise ValueError('Extension command missing')
            result = namespace.func(namespace)
            if result is False and not done_sent.is_set():
                emit('ERROR', 'Extension command failed; see preceding messages')
        except SystemExit as exc:
            emit('ERROR', 'Invalid extension command arguments: ' + str(exc.code))
        except Exception as exc:
            emit('ERROR', str(exc))
        finally:
            if not done_sent.is_set(): emit('DONE', '')
            sys.modules.pop(name, None)
            finished.set()

    thread = threading.Thread(target=worker, name='iPad Extension IO', daemon=True)
    thread.start()
    try:
        while True:
            batch = []
            # Bound one UI tick even during a busy progress stream.
            for _ in range(128):
                try: batch.append(messages.get_nowait())
                except queue.Empty: break
            if batch:
                if (yield batch): cancelled.set()
            elif finished.is_set():
                return
            else:
                if (yield []): cancelled.set()
                if use_idle: time.sleep(0.01)
    finally:
        # Cooperative cancellation. Do not block Blender by joining a network
        # worker; HTTP reads stop at the CLI's configured timeout.
        cancelled.set()
