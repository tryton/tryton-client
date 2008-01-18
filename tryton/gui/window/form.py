"Form"
import gettext
import gtk
import gobject
from gtk import glade
import gc
import tryton.rpc as rpc
import tryton.common as common
from tryton.gui.window.view_form.screen import Screen
from tryton.config import GLADE
from tryton.action import Action
from tryton.config import CONFIG
from tryton.gui.window.win_search import WinSearch
from tryton.gui.window.preference import Preference
from tryton.gui.window.win_export import WinExport
from tryton.gui.window.win_import import WinImport
from tryton.gui.window.attachment import Attachment

_ = gettext.gettext


class Form(object):
    "Form"

    def __init__(self, model, res_id=False, domain=None, view_type=None,
            view_ids=None, window=None, context=None, name=False, limit=80,
            auto_refresh=False):
        if not view_type:
            view_type = ['tree', 'form']
        if domain is None:
            domain = []
        if view_ids is None:
            view_ids = []
        if context is None:
            context = {}

        fields = {}
        self.model = model
        self.window = window
        self.previous_action = None
        self.glade = glade.XML(GLADE, 'win_form_container',
                gettext.textdomain())
        self.widget = self.glade.get_widget('win_form_container')
        self.widget.show_all()
        self.fields = fields
        self.domain = domain
        self.context = context

        self.screen = Screen(self.model, view_type=view_type,
                context=self.context, view_ids=view_ids, domain=domain,
                hastoolbar=CONFIG['form.toolbar'], show_search=True,
                window=self.window, limit=limit, readonly=bool(auto_refresh),
                form=self)
        self.screen.signal_connect(self, 'record-message', self._record_message)
        self.screen.widget.show()

        if not name:
            self.name = self.screen.current_view.title
        else:
            self.name = name
        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_NONE)
        viewport.add(self.screen.widget)
        viewport.show()
        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.set_shadow_type(gtk.SHADOW_NONE)
        self.scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
                gtk.POLICY_AUTOMATIC)
        self.scrolledwindow.add(viewport)
        self.scrolledwindow.show()

        self.has_backup = False
        self.backup = {}

        self.widget.pack_start(self.scrolledwindow)
        self.handlers = {
            'but_new': self.sig_new,
            'but_copy': self.sig_copy,
            'but_save': self.sig_save,
            'but_save_as': self.sig_save_as,
            'but_import': self.sig_import,
            'but_remove': self.sig_remove,
            'but_search': self.sig_search,
            'but_previous': self.sig_previous,
            'but_next': self.sig_next,
            'but_goto_id': self.sig_goto,
            'but_log': self.sig_logs,
            'but_print': self.sig_print,
            'but_reload': self.sig_reload,
            'but_action': self.sig_action,
            'but_switch': self.sig_switch,
            'but_attach': self.sig_attach,
            'but_close': self.sig_close,
        }
        if res_id:
            if isinstance(res_id, int):
                res_id = [res_id]
            self.screen.load(res_id)
        else:
            if self.screen.current_view.view_type == 'form':
                self.sig_new(None, autosave=False)
            if self.screen.current_view.view_type \
                    in ('tree', 'graph', 'calendar'):
                self.screen.search_filter()

        if auto_refresh and int(auto_refresh):
            gobject.timeout_add(int(auto_refresh) * 1000, self.sig_reload)

    def sig_goto(self, widget=None):
        if not self.modified_save():
            return
        glade2 = glade.XML(GLADE, 'dia_goto_id', gettext.textdomain())
        widget = glade2.get_widget('goto_spinbutton')
        win = glade2.get_widget('dia_goto_id')
        win.set_transient_for(self.window)
        win.show_all()

        response = win.run()
        win.destroy()
        if response == gtk.RESPONSE_OK:
            self.screen.load( [int(widget.get_value())] )

    def destroy(self):
        self.screen.signal_unconnect(self)
        self.screen.destroy()
        del self.screen
        del self.glade
        del self.widget
        self.scrolledwindow.destroy()
        del self.scrolledwindow
        gc.collect()

    def ids_get(self):
        return self.screen.ids_get()

    def id_get(self):
        return self.screen.id_get()

    def sig_attach(self, widget=None):
        obj_id = self.screen.id_get()
        if obj_id:
            win = Attachment(self.model, obj_id, self.window)
            win.run()
        else:
            self.message_state(_('No resource selected!'))
        return True

    def sig_switch(self, widget=None):
        if not self.modified_save():
            return
        self.screen.switch_view()

    def _id_get(self):
        return self.screen.id_get()

    def sig_logs(self, widget=None):
        obj_id = self._id_get()
        if not obj_id:
            self.message_state(_('You have to select one resource!'))
            return False

        fields = [
            ('id', _('ID')),
            ('create_uid', _('Creation User')),
            ('create_date', _('Creation Date')),
            ('write_uid', _('Latest Modification by')),
            ('write_date', _('Latest Modification Date')),
        ]

        res = rpc.session.rpc_exec_auth('/object', 'execute', self.model,
                'read', [obj_id], [x[0] for x in fields])
        message = ''
        for line in res:
            for (key, val) in fields:
                if line.get(key, False) and \
                        (key in ('create_uid', 'write_uid')):
                    line[key] = line[key][1]
                message += val+': ' + str(line.get(key, False) or '/')+'\n'
        common.message(message, self.window)
        return True

    def sig_remove(self, widget=None):
        if self.screen.current_view.view_type == 'form':
            msg = _('Are you sure to remove this record?')
        else:
            msg = _('Are you sure to remove those records?')
        if common.sur(msg, self.window):
            if not self.screen.remove(unlink=True):
                self.message_state(_('Resources not removed!'))
            else:
                self.message_state(_('Resources removed!'))

    def sig_import(self, widget=None):
        fields = []
        while(self.screen.view_to_load):
            self.screen.load_view_to_load()
        win = WinImport(self.model, self.screen.fields, fields,
                parent=self.window)
        win.run()

    def sig_save_as(self, widget=None):
        fields = []
        while(self.screen.view_to_load):
            self.screen.load_view_to_load()
        win = WinExport(self.model, self.screen.ids_get(),
                self.screen.fields, fields, parent=self.window)
        win.run()

    def sig_new(self, widget=None, autosave=True):
        if autosave:
            if not self.modified_save():
                return
        self.screen.new()
        self.message_state('')

    def sig_copy(self, widget=None):
        if not self.modified_save():
            return
        res_id = self._id_get()
        ctx = self.context.copy()
        ctx.update(rpc.session.context)
        new_id = rpc.session.rpc_exec_auth('/object', 'execute', self.model,
                'copy', res_id, {}, ctx)
        if new_id:
            self.screen.load([new_id])
            self.message_state(_('Working now on the duplicated document !'))

    def sig_save(self, widget=None):
        if self.screen.save_current():
            self.message_state(_('Document saved !'))
            return True
        else:
            self.message_state(_('Invalid form !'))
            return False

    def sig_previous(self, widget=None):
        if not self.modified_save():
            return
        self.screen.display_prev()
        self.message_state('')

    def sig_next(self, widget=None):
        if not self.modified_save():
            return
        self.screen.display_next()
        self.message_state('')

    def sig_reload(self, test_modified=True):
        if not hasattr(self, 'screen'):
            return False
        if test_modified and self.screen.is_modified():
            res = common.sur_3b(_('This record has been modified\n' \
                    'do you want to save it ?'), self.window)
            if res == 'ok':
                self.sig_save(None)
            elif res == 'ko':
                pass
            else:
                return False
        if self.screen.current_view.view_type == 'form':
            self.screen.cancel_current()
            self.screen.display()
        else:
            obj_id = self.screen.id_get()
            self.screen.search_filter()
            for model in self.screen.models:
                if model.id == obj_id:
                    self.screen.current_model = model
                    self.screen.display()
                    break
        self.message_state('')
        return True

    def sig_action(self, keyword='form_action'):
        ids = self.screen.ids_get()
        if self.screen.current_model:
            obj_id = self.screen.current_model.id
        else:
            obj_id = False
        if self.screen.current_view.view_type == 'form':
            obj_id = self.screen.save_current()
            if not obj_id:
                return False
            ids = [obj_id]
        if self.screen.current_view.view_type == 'tree':
            sel_ids = self.screen.current_view.sel_ids_get()
            if sel_ids:
                ids = sel_ids
        if len(ids):
            ctx = self.context.copy()
            if 'active_ids' in ctx:
                del ctx['active_ids']
            if 'active_id' in ctx:
                del ctx['active_id']
            res = Action.exec_keyword(keyword, {
                'model': self.screen.resource,
                'id': obj_id or False,
                'ids': ids,
                'window': self.window,
                }, context=ctx)
            if res:
                self.previous_action = res
            self.sig_reload(test_modified=False)
        else:
            self.message_state(_('No record selected!'), self.window)

    def sig_print(self):
        self.sig_action('form_print')

    def sig_search(self, widget=None):
        if not self.modified_save():
            return
        win = WinSearch(self.model, domain=self.domain,
                context=self.context, parent=self.window)
        res = win.run()
        if res:
            self.screen.clear()
            self.screen.load(res)

    def message_state(self, message, context='message'):
        statusbar = self.glade.get_widget('stat_state')
        cid = statusbar.get_context_id(context)
        statusbar.push(cid, message)

    def _record_message(self, screen, signal_data):
        if not signal_data[3]:
            msg = _('No record selected!')
        else:
            name = '_'
            if signal_data[0] >= 0:
                name = str(signal_data[0]+1)
            name2 = _('New document')
            if signal_data[3]:
                name2 = _('Editing document (id: ')+str(signal_data[3])+')'
            msg = _('Record: ') + name + ' / ' + str(signal_data[1]) + \
                    _(' of ') + str(signal_data[2]) + ' - ' + name2
        statusbar = self.glade.get_widget('stat_form')
        cid = statusbar.get_context_id('message')
        statusbar.push(cid, msg)

    def modified_save(self, reload=True):
        if self.screen.is_modified():
            value = common.sur_3b(
                    _('This record has been modified\n' \
                            'do you want to save it ?'),
                    self.window)
            if value == 'ok':
                return self.sig_save(None)
            elif value == 'ko':
                if reload:
                    self.sig_reload(test_modified=False)
                return True
            else:
                return False
        return True

    def sig_close(self):
        return self.modified_save(reload=False)
