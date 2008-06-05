import gettext
import gtk
from interface import WidgetInterface
import webbrowser


class URL(WidgetInterface):
    "url"

    def __init__(self, window, parent, model, attrs=None):
        if attrs is None:
            attrs = {}
        super(URL, self).__init__(window, parent, model, attrs=attrs)

        self.widget = gtk.HBox(homogeneous=False)

        self.entry = gtk.Entry()
        self.entry.set_max_length(int(attrs.get('size', 0)))
        self.entry.set_width_chars(5)
        self.entry.set_property('activates_default', True)
        self.entry.connect('activate', self.sig_activate)
        self.entry.connect('focus-in-event', lambda x, y: self._focus_in())
        self.entry.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.pack_start(self.entry, expand=True, fill=True)

        self.button = gtk.Button()
        img = gtk.Image()
        img.set_from_stock('gtk-jump-to', gtk.ICON_SIZE_BUTTON)
        self.button.set_image(img)
        self.button.set_relief(gtk.RELIEF_NONE)
        self.button.connect('clicked', self.button_clicked)
        self.button.set_alignment(0.5, 0.5)
        self.button.set_property('can-focus', False)
        self.widget.pack_start(self.button, expand=False, fill=False)

    def grab_focus(self):
        return self.entry.grab_focus()

    def set_value(self, model, model_field):
        return model_field.set_client(model, self.entry.get_text() or False)

    def display(self, model, model_field):
        if not model_field:
            self.entry.set_text('')
            return False
        super(URL, self).display(model, model_field)
        self.entry.set_text(model_field.get(model) or '')

    def _readonly_set(self, value):
        self.entry.set_editable(not value)
        self.entry.set_sensitive(not value)
        if value:
            self.entry.hide()
        else:
            self.entry.show()

    def button_clicked(self, widget):
        value = self.entry.get_text()
        if value:
            webbrowser.open(value, new=2)

    def _color_widget(self):
        return self.entry

class Email(URL):
    "email"

    def button_clicked(self, widget):
        value = self.entry.get_text()
        if value:
            webbrowser.open('mailto:%s' % value, new=2)

class CallTo(URL):
    "call to"

    def button_clicked(self, widget):
        value = self.entry.get_text()
        if value:
            webbrowser.open('callto:%s' % value, new=2)

class SIP(URL):
    "sip"

    def button_clicked(self, widget):
        value = self.entry.get_text()
        if value:
            webbrowser.open('sip:%s' % value, new=2)
