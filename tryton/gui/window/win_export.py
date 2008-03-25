import gtk
from gtk import glade
import gobject
import gettext
import tryton.common as common
import tryton.rpc as rpc
import types
from tryton.config import GLADE, TRYTON_ICON
import csv

_ = gettext.gettext



class WinExport(object):
    "Window export"

    def __init__(self, model, ids, fields, preload=None, parent=None,
            context=None):
        if preload is None:
            preload = []
        self.glade = glade.XML(GLADE, 'win_save_as',
                gettext.textdomain())
        self.win = self.glade.get_widget('win_save_as')
        self.ids = ids
        self.model = model
        self.fields_data = {}
        self.context = context

        self.win.set_transient_for(parent)
        self.win.set_icon(TRYTON_ICON)
        self.parent = parent

        self.view1 = gtk.TreeView()
        self.view1.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.glade.get_widget('exp_vp1').add(self.view1)
        self.view2 = gtk.TreeView()
        self.view2.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.glade.get_widget('exp_vp2').add(self.view2)
        self.view1.set_headers_visible(False)
        self.view2.set_headers_visible(False)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Field name', cell, text=0)
        self.view1.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Field name', cell, text=0)
        self.view2.append_column(column)

        self.model1 = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.model2 = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)

        for i in preload:
            self.model2.set(self.model2.append(), 0, i[1], 1, i[0])

        self.fields = {}

        def model_populate(fields, prefix_node='', prefix=None,
                prefix_value='', level=2):
            fields_order = fields.keys()
            fields_order.sort(lambda x, y: -cmp(fields[x].get('string', ''),
                fields[y].get('string', '')))
            for field in fields_order:
                self.fields_data[prefix_node+field] = fields[field]
                if prefix_node:
                    self.fields_data[prefix_node + field]['string'] = \
                            '%s%s' % (prefix_value,
                                    self.fields_data[prefix_node + \
                                            field]['string'])
                st_name = fields[field]['string'] or field 
                node = self.model1.insert(prefix, 0,
                        [st_name, prefix_node+field])
                self.fields[prefix_node+field] = (st_name,
                        fields[field].get('relation', False))
                if fields[field].get('relation', False) and level>0:
                    try:
                        fields2 = rpc.execute('object', 'execute',
                                fields[field]['relation'], 'fields_get', False,
                                rpc.CONTEXT)
                    except Exception, exception:
                        rpc.process_exception(exception, self.win)
                        continue
                    model_populate(fields2, prefix_node+field+'/', node,
                            st_name+'/', level-1)
        model_populate(fields)

        self.view1.set_model(self.model1)
        self.view2.set_model(self.model2)
        self.view1.show_all()
        self.view2.show_all()

        self.wid_action = self.glade.get_widget('win_saveas_combo')
        self.wid_write_field_names = self.glade.get_widget('add_field_names_cb')
        self.wid_action.set_active(1)

        self.glade.signal_connect('on_but_unselect_all_clicked',
                self.sig_unsel_all)
        self.glade.signal_connect('on_but_select_all_clicked', self.sig_sel_all)
        self.glade.signal_connect('on_but_select_clicked', self.sig_sel)
        self.glade.signal_connect('on_but_unselect_clicked', self.sig_unsel)
        self.glade.signal_connect('on_but_predefined_clicked', self.add_predef)
        self.glade.signal_connect('on_but_remove_predefined_clicked',
                self.remove_predef)

        # Creating the predefined export view
        self.pref_export = gtk.TreeView()
        self.pref_export.append_column(gtk.TreeViewColumn('Export name',
            gtk.CellRendererText(), text=2))
        self.pref_export.append_column(gtk.TreeViewColumn('Exported fields',
            gtk.CellRendererText(), text=3))
        self.glade.get_widget('predefined_exports').add(self.pref_export)

        self.pref_export.connect("row-activated", self.sel_predef)

        # Fill the predefined export tree view and show everything
        self.predef_model = gtk.ListStore(
                gobject.TYPE_INT,
                gobject.TYPE_PYOBJECT,
                gobject.TYPE_STRING,
                gobject.TYPE_STRING)
        self.fill_predefwin()
        self.pref_export.show_all()

    def sig_sel_all(self, widget=None):
        self.model2.clear()
        for field, relation in self.fields.keys():
            if not relation:
                self.model2.set(self.model2.append(), 0, self.fields[field],
                        1, field)

    def sig_sel(self, widget=None):
        sel = self.view1.get_selection()
        sel.selected_foreach(self._sig_sel_add)

    def _sig_sel_add(self, store, path, iter):
        relation = self.fields[store.get_value(iter, 1)][1]
        if relation:
            return
        num = self.model2.append()
        self.model2.set(num, 0, store.get_value(iter, 0), 1,
                store.get_value(iter, 1))

    def sig_unsel(self, widget=None):
        store, paths = self.view2.get_selection().get_selected_rows()
        for i in paths:
            store.remove(store.get_iter(i))

    def sig_unsel_all(self, widget=None):
        self.model2.clear()

    def fill_predefwin(self):
        ir_export = rpc.RPCProxy('ir.export')
        ir_export_line = rpc.RPCProxy('ir.export.line')
        try:
            export_ids = ir_export.search([('resource', '=', self.model)])
        except Exception, exception:
            rpc.process_exception(exception, self.win)
            return
        for export in ir_export.read(export_ids):
            try:
                fields = ir_export_line.read(export['export_fields'])
            except Exception, exception:
                rpc.process_exception(exception, self.win)
                continue
            self.predef_model.append((
                export['id'],
                [f['name'] for f in fields],
                export['name'],
                ', '.join([self.fields_data[f['name']]['string'] \
                        for f in fields]),
                ))
        self.pref_export.set_model(self.predef_model)

    def add_predef(self, widget):
        name = common.ask('What is the name of this export?', self.parent)
        if not name:
            return
        ir_export = rpc.RPCProxy('ir.export')
        iter = self.model2.get_iter_root()
        fields = []
        while iter:
            field_name = self.model2.get_value(iter, 1)
            fields.append(field_name)
            iter = self.model2.iter_next(iter)
        try:
            new_id = ir_export.create({'name' : name, 'resource' : self.model,
                'export_fields' : [('create', {'name' : f}) for f in fields]})
        except Exception, exception:
            rpc.process_exception(exception, self.win)
            return
        self.predef_model.append((
            new_id,
            fields,
            name,
            ','.join([self.fields_data[f]['string'] for f in fields])))
        self.pref_export.set_model(self.predef_model)

    def remove_predef(self, widget):
        sel = self.pref_export.get_selection().get_selected()
        if sel == None:
            return None
        (model, i) = sel
        if not i:
            return None
        ir_export = rpc.RPCProxy('ir.export')
        export_id = model.get_value(i, 0)
        try:
            ir_export.unlink(export_id)
        except Exception, exception:
            rpc.process_exception(exception, self.win)
            return
        for i in range(len(self.predef_model)):
            if self.predef_model[i][0] == export_id:
                del self.predef_model[i]
                break
        self.pref_export.set_model(self.predef_model)

    def sel_predef(self, widget, path, column):
        self.model2.clear()
        for field in self.predef_model[path[0]][1]:
            self.model2.append((self.fields_data[field]['string'], field))

    def run(self):
        button = self.win.run()
        if button == gtk.RESPONSE_OK:
            fields = []
            fields2 = []
            iter = self.model2.get_iter_root()
            while iter:
                fields.append(self.model2.get_value(iter, 1))
                fields2.append(self.model2.get_value(iter, 0))
                iter = self.model2.iter_next(iter)
            action = self.wid_action.get_active()
            self.parent.present()
            self.win.destroy()
            result = self.datas_read(self.ids, self.model, fields,
                    context=self.context)

            if action == 0:
                pass
            else:
                fname = common.file_selection(_('Save As...'),
                        parent=self.parent, action=gtk.FILE_CHOOSER_ACTION_SAVE)
                if fname:
                    self.export_csv(fname, fields2, result,
                            self.wid_write_field_names.get_active())
            return True
        else:
            self.parent.present()
            self.win.destroy()
            return False

    def export_csv(self, fname, fields, result, write_title=False):
        try:
            file_p = file(fname, 'wb+')
            writer = csv.writer(file_p)
            if write_title:
                writer.writerow(fields)
            for data in result:
                row = []
                for val in data:
                    if type(val) == types.StringType:
                        row.append(val.replace('\n',' ').replace('\t',' '))
                    else:
                        row.append(val)
                writer.writerow(row)
            file_p.close()
            common.message(str(len(result)) + _(' record(s) saved !'),
                    self.parent)
            return True
        except IOError, exception:
            common.message(_("Operation failed !\nI/O error") + \
                    "(%s)" % (exception[0],), self.parent)
            return False

    def datas_read(self, ids, model, fields, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update(rpc.CONTEXT)
        try:
            datas = rpc.execute('object', 'execute', model,
                    'export_data', ids, fields, ctx)
        except Exception, exception:
            rpc.process_exception(exception, self.win)
            return []
        return datas
