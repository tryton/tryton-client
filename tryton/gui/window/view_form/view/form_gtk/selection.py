import gtk
import gobject
from interface import WidgetInterface


class Selection(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(Selection, self).__init__(window, parent, model, attrs)

        self.widget = gtk.HBox(spacing=3)
        self.entry = gtk.ComboBoxEntry()
        child = self.entry.get_child()
        self.sig_changed_id = child.connect('changed',
                lambda x, y: self.sig_changed)
        child.set_editable(False)
        child.connect('button_press_event', self._menu_open)
        child.connect('key_press_event', self.sig_key_pressed)
        self.entry.set_size_request(int(attrs.get('size', -1)), -1)
        self.widget.pack_start(self.entry, expand=True, fill=True)

        self._selection = {}
        self.key_catalog = {}
        self.set_popdown(attrs.get('selection', []))
        self.last_key = (None, 0)

    def set_popdown(self, selection):
        model = gtk.ListStore(gobject.TYPE_STRING)
        self._selection = {}
        lst = []
        for (i, j) in selection:
            name = str(j)
            lst.append(name)
            self._selection[name] = i
        self.key_catalog = {}
        for name in lst:
            i = model.append()
            model.set(i, 0, name)
            if name:
                key = name[0].lower()
                self.key_catalog.setdefault(key, []).append(i)
        self.entry.set_model(model)
        self.entry.set_text_column(0)
        return lst

    def _readonly_set(self, value):
        super(Selection, self)._readonly_set(value)
        self.entry.set_sensitive(not value)

    def value_get(self):
        child = self.entry.get_child()
        res = child.get_text()
        return self._selection.get(res, False)

    def set_value(self, model, model_field):
        model_field.set_client(model, self.value_get())

    def _menu_sig_default_set(self):
        self.set_value(self._view.model, self._view.modelfield)
        super(Selection, self)._menu_sig_default_set()

    def display(self, model, model_field):
        child = self.entry.get_child()
        if self.sig_changed_id:
            child.disconnect(self.sig_changed_id)
            self.sig_changed_id = False
        if not model_field:
            child.set_text('')
            return False
        super(Selection, self).display(model, model_field)
        value = model_field.get(model)
        if not value:
            child.set_text('')
        else:
            found = False
            for long_text, sel_value in self._selection.items():
                if sel_value == value:
                    child.set_text(long_text)
                    found = True
                    break
        self.sig_changed_id = child.connect('changed',
                lambda x, y: self.sig_changed)

    def sig_changed(self):
        super(Selection, self).sig_changed()
        self._focus_out()

    def sig_key_pressed(self, *args):
        key = args[1].string.lower()
        if self.last_key[0] == key:
            self.last_key[1] += 1
        else:
            self.last_key = [ key, 1 ]
        if not self.key_catalog.has_key(key):
            return
        self.entry.set_active_iter(self.key_catalog[key][self.last_key[1] % \
                len(self.key_catalog[key])])
