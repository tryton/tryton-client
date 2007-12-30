from char import Char
from integer import Integer
import locale


class Float(Integer):
    "Float"

    def __init__(self, window, parent, model, attrs=None):
        super(Float, self).__init__(window, parent, model=model, attrs=attrs)
        self.digits = attrs.get('digits', (14, 2))

    def set_value(self, model, model_field):
        try:
            value = locale.atof(self.widget.get_text())
        except:
            value = 0.0
        return model_field.set_client(model, value)

    def display(self, model, model_field):
        super(Char, self).display(model, model_field)
        if not model_field:
            self.widget.set_text('')
            return False
        self.widget.set_text(locale.format('%.' + str(self.digits[1]) + 'f',
            model_field.get(model) or 0.0, True))

    def sig_insert_text(self, widget, new_text, new_text_length, position):
        value = widget.get_text()
        position = widget.get_position()
        new_value = value[:position] + new_text + value[position:]
        try:
            if len(str(int(locale.atof(new_value)))) > self.digits[0]:
                widget.stop_emission('insert-text')
        except:
            widget.stop_emission('insert-text')
