# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import gettext

from gi.repository import Gdk, GLib, Gtk

import tryton.common as common
from tryton.common.completion import get_completion, update_completion
from tryton.common.domain_parser import quote
from tryton.common.entry_position import reset_position
from tryton.common.popup_menu import populate
from tryton.gui.window.view_form.screen import Screen
from tryton.gui.window.win_form import WinForm
from tryton.gui.window.win_search import WinSearch

from .widget import Widget

_ = gettext.gettext


class Many2One(Widget):

    def __init__(self, view, attrs):
        super(Many2One, self).__init__(view, attrs)

        self.widget = Gtk.HBox(spacing=0)
        self.widget.set_property('sensitive', True)

        self.wid_text = self.mnemonic_widget = Gtk.Entry()
        self.wid_text.set_property('width-chars', self.default_width_chars)
        self.wid_text.set_property('activates_default', True)
        self.wid_text.connect('key-press-event', self.send_modified)
        self.wid_text.connect('key_press_event', self.sig_key_press)
        self.wid_text.connect('populate-popup', self._populate_popup)
        self.wid_text.connect('focus-out-event',
            lambda x, y: self._focus_out())
        self.wid_text.connect('changed', self.sig_changed)
        self.changed = True
        self.focus_out = True

        if int(self.attrs.get('completion', 1)):
            self.wid_text.connect('changed', self._update_completion)
        self.wid_completion = None

        self.wid_text.connect('icon-press', self.sig_edit)

        self.widget.pack_end(self.wid_text, expand=True, fill=True, padding=0)

        self._readonly = False

    def get_model(self):
        return self.attrs['relation']

    def _readonly_set(self, value):
        self._readonly = value
        self._set_button_sensitive()

    def _set_button_sensitive(self):
        self.wid_text.set_editable(not self._readonly)
        self.wid_text.set_icon_sensitive(
            Gtk.EntryIconPosition.PRIMARY, self.read_access)
        self.wid_text.set_icon_sensitive(
            Gtk.EntryIconPosition.SECONDARY, not self._readonly)

    def get_access(self, type_):
        model = self.get_model()
        if model:
            return common.MODELACCESS[model][type_]
        else:
            return True

    @property
    def read_access(self):
        return self.get_access('read')

    @property
    def create_access(self):
        return int(self.attrs.get('create', 1)) and self.get_access('create')

    @property
    def modified(self):
        if self.record and self.field:
            value = self.wid_text.get_text()
            return self.field.get_client(self.record) != value
        return False

    @staticmethod
    def has_target(value):
        return value is not None

    @staticmethod
    def value_from_id(id_, str_=None):
        if str_ is None:
            str_ = ''
        return id_, str_

    @staticmethod
    def id_from_value(value):
        return value

    def sig_activate(self):
        model = self.get_model()
        if not model or not common.MODELACCESS[model]['read']:
            return
        if not self.focus_out or not self.field:
            return
        self.changed = False
        value = self.field.get(self.record)
        model = self.get_model()

        self.focus_out = False
        if model and not self.has_target(value):
            if (not self._readonly
                    and (self.wid_text.get_text()
                        or self.field.get_state_attrs(
                            self.record)['required'])):
                domain = self.field.domain_get(self.record)
                context = self.field.get_search_context(self.record)
                order = self.field.get_search_order(self.record)
                text = self.wid_text.get_text()

                def callback(result):
                    if result:
                        self.field.set_client(self.record,
                            self.value_from_id(*result[0]), force_change=True)
                    else:
                        self.wid_text.set_text('')
                    self.focus_out = True
                    self.changed = True

                win = WinSearch(model, callback, sel_multi=False,
                    context=context, domain=domain, order=order,
                    view_ids=self.attrs.get('view_ids', '').split(','),
                    views_preload=self.attrs.get('views', {}),
                    new=self.create_access,
                    title=self.attrs.get('string'),
                    exclude_field=self.attrs.get('relation_field'))
                win.screen.search_filter(quote(text))
                if len(win.screen.group) == 1:
                    callback([
                            (r.id, r.value.get('rec_name', ''))
                            for r in win.screen.group])
                    win.destroy()
                else:
                    win.show()
                return
        self.focus_out = True
        self.changed = True
        return

    def get_screen(self, search=False):
        domain = self.field.domain_get(self.record)
        if search:
            context = self.field.get_search_context(self.record)
        else:
            context = self.field.get_context(self.record)
        # Remove first tree view as mode is form only
        view_ids = self.attrs.get('view_ids', '').split(',')[1:]
        model = self.get_model()
        breadcrumb = list(self.view.screen.breadcrumb)
        breadcrumb.append(
            self.attrs.get('string') or common.MODELNAME.get(model))
        return Screen(model, domain=domain, context=context,
            mode=['form'], view_ids=view_ids,
            views_preload=self.attrs.get('views', {}), readonly=self._readonly,
            exclude_field=self.attrs.get('relation_field'),
            breadcrumb=breadcrumb)

    def sig_new(self, *args):
        if not self.create_access:
            return
        self.focus_out = False
        screen = self.get_screen(search=True)

        def callback(result):
            if result:
                self.field.set_client(self.record,
                    self.value_from_id(screen.current_record.id,
                        screen.current_record.rec_name()))
            self.focus_out = True
        WinForm(screen, callback, new=True, save_current=True,
            rec_name=self.wid_text.get_text())

    def sig_edit(self, entry=None, icon_pos=None, *args):
        model = self.get_model()
        if not model or not common.MODELACCESS[model]['read']:
            return
        if not self.focus_out or not self.field:
            return
        self.changed = False
        self.focus_out = False
        value = self.field.get(self.record)

        if (icon_pos == Gtk.EntryIconPosition.SECONDARY
                and not self._readonly
                and self.has_target(value)):
            self.field.set_client(self.record, self.value_from_id(None, ''))
            self.wid_text.set_text('')
            self.changed = True
            self.focus_out = True
            return

        if self.has_target(value):
            screen = self.get_screen()
            screen.load([self.id_from_value(self.field.get(self.record))])

            def callback(result):
                if result:
                    self.field.set_client(self.record,
                        self.value_from_id(screen.current_record.id,
                            screen.current_record.rec_name()),
                        force_change=True)
                self.focus_out = True
                self.changed = True
            WinForm(screen, callback, save_current=True)
            return
        if not self._readonly:
            domain = self.field.domain_get(self.record)
            context = self.field.get_search_context(self.record)
            order = self.field.get_search_order(self.record)
            text = self.wid_text.get_text()

            def callback(result):
                if result:
                    self.field.set_client(self.record,
                        self.value_from_id(*result[0]), force_change=True)
                self.focus_out = True
                self.changed = True
            win = WinSearch(model, callback, sel_multi=False,
                context=context, domain=domain, order=order,
                view_ids=self.attrs.get('view_ids', '').split(','),
                views_preload=self.attrs.get('views', {}),
                new=self.create_access, title=self.attrs.get('string'),
                exclude_field=self.attrs.get('relation_field'))
            win.screen.search_filter(quote(text))
            win.show()
            return
        self.focus_out = True
        self.changed = True

    def sig_key_press(self, widget, event, *args):
        editable = self.wid_text.get_editable()
        activate_keys = [Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab]
        if not self.wid_completion:
            activate_keys.append(Gdk.KEY_Return)
        if (event.keyval == Gdk.KEY_F3
                and editable
                and self.create_access):
            self.sig_new(widget, event)
            return True
        elif event.keyval == Gdk.KEY_F2 and self.read_access:
            self.sig_edit(widget)
            return True
        elif (event.keyval in activate_keys
                and editable):
            self.sig_activate()
        elif (self.has_target(self.field.get(self.record))
                and editable
                and event.keyval in [Gdk.KEY_Delete, Gdk.KEY_BackSpace]):
            self.wid_text.set_text('')
        return False

    def sig_changed(self, *args):
        if not self.changed:
            return False
        value = self.field.get(self.record)
        if self.has_target(value) and self.modified:
            def clean():
                if not self.wid_text.props.window:
                    return
                text = self.wid_text.get_text()
                position = self.wid_text.get_position()
                self.field.set_client(self.record,
                    self.value_from_id(None, ''))
                # The value of the field could be different of None
                # in such case, the original text should not be restored
                if not self.wid_text.get_text():
                    # Restore text and position after display
                    self.wid_text.set_text(text)
                    self.wid_text.set_position(position)
            GLib.idle_add(clean)
        return False

    def get_value(self):
        return self.wid_text.get_text()

    def set_value(self):
        if self.field.get_client(self.record) != self.wid_text.get_text():
            self.field.set_client(self.record, self.value_from_id(None, ''))
            self.wid_text.set_text('')

    def set_text(self, value):
        if not value:
            value = ''
        self.wid_text.set_text(value)
        reset_position(self.wid_text)

    def display(self):
        self.changed = False
        super(Many2One, self).display()

        self._set_button_sensitive()
        self._set_completion()

        if not self.field:
            self.set_text(None)
            self.changed = True
            return False
        self.set_text(self.field.get_client(self.record))
        if self.has_target(self.field.get(self.record)):
            icon1, tooltip1 = 'tryton-open', _('Open the record <F2>')
            icon2, tooltip2 = 'tryton-clear', _('Clear the field <Del>')
        else:
            icon1, tooltip1 = None, ''
            icon2, tooltip2 = 'tryton-search', _('Search a record <F2>')
        if not self.wid_text.get_editable():
            icon2, tooltip2 = None, ''
        for pos, icon, tooltip in [
                (Gtk.EntryIconPosition.PRIMARY, icon1, tooltip1),
                (Gtk.EntryIconPosition.SECONDARY, icon2, tooltip2)]:
            if icon:
                pixbuf = common.IconFactory.get_pixbuf(
                    icon, Gtk.IconSize.MENU)
            else:
                pixbuf = None
            self.wid_text.set_icon_from_pixbuf(pos, pixbuf)
            self.wid_text.set_icon_tooltip_text(pos, tooltip)
        self.changed = True

    def _populate_popup(self, widget, menu):
        value = self.field.get(self.record)
        if self.has_target(value):
            populate(
                menu, self.get_model(), self.id_from_value(value),
                '', self.field, self.field.get_context(self.record))
        return True

    def _set_completion(self):
        if not int(self.attrs.get('completion', 1)):
            return
        self.wid_completion = get_completion(
            search=self.read_access,
            create=self.create_access)
        self.wid_completion.connect('match-selected',
            self._completion_match_selected)
        self.wid_completion.connect('action-activated',
            self._completion_action_activated)
        self.wid_text.set_completion(self.wid_completion)

    def _completion_match_selected(self, completion, model, iter_):
        rec_name, record_id = model.get(iter_, 0, 1)
        # GTK on win32 doesn't like synchronous call to set_client
        # because it triggers a display which reset the completion
        GLib.idle_add(self.field.set_client, self.record,
            self.value_from_id(record_id, rec_name), True)

        completion_model = self.wid_completion.get_model()
        completion_model.clear()
        completion_model.search_text = rec_name
        return True

    def _update_completion(self, widget):
        if self._readonly:
            return
        if not self.record:
            return
        value = self.field.get(self.record)
        if self.has_target(value):
            id_ = self.id_from_value(value)
            if id_ is not None and id_ >= 0:
                return
        model = self.get_model()
        update_completion(self.wid_text, self.record, self.field, model)

    def _completion_action_activated(self, completion, index):
        if index == 0:
            self.sig_edit()
        elif index == 1:
            self.sig_new()
