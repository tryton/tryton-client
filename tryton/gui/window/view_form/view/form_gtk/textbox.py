import gtk
from interface import WidgetInterface


class TextBox(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(TextBox, self).__init__(window, parent, model, attrs)

        self.widget = gtk.HBox()
        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
                gtk.POLICY_AUTOMATIC)
        self.scrolledwindow.set_shadow_type(gtk.SHADOW_NONE)
        self.scrolledwindow.set_size_request(-1, 80)

        self.textview = gtk.TextView()
        self.textview.set_wrap_mode(gtk.WRAP_WORD)
        self.textview.connect('button_press_event', self._menu_open)
        #TODO better tab solution
        self.textview.set_accepts_tab(False)
        self.textview.connect('focus-out-event', lambda x, y: self._focus_out())
        self.scrolledwindow.add(self.textview)
        self.scrolledwindow.show_all()

        self.widget.pack_start(self.scrolledwindow)

    def _readonly_set(self, value):
        super(TextBox, self)._readonly_set(value)
        self.textview.set_editable(not value)
        self.textview.set_sensitive(not value)

    def _color_scrolledwindow(self):
        return self.textview

    def set_value(self, model, model_field):
        buf = self.textview.get_buffer()
        iter_start = buf.get_start_iter()
        iter_end = buf.get_end_iter()
        current_text = buf.get_text(iter_start, iter_end, False)
        model_field.set_client(model, current_text or False)

    def display(self, model, model_field):
        super(TextBox, self).display(model, model_field)
        value = model_field and model_field.get(model)
        if not value:
            value = ''
        buf = self.textview.get_buffer()
        buf.delete(buf.get_start_iter(), buf.get_end_iter())
        iter_start = buf.get_start_iter()
        buf.insert(iter_start, value)
