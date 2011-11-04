#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
'Action'
import gtk
from tryton.gui.window.view_form.screen import Screen
import tryton.rpc as rpc
import time
import datetime
from tryton.gui.window.win_search import WinSearch
from tryton.action import Action as Action2
import tryton.common as common
from tryton.pyson import PYSONDecoder
import gettext
from tryton.config import CONFIG
from tryton.signal_event import SignalEvent
from tryton.exceptions import TrytonServerError
_ = gettext.gettext


class Action(SignalEvent):

    def __init__(self, attrs=None, context=None):
        super(Action, self).__init__()
        self.act_id = int(attrs['name'])
        self.context = context or {}

        try:
            self.action = rpc.execute('model', 'ir.action.act_window', 'read',
                    self.act_id, False, rpc.CONTEXT)
        except TrytonServerError, exception:
            common.process_exception(exception)
            raise

        view_ids = None
        self.action['view_mode'] = None
        if self.action.get('views', []):
            view_ids = [x[0] for x in self.action['views']]
            self.action['view_mode'] = [x[1] for x in self.action['views']]
        elif self.action.get('view_id', False):
            view_ids = [self.action['view_id'][0]]

        if 'view_mode' in attrs:
            self.action['view_mode'] = attrs['view_mode']

        self.action.setdefault('pyson_domain', '[]')
        self.context.update(rpc.CONTEXT)
        self.context['_user'] = rpc._USER
        self.context.update(PYSONDecoder(self.context).decode(
            self.action.get('pyson_context', '{}')))

        eval_ctx = self.context.copy()
        self.context.update(PYSONDecoder(eval_ctx).decode(
            self.action.get('pyson_context', '{}')))

        self.domain = []
        self.update_domain([])

        search_context = self.context.copy()
        search_context['context'] = self.context
        search_context['_user'] = rpc._USER
        search_value = PYSONDecoder(search_context).decode(
            self.action['pyson_search_value'] or '{}')

        self.widget = gtk.Frame()
        self.widget.set_border_width(0)

        vbox = gtk.VBox(homogeneous=False, spacing=3)
        hbox = gtk.HBox(homogeneous=False, spacing=0)
        vbox.pack_start(hbox, expand=False, fill=True)
        self.widget.add(vbox)

        self.title = gtk.Label()
        self.widget.set_label_widget(self.title)
        self.widget.set_label_align(0.0, 0.5)

        tooltips = common.Tooltips()

        label = gtk.Label(_('Search'))
        label.set_alignment(0.0, 0.5)
        hbox.pack_start(label, expand=False, fill=False, padding=5)

        self.search_entry = gtk.Entry()
        self.search_entry.set_alignment(0.0)
        self.completion = gtk.EntryCompletion()
        self.completion.set_model(gtk.ListStore(str))
        self.completion.set_text_column(0)
        self.completion.set_match_func(lambda *a: True, None)
        self.search_entry.connect_after('activate', self.do_search)
        self.search_entry.set_completion(self.completion)
        self.search_entry.connect('changed', self.changed)

        hbox.pack_start(self.search_entry, expand=True, fill=True, padding=5)

        but_search = gtk.Button()
        tooltips.set_tip(but_search, _('Search'))
        but_search.connect('clicked', self.do_search)
        img_search = gtk.Image()
        img_search.set_from_stock('tryton-find',
                gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_search.set_alignment(0.5, 0.5)
        but_search.add(img_search)
        but_search.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_search, expand=False, fill=False)

        but_clear = gtk.Button()
        tooltips.set_tip(but_clear, _('Clear'))
        but_clear.connect('clicked', lambda *a: self.search_entry.set_text(''))
        img_clear = gtk.Image()
        img_clear.set_from_stock('tryton-clear', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_clear.set_alignment(0.5, 0.5)
        but_clear.add(img_clear)
        but_clear.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_clear, expand=False, fill=False)

        hbox.pack_start(gtk.VSeparator(), expand=False, fill=True)
        but_open = gtk.Button()
        tooltips.set_tip(but_open, _('Open'))
        but_open.connect('clicked', self._sig_open)
        img_open = gtk.Image()
        img_open.set_from_stock('tryton-open', gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_open.set_alignment(0.5, 0.5)
        but_open.add(img_open)
        but_open.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_open, expand=False, fill=False)


        hbox.pack_start(gtk.VSeparator(), expand=False, fill=True)
        but_previous = gtk.Button()
        tooltips.set_tip(but_previous, _('Previous'))
        but_previous.connect('clicked', self._sig_previous)
        img_previous = gtk.Image()
        img_previous.set_from_stock('tryton-go-previous',
                gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_previous.set_alignment(0.5, 0.5)
        but_previous.add(img_previous)
        but_previous.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_previous, expand=False, fill=False)

        self.label = gtk.Label('(0,0)')
        hbox.pack_start(self.label, expand=False, fill=False)

        but_next = gtk.Button()
        tooltips.set_tip(but_next, _('Next'))
        but_next.connect('clicked', self._sig_next)
        img_next = gtk.Image()
        img_next.set_from_stock('tryton-go-next',
                gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_next.set_alignment(0.5, 0.5)
        but_next.add(img_next)
        but_next.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_next, expand=False, fill=False)

        hbox.pack_start(gtk.VSeparator(), expand=False, fill=True)

        but_switch = gtk.Button()
        tooltips.set_tip(but_switch, _('Switch'))
        but_switch.connect('clicked', self._sig_switch)
        img_switch = gtk.Image()
        img_switch.set_from_stock('tryton-fullscreen',
                gtk.ICON_SIZE_SMALL_TOOLBAR)
        img_switch.set_alignment(0.5, 0.5)
        but_switch.add(img_switch)
        but_switch.set_relief(gtk.RELIEF_NONE)
        hbox.pack_start(but_switch, expand=False, fill=False)

        vbox.pack_start(gtk.HSeparator(), expand=False, fill=True)

        hbox.set_focus_chain([self.search_entry])

        self.widget.show_all()

        self.screen = Screen(self.action['res_model'],
            mode=self.action['view_mode'],
            context=self.context, view_ids=view_ids,
            domain=self.domain, readonly=True, alternate_view=True,
            search_value=search_value)
        vbox.pack_start(self.screen.screen_container.alternate_viewport,
            expand=True, fill=True)
        name = self.screen.current_view.title
        self.screen.signal_connect(self, 'record-message', self._sig_label)
        self.screen.signal_connect(self, 'record-message',
                self._active_changed)

        if attrs.get('string'):
            self.title.set_text(attrs['string'])
        elif self.action.get('window_name'):
            self.title.set_text(self.action['name'])
        else:
            self.title.set_text(name)

        self.widget.set_size_request(int(attrs.get('width',-1)),
                int(attrs.get('height', -1)))

        self.screen.search_filter()
        self.search_entry.set_text(self.screen.screen_container.get_text())

    def get_text(self):
        return self.search_entry.get_text().strip().decode('utf-8')

    def changed(self, editable):
        res = self.screen.search_complete(self.get_text())
        model = self.completion.get_model()
        model.clear()
        for r in res:
            model.append([r.strip()])

    def _sig_switch(self, widget):
        self.screen.switch_view()

    def do_search(self, widget=None):
        self.screen.search_filter(self.get_text())
        self.search_entry.set_text(self.screen.screen_container.get_text())

    def _sig_open(self, widget):
        try:
            action_id = rpc.execute('model', 'ir.action',
                    'get_action_id', self.act_id, rpc.CONTEXT)
        except TrytonServerError, exception:
            common.process_exception(exception)
        if action_id:
            Action2.execute(action_id, {})

    def _sig_previous(self, widget):
        self.screen.display_prev()

    def _sig_next(self, widget):
        self.screen.display_next()

    def _sig_label(self, screen, signal_data):
        name = '_'
        if signal_data[0]:
            name = str(signal_data[0])
        line = '(%s/%s)' % (name, signal_data[1])
        self.label.set_text(line)

    def set_value(self, mode, model_field):
        self.screen.current_view.set_value()
        return True

    def display(self):
        self.do_search()

    def _active_changed(self, *args):
        self.signal('active-changed')

    def _get_active(self):
        if self.screen and self.screen.current_record:
            return common.EvalEnvironment(self.screen.current_record, False)

    active = property(_get_active)

    def update_domain(self, actions):
        domain_ctx = self.context.copy()
        domain_ctx['context'] = domain_ctx
        domain_ctx['_user'] = rpc._USER
        for action in actions:
            if action.active:
                domain_ctx['_active_%s' % action.act_id] = action.active
        new_domain = PYSONDecoder(domain_ctx).decode(
                self.action['pyson_domain'])
        if self.domain == new_domain:
            return
        del self.domain[:]
        self.domain.extend(new_domain)
        if hasattr(self, 'screen'): # Catch early update
            self.do_search()
