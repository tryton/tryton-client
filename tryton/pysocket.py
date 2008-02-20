import socket
import cPickle
import cStringIO

DNS_CACHE = {}

_ALLOWED_MODULES = {'datetime': ['datetime']}

def checkfunction(module, klass):
    if module in _ALLOWED_MODULES and klass in _ALLOWED_MODULES[module]:
        mod = __import__(module, {}, {}, ['__all__'])
        _class = getattr(mod, klass)
        return _class
    raise ValueError('Not supported: %s/%s' % (module, klass))


class PySocketException(Exception):

    def __init__(self, code, string):
        Exception.__init__(self)
        self.faultCode = code
        self.faultString = string
        self.args = (code, string)

class PySocket:

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.sock.settimeout(120)
        self.host = None
        self.port = None

    def connect(self, host, port=False):
        if not port:
            buf = host.split('//')[1]
            host, port = buf.split(':')
        if host in DNS_CACHE:
            host = DNS_CACHE[host]
        self.sock.connect((host, int(port)))
        DNS_CACHE[host], port = self.sock.getpeername()
        self.host = host
        self.port = port

    def disconnect(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self.sock.close()
        except:
            pass

    def reconnect(self):
        if self.host and self.port:
            self.disconnect()
            self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(120)
            self.sock.connect((self.host, int(self.port)))

    def send(self, msg, exception=False, traceback=None):
        msg = cPickle.dumps([msg, traceback])
        size = len(msg)
        self.sock.send('%8d' % size)
        self.sock.send(exception and "1" or "0")
        totalsent = 0
        while totalsent < size:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError, "socket connection broken"
            totalsent = totalsent + sent

    def receive(self):
        buf = ''
        while len(buf) < 8:
            chunk = self.sock.recv(8 - len(buf))
            if chunk == '':
                raise RuntimeError, "socket connection broken"
            buf += chunk
        size = int(buf)
        buf = self.sock.recv(1)
        if buf != "0":
            exception = buf
        else:
            exception = False
        msg = ''
        while len(msg) < size:
            chunk = self.sock.recv(size-len(msg))
            if chunk == '':
                raise RuntimeError, "socket connection broken"
            msg = msg + chunk
        msgio = cStringIO.StringIO(msg)
        unpickler = cPickle.Unpickler(msgio)
        unpickler.find_global = checkfunction
        res = unpickler.load()
        if exception:
            raise PySocketException(str(res[0]), str(res[1]))
        else:
            return res[0]
