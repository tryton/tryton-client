import locale
import gtk
import math

from tryton.rpc import RPCProxy
from editabletree import EditableTreeView
from tryton.gui.window.view_form.view.interface import ParserInterface

import time

from tryton.gui.window.view_form.view.form_gtk.many2one import Dialog \
        as M2ODialog
from tryton.gui.window.win_search import WinSearch

import tryton.rpc as rpc
import datetime as DT
from tryton.common import DT_FORMAT, DHM_FORMAT, COLORS, node_attributes

if not hasattr(locale, 'nl_langinfo'):
    locale.nl_langinfo = lambda *a: '%x'

if not hasattr(locale, 'D_FMT'):
    locale.D_FMT = None

def send_keys(renderer, editable, position, treeview):
    editable.connect('key_press_event', treeview.on_keypressed)
    editable.editing_done_id = editable.connect('editing_done',
            treeview.on_editing_done)
    if isinstance(editable, gtk.ComboBoxEntry):
        editable.connect('changed', treeview.on_editing_done)

def sort_model(column, treeview):
    model = treeview.get_model()
    model.sort(column.name)

class ParserTree(ParserInterface):

    def __init__(self, window, parent=None, attrs=None, screen=None):
        super(ParserTree, self).__init__(window, parent, attrs, screen)
        self.treeview = None

    def parse(self, model, root_node, fields):
        dict_widget = {}
        attrs = node_attributes(root_node)
        on_write = attrs.get('on_write', '')
        editable = attrs.get('editable', False)
        if editable:
            treeview = EditableTreeView(editable)
        else:
            treeview = gtk.TreeView()
            treeview.cells = {}
        treeview.colors = {}
        self.treeview = treeview
        for color_spec in attrs.get('colors', '').split(';'):
            if color_spec:
                colour, test = color_spec.split(':')
                self.treeview.colors[colour] = test
        treeview.set_property('rules-hint', True)
        if not self.title:
            self.title = attrs.get('string', 'Unknown')

        for node in root_node.childNodes:
            node_attrs = node_attributes(node)
            if node.localName == 'field':
                fname = str(node_attrs['name'])
                for boolean_fields in ('readonly', 'required'):
                    if boolean_fields in node_attrs:
                        node_attrs[boolean_fields] = \
                                bool(int(node_attrs[boolean_fields]))
                if fname not in fields:
                    continue
                fields[fname].update(node_attrs)
                node_attrs.update(fields[fname])
                cell = CELLTYPES.get(fields[fname]['type'])(fname, model,
                        treeview, node_attrs, self.window)
                treeview.cells[fname] = cell
                renderer = cell.renderer
                if editable and not node_attrs.get('readonly', False):
                    if isinstance(renderer, gtk.CellRendererToggle):
                        renderer.set_property('activatable', True)
                    else:
                        renderer.set_property('editable', True)
                    renderer.connect_after('editing-started', send_keys,
                            treeview)
                else:
                    if isinstance(renderer, gtk.CellRendererToggle):
                        renderer.set_property('activatable', False)

                col = gtk.TreeViewColumn(fields[fname]['string'], renderer)
                col.name = fname
                col._type = fields[fname]['type']
                col.set_cell_data_func(renderer, cell.setter)
                col.set_clickable(True)
                twidth = {
                    'integer': 60,
                    'float': 80,
                    'float_time': 80,
                    'date': 70,
                    'datetime': 120,
                    'selection': 90,
                    'char': 100,
                    'one2many': 50,
                    'many2many': 50,
                    'boolean': 20,
                }
                if 'width' in fields[fname]:
                    width = int(fields[fname]['width'])
                else:
                    width = twidth.get(fields[fname]['type'], 100)
                col.set_min_width(width)
                col.connect('clicked', sort_model, treeview)
                col.set_resizable(True)
                #col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                col.set_visible(not fields[fname].get('invisible', False))
                i = treeview.append_column(col)
                if 'sum' in fields[fname] and fields[fname]['type'] \
                        in ('integer', 'float', 'float_time'):
                    label = gtk.Label()
                    label.set_use_markup(True)
                    label_str = fields[fname]['sum'] + ': '
                    label_bold = bool(int(fields[fname].get('sum_bold', 0)))
                    if label_bold:
                        label.set_markup('<b>%s</b>' % label_str)
                    else:
                        label.set_markup(label_str)
                    label_sum = gtk.Label()
                    label_sum.set_use_markup(True)
                    dict_widget[i] = (fname, label, label_sum,
                            fields.get('digits', (16,2))[1], label_bold)
        return treeview, dict_widget, [], on_write


class Char(object):

    def __init__(self, field_name, model, treeview=None, attrs=None, window=None):
        self.field_name = field_name
        self.model = model
        self.attrs = attrs or {}
        self.renderer = gtk.CellRendererText()
        self.treeview = treeview
        self.window = window

    def setter(self, column, cell, store, iter):
        model = store.get_value(iter, 0)
        text = self.get_textual_value(model)
        cell.set_property('text', text)
        color = self.get_color(model)
        cell.set_property('foreground', str(color))
        if self.attrs['type'] in ('float', 'integer', 'boolean'):
            align = 1
        else:
            align = 0
        if hasattr(self.treeview, 'editable') \
                and self.treeview.editable:
            field = model[self.field_name]
            if not field.get_state_attrs(model).get('valid', True):
                cell.set_property('background',
                        COLORS.get('invalid', 'white'))
            elif bool(int(field.get_state_attrs(model).get('required', 0))):
                cell.set_property('background',
                        COLORS.get('required', 'white'))
        cell.set_property('xalign', align)

    def get_color(self, model):
        to_display = ''
        for color, expr in self.treeview.colors.items():
            if model.expr_eval(expr, check_load=False):
                to_display = color
                break
        return to_display or 'black'

    def open_remote(self, model, create, changed=False, text=None):
        raise NotImplementedError

    def get_textual_value(self, model):
        return model[self.field_name].get_client(model) or ''

    def value_from_text(self, model, text):
        return text

class Int(Char):

    def value_from_text(self, model, text):
        return int(text)

    def get_textual_value(self, model):
        return locale.format('%d',
                model[self.field_name].get_client(model) or 0, True)

class Boolean(Int):

    def __init__(self, *args):
        super(Boolean, self).__init__(*args)
        self.renderer = gtk.CellRendererToggle()
        self.renderer.connect('toggled', self._sig_toggled)

    def get_textual_value(self, model):
        return model[self.field_name].get_client(model) or 0

    def setter(self, column, cell, store, iter):
        model = store.get_value(iter, 0)
        value = self.get_textual_value(model)
        cell.set_active(bool(value))

    def _sig_toggled(self, renderer, path):
        store = self.treeview.get_model()
        model = store.get_value(store.get_iter(path), 0)
        field = model[self.field_name]
        if not field.get_state_attrs(model).get('readonly', False):
            value = model[self.field_name].get_client(model)
            model[self.field_name].set_client(model, int(not value))
            self.treeview.set_cursor(path)
        return True


class Date(Char):
    server_format = DT_FORMAT
    display_format = locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y')

    def get_textual_value(self, model):
        value = model[self.field_name].get_client(model)
        if not value:
            return ''
        date = time.strptime(value, self.server_format)
        return time.strftime(self.display_format, date)

    def value_from_text(self, model, text):
        if not text:
            return False
        try:
            date = time.strptime(text, self.display_format)
        except:
            try:
                date = list(time.localtime())
                date[2] = int(text)
                date = tuple(date)
            except:
                return False
        return time.strftime(self.server_format, date)


class Datetime(Date):
    server_format = DHM_FORMAT
    display_format = locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y') + \
            ' %H:%M:%S'

    def get_textual_value(self, model):
        value = model[self.field_name].get_client(model)
        if not value:
            return ''
        date = time.strptime(value, self.server_format)
        if 'timezone' in rpc.session.context:
            try:
                import pytz
                lzone = pytz.timezone(rpc.session.context['timezone'])
                szone = pytz.timezone(rpc.session.timezone)
                datetime = DT.datetime(date[0], date[1], date[2], date[3],
                        date[4], date[5], date[6])
                sdt = szone.localize(datetime, is_dst=True)
                ldt = sdt.astimezone(lzone)
                date = ldt.timetuple()
            except:
                pass
        return time.strftime(self.display_format, date)

    def value_from_text(self, model, text):
        if not text:
            return False
        try:
            date = time.strptime(text, self.display_format)
        except:
            try:
                datetime = list(time.localtime())
                datetime[2] = int(text)
                date = tuple(datetime)
            except:
                return False
        if 'timezone' in rpc.session.context:
            try:
                import pytz
                lzone = pytz.timezone(rpc.session.context['timezone'])
                szone = pytz.timezone(rpc.session.timezone)
                datetime = DT.datetime(date[0], date[1], date[2], date[3],
                        date[4], date[5], date[6])
                ldt = lzone.localize(datetime, is_dst=True)
                sdt = ldt.astimezone(szone)
                date = sdt.timetuple()
            except:
                pass
        return time.strftime(self.server_format, date)

class Float(Char):
    def get_textual_value(self, model):
        digit = self.attrs.get('digits', (16, 2))[1]
        return locale.format('%.'+str(digit)+'f',
                model[self.field_name].get_client(model) or 0.0, True)

    def value_from_text(self, model, text):
        try:
            return locale.atof(text)
        except:
            return 0.0


class FloatTime(Char):

    def get_textual_value(self, model):
        val = model[self.field_name].get_client(model)
        value = '%02d:%02d' % (math.floor(abs(val)),
                round(abs(val) % 1 + 0.01, 2) * 60)
        if val < 0:
            value = '-' + value
        return value

    def value_from_text(self, model, text):
        try:
            if text and ':' in text:
                return round(int(text.split(':')[0]) + \
                        int(text.split(':')[1]) / 60.0,2)
            else:
                return locale.atof(text)
        except:
            pass
        return 0.0

class M2O(Char):

    def value_from_text(self, model, text):
        if not text:
            return False

        relation = model[self.field_name].attrs['relation']
        rpc_relation = RPCProxy(relation)

        domain = model[self.field_name].domain_get(model)
        context = model[self.field_name].context_get(model)

        names = rpc_relation.name_search(text, domain, 'ilike', context)
        if len(names) != 1:
            return self.search_remote(relation, [x[0] for x in names],
                             domain=domain, context=context)[0]
        return names[0]

    def open_remote(self, model, create=True, changed=False, text=None):
        modelfield = model.mgroup.mfields[self.field_name]
        relation = modelfield.attrs['relation']

        domain = modelfield.domain_get(model)
        context = modelfield.context_get(model)
        if create:
            obj_id = None
        elif not changed:
            obj_id = modelfield.get(model)
        else:
            rpc_relation = RPCProxy(relation)

            names = rpc_relation.name_search(text, domain, 'ilike', context)
            if len(names) == 1:
                return True, names[0]
            searched = self.search_remote(relation, [x[0] for x in names],
                    domain=domain, context=context)
            if searched[0]:
                return True, searched
            return False, False
        dia = M2ODialog(relation, obj_id, domain=domain, context=context,
                window=self.window)
        res, value = dia.run()
        dia.destroy()
        if res:
            return True, value
        else:
            return False, False

    def search_remote(self, relation, ids=None, domain=None, context=None):
        rpc_relation = RPCProxy(relation)

        win = WinSearch(relation, sel_multi=False, ids=ids, context=context,
                domain=domain)
        found = win.go()
        if found:
            return rpc_relation.name_get([found[0]], context)[0]
        else:
            return False, None

class UnsettableColumn(Exception):

    def __init__(self):
        Exception.__init__()


class O2M(Char):

    def get_textual_value(self, model):
        return '( ' + str(len(model[self.field_name].\
                get_client(model).models)) + ' )'

    def value_from_text(self, model, text):
        raise UnsettableColumn('Can not set column of type o2m')


class M2M(Char):

    def get_textual_value(self, model):
        value = model[self.field_name].get_client(model)
        if value:
            return '(%s)' % len(value)
        else:
            return '(0)'

    def value_from_text(self, model, text):
        if not text:
            return []
        if not (text[0] != '('):
            return model[self.field_name].get(model)
        relation = model[self.field_name].attrs['relation']
        rpc_relation = RPCProxy(relation)
        domain = model[self.field_name].domain_get(model)
        context = model[self.field_name].context_get(model)
        names = rpc_relation.name_search(text, domain, 'ilike', context)
        ids = [x[0] for x in names]
        win = WinSearch(relation, sel_multi=True, ids=ids, context=context,
                domain=domain)
        found = win.go()
        return found or []

    def open_remote(self, model, create=True, changed=False, text=None):
        modelfield = model[self.field_name]
        relation = modelfield.attrs['relation']

        rpc_relation = RPCProxy(relation)
        context = model[self.field_name].context_get(model)
        domain = model[self.field_name].domain_get(model)
        if create:
            if text and len(text) and text[0] != '(':
                domain.append(('name', '=', text))
            ids = rpc_relation.search(domain)
            if ids and len(ids)==1:
                return True, ids
        else:
            ids = model[self.field_name].get_client(model)
        win = WinSearch(relation, sel_multi=True, ids=ids, context=context,
                domain=domain)
        found = win.go()
        if found:
            return True, found
        else:
            return False, None

class Selection(Char):

    def __init__(self, *args):
        super(Selection, self).__init__(*args)
        self.renderer = gtk.CellRendererCombo()
        selection_data = gtk.ListStore(str, str)
        selection = self.attrs.get('selection', [])
        if not isinstance(selection, (list, tuple)):
            selection = rpc.session.rpc_exec_auth('/object', 'execute',
                    self.model, selection, rpc.session.context)
            self.attrs['selection'] = selection
        self.selection = selection
        for i in self.selection:
            selection_data.append(i)
        self.renderer.set_property('model', selection_data)
        self.renderer.set_property('text-column', 1)

    def get_textual_value(self, model):
        return dict(self.selection).get(model[self.field_name].get(model), '')

    def value_from_text(self, model, text):
        res = False
        for val, txt in self.selection:
            if txt[:len(text)].lower() == text.lower():
                if len(txt) == len(text):
                    return val
                res = val
        return res


CELLTYPES = {
    'char': Char,
    'many2one': M2O,
    'date': Date,
    'one2many': O2M,
    'many2many': M2M,
    'selection': Selection,
    'float': Float,
    'float_time': FloatTime,
    'integer': Int,
    'datetime': Datetime,
    'boolean': Boolean,
    'text': Char,
}
