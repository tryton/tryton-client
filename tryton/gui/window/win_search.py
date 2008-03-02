import gtk
import gettext
import tryton.rpc as rpc
from tryton.gui.window.view_form.screen import Screen
import tryton.gui.window.view_form.widget_search as widget_search
from tryton.config import TRYTON_ICON, GLADE

_ = gettext.gettext


class WinSearch(object):

    def __init__(self, model, sel_multi=True, ids=None, context=None,
            domain=None, parent=None):
        self.domain = domain or []
        self.context = context or {}
        self.context.update(rpc.CONTEXT)
        self.sel_multi = sel_multi
        self.parent = parent

        self.win = gtk.Dialog(_('Tryton - Search'), self.parent,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_FIND, gtk.RESPONSE_APPLY,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.win.set_icon(TRYTON_ICON)
        self.win.set_default_response(gtk.RESPONSE_APPLY)
        hbox = gtk.HBox()
        hbox.show()
        self.win.vbox.pack_start(hbox, expand=False, fill=True)
        self.win.vbox.pack_start(gtk.HSeparator(), expand=False, fill=True)
        scrollwindow = gtk.ScrolledWindow()
        scrollwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.win.vbox.pack_start(scrollwindow, expand=True, fill=True)

        self.screen = Screen(model, view_type=['tree'], context=context,
                parent=self.win)
        self.view = self.screen.current_view
        self.view.unset_editable()
        sel = self.view.widget_tree.get_selection()

        if not sel_multi:
            sel.set_mode(gtk.SELECTION_SINGLE)
        else:
            sel.set_mode(gtk.SELECTION_MULTIPLE)
        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        viewport.add(self.screen.widget)
        scrollwindow.add(viewport)
        scrollwindow.show_all()
        self.view.widget_tree.connect('row_activated', self.sig_activate)
        self.view.widget_tree.connect('button_press_event', self.sig_button)

        self.model_name = model

        try:
            view_form = rpc.execute('object', 'execute',
                    self.model_name, 'fields_view_get', False, 'tree',
                    self.context)
        except Exception, exception:
            rpc.process_exception(exception, self.parent)
            raise
        self.form = widget_search.Form(view_form['arch'], view_form['fields'],
                model, parent=self.win)

        self.title = _('Tryton Search: %s') % self.form.name
        self.title_results = _('Tryton Search: %s (%%d result(s))') % \
                self.form.name
        self.win.set_title(self.title)

        hbox.pack_start(self.form.widget)
        self.ids = ids
        if self.ids:
            self.reload()
        self.old_search = None
        self.old_offset = self.old_limit = None
        if self.ids:
            self.old_search = []
            self.old_limit = self.form.get_limit()
            self.old_offset = self.form.get_offset()

        self.view.widget.show_all()
        if self.form.focusable:
            self.form.focusable.grab_focus()

        self.win.set_size_request(700, 500)

    def sig_activate(self, *args):
        self.view.widget_tree.emit_stop_by_name('row_activated')
        if not self.sel_multi:
            self.win.response(gtk.RESPONSE_OK)
        return False

    def sig_button(self, view, event):
        if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
            self.win.response(gtk.RESPONSE_OK)
        return False

    def find(self, *args):
        limit = self.form.get_limit()
        offset = self.form.get_offset()
        if (self.old_search == self.form.value) \
                and (self.old_limit==limit) \
                and (self.old_offset==offset):
            self.win.response(gtk.RESPONSE_OK)
            return False
        self.old_offset = offset
        self.old_limit = limit
        value = self.form.value
        value += self.domain
        try:
            self.ids = rpc.execute('object', 'execute',
                    self.model_name, 'search', value, offset, limit, 0,
                    rpc.CONTEXT)
        except Exception, exception:
            rpc.process_exception(exception, self.win)
            return False
        self.reload()
        self.old_search = self.form.value
        self.win.set_title(self.title_results % len(self.ids))
        return True

    def reload(self):
        self.screen.clear()
        self.screen.load(self.ids)
        sel = self.view.widget_tree.get_selection()
        if sel.get_mode() == gtk.SELECTION_MULTIPLE:
            sel.select_all()

    def sel_ids_get(self):
        return self.screen.sel_ids_get()

    def destroy(self):
        self.parent.present()
        self.win.destroy()

    def run(self):
        end = False
        while not end:
            button = self.win.run()
            if button == gtk.RESPONSE_OK:
                res = self.sel_ids_get() or self.ids
                end = True
            elif button == gtk.RESPONSE_APPLY:
                end = not self.find()
                if end:
                    res = self.sel_ids_get() or self.ids
            else:
                res = None
                end = True
        self.destroy()
        return res
