#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gettext

import gtk
from interface import WidgetInterface
from tryton.common import Tooltips

_ = gettext.gettext

class Char(WidgetInterface):
    "Char"

    def __init__(self, field_name, model_name, window, attrs=None):
        super(Char, self).__init__(field_name, model_name, window, attrs=attrs)

        self.widget = gtk.HBox()
        self.entry = gtk.Entry()
        self.entry.set_property('activates_default', True)
        self.entry.set_max_length(int(attrs.get('size', 0)))
        self.entry.set_width_chars(5)

        self.entry.connect('activate', self.sig_activate)
        self.entry.connect('focus-in-event', lambda x, y: self._focus_in())
        self.entry.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.pack_start(self.entry)

    def _color_widget(self):
        return self.entry

    def grab_focus(self):
        return self.entry.grab_focus()

    def set_value(self, record, field):
        return field.set_client(record, self.entry.get_text() or False)

    def display(self, record, field):
        super(Char, self).display(record, field)
        if not field:
            self.entry.set_text('')
            return False
        self.entry.set_text(field.get(record) or '')

    def _readonly_set(self, value):
        super(Char, self)._readonly_set(value)
        self.entry.set_editable(not value)
        if value:
            self.widget.set_focus_chain([])
        else:
            self.widget.set_focus_chain([self.entry])


class Sha(Char):

    def __init__(self, field_name, model_name, window, attrs=None):
        super(Sha, self).__init__(field_name, model_name, window, attrs=attrs)
        self.entry.props.visibility = False

        self.visibility_checkbox = gtk.CheckButton()
        self.visibility_checkbox.connect('toggled', self.toggle_visibility)
        Tooltips().set_tip(self.visibility_checkbox, _('Show plain text'))
        self.widget.pack_start(self.visibility_checkbox, expand=False)

    def _readonly_set(self, value):
        super(Char, self)._readonly_set(value)
        self.entry.set_editable(not value)
        self.visibility_checkbox.props.visible = not value
        if value:
            self.widget.set_focus_chain([])
        else:
            self.widget.set_focus_chain([self.entry, self.visibility_checkbox])

    def toggle_visibility(self, button):
        self.entry.props.visibility = not self.entry.props.visibility
