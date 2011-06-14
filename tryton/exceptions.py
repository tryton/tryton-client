#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.


class TrytonServerError(Exception):

    def __init__(self, *args):
        super(TrytonServerError, self).__init__(*args)
        self.ex_type = str(args[0])
        self.traceback = args[-1]


class TrytonError(Exception):

    def __init__(self, ex_type):
        self.ex_type = ex_type
