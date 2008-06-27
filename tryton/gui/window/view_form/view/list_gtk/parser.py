#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import locale
import gtk
import math

from tryton.rpc import RPCProxy
from editabletree import EditableTreeView
from tryton.gui.window.view_form.view.interface import ParserInterface

import time

from tryton.gui.window.view_form.view.form_gtk.many2one import Dialog \
        as M2ODialog
from tryton.gui.window.view_form.view.form_gtk.one2many import Dialog \
        as O2MDialog
from tryton.gui.window.win_search import WinSearch

import tryton.rpc as rpc
import datetime as DT
from tryton.common import DT_FORMAT, DHM_FORMAT, COLORS, node_attributes, TRYTON_ICON
import tryton.common as common

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

def sort_model(column, treeview, screen):
    for col in treeview.get_columns():
        if col != column:
            col.arrow_show = False
            col.arrow.hide()
    screen.sort = None
    if not column.arrow_show:
        column.arrow_show = True
        column.arrow.set(gtk.ARROW_DOWN, gtk.SHADOW_IN)
        column.arrow.show()
        screen.sort = [(column.name, 'ASC')]
    else:
        if column.arrow.get_property('arrow-type') == gtk.ARROW_DOWN:
            column.arrow.set(gtk.ARROW_UP, gtk.SHADOW_IN)
            screen.sort = [(column.name, 'DESC')]
        else:
            column.arrow_show = False
            column.arrow.hide()
    model = treeview.get_model()
    if screen.search_count == len(model):
        ids = screen.search_filter(only_ids=True)
        model.sort(ids)
    else:
        screen.search_filter()

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
        treeview.sequence = attrs.get('sequence', False)
        treeview.colors = {}
        self.treeview = treeview
        for color_spec in attrs.get('colors', '').split(';'):
            if color_spec:
                colour, test = color_spec.split(':')
                self.treeview.colors[colour] = test
        treeview.set_property('rules-hint', True)
        if not self.title:
            self.title = attrs.get('string', 'Unknown')
        tooltips = gtk.Tooltips()

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
                cell = CELLTYPES.get(node_attrs.get('widget',
                    fields[fname]['type']))(fname, model,
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

                hbox = gtk.HBox(False, 2)
                label = gtk.Label(fields[fname]['string'])
                label.show()
                help = fields[fname]['string']
                if fields[fname].get('help'):
                    help += '\n' + fields[fname]['help']
                tooltips.set_tip(label, help)
                tooltips.enable()
                arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_IN)
                col.arrow = arrow
                col.arrow_show = False
                hbox.pack_start(label, True, True, 0)
                hbox.pack_start(arrow, False, False, 0)
                hbox.show()
                col.set_widget(hbox)

                col._type = fields[fname]['type']
                col.set_cell_data_func(renderer, cell.setter)
                col.set_clickable(True)
                twidth = {
                    'integer': 60,
                    'float': 80,
                    'numeric': 80,
                    'float_time': 80,
                    'date': 80,
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
                col.width = width
                if width > 0:
                    col.set_fixed_width(width)
                #XXX doesn't work well when resize columns
                #col.set_expand(True)
                if not treeview.sequence:
                    col.connect('clicked', sort_model, treeview, self.screen)
                col.set_resizable(True)
                col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                col.set_visible(not fields[fname].get('tree_invisible', False))
                i = treeview.append_column(col)
                if 'sum' in fields[fname] and fields[fname]['type'] \
                        in ('integer', 'float', 'numeric', 'float_time'):
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
        if not bool(int(attrs.get('fill', '0'))):
            col = gtk.TreeViewColumn()
            col.name = None
            arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_IN)
            col.arrow = arrow
            col.arrow_show = False
            col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            treeview.append_column(col)
        treeview.set_fixed_height_mode(True)
        return treeview, dict_widget, [], on_write, [], None


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
        if self.attrs['type'] in ('float', 'integer', 'boolean', 'numeric',
                'float_time'):
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
        if 'timezone' in rpc.CONTEXT:
            try:
                import pytz
                lzone = pytz.timezone(rpc.CONTEXT['timezone'])
                szone = pytz.timezone(rpc.TIMEZONE)
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
        if 'timezone' in rpc.CONTEXT:
            try:
                import pytz
                lzone = pytz.timezone(rpc.CONTEXT['timezone'])
                szone = pytz.timezone(rpc.TIMEZONE)
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
                # assume <hours>:<minutes>
                h, m = text.split(':')
                h = h or 0
                m = m or 0
                return round(int(h) + int(m)/60.0, 2)
            else:
                # try float in locale notion
                return locale.atof(text)
        except:
            return 0.0

class M2O(Char):

    def value_from_text(self, model, text):
        if not text:
            return False

        relation = model[self.field_name].attrs['relation']
        rpc_relation = RPCProxy(relation)

        domain = model[self.field_name].domain_get(model)
        context = model[self.field_name].context_get(model)

        try:
            names = rpc_relation.name_search(text, domain, 'ilike', context)
        except Exception, exception:
            common.process_exception(exception, self.window)
            return '???'
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

            try:
                names = rpc_relation.name_search(text, domain, 'ilike', context)
            except Exception, exception:
                common.process_exception(exception, self.window)
                return False, False
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
                domain=domain, parent=self.window)
        found = win.run()
        if found:
            try:
                return rpc_relation.name_get([found[0]], context)[0]
            except Exception, exception:
                common.process_exception(exception, self.window)
                return False, None
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
        pass

    def open_remote(self, model, create=True, changed=False, text=None):
        models = model.value[self.field_name]
        modelfield = model.mgroup.mfields[self.field_name]
        relation = modelfield.attrs['relation']
        context = modelfield.context_get(model)

        dia = O2MDialog(relation, parent=model, model=models,
                attrs=modelfield.attrs, default_get_ctx=context,
                window=self.window)
        res, value = dia.run()
        dia.destroy()
        return False, False


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
        try:
            names = rpc_relation.name_search(text, domain, 'ilike', context)
        except Exception, exception:
            common.process_exception(exception, self.window)
            return []
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
            try:
                ids = rpc_relation.search(domain)
            except Exception, exception:
                common.process_exception(exception, self.window)
                return False, None
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
        if 'relation' in self.attrs:
            try:
                selection = rpc.execute('object', 'execute',
                        self.attrs['relation'], 'name_search', '',
                        self.attrs.get('domain', []), 'ilike', rpc.CONTEXT)
            except Exception, exception:
                common.process_exception(exception, self.window)
                selection = []
        else:
            if not isinstance(selection, (list, tuple)):
                try:
                    selection = rpc.execute('object', 'execute',
                            self.model, selection, rpc.CONTEXT)
                except Exception, exception:
                    common.process_exception(exception, self.window)
                    selection = []
        selection.sort(lambda x, y: cmp(x[1], y[1]))
        self.attrs['selection'] = selection
        self.selection = selection
        for i in self.selection:
            selection_data.append(i)
        self.renderer.set_property('model', selection_data)
        self.renderer.set_property('text-column', 1)

    def get_textual_value(self, model):
        value = model[self.field_name].get(model)
        if isinstance(value, (list, tuple)):
            value = value[0]
        return dict(self.selection).get(value, '')

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
    'numeric': Float,
    'float_time': FloatTime,
    'integer': Int,
    'datetime': Datetime,
    'boolean': Boolean,
    'text': Char,
    'url': Char,
    'email': Char,
    'callto': Char,
    'sip': Char,
}
