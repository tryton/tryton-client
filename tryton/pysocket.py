import socket
import cPickle
import cStringIO

DNS_CACHE = {}

_ALLOWED_MODULES = {'datetime': ['datetime', 'date'], 'decimal': ['Decimal']}

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
        self.sock = sock
        self.host = None
        self.port = None
        self.ssl = False
        self.ssl_sock = None

    def connect(self, host, port=False):
        if not port:
            buf = host.split('//')[1]
            host, port = buf.split(':')
        if host in DNS_CACHE:
            host = DNS_CACHE[host]
        if not self.sock:
            familly = socket.AF_INET
            if socket.has_ipv6:
                try:
                    socket.getaddrinfo(host, int(port), socket.AF_INET6)
                    familly = socket.AF_INET6
                except:
                    pass
            self.sock = socket.socket(familly, socket.SOCK_STREAM)
            self.sock.settimeout(120)
        self.sock.connect((host, int(port)))
        DNS_CACHE[host], port = self.sock.getpeername()[:2]
        try:
            familly = socket.AF_INET
            if socket.has_ipv6:
                try:
                    socket.getaddrinfo(host, int(port), socket.AF_INET6)
                    familly = socket.AF_INET6
                except:
                    pass
            sock = socket.socket(familly, socket.SOCK_STREAM)
            sock.settimeout(120)
            sock.connect((host, int(port)))
            ssl_sock = socket.ssl(sock)
            self.ssl = True
        except:
            pass
        if self.ssl:
            self.ssl_sock = socket.ssl(self.sock)
        self.host = host
        self.port = port

    def disconnect(self):
        try:
            if self.secure:
                if hasattr(socket, 'SHUT_RDWR'):
                    self.socket.sock_shutdown(socket.SHUT_RDWR)
                else:
                    self.socket.sock_shutdown(2)
            else:
                if hasattr(socket, 'SHUT_RDWR'):
                    self.socket.shutdown(socket.SHUT_RDWR)
                else:
                    self.socket.shutdown(2)
            self.sock.close()
        except:
            pass

    def reconnect(self):
        if self.host and self.port:
            self.disconnect()
            familly = socket.AF_INET
            if socket.has_ipv6:
                try:
                    socket.getaddrinfo(self.host, int(self.port),
                            socket.AF_INET6)
                    familly = socket.AF_INET6
                except:
                    pass
            self.sock = socket.socket(
                familly, socket.SOCK_STREAM)
            self.sock.settimeout(120)
            self.sock.connect((self.host, int(self.port)))
            if self.ssl:
                self.ssl_sock = socket.ssl(self.sock)

    def send(self, msg, exception=False, traceback=None):
        msg = cPickle.dumps([msg, traceback])
        size = len(msg)
        if self.ssl:
            self.ssl_sock.write('%8d' % size)
        else:
            self.sock.send('%8d' % size)
        if self.ssl:
            self.ssl_sock.write(exception and "1" or "0")
        else:
            self.sock.send(exception and "1" or "0")
        totalsent = 0
        while totalsent < size:
            if self.ssl:
                sent = self.ssl_sock.write(msg[totalsent:])
            else:
                sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError, "socket connection broken"
            totalsent = totalsent + sent

    def receive(self):
        buf = ''
        while len(buf) < 8:
            if self.ssl:
                chunk = self.ssl_sock.read(8 - len(buf))
            else:
                chunk = self.sock.recv(8 - len(buf))
            if chunk == '':
                raise RuntimeError, "socket connection broken"
            buf += chunk
        size = int(buf)
        if self.ssl:
            buf = self.ssl_sock.read(1)
        else:
            buf = self.sock.recv(1)
        if buf != "0":
            exception = buf
        else:
            exception = False
        msg = ''
        while len(msg) < size:
            if self.ssl:
                chunk = self.ssl_sock.read(size-len(msg))
            else:
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
