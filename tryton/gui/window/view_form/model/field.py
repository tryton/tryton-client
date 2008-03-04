from tryton.rpc import RPCProxy
import tryton.rpc as rpc

class ModelField(object):
    '''
    get: return the values to write to the server
    get_client: return the value for the client widget (form_gtk)
    set: save the value from the server
    set_client: save the value from the widget
    '''

    def __new__(cls, ctype):
        klass = TYPES.get(ctype, CharField)
        return klass


class CharField(object):

    def __init__(self, parent, attrs):
        self.parent = parent
        self.attrs = attrs
        self.name = attrs['name']
        self.internal = False
        self.default_attrs = {}

    def sig_changed(self, model):
        if self.get_state_attrs(model).get('readonly', False):
            return
        if self.attrs.get('on_change', False):
            model.on_change(self.name, self.attrs['on_change'])
        if self.attrs.get('change_default', False):
            model.cond_default(self.attrs['name'], self.get(model))

    def domain_get(self, model):
        dom = self.attrs.get('domain', '[]')
        return model.expr_eval(dom)

    def context_get(self, model, check_load=True, eval_context=True):
        context = {}
        context.update(self.parent.context)
        if eval_context:
            field_context_str = self.attrs.get('context', '{}') or '{}'
            field_context = model.expr_eval('dict(%s)' % field_context_str,
                    check_load=check_load)
            context.update(field_context)
        return context

    def validate(self, model):
        res = True
        if bool(int(self.get_state_attrs(model).get('required', 0))):
            if not model.value[self.name]:
                res = False
        self.get_state_attrs(model)['valid'] = res
        return res

    def set(self, model, value, test_state=True, modified=False):
        model.value[self.name] = value
        if modified:
            model.modified = True
            model.modified_fields.setdefault(self.name)
        return True

    def get(self, model, check_load=True, readonly=True, modified=False):
        return model.value.get(self.name, False) or False

    def set_client(self, model, value, test_state=True, force_change=False):
        internal = model.value.get(self.name, False)
        self.set(model, value, test_state)
        if (internal or False) != (model.value.get(self.name, False) or False):
            model.modified = True
            model.modified_fields.setdefault(self.name)
            self.sig_changed(model)
            model.signal('record-changed', model)

    def get_client(self, model):
        return model.value[self.name] or False

    def set_default(self, model, value):
        res = self.set(model, value)
        if self.attrs.get('on_change', False):
            model.on_change(self.name, self.attrs['on_change'])
        return res

    def get_default(self, model):
        return self.get(model)

    def create(self, model):
        return False

    def state_set(self, model, values=None):
        if values is None:
            values = {'state': 'draft'}
        state_changes = self.attrs.get('states', {})
        if isinstance(state_changes, str):
            state_changes = eval(state_changes)
        for key in ('readonly', 'required', 'invisible'):
            if key in state_changes:
                self.get_state_attrs(model)[key] = \
                        eval(state_changes[key], values)
            elif key in self.attrs:
                self.get_state_attrs(model)[key] = self.attrs[key]
        if 'value' in state_changes:
            value = eval(state_changes['value'], values)
            if value:
                self.set(model, value, test_state=False,
                        modified=True)

    def get_state_attrs(self, model):
        if self.name not in model.state_attrs:
            model.state_attrs[self.name] = self.attrs.copy()
        return model.state_attrs[self.name]


class SelectionField(CharField):
    pass


class DateTimeField(CharField):

    def get_client(self, model):
        value = super(DateTimeField, self).get_client(model)
        return value and str(value) or False


class FloatField(CharField):

    def validate(self, model):
        self.get_state_attrs(model)['valid'] = True
        return True

    def set_client(self, model, value, test_state=True, force_change=False):
        internal = model.value[self.name]
        self.set(model, value, test_state)
        if abs(float(internal or 0.0) - float(model.value[self.name] or 0.0)) \
                >= (10.0**(-int(self.attrs.get('digits', (12,4))[1]))):
            if not self.get_state_attrs(model).get('readonly', False):
                model.modified = True
                model.modified_fields.setdefault(self.name)
                self.sig_changed(model)
                model.signal('record-changed', model)


class IntegerField(CharField):

    def get(self, model, check_load=True, readonly=True, modified=False):
        return model.value.get(self.name, 0) or 0

    def get_client(self, model):
        return model.value[self.name] or 0

    def validate(self, model):
        self.get_state_attrs(model)['valid'] = True
        return True


class M2OField(CharField):
    '''
    internal = (id, name)
    '''

    def create(self, model):
        return False

    def get(self, model, check_load=True, readonly=True, modified=False):
        if model.value[self.name]:
            return model.value[self.name][0] or False
        return False

    def get_client(self, model):
        #model._check_load()
        if model.value[self.name]:
            return model.value[self.name][1]
        return False

    def set(self, model, value, test_state=False, modified=False):
        if value and isinstance(value, (int, str, unicode, long)):
            rpc2 = RPCProxy(self.attrs['relation'])
            try:
                result = rpc2.name_get([value], rpc.CONTEXT)
            except:
                return
            model.value[self.name] = result[0]
        else:
            model.value[self.name] = value
        if modified:
            model.modified = True
            model.modified_fields.setdefault(self.name)

    def set_client(self, model, value, test_state=False, force_change=False):
        internal = model.value[self.name]
        self.set(model, value, test_state)
        if internal != model.value[self.name]:
            model.modified = True
            model.modified_fields.setdefault(self.name)
            self.sig_changed(model)
            model.signal('record-changed', model)
        elif force_change:
            self.sig_changed(model)


class M2MField(CharField):
    '''
    internal = [id]
    '''

    def __init__(self, parent, attrs):
        super(M2MField, self).__init__(parent, attrs)

    def create(self, model):
        return []

    def get(self, model, check_load=True, readonly=True, modified=False):
        return [(6, 0, model.value[self.name] or [])]

    def get_client(self, model):
        return model.value[self.name] or []

    def set(self, model, value, test_state=False, modified=False):
        model.value[self.name] = value or []
        if modified:
            model.modified = True
            model.modified_fields.setdefault(self.name)

    def set_client(self, model, value, test_state=False, force_change=False):
        internal = model.value[self.name]
        self.set(model, value, test_state, modified=False)
        if set(internal) != set(value):
            model.modified = True
            model.modified_fields.setdefault(self.name)
            self.sig_changed(model)
            model.signal('record-changed', model)

    def get_default(self, model):
        return self.get_client(model)


class O2MField(CharField):
    '''
    internal = ModelRecordGroup of the related objects
    '''

    def __init__(self, parent, attrs):
        super(O2MField, self).__init__(parent, attrs)
        self.context = {}

    def create(self, model):
        from group import ModelRecordGroup
        mod = ModelRecordGroup(self.attrs['relation'], {}, model.window,
                parent=model)
        mod.signal_connect(mod, 'model-changed', self._model_changed)
        return mod

    def _model_changed(self, group, model):
        model.parent.modified = True
        model.parent.modified_fields.setdefault(self.name)
        self.sig_changed(model.parent)
        self.parent.signal('record-changed', model)

    def get_client(self, model):
        return model.value[self.name]

    def get(self, model, check_load=True, readonly=True, modified=False):
        if not model.value[self.name]:
            return []
        result = []
        for model2 in model.value[self.name].models:
            if (modified and not model2.is_modified()):
                continue
            if model2.id:
                result.append((1, model2.id,
                    model2.get(check_load=check_load, get_readonly=readonly)))
            else:
                result.append((0, 0,
                    model2.get(check_load=check_load, get_readonly=readonly)))
        for rm_id in model.value[self.name].model_removed:
            result.append((2, rm_id, False))
        return result

    def set(self, model, value, test_state=False, modified=False):
        from group import ModelRecordGroup
        mod = ModelRecordGroup(self.attrs['relation'], {}, model.window,
                parent=model)
        mod.signal_connect(mod, 'model-changed', self._model_changed)
        model.value[self.name] = mod
        #self.internal.signal_connect(self.internal, 'model-changed',
        #       self._model_changed)
        model.value[self.name].pre_load(value, display=False)
        #self.internal.signal_connect(self.internal, 'model-changed',
        #       self._model_changed)

    def set_client(self, model, value, test_state=False, force_change=False):
        self.set(model, value, test_state=test_state)
        model.signal('record-changed', model)

    def set_default(self, model, value):
        from group import ModelRecordGroup
        fields = {}
        if value and len(value):
            context = self.context_get(model)
            rpc2 = RPCProxy(self.attrs['relation'])
            try:
                fields = rpc2.fields_get(value[0].keys(), context)
            except:
                return False

        model.value[self.name] = ModelRecordGroup(
                self.attrs['relation'], fields, model.window, parent=model)
        model.value[self.name].signal_connect(model.value[self.name],
                'model-changed', self._model_changed)
        mod = None
        for record in (value or []):
            mod = model.value[self.name].model_new(default=False)
            mod.set_default(record)
            model.value[self.name].model_add(mod)
        model.value[self.name].current_model = mod
        #mod.signal('record-changed')
        return True

    def get_default(self, model):
        res = [x.get_default() for x in model.value[self.name].models or []]
        return res

    def validate(self, model):
        res = True
        for model2 in model.value[self.name].models:
            if not model2.validate():
                if not model2.is_modified():
                    model.value[self.name].models.remove(model2)
                else:
                    res = False
        if not super(O2MField, self).validate(model):
            res = False
        self.get_state_attrs(model)['valid'] = res
        return res


class ReferenceField(CharField):

    def get_client(self, model):
        if model.value[self.name]:
            return model.value[self.name]
        return False

    def get(self, model, check_load=True, readonly=True, modified=False):
        if model.value[self.name]:
            return '%s,%d' % (model.value[self.name][0],
                    model.value[self.name][1][0])
        return False

    def set_client(self, model, value, test_state=False, force_change=False):
        internal = model.value[self.name]
        model.value[self.name] = value
        if (internal or False) != (model.value[self.name] or False):
            model.modified = True
            model.modified_fields.setdefault(self.name)
            self.sig_changed(model)
            model.signal('record-changed', model)

    def set(self, model, value, test_state=False, modified=False):
        if not value:
            model.value[self.name] = False
            return
        ref_model, ref_id = value.split(',')
        rpc2 = RPCProxy(ref_model)
        try:
            result = rpc2.name_get([ref_id], rpc.CONTEXT)
        except:
            return
        if result:
            model.value[self.name] = ref_model, result[0]
        else:
            model.value[self.name] = ref_model, (0, '')
        if modified:
            model.modified = True
            model.modified_fields.setdefault(self.name)

TYPES = {
    'char': CharField,
    'sha': CharField,
    'float_time': FloatField,
    'integer' : IntegerField,
    'float' : FloatField,
    'numeric' : FloatField,
    'many2one' : M2OField,
    'many2many' : M2MField,
    'one2many' : O2MField,
    'reference' : ReferenceField,
    'selection': SelectionField,
    'boolean': IntegerField,
    'datetime': DateTimeField,
}
