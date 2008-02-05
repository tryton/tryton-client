import re
import time
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
from tryton.signal_event import SignalEvent
import field


class EvalEnvironment(object):

    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, item):
        if item == 'parent' and self.parent.parent:
            return EvalEnvironment(self.parent.parent)
        if item == "current_date":
            return time.strftime('%Y-%m-%d')
        if item == "time":
            return time
        return self.parent.get(includeid=True)[item]


class ModelRecord(SignalEvent):

    def __init__(self, resource, obj_id, group=None, parent=None, new=False ):
        super(ModelRecord, self).__init__()
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
        for key, val in self.mgroup.mfields.items():
            self.value[key] = val.create(self)
            if (new and val.attrs['type']=='one2many') \
                    and (val.attrs.get('mode','tree,form').startswith('form')):
                mod = self.value[key].model_new()
                self.value[key].model_add(mod)

    def __getitem__(self, name):
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
            value = self.get(get_readonly=False)
            self.id = self.rpc.create(value, self.context_get())
        else:
            if not self.is_modified():
                return self.id
            value = self.get(get_readonly=False, get_modifiedonly=True)
            context = self.context_get()
            context = context.copy()
            #XXX must compute delta on server side
            context['read_delta'] = time.time() - self.read_time
            if not rpc.session.rpc_exec_auth('/object', 'execute',
                    self.resource, 'write', [self.id], value, context):
                return False
        self._loaded = False
        if force_reload:
            self.reload()
        return self.id

    def default_get(self, domain=None, context=None):
        if domain is None:
            domain = []
        if len(self.mgroup.fields):
            val = self.rpc.default_get(self.mgroup.fields.keys(), context)
            for clause in domain:
                if clause[0] in self.mgroup.fields:
                    if clause[1] == '=':
                        val[clause[0]] = clause[2]
                    if clause[1] == 'in' and len(d[2]) == 1:
                        val[clause[0]] = clause[2][0]
            self.set_default(val)

    def name_get(self):
        name = self.rpc.name_get([self.id], rpc.session.context)[0]
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
        ctx = rpc.session.context.copy()
        ctx.update(self.context_get())
        res = self.rpc.read([self.id], self.mgroup.mfields.keys(), ctx)
        if res:
            value = res[0]
            self.read_time = time.time()
            self.set(value)

    def expr_eval(self, dom, check_load=True):
        if not isinstance(dom, basestring):
            return dom
        if check_load:
            self._check_load()
        ctx = {}
        for name, mfield in self.mgroup.mfields.items():
            ctx[name] = mfield.get(self, check_load=check_load)

        ctx['current_date'] = time.strftime('%Y-%m-%d')
        ctx['time'] = time
        ctx['context'] = self.context_get()
        ctx['active_id'] = self.id
        if self.parent:
            ctx['parent'] = EvalEnvironment(self.parent)
        val = eval(dom, ctx)
        return val

    #XXX Shoud use changes of attributes (ro, ...)
    def on_change(self, callback):
        match = re.match('^(.*?)\((.*)\)$', callback)
        if not match:
            raise Exception, 'ERROR: Wrong on_change trigger: %s' % callback
        func_name = match.group(1)
        arg_names = [n.strip() for n in match.group(2).split(',')]
        args = [self.expr_eval(arg) for arg in arg_names]
        ids = self.id and [self.id] or []
        response = getattr(self.rpc, func_name)(ids, *args)
        if response:
            self.set(response.get('value', {}), modified=True)
            if 'domain' in response:
                for fieldname, value in response['domain'].items():
                    if fieldname not in self.mgroup.mfields:
                        continue
                    self.mgroup.mfields[fieldname].attrs['domain'] = value
        self.signal('record-changed')

    def cond_default(self, field_name, value):
        ir_default = RPCProxy('ir.default')
        ctx = rpc.session.context.copy()
        ctx.update(self.context_get())
        self.set_default(ir_default.get_default(self.resource,
            field_name + '=' + str(value), ctx))

    def get_attachment_count(self, reload=False):
        if not self.id:
            return 0
        if self.attachment_count < 0 or reload:
            ir_attachment = RPCProxy('ir.attachment')
            self.attachment_count = ir_attachment.search_count([
                ('res_model', '=', self.resource),
                ('res_id', '=', self.id),
                ])
        return self.attachment_count
