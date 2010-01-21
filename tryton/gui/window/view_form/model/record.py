#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import re
import time
from tryton.rpc import RPCProxy
import tryton.rpc as rpc
from tryton.signal_event import SignalEvent
from tryton.pyson import PYSONDecoder
import field
import datetime
import tryton.common as common
import logging


class EvalEnvironment(dict):

    def __init__(self, parent, check_load):
        super(EvalEnvironment, self).__init__()
        self.parent = parent
        self.check_load = check_load

    def __getitem__(self, item):
        if item == '_parent_' + self.parent.parent_name and self.parent.parent:
            return EvalEnvironment(self.parent.parent)
        return self.parent.get_eval(check_load=self.check_load)[item]

    def __getattr__(self, item):
        return self.__getitem__(item)

    def get(self, item, default=None):
        try:
            return self.__getattr__(item)
        except:
            pass
        return super(EvalEnvironment, self).get(item, default)

    def __nonzero__(self):
        return True

    def __str__(self):
        return str(self.parent)

    __repr__ = __str__


class ModelRecord(SignalEvent):

    id = -1


    def __init__(self, resource, obj_id, window, group=None, parent=None,
            parent_name='', new=False):
        global ID_COUNT
        super(ModelRecord, self).__init__()
        self.window = window
        self.resource = resource
        self.rpc = RPCProxy(self.resource)
        self.id = obj_id or ModelRecord.id
        if self.id < 0:
            ModelRecord.id -= 1
        self._loaded = set()
        self.parent = parent
        self.parent_name = parent_name
        self.mgroup = group
        self.value = {}
        self.state_attrs = {}
        self.__modified = False
        self.modified_fields = {}
        self._timestamp = None
        self.attachment_count = -1
        self.next = {}
        for key, val in self.mgroup.mfields.items():
            self.value[key] = val.create(self)
            if (new and val.attrs['type']=='one2many') \
                    and (val.attrs.get('mode','tree,form').startswith('form')):
                mod = self.value[key].model_new()
                self.value[key].model_add(mod)

    def __getitem__(self, name):
        if name not in self._loaded and self.id > 0:
            ids =  [self.id]
            idx = self.mgroup.models.index(self)
            length = len(self.mgroup.models)
            n = 1
            while len(ids) < 80 and (idx - n >= 0 or idx + n < length) and n < 100:
                if idx - n >= 0:
                    model = self.mgroup.models[idx - n]
                    if name not in model._loaded and model.id > 0:
                        ids.append(model.id)
                if idx + n < length:
                    model = self.mgroup.models[idx + n]
                    if name not in model._loaded and model.id > 0:
                        ids.append(model.id)
                n += 1
            ctx = rpc.CONTEXT.copy()
            ctx.update(self.context_get())
            args = (ids, self.mgroup.mfields.keys() + \
                        [x + '.rec_name' for x in self.mgroup.mfields.keys()
                            if self.mgroup.fields[x]['type'] \
                                    in ('many2one', 'reference')] + \
                        ['_timestamp'], ctx)
            try:
                values = self.rpc.read(*args)
            except Exception, exception:
                common.process_exception(exception, self.window)
                try:
                    values = self.rpc.read(args)
                except:
                    log = logging.getLogger('record')
                    log.error('%s' % exception.args[-1])
                    values = [{'id': x} for x in ids]
            model_set = None
            signal = True
            if len(values) > 10:
                signal = False
            id2value = dict((value['id'], value) for value in values)
            for model in self.mgroup.models:
                value = id2value.get(model.id)
                if value:
                    model.set(value, signal=signal)
                    model_set = model
            if not signal and model_set:
                model_set.signal('record-changed')
        return self.mgroup.mfields.get(name, False)

    def __repr__(self):
        return '<ModelRecord %s@%s>' % (self.id, self.resource)

    def get_modified(self):
        return self.__modified

    def set_modified(self, value):
        self.__modified = value
        if value:
            self.signal('record-modified')

    modified = property(get_modified, set_modified)

    def is_modified(self):
        return self.modified

    def fields_get(self):
        return self.mgroup.mfields

    def _check_load(self):
        if not self.loaded:
            self.reload()
            return True
        return False

    def get_loaded(self):
        return set(self.mgroup.mfields.keys()) == self._loaded

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
                   or mfield.name in self.modified_fields):
                value.append((name, mfield.get(self, check_load=check_load,
                    readonly=get_readonly, modified=get_modifiedonly)))
        value = dict(value)
        if includeid:
            value['id'] = self.id
        return value

    def get_eval(self, check_load=True):
        if check_load:
            self._check_load()
        value = {}
        for name, mfield in self.mgroup.mfields.items():
            value[name] = mfield.get_eval(self, check_load=check_load)
        value['id'] = self.id
        return value

    def cancel(self):
        self._loaded.clear()
        self.reload()

    def get_timestamp(self):
        result = {self.resource + ',' + str(self.id): self._timestamp}
        for name, mfield in self.mgroup.mfields.items():
            result.update(mfield.get_timestamp(self))
        return result

    def save(self, force_reload=True):
        self._check_load()
        if self.id < 0:
            value = self.get(get_readonly=True)
            args = ('model', self.resource, 'create', value, self.context_get())
            try:
                self.id = rpc.execute(*args)
            except Exception, exception:
                res = common.process_exception(exception, self.window, *args)
                if not res:
                    return False
                self.id = res
        else:
            if not self.is_modified():
                return self.id
            value = self.get(get_readonly=True, get_modifiedonly=True)
            context = self.context_get()
            context = context.copy()
            context['_timestamp'] = self.get_timestamp()
            args = ('model', self.resource, 'write', [self.id], value, context)
            try:
                if not rpc.execute(*args):
                    return False
            except Exception, exception:
                if not common.process_exception(exception, self.window, *args):
                    return False
        self._loaded.clear()
        if force_reload:
            self.reload()
        if self.mgroup:
            self.mgroup.writen(self.id)
        return self.id

    def default_get(self, domain=None, context=None):
        if len(self.mgroup.fields):
            try:
                val = self.rpc.default_get(self.mgroup.fields.keys(), context)
            except Exception, exception:
                common.process_exception(exception, self.window)
                val = self.rpc.default_get(self.mgroup.fields.keys(), context)
            self.set_default(val)

    def rec_name(self):
        ctx = rpc.CONTEXT.copy()
        ctx.update(self.context_get())
        try:
            name = self.rpc.read(self.id, ['rec_name'], ctx)['rec_name']
        except Exception, exception:
            common.process_exception(exception, self.window)
            name = self.rpc.read(self.id, ['rec_name'], ctx)['rec_name']
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

    def set_default(self, val, signal=True, modified=False):
        for fieldname, value in val.items():
            if fieldname not in self.mgroup.mfields:
                continue
            if isinstance(self.mgroup.mfields[fieldname], field.M2OField):
                if fieldname + '.rec_name' in val:
                    value = (value, val[fieldname + '.rec_name'])
            elif isinstance(self.mgroup.mfields[fieldname], field.ReferenceField):
                if value:
                    ref_model, ref_id = value.split(',', 1)
                    if fieldname + '.rec_name' in val:
                        value = ref_model, (ref_id, val[fieldname + '.rec_name'])
                    else:
                        value = ref_model, (ref_id, ref_id)
            self.mgroup.mfields[fieldname].set_default(self, value,
                    modified=modified)
            self._loaded.add(fieldname)
        if signal:
            self.signal('record-changed')

    def set(self, val, modified=False, signal=True):
        later = {}
        for fieldname, value in val.items():
            if fieldname == '_timestamp':
                self._timestamp = value
                continue
            if fieldname not in self.mgroup.mfields:
                continue
            if isinstance(self.mgroup.mfields[fieldname], field.O2MField):
                later[fieldname] = value
                continue
            if isinstance(self.mgroup.mfields[fieldname], field.M2OField):
                if fieldname + '.rec_name' in val:
                    value = (value, val[fieldname + '.rec_name'])
            elif isinstance(self.mgroup.mfields[fieldname], field.ReferenceField):
                if value:
                    ref_model, ref_id = value.split(',', 1)
                    if fieldname + '.rec_name' in val:
                        value = ref_model, (ref_id, val[fieldname + '.rec_name'])
                    else:
                        value = ref_model, (ref_id, ref_id)
            self.mgroup.mfields[fieldname].set(self, value, modified=modified)
            self._loaded.add(fieldname)
        for fieldname, value in later.items():
            self.mgroup.mfields[fieldname].set(self, value, modified=modified)
            self._loaded.add(fieldname)
        self.modified = modified
        if not self.modified:
            self.modified_fields = {}
        if signal:
            self.signal('record-changed')

    def reload(self):
        if self.id < 0:
            return
        self['*']
        self.validate()

    def expr_eval(self, expr, check_load=False):
        if not isinstance(expr, basestring):
            return expr
        if check_load:
            self._check_load()
        ctx = rpc.CONTEXT.copy()
        for name, mfield in self.mgroup.mfields.items():
            ctx[name] = mfield.get_eval(self, check_load=check_load)

        ctx['context'] = self.context_get()
        ctx['active_id'] = self.id
        ctx['_user'] = rpc._USER
        if self.parent and self.parent_name:
            ctx['_parent_' + self.parent_name] = EvalEnvironment(self.parent,
                    check_load)
        val = PYSONDecoder(ctx).decode(expr)
        return val

    def _get_on_change_args(self, args):
        res = {}
        values = {}
        for name, mfield in self.mgroup.mfields.items():
            values[name] = mfield.get_eval(self, check_load=False)
        if self.parent and self.parent_name:
            values['_parent_' + self.parent_name] = EvalEnvironment(self.parent,
                    False)
        for arg in args:
            scope = values
            for i in arg.split('.'):
                if i not in scope:
                    scope = False
                    break
                scope = scope[i]
            res[arg] = scope
        return res

    def on_change(self, fieldname, attr):
        if isinstance(attr, basestring):
            attr = PYSONDecoder().decode(attr)
        args = self._get_on_change_args(attr)
        ids = [self.id]
        ctx = rpc.CONTEXT.copy()
        ctx.update(self.context_get())
        try:
            res = getattr(self.rpc, 'on_change_' + fieldname)(ids, args,
                    ctx)
        except Exception, exception:
            common.process_exception(exception, self.window)
            res = getattr(self.rpc, 'on_change_' + fieldname)(ids, args,
                    ctx)
        if res:
            later = {}
            for fieldname, value in res.items():
                if fieldname not in self.mgroup.mfields:
                    continue
                if isinstance(self.mgroup.mfields[fieldname], field.O2MField):
                    later[fieldname] = value
                    continue
                if isinstance(self.mgroup.mfields[fieldname], field.M2OField):
                    if fieldname + '.rec_name' in res:
                        value = (value, res[fieldname + '.rec_name'])
                elif isinstance(self.mgroup.mfields[fieldname],
                        field.ReferenceField):
                    if value:
                        ref_mode, ref_id = value.split(',', 1)
                        if fieldname + '.rec_name' in res:
                            value = ref_model, (ref_id,
                                    res[fieldname + '.rec_name'])
                        else:
                            value = ref_model, (ref_id, ref_id)
                self.mgroup.mfields[fieldname].set_on_change(self, value)
            for fieldname, value in later.items():
                self.mgroup.mfields[fieldname].set_on_change(self, value)
            self.signal('record-changed')

    def on_change_with(self, field_name):
        for fieldname in self.mgroup.mfields:
            on_change_with = self.mgroup.mfields[fieldname].attrs.get(
                    'on_change_with')
            if not on_change_with:
                continue
            if field_name not in on_change_with:
                continue
            if field_name == fieldname:
                continue
            args = self._get_on_change_args(on_change_with)
            ids = [self.id]
            ctx = rpc.CONTEXT.copy()
            ctx.update(self.context_get())
            try:
                res = getattr(self.rpc, 'on_change_with_' + fieldname)(ids,
                        args, ctx)
            except Exception, exception:
                common.process_exception(exception, self.window)
                res = getattr(self.rpc, 'on_change_with_' + fieldname)(ids,
                        args, ctx)
            self.mgroup.mfields[fieldname].set_on_change(self, res)

    def cond_default(self, field_name, value):
        ir_default = RPCProxy('ir.default')
        ctx = rpc.CONTEXT.copy()
        ctx.update(self.context_get())
        try:
            self.set_default(ir_default.get_default(self.resource,
                field_name + '=' + str(value), ctx))
        except Exception, exception:
            common.process_exception(exception, self.window)
            self.set_default(ir_default.get_default(self.resource,
                field_name + '=' + str(value), ctx))

    def get_attachment_count(self, reload=False):
        if self.id < 0:
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
