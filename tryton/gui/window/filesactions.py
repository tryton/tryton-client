"Files actions"
import gtk
import gettext
from tryton.config import TRYTON_ICON, CONFIG

_ = gettext.gettext


class FilesActions(object):
    "Files actions window"

    def __init__(self, parent):
        self.win = gtk.Dialog(_('Tryton - Files Actions'), parent,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.parent = parent
        self.win.set_default_response(gtk.RESPONSE_OK)
        self.win.set_icon(TRYTON_ICON)
        self.win.set_transient_for(parent)
        self.win.vbox.pack_start(gtk.Label(
            _('Edit files actions')), expand=False, fill=True)
        self.win.vbox.pack_start(gtk.HSeparator())
        self.entries = {}
        table = gtk.Table(len(CONFIG['client.actions']), 2)
        table.set_col_spacings(3)
        table.set_row_spacings(3)
        table.set_border_width(1)
        i = 0
        for extension in CONFIG['client.actions']:
            table.attach(gtk.Label(_('%s file: ') % extension.upper()),
                    0, 1, i, i + 1, yoptions = False, xoptions=gtk.FILL)
            self.entries[extension] = gtk.Entry()
            self.entries[extension].set_property(
                    'activates_default', True)
            self.entries[extension].set_text(
                    CONFIG['client.actions'][extension])
            table.attach(self.entries[extension], 1, 2, i, i + 1,
                yoptions = False, xoptions=gtk.FILL)
            i += 1
        self.win.vbox.pack_start(table, expand=True, fill=True)
        self.win.show_all()

    def run(self):
        "Run the window"
        res = self.win.run()
        if res == gtk.RESPONSE_OK:
            for extension in self.entries:
                CONFIG['client.actions'][extension] = \
                        self.entries[extension].get_text()
            CONFIG.save()
        self.parent.present()
        self.win.destroy()
        return res
