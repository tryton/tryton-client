# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import operator

from tryton import rpc
from tryton.common import MODELACCESS, RPCException, RPCExecute
from tryton.common.domain_inversion import is_leaf

from .field import Field, M2OField, ReferenceField
from .record import Record


class Group(list):

    def __init__(self, model_name, fields, ids=None, parent=None,
            parent_name='', child_name='', context=None, domain=None,
            readonly=False, parent_datetime_field=None):
        super(Group, self).__init__()
        if domain is None:
            domain = []
        self.__domain = domain
        self.__domain4inversion = None
        self.lock_signal = False
        self.screens = []
        self.parent = parent
        self.parent_name = parent_name or ''
        self.children = []
        self.child_name = child_name
        self.parent_datetime_field = parent_datetime_field
        self._context = context or {}
        self.model_name = model_name
        self.fields = {}
        self.load_fields(fields)
        self.current_idx = None
        self.load(ids)
        self.record_deleted, self.record_removed = [], []
        self.on_write = set()
        self.__readonly = readonly
        self.__id2record = {}
        self.__field_childs = None
        self.exclude_field = None
        self.skip_model_access = False

        if self.parent and self.parent.model_name == model_name:
            self.parent.group.children.append(self)

    @property
    def readonly(self):
        # Must skip res.user for Preference windows
        if (self.context.get('_datetime')
                or (not (MODELACCESS[self.model_name]['write']
                        or MODELACCESS[self.model_name]['create'])
                    and not self.skip_model_access)):
            return True
        return self.__readonly

    @readonly.setter
    def readonly(self, value):
        self.__readonly = value

    @property
    def domain(self):
        if self.parent and self.child_name:
            field = self.parent.group.fields[self.child_name]
            return [self.__domain, field.domain_get(self.parent)]
        return self.__domain

    def clean4inversion(self, domain):
        "This method will replace non relevant fields for domain inversion"
        if domain in ([], ()):
            return []
        head, tail = domain[0], domain[1:]
        if head in ('AND', 'OR'):
            pass
        elif is_leaf(head):
            field = head[0]
            if (field in self.fields
                    and self.fields[field].attrs.get('readonly')):
                head = []
        else:
            head = self.clean4inversion(head)
        return [head] + self.clean4inversion(tail)

    def __get_domain4inversion(self):
        domain = self.domain
        if (self.__domain4inversion is None
                or self.__domain4inversion[0] != domain):
            self.__domain4inversion = (
                domain, self.clean4inversion(domain))
        domain, domain4inversion = self.__domain4inversion
        return domain4inversion

    domain4inversion = property(__get_domain4inversion)

    def insert(self, pos, record):
        assert record.group is self
        pos = min(pos, len(self))
        if pos >= 1:
            self.__getitem__(pos - 1).next[id(self)] = record
        if pos < self.__len__():
            record.next[id(self)] = self.__getitem__(pos)
        else:
            record.next[id(self)] = None
        super(Group, self).insert(pos, record)
        self.__id2record[record.id] = record
        if not self.lock_signal:
            self._group_list_changed('record-added', record, pos)

    def append(self, record):
        assert record.group is self
        if self.__len__() >= 1:
            self.__getitem__(self.__len__() - 1).next[id(self)] = record
        record.next[id(self)] = None
        super(Group, self).append(record)
        self.__id2record[record.id] = record
        if not self.lock_signal:
            self._group_list_changed(
                'record-added', record, self.__len__() - 1)

    def _remove(self, record):
        idx = self.index(record)
        if idx >= 1:
            if idx + 1 < self.__len__():
                self.__getitem__(idx - 1).next[id(self)] = \
                    self.__getitem__(idx + 1)
            else:
                self.__getitem__(idx - 1).next[id(self)] = None
        self._group_list_changed('record-removed', record, idx)
        super(Group, self).remove(record)
        del self.__id2record[record.id]

    def clear(self):
        # Use reversed order to minimize the cursor reposition as the cursor
        # has more chances to be on top of the list.
        length = self.__len__()
        for record in reversed(self[:]):
            # Destroy record before propagating the signal to recursively
            # destroy also the underlying records
            record.destroy()
            self._group_list_changed('record-removed', record, length - 1)
            self.pop()
            length -= 1
        self.__id2record = {}
        self.record_removed, self.record_deleted = [], []

    def move(self, record, pos):
        if self.__len__() > pos >= 0:
            idx = self.index(record)
            self._remove(record)
            if pos > idx:
                pos -= 1
            self.insert(pos, record)
        else:
            self._remove(record)
            self.append(record)

    def __repr__(self):
        return '<Group %s at %s>' % (self.model_name, id(self))

    def load_fields(self, fields):
        for name, attr in fields.items():
            field = Field.get_field(attr['type'])
            attr['name'] = name
            self.fields[name] = field(attr)

    def save(self):
        saved = []
        for record in self:
            saved.append(record.save(force_reload=False))
        if self.record_deleted:
            for record in self.record_deleted:
                self._remove(record)
                record.destroy()
            self.delete(self.record_deleted)
            del self.record_deleted[:]
        return saved

    def delete(self, records):
        if not records:
            return
        root_group = self.root_group
        assert all(r.model_name == self.model_name for r in records)
        assert all(r.group.root_group == root_group for r in records)
        records = [r for r in records if r.id >= 0]
        ctx = self.context
        ctx['_timestamp'] = {}
        for rec in records:
            ctx['_timestamp'].update(rec.get_timestamp())
        record_ids = set(r.id for r in records)
        reload_ids = set(root_group.on_write_ids(list(record_ids)))
        reload_ids -= record_ids
        reload_ids = list(reload_ids)
        try:
            RPCExecute('model', self.model_name, 'delete', list(record_ids),
                context=ctx)
        except RPCException:
            return False
        for rec in records:
            rec.destroy()
        if reload_ids:
            root_group.reload(reload_ids)
        return True

    @property
    def root_group(self):
        root = self
        parent = self.parent
        while parent:
            root = parent.group
            parent = parent.parent
        return root

    def written(self, ids):
        if isinstance(ids, int):
            ids = [ids]
        ids = [x for x in self.on_write_ids(ids) or [] if x not in ids]
        if not ids:
            return
        self.root_group.reload(ids)
        return ids

    def reload(self, ids):
        for child in self.children:
            child.reload(ids)
        for id_ in ids:
            record = self.get(id_)
            if record and not record.modified:
                record.cancel()

    def on_write_ids(self, ids):
        if not self.on_write:
            return []
        res = []
        for fnct in self.on_write:
            try:
                res += RPCExecute('model', self.model_name, fnct, ids,
                    context=self.context)
            except RPCException:
                return []
        return list({}.fromkeys(res))

    def load(self, ids, modified=False, position=-1):
        if not ids:
            return True

        if len(ids) > 1:
            self.lock_signal = True

        new_records = []
        for id in ids:
            new_record = self.get(id)
            if not new_record:
                new_record = Record(self.model_name, id, group=self)
                if position == -1:
                    self.append(new_record)
                else:
                    self.insert(position, new_record)
                    position += 1
            new_records.append(new_record)

        # Remove previously removed or deleted records
        for record in self.record_removed[:]:
            if record.id in ids:
                self.record_removed.remove(record)
        for record in self.record_deleted[:]:
            if record.id in ids:
                self.record_deleted.remove(record)

        if self.lock_signal:
            self.lock_signal = False
            self._group_list_changed('group-cleared')

        if new_records and modified:
            for record in new_records:
                record.modified_fields.setdefault('id')
            self.record_modified()

        self.current_idx = 0
        return True

    @property
    def context(self):
        return self._get_context(local=False)

    @property
    def local_context(self):
        return self._get_context(local=True)

    def _get_context(self, local=False):
        if not local:
            ctx = rpc.CONTEXT.copy()
        else:
            ctx = {}
        if self.parent:
            parent_context = self.parent.get_context(local=local)
            ctx.update(parent_context)
            if self.child_name in self.parent.group.fields:
                field = self.parent.group.fields[self.child_name]
                ctx.update(field.get_context(
                        self.parent, parent_context, local=local))
        ctx.update(self._context)
        if self.parent_datetime_field:
            ctx['_datetime'] = self.parent.get_eval(
                )[self.parent_datetime_field]
        return ctx

    @context.setter
    def context(self, value):
        self._context = value.copy()

    def add(self, record, position=-1, modified=True):
        if record.group is not self:
            record.group = self
        if record not in self:
            if position == -1:
                self.append(record)
            else:
                self.insert(position, record)
        for record_rm in self.record_removed:
            if record_rm.id == record.id:
                self.record_removed.remove(record_rm)
        for record_del in self.record_deleted:
            if record_del.id == record.id:
                self.record_deleted.remove(record_del)
        self.current_idx = position
        record.modified_fields.setdefault('id')
        if modified:
            # Set parent field to trigger on_change
            if self.parent and self.parent_name in self.fields:
                field = self.fields[self.parent_name]
                if isinstance(field, (M2OField, ReferenceField)):
                    value = self.parent.id, ''
                    if isinstance(field, ReferenceField):
                        value = self.parent.model_name, value
                    field.set_client(record, value)
        return record

    def set_sequence(self, field='sequence', position=-1):
        changed = False
        prev = None
        if position == 0:
            cmp = operator.gt
        else:
            cmp = operator.lt
        for record in self:
            # Assume not loaded records are correctly ordered
            # as far as we do not change any previous records.
            if record.get_loaded([field]) or changed or record.id < 0:
                if prev:
                    index = prev[field].get(prev)
                else:
                    index = None
                update = False
                value = record[field].get(record)
                if value is None:
                    if index:
                        update = True
                    elif prev:
                        if record.id >= 0:
                            update = cmp(record.id, prev.id)
                        elif position == 0:
                            update = True
                elif value == index:
                    if prev:
                        if record.id >= 0:
                            update = cmp(record.id, prev.id)
                        elif position == 0:
                            update = True
                elif value <= (index or 0):
                    update = True
                if update:
                    if index is None:
                        index = 0
                    index += 1
                    record[field].set_client(record, index)
                    changed = record
            prev = record
        if changed:
            self.record_modified()

    def new(self, default=True, obj_id=None, rec_name=None):
        record = Record(self.model_name, obj_id, group=self)
        if default:
            record.default_get(rec_name=rec_name)
        return record

    def unremove(self, record, modified=True):
        if record in self.record_removed:
            self.record_removed.remove(record)
        if record in self.record_deleted:
            self.record_deleted.remove(record)
        if modified:
            self.record_modified()

    def remove(self, record, remove=False, modified=True, force_remove=False):
        idx = self.index(record)
        if record.id >= 0:
            if remove:
                if record in self.record_deleted:
                    self.record_deleted.remove(record)
                if record not in self.record_removed:
                    self.record_removed.append(record)
            else:
                if record in self.record_removed:
                    self.record_removed.remove(record)
                if record not in self.record_deleted:
                    self.record_deleted.append(record)
        record.modified_fields.setdefault('id')
        if record.id < 0 or force_remove:
            self._remove(record)

        if len(self):
            self.current_idx = min(idx, len(self) - 1)
        else:
            self.current_idx = None

        if modified:
            self.record_modified()

    def prev(self):
        if len(self) and self.current_idx is not None:
            self.current_idx = (self.current_idx - 1) % len(self)
        elif len(self):
            self.current_idx = 0
        else:
            return None
        return self[self.current_idx]

    def __next__(self):
        if len(self) and self.current_idx is not None:
            self.current_idx = (self.current_idx + 1) % len(self)
        elif len(self):
            self.current_idx = 0
        else:
            return None
        return self[self.current_idx]

    def add_fields(self, fields):
        to_add = {}
        for name, attr in fields.items():
            if name not in self.fields:
                to_add[name] = attr
            else:
                self.fields[name].attrs.update(attr)
        self.load_fields(to_add)

        if not len(self):
            return True

        new = []
        for record in self:
            if record.id < 0:
                new.append(record)

        if len(new) and len(to_add):
            try:
                values = RPCExecute('model', self.model_name, 'default_get',
                    list(to_add.keys()), context=self.context)
            except RPCException:
                return False
            for record in new:
                record.set_default(values, modified=False)
            # Trigger modified only once with the last record
            self.record_modified()

    def get(self, id):
        'Return record with the id'
        return self.__id2record.get(id)

    def id_changed(self, old_id):
        'Update index for old id'
        record = self.__id2record[old_id]
        self.__id2record[record.id] = record
        del self.__id2record[old_id]

    def destroy(self):
        if self.parent:
            try:
                self.parent.group.children.remove(self)
            except ValueError:
                pass
        # One2Many connect the group to itself to send modified to the parent
        # but as we are destroying the group, we do not need to notify the
        # parent otherwise it will trigger unnecessary display.
        self.screens.clear()
        self.parent = None

    def get_by_path(self, path):
        'return record by path'
        group = self
        record = None
        for child_name, id_ in path:
            record = group.get(id_)
            if not record:
                return None
            if not child_name:
                continue
            record[child_name]
            group = record.value.get(child_name)
            if not isinstance(group, Group):
                return None
        return record

    def _group_list_changed(self, action, *args):
        def groups(group):
            yield group
            while group.parent:
                if group.model_name != group.parent.model_name:
                    break
                else:
                    group = group.parent.group
                    yield group
        for group in groups(self):
            for screen in group.screens:
                screen.group_list_changed(group, action, *args)

    def record_modified(self):
        if not self.parent:
            for screen in self.screens:
                screen.record_modified()
        else:
            self.parent.modified_fields.setdefault(self.child_name)
            self.parent.group.fields[self.child_name].sig_changed(self.parent)
            self.parent.validate(softvalidation=True)
            self.parent.group.record_modified()

    def record_notify(self, notifications):
        for screen in self.screens:
            screen.record_notify(notifications)
