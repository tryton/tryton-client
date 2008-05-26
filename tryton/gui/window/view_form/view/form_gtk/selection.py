import gtk
import gobject
from interface import WidgetInterface
import tryton.rpc as rpc


class Selection(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(Selection, self).__init__(window, parent, model, attrs)

        self.widget = gtk.HBox(spacing=3)
        self.entry = gtk.ComboBoxEntry()
        child = self.entry.get_child()
        child.set_property('activates_default', True)
        child.connect('changed', self.sig_changed)
        self.changed = True
        child.connect('button_press_event', self._menu_open)
        child.connect('activate', self.sig_activate)
        child.connect_after('focus-out-event', self.sig_activate)
        self.entry.set_size_request(int(attrs.get('widget_size', -1)), -1)
        self.widget.pack_start(self.entry, expand=True, fill=True)

        self._selection = {}
        selection = attrs.get('selection', [])
        if 'relation' in attrs:
            try:
                selection = rpc.execute('object', 'execute',
                        attrs['relation'], 'name_search', '',
                        attrs.get('domain', []), 'ilike', rpc.CONTEXT)
            except Exception, exception:
                rpc.process_exception(exception, self._window)
                selection = []
        else:
            if not isinstance(selection, (list, tuple)):
                try:
                    selection = rpc.execute('object', 'execute',
                            self.model, selection, rpc.CONTEXT)
                except Exception, exception:
                    rpc.process_exception(exception, self._window)
                    selection = []
        selection.sort(lambda x, y: cmp(x[1], y[1]))
        attrs['selection'] = selection
        self.set_popdown(selection)
        self.last_key = (None, 0)

    def grab_focus(self):
        return self.entry.grab_focus()

    def set_popdown(self, selection):
        model = gtk.ListStore(gobject.TYPE_STRING)
        self._selection = {}
        lst = []
        for (value, name) in selection:
            name = str(name)
            lst.append(name)
            self._selection[name] = value
            i = model.append()
            model.set(i, 0, name)
        self.entry.set_model(model)
        self.entry.set_text_column(0)
        return lst

    def _readonly_set(self, value):
        super(Selection, self)._readonly_set(value)
        self.entry.set_sensitive(not value)

    def _color_widget(self):
        return self.entry.get_child()

    def value_get(self):
        child = self.entry.get_child()
        res = child.get_text()
        return self._selection.get(res, False)

    def sig_activate(self, widget, event=None):
        text = self.entry.child.get_text()
        value = False
        if text:
            for txt, val in self._selection.items():
                if not val:
                    continue
                if txt[:len(text)].lower() == text.lower():
                    value = val
                    if len(txt) == len(text):
                        break
        self._view.modelfield.set_client(self._view.model, value, force_change=True)
        self.display(self._view.model, self._view.modelfield)

    def set_value(self, model, model_field):
        model_field.set_client(model, self.value_get())

    def _menu_sig_default_set(self):
        self.set_value(self._view.model, self._view.modelfield)
        super(Selection, self)._menu_sig_default_set()

    def display(self, model, model_field):
        child = self.entry.get_child()
        self.changed = False
        if not model_field:
            child.set_text('')
            return False
        super(Selection, self).display(model, model_field)
        value = model_field.get(model)
        if isinstance(value, (list, tuple)):
            value = value[0]
        if not value:
            child.set_text('')
        else:
            found = False
            for long_text, sel_value in self._selection.items():
                if sel_value == value:
                    child.set_text(long_text)
                    found = True
                    break
        self.changed = True

    def sig_changed(self, *args):
        if self.changed:
            self._focus_out()
