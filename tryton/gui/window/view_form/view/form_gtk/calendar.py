import time
import datetime as DT
import gtk
import gettext
import locale
from interface import WidgetInterface
import tryton.rpc as rpc
from tryton.common import DT_FORMAT, DHM_FORMAT, HM_FORMAT, message, TRYTON_ICON

_ = gettext.gettext

if not hasattr(locale, 'nl_langinfo'):
    locale.nl_langinfo = lambda *a: '%x'

if not hasattr(locale, 'D_FMT'):
    locale.D_FMT = None


class Calendar(WidgetInterface):
    "Calendar"

    def __init__(self, window, parent=None, model=None, attrs=None):
        super(Calendar, self).__init__(window, parent, model=model, attrs=attrs)

        self.widget = gtk.HBox(spacing=3)
        self.entry = gtk.Entry()
        self.entry.set_property('activates_default', True)
        self.entry.connect('button_press_event', self._menu_open)
        self.entry.connect('activate', self.sig_activate)
        self.entry.connect('focus-in-event', lambda x, y: self._focus_in())
        self.entry.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.pack_start(self.entry, expand=True, fill=True)

        self.but_open = gtk.Button()
        img_find = gtk.Image()
        img_find.set_from_stock('gtk-find', gtk.ICON_SIZE_BUTTON)
        self.but_open.set_image(img_find)
        self.but_open.set_relief(gtk.RELIEF_NONE)
        self.but_open.connect('clicked', self.cal_open)
        self.but_open.set_alignment(0.5, 0.5)
        self.but_open.set_property('can-focus', False)
        self.widget.pack_start(self.but_open, expand=False, fill=False)

        tooltips = gtk.Tooltips()
        tooltips.set_tip(self.but_open, _('Open the calendar widget'))
        tooltips.enable()

        self.readonly = False

    def _color_widget(self):
        return self.entry

    def _readonly_set(self, value):
        super(Calendar, self)._readonly_set(value)
        self.entry.set_editable(not value)
        self.entry.set_sensitive(not value)
        self.but_open.set_sensitive(not value)

    def get_value(self, model):
        value = self.entry.get_text()
        if value == '':
            return False
        try:
            date = time.strptime(value, locale.nl_langinfo(
                locale.D_FMT).replace('%y', '%Y'))
        except:
            return False
        return time.strftime(DT_FORMAT, date)

    def set_value(self, model, model_field):
        model_field.set_client(model, self.get_value(model))
        return True

    def display(self, model, model_field):
        if not model_field:
            self.entry.set_text('')
            return False
        super(Calendar, self).display(model, model_field)
        value = model_field.get(model)
        if not value:
            self.entry.set_text('')
        else:
            if len(value)>10:
                value = value[:10]
            date = time.strptime(value, DT_FORMAT)
            value = time.strftime(locale.nl_langinfo(
                locale.D_FMT).replace('%y', '%Y'), date)
            if len(value) > self.entry.get_width_chars():
                self.entry.set_width_chars(len(value))
            self.entry.set_text(value)
        return True

    def cal_open(self, widget):
        if self.readonly:
            message(_('This widget is readonly!'), self._window)
            return True

        win = gtk.Dialog(_('Tryton - Date selection'), self._window,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))
        win.set_icon(TRYTON_ICON)

        cal = gtk.Calendar()
        cal.display_options(gtk.CALENDAR_SHOW_HEADING | \
                gtk.CALENDAR_SHOW_DAY_NAMES | \
                gtk.CALENDAR_SHOW_WEEK_NUMBERS)
        cal.connect('day-selected-double-click',
                lambda *x: win.response(gtk.RESPONSE_OK))
        win.vbox.pack_start(cal, expand=True, fill=True)
        win.show_all()

        try:
            val = self.get_value(self.model)
            if val:
                cal.select_month(int(val[5:7])-1, int(val[0:4]))
                cal.select_day(int(val[8:10]))
        except ValueError:
            pass

        response = win.run()
        if response == gtk.RESPONSE_OK:
            year, month, day = cal.get_date()
            date = DT.date(year, month+1, day)
            self.entry.set_text(date.strftime(
                locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y')))
        self._focus_out()
        self._window.present()
        win.destroy()


class DateTime(WidgetInterface):
    "DateTime"

    def __init__(self, window, parent, model, attrs=None):
        super(DateTime, self).__init__(window, parent, model, attrs=attrs)

        self.widget = gtk.HBox(spacing=3)
        self.entry = gtk.Entry()
        self.entry.set_property('activates_default', True)
        self.entry.connect('button_press_event', self._menu_open)
        self.entry.connect('focus-in-event', lambda x, y: self._focus_in())
        self.entry.connect('focus-out-event', lambda x, y: self._focus_out())
        self.widget.pack_start(self.entry, expand=True, fill=True)

        self.but_open = gtk.Button()
        img_find = gtk.Image()
        img_find.set_from_stock('gtk-find', gtk.ICON_SIZE_BUTTON)
        self.but_open.set_image(img_find)
        self.but_open.set_relief(gtk.RELIEF_NONE)
        self.but_open.connect('clicked', self.cal_open)
        self.but_open.set_alignment(0.5, 0.5)
        self.but_open.set_property('can-focus', False)
        self.widget.pack_start(self.but_open, expand=False, fill=False)

        tooltips = gtk.Tooltips()
        tooltips.set_tip(self.but_open, _('Open the calendar widget'))
        tooltips.enable()

        self.readonly = False

    def _color_widget(self):
        return self.entry

    def _readonly_set(self, value):
        self.readonly = value
        self.entry.set_editable(not value)
        self.entry.set_sensitive(not value)

    def get_value(self, model, timezone=True):
        value = self.entry.get_text()
        if value == '':
            return False
        try:
            date = time.strptime(value, locale.nl_langinfo(
                locale.D_FMT).replace('%y', '%Y') + ' ' + HM_FORMAT)
        except:
            return False
        if 'timezone' in rpc.session.context and timezone:
            try:
                import pytz
                lzone = pytz.timezone(rpc.session.context['timezone'])
                szone = pytz.timezone(rpc.session.timezone)
                datetime = DT.datetime(date[0], date[1], date[2], date[3],
                        date[4], date[5], date[6])
                ldt = lzone.localize(datetime, is_dst=True)
                sdt = ldt.astimezone(szone)
                date = sdt.timetuple()
            except:
                pass
        return time.strftime(DHM_FORMAT, date)

    def set_value(self, model, model_field):
        model_field.set_client(model, self.get_value(model))
        return True

    def display(self, model, model_field):
        super(DateTime, self).display(model, model_field)
        if not model_field:
            return self.show(False)
        self.show(model_field.get(model))

    def show(self, dt_val, timezone=True):
        if not dt_val:
            self.entry.set_text('')
        else:
            date = time.strptime(dt_val, DHM_FORMAT)
            if 'timezone' in rpc.session.context and timezone:
                try:
                    import pytz
                    lzone = pytz.timezone(rpc.session.context['timezone'])
                    szone = pytz.timezone(rpc.session.timezone)
                    datetime = DT.datetime(date[0], date[1], date[2], date[3],
                            date[4], date[5], date[6])
                    sdt = szone.localize(datetime, is_dst=True)
                    ldt = sdt.astimezone(lzone)
                    date = ldt.timetuple()
                except:
                    pass
            value = time.strftime(locale.nl_langinfo(
                locale.D_FMT).replace('%y', '%Y') + ' ' + HM_FORMAT, date)
            if len(value) > self.entry.get_width_chars():
                self.entry.set_width_chars(len(value))
            self.entry.set_text(value)
        return True

    def cal_open(self, widget):
        if self.readonly:
            message(_('This widget is readonly!'), self._window)
            return True

        win = gtk.Dialog(_('Tryton - Date selection'), self._window,
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))

        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(_('Hour:')), expand=False, fill=False)
        widget_hour = gtk.SpinButton(gtk.Adjustment(0, 0, 23, 1, 5, 5), 1, 0)
        hbox.pack_start(widget_hour, expand=True, fill=True)
        hbox.pack_start(gtk.Label(_('Minute:')), expand=False, fill=False)
        widget_minute = gtk.SpinButton(
                gtk.Adjustment(0, 0, 59, 1, 10, 10), 1, 0)
        hbox.pack_start(widget_minute, expand=True, fill=True)
        win.vbox.pack_start(hbox, expand=False, fill=True)

        cal = gtk.Calendar()
        cal.display_options(gtk.CALENDAR_SHOW_HEADING | \
                gtk.CALENDAR_SHOW_DAY_NAMES | \
                gtk.CALENDAR_SHOW_WEEK_NUMBERS)
        cal.connect('day-selected-double-click',
                lambda *x: win.response(gtk.RESPONSE_OK))
        win.vbox.pack_start(cal, expand=True, fill=True)
        win.show_all()

        try:
            val = self.get_value(self.model, timezone=False)
            if val:
                widget_hour.set_value(int(val[11:13]))
                widget_minute.set_value(int(val[-5:-3]))
                cal.select_month(int(val[5:7])-1, int(val[0:4]))
                cal.select_day(int(val[8:10]))
            else:
                widget_hour.set_value(time.localtime()[3])
                widget_minute.set_value(time.localtime()[4])
        except ValueError:
            pass
        response = win.run()
        if response == gtk.RESPONSE_OK:
            hour = int(widget_hour.get_value())
            minute = int(widget_minute.get_value())
            year = int(cal.get_date()[0])
            month = int(cal.get_date()[1]) + 1
            day = int(cal.get_date()[2])
            date = DT.datetime(year, month, day, hour, minute)
            value = time.strftime(DHM_FORMAT, date.timetuple())
            self.show(value, timezone=False)
        self._focus_out()
        self._window.present()
        win.destroy()
