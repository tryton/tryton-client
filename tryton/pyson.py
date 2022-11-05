# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import datetime
import json
from decimal import Decimal
from functools import reduce

from dateutil.relativedelta import relativedelta


class PYSON(object):

    def pyson(self):
        raise NotImplementedError

    def types(self):
        raise NotImplementedError

    @staticmethod
    def eval(dct, context):
        raise NotImplementedError

    def __invert__(self):
        if self.types() != {bool}:
            return Not(Bool(self))
        else:
            return Not(self)

    def __and__(self, other):
        if (isinstance(other, PYSON)
                and other.types() != {bool}):
            other = Bool(other)
        if (isinstance(self, And)
                and not isinstance(self, Or)):
            return And(*self._statements, other)
        if self.types() != {bool}:
            return And(Bool(self), other)
        else:
            return And(self, other)

    __rand__ = __and__

    def __or__(self, other):
        if (isinstance(other, PYSON)
                and other.types() != {bool}):
            other = Bool(other)
        if isinstance(self, Or):
            return Or(*self._statements, other)
        if self.types() != {bool}:
            return Or(Bool(self), other)
        else:
            return Or(self, other)

    __ror__ = __or__

    def __eq__(self, other):
        return Equal(self, other)

    def __ne__(self, other):
        return Not(Equal(self, other))

    def __gt__(self, other):
        return Greater(self, other)

    def __ge__(self, other):
        return Greater(self, other, True)

    def __lt__(self, other):
        return Less(self, other)

    def __le__(self, other):
        return Less(self, other, True)

    def get(self, k, d=''):
        return Get(self, k, d)

    def in_(self, obj):
        return In(self, obj)

    def contains(self, k):
        return In(k, self)

    def __repr__(self):
        klass = self.__class__.__name__
        return '%s(%s)' % (klass, ', '.join(map(repr, self.__repr_params__)))

    @property
    def __repr_params__(self):
        return NotImplementedError


class PYSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, PYSON):
            return obj.pyson()
        elif isinstance(obj, datetime.date):
            if isinstance(obj, datetime.datetime):
                return DateTime(obj.year, obj.month, obj.day,
                        obj.hour, obj.minute, obj.second, obj.microsecond
                        ).pyson()
            else:
                return Date(obj.year, obj.month, obj.day).pyson()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super(PYSONEncoder, self).default(obj)


class PYSONDecoder(json.JSONDecoder):

    def __init__(self, context=None, noeval=False):
        self.__context = context or {}
        self.noeval = noeval
        super(PYSONDecoder, self).__init__(object_hook=self._object_hook)

    def _object_hook(self, dct):
        if '__class__' in dct:
            klass = CONTEXT.get(dct['__class__'])
            if klass:
                if not self.noeval:
                    return klass.eval(dct, self.__context)
                else:
                    dct = dct.copy()
                    del dct['__class__']
                    return klass(**dct)
        return dct


class Eval(PYSON):

    def __init__(self, v, d=''):
        super(Eval, self).__init__()
        self._value = v
        self._default = d

    @property
    def __repr_params__(self):
        return self._value, self._default

    def pyson(self):
        return {
            '__class__': 'Eval',
            'v': self._value,
            'd': self._default,
            }

    def types(self):
        if isinstance(self._default, PYSON):
            return self._default.types()
        else:
            return {type(self._default)}

    @staticmethod
    def eval(dct, context):
        if '.' in dct['v'] and dct['v'] not in context:
            base, name = dct['v'].split('.', 1)
            return Eval.eval({
                    'v': name,
                    'd': dct['d'],
                    }, context.get(base) or {})
        return context.get(dct['v'], dct['d'])

    @property
    def basename(self):
        name = self._value
        if name.startswith('_parent_'):
            name = name[len('_parent_'):]
        if '.' in name:
            name = name.split('.', 1)[0]
        return name


class Not(PYSON):

    def __init__(self, v):
        super(Not, self).__init__()
        if isinstance(v, PYSON):
            if v.types() != {bool}:
                v = Bool(v)
        elif not isinstance(v, bool):
            v = bool(v)
        self._value = v

    @property
    def __repr_params__(self):
        return (self._value,)

    def pyson(self):
        return {
            '__class__': 'Not',
            'v': self._value,
            }

    def types(self):
        return {bool}

    @staticmethod
    def eval(dct, context):
        return not dct['v']


class Bool(PYSON):

    def __init__(self, v):
        super(Bool, self).__init__()
        self._value = v

    @property
    def __repr_params__(self):
        return (self._value,)

    def pyson(self):
        return {
            '__class__': 'Bool',
            'v': self._value,
            }

    def types(self):
        return {bool}

    @staticmethod
    def eval(dct, context):
        return bool(dct['v'])


class And(PYSON):

    def __init__(self, *statements, **kwargs):
        super(And, self).__init__()
        statements = list(statements) + kwargs.get('s', [])
        for i, statement in enumerate(list(statements)):
            if isinstance(statement, PYSON):
                if statement.types() != {bool}:
                    statements[i] = Bool(statement)
            elif not isinstance(statement, bool):
                statements[i] = bool(statement)
        assert len(statements) >= 2, 'must have at least 2 statements'
        self._statements = statements

    @property
    def __repr_params__(self):
        return tuple(self._statements)

    def pyson(self):
        return {
            '__class__': 'And',
            's': self._statements,
            }

    def types(self):
        return {bool}

    @staticmethod
    def eval(dct, context):
        return bool(reduce(lambda x, y: x and y, dct['s']))


class Or(And):

    def pyson(self):
        res = super(Or, self).pyson()
        res['__class__'] = 'Or'
        return res

    @staticmethod
    def eval(dct, context):
        return bool(reduce(lambda x, y: x or y, dct['s']))


class Equal(PYSON):

    def __init__(self, s1, s2):
        statement1, statement2 = s1, s2
        super(Equal, self).__init__()
        if isinstance(statement1, PYSON):
            types1 = statement1.types()
        else:
            types1 = {type(s1)}
        if isinstance(statement2, PYSON):
            types2 = statement2.types()
        else:
            types2 = {type(s2)}
        assert types1 == types2, 'statements must have the same type'
        self._statement1 = statement1
        self._statement2 = statement2

    @property
    def __repr_params__(self):
        return (self._statement1, self._statement2)

    def pyson(self):
        return {
            '__class__': 'Equal',
            's1': self._statement1,
            's2': self._statement2,
            }

    def types(self):
        return {bool}

    @staticmethod
    def eval(dct, context):
        return dct['s1'] == dct['s2']


class Greater(PYSON):

    def __init__(self, s1, s2, e=False):
        statement1, statement2, equal = s1, s2, e
        super(Greater, self).__init__()
        for i in (statement1, statement2):
            if isinstance(i, PYSON):
                assert i.types().issubset({
                        int, float, type(None),
                        datetime.datetime, datetime.date}), \
                    'statement must be an integer, float, date or datetime'
            else:
                assert isinstance(i, (
                        int, float, type(None),
                        datetime.datetime, datetime.date)), \
                    'statement must be an integer, float, date or datetime'
        if isinstance(equal, PYSON):
            if equal.types() != {bool}:
                equal = Bool(equal)
        elif not isinstance(equal, bool):
            equal = bool(equal)
        self._statement1 = statement1
        self._statement2 = statement2
        self._equal = equal

    @property
    def __repr_params__(self):
        return (self._statement1, self._statement2, self._equal)

    def pyson(self):
        return {
            '__class__': 'Greater',
            's1': self._statement1,
            's2': self._statement2,
            'e': self._equal,
            }

    def types(self):
        return {bool}

    @staticmethod
    def _convert(dct):
        for i in ('s1', 's2'):
            if dct[i] is None:
                dct[i] = 0.0
            if not isinstance(dct[i], (int, float)):
                dct = dct.copy()
                stmt = dct[i]
                if isinstance(stmt, datetime.datetime):
                    stmt = stmt.timestamp()
                elif isinstance(stmt, datetime.date):
                    time = datetime.time(0, 0)
                    stmt = datetime.datetime.combine(stmt, time).timestamp()
                dct[i] = float(stmt)
        return dct

    @staticmethod
    def eval(dct, context):
        if dct['s1'] is None or dct['s2'] is None:
            return False
        dct = Greater._convert(dct)
        if dct['e']:
            return dct['s1'] >= dct['s2']
        else:
            return dct['s1'] > dct['s2']


class Less(Greater):

    def pyson(self):
        res = super(Less, self).pyson()
        res['__class__'] = 'Less'
        return res

    @staticmethod
    def eval(dct, context):
        if dct['s1'] is None or dct['s2'] is None:
            return False
        dct = Less._convert(dct)
        if dct['e']:
            return dct['s1'] <= dct['s2']
        else:
            return dct['s1'] < dct['s2']


class If(PYSON):

    def __init__(self, c, t, e=None):
        condition, then_statement, else_statement = c, t, e
        super(If, self).__init__()
        if isinstance(condition, PYSON):
            if condition.types() != {bool}:
                condition = Bool(condition)
        elif not isinstance(condition, bool):
            condition = bool(condition)
        self._condition = condition
        self._then_statement = then_statement
        self._else_statement = else_statement

    @property
    def __repr_params__(self):
        return (self._condition, self._then_statement, self._else_statement)

    def pyson(self):
        return {
            '__class__': 'If',
            'c': self._condition,
            't': self._then_statement,
            'e': self._else_statement,
            }

    def types(self):
        if isinstance(self._then_statement, PYSON):
            types = self._then_statement.types()
        else:
            types = {type(self._then_statement)}
        if isinstance(self._else_statement, PYSON):
            types |= self._else_statement.types()
        else:
            types |= {type(self._else_statement)}
        return types

    @staticmethod
    def eval(dct, context):
        if dct['c']:
            return dct['t']
        else:
            return dct['e']


class Get(PYSON):

    def __init__(self, v, k, d=''):
        obj, key, default = v, k, d
        super(Get, self).__init__()
        if isinstance(obj, PYSON):
            assert obj.types() == {dict}, 'obj must be a dict'
        else:
            assert isinstance(obj, dict), 'obj must be a dict'
        self._obj = obj
        if isinstance(key, PYSON):
            assert key.types() == {str}, 'key must be a string'
        else:
            assert isinstance(key, str), 'key must be a string'
        self._key = key
        self._default = default

    @property
    def __repr_params__(self):
        return (self._obj, self._key, self._default)

    def pyson(self):
        return {
            '__class__': 'Get',
            'v': self._obj,
            'k': self._key,
            'd': self._default,
            }

    def types(self):
        if isinstance(self._default, PYSON):
            return self._default.types()
        else:
            return {type(self._default)}

    @staticmethod
    def eval(dct, context):
        return dct['v'].get(dct['k'], dct['d'])


class In(PYSON):

    def __init__(self, k, v):
        key, obj = k, v
        super(In, self).__init__()
        if isinstance(key, PYSON):
            assert key.types().issubset({str, int}), \
                'key must be a string or an integer or a long'
        else:
            assert isinstance(key, (str, int)), \
                'key must be a string or an integer or a long'
        if isinstance(obj, PYSON):
            assert obj.types().issubset({dict, list}), \
                'obj must be a dict or a list'
            if obj.types() == {dict}:
                if isinstance(key, PYSON):
                    assert key.types() == {str}, 'key must be a string'
                else:
                    assert isinstance(key, str), 'key must be a string'
        else:
            assert isinstance(obj, (dict, list))
            if isinstance(obj, dict):
                if isinstance(key, PYSON):
                    assert key.types() == {str}, 'key must be a string'
                else:
                    assert isinstance(key, str), 'key must be a string'
        self._key = key
        self._obj = obj

    @property
    def __repr_params__(self):
        return (self._key, self._obj)

    def pyson(self):
        return {
            '__class__': 'In',
            'k': self._key,
            'v': self._obj,
            }

    def types(self):
        return {bool}

    @staticmethod
    def eval(dct, context):
        if dct['v']:
            return dct['k'] in dct['v']
        else:
            return False


class Date(PYSON):

    def __init__(self, year=None, month=None, day=None,
            delta_years=0, delta_months=0, delta_days=0, start=None, **kwargs):
        year = kwargs.get('y', year)
        month = kwargs.get('M', month)
        day = kwargs.get('d', day)
        delta_years = kwargs.get('dy', delta_years)
        delta_months = kwargs.get('dM', delta_months)
        delta_days = kwargs.get('dd', delta_days)
        super(Date, self).__init__()
        for i in (year, month, day, delta_years, delta_months, delta_days):
            if isinstance(i, PYSON):
                assert i.types().issubset({int, type(None)}), \
                    '%s must be an integer or None' % (i,)
            else:
                assert isinstance(i, (int, type(None))), \
                    '%s must be an integer or None' % (i,)
        self._year = year
        self._month = month
        self._day = day
        self._delta_years = delta_years
        self._delta_months = delta_months
        self._delta_days = delta_days
        self._start = start

    @property
    def __repr_params__(self):
        return (self._year, self._month, self._day,
            self._delta_years, self._delta_months, self._delta_days,
            self._start)

    def pyson(self):
        return {
            '__class__': 'Date',
            'y': self._year,
            'M': self._month,
            'd': self._day,
            'dy': self._delta_years,
            'dM': self._delta_months,
            'dd': self._delta_days,
            'start': self._start,
            }

    def types(self):
        return {datetime.date}

    @staticmethod
    def eval(dct, context):
        today = dct.get('start')
        if isinstance(today, datetime.datetime):
            today = today.date()
        if not isinstance(today, datetime.date):
            today = datetime.date.today()
        return today + relativedelta(
            year=dct['y'],
            month=dct['M'],
            day=dct['d'],
            years=dct['dy'],
            months=dct['dM'],
            days=dct['dd'],
            )


class DateTime(Date):

    def __init__(self, year=None, month=None, day=None,
            hour=None, minute=None, second=None, microsecond=None,
            delta_years=0, delta_months=0, delta_days=0,
            delta_hours=0, delta_minutes=0, delta_seconds=0,
            delta_microseconds=0, start=None, **kwargs):
        hour = kwargs.get('h', hour)
        minute = kwargs.get('m', minute)
        second = kwargs.get('s', second)
        microsecond = kwargs.get('ms', microsecond)
        delta_hours = kwargs.get('dh', delta_hours)
        delta_minutes = kwargs.get('dm', delta_minutes)
        delta_seconds = kwargs.get('ds', delta_seconds)
        delta_microseconds = kwargs.get('dms', delta_microseconds)
        super(DateTime, self).__init__(year=year, month=month, day=day,
                delta_years=delta_years, delta_months=delta_months,
                delta_days=delta_days, start=start, **kwargs)
        for i in (hour, minute, second, microsecond,
                delta_hours, delta_minutes, delta_seconds, delta_microseconds):
            if isinstance(i, PYSON):
                assert i.types() == {int, type(None)}, \
                    '%s must be an integer or None' % (i,)
            else:
                assert isinstance(i, (int, type(None))), \
                    '%s must be an integer or None' % (i,)
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond
        self._delta_hours = delta_hours
        self._delta_minutes = delta_minutes
        self._delta_seconds = delta_seconds
        self._delta_microseconds = delta_microseconds

    @property
    def __repr_params__(self):
        date_params = super(DateTime, self).__repr_params__
        return (date_params[:3]
            + (self._hour, self._minute, self._second, self._microsecond)
            + date_params[3:-1]
            + (self._delta_hours, self._delta_minutes, self._delta_seconds,
                self._delta_microseconds)
            + date_params[-1:])

    def pyson(self):
        res = super(DateTime, self).pyson()
        res['__class__'] = 'DateTime'
        res['h'] = self._hour
        res['m'] = self._minute
        res['s'] = self._second
        res['ms'] = self._microsecond
        res['dh'] = self._delta_hours
        res['dm'] = self._delta_minutes
        res['ds'] = self._delta_seconds
        res['dms'] = self._delta_microseconds
        return res

    def types(self):
        return {datetime.datetime}

    @staticmethod
    def eval(dct, context):
        now = dct.get('start')
        if (isinstance(now, datetime.date)
                and not isinstance(now, datetime.datetime)):
            now = datetime.datetime.combine(now, datetime.time())
        if not isinstance(now, datetime.datetime):
            now = datetime.datetime.utcnow()
        return now + relativedelta(
            year=dct['y'],
            month=dct['M'],
            day=dct['d'],
            hour=dct['h'],
            minute=dct['m'],
            second=dct['s'],
            microsecond=dct['ms'],
            years=dct['dy'],
            months=dct['dM'],
            days=dct['dd'],
            hours=dct['dh'],
            minutes=dct['dm'],
            seconds=dct['ds'],
            microseconds=dct['dms'],
            )


class TimeDelta(PYSON):

    def __init__(self, days=0, seconds=0, microseconds=0):
        for i in [days, seconds, microseconds]:
            if isinstance(i, PYSON):
                assert i.types().issubset({int, float}), \
                        '%s must be an integer' % (i,)
            else:
                assert isinstance(i, (int, float)), \
                        '%s must be an integer' % (i,)
        self._days = days
        self._seconds = seconds
        self._microseconds = microseconds

    @property
    def __repr_params__(self):
        return self._days, self._seconds, self._microseconds

    def pyson(self):
        return {
            '__class__': 'TimeDelta',
            'd': self._days,
            's': self._seconds,
            'm': self._microseconds,
            }

    def types(self):
        return {datetime.timedelta}

    @staticmethod
    def eval(dct, context):
        return datetime.timedelta(
            days=dct['d'],
            seconds=dct['s'],
            microseconds=dct['m'],
            )


class Len(PYSON):

    def __init__(self, v):
        super(Len, self).__init__()
        if isinstance(v, PYSON):
            assert v.types().issubset({dict, list, str}), \
                'value must be a dict or a list or a string'
        else:
            assert isinstance(v, (dict, list, str)), \
                'value must be a dict or list or a string'
        self._value = v

    @property
    def __repr_params__(self):
        return (self._value,)

    def pyson(self):
        return {
            '__class__': 'Len',
            'v': self._value,
            }

    def types(self):
        return {int}

    @staticmethod
    def eval(dct, context):
        return len(dct['v'])


CONTEXT = {
    'Eval': Eval,
    'Not': Not,
    'Bool': Bool,
    'And': And,
    'Or': Or,
    'Equal': Equal,
    'Greater': Greater,
    'Less': Less,
    'If': If,
    'Get': Get,
    'In': In,
    'Date': Date,
    'DateTime': DateTime,
    'TimeDelta': TimeDelta,
    'Len': Len,
    'true': True,
    'false': False,
}
