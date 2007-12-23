import gtk
from interface import WidgetInterface

class Char(WidgetInterface):
    "Char"

    def __init__(self, window, parent, model, attrs=None):
        super(Char, self).__init__(window, parent, model=model, attrs=attrs)

        self.widget = gtk.Entry()
        self.widget.set_property('activates_default', True)
        self.widget.set_max_length(int(attrs.get('size', 16)))
        self.widget.set_visibility(not attrs.get('invisible', False))
        self.widget.set_width_chars(5)

        self.widget.connect('button_press_event', self._menu_open)
        self.widget.connect('activate', self.sig_activate)
        self.widget.connect('focus-in-event', lambda x, y: self._focus_in())
        self.widget.connect('focus-out-event', lambda x, y: self._focus_out())

    def set_value(self, model, model_field):
        return model_field.set_client(model, self.widget.get_text() or False)

    def display(self, model, model_field):
        super(Char, self).display(model, model_field)
        if not model_field:
            self.widget.set_text('')
            return False
        self.widget.set_text(model_field.get(model) or '')

    def _readonly_set(self, value):
        super(Char, self)._readonly_set(value)
        self.widget.set_editable(not value)
        self.widget.set_sensitive(not value)
