# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be)
# Copyright (c) 2007 Cedric Krier.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contact a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

"""
%prog [options]
"""
import os
import sys

import pygtk
pygtk.require('2.0')
import gtk
import logging

import version
import config
from config import CONFIG, CURRENT_DIR, PREFIX, PIXMAPS_DIR, TRYTON_ICON
import translate
from gui import Main


class TrytonClient(object):
    "Tryton client"

    def __init__(self):
        logging.basicConfig()
        translate.setlang()
        translate.setlang(CONFIG['client.lang'])

        for logger in CONFIG['logging.logger'].split(','):
            if logger:
                loglevel = {
                        'DEBUG': logging.DEBUG,
                        'INFO': logging.INFO,
                        'WARNING': logging.WARNING,
                        'ERROR': logging.ERROR,
                        'CRITICAL': logging.CRITICAL,
                        }
                log = logging.getLogger(logger)
                log.setLevel(loglevel[CONFIG['logging.level'].upper()])
        if CONFIG['logging.verbose']:
            logging.getLogger().setLevel(logging.INFO)
        else:
            logging.getLogger().setLevel(logging.ERROR)

        factory = gtk.IconFactory()
        factory.add_default()

        for fname in os.listdir(PIXMAPS_DIR):
            name = os.path.splitext(fname)[0]
            if not name.startswith('tryton-'):
                continue
            if not os.path.isfile(os.path.join(PIXMAPS_DIR, fname)):
                continue
            try:
                pixbuf = gtk.gdk.pixbuf_new_from_file(
                        os.path.join(PIXMAPS_DIR, fname))
            except:
                continue
            icon_set = gtk.IconSet(pixbuf)
            factory.add(name, icon_set)
            #XXX override gtk icon until we remove glade
            factory.add('gtk-' + name[7:], icon_set)

    def run(self):
        main = Main()
        if CONFIG['tip.autostart']:
            main.sig_tips()
        main.sig_login()
        gtk.main()

if __name__ == "__main__":
    CLIENT = TrytonClient()
    CLIENT.run()
