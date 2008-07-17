#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
from interface import Interface
import tryton.rpc as rpc
import tryton.common as common

class Selection(Interface):

    def __init__(self, name, parent, attrs=None):
        if attrs is None:
            attrs = {}
        super(Selection, self).__init__(name, parent, attrs)

        self.widget = gtk.combo_box_entry_new_text()
        self.widget.child.set_editable(True)
        self.widget.child.set_property('activates_default', True)
        self.widget.child.connect('key_press_event', self.sig_key_press)
        self.widget.set_focus_chain([self.widget.child])
        self._selection = {}
        selection = attrs.get('selection', [])
        if 'relation' in attrs:
            try:
                selection = rpc.execute('object', 'execute',
                        attrs['relation'], 'name_search', '',
                        attrs.get('domain', []), 'ilike', rpc.CONTEXT)
            except Exception, exception:
                common.process_exception(exception, parent)
                selection = []
        else:
            if not isinstance(selection, (list, tuple)):
                try:
                    selection = rpc.execute('object', 'execute',
                            attrs['model'], selection, rpc.CONTEXT)
                except Exception, exception:
                    common.process_exception(exception, parent)
                    selection = []
        selection.sort(lambda x, y: cmp(x[1], y[1]))
        attrs['selection'] = selection
        self.set_popdown(selection)

    def set_popdown(self, selection):
        model = self.widget.get_model()
        model.clear()
        self._selection = {}
        lst = []
        for (i, j) in selection:
            name = str(j)
            if type(i) == type(1):
                name += ' (' + str(i) + ')'
            lst.append(name)
            self._selection[name] = i
        self.widget.append_text('')
        for name in lst:
            self.widget.append_text(name)
        completion = gtk.EntryCompletion()
        #Only available in PyGTK 2.6 and above.
        if hasattr(completion, 'set_inline_selection'):
            completion.set_inline_selection(True)
        completion.set_model(model)
        self.widget.child.set_completion(completion)
        completion.set_text_column(0)
        return lst

    def sig_key_press(self, widget, event):
        if event.type == gtk.gdk.KEY_PRESS \
                and event.state & gtk.gdk.CONTROL_MASK \
                and event.keyval == gtk.keysyms.space:
            self.widget.popup()

    def _value_get(self):
        res = self._selection.get(self.widget.child.get_text(), False)
        if res:
            return [(self.name, '=', res)]
        self.widget.child.set_text('')
        return []

    def _value_set(self, value):
        if value == False:
            self.widget.child.set_text('')
            return
        for long_text, sel_value in self._selection.items():
            if sel_value == value:
                self.widget.child.set_text(long_text)
                break

    def clear(self):
        self.value = False

    value = property(_value_get, _value_set, None,
      'The content of the widget or ValueError if not valid')

    def _readonly_set(self, value):
        self.widget.set_sensitive(not value)

    def sig_activate(self, fct):
        self.widget.child.connect_after('activate', fct)
