import gtk
import gettext
from interface import Interface
import tryton.rpc as rpc
import tryton.common as common

_ = gettext.gettext


class Reference(Interface):

    def __init__(self, name, parent, attrs=None):
        if attrs is None:
            attrs = {}
        super(Reference, self).__init__(name, parent, attrs)
        self.widget = gtk.combo_box_entry_new_text()
        self.widget.child.set_editable(False)
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

    def get_model(self):
        res = self.widget.child.get_text()
        return self._selection.get(res, False)

    def set_popdown(self, selection):
        model = self.widget.get_model()
        model.clear()
        lst = []
        for (i, j) in selection:
            name = str(j)
            if type(i) == type(1):
                name += ' ('+str(i)+')'
            lst.append(name)
            self._selection[name] = i
        self.widget.append_text('')
        for name in lst:
            self.widget.append_text(name)
        return lst

    def _value_get(self):
        if self.get_model():
            return [(self.name, 'like', self.get_model() + ',')]
        else:
            return []

    def _value_set(self, value):
        if value == False:
            value = ''
        for sel in self._selection:
            if self._selection[sel] == value:
                self.widget.child.set_text(sel)


    value = property(_value_get, _value_set, None,
            _('The content of the widget or ValueError if not valid'))

    def clear(self):
        self.value = ''
