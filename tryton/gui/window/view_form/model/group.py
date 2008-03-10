from tryton.rpc import RPCProxy
import tryton.rpc as rpc
from record import ModelRecord
import field
from tryton.signal_event import SignalEvent


class ModelList(list):
    def __init__(self, screen):
        super(ModelList, self).__init__()
        self.lock_signal = False
        self.__screen = screen

    def insert(self, pos, obj):
        if pos >= 1:
            self.__getitem__(pos - 1).next = obj
        if pos < self.__len__():
            obj.next = self.__getitem__(pos)
        else:
            obj.next = None
        super(ModelList, self).insert(pos, obj)
        if not self.lock_signal:
            self.__screen.signal('record-changed', ('record-added', pos))

    def append(self, obj):
        if self.__len__() >= 1:
            self.__getitem__(self.__len__() - 1).next = obj
        super(ModelList, self).append(obj)
        if not self.lock_signal:
            self.__screen.signal('record-changed', ('record-added', -1))

    def remove(self, obj):
        idx = self.index(obj)
        if idx >= 1:
            if idx + 1 < self.__len__():
                self.__getitem__(idx - 1).next = self.__getitem__(idx + 1)
            else:
                self.__getitem__(idx - 1).next = None
        super(ModelList, self).remove(obj)
        if not self.lock_signal:
            self.__screen.signal('record-changed', ('record-removed', idx))

    def clear(self):
        while self:
            self.pop()
            if not self.lock_signal:
                self.__screen.signal('record-changed',
                        ('record-removed', len(self)))

    def move(self, obj, pos):
        self.lock_signal = True
        if self.__len__() > pos:
            idx = self.index(obj)
            self.remove(obj)
            if pos > idx:
                pos -= 1
            self.insert(pos, obj)
        else:
            self.remove(obj)
            self.append(obj)
        self.lock_signal = False

    def __setitem__(self, key, value):
        super(ModelList, self).__setitem__(key, value)
        if not self.lock_signal:
            self.__screen.signal('record-changed', ('record-changed', key))


class ModelRecordGroup(SignalEvent):

    def __init__(self, resource, fields, window, ids=None, parent=None, context=None):
        super(ModelRecordGroup, self).__init__()
        self.window = window
        self.parent = parent
        self._context = context or {}
        self._context.update(rpc.CONTEXT)
        self.resource = resource
        self.rpc = RPCProxy(resource)
        self.fields = fields
        self.mfields = {}
        ModelRecordGroup.mfields_load(fields.keys(), self)
        self.models = ModelList(self)
        self.current_idx = None
        self.load(ids)
        self.model_removed = []
        self.on_write = ''

    @staticmethod
    def mfields_load(fkeys, models):
        for fname in fkeys:
            fvalue = models.fields[fname]
            modelfield = field.ModelField(fvalue['type'])
            fvalue['name'] = fname
            models.mfields[fname] = modelfield(models, fvalue)

    def save(self):
        for model in self.models:
            saved = model.save()
            self.writen(saved)

    def writen(self, edited_id):
        if not self.on_write:
            return
        try:
            new_ids = getattr(self.rpc, self.on_write)(edited_id, self.context)
        except Exception, exception:
            rpc.process_exception(exception, self.window)
            return
        model_idx = self.models.index(self[edited_id])
        result = False
        for new_id in new_ids:
            cont = False
            for model in self.models:
                if model.id == new_id:
                    cont = True
                    model.reload()
            if cont:
                continue
            newmod = ModelRecord(self.resource, new_id, self.window,
                    parent=self.parent, group=self)
            newmod.reload()
            if not result:
                result = newmod
            new_index = min(model_idx, len(self.models)-1)
            self.model_add(newmod, new_index)
        return result

    def pre_load(self, ids, display=True):
        if not ids:
            return True
        if len(ids)>10:
            self.models.lock_signal = True
        for obj_id in ids:
            newmod = ModelRecord(self.resource, obj_id, self.window,
                    parent=self.parent, group=self)
            self.model_add(newmod)
            if display:
                self.signal('model-changed', newmod)
        if len(ids)>10:
            self.models.lock_signal = False
            self.signal('record-cleared')
        return True

    def _load_for(self, values):
        if len(values)>10:
            self.models.lock_signal = True
        for value in values:
            for model in self.models:
                if model.id == value['id']:
                    model.set(value)
        if len(values)>10:
            self.models.lock_signal = False
            self.signal('record-cleared')

    def load(self, ids, display=True):
        if not ids:
            return True
        if not self.fields:
            return self.pre_load(ids, display)

        self.models.lock_signal = True
        for id in ids:
            newmod = ModelRecord(self.resource, id, self.window,
                    parent=self.parent, group=self)
            self.models.append(newmod)
            newmod.signal_connect(self, 'record-changed', self._record_changed)
        self.models.lock_signal = False

        ctx = rpc.CONTEXT.copy()
        ctx.update(self.context)
        try:
            values = self.rpc.read(ids[:80], self.fields.keys(), ctx)
        except Exception, exception:
            rpc.process_exception(exception, self.window)
            return False
        if not values:
            return False
        self._load_for(values)

        #newmod = False
        #if newmod and display:
        #    self.signal('model-changed', newmod)
        self.current_idx = 0
        return True

    def clear(self):
        self.models.clear()
        self.model_removed = []

    def _get_context(self):
        ctx = {}
        ctx.update(self._context)
        return ctx
    context = property(_get_context)

    def model_add(self, model, position=-1):
        #TODO To be checked
        if not model.mgroup is self:
            fields = {}
            for i in model.mgroup.fields:
                fields[model.mgroup.fields[i]['name']] = \
                        model.mgroup.fields[i]
            self.add_fields(fields, self)
            self.add_fields(self.fields, model.mgroup)
            model.mgroup = self

        if position == -1:
            self.models.append(model)
        else:
            self.models.insert(position, model)
        self.current_idx = position
        model.parent = self.parent
        model.window = self.window
        model.signal_connect(self, 'record-changed', self._record_changed)
        return model

    def model_move(self, model, position=0):
        self.models.move(model, position)

    def set_sequence(self, field='sequence'):
        index = 0
        for model in self.models:
            if model[field]:
                if index >= model[field].get(model):
                    index += 1
                    model[field].set(model, index, modified=True)
                else:
                    index = model[field].get(model)
                if model.id:
                    model.save()

    def model_new(self, default=True, domain=None, context=None):
        newmod = ModelRecord(self.resource, None, self.window, group=self,
                parent=self.parent, new=True)
        newmod.signal_connect(self, 'record-changed', self._record_changed)
        if default:
            ctx = {}
            ctx.update(context or {})
            ctx.update(self.context)
            newmod.default_get(domain, ctx)
        self.signal('model-changed', newmod)
        return newmod

    def model_remove(self, model):
        idx = self.models.index(model)
        self.models.remove(model)
        if model.parent:
            model.parent.modified = True
        if self.models:
            self.current_idx = min(idx, len(self.models)-1)
        else:
            self.current_idx = None

    def _record_changed(self, model, signal_data):
        self.signal('model-changed', model)

    def prev(self):
        if self.models and self.current_idx is not None:
            self.current_idx = (self.current_idx - 1) % len(self.models)
        elif self.models:
            self.current_idx = 0
        else:
            return None
        return self.models[self.current_idx]

    def next(self):
        if self.models and self.current_idx is not None:
            self.current_idx = (self.current_idx + 1) % len(self.models)
        elif self.models:
            self.current_idx = 0
        else:
            return None
        return self.models[self.current_idx]

    def remove(self, model):
        idx = self.models.index(model)
        if self.models[idx].id:
            self.model_removed.append(self.models[idx].id)
        if model.parent:
            model.parent.modified = True
        self.models.remove(self.models[idx])

    def add_fields_custom(self, fields, models):
        to_add = []
        for field_add in fields.keys():
            if not field_add in models.fields:
                models.fields[field_add] = fields[field_add]
                models.fields[field_add]['name'] = field_add
                to_add.append(field_add)
            else:
                models.fields[field_add].update(fields[field_add])
        ModelRecordGroup.mfields_load(to_add, models)
        for fname in to_add:
            for model in models.models:
                model.value[fname] = self.mfields[fname].create(model)
        return to_add

    def add_fields(self, fields, models, context=None):
        if context is None:
            context = {}
        to_add = self.add_fields_custom(fields, models)
        models = models.models
        if not len(models):
            return True

        old = []
        new = []
        for model in models:
            if model.id:
                if model.is_modified():
                    old.append(model.id)
                else:
                    model._loaded = False
            else:
                new.append(model)
        ctx = context.copy()
        if len(old) and len(to_add):
            ctx.update(rpc.CONTEXT)
            ctx.update(self.context)
            try:
                values = self.rpc.read(old, to_add, ctx)
            except Exception, exception:
                rpc.process_exception(exception, self.window)
                return False
            if values:
                for value in values:
                    value_id = value['id']
                    if 'id' not in to_add:
                        del value['id']
                    self[value_id].set(value, signal=False)
        if len(new) and len(to_add):
            ctx.update(self.context)
            try:
                values = self.rpc.default_get(to_add, ctx)
            except Exception, exception:
                rpc.process_exception(exception, self.window)
                return False
            for field_to_add in to_add:
                if field_to_add not in values:
                    values[field_to_add] = False
            for mod in new:
                mod.set_default(values)

    def __iter__(self):
        return iter(self.models)

    def get_by_id(self, m_id):
        for model in self.models:
            if model.id == m_id:
                return model

    __getitem__ = get_by_id
