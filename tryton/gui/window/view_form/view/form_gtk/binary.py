#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import base64
import gtk
import gettext
import os
from tryton.common import file_selection, message, warning, Tooltips
from interface import WidgetInterface

_ = gettext.gettext

def humanize(size):
    for x in ('bytes', 'KB', 'MB', 'GB', 'TB', 'PB'):
        if size < 1000:
            return '%3.1f%s' % (size, x)
        size /= 1000.0


class Binary(WidgetInterface):
    "Binary"

    def __init__(self, field_name, model_name, window, attrs=None):
        super(Binary, self).__init__(field_name, model_name, window,
                attrs=attrs)

        self.filename = attrs.get('filename')
        self.filename_visible = attrs.get('filename_visible')

        self.tooltips = Tooltips()

        self.widget = gtk.HBox(spacing=0)
        if self.filename and self.filename_visible:
            self.wid_text = gtk.Entry()
            self.wid_text.set_property('activates_default', True)
            self.wid_text.connect('focus-in-event', lambda x, y: self._focus_in())
            self.wid_text.connect('focus-out-event', lambda x, y: self._focus_out())
            self.wid_text.connect_after('key_press_event', self.sig_key_press)
            self.wid_size = gtk.Entry()
            self.wid_size.set_width_chars(11)
            self.wid_size.props.sensitive = False
            self.widget.pack_start(self.wid_text, expand=True, fill=True)
        else:
            self.wid_text = None
        self.widget.pack_start(self.wid_size, expand=not self.filename,
            fill=True)

        self.but_new = gtk.Button()
        img_new = gtk.Image()
        img_new.set_from_stock('tryton-open', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.but_new.set_image(img_new)
        self.but_new.set_relief(gtk.RELIEF_NONE)
        self.but_new.connect('clicked', self.sig_new)
        self.tooltips.set_tip(self.but_new, _('Select a File'))
        self.widget.pack_start(self.but_new, expand=False, fill=False)

        self.but_save_as = gtk.Button()
        img_save_as = gtk.Image()
        img_save_as.set_from_stock('tryton-save-as',
            gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.but_save_as.set_image(img_save_as)
        self.but_save_as.set_relief(gtk.RELIEF_NONE)
        self.but_save_as.connect('clicked', self.sig_save_as)
        self.tooltips.set_tip(self.but_save_as, _('Save As...'))
        self.widget.pack_start(self.but_save_as, expand=False, fill=False)

        self.but_remove = gtk.Button()
        img_remove = gtk.Image()
        img_remove.set_from_stock('tryton-clear', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.but_remove.set_image(img_remove)
        self.but_remove.set_relief(gtk.RELIEF_NONE)
        self.but_remove.connect('clicked', self.sig_remove)
        self.tooltips.set_tip(self.but_remove, _('Clear'))
        self.widget.pack_start(self.but_remove, expand=False, fill=False)

        self.tooltips.enable()

    def _readonly_set(self, value):
        if value:
            self.but_new.hide()
            self.but_remove.hide()
            self.widget.set_focus_chain([])
        else:
            self.but_new.show()
            self.but_remove.show()
            if self.wid_text:
                focus_chain = [self.wid_text]
            else:
                focus_chain = [self.but_new, self.but_save_as, self.but_remove]
            self.widget.set_focus_chain(focus_chain)

    def grab_focus(self):
        if self.wid_text:
            return self.wid_text.grab_focus()
        else:
            return self.wid_size.grab_focus()

    def sig_new(self, widget=None):
        try:
            filename = file_selection(_('Open...'),
                    parent=self.window)
            if filename and self.field:
                self.field.set_client(self.record,
                        base64.encodestring(open(filename, 'rb').read()))
                if self.filename and self.filename_visible and self.record:
                    name_wid = self.record.group.fields[self.filename]
                    name_wid.set_client(self.record, os.path.basename(filename))
                self.display(self.record, self.field)
        except Exception, exception:
            warning(_('Error reading the file.\nError message:\n%s') \
                    % str(exception), self.window, _('Error'))

    def sig_save_as(self, widget=None):
        try:
            filename = file_selection(_('Save As...'),
                    parent=self.window, action=gtk.FILE_CHOOSER_ACTION_SAVE)
            if filename and self.field:
                file_p = open(filename,'wb+')
                file_p.write(base64.decodestring(
                    self.field.get(self.record)))
                file_p.close()
        except Exception, exception:
            warning(_('Error writing the file.\nError message:\n%s') \
                    % str(exception), self.window, _('Error'))

    def sig_remove(self, widget=None):
        if self.field:
            self.field.set_client(self.record, False)
        self.display(self.record, self.field)

    def sig_key_press(self, widget, event, *args):
        editable = self.wid_text and self.wid_text.get_editable()
        if event.keyval == gtk.keysyms.F3 and editable:
            self.sig_new(widget)
            return True
        elif event.keyval == gtk.keysyms.F2:
            self.sig_save_as(widget)
            return True
        return False

    def display(self, record, field):
        super(Binary, self).display(record, field)
        if not field:
            if self.wid_text:
                self.wid_text.set_text('')
            self.wid_size.set_text('')
            self.but_save_as.set_sensitive(False)
            return False
        if self.wid_text:
            name_wid = record.group.fields[self.filename]
            self.wid_text.set_text(name_wid.get(record) or '')
        self.wid_size.set_text(humanize(len(field.get(record) or [])))
        self.but_save_as.set_sensitive(bool(field.get(record)))
        return True

    def display_value(self):
        if self.wid_text:
            return self.wid_text.get_text()
        else:
            return ''

    def set_value(self, record, field):
        if self.wid_text:
            name_wid = self.record.group.fields[self.filename]
            name_wid.set_client(self.record, self.wid_text.get_text() or False)
        return

    def _color_widget(self):
        if self.wid_text:
            return self.wid_text
        else:
            return self.wid_size
