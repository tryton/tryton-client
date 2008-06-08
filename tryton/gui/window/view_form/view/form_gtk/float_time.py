import gtk
import math
import locale
from interface import WidgetInterface


class FloatTime(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(FloatTime, self).__init__(window, parent, model=model,
                attrs=attrs)

        self.widget = gtk.Entry()
        self.widget.set_alignment(1.0)
        self.widget.set_property('activates_default', True)

        self.widget.connect('populate-popup', self._populate_popup)
        self.widget.connect('activate', self.sig_activate)
        self.widget.connect('focus-in-event', lambda x, y: self._focus_in())
        self.widget.connect('focus-out-event', lambda x, y: self._focus_out())

    def text_to_float(self, text):
        try:
            if text and ':' in text:
                # assume <hours>:<minutes>
                h, m = text.split(':')
                h = h or 0
                m = m or 0
                return round(int(h) + int(m)/60.0, 2)
            else:
                # try float in locale notion
                return locale.atof(text)
        except:
            return 0.0

    def set_value(self, model, model_field):
        value = self.widget.get_text()
        if not value:
            return model_field.set_client(model, 0.0)
        return model_field.set_client(model, self.text_to_float(value))

    def display(self, model, model_field):
        super(FloatTime, self).display(model, model_field)
        if not model_field:
            self.widget.set_text('00:00')
            return False
        val = model_field.get(model)
        value = '%02d:%02d' % (math.floor(abs(val)),
                round(abs(val)%1+0.01, 2) * 60)
        if val < 0:
            value = '-' + value
        self.widget.set_text(value)

    def _readonly_set(self, value):
        self.widget.set_editable(not value)
        self.widget.set_sensitive(not value)
