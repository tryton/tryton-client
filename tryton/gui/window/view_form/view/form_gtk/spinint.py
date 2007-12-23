import gtk
import sys
from interface import WidgetInterface


class SpinInt(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(SpinInt, self).__init__(window, parent, model, attrs)

        adj = gtk.Adjustment(0.0, -sys.maxint, sys.maxint, 1.0, 5.0, 5.0)
        self.widget = gtk.SpinButton(adj, 1, digits=0)
        self.widget.set_numeric(True)
        self.widget.set_width_chars(5)
        self.widget.set_activates_default(True)
        self.widget.connect('button_press_event', self._menu_open)
        self.widget.connect('focus-in-event', lambda x, y: self._focus_in())
        self.widget.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.connect('activate', self.sig_activate)

    def set_value(self, model, model_field):
        self.widget.update()
        model_field.set_client(model, self.widget.get_value_as_int())

    def display(self, model, model_field):
        super(SpinInt, self).display(model, model_field)
        if not model_field:
            self.widget.set_value(0)
            return False
        value = model_field.get(model)
        if isinstance(value, int):
            self.widget.set_value(value)
        elif isinstance(value, float):
            self.widget.set_value(int(value))
        else:
            self.widget.set_value(0)

    def _readonly_set(self, value):
        super(SpinInt, self)._readonly_set(value)
        self.widget.set_editable(not value)
        self.widget.set_sensitive(not value)
