import gtk
from gtk import glade
import gobject
import gettext
import tryton.common as common
import tryton.rpc as rpc
import csv
import StringIO
from tryton.config import GLADE, TRYTON_ICON, CONFIG

_ = gettext.gettext


class WinImport(object):
    "Window import"

    def __init__(self, model, fields, preload=None, parent=None):
        self.glade = glade.XML(GLADE, 'win_import', gettext.textdomain())
        self.glade.get_widget('import_csv_combo').set_active(0)
        self.win = self.glade.get_widget('win_import')
        self.model = model
        self.fields_data = {}

        self.win.set_transient_for(parent)
        self.win.set_icon(TRYTON_ICON)
        self.parent = parent

        self.glade.get_widget('import_csv_file').set_current_folder(
                CONFIG['client.default_path'])
        self.view1 = gtk.TreeView()
        self.view1.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.glade.get_widget('import_vp_left').add(self.view1)
        self.view2 = gtk.TreeView()
        self.view2.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.glade.get_widget('import_vp_right').add(self.view2)
        self.view1.set_headers_visible(False)
        self.view2.set_headers_visible(False)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('Field name'), cell, text=0, background=2)
        self.view1.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('Field name'), cell, text=0)
        self.view2.append_column(column)

        self.model1 = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
                gobject.TYPE_STRING)
        self.model2 = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)

        for field in (preload or []):
            self.model2.set(self.model2.append(), 0, field[1], 1, field[0])

        self.fields = {}
        self.fields_invert = {}

        def model_populate(fields, prefix_node='', prefix=None, prefix_value='',
                level=2):
            fields_order = fields.keys()
            fields_order.sort(lambda x, y: -cmp(fields[x].get('string', ''),
                fields[y].get('string', '')))
            for field in fields_order:
                if (fields[field]['type'] not in ('reference',)) \
                        and (not fields[field].get('readonly', False) \
                        or not dict(fields[field].get('states', {}).get(
                            'draft', [('readonly', True)])).get('readonly',
                                True)):
                    self.fields_data[prefix_node+field] = fields[field]
                    st_name = prefix_value+fields[field]['string'] or field
                    node = self.model1.insert(prefix, 0, [st_name,
                        prefix_node+field,
                        (fields[field].get('required', False) and '#ddddff') \
                                or 'white'])
                    self.fields[prefix_node+field] = st_name
                    self.fields_invert[st_name] = prefix_node+field
                    if fields[field]['type'] == 'one2many' and level > 0:
                        try:
                            fields2 = rpc.execute('object',
                                    'execute', fields[field]['relation'],
                                    'fields_get', False, rpc.CONTEXT)
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

        self.glade.signal_connect('on_but_unselect_all_clicked',
                self.sig_unsel_all)
        self.glade.signal_connect('on_but_select_all_clicked', self.sig_sel_all)
        self.glade.signal_connect('on_but_select_clicked', self.sig_sel)
        self.glade.signal_connect('on_but_unselect_clicked', self.sig_unsel)
        self.glade.signal_connect('on_but_autodetect_clicked',
                self.sig_autodetect)

    def sig_autodetect(self, widget=None):
        fname = self.glade.get_widget('import_csv_file').get_filename()
        if not fname:
            common.message('You must select an import file first !',
                    self.parent)
            return True
        csvsep = self.glade.get_widget('import_csv_sep').get_text()
        csvdel = self.glade.get_widget('import_csv_del').get_text()
        csvcode = self.glade.get_widget('import_csv_combo').get_active_text() \
                or 'UTF-8'

        self.glade.get_widget('import_csv_skip').set_value(1)
        try:
            data = csv.reader(file(fname), quotechar=csvdel, delimiter=csvsep)
        except:
            common.warning(_('Error opening CSV file'), self.parent,
                    _('Input Error'))
            return True
        self.sig_unsel_all()
        word = ''
        try:
            for line in data:
                for word in line:
                    word = word.decode(csvcode).encode('utf-8')
                    num = self.model2.append()
                    self.model2.set(num, 0, word, 1, self.fields_invert[word])
                break
        except:
            common.warning(_('Error processing your first line of the file.\n' \
                    'Field %s is unknown!') % (word,), self.parent,
                    _('Import Error'))
        return True

    def sig_sel_all(self, widget=None):
        self.model2.clear()
        for field in self.fields.keys():
            self.model2.set(self.model2.append(), 0, self.fields[field],
                    1, field)

    def sig_sel(self, widget=None):
        sel = self.view1.get_selection()
        sel.selected_foreach(self._sig_sel_add)

    def _sig_sel_add(self, store, path, iter):
        num = self.model2.append()
        self.model2.set(num, 0, store.get_value(iter, 0), 1,
                store.get_value(iter,1))

    def sig_unsel(self, widget=None):
        (store, paths) = self.view2.get_selection().get_selected_rows()
        for path in paths:
            store.remove(store.get_iter(path))

    def sig_unsel_all(self, widget=None):
        self.model2.clear()

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

            csv_data = {
                'fname': self.glade.get_widget('import_csv_file'
                    ).get_filename(),
                'sep': self.glade.get_widget('import_csv_sep').get_text(),
                'del': self.glade.get_widget('import_csv_del').get_text(),
                'skip': self.glade.get_widget('import_csv_skip').get_value(),
                'combo': self.glade.get_widget('import_csv_combo'
                    ).get_active_text() or 'UTF-8'
            }
            self.parent.present()
            self.win.destroy()
            if csv_data['fname']:
                return self.import_csv(csv_data, fields, self.model)
            return False
        else:
            self.parent.present()
            self.win.destroy()
            return False

    def import_csv(self, csv_data, fields, model):
        # TODO: make it works with references
        fname = csv_data['fname']
        content = file(fname,'rb').read()
        file_p = StringIO.StringIO(content)
        data = list(csv.reader(file_p, quotechar=csv_data['del'],
            delimiter=csv_data['sep']))[int(csv_data['skip']):]
        datas = []

        for line in data:
            if not line:
                continue
            datas.append([x.decode(csv_data['combo']).encode('utf-8') \
                    for x in line])
        try:
            res = rpc.execute('object', 'execute',
                    model, 'import_data', fields, datas)
        except Exception, exception:
            rpc.process_exception(exception, self.win)
            return False
        if res[0] >= 0:
            common.message(_('Imported %d objects!') % (res[0],), self.parent)
        else:
            buf = ''
            for key, val in res[1].items():
                buf += ('\t%s: %s\n' % (str(key), str(val)))
            common.message_box(_('Importation Error!'),
                    _('Error trying to import this record:\n' \
                            '%s\nError Message:\n%s\n\n%s') % \
                            (buf, res[2], res[3]), self.parent)
        return True
