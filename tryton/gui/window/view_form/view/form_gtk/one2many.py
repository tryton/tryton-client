import gtk
import gettext
from tryton.common import TRYTON_ICON
from interface import WidgetInterface
from tryton.gui.window.view_form.screen import Screen

_ = gettext.gettext


class Dialog(object):

    def __init__(self, model_name, parent, model=None, attrs=None,
            model_ctx=None, window=None, default_get_ctx=None):

        if attrs is None:
            attrs = {}
        if model_ctx is None:
            model_ctx = {}
        if default_get_ctx is None:
            default_get_ctx = {}

        self.dia = gtk.Dialog(_('Tryton - Link'), window,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT)
        self.window = window
        self.dia.set_property('default-width', 760)
        self.dia.set_property('default-height', 500)
        self.dia.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.dia.set_icon(TRYTON_ICON)

        self.accel_group = gtk.AccelGroup()
        self.dia.add_accel_group(self.accel_group)

        icon_cancel = gtk.STOCK_CLOSE
        if not model:
            icon_cancel = gtk.STOCK_CANCEL
        self.but_cancel = self.dia.add_button(icon_cancel,
                gtk.RESPONSE_CANCEL)
        self.but_cancel.add_accelerator('clicked', self.accel_group,
                gtk.keysyms.Escape, gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

        self.but_ok = self.dia.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.but_ok.add_accelerator('clicked', self.accel_group,
                gtk.keysyms.Return, gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

        self.default_get_ctx = default_get_ctx

        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.set_placement(gtk.CORNER_TOP_LEFT)
        scroll.set_shadow_type(gtk.SHADOW_NONE)
        self.dia.vbox.pack_start(scroll, expand=True, fill=True)

        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        scroll.add(viewport)

        self.dia.show_all()
        self.screen = Screen(model_name, self.dia, view_type=[], parent=parent,
                exclude_field=attrs.get('relation_field', None))
        self.screen.models._context.update(model_ctx)
        if not model:
            model = self.screen.new(context=default_get_ctx)
        self.screen.models.model_add(model)
        self.screen.current_model = model
        if ('views' in attrs) and ('form' in attrs['views']):
            arch = attrs['views']['form']['arch']
            fields = attrs['views']['form']['fields']
            if attrs.get('relation_field', False) \
                    and attrs['relation_field'] in fields:
                del fields[attrs['relation_field']]
            self.screen.add_view(arch, fields, display=True,
                    context=default_get_ctx)
        else:
            self.screen.add_view_id(False, 'form', display=True,
                    context=default_get_ctx)

        name = attrs.get('string', '')
        if name:
            name += ' - '
        name += self.screen.current_view.title
        self.dia.set_title(self.dia.get_title() + ' - ' + name)

        viewport.add(self.screen.widget)
        width, height = self.screen.screen_container.size_get()
        viewport.set_size_request(width, height + 30)
        self.dia.show_all()
        self.screen.display()

    def new(self):
        model = self.screen.new(context=self.default_get_ctx)
        self.screen.models.model_add(model)
        self.screen.current_model = model
        return True

    def run(self):
        end = False
        while not end:
            res = self.dia.run()
            end = (res != gtk.RESPONSE_OK) \
                    or self.screen.current_model.validate()
            if not end:
                self.screen.display()
            self.but_cancel.set_label(gtk.STOCK_CLOSE)

        if res == gtk.RESPONSE_OK:
            self.screen.current_view.set_value()
            model = self.screen.current_model
            return (True, model)
        return (False, None)

    def destroy(self):
        self.screen.signal_unconnect(self)
        self.window.present()
        self.dia.destroy()
        self.screen.destroy()


class One2Many(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(One2Many, self).__init__(window, parent, model, attrs)

        self.widget = gtk.VBox(homogeneous=False, spacing=5)

        hbox = gtk.HBox(homogeneous=False, spacing=5)
        menubar = gtk.MenuBar()
        if hasattr(menubar, 'set_pack_direction') and \
                hasattr(menubar, 'set_child_pack_direction'):
            menubar.set_pack_direction(gtk.PACK_DIRECTION_LTR)
            menubar.set_child_pack_direction(gtk.PACK_DIRECTION_LTR)

        menuitem_title = gtk.ImageMenuItem(stock_id='gtk-preferences')

        menu_title = gtk.Menu()
        menuitem_set_to_default = gtk.MenuItem(_('Set to default value'), True)
        menuitem_set_to_default.connect('activate',
                lambda *x: self._menu_sig_default_get())
        menu_title.add(menuitem_set_to_default)
        menuitem_set_default = gtk.MenuItem(_('Set Default'), True)
        menuitem_set_default.connect('activate',
                lambda *x: self._menu_sig_default_set())
        menu_title.add(menuitem_set_default)
        menuitem_title.set_submenu(menu_title)

        menubar.add(menuitem_title)
        hbox.pack_start(menubar, expand=True, fill=True)

        tooltips = gtk.Tooltips()

        self.eb_new = gtk.EventBox()
        tooltips.set_tip(self.eb_new, _('Create a new entry'))
        self.eb_new.set_events(gtk.gdk.BUTTON_PRESS)
        self.eb_new.connect('button_press_event', self._sig_new)
        img_new = gtk.Image()
        img_new.set_from_stock('gtk-new', gtk.ICON_SIZE_MENU)
        img_new.set_alignment(0.5, 0.5)
        self.eb_new.add(img_new)
        hbox.pack_start(self.eb_new, expand=False, fill=False)

        self.eb_open = gtk.EventBox()
        tooltips.set_tip(self.eb_open, _('Edit this entry'))
        self.eb_open.set_events(gtk.gdk.BUTTON_PRESS)
        self.eb_open.connect('button_press_event', self._sig_edit)
        img_open = gtk.Image()
        img_open.set_from_stock('gtk-open', gtk.ICON_SIZE_MENU)
        img_open.set_alignment(0.5, 0.5)
        self.eb_open.add(img_open)
        hbox.pack_start(self.eb_open, expand=False, fill=False)

        self.eb_del = gtk.EventBox()
        tooltips.set_tip(self.eb_del, _('Remove this entry'))
        self.eb_del.set_events(gtk.gdk.BUTTON_PRESS)
        self.eb_del.connect('button_press_event', self._sig_remove)
        img_del = gtk.Image()
        img_del.set_from_stock('gtk-delete', gtk.ICON_SIZE_MENU)
        img_del.set_alignment(0.5, 0.5)
        self.eb_del.add(img_del)
        hbox.pack_start(self.eb_del, expand=False, fill=False)

        hbox.pack_start(gtk.VSeparator(), expand=False, fill=True)

        eb_pre = gtk.EventBox()
        tooltips.set_tip(eb_pre, _('Previous'))
        eb_pre.set_events(gtk.gdk.BUTTON_PRESS)
        eb_pre.connect('button_press_event', self._sig_previous)
        img_pre = gtk.Image()
        img_pre.set_from_stock('gtk-go-back', gtk.ICON_SIZE_MENU)
        img_pre.set_alignment(0.5, 0.5)
        eb_pre.add(img_pre)
        hbox.pack_start(eb_pre, expand=False, fill=False)

        self.label = gtk.Label('(0,0)')
        hbox.pack_start(self.label, expand=False, fill=False)

        eb_next = gtk.EventBox()
        tooltips.set_tip(eb_next, _('Next'))
        eb_next.set_events(gtk.gdk.BUTTON_PRESS)
        eb_next.connect('button_press_event', self._sig_next)
        img_next = gtk.Image()
        img_next.set_from_stock('gtk-go-forward', gtk.ICON_SIZE_MENU)
        img_next.set_alignment(0.5, 0.5)
        eb_next.add(img_next)
        hbox.pack_start(eb_next, expand=False, fill=False)

        hbox.pack_start(gtk.VSeparator(), expand=False, fill=True)

        eb_switch = gtk.EventBox()
        tooltips.set_tip(eb_switch, _('Switch'))
        eb_switch.set_events(gtk.gdk.BUTTON_PRESS)
        eb_switch.connect('button_press_event', self.switch_view)
        img_switch = gtk.Image()
        img_switch.set_from_stock('gtk-justify-left', gtk.ICON_SIZE_MENU)
        img_switch.set_alignment(0.5, 0.5)
        eb_switch.add(img_switch)
        hbox.pack_start(eb_switch, expand=False, fill=False)

        tooltips.enable()
        self.widget.pack_start(hbox, expand=False, fill=True)

        self.screen = Screen(attrs['relation'], self._window,
                view_type=attrs.get('mode','tree,form').split(','),
                parent=self.parent, views_preload=attrs.get('views', {}),
                tree_saves=attrs.get('saves', False), create_new=True,
                row_activate=self._on_activate,
                default_get=attrs.get('default_get', {}),
                exclude_field=attrs.get('relation_field', None))
        self.screen.signal_connect(self, 'record-message', self._sig_label)
        name = attrs.get('string', '')
        if name:
            name += ' - '
        name += self.screen.current_view.title
        menuitem_title.get_child().set_text(name)

        self.widget.pack_start(self.screen.widget, expand=True, fill=True)

        self.screen.widget.connect('key_press_event', self.on_keypress)

    def on_keypress(self, widget, event):
        if (event.keyval == gtk.keysyms.N \
                    and event.state & gtk.gdk.CONTROL_MASK \
                    and event.state & gtk.gdk.SHIFT_MASK) \
                or event.keyval == gtk.keysyms.F1:
            self._sig_new(widget, event)
            return False
        if event.keyval == gtk.keysyms.F2:
            self._sig_edit(widget, event)
            return False

    def destroy(self):
        self.screen.destroy()

    def _on_activate(self):
        self._sig_edit()

    def switch_view(self, btn, arg):
        self.screen.switch_view()

    def _readonly_set(self, value):
        self.eb_new.set_sensitive(not value)
        self.eb_del.set_sensitive(not value)

    def _sig_new(self, widget, event):
        ctx = self._view.model.expr_eval(self.screen.default_get)
        ctx.update(self._view.model.expr_eval('dict(%s)' % \
                self.attrs.get('context', '')))
        if event.type in (gtk.gdk.BUTTON_PRESS, gtk.gdk.KEY_PRESS):
            if (self.screen.current_view.view_type == 'form') \
                    or self.screen.editable_get():
                self.screen.new(context=ctx)
                self.screen.current_view.widget.set_sensitive(True)
            else:
                dia = Dialog(self.attrs['relation'], parent=self._view.model,
                        attrs=self.attrs,
                        model_ctx=self.screen.models._context,
                        default_get_ctx=ctx, window=self._window)
                res = True
                while res:
                    res, value = dia.run()
                    if res:
                        self.screen.models.model_add(value)
                        value.signal('record-changed', value.parent)
                        self.screen.display()
                        dia.new()
                dia.destroy()

    def _sig_edit(self, widget=None, event=None):
        if self.screen.current_model:
            dia = Dialog(self.attrs['relation'], parent=self._view.model,
                    model=self.screen.current_model, attrs=self.attrs,
                    window=self._window)
            res, value = dia.run()
            dia.destroy()

    def _sig_next(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.screen.display_next()

    def _sig_previous(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.screen.display_prev()

    def _sig_remove(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.screen.remove()
            if not self.screen.models.models:
                self.screen.current_view.widget.set_sensitive(False)

    def _sig_label(self, screen, signal_data):
        name = '_'
        if signal_data[0] >= 0:
            name = str(signal_data[0] + 1)
        line = '(%s/%s)' % (name, signal_data[1])
        self.label.set_text(line)

    def display(self, model, model_field):
        if not model_field:
            self.screen.current_model = None
            self.screen.display()
            return False
        super(One2Many, self).display(model, model_field)
        new_models = model_field.get_client(model)
        if self.screen.models != new_models:
            self.screen.models_set(new_models)
            if (self.screen.current_view.view_type == 'tree') \
                    and self.screen.editable_get():
                self.screen.current_model = None
        self.screen.display()
        return True

    def set_value(self, model, model_field):
        self.screen.current_view.set_value()
        if self.screen.is_modified():
            model.modified = True
            model.modified_fields.setdefault(model_field.name)
        return True
