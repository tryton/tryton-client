#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
from interface import Interface
import locale
import gettext

_ = gettext.gettext


class Integer(Interface):

    def __init__(self, name, parent, attrs=None):
        super(Integer, self).__init__(name, parent, attrs=attrs)
        self.widget = gtk.HBox(spacing=3)
        self.entry1 = gtk.Entry()
        self.entry1.set_max_length(0)
        self.entry1.set_width_chars(5)
        self.entry1.set_activates_default(True)
        self.entry1.set_alignment(1.0)
        self.entry1.connect('insert_text', self.sig_insert_text)
        self.widget.pack_start(self.entry1, expand=False, fill=True)
        self.widget.pack_start(gtk.Label('-'), expand=False, fill=False)
        self.entry2 = gtk.Entry()
        self.entry2.set_max_length(0)
        self.entry2.set_width_chars(5)
        self.entry2.set_activates_default(True)
        self.entry2.set_alignment(1.0)
        self.entry2.connect('insert_text', self.sig_insert_text)
        self.widget.pack_start(self.entry2, expand=False, fill=True)

    def _value_get(self):
        try:
            value1 = locale.atoi(self.entry1.get_text())
        except:
            value1 = 0
        try:
            value2 = locale.atoi(self.entry2.get_text())
        except:
            value2 = 0
        return self._get_clause(value1, value2)

    def _get_clause(self, value1, value2):
        res = []
        if value1 > value2:
            if value2 != 0:
                res.append((self.name, '>=', value2))
                res.append((self.name, '<=', value1))
            else:
                res.append((self.name, '>=', value1))
        elif value1 < value2:
            res.append((self.name, '>=', value1))
            res.append((self.name, '<=', value2))
        elif value1 == value2 and value1 != 0:
            res.append((self.name, '=', value1))
        return res

    def _value_set(self, value):
        def conv(value):
            if value == False:
                return ''
            else:
                return locale.format('%d', value or 0, True)
        self.entry1.set_text(conv(value[0]))
        self.entry2.set_text(conv(value[1]))

    value = property(_value_get, _value_set)

    def clear(self):
        self.value = (False, False)

    def sig_activate(self, fct):
        self.entry1.connect_after('activate', fct)
        self.entry2.connect_after('activate', fct)

    def sig_insert_text(self, widget, new_text, new_text_length, position):
        value = widget.get_text()
        position = widget.get_position()
        new_value = value[:position] + new_text + value[position:]
        try:
            if new_value == '-':
                return
            locale.atoi(new_value)
        except:
            widget.stop_emission('insert-text')
