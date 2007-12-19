import tryton.rpc as rpc
#import form
from preference import *


class Window(object):

    @staticmethod
    def create(view_ids, model, res_id=False, domain=None,
            view_type='form', window=None, context=None, mode=None, name=False,
            limit=80, auto_refresh=False):
        from tryton.gui import Main
        if context is None:
            context = {}
        context.update(rpc.session.context)

        if view_type == 'form':
            mode = (mode or 'form,tree').split(',')
            win = form.form(model, res_id, domain, view_type=mode,
                    view_ids = (view_ids or []), window=window,
                    context=context, name=name, limit=limit,
                    auto_refresh=auto_refresh)
            Main.get_main().win_add(win)
        elif view_type == 'tree':
            if view_ids and view_ids[0]:
                view_base =  rpc.session.rpc_exec_auth('/object', 'execute',
                        'ir.ui.view', 'read', [view_ids[0]],
                        ['model', 'type'], context)[0]
                model = view_base['model']
                view = rpc.session.rpc_exec_auth('/object', 'execute',
                        view_base['model'], 'fields_view_get', view_ids[0],
                        view_base['type'],context)
            else:
                view = rpc.session.rpc_exec_auth('/object', 'execute', model,
                        'fields_view_get', False, view_type, context)

            from tree import Tree
            win = Tree(view, model, res_id, domain, context,
                    window=window, name=name)
            Main.get_main().win_add(win)
        else:
            import logging
            log = logging.getLogger('view')
            log.error('unknown view type: '+view_type)
            del log
