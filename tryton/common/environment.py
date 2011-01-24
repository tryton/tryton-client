#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.


class EvalEnvironment(dict):

    def __init__(self, parent, check_load):
        super(EvalEnvironment, self).__init__()
        self.parent = parent
        self.check_load = check_load

    def __getitem__(self, item):
        if item == '_parent_' + self.parent.parent_name and self.parent.parent:
            return EvalEnvironment(self.parent.parent, self.check_load)
        return self.parent.get_eval(check_load=self.check_load)[item]

    def __getattr__(self, item):
        return self.__getitem__(item)

    def get(self, item, default=None):
        try:
            return self.__getattr__(item)
        except Exception:
            pass
        return super(EvalEnvironment, self).get(item, default)

    def __nonzero__(self):
        return True

    def __str__(self):
        return str(self.parent)

    __repr__ = __str__

    def __contains__(self, item):
        if item == '_parent_' + self.parent.parent_name and self.parent.parent:
            return item in EvalEnvironment(self.parent.parent, self.check_load)
        return item in self.parent.get_eval(check_load=self.check_load)
