#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gettext
from interface import Interface

_ = gettext.gettext


class CheckBox(Interface):

    def __init__(self, name, parent, attrs=None):
        super(CheckBox, self).__init__(name, parent, attrs)

        self.widget = gtk.combo_box_entry_new_text()
        self.widget.append_text('')
        self.widget.append_text(_('Yes'))
        self.widget.append_text(_('No'))

        self.entry = self.widget.child
        self.entry.set_property('activates_default', True)
        self.entry.set_editable(False)

    def _value_get(self):
        val = self.entry.get_text()
        if val:
            return [(self.name, '=', int(val == _('Yes')))]
        return []

    def _value_set(self, value):
        pass

    value = property(_value_get, _value_set, None,
            _('The content of the widget or ValueError if not valid'))
