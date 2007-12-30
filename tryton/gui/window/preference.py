"Preference"
import gettext
import gtk
import tryton.rpc as rpc
import copy
from tryton.gui.window.view_form.screen import Screen
from tryton.config import TRYTON_ICON

_ = gettext.gettext


class Preference(object):
    "Preference window"

    def __init__(self, model, obj_id, preferences, parent):
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
        self.obj_id = obj_id
        self.model = model

        fields = {}
        arch = '<?xml version="1.0"?><form string="%s">\n' % (_('Preferences'),)
        for pref in preferences:
            arch += '<field name="%s" colspan="4"/>' % (pref[1],)
            fields[pref[1]] = pref[3]
        arch += '</form>'

        self.screen = Screen(model, view_type=[])
        self.screen.new(default=False)
        self.screen.add_view_custom(arch, fields, display=True)

        defaults = rpc.session.rpc_exec_auth('/object', 'execute', 'ir.values',
                'get', 'meta', False, [(self.model, self.obj_id)], False,
                rpc.session.context, True, True, False)
        default2 = {}
        self.defaults = {}
        for default in defaults:
            default2[default[1]] = default[2]
            self.defaults[default[1]] = default[0]
        self.screen.current_model.set(default2)

        width, height = self.screen.screen_container.size_get()
        self.screen.widget.set_size_request(width, height)

        self.win.vbox.pack_start(self.screen.widget)

        self.win.set_title(_('Preference')+' '+model)
        self.win.show_all()

    def run(self):
        "Run the window"
        final = False
        while True:
            res = self.win.run()
            if res == gtk.RESPONSE_OK:
                if self.screen.current_model.validate():
                    final = True

                    val = copy.copy(self.screen.get())

                    for key in val:
                        if val[key]:
                            rpc.session.rpc_exec_auth('/object', 'execute',
                                    'ir.values', 'set', 'meta', key, key,
                                    [(self.model, self.obj_id)], val[key])
                        elif self.defaults.get(key, False):
                            rpc.session.rpc_exec_auth('/common', 'ir_del',
                                    self.defaults[key])
                    break
            else:
                break
        self.parent.present()
        self.win.destroy()
        return final
