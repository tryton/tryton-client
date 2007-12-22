import gtk
import sys
import gettext
from interface import Interface

_ = gettext.gettext


class SpinButton(Interface):

    def __init__(self, name, parent, attrs=None):
        if attrs is None:
            attrs = {}
        super(SpinButton, self).__init__(name, parent, attrs)

        self.widget = gtk.HBox(spacing=3)

        adj1 = gtk.Adjustment(0.0, -sys.maxint, sys.maxint, 1.0, 5.0, 5.0)
        self.spin1 = gtk.SpinButton(adj1, 1.0,
                digits=int(attrs.get('digits', (14, 2))[1]))
        self.spin1.set_numeric(True)
        self.spin1.set_activates_default(True)
        self.widget.pack_start(self.spin1, expand=False, fill=True)

        self.widget.pack_start(gtk.Label('-'), expand=False, fill=False)

        adj2 = gtk.Adjustment(0.0, -sys.maxint, sys.maxint, 1.0, 5.0, 5.0)
        self.spin2 = gtk.SpinButton(adj2, 1.0,
                digits=int(attrs.get('digits', (14, 2))[1]))
        self.spin2.set_numeric(True)
        self.spin2.set_activates_default(True)
        self.widget.pack_start(self.spin2, expand=False, fill=True)

    def _value_get(self):
        res = []
        self.spin1.update()
        self.spin2.update()
        if self.spin1.get_value() > self.spin2.get_value():
            if self.spin2.get_value() != 0.0:
                res.append((self.name, '>=', self.spin2.get_value()))
                res.append((self.name, '<=', self.spin1.get_value()))
            else:
                res.append((self.name, '>=', self.spin1.get_value()))
        elif self.spin2.get_value() > self.spin1.get_value():
            res.append((self.name, '<=', self.spin2.get_value()))
            res.append((self.name, '>=', self.spin1.get_value()))
        elif (self.spin2.get_value() == self.spin1.get_value()) \
                and (self.spin1.get_value() != 0.0):
            res.append((self.name, '=', self.spin1.get_value()))
        return res

    def _value_set(self, value):
        self.spin1.set_value(value)
        self.spin2.set_value(value)

    value = property(_value_get, _value_set, None,
            _('The content of the widget or ValueError if not valid'))

    def clear(self):
        self.value = 0.00

    def sig_activate(self, fct):
        self.spin1.connect_after('activate', fct)
        self.spin2.connect_after('activate', fct)
