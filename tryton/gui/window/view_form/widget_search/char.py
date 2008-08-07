#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gettext
from interface import Interface

_ = gettext.gettext


class Char(Interface):

    def __init__(self, name, parent, attrs=None):
        if attrs is None:
            attrs = {}
        super(Char, self).__init__(name, parent, attrs)

        self.widget = gtk.Entry()
        self.widget.set_max_length(int(attrs.get('size', 0)))
        self.widget.set_width_chars(5)
        self.widget.set_property('activates_default', True)

    def _value_get(self):
        value = self.widget.get_text()
        if value:
            return [(self.name, self.attrs.get('comparator', 'ilike'), value)]
        else:
            return []

    def _value_set(self, value):
        self.widget.set_text(value or '')

    value = property(_value_get, _value_set)

    def clear(self):
        self.value = ''

    def _readonly_set(self, value):
        self.widget.set_editable(not value)
        self.widget.set_sensitive(not value)

    def sig_activate(self, fct):
        self.widget.connect_after('activate', fct)
