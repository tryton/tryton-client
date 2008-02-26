import gobject
import gtk
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
import locale
from interface import ParserView
from tryton.action import Action
from tryton.common import message
import gettext

_ = gettext.gettext


class AdaptModelGroup(gtk.GenericTreeModel):

    def __init__(self, model_group):
        super(AdaptModelGroup, self).__init__()
        self.model_group = model_group
        self.models = model_group.models
        self.last_sort = None
        self.sort_asc = True
        self.set_property('leak_references', False)

    def added(self, modellist, position):
        if modellist is self.models:
            model = self.models[position]
            self.emit('row_inserted', self.on_get_path(model),
                      self.get_iter(self.on_get_path(model)))

    def cancel(self):
        pass

    def removed(self, lst, position):
        self.emit('row_deleted', position)
        self.invalidate_iters()

    def append(self, model):
        self.model_group.model_add(model)

    def prepend(self, model):
        self.model_group.model_add(model, 0)

    def remove(self, iter):
        idx = self.get_path(iter)[0]
        self.model_group.model_remove(self.models[idx])
        self.invalidate_iters()

    def sort(self, name):
        self.sort_asc = not (self.sort_asc and (self.last_sort == name))
        self.last_sort = name
        if self.sort_asc:
            sort_fct = lambda x, y: cmp(x[name].get_client(x),
                    y[name].get_client(y))
        else:
            sort_fct = lambda x, y: -1 * cmp(x[name].get_client(x),
                    y[name].get_client(y))
        self.models.sort(sort_fct)
        for idx, row in enumerate(self.models):
            iter = self.get_iter(idx)
            self.row_changed(self.get_path(iter), iter)

    def saved(self, obj_id):
        return self.model_group.writen(obj_id)

    def __len__(self):
        return len(self.models)

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns(self):
        return 1

    def on_get_column_type(self, index):
        return gobject.TYPE_PYOBJECT

    def on_get_path(self, iter):
        return self.models.index(iter)

    def on_get_iter(self, path):
        if isinstance(path, tuple):
            path = path[0]
        if self.models:
            if path < len(self.models):
                return self.models[path]
            else:
                return None
        else:
            return None

    def on_get_value(self, node, column):
        assert column == 0
        return node

    def on_iter_next(self, node):
        try:
            return self.on_get_iter(self.on_get_path(node) + 1)
        except IndexError:
            return None

    def on_iter_has_child(self, node):
        return False

    def on_iter_children(self, node):
        return None

    def on_iter_n_children(self, node):
        return 0

    def on_iter_nth_child(self, node, nth):
        if node is None and self.models:
            return self.on_get_iter(0)
        return None

    def on_iter_parent(self, node):
        return None


class ViewList(ParserView):

    def __init__(self, window, screen, widget, children=None, buttons=None,
            toolbar=None):
        super(ViewList, self).__init__(window, screen, widget, children,
                buttons, toolbar)
        self.store = None
        self.view_type = 'tree'
        self.model_add_new = True
        self.widget = gtk.VBox()
        self.widget_tree = widget
        scroll = gtk.ScrolledWindow()
        scroll.add(self.widget_tree)
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.widget.pack_start(scroll, expand=True, fill=True)
        self.widget_tree.screen = screen
        self.reload = False
        self.children = children

        if children:
            hbox = gtk.HBox()
            self.widget.pack_start(hbox, expand=False, fill=False, padding=2)
            for child in children:
                hbox2 = gtk.HBox()
                hbox2.pack_start(children[child][1], expand=True, fill=False)
                hbox2.pack_start(children[child][2], expand=True, fill=False)
                hbox.pack_start(hbox2, expand=False, fill=False, padding=12)
            hbox.show_all()

        self.display()

        self.widget_tree.connect('button-press-event', self.__button_press)
        self.widget_tree.connect_after('row-activated', self.__sig_switch)
        selection = self.widget_tree.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.__select_changed)

    def __button_press(self, treeview, event):
        if event.button == 3:
            path = treeview.get_path_at_pos(int(event.x), int(event.y))
            selection = treeview.get_selection()
            if selection.get_mode() == gtk.SELECTION_SINGLE:
                model = selection.get_selected()[0]
            elif selection.get_mode() == gtk.SELECTION_MULTIPLE:
                model = selection.get_selected_rows()[0]
            if (not path) or not path[0]:
                return False
            model = model.models[path[0][0]]

            if path[1]._type == 'many2one':
                value = model[path[1].name].get(model)
                ir_action_keyword = RPCProxy('ir.action.keyword')
                relates = ir_action_keyword.get_keyword('form_relate',
                        (self.screen.fields[path[1].name]['relation'], 0),
                        rpc.session.context)
                menu_entries = []
                menu_entries.append((None, None, None))
                menu_entries.append((_('Actions'),
                    lambda x: self.click_and_action(
                        'form_action', value, path), 0))
                menu_entries.append((_('Reports'),
                    lambda x: self.click_and_action(
                        'form_print', value, path), 0))
                menu_entries.append((None, None, None))
                for relate in relates:
                    relate['string'] = relate['name']
                    fct = lambda action: lambda x: \
                            self.click_and_relate(action, value, path)
                    menu_entries.append(
                            ('... ' + relate['name'], fct(relate), 0))
                menu = gtk.Menu()
                for stock_id, callback, sensitivity in menu_entries:
                    if stock_id:
                        item = gtk.ImageMenuItem(stock_id)
                        if callback:
                            item.connect('activate', callback)
                        item.set_sensitive(bool(sensitivity or value))
                    else:
                        item = gtk.SeparatorMenuItem()
                    item.show()
                    menu.append(item)
                menu.popup(None, None, None, event.button, event.time)

    def click_and_relate(self, action, value, path):
        data = {}
        context = {}
        act = action.copy()
        if not(value):
            message(_('You must select a record to use the relation!'))
            return False
        from tryton.gui.window.view_form.screen import Screen
        screen = Screen(self.screen.fields[path[1].name]['relation'])
        screen.load([value])
        act['domain'] = screen.current_model.expr_eval(act['domain'],
                check_load=False)
        act['context'] = str(screen.current_model.expr_eval(act['context'],
            check_load=False))
        return Action._exec_action(act, data, context)

    def click_and_action(self, atype, value, path):
        return Action.exec_keyword(atype, {
            'model': self.screen.fields[path[1].name]['relation'],
            'id': value or False, 'ids': [value]})

    def signal_record_changed(self, signal, *args):
        if not self.store:
            return
        if signal == 'record-added':
            self.store.added(*args)
        elif signal == 'record-removed':
            self.store.removed(*args)
        else:
            pass
        self.update_children()

    def cancel(self):
        pass

    def __str__(self):
        return 'ViewList (%s)' % self.screen.resource

    def __getitem__(self, name):
        return None

    def destroy(self):
        self.widget_tree.destroy()
        del self.screen
        del self.widget_tree
        del self.widget

    def __sig_switch(self, treeview, *args):
        self.screen.row_activate()

    def __select_changed(self, tree_sel):
        if tree_sel.get_mode() == gtk.SELECTION_SINGLE:
            model, iter = tree_sel.get_selected()
            if iter:
                path = model.get_path(iter)[0]
                self.screen.current_model = model.models[path]
        elif tree_sel.get_mode() == gtk.SELECTION_MULTIPLE:
            model, paths = tree_sel.get_selected_rows()
            if paths:
                self.screen.current_model = model.models[paths[0][0]]
        self.update_children()


    def set_value(self):
        if hasattr(self.widget_tree, 'editable') \
                and self.widget_tree.editable:
            self.widget_tree.set_value()

    def reset(self):
        pass

    # self.widget.set_model(self.store) could be removed if the store
    # has not changed -> better ergonomy. To test
    def display(self):
        if self.reload \
                or (not self.widget_tree.get_model()) \
                    or self.screen.models != \
                        self.widget_tree.get_model().model_group:
            self.store = AdaptModelGroup(self.screen.models)
            self.widget_tree.set_model(self.store)
        self.reload = False
        if not self.screen.current_model:
            # Should find a simpler solution to do something like
            #self.widget.set_cursor(None,None,False)
            if self.store:
                self.widget_tree.set_model(self.store)
        self.update_children()

    def update_children(self):
        ids = self.sel_ids_get()
        for child in self.children:
            value = 0.0
            for model in self.screen.models.models:
                if model.id in ids or not ids:
                    value += model.fields_get()[self.children[child][0]]\
                            .get(model, check_load=False)
            label_str = locale.format('%.' + str(self.children[child][3]) + 'f',
                    value, True)
            if self.children[child][4]:
                self.children[child][2].set_markup('<b>%s</b>' % label_str)
            else:
                self.children[child][2].set_markup(label_str)

    def set_cursor(self, new=False):
        if self.screen.current_model:
            path = self.store.on_get_path(self.screen.current_model)
            focus_column = None
            for column in self.widget_tree.get_columns():
                renderer = column.get_cell_renderers()[0]
                if isinstance(renderer, gtk.CellRendererToggle):
                    editable = renderer.get_property('activatable')
                else:
                    editable = renderer.get_property('editable')
                if column.get_visible() and editable:
                    focus_column = column
                    break
            self.widget_tree.set_cursor(path, focus_column, new)

    def sel_ids_get(self):
        def _func_sel_get(store, path, iter, ids):
            model = store.on_get_iter(path)
            if model.id:
                ids.append(model.id)
        ids = []
        sel = self.widget_tree.get_selection()
        sel.selected_foreach(_func_sel_get, ids)
        return ids

    def sel_models_get(self):
        def _func_sel_get(store, path, iter, models):
            models.append(store.on_get_iter(path))
        models = []
        sel = self.widget_tree.get_selection()
        sel.selected_foreach(_func_sel_get, models)
        return models

    def unset_editable(self):
        self.widget_tree.editable = False
        for col in self.widget_tree.get_columns():
            for renderer in col.get_cell_renderers():
                if isinstance(renderer, gtk.CellRendererToggle):
                    renderer.set_property('activatable', False)
                else:
                    renderer.set_property('editable', False)
