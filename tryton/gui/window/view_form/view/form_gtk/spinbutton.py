import gtk
import sys
from interface import WidgetInterface


class SpinButton(WidgetInterface):
    "Spin button"

    def __init__(self, window, parent, model, attrs=None):
        super(SpinButton, self).__init__(window, parent, model, attrs)

        adj = gtk.Adjustment(0.0, -sys.maxint, sys.maxint, 1.0, 5.0, 5.0)
        self.widget = gtk.SpinButton(adj, 1.0,
                digits=int( attrs.get('digits',(14,2))[1] ) )
        self.widget.set_numeric(True)
        self.widget.set_activates_default(True)
        self.widget.connect('button_press_event', self._menu_open)
        if self.attrs['readonly']:
            self._readonly_set(True)
        self.widget.connect('focus-in-event', lambda x, y: self._focus_in())
        self.widget.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.connect('activate', self.sig_activate)

    def set_value(self, model, model_field):
        self.widget.update()
        model_field.set_client(model, self.widget.get_value())

    def display(self, model, model_field):
        if not model_field:
            self.widget.set_value( 0.0 )
            return False
        super(SpinButton, self).display(model, model_field)
        value = model_field.get(model) or 0.0
        self.widget.set_value( float(value) )

    def _readonly_set(self, value):
        self.widget.set_editable(not value)
        self.widget.set_sensitive(not value)
