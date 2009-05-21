#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gtk
import locale
from interface import WidgetInterface
import tryton.common as common


class FloatTime(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(FloatTime, self).__init__(window, parent, model=model,
                attrs=attrs)

        self.widget = gtk.HBox()
        self.entry = gtk.Entry()
        self.entry.set_alignment(1.0)
        self.entry.set_property('activates_default', True)

        self.entry.connect('populate-popup', self._populate_popup)
        self.entry.connect('activate', self.sig_activate)
        self.entry.connect('focus-in-event', lambda x, y: self._focus_in())
        self.entry.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.pack_start(self.entry)

    def _color_widget(self):
        return self.entry

    def grab_focus(self):
        return self.entry.grab_focus()

    def text_to_float(self, text):
        try:
            try:
                return round(locale.atof(text), 2)
            except:
                pass
            conv = common.FLOAT_TIME_CONV
            for key in common.FLOAT_TIME_SEPS.keys():
                text = text.replace(common.FLOAT_TIME_SEPS[key], key + ' ')
            value = 0
            for buf in text.split(' '):
                buf = buf.strip()
                if ':' in buf:
                    hour, min = buf.split(':')
                    value += abs(int(hour or 0))
                    value += abs(int(min or 0) * conv['m'])
                    continue
                elif '-' in buf and not buf.startswith('-'):
                    hour, min = buf.split('-')
                    value += abs(int(hour or 0))
                    value += abs(int(min or 0) * conv['m'])
                    continue
                try:
                    value += abs(locale.atof(buf))
                    continue
                except:
                    pass
                for sep in conv.keys():
                    if buf.endswith(sep):
                        value += abs(locale.atof(buf[:-len(sep)])) * conv[sep]
                        break
            if text.startswith('-'):
                value *= -1
            return round(value, 2)
        except:
            return 0.0

    def set_value(self, model, model_field):
        value = self.entry.get_text()
        if not value:
            return model_field.set_client(model, 0.0)
        return model_field.set_client(model, self.text_to_float(value))

    def display(self, model, model_field):
        super(FloatTime, self).display(model, model_field)
        if not model_field:
            self.entry.set_text('00:00')
            return False
        val = model_field.get(model)

        conv = common.FLOAT_TIME_CONV

        months = int(abs(val) / conv['M'])
        weeks = int((abs(val) - months * conv['M']) / conv['w'])
        days = int((abs(val) - months * conv['M'] - weeks * conv['w']) \
                / conv['d'])
        hours = int(abs(val) - months * conv['M'] - weeks * conv['w'] \
                - days * conv['d'])
        mins = round((abs(val) - months * conv['M'] - weeks * conv['w'] \
                - days * conv['d'] - hours)% 1, 2) / conv['m']
        value = ''
        if months:
            value += ' ' + locale.format('%d' + common.FLOAT_TIME_SEPS['M'],
                    months, True)
        if weeks:
            value += ' ' + locale.format('%d' + common.FLOAT_TIME_SEPS['w'],
                    weeks, True)
        if days:
            value += ' ' + locale.format('%d' + common.FLOAT_TIME_SEPS['d'],
                    days, True)
        if hours or mins:
            value += ' %02d:%02d' % (hours, mins)
        value = value.strip()
        if val < 0:
            value = '-' + value

        self.entry.set_text(value)

    def display_value(self):
        return self.entry.get_text()

    def _readonly_set(self, value):
        super(FloatTime, self)._readonly_set(value)
        self.entry.set_editable(not value)
        if value:
            self.widget.set_focus_chain([])
        else:
            self.widget.set_focus_chain([self.entry])
