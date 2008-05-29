import re
import time
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
from tryton.signal_event import SignalEvent
import field
import datetime


class EvalEnvironment(object):

    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, item):
        if item == 'parent' and self.parent.parent:
            return EvalEnvironment(self.parent.parent)
        if item == "current_date":
            return datetime.datetime.today()
        if item == "time":
            return time
        return self.parent.get(includeid=True)[item]


class ModelRecord(SignalEvent):

    def __init__(self, resource, obj_id, window, group=None, parent=None, new=False ):
        super(ModelRecord, self).__init__()
        self.window = window
        self.resource = resource
        self.rpc = RPCProxy(self.resource)
        self.id = obj_id
        self._loaded = False
        self.parent = parent
        self.mgroup = group
        self.value = {}
        self.state_attrs = {}
        self.modified = False
        self.modified_fields = {}
        self.read_time = time.time()
        self.attachment_count = -1
        self.next = {}
        for key, val in self.mgroup.mfields.items():
            self.value[key] = val.create(self)
            if (new and val.attrs['type']=='one2many') \
                    and (val.attrs.get('mode','tree,form').startswith('form')):
                mod = self.value[key].model_new()
                self.value[key].model_add(mod)

    def __getitem__(self, name):
        if not self._loaded and self.id:
            ids =  [self.id]
            idx = self.mgroup.models.index(self)
            length = len(self.mgroup.models)
            n = 1
            while len(ids) < 80 and (idx - n >= 0 or idx + n < length) and n < 100:
                if idx - n >= 0:
                    model = self.mgroup.models[idx - n]
                    if not model._loaded:
                        ids.append(model.id)
                if idx + n < length:
                    model = self.mgroup.models[idx + n]
                    if not model._loaded:
                        ids.append(model.id)
                n += 1
            ctx = rpc.CONTEXT.copy()
            ctx.update(self.context_get())
            try:
                values = self.rpc.read(ids, self.mgroup.mfields.keys(), ctx)
            except Exception, exception:
                values = [{'id': x} for x in ids]
            for value in values:
                for model in self.mgroup.models:
                    if model.id == value['id']:
                        model.set(value, signal=True)
        return self.mgroup.mfields.get(name, False)

    def __repr__(self):
        return '<ModelRecord %s@%s>' % (self.id, self.resource)

    def is_modified(self):
        return self.modified

    def fields_get(self):
        return self.mgroup.mfields

    def _check_load(self):
        if not self._loaded:
            self.reload()
            return True
        return False

    def get_loaded(self):
        return self._loaded

    loaded = property(get_loaded)

    def get(self, get_readonly=True, includeid=False, check_load=True,
            get_modifiedonly=False):
        if check_load:
            self._check_load()
        value = []
        for name, mfield in self.mgroup.mfields.items():
            if (get_readonly or \
                    not mfield.get_state_attrs(self).get('readonly', False)) \
                and (not get_modifiedonly \
                    or (mfield.name in self.modified_fields \
                        or isinstance(mfield, field.O2MField))):
                value.append((name, mfield.get(self, readonly=get_readonly,
                    modified=get_modifiedonly)))
        value = dict(value)
        if includeid:
            value['id'] = self.id
        return value

    def cancel(self):
        self._loaded = False
        self.reload()

    def save(self, force_reload=True):
        self._check_load()
        if not self.id:
            value = self.get(get_readonly=True)
            try:
                self.id = self.rpc.create(value, self.context_get())
            except Exception, exception:
                self.id = rpc.process_exception(exception, self.window, 'object',
                        'execute', self.resource, 'create', value,
                        self.context_get())
                if not self.id:
                    return False
        else:
            if not self.is_modified():
                return self.id
            value = self.get(get_readonly=False, get_modifiedonly=True)
            context = self.context_get()
            context = context.copy()
            #XXX must compute delta on server side
            context['read_delta'] = time.time() - self.read_time
            args = ('object', 'execute', self.resource, 'write',
                    [self.id], value, context)
            try:
                if not rpc.execute(*args):
                    return False
            except Exception, exception:
                if not rpc.process_exception(exception, self.window, *args):
                    return False
        self._loaded = False
        if force_reload:
            self.reload()
        if self.mgroup:
            self.mgroup.writen(self.id)
        return self.id

    def default_get(self, domain=None, context=None):
        if domain is None:
            domain = []
        if len(self.mgroup.fields):
            try:
                val = self.rpc.default_get(self.mgroup.fields.keys(), context)
            except Exception, exception:
                rpc.process_exception(exception, self.window)
                return
            for clause in domain:
                if clause[0] in self.mgroup.fields:
                    if clause[1] == '=':
                        val[clause[0]] = clause[2]
                    if clause[1] == 'in' and len(clause[2]) == 1:
                        val[clause[0]] = clause[2][0]
            self.set_default(val)

    def name_get(self):
        try:
            name = self.rpc.name_get([self.id], rpc.CONTEXT)[0]
        except Exception, exception:
            rpc.process_exception(exception, self.window)
            return False
        return name

    def validate_set(self):
        change = self._check_load()
        for fname in self.mgroup.mfields:
            mfield = self.mgroup.mfields[fname]
            change = change or \
                    not mfield.get_state_attrs(self).get('valid', True)
            mfield.get_state_attrs(self)['valid'] = True
        if change:
            self.signal('record-changed')
        return change

    def validate(self):
        self._check_load()
        res = True
        for fname in self.mgroup.mfields:
            if not self.mgroup.mfields[fname].validate(self):
                res = False
        return res

    def _get_invalid_fields(self):
        res = []
        for fname, mfield in self.mgroup.mfields.items():
            if not mfield.get_state_attrs(self).get('valid', True):
                res.append((fname, mfield.attrs['string']))
        return dict(res)
    invalid_fields = property(_get_invalid_fields)

    def context_get(self):
        return self.mgroup.context

    def get_default(self):
        self._check_load()
        value = dict([(name, mfield.get_default(self))
                      for name, mfield in self.mgroup.mfields.items()])
        return value

    def set_default(self, val):
        for fieldname, value in val.items():
            if fieldname not in self.mgroup.mfields:
                continue
            self.mgroup.mfields[fieldname].set_default(self, value)
        self._loaded = True
        self.signal('record-changed')

    def set(self, val, modified=False, signal=True):
        later = {}
        for fieldname, value in val.items():
            if fieldname not in self.mgroup.mfields:
                continue
            if isinstance(self.mgroup.mfields[fieldname], field.O2MField):
                later[fieldname] = value
                continue
            self.mgroup.mfields[fieldname].set(self, value, modified=modified)
        for fieldname, value in later.items():
            self.mgroup.mfields[fieldname].set(self, value, modified=modified)
        self._loaded = True
        self.modified = modified
        if not self.modified:
            self.modified_fields = {}
        if signal:
            self.signal('record-changed')

    def reload(self):
        if not self.id:
            return
        ctx = rpc.CONTEXT.copy()
        ctx.update(self.context_get())
        try:
            res = self.rpc.read([self.id], self.mgroup.mfields.keys(), ctx)
        except Exception, exception:
            rpc.process_exception(exception, self.window)
            return
        if res:
            value = res[0]
            self.read_time = time.time()
            self.set(value)

    def expr_eval(self, dom, check_load=True):
        if not isinstance(dom, basestring):
            return dom
        if check_load:
            self._check_load()
        ctx = rpc.CONTEXT.copy()
        for name, mfield in self.mgroup.mfields.items():
            ctx[name] = mfield.get(self, check_load=check_load)

        ctx['current_date'] = datetime.datetime.today()
        ctx['time'] = time
        ctx['context'] = self.context_get()
        ctx['active_id'] = self.id
        if self.parent:
            ctx['parent'] = EvalEnvironment(self.parent)
        val = eval(dom, ctx)
        return val

    def on_change(self, fieldname, attr):
        args = {}
        if isinstance(attr, basestring):
            attr = eval(attr)
        for arg in attr:
            try:
                args[arg] = self.expr_eval(arg)
            except:
                args[arg] = False
        ids = self.id and [self.id] or []
        ctx = rpc.CONTEXT.copy()
        ctx.update(self.context_get())
        try:
            res = getattr(self.rpc, 'on_change_' + fieldname)(ids, args,
                    ctx)
        except Exception, exception:
            rpc.process_exception(exception, self.window)
            return
        if res:
            later = {}
            for fieldname, value in res.items():
                if fieldname not in self.mgroup.mfields:
                    continue
                if isinstance(self.mgroup.mfields[fieldname], field.O2MField):
                    later[fieldname] = value
                    continue
                self.mgroup.mfields[fieldname].set_on_change(self, value)
            for fieldname, value in later.items():
                self.mgroup.mfields[fieldname].set_on_change(self, value)
            self.signal('record-changed')

    def cond_default(self, field_name, value):
        ir_default = RPCProxy('ir.default')
        ctx = rpc.CONTEXT.copy()
        ctx.update(self.context_get())
        try:
            self.set_default(ir_default.get_default(self.resource,
                field_name + '=' + str(value), ctx))
        except Exception, exception:
            rpc.process_exception(exception, self.window)
            return False

    def get_attachment_count(self, reload=False):
        if not self.id:
            return 0
        if self.attachment_count < 0 or reload:
            ir_attachment = RPCProxy('ir.attachment')
            try:
                self.attachment_count = ir_attachment.search_count([
                    ('res_model', '=', self.resource),
                    ('res_id', '=', self.id),
                    ])
            except:
                return 0
        return self.attachment_count
