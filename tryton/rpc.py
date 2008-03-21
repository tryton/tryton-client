import pysocket
import translate
from config import CONFIG, GLADE, TRYTON_ICON
import gtk
import logging
import common
import socket
from threading import Semaphore
from gtk import glade
import gettext

_SOCK = None
_USER = 0
_USERNAME = ''
_SESSION = ''
_DATABASE = ''
CONTEXT = {}
_VIEW_CACHE = {}
TIMEZONE = 'utc'
SECURE = False
_SEMAPHORE = Semaphore()

def db_list(host, port):
    global _SOCK
    if _SOCK:
        _SOCK.disconnect()
        _SOCK = None
    try:
        _SOCK = pysocket.PySocket()
        _SEMAPHORE.acquire()
        try:
            _SOCK.connect(host, port)
            _SOCK.send(('db', 'list'))
            res = _SOCK.receive()
        finally:
            _SEMAPHORE.release()
        return res
    except:
        return None

def db_exec(host, port, method, *args):
    global _SOCK
    if _SOCK:
        _SOCK.disconnect()
        _SOCK = None
    _SOCK= pysocket.PySocket()
    _SEMAPHORE.acquire()
    try:
        _SOCK.connect(host, port)
        _SOCK.send(('db', method) + args)
        res = _SOCK.receive()
    finally:
        _SEMAPHORE.release()
    return res

def login(username, password, host, port, database):
    global _SOCK, _USER, _USERNAME, _SESSION, _DATABASE, _VIEW_CACHE, SECURE
    if _SOCK:
        _SOCK.disconnect()
        _SOCK = None
    _VIEW_CACHE = {}
    SECURE = False
    try:
        _SOCK = pysocket.PySocket()
        _SEMAPHORE.acquire()
        try:
            _SOCK.connect(host, port)
            _SOCK.send(('common', 'login', database, username, password))
            res = _SOCK.receive()
        finally:
            _SEMAPHORE.release()
    except socket.error:
        _USER = 0
        _SESSION = ''
        return -1
    if not res:
        _USER = 0
        _SESSION = ''
        return -2
    _USER = res[0]
    _USERNAME = username
    _SESSION = res[1]
    _DATABASE = database
    SECURE = _SOCK.ssl
    context_reload()
    return 1

def logout():
    global _SOCK, _USER, _USERNAME, _SESSION, _DATABASE, _VIEW_CACHE
    if _SOCK:
        _SOCK.disconnect()
        _SOCK = None
    _USER = 0
    _USERNAME = ''
    _SESSION = ''
    _DATABASE = ''
    _VIEW_CACHE = {}

def context_reload():
    global CONTEXT, TIMEZONE
    CONTEXT = {}
    user = RPCProxy('res.user')
    lang = RPCProxy('ir.lang')
    try:
        context = user.get_preferences(True, {})
    except:
        return
    for i in context:
        value = context[i]
        if value:
            CONTEXT[i] = value
        if i == 'language_direction':
            if value == 'rtl':
                gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)
            else:
                gtk.widget_set_default_direction(gtk.TEXT_DIR_LTR)
        if i == 'timezone':
            TIMEZONE = execute('common', 'timezone_get')

def execute(obj, method, *args):
    global _SOCK, _DATABASE, _USER, _SESSION
    if not _SOCK:
        raise Exception('Not logged!')
    logging.getLogger('rpc.request').info(str((obj, method, args)))
    key = False
    if len(args) >= 7 and args[3] == 'fields_view_get':
        key = str(args)
        if key in _VIEW_CACHE and _VIEW_CACHE[key][0]:
            args = args[:]
            args = args + (_VIEW_CACHE[key][0],)
    try:
        _SEMAPHORE.acquire()
        try:
            _SOCK.send((obj, method, _DATABASE, _USER, _SESSION) + args)
            result = _SOCK.receive()
        finally:
            _SEMAPHORE.release()
    except socket.error:
        _SEMAPHORE.acquire()
        try:
            _SOCK.reconnect()
            _SOCK.send((obj, method, _DATABASE, _USER, _SESSION) + args)
            result = _SOCK.receive()
        finally:
            _SEMAPHORE.release()
    if key:
        if result is True and key in _VIEW_CACHE:
            result = _VIEW_CACHE[key][1]
        else:
            _VIEW_CACHE[key] = (result['md5'], result)
    return result

def process_exception(exception, parent, obj='', method='', *args):
    global _USERNAME, _DATABASE, _SOCK
    if str(exception.args[0]) == 'NotLogged':
        while True:
            password = common.ask(_('Password:'), parent, visibility=False)
            if password is None:
                break
            res = login(_USERNAME, password, _SOCK.host, _SOCK.port, _DATABASE)
            if res < 0:
                continue
            if obj and method:
                try:
                    return execute(obj, method, *args)
                except Exception, exception:
                    return process_exception(exception, parent, obj,
                            method, *args)
            return
    type = 'error'
    data = str(exception.args[0])
    description = data
    if len(exception.args) > 1:
        details = str(exception.args[1])
    else:
        details = data
    if hasattr(data, 'split'):
        lines = data.split('\n')
        type = lines[0].split(' -- ')[0]
        description = ''
        if len(lines[0].split(' -- ')) > 1:
            description = lines[0].split(' -- ')[1]
        if len(lines) > 2:
            details = '\n'.join(lines[2:])
    if type == 'warning':
        if description == 'ConcurrencyException' \
                and len(args) > 4:
            if concurrency(args[0], args[2][0], args[4], parent):
                if 'read_delta' in args[4]:
                    del args[4]['read_delta']
                try:
                    return execute(obj, method, *args)
                except Exception, exception:
                    return process_exception(exception, parent, obj,
                            method, *args)
        else:
            common.warning(details, parent, description)
    else:
        common.error(type, description, parent, details)


class RPCProxy(object):

    def __init__(self, name):
        self.name = name
        self.__attrs = {}

    def __getattr__(self, attr):
        if attr not in self.__attrs:
            self.__attrs[attr] = RPCFunction(self.name, attr)
        return self.__attrs[attr]

class RPCFunction(object):

    def __init__(self, name, func_name):
        self.name = name
        self.func = func_name

    def __call__(self, *args):
        return execute('object', 'execute', self.name, self.func, *args)

def concurrency(resource, obj_id, context, parent):
    dia = glade.XML(GLADE, 'dialog_concurrency_exception', gettext.textdomain())
    win = dia.get_widget('dialog_concurrency_exception')

    win.set_transient_for(parent)
    win.set_icon(TRYTON_ICON)

    res = win.run()
    parent.present()
    win.destroy()

    if res == gtk.RESPONSE_OK:
        return True
    if res == gtk.RESPONSE_APPLY:
        from gui.window import Window
        Window.create(False, resource, obj_id, [('id', '=', obj_id)], 'form',
                parent, context, ['form', 'tree'])
    return False
