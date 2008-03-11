from interface import WidgetInterface
from tryton.gui.window.view_form.screen import Screen
import tryton.rpc as rpc
import time
import datetime
from tryton.gui.window.win_search import WinSearch
from tryton.action import Action as Action2


class Action(WidgetInterface):

    def __init__(self, window, parent, model, attrs=None):
        super(Action, self).__init__(window, parent, model, attrs)

        self.act_id = attrs['name']
        try:
            res = rpc.execute('object', 'execute',
                    'ir.actions.actions', 'read', [self.act_id], ['type'],
                    rpc.CONTEXT)
        except Exception, exception:
            rpc.process_exception(exception, self._window)
            raise
        if not res:
            raise Exception('ActionNotFound')

        atype = res[0]['type']
        try:
            self.action = rpc.execute('object', 'execute', atype,
                    'read', self.act_id, False, rpc.CONTEXT)
        except Exception, exception:
            rpc.process_exception(exception, self._window)
            raise
        if 'view_mode' in attrs:
            self.action['view_mode'] = attrs['view_mode']

        if self.action['type'] == 'ir.actions.act_window':
            self.action.setdefault('domain', '[]')
            self.context = {'active_id': False, 'active_ids': []}
            self.context.update(eval(self.action.get('context', '{}'),
                self.context.copy()))
            ctx = self.context.copy()
            ctx['time'] = time
            ctx['datetime'] = datetime
            self.domain = eval(self.action['domain'], ctx)

            view_id = []
            if self.action['view_id']:
                view_id = [self.action['view_id'][0]]
            if self.action['view_type'] == 'form':
                mode = (self.action['view_mode'] or 'form,tree').split(',')
                self.screen = Screen(self.action['res_model'], self._window,
                        view_type=mode, context=self.context, view_ids=view_id,
                        domain=self.domain)
#                self.win_gl = glade.XML(common.terp_path("terp.glade"),
#                        'widget_paned', gettext.textdomain())
#
#                self.win_gl.signal_connect(
#                       'on_switch_button_press_event',
#                       self._sig_switch)
#                self.win_gl.signal_connect(
#                       'on_search_button_press_event',
#                       self._sig_search)
#                self.win_gl.signal_connect(
#                       'on_open_button_press_event', self._sig_open)
#                label=self.win_gl.get_widget('widget_paned_lab')
#                label.set_text(attrs.get('string',
#                       self.screen.current_view.title))
#                vbox=self.win_gl.get_widget('widget_paned_vbox')
#                vbox.add(self.screen.widget)
#                self.widget=self.win_gl.get_widget('widget_paned')
#                self.widget.set_size_request(
#                       int(attrs.get('width', -1)),
#                       int(attrs.get('height', -1)))
            elif self.action['view_type']=='tree':
                pass #TODO

    def _sig_switch(self, *args):
        self.screen.switch_view()

    def _sig_search(self, *args):
        win = WinSearch(self.action['res_model'], domain=self.domain,
                context=self.context)
        res = win.run()
        if res:
            self.screen.clear()
            self.screen.load(res)

    def _sig_open(self, *args):
        Action2.execute(self.act_id, {})

    def set_value(self, mode, model_field):
        self.screen.current_view.set_value()
        return True

    def display(self, model, model_field):
        try:
            res_id = rpc.execute('object', 'execute',
                    self.action['res_model'], 'search', self.domain, 0,
                    self.action.get('limit', 80))
        except Exception, exception:
            rpc.process_exception(exception, self._window)
            return False
        self.screen.clear()
        self.screen.load(res_id)
        return True
