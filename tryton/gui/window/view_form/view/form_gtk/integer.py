from char import Char
import locale


class Integer(Char):
    "Integer"

    def __init__(self, window, parent, model, attrs=None):
        super(Integer, self).__init__(window, parent, model=model, attrs=attrs)
        self.widget.set_max_length(0)
        self.widget.set_alignment(1.0)
        self.widget.connect('insert_text', self.sig_insert_text)

    def set_value(self, model, model_field):
        try:
            value = locale.atoi(self.widget.get_text())
        except:
            value = 0
        return model_field.set_client(model, value)

    def display(self, model, model_field):
        super(Char, self).display(model, model_field)
        if not model_field:
            self.widget.set_text('')
            return False
        self.widget.set_text(locale.format('%d',
            model_field.get(model) or 0, True))

    def sig_insert_text(self, widget, new_text, new_text_length, position):
        value = widget.get_text()
        position = widget.get_position()
        new_value = value[:position] + new_text + value[position:]
        try:
            locale.atoi(new_value)
        except:
            widget.stop_emission('insert-text')
