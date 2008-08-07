#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gettext
import os
from tryton.config import TRYTON_ICON, PIXMAPS_DIR, DATA_DIR

_ = gettext.gettext


class Credits(object):

    def __init__(self, parent):
        self.win = gtk.Dialog(_('Credits'), parent,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        self.win.set_icon(TRYTON_ICON)

        self.win.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)

        vbox = gtk.VBox()
        img = gtk.Image()
        img.set_from_file(os.path.join(PIXMAPS_DIR, 'tryton.png'))
        vbox.pack_start(img, False, False)
        self.label = gtk.Label()
        self.label.set_alignment(0.5, 0)
        contributors_file = os.path.join(DATA_DIR, 'contributors.txt')
        contributors = '\n<b>' + _('Contributors:') + '</b>\n\n'
        contributors += file(contributors_file).read()
        self.label.set_text(contributors)
        self.label.set_use_markup(True)
        vbox.pack_start(self.label, True, True)
        self.win.vbox.pack_start(vbox)
        self.win.show_all()

        self.win.run()
        parent.present()
        self.win.destroy()
