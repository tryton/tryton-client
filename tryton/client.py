#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
"""
%prog [options]
"""
import os
import sys
import pygtk
pygtk.require('2.0')
import gtk
gtk.gdk.threads_init()
import logging
from urlparse import urlparse

from tryton import version
from tryton import config
import tryton.common as common
from tryton.config import CONFIG, CURRENT_DIR, PREFIX, PIXMAPS_DIR, \
        TRYTON_ICON, get_config_dir
from tryton import translate
from tryton import gui
from tryton.ipc import Client as IPCClient
import traceback
import time
import signal


class TrytonClient(object):
    "Tryton client"

    def __init__(self):
        CONFIG.parse()
        if CONFIG.arguments:
            url, = CONFIG.arguments
            urlp = urlparse(url)
            if urlp.scheme == 'tryton':
                urlp = urlparse('http' + url[6:])
                hostname, port = (urlp.netloc.split(':', 1)
                        + [CONFIG.defaults['login.port']])[:2]
                database, _ = (urlp.path[1:].split('/', 1) + [None])[:2]
                if IPCClient(hostname, port, database).write(url):
                    sys.exit(0)
                CONFIG['login.server'] = hostname
                CONFIG['login.port'] = port
                CONFIG['login.db'] = database
        logging.basicConfig()
        translate.set_language_direction(CONFIG['client.language_direction'])
        translate.setlang(CONFIG['client.lang'])
        loglevel = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL,
                }
        for logger in CONFIG['logging.logger'].split(','):
            if logger:
                log = logging.getLogger(logger)
                log.setLevel(loglevel[CONFIG['logging.level'].upper()])
        if CONFIG['logging.default']:
            logging.getLogger().setLevel(
                    loglevel[CONFIG['logging.default'].upper()])

        common.ICONFACTORY.load_client_icons()

    def run(self):
        main = gui.Main()

        signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))
        signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
        if hasattr(signal, 'SIGQUIT'):
            signal.signal(signal.SIGQUIT, lambda signum, frame: sys.exit(0))

        def excepthook(exctyp, value, tb):
            import common

            if str(value) == 'NotLogged':
                return

            tb_s = reduce(lambda x, y: x+y,
                    traceback.format_exception(exctyp, value, tb))
            for path in sys.path:
                tb_s = tb_s.replace(path, '')
            common.error(str(value), main.window, tb_s)

        sys.excepthook = excepthook

        if CONFIG['tip.autostart']:
            main.sig_tips()
        main.sig_login()

        #XXX psyco breaks report printing
        #try:
        #    import psyco
        #    psyco.full()
        #except ImportError:
        #    pass

        try:
            gtk.main()
        except KeyboardInterrupt:
            CONFIG.save()
            if hasattr(gtk, 'accel_map_save'):
                gtk.accel_map_save(os.path.join(get_config_dir(), 'accel.map'))

if __name__ == "__main__":
    CLIENT = TrytonClient()
    CLIENT.run()
