"Screen"
import xml.dom.minidom
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
from tryton.gui.window.view_form.model.group import ModelRecordGroup
from tryton.gui.window.view_form.view.screen_container import ScreenContainer
from tryton.gui.window.view_form.widget_search import Form
from tryton.signal_event import SignalEvent
from tryton.common import node_attributes
import gobject

_LIMIT = 20000


class Screen(SignalEvent):
    "Screen"

    def __init__(self, model_name, view_ids=None, view_type=None,
            parent=None, context=None, views_preload=None, tree_saves=True,
            domain=None, create_new=False, row_activate=None, hastoolbar=False,
            default_get=None, show_search=False, window=None, limit=None,
            readonly=False, form=None, exclude_field=None):
        if view_ids is None:
            view_ids = []
        if view_type is None:
            view_type = ['tree', 'form']
        if context is None:
            context = {}
        if views_preload is None:
            views_preload = {}
        if domain is None:
            domain = []
        if default_get is None:
            default_get = {}

        super(Screen, self).__init__()

        self.__current_model = None
        self.show_search = show_search
        self.search_count = 0
        self.hastoolbar = hastoolbar
        self.default_get = default_get
        if not row_activate:
            # TODO change for a function that switch to form view
            self.row_activate = self.switch_view
        else:
            self.row_activate = row_activate
        self.create_new = create_new
        self.name = model_name
        self.domain = domain
        self.views_preload = views_preload
        self.resource = model_name
        self.rpc = RPCProxy(model_name)
        self.context = context
        self.context.update(rpc.CONTEXT)
        self.views = []
        self.fields = {}
        self.view_ids = view_ids
        self.models = None
        self.parent = parent
        self.window = window
        models = ModelRecordGroup(model_name, self.fields, self.window,
                parent=self.parent, context=self.context)
        self.models_set(models)
        self.current_model = None
        self.screen_container = ScreenContainer()
        self.filter_widget = None
        self.widget = self.screen_container.widget_get()
        self.__current_view = 0
        self.tree_saves = tree_saves
        self.limit = limit
        self.readonly = readonly
        self.form = form
        self.fields_view_tree = None
        self.exclude_field = exclude_field

        if view_type:
            self.view_to_load = view_type[1:]
            view_id = False
            if view_ids:
                view_id = view_ids.pop(0)
            view = self.add_view_id(view_id, view_type[0])
            self.screen_container.set(view.widget)
        self.display()

    def search_active(self, active=True):
        if active and self.show_search:
            if not self.filter_widget:
                if not self.fields_view_tree:
                    try:
                        self.fields_view_tree = rpc.execute('object',
                                'execute', self.name, 'fields_view_get', False,
                                'tree', self.context)
                    except:
                        return
                self.filter_widget = Form(self.fields_view_tree['arch'],
                        self.fields_view_tree['fields'], self.name, self.window,
                        self.domain, (self, self.search_filter))
                self.screen_container.add_filter(self.filter_widget.widget,
                        self.search_filter, self.search_clear)
                self.filter_widget.set_limit(self.limit or _LIMIT)
            self.screen_container.show_filter()
        else:
            self.screen_container.hide_filter()

    def search_clear(self, widget=None):
        self.filter_widget.clear()
        self.clear()

    def search_filter(self, widget=None):
        limit = self.filter_widget.get_limit()
        offset = self.filter_widget.get_offset()
        values = self.filter_widget.value
        filter_keys = []
        for key, operator, value in values:
            filter_keys.append(key)
        for key, operator, value in self.domain:
            if key not in filter_keys and \
                    not (key == 'active' \
                    and self.context.get('active_test', False)):
                values.append((key, operator, value))
        try:
            ids = rpc.execute('object', 'execute',
                    self.name, 'search', values, offset, limit, 0, self.context)
            if len(ids) == limit:
                self.search_count = rpc.execute('object', 'execute',
                        self.name, 'search_count', values, self.context)
            else:
                self.search_count = len(ids)
        except:
            ids = []
        self.clear()
        self.load(ids)
        return True

    def models_set(self, models):
        if self.models:
            self.models.signal_unconnect(self.models)
        self.models = models
        self.parent = models.parent
        if len(models.models):
            self.current_model = models.models[0]
        else:
            self.current_model = None
        self.models.signal_connect(self, 'record-cleared', self._record_cleared)
        self.models.signal_connect(self, 'record-changed', self._record_changed)
        self.models.signal_connect(self, 'model-changed', self._model_changed)
        models.add_fields(self.fields, models)
        self.fields.update(models.fields)

    def _record_cleared(self, model_group, signal, *args):
        for view in self.views:
            view.reload = True

    def _record_changed(self, model_group, signal, *args):
        for view in self.views:
            view.signal_record_changed(signal[0], model_group.models,
                    signal[1], *args)

    def _model_changed(self, model_group, model):
        if (not model) or (model == self.current_model):
            self.display()

    def _get_current_model(self):
        return self.__current_model

    #
    # Check more or less fields than in the screen !
    #
    def _set_current_model(self, value):
        self.__current_model = value
        try:
            offset = int(self.filter_widget.get_offset())
        except:
            offset = 0
        try:
            pos = self.models.models.index(value)
        except:
            pos = -1
        self.signal('record-message', (pos + offset,
            len(self.models.models or []) + offset,
            self.search_count,
            value and value.id))
        attachment_count = 0
        if value and value.attachment_count > 0:
            attachment_count = value.attachment_count
        self.signal('attachment-count', attachment_count)
        # update attachment-count after 5 seconds
        gobject.timeout_add(5 * 1000, self.update_attachment, value)
        return True
    current_model = property(_get_current_model, _set_current_model)

    def update_attachment(self, model):
        if model != self.__current_model:
            return False
        if model:
            attachment_count = model.get_attachment_count()
            self.signal('attachment-count', attachment_count)
        return False

    def destroy(self):
        for view in self.views:
            view.destroy()
            del view
        #del self.current_model
        self.models.signal_unconnect(self)
        del self.models
        del self.views

    def switch_view(self):
        self.current_view.set_value()
        if self.current_model and self.current_model not in self.models.models:
            self.current_model = None
        if len(self.view_to_load):
            self.load_view_to_load()
            self.__current_view = len(self.views) - 1
        else:
            self.__current_view = (self.__current_view + 1) % len(self.views)
        self.screen_container.set(self.current_view.widget)
        if self.current_model:
            self.current_model.validate_set()
        self.display()
        self.current_view.set_cursor()
        # TODO: set True or False accoring to the type

    def load_view_to_load(self):
        if len(self.view_to_load):
            if self.view_ids:
                view_id = self.view_ids.pop(0)
                view_type = self.view_to_load.pop(0)
            else:
                view_id = False
                view_type = self.view_to_load.pop(0)
            self.add_view_id(view_id, view_type)

    def add_view_custom(self, arch, fields, display=False, toolbar=None):
        return self.add_view(arch, fields, display, True, toolbar=toolbar)

    def add_view_id(self, view_id, view_type, display=False, context=None):
        if view_type in self.views_preload:
            return self.add_view(self.views_preload[view_type]['arch'],
                    self.views_preload[view_type]['fields'], display,
                    toolbar=self.views_preload[view_type].get('toolbar', False),
                    context=context)
        else:
            try:
                view = self.rpc.fields_view_get(view_id, view_type, self.context,
                        self.hastoolbar)
            except Exception, exception:
                rpc.process_exception(exception, self.window)
                raise
            if self.exclude_field:
                if self.exclude_field in view['fields']:
                    del view['fields'][self.exclude_field]
            return self.add_view(view['arch'], view['fields'], display,
                    toolbar=view.get('toolbar', False), context=context)

    def add_view(self, arch, fields, display=False, custom=False, toolbar=None,
            context=None):
        if toolbar is None:
            toolbar = {}
        def _parse_fields(node, fields):
            if node.nodeType == node.ELEMENT_NODE:
                if node.localName == 'field':
                    attrs = node_attributes(node)
                    if attrs.get('widget', False):
                        attrs['type'] = attrs['widget']
                    if self.readonly:
                        attrs['readonly'] = 1
                    try:
                        fields[str(attrs['name'])].update(attrs)
                    except:
                        pass
            for node2 in node.childNodes:
                _parse_fields(node2, fields)
        xml_dom = xml.dom.minidom.parseString(arch)
        _parse_fields(xml_dom, fields)
        for dom in self.domain:
            if dom[0] in fields:
                field_dom = str(fields[dom[0]].setdefault('domain',[]))
                fields[dom[0]]['domain'] = field_dom[:1] + \
                        str(('id', dom[1], dom[2])) + ',' + field_dom[1:]
        for node in xml_dom.childNodes:
            if node.localName == 'tree':
                self.fields_view_tree = {'arch': arch, 'fields': fields}

        from tryton.gui.window.view_form.view.widget_parse import WidgetParse
        models = self.models.models
        if self.current_model and (self.current_model not in models):
            models = models + [self.current_model]
        if custom:
            self.models.add_fields_custom(fields, self.models)
        else:
            self.models.add_fields(fields, self.models, context=context)
        self.fields = self.models.fields

        parser = WidgetParse(parent=self.parent, window=self.window)
        view = parser.parse(self, xml_dom, self.fields, toolbar=toolbar)

        self.views.append(view)

        if display:
            self.__current_view = len(self.views) - 1
            self.current_view.display()
            self.screen_container.set(view.widget)
        return view

    def editable_get(self):
        if hasattr(self.current_view, 'widget_tree'):
            if hasattr(self.current_view.widget_tree, 'editable'):
                return self.current_view.widget_tree.editable
        return False

    def new(self, default=True, context=None):
        if context is None:
            context = {}
        if self.current_view and self.current_view.view_type == 'tree' \
                and not (hasattr(self.current_view.widget_tree, 'editable') \
                    and self.current_view.widget_tree.editable):
            self.switch_view()
        ctx = self.context.copy()
        ctx.update(context)
        model = self.models.model_new(default, self.domain, ctx)
        if (not self.current_view) \
                or self.current_view.model_add_new \
                or self.create_new:
            self.models.model_add(model, self.new_model_position())
        self.current_model = model
        self.current_model.validate_set()
        self.display()
        if self.current_view:
            self.current_view.set_cursor(new=True)
        return self.current_model

    def new_model_position(self):
        position = -1
        if self.current_view and self.current_view.view_type == 'tree' \
                and hasattr(self.current_view.widget_tree, 'editable') \
                    and self.current_view.widget_tree.editable == 'top':
            position = 0
        return position

    def set_on_write(self, func_name):
        self.models.on_write = func_name

    def cancel_current(self):
        if self.current_model:
            self.current_model.cancel()
        if self.current_view:
            self.current_view.cancel()

    def save_current(self):
        if not self.current_model:
            return False
        self.current_view.set_value()
        obj_id = False
        if self.current_model.validate():
            obj_id = self.current_model.save(force_reload=True)
        else:
            self.current_view.display()
            self.current_view.set_cursor()
            return False
        if self.current_view.view_type == 'tree':
            for model in self.models.models:
                if model.is_modified():
                    if model.validate():
                        obj_id = model.save(force_reload=True)
                    else:
                        self.current_model = model
                        self.display()
                        self.current_view.set_cursor()
                        return False
            self.display()
            self.current_view.set_cursor()
        if self.current_model not in self.models:
            self.models.model_add(self.current_model)
        return obj_id

    def _get_current_view(self):
        if not len(self.views):
            return None
        return self.views[self.__current_view]
    current_view = property(_get_current_view)

    def get(self):
        if not self.current_model:
            return None
        self.current_view.set_value()
        return self.current_model.get()

    def is_modified(self):
        if not self.current_model:
            return False
        self.current_view.set_value()
        res = False
        if self.current_view.view_type != 'tree':
            res = self.current_model.is_modified()
        else:
            for model in self.models.models:
                if model.is_modified():
                    res = True
        return res

    def reload(self):
        self.current_model.reload()
        if self.parent:
            self.parent.reload()
        self.display()

    def remove(self, unlink=False):
        res = False
        if self.current_view.view_type == 'form' and self.current_model:
            obj_id = self.current_model.id
            if unlink and obj_id:
                try:
                    if not self.rpc.unlink([obj_id]):
                        return False
                except Exception, exception:
                    rpc.process_exception(exception, self.window)
                    return False
            idx = self.models.models.index(self.current_model)
            self.models.remove(self.current_model)
            if self.models.models:
                idx = min(idx, len(self.models.models)-1)
                self.current_model = self.models.models[idx]
            else:
                self.current_model = None
            self.display()
            self.current_view.set_cursor()
            res = obj_id
        if self.current_view.view_type == 'tree':
            ids = self.current_view.sel_ids_get()
            if unlink and ids:
                try:
                    if not self.rpc.unlink(ids):
                        return False
                except Exception, exception:
                    rpc.process_exception(exception, self.window)
                    return False
            for model in self.current_view.sel_models_get():
                self.models.remove(model)
            self.current_model = None
            self.display()
            self.current_view.set_cursor()
            res = ids
        return res

    def load(self, ids):
        self.models.load(ids, display=False)
        self.current_view.reset()
        if ids:
            self.display(ids[0])
        else:
            self.current_model = None
            self.display()

    def display(self, res_id=None):
        if res_id:
            self.current_model = self.models[res_id]
        if self.views:
            #XXX To remove when calendar will be implemented
            if self.current_view.view_type == 'calendar' and \
                    len(self.views) > 1:
                self.switch_view()
            self.current_view.display()
            self.current_view.widget.set_sensitive(
                    bool(self.models.models \
                            or (self.current_view.view_type != 'form') \
                            or self.current_model))
            self.search_active(self.current_view.view_type \
                    in ('tree', 'graph', 'calendar'))

    def display_next(self):
        self.current_view.set_value()
        if self.current_model in self.models.models:
            idx = self.models.models.index(self.current_model)
            idx = (idx+1) % len(self.models.models)
            self.current_model = self.models.models[idx]
        else:
            self.current_model = len(self.models.models) \
                    and self.models.models[0]
        if self.current_model:
            self.current_model.validate_set()
        self.display()
        self.current_view.set_cursor()

    def display_prev(self):
        self.current_view.set_value()
        if self.current_model in self.models.models:
            idx = self.models.models.index(self.current_model)-1
            if idx < 0:
                idx = len(self.models.models)-1
            self.current_model = self.models.models[idx]
        else:
            self.current_model = len(self.models.models) \
                    and self.models.models[-1]

        if self.current_model:
            self.current_model.validate_set()
        self.display()
        self.current_view.set_cursor()

    def sel_ids_get(self):
        return self.current_view.sel_ids_get()

    def id_get(self):
        if not self.current_model:
            return False
        return self.current_model.id

    def ids_get(self):
        return [x.id for x in self.models if x.id]

    def clear(self):
        self.models.clear()
        self.current_model = None

    def on_change(self, fieldname, attr):
        self.current_model.on_change(fieldname, attr)
        self.display()
