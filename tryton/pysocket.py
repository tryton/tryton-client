#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import socket
# can't use/fall-back pickle due to different interface :-(
import cPickle
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

DNS_CACHE = {}

_ALLOWED_MODULES = {'datetime': ['datetime', 'date'], 'decimal': ['Decimal']}

def checkfunction(module, klass):
    if module in _ALLOWED_MODULES and klass in _ALLOWED_MODULES[module]:
        mod = __import__(module, {}, {}, ['__all__'])
        _class = getattr(mod, klass)
        return _class
    raise ValueError('Not supported: %s/%s' % (module, klass))


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
            host, port = buf.rsplit(':', 1)
        hostname = host
        if host in DNS_CACHE:
            host = DNS_CACHE[host]
        if not self.sock:
            self.sock = None
            if socket.has_ipv6:
                try:
                    socket.getaddrinfo(host, int(port), socket.AF_INET6)
                    self.sock = socket.socket(socket.AF_INET6,
                            socket.SOCK_STREAM)
                except:
                    pass
            if self.sock is None:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(120)
        self.sock.connect((host, int(port)))
        DNS_CACHE[hostname], port = self.sock.getpeername()[:2]
        try:
            sock = None
            if socket.has_ipv6:
                try:
                    socket.getaddrinfo(host, int(port), socket.AF_INET6)
                    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                except:
                    pass
            if sock is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(120)
            sock.connect((host, int(port)))
            ssl_sock = socket.ssl(sock)
            self.ssl = True
        except:
            pass
        if self.ssl:
            self.ssl_sock = socket.ssl(self.sock)
        self.host = host
        self.hostname = hostname
        self.port = port

    def disconnect(self):
        try:
            if self.ssl:
                try:
                    if hasattr(socket, 'SHUT_RDWR'):
                        self.ssl_sock.sock_shutdown(socket.SHUT_RDWR)
                    else:
                        self.ssl_sock.sock_shutdown(2)
                except:
                    pass
                self.ssl_sock.close()
            else:
                try:
                    if hasattr(socket, 'SHUT_RDWR'):
                        self.sock.shutdown(socket.SHUT_RDWR)
                    else:
                        self.sock.shutdown(2)
                except:
                    pass
                self.sock.close()
        except:
            pass

    def reconnect(self):
        if self.host and self.port:
            self.disconnect()
            self.sock = None
            if socket.has_ipv6:
                try:
                    socket.getaddrinfo(self.host, int(self.port),
                            socket.AF_INET6)
                    self.sock = socket.socket(socket.AF_INET6,
                            socket.SOCK_STREAM)
                except:
                    pass
            if self.sock is None:
                self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.sock.settimeout(120)
            self.sock.connect((self.host, int(self.port)))
            if self.ssl:
                self.ssl_sock = socket.ssl(self.sock)

    def send(self, msg, exception=False, traceback=None):
        msg = cPickle.dumps([msg, traceback], protocol=2)
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
        msgio = StringIO.StringIO(msg)
        unpickler = cPickle.Unpickler(msgio)
        # cPickle mechanism to import instances (pickle differs here)
        unpickler.find_global = checkfunction
        res = unpickler.load()
        if exception:
            raise Exception(*(list(res[0]) + [res[1]]))
        else:
            return res[0]
