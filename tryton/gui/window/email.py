#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

import gtk
import gettext
from tryton.config import TRYTON_ICON, CONFIG

_ = gettext.gettext


class Email(object):

    def __init__(self, parent):
        self.win = gtk.Dialog(_('Email'), parent,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.parent = parent
        self.win.set_default_response(gtk.RESPONSE_OK)
        self.win.set_icon(TRYTON_ICON)
        self.win.set_has_separator(True)
        self.win.set_transient_for(parent)
        self.win.vbox.set_spacing(3)
        self.win.vbox.pack_start(gtk.Label(
            _('Sending reports as email attachments')), expand=False, fill=True)
        self.win.vbox.pack_start(gtk.HSeparator())
        hbox = gtk.HBox(spacing=3)
        hbox.pack_start(gtk.Label(_('Email program:')), expand=True,
            fill=True)
        self.entry = gtk.Entry()
        self.entry.set_property('activates_default', True)
        self.entry.set_width_chars(50)
        self.entry.set_text(CONFIG['client.email'])
        hbox.pack_start(self.entry, expand=True, fill=True)
        self.win.vbox.pack_start(hbox, expand=True, fill=True)

        label = gtk.Label(_('Available Values:'))
        label.set_alignment(0.0, 0.5)
        label.set_padding(0, 10)
        self.win.vbox.pack_start(label, expand=False, fill=True)
        label = gtk.Label('${to}, ${cc}, ${subject}, ${body}, ${attachment}')
        self.win.vbox.pack_start(label, expand=False, fill=True)

        self.win.show_all()

    def run(self):
        "Run the window"
        res = self.win.run()
        if res == gtk.RESPONSE_OK:
            CONFIG['client.email'] = self.entry.get_text()
            CONFIG.save()
        self.parent.present()
        self.win.destroy()
        return res
