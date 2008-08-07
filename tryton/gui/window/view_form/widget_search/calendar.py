#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import time
import datetime as DT
import gtk
import gettext
import locale
from interface import Interface
from tryton.common import DT_FORMAT
from _strptime import LocaleTime

_ = gettext.gettext


class Calendar(Interface):

    def __init__(self, name, parent, attrs=None):
        super(Calendar, self).__init__(name, parent, attrs)

        tooltips = gtk.Tooltips()
        self.widget = gtk.HBox(spacing=3)

        self.entry1 = gtk.Entry()
        self.entry1.set_property('width-chars', 10)
        self.entry1.set_property('activates_default', True)
        tooltips.set_tip(self.entry1, _('Start date'))
        self.widget.pack_start(self.entry1, expand=False, fill=True)

        self.eb1 = gtk.EventBox()
        tooltips.set_tip(self.eb1, _('Open the calendar'))
        self.eb1.set_events(gtk.gdk.BUTTON_PRESS)
        self.eb1.connect('button_press_event', self.cal_open, self.entry1,
                parent)
        img = gtk.Image()
        img.set_from_stock('tryton-find', gtk.ICON_SIZE_BUTTON)
        img.set_alignment(0.5, 0.5)
        self.eb1.add(img)
        self.widget.pack_start(self.eb1, expand=False, fill=False)

        self.widget.pack_start(gtk.Label('-'), expand=False, fill=False)

        self.entry2 = gtk.Entry()
        self.entry2.set_property('width-chars', 10)
        self.entry2.set_property('activates_default', True)
        tooltips.set_tip(self.entry2, _('End date'))
        self.widget.pack_start(self.entry2, expand=False, fill=True)

        self.eb2 = gtk.EventBox()
        tooltips.set_tip(self.eb2, _('Open the calendar'))
        self.eb2.set_events(gtk.gdk.BUTTON_PRESS)
        self.eb2.connect('button_press_event', self.cal_open, self.entry2,
                parent)
        img = gtk.Image()
        img.set_from_stock('tryton-find', gtk.ICON_SIZE_BUTTON)
        img.set_alignment(0.5, 0.5)
        self.eb2.add(img)
        self.widget.pack_start(self.eb2, expand=False, fill=False)

        tooltips.enable()

    def _date_get(self, value):
        try:
            date = time.strptime(value,
                    LocaleTime().LC_date.replace('%y', '%Y'))
        except:
            return False
        return time.strftime(DT_FORMAT, date)

    def _value_get(self):
        res = []
        val = self.entry1.get_text()
        if val:
            res.append((self.name, '>=', self._date_get(val)))
        val = self.entry2.get_text()
        if val:
            res.append((self.name, '<=', self._date_get(val)))
        return res

    def _value_set(self, value):
        def conv(value):
            if not value:
                return ''
            try:
                return value.strftime(LocaleTime().LC_date.replace('%y', '%Y'))
            except:
                return ''

        self.entry1.set_text(conv(value[0]))
        self.entry2.set_text(conv(value[1]))

    value = property(_value_get, _value_set)

    def cal_open(self, widget, event, dest, parent=None):
        win = gtk.Dialog(_('Date selection'), parent,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))

        cal = gtk.Calendar()
        cal.display_options(gtk.CALENDAR_SHOW_HEADING | \
                        gtk.CALENDAR_SHOW_DAY_NAMES | \
                        gtk.CALENDAR_SHOW_WEEK_NUMBERS)
        cal.connect('day-selected-double-click',
                lambda *x: win.response(gtk.RESPONSE_OK))
        win.vbox.pack_start(cal, expand=True, fill=True)
        win.show_all()

        try:
            val = self._date_get(dest.get_text())
            if val:
                cal.select_month(int(val[5:7])-1, int(val[0:4]))
                cal.select_day(int(val[8:10]))
        except ValueError:
            pass

        response = win.run()
        if response == gtk.RESPONSE_OK:
            year, month, day = cal.get_date()
            date = DT.date(year, month+1, day)
            dest.set_text(date.strftime(
                LocaleTime().LC_date.replace('%y', '%Y')))
        win.destroy()

    def clear(self):
        self.value = ('', '')

    def sig_activate(self, fct):
        self.entry1.connect_after('activate', fct)
        self.entry2.connect_after('activate', fct)
