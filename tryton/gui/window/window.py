import tryton.rpc as rpc
from preference import *


class Window(object):

    @staticmethod
    def create(view_ids, model, res_id=False, domain=None,
            view_type='form', window=None, context=None, mode=None, name=False,
            limit=80, auto_refresh=False):
        from tryton.gui import Main
        if context is None:
            context = {}
        context.update(rpc.CONTEXT)

        if view_type == 'form':
            from form import Form
            win = Form(model, res_id, domain, view_type=mode,
                    view_ids = (view_ids or []), window=window,
                    context=context, name=name, limit=limit,
                    auto_refresh=auto_refresh)
            Main.get_main().win_add(win)
        elif view_type == 'tree':
            from tree import Tree
            win = Tree(model, res_id, view_ids and view_ids[0] or None, domain,
                    context, window=window, name=name)
            Main.get_main().win_add(win)
        else:
            import logging
            log = logging.getLogger('view')
            log.error('unknown view type: '+view_type)
            del log
