"View tree"
import gtk
import gobject
from tryton.config import CONFIG
import time
import math
import tryton.rpc as rpc
from parse import Parse
import datetime as DT
import locale
from tryton.common import DT_FORMAT, DHM_FORMAT

if not hasattr(locale, 'nl_langinfo'):
    locale.nl_langinfo = lambda *a: '%x'

if not hasattr(locale, 'D_FMT'):
    locale.D_FMT = None

FIELDS_LIST_TYPE = {
    'checkbox': gobject.TYPE_BOOLEAN,
    'integer': gobject.TYPE_INT,
}


class ViewTreeModel(gtk.GenericTreeModel, gtk.TreeSortable):
    """
    BUG: ids = []

    Tree struct:  [ id, values, childs, childs_id ]

       values: [...]
       childs: [ tree_struct ]
               [] for no childs
               None for undevelopped (with childs!)
           assert: no childs => []

    Node struct: [list of (pos, list) ]
    """

    def __init__(self, ids, view, fields, fields_type, context=None,
            pixbufs=None, treeview=None):
        gtk.GenericTreeModel.__init__(self)
        self.fields = fields
        self.fields_type = fields_type
        self.view = view
        self.roots = ids
        self.context = context or {}
        self.tree = self._node_process(self.roots)
        self.pixbufs = pixbufs or {}
        self.treeview = treeview

    def _read(self, ids, fields):
        ctx = {}
        ctx.update(rpc.session.context)
        ctx.update(self.context)
        try:
            res_ids = rpc.session.rpc_exec_auth_try('/object', 'execute',
                    self.view['model'], 'read', ids, fields, ctx)
        except:
            res_ids = []
            for obj_id in ids:
                val = {'id': obj_id}
                for field in fields:
                    if self.fields_type[field]['type'] \
                            in ('one2many', 'many2many'):
                        val[field] = []
                    else:
                        val[field] = ''
                res_ids.append(val)
        for field in self.fields:
            if self.fields_type[field]['type'] in ('date',):
                display_format = locale.nl_langinfo(locale.D_FMT).replace('%y',
                        '%Y')
                for obj in res_ids:
                    if obj[field]:
                        date = time.strptime(obj[field], DT_FORMAT)
                        obj[field] = time.strftime(display_format, date)
            if self.fields_type[field]['type'] in ('datetime',):
                display_format = locale.nl_langinfo(locale.D_FMT).replace('%y',
                        '%Y') + ' %H:%M:%S'
                for obj in res_ids:
                    if obj[field]:
                        date = time.strptime(obj[field], DHM_FORMAT)
                        if 'timezone' in rpc.session.context:
                            try:
                                import pytz
                                lzone = pytz.timezone(rpc.session.context['timezone'])
                                szone = pytz.timezone(rpc.session.timezone)
                                datetime = DT.datetime(date[0], date[1],
                                        date[2], date[3], date[4], date[5],
                                        date[6])
                                sdt = szone.localize(datetime, is_dst=True)
                                ldt = sdt.astimezone(lzone)
                                date = ldt.timetuple()
                            except:
                                pass
                        obj[field] = time.strftime(display_format, date)
            if self.fields_type[field]['type'] in ('one2one','many2one'):
                for obj in res_ids:
                    if obj[field]:
                        obj[field] = obj[field][1]
            if self.fields_type[field]['type'] in ('selection'):
                for obj in res_ids:
                    if obj[field]:
                        obj[field] = dict(self.fields_type[field]['selection']
                                ).get(obj[field],'')
            if self.fields_type[field]['type'] in ('float',):
                digit = self.fields_type[field].get('digits', (16, 2))[1]
                for obj in res_ids:
                    obj[field] = locale.format('%.' + str(digit) + 'f',
                            obj[field] or 0.0, True)
            if self.fields_type[field]['type'] in ('float_time',):
                for obj in res_ids:
                    val = '%02d:%02d' % (math.floor(abs(obj[field])),
                            round(abs(obj[field]) % 1 + 0.01, 2) * 60)
                    if obj[field] < 0:
                        val = '-' + val
                    obj[field] = val
        return res_ids

    def _node_process(self, ids):
        tree = []
        if self.view.get('field_parent', False):
            res = self._read(ids, self.fields+[self.view['field_parent']])
            for obj in res:
                tree.append([obj['id'], None, [],
                    obj[self.view['field_parent']]])
                tree[-1][1] = [obj[y] for y in self.fields]
                if obj[self.view['field_parent']]:
                    tree[-1][2] = None
        else:
            res = self._read(ids, self.fields)
            for obj in res:
                tree.append([obj['id'], [obj[y] for y in self.fields], []])
        return tree

    def _node_expand(self, node):
        node[2] = self._node_process(node[3])
        del node[3]

    #Mandatory GenericTreeModel method
    def on_get_path(self, node):
        '''returns the tree path (a tuple of indices)'''
        return tuple([x[0] for x in node])

    def on_get_flags(self):
        return 0

    def on_get_n_columns(self):
        return len(self.fields)+1

    def on_get_column_type(self, index):
        if index in self.pixbufs:
            return gtk.gdk.Pixbuf
        return FIELDS_LIST_TYPE.get(
                self.fields_type[self.fields[index-1]]['type'],
                gobject.TYPE_STRING)

    def on_get_tree_path(self, node):
        '''returns the tree path (a tuple of indices)'''
        return tuple([x[0] for x in node])

    def on_get_iter(self, path):
        '''returns the node corresponding to the given path.'''
        node = []
        tree = self.tree
        if self.tree == []:
            return None
        for i in path:
            node.append((i, tree))
            tree = tree[i][2]
        return node

    def on_get_value(self, node, column):
        (i, values) = node[-1]
        if column:
            value = values[i][1][column-1]
        else:
            value = values[i][0]

        res = value or ''
        if (column in self.pixbufs) and res:
            if res.startswith('STOCK_'):
                res = getattr(gtk, res)
            return self.treeview.render_icon(stock_id=res,
                    size=gtk.ICON_SIZE_MENU, detail=None)
        return res

    def on_iter_next(self, node):
        '''returns the next node at this level of the tree'''
        node = node[:]
        (i, values) = node[-1]
        if i < len(values) - 1:
            node[-1] = (i + 1, values)
            return node
        return None

    def on_iter_children(self, node):
        '''returns the first child of this node'''
        if node == None:
            return [(0, self.tree)]
        node = node[:]
        (i, values) = node[-1]
        if values[i][2] == None:
            self._node_expand(values[i])
        if values[i][2] == []:
            return None
        node.append((0, values[i][2]))
        return node

    def on_iter_has_child(self, node):
        '''returns true if this node has children'''
        (i, values) = node[-1]
        return values[i][2] != []

    def on_iter_n_children(self, node):
        '''returns the number of children of this node'''
        if node == None:
            return len(self.tree)
        (i, values) = node[-1]
        if values[i][2] == None:
            self._node_expand(values[i])
        return len(values[i][2])

    def on_iter_nth_child(self, node, child):
        '''returns the nth child of this node'''
        if node == None:
            if child < len(self.tree):
                return [(child, self.tree)]
            return None
        node = node[:]
        (i, values) = node[-1]
        if values[i][2] == None:
            self._node_expand(values[i])
        if child < len(values[i][2]):
            node.append((child, values[i][2]))
            return node
        return None

    def on_iter_parent(self, node):
        '''returns the parent of this node'''
        if node == None:
            return None
        return node[:-1]

    def cus_refresh(self):
        tree = self.tree
        tree[0][2] = None

    def _cus_row_find(self, ids_res):
        tree = self.tree
        try:
            ids = ids_res[:]
            while len(ids)>0:
                if ids[-1] in self.roots:
                    ids.pop()
                    break
                ids.pop()
            path = []
            while ids != []:
                path.append(0)
                val = ids.pop()
                i = iter(tree)
                while True:
                    node = i.next()
                    if node[0] == val:
                        break
                    path[-1] += 1
                if (node[2] == None) and (ids != []):
                    return None
                tree = node[2]
            return (tuple(path), node)
        except:
            return None

class ViewTree(object):
    "View tree"

    def __init__(self, view_info, ids, sel_multi=False,
            context=None):
        self.view = gtk.TreeView()
        self.view.set_headers_visible(not CONFIG['client.modepda'])
        self.context = {}
        self.context.update(rpc.session.context)
        if context:
            self.context.update(context)
        self.fields = rpc.session.rpc_exec_auth('/object', 'execute',
                view_info['model'], 'fields_get', False, self.context)
        parse = Parse(self.fields)
        parse.parse(view_info['arch'], self.view)
        self.toolbar = parse.toolbar
        self.pixbufs = parse.pixbufs
        self.name = parse.title
        self.sel_multi = sel_multi

        if sel_multi:
            self.view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        else:
            self.view.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.view.set_expander_column(self.view.get_column(1))
        self.view.set_enable_search(False)
        self.view.get_column(0).set_visible(False)

        self.ids = ids
        self.view_info = view_info
        self.fields_order = parse.fields_order
        self.model = None
        self.reload()

        self.view.show_all()
        self.search = []
        self.next = 0

    def reload(self):
        del self.model
        self.model = ViewTreeModel(self.ids, self.view_info,
                self.fields_order, self.fields, context=self.context,
                pixbufs=self.pixbufs, treeview=self.view)
        self.view.set_model(self.model)

    def widget_get(self):
        return self.view

    def sel_ids_get(self):
        sel = self.view.get_selection()
        if not sel:
            return None
        sel = sel.get_selected_rows()
        if not sel:
            return []
        (model, iters) = sel
        return [int(model.get_value(model.get_iter(x), 0)) for x in iters]

    def sel_id_get(self):
        sel = self.view.get_selection().get_selected()
        if sel == None:
            return None
        (model, i) = sel
        if not i:
            return None
        res = model.get_value(i, 0)
        if res != None:
            return int(res)
        return res

    def value_get(self, col):
        sel = self.view.get_selection().get_selected_rows()
        if sel == None:
            return None
        (model, i) = sel
        if not i:
            return None
        return model.get_value(i, col)
