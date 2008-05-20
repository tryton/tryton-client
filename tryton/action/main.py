import time
import datetime
import tryton.rpc as rpc
from tryton.wizard import Wizard
from tryton.common import message, error, selection, file_open
from tryton.gui.window import Window
import gettext
import tempfile
import base64
import os
import webbrowser

_ = gettext.gettext

class Action(object):

    @staticmethod
    def exec_report(name, data, context=None):
        from tryton.gui import Main
        if context is None:
            context = {}
        datas = data.copy()
        ids = datas['ids']
        del datas['ids']
        if not ids:
            try:
                ids = rpc.execute('object', 'execute', datas['model'],
                        'search', [])
            except Exception, exception:
                ids = rpc.process_exception(exception, Main.get_main().window,
                        'object', 'execute', datas['model'], 'search', [])
                if not ids:
                    return False
            if ids == []:
                message(_('Nothing to print!'), Main.get_main().window)
                return False
            datas['id'] = ids[0]
        ctx = rpc.CONTEXT.copy()
        ctx.update(context)
        try:
            res = rpc.execute('report', 'execute', name, ids, datas, ctx)
        except Exception, exception:
            res = rpc.process_exception(exception, Main.get_main().window,
                    'report', 'execute', name, ids, datas, ctx)
            if not res:
                return False
        if not res:
            return False
        (type, data, print_p) = res
        (fileno, fp_name) = tempfile.mkstemp('.' + type, 'tryton_')
        file_d = os.fdopen(fileno, 'wb+')
        file_d.write(base64.decodestring(data))
        file_d.close()
        file_open(fp_name, type, Main.get_main().window, print_p=print_p)
        return True

    @staticmethod
    def execute(act_id, datas, action_type=None, context=None):
        from tryton.gui import Main
        if context is None:
            context = {}
        ctx = rpc.CONTEXT.copy()
        ctx.update(context)
        if not action_type:
            res = False
            try:
                res = rpc.execute('object', 'execute', 'ir.action', 'read',
                        act_id, ['type'], ctx)
            except Exception, exception:
                rpc.process_exception(exception, Main.get_main().window)
                return
            if not res:
                raise Exception, 'ActionNotFound'
            action_type = res['type']
        try:
            act_id2 = rpc.execute('object', 'execute', action_type,
                'search', [('action', '=', act_id)], 0, None, None, ctx)[0]
        except Exception, exception:
            rpc.process_exception(exception, Main.get_main().window)
            return
        try:
            res = rpc.execute('object', 'execute', action_type,
                'read', act_id2, False, ctx)
        except Exception, exception:
            rpc.process_exception(exception, Main.get_main().window)
            return
        Action._exec_action(res, datas)

    @staticmethod
    def _exec_action(action, datas=None, context=None):
        if context is None:
            context = rpc.CONTEXT.copy()
        if datas is None:
            datas = {}
        if 'type' not in action:
            return
        from tryton.gui import Main
        win = Main.get_main().window
        if 'window' in datas:
            win = datas['window']
            del datas['window']

        if action['type'] == 'ir.action.act_window':
            for key in (
                    'res_id',
                    'res_model',
                    'view_type',
                    'limit',
                    'auto_refresh',
                    ):
                datas[key] = action.get(key, datas.get(key, None))

            view_ids = False
            datas['view_mode'] = None
            if action.get('views', []):
                view_ids = [x[0] for x in action['views']]
                datas['view_mode'] = [x[1] for x in action['views']]
            elif action.get('view_id', False):
                view_ids = [action['view_id'][0]]

            if not action.get('domain', False):
                action['domain'] = '[]'
            ctx = {
                'active_id': datas.get('id',False),
                'active_ids': datas.get('ids',[]),
                'user': rpc._USER,
            }
            eval_ctx = ctx.copy()
            eval_ctx['datetime'] = datetime
            ctx.update(eval(action.get('context','{}'), eval_ctx))
            ctx.update(context)

            domain_context = ctx.copy()
            domain_context['time'] = time
            domain_context['datetime'] = datetime
            domain = eval(action['domain'], domain_context)

            if datas.get('domain', False):
                domain.append(datas['domain'])

            name = False
            if action.get('window_name', True):
                name = action.get('name', False)

            Window.create(view_ids, datas['res_model'], datas['res_id'], domain,
                    action['view_type'], win, ctx,
                    datas['view_mode'], name=name,
                    limit=datas['limit'], auto_refresh=datas['auto_refresh'])
        elif action['type'] == 'ir.action.wizard':
            Wizard.execute(action['wiz_name'], datas, win,
                    context=context)

        elif action['type'] == 'ir.action.report':
            Action.exec_report(action['report_name'], datas)

        elif action['type'] == 'ir.action.url':
            if action['url']:
                webbrowser.open(action['url'], new=2)

    @staticmethod
    def exec_keyword(keyword, data=None, context=None, warning=True,
            alwaysask=False):
        from tryton.gui import Main
        actions = []
        if 'id' in data:
            model_id = data.get('id', False)
            try:
                actions = rpc.execute('object', 'execute',
                        'ir.action.keyword', 'get_keyword', keyword,
                        (data['model'], model_id))
            except Exception, exception:
                from tryton.gui import Main
                rpc.process_exception(exception, Main.get_main().window)
                return False

        keyact = {}
        for action in actions:
            keyact[action['name']] = action

        from tryton.gui import Main
        res = selection(_('Select your action'), keyact, Main.get_main().window,
                alwaysask=alwaysask)
        if res:
            (name, action) = res
            Action._exec_action(action, data, context=context)
            return (name, action)
        elif not len(keyact) and warning:
            message(_('No action defined!'), Main.get_main().window)
        return False
