import gtk
from interface import WidgetInterface

class Char(WidgetInterface):
    "Char"

    def __init__(self, window, parent, model, attrs=None):
        super(Char, self).__init__(window, parent, model=model, attrs=attrs)

        self.widget = gtk.HBox()
        self.entry = gtk.Entry()
        self.entry.set_property('activates_default', True)
        self.entry.set_max_length(int(attrs.get('size', 16)))
        self.entry.set_width_chars(5)

        self.entry.connect('button_press_event', self._menu_open)
        self.entry.connect('activate', self.sig_activate)
        self.entry.connect('focus-in-event', lambda x, y: self._focus_in())
        self.entry.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.pack_start(self.entry)

    def _color_widget(self):
        return self.entry

    def set_value(self, model, model_field):
        return model_field.set_client(model, self.entry.get_text() or False)

    def display(self, model, model_field):
        super(Char, self).display(model, model_field)
        if not model_field:
            self.entry.set_text('')
            return False
        self.entry.set_text(model_field.get(model) or '')

    def _readonly_set(self, value):
        super(Char, self)._readonly_set(value)
        self.entry.set_editable(not value)
        self.entry.set_sensitive(not value)
