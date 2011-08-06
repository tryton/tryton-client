#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import itertools
import logging
import socket
import os
from threading import Semaphore
from functools import partial
from tryton.jsonrpc import ServerProxy, Fault
from tryton.fingerprints import Fingerprints
from tryton.config import get_config_dir
from tryton.ipc import Server as IPCServer
from tryton.exceptions import TrytonServerError

CONNECTION = None
_USER = None
_USERNAME = ''
_SESSION = ''
_HOST = ''
_PORT = None
_DATABASE = ''
CONTEXT = {}
_VIEW_CACHE = {}
TIMEZONE = 'utc'
_SEMAPHORE = Semaphore()
_CA_CERTS = os.path.join(get_config_dir(), 'ca_certs')
if not os.path.isfile(_CA_CERTS):
    _CA_CERTS = None
_FINGERPRINTS = Fingerprints()

ServerProxy = partial(ServerProxy, fingerprints=_FINGERPRINTS, ca_certs=_CA_CERTS)

def db_list(host, port):
    try:
        connection = ServerProxy(host, port)
        logging.getLogger('rpc.request').info('common.db.list(None, None)')
        result = connection.common.db.list(None, None)
        logging.getLogger('rpc.result').debug(repr(result))
        return result
    except Fault, exception:
        if exception.args[0] == 'AccessDenied':
            raise
        else:
            logging.getLogger('rpc.result').debug(repr(None))
            return None

def db_exec(host, port, method, *args):
    connection = ServerProxy(host, port)
    logging.getLogger('rpc.request').info('common.db.%s(None, None, %s)' %
        (method, args))
    result = getattr(connection.common.db, method)(None, None, *args)
    logging.getLogger('rpc.result').debug(repr(result))
    return result

def server_version(host, port):
    try:
        connection = ServerProxy(host, port)
        logging.getLogger('rpc.request').info(
            'common.server.version(None, None)')
        result = connection.common.server.version(None, None)
        logging.getLogger('rpc.result').debug(repr(result))
        return result
    except (Fault, socket.error):
        logging.getLogger('rpc.result').debug(repr(None))
        return None

def login(username, password, host, port, database):
    global CONNECTION, _USER, _USERNAME, _SESSION, _HOST, _PORT, _DATABASE, _VIEW_CACHE
    _VIEW_CACHE = {}
    try:
        _SEMAPHORE.acquire()
        try:
            connection = ServerProxy(host, port, database)
            if str(connection) != str(CONNECTION):
                if CONNECTION:
                    CONNECTION.close()
                CONNECTION = connection
            else:
                connection = CONNECTION
            logging.getLogger('rpc.request').info('common.db.login(%s, %s)' %
                (username, 'x' * 10))
            result = connection.common.db.login(username, password)
            logging.getLogger('rpc.result').debug(repr(result))
        finally:
            _SEMAPHORE.release()
    except socket.error:
        _USER = None
        _SESSION = ''
        return -1
    if not result:
        _USER = None
        _SESSION = ''
        return -2
    _USER = result[0]
    _USERNAME = username
    _SESSION = result[1]
    _HOST = host
    _PORT = port
    _DATABASE = database
    IPCServer(host, port, database).run()
    return 1

def logout():
    global CONNECTION, _USER, _USERNAME, _SESSION, _HOST, _PORT, _DATABASE, _VIEW_CACHE
    if IPCServer.instance:
        IPCServer.instance.stop()
    if CONNECTION is not None:
        _SEMAPHORE.acquire()
        try:
            logging.getLogger('rpc.request').info('common.db.logout(%s, %s)' %
                (_USER, _SESSION))
            CONNECTION.common.db.logout(_USER, _SESSION)
        except (Fault, socket.error):
            pass
        finally:
            _SEMAPHORE.release()
        CONNECTION.close()
        CONNECTION = None
    _USER = None
    _USERNAME = ''
    _SESSION = ''
    _HOST = ''
    _PORT = None
    _DATABASE = ''
    _VIEW_CACHE = {}

def context_reload():
    global CONTEXT, TIMEZONE, _HOST, _PORT
    try:
        context = execute('model', 'res.user', 'get_preferences', True, {})
    except Fault:
        return
    CONTEXT = {}
    for i in context:
        value = context[i]
        CONTEXT[i] = value
        if i == 'timezone':
            try:
                connection = ServerProxy(_HOST, _PORT)
                TIMEZONE = connection.common.server.timezone_get(None, None)
            except Fault:
                pass

def _execute(blocking, *args):
    global CONNECTION, _USER, _SESSION
    if CONNECTION is None:
        raise TrytonServerError('NotLogged')
    key = False
    if args[2] == 'fields_view_get':
        args, ctx = args[:-1], args[-1]
        # Make sure all the arguments are present
        args = tuple(arg if arg is not None else default
            for arg, default in itertools.izip_longest(args,
                ('', '', 'fields_view_get', None, 'form'),
                fillvalue=None))
        key = str(args + (ctx,))
        if key in _VIEW_CACHE and _VIEW_CACHE[key][0]:
            args += (_VIEW_CACHE[key][0], ctx)
        else:
            args += (ctx,)
    res = _SEMAPHORE.acquire(blocking)
    if not res:
        return
    try:
        name = '.'.join(args[:3])
        args = (_USER, _SESSION) + args[3:]
        logging.getLogger('rpc.request').info('%s%s' % (name, args))
        result = getattr(CONNECTION, name)(*args)
    finally:
        _SEMAPHORE.release()
    if key:
        if result is True and key in _VIEW_CACHE:
            result = _VIEW_CACHE[key][1]
        else:
            _VIEW_CACHE[key] = (result['md5'], result)
    logging.getLogger('rpc.result').debug(repr(result))
    return result

def execute(*args):
    return _execute(True, *args)

def execute_nonblocking(*args):
    return _execute(False, *args)
