#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import locale
from integer import Integer
import gettext

_ = gettext.gettext


class Float(Integer):

    def __init__(self, name, parent, attrs=None):
        super(Float, self).__init__(name, parent, attrs=attrs)
        self.digits = attrs.get('digits', (14, 2))

    def _value_get(self):
        try:
            value1 = locale.atof(self.entry1.get_text())
        except:
            value1 = 0.0
        try:
            value2 = locale.atof(self.entry2.get_text())
        except:
            value2 = 0.0
        return self._get_clause(value1, value2)

    def _value_set(self, value):
        if value == False:
            text = ''
        else:
            text = locale.format('%.' + str(self.digits[1]) + 'f',
            value or 0.0, True)
        self.entry1.set_text(text)
        self.entry2.set_text(text)

    value = property(_value_get, _value_set, None,
            _('The content of the widget or ValueError if not valid'))

    def clear(self):
        self.value = False

    def sig_insert_text(self, widget, new_text, new_text_length, position):
        value = widget.get_text()
        position = widget.get_position()
        new_value = value[:position] + new_text + value[position:]
        try:
            if len(str(int(locale.atof(new_value)))) > self.digits[0]:
                widget.stop_emission('insert-text')
        except:
            widget.stop_emission('insert-text')
