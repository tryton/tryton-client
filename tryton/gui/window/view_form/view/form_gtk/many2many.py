import gtk
from tryton.gui.window.view_form.screen import Screen
from interface import WidgetInterface
import tryton.rpc as rpc
from tryton.gui.window.win_search import WinSearch
from tryton.gui.window.view_form.widget_search.form import _LIMIT
import tryton.common as common


class Many2Many(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(Many2Many, self).__init__(window, parent, model, attrs)

        self.widget = gtk.VBox(homogeneous=False, spacing=1)

        hbox = gtk.HBox(homogeneous=False, spacing=3)
        self.wid_text = gtk.Entry()
        self.wid_text.set_property('width_chars', 13)
        self.wid_text.connect('activate', self._sig_activate)
        self.wid_text.connect('button_press_event', self._menu_open)
        hbox.pack_start(self.wid_text, expand=True, fill=True)

        hbox.pack_start(gtk.VSeparator(), padding=2, expand=False, fill=False)

        self.wid_but_add = gtk.Button(stock='gtk-add')
        self.wid_but_add.set_relief(gtk.RELIEF_HALF)
        self.wid_but_add.set_focus_on_click(True)
        self.wid_but_add.connect('clicked', self._sig_add)
        hbox.pack_start(self.wid_but_add, padding=3, expand=False, fill=False)

        self.wid_but_remove = gtk.Button(stock='gtk-remove')
        self.wid_but_remove.set_relief(gtk.RELIEF_HALF)
        self.wid_but_remove.set_focus_on_click(True)
        self.wid_but_remove.connect('clicked', self._sig_remove)
        hbox.pack_start(self.wid_but_remove, expand=False, fill=False)

        self.widget.pack_start(hbox, expand=False, fill=False)
        self.widget.pack_start(gtk.HSeparator(), expand=False, fill=True)

        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.set_placement(gtk.CORNER_TOP_LEFT)
        scroll.set_shadow_type(gtk.SHADOW_NONE)

        self.screen = Screen(attrs['relation'], self._window,
                view_type=['tree'], views_preload=attrs.get('views', {}))
        scroll.add_with_viewport(self.screen.widget)
        self.widget.pack_start(scroll, expand=True, fill=True)

        self.old = None

    def grab_focus(self):
        return self.wid_text.grab_focus()

    def destroy(self):
        self.screen.destroy()
        self.widget.destroy()
        del self.widget

    def _sig_add(self, *args):
        domain = self._view.modelfield.domain_get(self._view.model)
        context = self._view.modelfield.context_get(self._view.model)

        try:
            ids = rpc.execute('object', 'execute',
                    self.attrs['relation'], 'name_search',
                    self.wid_text.get_text(), domain, 'ilike', context,
                    _LIMIT)
        except Exception, exception:
            common.process_exception(exception, self._window)
            return False
        ids = [x[0] for x in ids]
        if len(ids) != 1:
            win = WinSearch(self.attrs['relation'], sel_multi=True, ids=ids,
                    context=context, domain=domain, parent=self._window,
                    views_preload=self.attrs.get('views', {}))
            ids = win.run()

        self.screen.load(ids)
        self.screen.display()
        self.wid_text.set_text('')

    def _sig_remove(self, *args):
        self.screen.remove()
        self.screen.display()

    def _sig_activate(self, *args):
        self._sig_add()

    def _readonly_set(self, value):
        super(Many2Many, self)._readonly_set(value)
        self.wid_text.set_editable(not value)
        self.wid_text.set_sensitive(not value)
        self.wid_but_remove.set_sensitive(not value)
        self.wid_but_add.set_sensitive(not value)

    def display(self, model, model_field):
        super(Many2Many, self).display(model, model_field)
        ids = []
        if model_field:
            ids = model_field.get_client(model)
        if ids != self.old:
            self.screen.clear()
            self.screen.load(ids)
            self.old = ids
        self.screen.display()
        return True

    def set_value(self, model, model_field):
        model_field.set_client(model, [x.id for x in self.screen.models.models])
