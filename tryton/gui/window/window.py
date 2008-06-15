import tryton.rpc as rpc
from preference import *


class Window(object):

    @staticmethod
    def create(view_ids, model, res_id=False, domain=None,
            view_type='form', window=None, context=None, mode=None, name=False,
            limit=None, auto_refresh=False):
        from tryton.gui import Main
        if context is None:
            context = {}
        context.update(rpc.CONTEXT)

        if view_type == 'form':
            from form import Form
            win = Form(model, window, res_id, domain, view_type=mode,
                    view_ids = (view_ids or []), context=context, name=name,
                    limit=limit, auto_refresh=auto_refresh)
            Main.get_main().win_add(win)
        elif view_type == 'tree':
            from tree import Tree
            win = Tree(model, window, res_id, view_ids and view_ids[0] or None,
                    domain, context, name=name)
            Main.get_main().win_add(win)
        elif view_type == 'board':
            from board import Board
            win = Board(window, view_ids[0], context=context, name=name,
                    auto_refresh=auto_refresh)
            Main.get_main().win_add(win)
        else:
            import logging
            log = logging.getLogger('view')
            log.error('unknown view type: '+view_type)
            del log
