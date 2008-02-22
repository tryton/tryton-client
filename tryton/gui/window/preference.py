"Preference"
import gettext
import gtk
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
import copy
from tryton.gui.window.view_form.screen import Screen
from tryton.config import TRYTON_ICON

_ = gettext.gettext


class Preference(object):
    "Preference window"

    def __init__(self, user, parent):
        self.win = gtk.Dialog(_('Tryton - Preferences'), parent,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OK, gtk.RESPONSE_OK))

        self.win.set_default_response(gtk.RESPONSE_OK)
        self.win.vbox.pack_start(gtk.Label(_('Edit ressource preferences')),
                expand=False, fill=True)
        self.win.vbox.pack_start(gtk.HSeparator())
        self.win.set_icon(TRYTON_ICON)
        self.win.set_transient_for(parent)
        self.parent = parent
        self.win.show_all()

        user = RPCProxy('res.user')

        res = user.get_preferences_fields_view(rpc.session.context)
        arch = res['arch']
        fields = res['fields']
        self.screen = Screen('res.user', view_type=[], window=self.win)
        self.screen.new(default=False)
        self.screen.add_view_custom(arch, fields, display=True)

        preferences = user.get_preferences(False, rpc.session.context)
        self.screen.current_model.set(preferences)

        width, height = self.screen.screen_container.size_get()
        parent_width, parent_height = parent.get_size()
        self.screen.widget.set_size_request(min(parent_width - 20, width + 20),
                min(parent_height - 60, height + 25))
        self.screen.widget.show()
        self.win.vbox.pack_start(self.screen.widget)
        self.win.set_title(_('Preference'))
        self.win.show()

    def run(self):
        "Run the window"
        res = False
        while True:
            if self.win.run() == gtk.RESPONSE_OK:
                if self.screen.current_model.validate():
                    val = copy.copy(self.screen.get())
                    user = RPCProxy('res.user')
                    user.set_preferences(val, rpc.session.context)
                    res = True
                    break
            else:
                break
        self.parent.present()
        self.win.destroy()
        return res
