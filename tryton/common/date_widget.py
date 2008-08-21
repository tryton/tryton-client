#
# Copyright (C) 2006 Async Open Source
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA
#
# Author(s): Johan Dahlin <[EMAIL PROTECTED]>
#            Cedric Krier <ced@b2ck.com>
#


import gobject
import pango
import gtk
import re

import time
from mx.DateTime import RelativeDateTime
from mx.DateTime import DateTime
from mx.DateTime import now
from mx.DateTime import strptime

mapping = {
    '%y': ('__', '[_0-9][_0-9]'),
    '%Y': ('____', '[_1-9][_0-9][_0-9][_0-9]'),
    '%m': ('__', '[_0-1][_0-9]'),
    '%d': ('__', '[_0-3][_0-9]'),
    '%H': ('__', '[_0-2][_0-9]'),
    '%M': ('__', '[_0-6][_0-9]'),
    '%S': ('__', '[_0-6][_0-9]'),
}

class DateEntry(gtk.Entry):
    def __init__(self, format, callback=None, callback_process=None):
        super(DateEntry, self).__init__()
        self.modify_font(pango.FontDescription("monospace"))

        self.format = format
        self.regex = self.initial_value = format
        for key,val in mapping.items():
            self.regex = self.regex.replace(key, val[1])
            self.initial_value = self.initial_value.replace(key, val[0])

        self.set_text(self.initial_value)
        self.regex = re.compile(self.regex)

        assert self.regex.match(self.initial_value), 'Error, the initial value should be validated by regex'
        self.set_width_chars(len(self.initial_value))
        self.set_max_length(len(self.initial_value))

        self.connect('key-press-event', self._on_key_press)
        self.connect('insert-text', self._on_insert_text)
        self.connect('delete-text', self._on_delete_text)

        self.connect('focus-out-event', self._focus_out)
        self.callback = callback
        self.callback_process = callback_process

        self._interactive_input = True
        self.mode_cmd = False
        gobject.idle_add(self.set_position, 0)

    def _on_insert_text(self, editable, value, length, position):
        if not self._interactive_input:
            return

        if self.mode_cmd:
            if self.callback: self.callback(value)
            self.stop_emission('insert-text')
            return

        pos = self.get_position()

        text = self.get_text()
        if text == self.initial_value and pos >= len(self.initial_value):
            pos = 0

        text = text[:pos] + value + text[pos + length:]
        if self.regex.match(text):
            pos += 1
            while (pos<len(self.initial_value)) and (text[pos] != '_'):
                pos += 1
            self.set_text(text)
            gobject.idle_add(self.set_position, pos)
        self.stop_emission('insert-text')
        self.show()
        return

    def _on_delete_text(self, editable, start, end):
        if not self._interactive_input:
            return

        while (start>0) and (self.initial_value[start] not in ['_','0','X']):
            start -= 1
        text = self.get_text()
        text = text[:start] + self.initial_value[start:end] + text[end:]
        self.set_text(text)
        gobject.idle_add(self.set_position, start)
        self.stop_emission('delete-text')
        return

    def _focus_out(self, args, args2):
        self.date_get()

    def set_text(self, text):
        self._interactive_input = False
        try:
            gtk.Entry.set_text(self, text)
        finally:
            self._interactive_input = True

    def date_set(self, dt):
        if dt:
            self.set_text( dt.strftime(self.format) )
        else:
            self.set_text(self.initial_value)

    def date_get(self):
        tt = time.strftime(self.format, time.localtime())
        tc = self.get_text()
        if tc==self.initial_value:
            return False
        for a in range(len(self.initial_value)):
            if self.initial_value[a] == tc[a]:
                tc = tc[:a] + tt[a] + tc[a+1:]
        try:
            self.set_text(tc)
            return strptime(tc, self.format)
        except:
            tc = tt
        self.set_text(tc)
        return strptime(tc, self.format)

    def delete_text(self, start, end):
        self._interactive_input = False
        try:
            gtk.Entry.delete_text(self, start, end)
        finally:
            self._interactive_input = True

    def insert_text(self, text, position=0):
        self._interactive_input = False
        try:
            gtk.Entry.insert_text(self, text, position)
        finally:
            self._interactive_input = True

    def clear(self):
        self.set_text(self.initial_value)

    def _on_key_press(self, editable, event):
        if event.keyval in (gtk.keysyms.Tab, gtk.keysyms.Escape, gtk.keysyms.Return):
            if self.mode_cmd:
                self.mode_cmd = False
                if self.callback_process: self.callback_process(False, self, event)
                self.stop_emission("key-press-event")
                return True
        elif event.keyval in (ord('+'),ord('-'),ord('=')):
                self.mode_cmd = True
                self.date_get()
                if self.callback_process: self.callback_process(True, self, event)
                self.stop_emission("key-press-event")
                return True
        elif self.mode_cmd:
            if self.callback: self.callback(event)
            return True
        return False

class CmdEntry(gtk.Label):
    pass

class ComplexEntry(gtk.HBox):
    def __init__(self, format, *args, **argv):
        super(ComplexEntry, self).__init__(*args, **argv)
        self.widget = DateEntry(
            format,
            self._date_cb,
            self._process_cb
        )
        self.widget.set_position(0)
        self.widget.select_region(0, 0)
        self.widget_cmd = CmdEntry()
        self.widget_cmd.hide()
        self.pack_start(self.widget, expand=True, fill=True)
        self.pack_start(self.widget_cmd, expand=False, fill=True)

    def _date_cb(self, event):
        if event.keyval in (gtk.keysyms.BackSpace,):
            text = self.widget_cmd.get_text()[:-1]
            self.widget_cmd.set_text(text)
            return True
        if event.keyval<250:
            value = chr(event.keyval)
            text = self.widget_cmd.get_text()
            self.widget_cmd.set_text(text+value)
        return True

    def _process_cb(self, ok, widget, event=None):
        if ok:
            self.widget_cmd.show()
            self._date_cb(event)
        else:
            data = self.widget.get_text()
            if not event.keyval == gtk.keysyms.Escape:
                lst = {
                    '^=(\d+)w$': lambda dt,r: dt+RelativeDateTime(day=0, month=0, weeks = int(r.group(1))),
                    '^=(\d+)d$': lambda dt,r: dt+RelativeDateTime(day=int(r.group(1))),
                    '^=(\d+)m$': lambda dt,r: dt+RelativeDateTime(day=0, month = int(r.group(1))),
                    '^=(2\d\d\d)y$': lambda dt,r: dt+RelativeDateTime(year = int(r.group(1))),
                    '^=(\d+)h$': lambda dt,r: dt+RelativeDateTime(hour = int(r.group(1))),
                    '^([\\+-]\d+)h$': lambda dt,r: dt+RelativeDateTime(hours = int(r.group(1))),
                    '^([\\+-]\d+)w$': lambda dt,r: dt+RelativeDateTime(days = 7*int(r.group(1))),
                    '^([\\+-]\d+)d$': lambda dt,r: dt+RelativeDateTime(days = int(r.group(1))),
                    '^([\\+-]\d+)m$': lambda dt,r: dt+RelativeDateTime(months = int(r.group(1))),
                    '^([\\+-]\d+)y$': lambda dt,r: dt+RelativeDateTime(years = int(r.group(1))),
                    '^=$': lambda dt,r: now(),
                    '^-$': lambda dt,r: False
                }
                cmd = self.widget_cmd.get_text()
                for r,f in lst.items():
                    groups = re.match(r, cmd)
                    if groups:
                        dt = self.widget.date_get()
                        if not dt:
                            dt = time.strftime(self.widget.format, time.localtime())
                            dt = strptime(dt, self.widget.format)
                        self.widget.date_set(f(dt,groups))
                        break

                # Compute HERE using DATA and setting WIDGET
                pass
            self.widget_cmd.set_text('')
            self.widget_cmd.hide()

if __name__ == '__main__':
    import sys
    def main(args):
        win = gtk.Window()
        win.set_title('gtk.Entry subclass')
        def cb(window, event):
            gtk.main_quit()
        win.connect('delete-event', cb)

        widget = ComplexEntry('%d/%m/%Y %H:%M:%S')
        win.add(widget)

        win.show_all()
        gtk.main()

    sys.exit(main(sys.argv))

