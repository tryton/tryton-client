#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gobject
import pango
from date_widget import mapping, DateEntry, compute_date
import re
import time
from mx.DateTime import RelativeDateTime
from mx.DateTime import DateTime
from mx.DateTime import now
from mx.DateTime import strptime


class CellRendererDate(gtk.GenericCellRenderer):
    __gproperties__ = {
            'text': (gobject.TYPE_STRING, None, 'Text',
                'Text', gobject.PARAM_READWRITE),
            'foreground': (gobject.TYPE_STRING, None, 'Foreground',
                'Foreground', gobject.PARAM_READWRITE),
            'background': (gobject.TYPE_STRING, None, 'Background',
                'Background', gobject.PARAM_READWRITE),
            'editable': (gobject.TYPE_INT, 'Editable',
                'Editable', 0, 10, 0, gobject.PARAM_READWRITE),
    }

    def __init__(self, format):
        self.__gobject_init__()
        self._renderer = gtk.CellRendererText()
        self.set_property("mode", self._renderer.get_property("mode"))

        self.format = format
        self.cmd = ''

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)
        self._renderer.set_property(pspec.name, value)
        self.set_property("mode", self._renderer.get_property("mode"))

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def on_get_size(self, widget, cell_area):
        return self._renderer.get_size(widget, cell_area)

    def on_render(self, window, widget, background_area, cell_area,
            expose_area, flags):
        return self._renderer.render(window, widget, background_area,
                cell_area, expose_area, flags)

    def on_activate(self, event, widget, path, background_area, cell_area,
            flags):
        return self._renderer.activate(event, widget, path, background_area,
                cell_area, flags)

    def on_start_editing(self, event, widget, path, background_area,
            cell_area, flags):
        editable = DateEntry(self.format, self._date_cb, self._process_cb)
        editable.set_text(self.text)
        editable.grab_focus()
        editable.show()
        return editable

    def _date_cb(self, event):
        if event.keyval in (gtk.keysyms.BackSpace,):
            self.cmd = self.cmd[:-1]
            return True
        if event.keyval < 250:
            value = chr(event.keyval)
            self.cmd += value
        return True

    def _process_cb(self, ok, widget, event=None):
        if ok:
            self._date_cb(event)
        else:
            if hasattr(event, 'keyval') and not event.keyval == gtk.keysyms.Escape:
                dt = widget.date_get()
                res= compute_date(self.cmd, dt, widget.format)
                if res:
                    widget.date_set(res)
            self.cmd = ''

gobject.type_register(CellRendererDate)
