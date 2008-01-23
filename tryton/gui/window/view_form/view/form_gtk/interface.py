import gtk
from gtk import glade
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
from tryton.common import warning, COLORS
from tryton.config import GLADE, TRYTON_ICON
import gettext

_ = gettext.gettext

_ATTRS_BOOLEAN = {
    'required': False,
    'readonly': False
}

def field_pref_set(field, name, model, value, dependance=None, window=None):
    win_gl = glade.XML(GLADE, 'win_field_pref', gettext.textdomain())
    if dependance is None:
        dependance = []
    win = win_gl.get_widget('win_field_pref')
    win.set_transient_for(window)
    win.set_icon(TRYTON_ICON)
    ent = win_gl.get_widget('ent_field')
    ent.set_text(name)
    ent = win_gl.get_widget('ent_domain')
    ent.set_text(model)
    ent = win_gl.get_widget('ent_value')
    ent.set_text((value and str(value)) or '/')

    radio = win_gl.get_widget('radio_user_pref')

    vbox = win_gl.get_widget('pref_vbox')
    widgets = {}
    addwidget = False
    widget = None
    if dependance:
        widget = gtk.RadioButton(widget, _('Always'))
        vbox.pack_start(widget)
    for (fname, name, fvalue, value) in dependance:
        if fvalue:
            addwidget = True
            widget = gtk.RadioButton(widget, name+' = '+str(value))
            widgets[(fname, fvalue)] = widget
            vbox.pack_start(widget)
    if not len(dependance) or not addwidget:
        vbox.pack_start(gtk.Label(_('Always applicable !')))
    vbox.show_all()

    res = win.run()

    clause = False
    for val in widgets.keys():
        if widgets[val].get_active():
            clause = val[0] + '=' + str(val[1])
            break
    user = False
    if radio.get_active():
        user = rpc.session.user
    window.present()
    win.destroy()
    if res == gtk.RESPONSE_OK:
        ir_default = RPCProxy('ir.default')
        ir_default.set_default(model, field, clause, value, user,
                rpc.session.context)
        return True
    return False


class WidgetInterface(object):

    def __init__(self, window, parent=None, model=None, attrs=None):
        if attrs is None:
            attrs = {}
        self.parent = parent
        self.model = model
        self._window = window
        self._view = None
        self.attrs = attrs
        for key, val in _ATTRS_BOOLEAN.items():
            self.attrs[key] = attrs.get(key, False) not in ('False', '0', False)
        self.default_readonly = self.attrs.get('readonly', False)
        self._menu_entries = [
            (_('Set to default value'),
                lambda x: self._menu_sig_default_get(), 1),
            (_('Set as default'),
                lambda x: self._menu_sig_default_set(), 1),
        ]
        self.widget = None

    def destroy(self):
        pass

    def _menu_sig_default_get(self):
        try:
            if self._view.modelfield.get_state_attrs(self._view.model)\
                    .get('readonly', False):
                return False
            model = self._view.modelfield.parent.resource
            res = rpc.session.rpc_exec_auth_try('/object', 'execute', model,
                    'default_get', [self.attrs['name']])
            self._view.modelfield.set(self._view.model,
                    res.get(self.attrs['name'], False))
            self.display(self._view.model, self._view.modelfield)
        except:
            warning(_('You can not set to the default value here!'),
                    _('Operation not permited'))
            return False

    def sig_activate(self, widget=None):
        # emulate a focus_out so that the onchange is called if needed
        self._focus_out()

    def _readonly_set(self, readonly):
        pass

    def _color_widget(self):
        return self.widget

    def color_set(self, name):
        widget = self._color_widget()
        colormap = widget.get_colormap()
        colour = colormap.alloc_color(COLORS.get(name,'white'))
        widget.modify_bg(gtk.STATE_ACTIVE, colour)
        widget.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        widget.modify_base(gtk.STATE_NORMAL, colour)
        widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        widget.modify_text(gtk.STATE_INSENSITIVE, gtk.gdk.color_parse("black"))

    def _menu_sig_default_set(self):
        deps = []
        for wname, wview in self._view.view_form.widgets.items():
            if wview.modelfield.attrs.get('change_default', False):
                wvalue = wview.modelfield.get(self._view.model)
                name = wview.modelfield.attrs.get('string', wname)
                value = wview.modelfield.get_client(self._view.model)
                deps.append((wname, name, wvalue, value))
        value = self._view.modelfield.get_default(self._view.model)
        model = self._view.modelfield.parent.resource
        field_pref_set(self._view.widget_name,
                self.attrs.get('string', self._view.widget_name), model,
                value, deps, window=self._window)

    def _menu_open(self, obj, event):
        if event.button == 3:
            menu = gtk.Menu()
            for stock_id, callback, sensitivity in self._menu_entries:
                if stock_id:
                    item = gtk.ImageMenuItem(stock_id)
                    if callback:
                        item.connect("activate", callback)
                    item.set_sensitive(sensitivity)
                else:
                    item = gtk.SeparatorMenuItem()
                item.show()
                menu.append(item)
            menu.popup(None, None, None, event.button, event.time)
            return True

    def _focus_in(self):
        pass

    def _focus_out(self):
        if not self._view.modelfield:
            return False
        self.set_value(self._view.model, self._view.modelfield)

    def display(self, model, modelfield):
        if not modelfield:
            self._readonly_set(self.attrs.get('readonly', False))
            return
        self._readonly_set(modelfield.get_state_attrs(model).\
                get('readonly', False))
        if modelfield.get_state_attrs(model).get('readonly', False):
            self.color_set('readonly')
        elif not modelfield.get_state_attrs(model).get('valid', True):
            self.color_set('invalid')
        elif modelfield.get_state_attrs(model).get('required', False):
            self.color_set('required')
        else:
            self.color_set('normal')

    def sig_changed(self):
        if self.attrs.get('on_change', False):
            self._view.view_form.screen.on_change(self.attrs['on_change'])

    def set_value(self, model, model_field):
        pass
