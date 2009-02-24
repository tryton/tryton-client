#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gobject
from cellrendererinteger import CellRendererInteger
import locale


class CellRendererFloat(CellRendererInteger):

    def __init__(self):
        super(CellRendererFloat, self).__init__()
        self.digits = (16, 2)

    def sig_insert_text(self, entry, new_text, new_text_length, position):
        value = entry.get_text()
        position = entry.get_position()
        new_value = value[:position] + new_text + value[position:]
        try:
            if new_value == '-':
                return

            if len(str(int(locale.atof(new_value)))) > self.digits[0]:
                entry.stop_emission('insert-text')

            exp_value = locale.atof(new_value) * (10 ** self.digits[1])
            if exp_value - int(exp_value) != 0.0:
                entry.stop_emission('insert-text')
        except:
            entry.stop_emission('insert-text')

gobject.type_register(CellRendererFloat)
