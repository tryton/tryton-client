#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import os
import gettext
import urlparse
import gobject
import gtk
from gtk import glade
import tryton.rpc as rpc
from tryton.config import CONFIG, GLADE, TRYTON_ICON, PIXMAPS_DIR, DATA_DIR
import tryton.common as common
from tryton.version import VERSION
from tryton.action import Action
from tryton.gui.window import Window
from tryton.gui.window.preference import Preference
from tryton.gui.window import FilesActions
import re
import base64
import tryton.translate as translate
import tryton.plugin
import locale

_ = gettext.gettext

def _refresh_dblist(db_widget, host, port, dbtoload=None):
    if not dbtoload:
        dbtoload = CONFIG['login.db']
    index = 0
    liststore = db_widget.get_model()
    liststore.clear()
    result = rpc.db_list(host, port)
    Main.get_main().refresh_ssl()
    if result is None:
        return None
    for db_num, dbname in enumerate(result):
        liststore.append([dbname])
        if dbname == dbtoload:
            index = db_num
    db_widget.set_active(index)
    return len(liststore)

def _refresh_langlist(lang_widget, host, port):
    liststore = lang_widget.get_model()
    liststore.clear()
    lang_list = rpc.db_exec(host, port, 'list_lang')
    Main.get_main().refresh_ssl()
    index = -1
    i = 0
    lang = locale.getdefaultlocale()[0]
    for key, val in lang_list:
        liststore.insert(i, (val, key))
        if key == lang:
            index = i
        if key == 'en_US' and index < 0 :
            index = i
        i += 1
    lang_widget.set_active(index)
    return lang_list

def _request_server(server_widget, parent):
    result = False
    dialog = gtk.Dialog(
        title =  _('Server'),
        parent = parent,
        flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT |
            gtk.WIN_POS_CENTER_ON_PARENT | 
            gtk.gdk.WINDOW_TYPE_HINT_DIALOG,)
    vbox = gtk.VBox()
    label_connect = gtk.Label(_("<b>Connect to a Tryton server</b>"))
    label_connect.set_use_markup(True)
    label_connect.set_alignment(0, 0.5)
    vbox.pack_start(label_connect, False, False, 0)
    hseparator = gtk.HSeparator()
    vbox.pack_start(hseparator, False, True, 0)
    table = gtk.Table(2, 2, False)
    table.set_border_width(12)
    table.set_row_spacings(6)
    vbox.pack_start(table, False, True, 0)
    label_server = gtk.Label(_("Server:"))
    label_server.set_alignment(1, 0)
    label_server.set_padding(3, 0)
    table.attach(label_server, 0, 1, 0, 1, yoptions=False,
        xoptions=gtk.FILL)
    entry_port = gtk.Entry()
    entry_port.set_max_length(5)
    entry_port.set_text("8069")
    entry_port.set_activates_default(True)
    entry_port.set_width_chars(16)
    table.attach(entry_port, 1, 2, 1, 2, yoptions=False,
        xoptions=gtk.FILL)
    entry_server = gtk.Entry()
    entry_server.set_text("localhost")
    entry_server.set_activates_default(True)
    entry_server.set_width_chars(16)
    table.attach(entry_server, 1, 2, 0, 1,yoptions=False,
        xoptions=gtk.FILL | gtk.EXPAND)
    label_port = gtk.Label(_("Port:"))
    label_port.set_alignment(1, 0.5)
    label_port.set_padding(3, 3)
    table.attach(label_port, 0, 1, 1, 2, yoptions=False,
        xoptions=False)
    dialog.add_button("gtk-cancel", gtk.RESPONSE_CANCEL | gtk.CAN_DEFAULT)
    dialog.add_button("gtk-ok", gtk.RESPONSE_OK)
    dialog.vbox.pack_start(vbox)
    dialog.set_transient_for(parent)
    dialog.set_icon(TRYTON_ICON)
    dialog.show_all()
    dialog.set_default_response(gtk.RESPONSE_OK)

    url_m = re.match('^([\w.-]+):(\d{1,5})$',
        server_widget.get_text())
    if url_m:
        entry_server.set_text(url_m.group(1))
        entry_port.set_text(url_m.group(2))

    res = dialog.run()
    if res == gtk.RESPONSE_OK:
        host = entry_server.get_text()
        port = int(entry_port.get_text())
        url = '%s:%d' % (host, port)
        server_widget.set_text(url)
        result = (host, port)
    parent.present()
    dialog.destroy()
    return result


class DBLogin(object):
    def __init__(self, parent=None):
        self.dialog = gtk.Dialog(
            title =  _('Login'),
            parent = parent,
            flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,)
        self.dialog.set_size_request(500, 301)
        self.dialog.set_title (_("Login"))
        self.dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.dialog.set_has_separator(False)
        self.dialog.set_icon(TRYTON_ICON)
        self.dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CANCEL)
        self.button_connect = gtk.Button(_('C_onnect'))
        self.button_connect.set_flags(gtk.CAN_FOCUS|gtk.CAN_DEFAULT
            |gtk.HAS_DEFAULT)
        self.dialog.add_action_widget(self.button_connect, gtk.RESPONSE_OK)
        self.dialog.set_default_response(gtk.RESPONSE_OK)
        dialog_vbox = gtk.VBox()
        vbox_image = gtk.VBox()
        image = gtk.Image()
        image.set_from_file(os.path.join(PIXMAPS_DIR, 'tryton.png'))
        image.set_size_request(500, 129)
        vbox_image.pack_start(image)
        dialog_vbox.pack_start(vbox_image)
        table_main = gtk.Table(4, 3, False)
        table_main.set_border_width(10)
        table_main.set_row_spacings(3)
        table_main.set_col_spacings(3)
        vbox_image.pack_start(table_main, True, True, 0)
        vbox_combo = gtk.VBox()
        self.combo_database = gtk.ComboBox()
        self.combo_label = gtk.Label()
        self.combo_label.set_use_markup(True)
        self.combo_label.set_alignment(0.01, 1)
        vbox_combo.pack_start(self.combo_database, True, True, 0)
        vbox_combo.pack_start(self.combo_label, False, False, 0)
        table_main.attach(vbox_combo, 1, 3, 1, 2, yoptions=False, 
            xoptions=gtk.FILL)
        self.entry_password = gtk.Entry()
        self.entry_password.set_visibility(False)
        self.entry_password.set_activates_default(True)
        table_main.attach(self.entry_password, 1, 3, 3, 4, yoptions=False,
            xoptions=gtk.FILL)
        self.entry_login = gtk.Entry()
        self.entry_login.set_text("admin")
        self.entry_login.set_activates_default(True)
        table_main.attach(self.entry_login, 1, 3, 2, 3, yoptions=False,
            xoptions=gtk.FILL)
        label_server = gtk.Label()
        label_server.set_text(_("Server:"))
        label_server.set_size_request(117, -1)
        label_server.set_alignment(1, 0.5)
        label_server.set_padding(3, 3)
        table_main.attach(label_server, 0, 1, 0, 1, yoptions=False,
            xoptions=gtk.FILL)
        label_database = gtk.Label()
        label_database.set_text(_("Database:"))
        label_database.set_alignment(1, 0.5)
        label_database.set_padding(3, 3)
        table_main.attach(label_database, 0, 1, 1, 2,yoptions=False,
            xoptions=gtk.FILL)
        self.entry_server = gtk.Entry()
        table_main.attach(self.entry_server, 1, 2, 0, 1, yoptions=False, 
            xoptions=gtk.FILL)
        self.entry_server.set_sensitive(False)
        self.entry_server.unset_flags(gtk.CAN_FOCUS)
        self.entry_server.set_editable(False)
        self.entry_server.set_text("localhost")
        self.entry_server.set_activates_default(True)
        self.entry_server.set_width_chars(16)
        self.button_server = gtk.Button(label=_("C_hange"), stock=None, 
            use_underline=True)
        table_main.attach(self.button_server, 2, 3, 0, 1, yoptions=False,
            xoptions=gtk.FILL)
        label_password = gtk.Label(str = _("Password:"))
        label_password.set_justify(gtk.JUSTIFY_RIGHT)
        label_password.set_alignment(1, 0.5)
        label_password.set_padding(3, 3)
        table_main.attach(label_password, 0, 1, 3, 4, yoptions=False,
            xoptions=gtk.FILL)
        label_username = gtk.Label(str = _("User name:"))
        label_username.set_alignment(1, 0.5)
        label_username.set_padding(3, 3)
        table_main.attach(label_username, 0, 1, 2, 3,yoptions=False,
            xoptions=gtk.FILL)
        self.entry_password.grab_focus()
        self.dialog.vbox.pack_start(dialog_vbox)

    @staticmethod
    def refreshlist(widget, db_widget, label, host, port, butconnect=None):
        res = _refresh_dblist(db_widget, host, port)
        if res is None:
            label.set_label('<b>'+_('Could not connect to server!')+'</b>')
            db_widget.hide()
            label.show()
            if butconnect:
                butconnect.set_sensitive(False)
        elif res==0:
            label.set_label('<b>' + \
                    _('No database found, you must create one!') + '</b>')
            db_widget.hide()
            label.show()
            if butconnect:
                butconnect.set_sensitive(False)
        else:
            label.hide()
            db_widget.show()
            if butconnect:
                butconnect.set_sensitive(True)
        return res

    @staticmethod
    def refreshlist_ask(widget, server_widget, db_widget, label,
            butconnect=False, host=False, port=0, parent=None):
        host, port = _request_server(server_widget, parent) or (host, port)
        return DBLogin.refreshlist(widget, db_widget, label, host, port,
                butconnect)

    def run(self, dbname, parent):
        self.dialog.set_transient_for(parent)
        self.dialog.show_all()
        self.combo_label.hide()

        host = CONFIG['login.server']
        port = int(CONFIG['login.port'])

        url = '%s:%d' % (host, port)
        self.entry_server.set_text(url)
        self.entry_login.set_text(CONFIG['login.login'])

        # construct the list of available db and select the last one used
        liststore = gtk.ListStore(str)
        self.combo_database.set_model(liststore)
        cell = gtk.CellRendererText()
        self.combo_database.pack_start(cell, True)
        self.combo_database.add_attribute(cell, 'text', 0)

        res = self.refreshlist(None, self.combo_database, self.combo_label, 
            host, port, self.button_connect)
        
        self.button_server.connect_after('clicked', DBLogin.refreshlist_ask,
            self.entry_server, self.combo_database, self.combo_label, 
            self.button_connect, host, port, self.dialog)
        if dbname:
            i = liststore.get_iter_root()
            while i:
                if liststore.get_value(i, 0)==dbname:
                    self.combo_database.set_active_iter(i)
                    break
                i = liststore.iter_next(i)

        res = self.dialog.run()
        url_m = re.match('^([\w.:\-\d]+):(\d{1,5})$',
                self.entry_server.get_text() or '')
        if url_m:
            CONFIG['login.server'] = url_m.group(1)
            CONFIG['login.login'] = self.entry_login.get_text()
            CONFIG['login.port'] = url_m.group(2)
            CONFIG['login.db'] = self.combo_database.get_active_text()
            result = (self.entry_login.get_text(), 
                self.entry_password.get_text(), url_m.group(1), 
                int(url_m.group(2)), self.combo_database.get_active_text())
        else:
            parent.present()
            self.dialog.destroy()
            raise Exception('QueryCanceled')
        if res != gtk.RESPONSE_OK:
            parent.present()
            self.dialog.destroy()
            rpc.logout()
            Main.get_main().refresh_ssl()
            raise Exception('QueryCanceled')
        parent.present()
        self.dialog.destroy()
        return result

class DBCreate(object):
    def set_sensitive(self, sensitive):
        if sensitive:
            label = self.dialog.get_widget('db_label_info')
            label.set_text(_('Do not use special characters!'))
            self.dialog.get_widget('button_db_ok').set_sensitive(True)
        else:
            label = self.dialog.get_widget('db_label_info')
            label.set_markup('<b>' + \
                    _('Can not connect to server!') + '</b>')
            self.dialog.get_widget('button_db_ok').set_sensitive(False)
        return sensitive

    def server_change(self, widget, parent):
        host, port = _request_server(self.server_widget, parent)
        try:
            if self.lang_widget and host and port:
                _refresh_langlist(self.lang_widget, host, port)
            self.set_sensitive(True)
        except:
            self.set_sensitive(False)
            return False
        return url

    def __init__(self, sig_login):
        self.dialog = glade.XML(GLADE, "win_createdb", gettext.textdomain())
        self.sig_login = sig_login
        self.lang_widget = self.dialog.get_widget('db_create_combo')
        self.db_widget = self.dialog.get_widget('ent_db')
        self.server_widget = self.dialog.get_widget('ent_server_new')

    def run(self, parent):
        win = self.dialog.get_widget('win_createdb')
        win.set_default_response(gtk.RESPONSE_OK)
        win.set_transient_for(parent)
        win.show_all()
        pass_widget = self.dialog.get_widget('ent_password_new')
        change_button = self.dialog.get_widget('but_server_new')

        change_button.connect_after('clicked', self.server_change, win)
        host = CONFIG['login.server']
        port = int(CONFIG['login.port'])
        url = '%s:%d' % (host, port)

        self.server_widget.set_text(url)
        liststore = gtk.ListStore(str, str)
        self.lang_widget.set_model(liststore)
        try:
            _refresh_langlist(self.lang_widget, host, port)
        except:
            self.set_sensitive(False)

        while True:
            res = win.run()
            dbname = self.db_widget.get_text()
            if (res==gtk.RESPONSE_OK) \
                    and ((not dbname) \
                        or (not re.match('^[a-zA-Z][a-zA-Z0-9_]+$', dbname))):
                common.warning(_('The database name must contain ' \
                        'only normal characters or "_".\n' \
                        'You must avoid all accents, space ' \
                        'or special characters.'), parent,
                        _('Bad database name!'))

            else:
                break

        langidx = self.lang_widget.get_active_iter()
        langreal = langidx \
                and self.lang_widget.get_model().get_value(langidx, 1)
        passwd = pass_widget.get_text()
        url = self.server_widget.get_text()
        url_m = re.match('^([\w.\-]+):(\d{1,5})$',
                url or '')
        if url_m:
            CONFIG['login.server'] = host = url_m.group(1)
            CONFIG['login.port'] = port = url_m.group(2)
        parent.present()
        win.destroy()

        if res == gtk.RESPONSE_OK:
            try:
                if rpc.db_exec(host, int(port), 'db_exist', dbname):
                    common.warning(_('Try with an other name.'), parent,
                            _('The Database already exists!'))
                    return False
                users = rpc.db_exec(host, int(port), 'create', passwd, dbname,
                            langreal)
                Main.get_main().refresh_ssl()
            except Exception, exception:
                common.warning(_('The server crashed during installation.\n' \
                        'We suggest you to drop this database.\n' \
                        'Error message:\n') + str(exception[0]), parent,
                        _("Error during database creation!"))
                return False
            dialog = glade.XML(GLADE, "dia_dbcreate_ok", gettext.textdomain())
            win = dialog.get_widget('dia_dbcreate_ok')
            win.set_transient_for(parent)
            win.show_all()
            buf = dialog.get_widget('dia_tv').get_buffer()

            buf.delete(buf.get_start_iter(), buf.get_end_iter())
            iter_start = buf.get_start_iter()

            pwdlst = '\n'.join(['    - %s: %s / %s' % \
                    (x['name'], x['login'], x['password']) for x in users])

            buf.insert(iter_start, _('The following users have been ' \
                    'installed on your database:') + '\n\n' + pwdlst + \
                    '\n\n' + _('You can now connect to the database ' \
                    'as an administrator.'))
            res = win.run()
            parent.present()
            win.destroy()

            if res == gtk.RESPONSE_OK:
                url_m = re.match('^(http[s]?://|socket://)([\w.]+):(\d{1,5})$',
                        url)
                res = ['admin', 'admin']
                if url_m:
                    res.append(url_m.group(2))
                    res.append(url_m.group(3))
                    res.append(url_m.group(1))
                    res.append(dbname)

                self.sig_login(dbname=dbname)
            return True
        else:
            rpc.logout()
            Main.get_main().refresh_ssl()


class Tips(object):

    def __init__(self, parent):
        self.win = gtk.Dialog(_('Tips'), parent,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        self.win.set_icon(TRYTON_ICON)

        self.win.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)

        vbox = gtk.VBox()
        img = gtk.Image()
        img.set_from_file(os.path.join(PIXMAPS_DIR, 'tryton.png'))
        vbox.pack_start(img, False, False)
        self.label = gtk.Label()
        self.label.set_alignment(0, 0)
        vbox.pack_start(self.label, True, True)
        separator = gtk.HSeparator()
        vbox.pack_start(separator, False, False)

        hbox = gtk.HBox()
        self.check = gtk.CheckButton(_('_Display a new tip next time'), True)
        self.check.set_active(True)
        hbox.pack_start(self.check)
        but_previous = gtk.Button()
        hbox_previous = gtk.HBox()
        img_previous = gtk.Image()
        img_previous.set_from_stock('tryton-go-previous', gtk.ICON_SIZE_BUTTON)
        hbox_previous.pack_start(img_previous)
        label_previous = gtk.Label(_('Previous'))
        hbox_previous.pack_start(label_previous)
        but_previous.add(hbox_previous)
        but_previous.set_relief(gtk.RELIEF_NONE)
        but_previous.connect('clicked', self.tip_previous)
        hbox.pack_start(but_previous)
        hbox_next = gtk.HBox()
        label_next = gtk.Label(_('Next'))
        hbox_next.pack_start(label_next)
        but_next = gtk.Button()
        img_next = gtk.Image()
        img_next.set_from_stock('tryton-go-next', gtk.ICON_SIZE_BUTTON)
        hbox_next.pack_start(img_next)
        but_next.add(hbox_next)
        but_next.set_relief(gtk.RELIEF_NONE)
        but_next.connect('clicked', self.tip_next)
        hbox.pack_start(but_next)
        vbox.pack_start(hbox, False, False)
        self.win.vbox.pack_start(vbox)
        self.win.show_all()

        try:
            self.number = int(CONFIG['tip.position'])
        except:
            self.number = 0

        self.tip_set()

        self.win.run()
        CONFIG['tip.autostart'] = self.check.get_active()
        CONFIG['tip.position'] = self.number + 1
        CONFIG.save()
        parent.present()
        self.win.destroy()

    def tip_set(self):
        lang = CONFIG['client.lang']
        tip_file = False
        if lang:
            tip_file = os.path.join(DATA_DIR, 'tipoftheday.'+lang+'.txt')
        if not os.path.isfile(tip_file):
            tip_file = os.path.join(DATA_DIR, 'tipoftheday.txt')
        if not os.path.isfile(tip_file):
            return
        tips = file(tip_file).read().split('---')
        tip = tips[self.number % len(tips)].lstrip()
        del tips
        self.label.set_text(tip)
        self.label.set_use_markup(True)

    def tip_next(self, widget):
        self.number += 1
        self.tip_set()

    def tip_previous(self, widget):
        self.number -= 1
        self.tip_set()


class Credits(object):

    def __init__(self, parent):
        self.win = gtk.Dialog(_('Credits'), parent,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        self.win.set_icon(TRYTON_ICON)

        self.win.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)

        vbox = gtk.VBox()
        img = gtk.Image()
        img.set_from_file(os.path.join(PIXMAPS_DIR, 'tryton.png'))
        vbox.pack_start(img, False, False)
        self.label = gtk.Label()
        self.label.set_alignment(0.5, 0)
        contributors_file = os.path.join(DATA_DIR, 'contributors.txt')
        contributors = '\n' + _('<b>Contributors:</b>') + '\n\n'
        contributors += file(contributors_file).read()
        self.label.set_text(contributors)
        self.label.set_use_markup(True)
        vbox.pack_start(self.label, True, True)
        self.win.vbox.pack_start(vbox)
        self.win.show_all()

        self.win.run()
        parent.present()
        self.win.destroy()

_MAIN = []

class Main(object):
    window = None

    def __init__(self):
        super(Main, self).__init__()

        self.glade = glade.XML(GLADE, "win_main", gettext.textdomain())
        self.status_bar_main = self.glade.get_widget('hbox_status_main')
        self.toolbar = self.glade.get_widget('main_toolbar')
        self.sb_requests = self.glade.get_widget('sb_requests')
        self.sb_username = self.glade.get_widget('sb_user_name')
        self.sb_servername = self.glade.get_widget('sb_user_server')
        sb_id = self.sb_servername.get_context_id('message')
        self.sb_servername.push(sb_id, _('Press Ctrl+O to login'))
        self.secure_img = self.glade.get_widget('secure_img')

        window = self.glade.get_widget('win_main')
        window.connect("destroy", Main.sig_quit)
        window.connect("delete_event", self.sig_delete)
        self.window = window
        self.window.set_icon(TRYTON_ICON)

        self.notebook = gtk.Notebook()
        self.notebook.popup_enable()
        self.notebook.set_scrollable(True)
        self.notebook.connect_after('switch-page', self._sig_page_changt)
        vbox = self.glade.get_widget('vbox_main')
        vbox.pack_start(self.notebook, expand=True, fill=True)

        self.tooltips = gtk.Tooltips()

        self.shortcut_menu = self.glade.get_widget('shortcut')

        #
        # Default Notebook
        #

        self.notebook.show()
        self.pages = []
        self.current_page = 0
        self.last_page = 0

        signals = {
            'on_login_activate': self.sig_login,
            'on_logout_activate': self.sig_logout,
            'on_win_next_activate': self.sig_win_next,
            'on_win_prev_activate': self.sig_win_prev,
            'on_plugin_execute_activate': self.sig_plugin_execute,
            'on_quit_activate': self.sig_close,
            'on_but_menu_clicked': self.sig_win_menu,
            'on_win_new_activate': self.sig_win_menu,
            'on_win_home_activate': self.sig_home_new,
            'on_win_close_activate': self.sig_win_close,
            'on_preference_activate': self.sig_user_preferences,
            'on_read_requests_activate': self.sig_request_open,
            'on_send_request_activate': self.sig_request_new,
            'on_request_wait_activate': self.sig_request_wait,
            'on_opt_save_activate': lambda x: CONFIG.save(),
            'on_menubar_default_activate': lambda x: self.sig_menubar('default'),
            'on_menubar_icons_activate': lambda x: self.sig_menubar('icons'),
            'on_menubar_text_activate': lambda x: self.sig_menubar('text'),
            'on_menubar_both_activate': lambda x: self.sig_menubar('both'),
            'on_mode_normal_activate': lambda x: self.sig_mode_change(False),
            'on_mode_pda_activate': lambda x: self.sig_mode_change(True),
            'on_opt_form_tab_top_activate': lambda x: Main.sig_form_tab('top'),
            'on_opt_form_tab_left_activate': lambda x: \
                    Main.sig_form_tab('left'),
            'on_opt_form_tab_right_activate': lambda x: \
                    Main.sig_form_tab('right'),
            'on_opt_form_tab_bottom_activate': lambda x: \
                    Main.sig_form_tab('bottom'),
            'on_opt_form_tab_orientation_horizontal_activate': lambda x: \
                    Main.sig_form_tab_orientation(0),
            'on_opt_form_tab_orientation_vertical_activate': lambda x: \
                    Main.sig_form_tab_orientation(90),
            'on_opt_files_actions_activate': self.sig_files_actions,
            'on_help_tips_activate': self.sig_tips,
            'on_help_license_activate': self.sig_license,
            'on_help_credits_activate': self.sig_credits,
            'on_shortcuts_activate' : self.sig_shortcuts,
            'on_db_new_activate': self.sig_db_new,
            'on_db_restore_activate': self.sig_db_restore,
            'on_db_backup_activate': self.sig_db_dump,
            'on_db_drop_activate': self.sig_db_drop,
            'on_admin_password_activate': self.sig_db_password,
        }
        for signal in signals:
            self.glade.signal_connect(signal, signals[signal])

        self.buttons = {}
        for button in (
                'but_new',
                'but_save',
                'but_remove',
                'but_search',
                'but_previous',
                'but_next',
                'but_action',
                'but_print',
                'but_close',
                'but_reload',
                'but_switch',
                'but_attach',
                ):
            self.glade.signal_connect('on_'+button+'_clicked',
                    self._sig_child_call, button)
            self.buttons[button] = self.glade.get_widget(button)

        menus = {
            'form_del': 'but_remove',
            'form_new': 'but_new',
            'form_copy': 'but_copy',
            'form_reload': 'but_reload',
            'form_log': 'but_log',
            'form_search': 'but_search',
            'form_previous': 'but_previous',
            'form_next': 'but_next',
            'form_save': 'but_save',
            'goto_id': 'but_goto_id',
            'form_actions': 'but_action',
            'form_print': 'but_print',
            'form_save_as': 'but_save_as',
            'form_import': 'but_import',
            'form_filter': 'but_filter',
        }
        for menu in menus:
            self.glade.signal_connect('on_'+menu+'_activate',
                    self._sig_child_call, menus[menu])

        self.sb_set()

        settings = gtk.settings_get_default()
        settings.set_long_property('gtk-button-images', 1, 'Tryton:gui.main')

        def fnc_menuitem(menuitem, opt_name):
            CONFIG[opt_name] = menuitem.get_active()
        signals = {
            'on_opt_form_toolbar_activate': (fnc_menuitem, 'form.toolbar',
                'opt_form_toolbar'),
            'on_opt_tree_width_activate': (fnc_menuitem, 'client.tree_width',
                'opt_tree_width'),
        }
        self.glade.get_widget('menubar_'+(CONFIG['client.toolbar'] or \
                'both')).set_active(True)
        self.sig_menubar(CONFIG['client.toolbar'] or 'default')
        self.glade.get_widget('opt_form_tab_' + (CONFIG['client.form_tab'] or \
                'left')).set_active(True)
        Main.sig_form_tab(CONFIG['client.form_tab'] or 'left')
        self.glade.get_widget('opt_form_tab_orientation_' + \
                (str(CONFIG['client.form_tab_orientation']) or \
                '0')).set_active(True)
        Main.sig_form_tab_orientation(CONFIG['client.form_tab_orientation'] or \
                0)
        if CONFIG['client.modepda']:
            self.glade.get_widget('mode_pda').set_active(True)
        else:
            self.glade.get_widget('mode_normal').set_active(True)
        self.sig_mode()
        for signal in signals:
            self.glade.signal_connect(signal, signals[signal][0],
                    signals[signal][1])
            self.glade.get_widget(signals[signal][2]).set_active(
                    int(bool(CONFIG[signals[signal][1]])))

        if os.name == 'nt':
            # Disable actions, on win32 we use os.startfile
            self.glade.get_widget('actions').set_sensitive(False)

        # Adding a timer the check to requests
        gobject.timeout_add(5 * 60 * 1000, self.request_set)
        _MAIN.append(self)

    @staticmethod
    def get_main():
        return _MAIN[0]

    def shortcut_set(self, shortcuts=None):
        def _action_shortcut(widget, action):
            ctx = rpc.CONTEXT.copy()
            Action.exec_keyword('tree_open', {'model': 'ir.ui.menu',
                'id': action, 'ids': [action],
                'window': self.window}, context=ctx)
        if shortcuts is None:
            user = rpc._USER
            try:
                shortcuts = rpc.execute('object', 'execute',
                        'ir.ui.view_sc', 'get_sc', user, 'ir.ui.menu',
                        rpc.CONTEXT)
            except:
                shortcuts = []
        menu = gtk.Menu()
        for shortcut in shortcuts:
            menuitem = gtk.MenuItem(shortcut['name'])
            menuitem.connect('activate', _action_shortcut, shortcut['res_id'])
            menu.add(menuitem)
        menu.show_all()
        self.shortcut_menu.set_submenu(menu)
        self.shortcut_menu.set_sensitive(True)

    def shortcut_unset(self):
        menu = gtk.Menu()
        menu.show_all()
        self.shortcut_menu.set_submenu(menu)
        self.shortcut_menu.set_sensitive(False)

    def sig_mode_change(self, pda_mode=False):
        CONFIG['client.modepda'] = pda_mode
        return self.sig_mode()

    def sig_mode(self):
        pda_mode = CONFIG['client.modepda']
        if pda_mode:
            self.status_bar_main.hide()
        else:
            self.status_bar_main.show()
        return pda_mode

    def sig_menubar(self, option):
        CONFIG['client.toolbar'] = option
        if option == 'default':
            self.toolbar.set_style(False)
        elif option == 'both':
            self.toolbar.set_style(gtk.TOOLBAR_BOTH)
        elif option == 'text':
            self.toolbar.set_style(gtk.TOOLBAR_TEXT)
        elif option == 'icons':
            self.toolbar.set_style(gtk.TOOLBAR_ICONS)

    @staticmethod
    def sig_form_tab(option):
        CONFIG['client.form_tab'] = option

    @staticmethod
    def sig_form_tab_orientation(option):
        CONFIG['client.form_tab_orientation'] = option

    def sig_files_actions(self, widget):
        FilesActions(self.window).run()

    def sig_win_next(self, widget):
        page = self.notebook.get_current_page()
        if page == len(self.pages) - 1:
            page = -1
        self.notebook.set_current_page(page + 1)

    def sig_win_prev(self, widget):
        page = self.notebook.get_current_page()
        self.notebook.set_current_page(page - 1)

    def sig_user_preferences(self, widget):
        win = Preference(rpc._USER, self.window)
        if win.run():
            rpc.context_reload()
            if 'language_direction' in rpc.CONTEXT:
                translate.set_language_direction(
                        rpc.CONTEXT['language_direction'])
            prefs = rpc.execute('object', 'execute', 'res.user',
                    'get_preferences', False, rpc.CONTEXT)
            sb_id = self.sb_username.get_context_id('message')
            self.sb_username.push(sb_id, prefs.get('status_bar', ''))
            if prefs and 'language' in prefs:
                translate.setlang(prefs['language'])
                CONFIG['client.lang'] = prefs['language']
                CONFIG.save()
        self.window.present()
        return True

    def sig_win_close(self, widget):
        self._sig_child_call(widget, 'but_close')

    def sig_request_new(self, widget):
        return Window.create(None, 'res.request', False,
                [('act_from', '=', rpc._USER)], 'form',
                mode=['form', 'tree'], window=self.window,
                context={'active_test': False})

    def sig_request_open(self, widget):
        ids = self.request_set()[0]
        return Window.create(False, 'res.request', ids,
                [('act_to', '=', rpc._USER), ('active', '=', True)],
                'form', mode=['tree', 'form'], window=self.window,
                context={'active_test': False})

    def sig_request_wait(self, widget):
        ids = self.request_set()[0]
        return Window.create(False, 'res.request', ids,
                [('act_from', '=', rpc._USER),
                    ('state', '=', 'waiting'), ('active', '=', True)],
                'form', mode=['tree', 'form'], window=self.window,
                context={'active_test': False})

    def request_set(self):
        try:
            ids, ids2 = rpc.execute('object', 'execute',
                    'res.request', 'request_get')
            if len(ids):
                message = _('%s request(s)') % len(ids)
            else:
                message = _('No request')
            if len(ids2):
                message += _(' - %s request(s) sended') % len(ids2)
            sb_id = self.sb_requests.get_context_id('message')
            self.sb_requests.push(sb_id, message)
            return (ids, ids2)
        except:
            return ([], [])

    def sig_login(self, widget=None, dbname=False, res=None):
        if not res:
            try:
                dblogin = DBLogin()
                res = dblogin.run(dbname, self.window)
            except Exception, exception:
                if exception.args == ('QueryCanceled',):
                    return False
                raise
        self.window.present()
        self.sig_logout(widget, disconnect=False)
        log_response = rpc.login(*res)
        self.refresh_ssl()
        if log_response > 0:
            try:
                prefs = rpc.execute('object', 'execute',
                        'res.user', 'get_preferences', False, rpc.CONTEXT)
            except:
                prefs = None
            menu_id = self.sig_win_menu(quiet=False, prefs=prefs)
            if menu_id:
                self.sig_home_new(quiet=True, except_id=menu_id, prefs=prefs)
            self.request_set()
            if prefs and 'language' in prefs:
                translate.setlang(prefs['language'])
                CONFIG['client.lang'] = prefs['language']
            CONFIG.save()
        elif log_response == -1:
            common.message(_('Connection error !\n' \
                    'Unable to connect to the server !'), self.window)
        elif log_response == -2:
            common.message(_('Connection error !\n' \
                    'Bad username or password !'), self.window)
            return self.sig_login()
        if not self.shortcut_menu.get_property('sensitive'):
            self.shortcut_set()
        self.glade.get_widget('but_menu').set_sensitive(True)
        self.glade.get_widget('user').set_sensitive(True)
        self.glade.get_widget('form').set_sensitive(True)
        self.glade.get_widget('plugins').set_sensitive(True)
        self.glade.get_widget('request_new_but').set_sensitive(True)
        self.glade.get_widget('req_search_but').set_sensitive(True)
        self.notebook.grab_focus()
        return True

    def sig_logout(self, widget, disconnect=True):
        res = True
        while res:
            wid = self._wid_get()
            if wid:
                if 'but_close' in wid.handlers:
                    res = wid.handlers['but_close']()
                if not res:
                    return False
                res = self._win_del()
            else:
                res = False
        sb_id = self.sb_requests.get_context_id('message')
        self.sb_requests.push(sb_id, '')
        sb_id = self.sb_username.get_context_id('message')
        self.sb_username.push(sb_id, _('Not logged !'))
        sb_id = self.sb_servername.get_context_id('message')
        self.sb_servername.push(sb_id, _('Press Ctrl+O to login'))
        self.shortcut_unset()
        self.glade.get_widget('but_menu').set_sensitive(False)
        self.glade.get_widget('user').set_sensitive(False)
        self.glade.get_widget('form').set_sensitive(False)
        self.glade.get_widget('plugins').set_sensitive(False)
        self.glade.get_widget('request_new_but').set_sensitive(False)
        self.glade.get_widget('req_search_but').set_sensitive(False)
        if disconnect:
            rpc.logout()
        self.refresh_ssl()
        return True

    def refresh_ssl(self):
        if rpc.SECURE:
            self.secure_img.show()
        else:
            self.secure_img.hide()

    def sig_tips(self, *args):
        Tips(self.window)

    def sig_license(self, widget):
        dialog = glade.XML(GLADE, "win_license", gettext.textdomain())
        dialog.signal_connect("on_but_ok_pressed",
                lambda obj: dialog.get_widget('win_license').destroy())

        win = dialog.get_widget('win_license')
        win.set_transient_for(self.window)
        win.show_all()

    def sig_credits(self, widget):
        Credits(self.window)

    def sig_shortcuts(self, widget):
        shortcuts_win = glade.XML(GLADE, 'shortcuts_dia', gettext.textdomain())
        shortcuts_win.signal_connect("on_but_ok_pressed",
                lambda obj: shortcuts_win.get_widget('shortcuts_dia').destroy())

        win = shortcuts_win.get_widget('shortcuts_dia')
        win.set_transient_for(self.window)
        win.show_all()

    def sig_win_menu(self, widget=None, quiet=True, prefs=None):
        for page in range(len(self.pages)):
            if self.pages[page].model == 'ir.ui.menu':
                page_num = self.notebook.page_num(self.pages[page].widget)
                self.notebook.set_current_page(page_num)
                return True
        res = self.sig_win_new(widget, menu_type='menu', quiet=quiet,
                prefs=prefs)
        return res

    def sig_win_new(self, widget=None, menu_type='menu', quiet=True,
            except_id=False, prefs=None):
        if not prefs:
            try:
                prefs = rpc.execute('object', 'execute',
                        'res.user', 'get_preferences', False, rpc.CONTEXT)
            except:
                return False
        sb_id = self.sb_username.get_context_id('message')
        self.sb_username.push(sb_id, prefs['status_bar'] or '')
        sb_id = self.sb_servername.get_context_id('message')
        self.sb_servername.push(sb_id, '%s@%s:%d/%s' % (rpc._USERNAME,
            rpc._SOCK.hostname, rpc._SOCK.port, rpc._DATABASE))
        if not prefs[menu_type]:
            if quiet:
                return False
            common.warning(_('You can not log into the system !\n' \
                    'Ask the administrator to verify\n' \
                    'you have an action defined for your user.'),
                    'Access Denied!', self.window)
            rpc.logout()
            self.refresh_ssl()
            return False
        act_id = prefs[menu_type]
        if except_id and act_id == except_id:
            return act_id
        Action.execute(act_id, {'window': self.window})
        return act_id

    def sig_home_new(self, widget=None, quiet=True, except_id=False,
            prefs=None):
        return self.sig_win_new(widget, menu_type='action', quiet=quiet,
                except_id=except_id, prefs=prefs)

    def sig_plugin_execute(self, widget):
        page = self.notebook.get_current_page()
        datas = {
                'model': self.pages[page].model,
                'ids': self.pages[page].ids_get(),
                'id': self.pages[page].id_get(),
                }
        tryton.plugin.execute(datas, self.window)

    @staticmethod
    def sig_quit(widget):
        CONFIG.save()
        gtk.main_quit()

    def sig_close(self, widget):
        if common.sur(_("Do you really want to quit ?"), parent=self.window):
            if not self.sig_logout(widget):
                return False
            CONFIG.save()
            gtk.main_quit()

    def sig_delete(self, widget, event):
        if common.sur(_("Do you really want to quit ?"), parent=self.window):
            if not self.sig_logout(widget):
                return True
            return False
        return True

    def win_add(self, page):
        self.pages.append(page)
        hbox = gtk.HBox()
        if len(page.name) > 15:
            name = page.name[:13] + '...'
        else:
            name = page.name
        label = gtk.Label(name)
        self.tooltips.set_tip(label, page.name)
        self.tooltips.enable()
        label.set_alignment(0.0, 0.5)
        hbox.pack_start(label, expand=True, fill=True)
        button = gtk.Button()
        img = gtk.Image()
        img.set_from_stock('tryton-close', gtk.ICON_SIZE_SMALL_TOOLBAR)
        button.set_relief(gtk.RELIEF_NONE)
        button.add(img)
        hbox.pack_start(button, expand=False, fill=False)
        hbox.show_all()
        hbox.set_size_request(120, -1)
        button.connect('clicked', self._sig_remove_book, page.widget)
        label_menu = gtk.Label(page.name)
        label_menu.set_alignment(0.0, 0.5)
        self.notebook.append_page_menu(page.widget, hbox, label_menu)
        if hasattr(self.notebook, 'set_tab_reorderable'):
            self.notebook.set_tab_reorderable(page.widget, True)
        self.notebook.set_current_page(-1)
        page.signal_connect(self, 'attachment-count', self._attachment_count)

    def sb_set(self, view=None):
        if not view:
            view = self._wid_get()
        for i in self.buttons:
            if self.buttons[i]:
                self.buttons[i].set_sensitive(
                        bool(view and (i in view.handlers)))
        self.buttons['but_attach'].set_stock_id('tryton-attachment')

    def _attachment_count(self, widget, signal_data):
        label = _('Attachment(%d)') % signal_data
        self.buttons['but_attach'].set_label(label)
        if signal_data:
            self.buttons['but_attach'].set_stock_id('tryton-attachment-hi')
        else:
            self.buttons['but_attach'].set_stock_id('tryton-attachment')

    def _sig_remove_book(self, widget, page_widget):
        for page in self.pages:
            if page.widget == page_widget:
                if 'but_close' in page.handlers:
                    res = page.handlers['but_close']()
                    if not res:
                        return
        self._win_del(page_widget)

    def _win_del(self, page_widget=None):
        if page_widget:
            page_id = self.notebook.page_num(page_widget)
        else:
            page_id = int(self.notebook.get_current_page())
            page_widget = self.notebook.get_nth_page(page_id)
        if page_id != -1:
            page = None
            for i in range(len(self.pages)):
                if self.pages[i].widget == page_widget:
                    page = self.pages.pop(i)
                    page.signal_unconnect(self)
                    break
            self.notebook.remove_page(page_id)
            self.sb_set()

            if hasattr(page, 'destroy'):
                page.destroy()
            del page
        return self.notebook.get_current_page() != -1

    def _wid_get(self):
        page_id = self.notebook.get_current_page()
        if page_id == -1:
            return None
        page_widget = self.notebook.get_nth_page(page_id)
        for page in self.pages:
            if page.widget == page_widget:
                return page
        return None

    def _sig_child_call(self, widget, button_name):
        wid = self._wid_get()
        if wid:
            res = True
            if button_name in wid.handlers:
                res = wid.handlers[button_name]()
            if button_name == 'but_close' and res:
                self._win_del()

    def _sig_page_changt(self, notebook, page, page_num):
        self.last_page = self.current_page
        self.current_page = self.notebook.get_current_page()
        title = _('Tryton')
        page = self._wid_get()
        if page:
            title += ' - ' + page.name
        self.window.set_title(title)
        self.sb_set()

    def sig_db_new(self, widget):
        if not self.sig_logout(widget):
            return False
        dia = DBCreate(self.sig_login)
        res = dia.run(self.window)
        if res:
            CONFIG.save()
        return res

    def sig_db_drop(self, widget):
        if not self.sig_logout(widget):
            return False
        url, dbname, passwd = self._choose_db_select(_('Delete a database'))
        if not dbname:
            rpc.logout()
            Main.get_main().refresh_ssl()
            return

        host, port = url.rsplit(':', 1)

        try:
            rpc.db_exec(host, int(port), 'drop', passwd, dbname)
        except Exception, exception:
            self.refresh_ssl()
            common.warning(_('Database drop failed with '\
                    'error message:\n') + str(exception[0]), self.window,
                    _('Database drop failed!'))
            return
        self.refresh_ssl()
        common.message(_("Database dropped successfully!"),
                parent=self.window)

    def sig_db_restore(self, widget):
        filename = common.file_selection(_('Open...'), parent=self.window,
                preview=False)
        if not filename:
            rpc.logout()
            Main.get_main().refresh_ssl()
            return

        url, dbname, passwd = self._choose_db_ent()
        if dbname:
            file_p = file(filename, 'rb')
            data_b64 = base64.encodestring(file_p.read())
            file_p.close()
            host, port = url.rsplit(':' , 1)
            try:
                res = rpc.db_exec(host, int(port), 'restore', passwd, dbname,
                        data_b64)
            except Exception, exception:
                self.refresh_ssl()
                common.warning(_('Database restore failed with ' \
                        'error message:\n') + str(exception[0]), self.window,
                        _('Database restore failed!'))
                return
            self.refresh_ssl()
            if res:
                common.message(_("Database restored successfully!"),
                        parent=self.window)
            else:
                common.message(_('Database restore failed!'),
                        parent=self.window)
        else:
            rpc.logout()
            Main.get_main().refresh_ssl()

    def sig_db_password(self, widget):
        dialog = glade.XML(GLADE, "dia_passwd_change",
                gettext.textdomain())
        win = dialog.get_widget('dia_passwd_change')
        win.set_icon(TRYTON_ICON)
        win.set_transient_for(self.window)
        win.show_all()
        server_widget = dialog.get_widget('ent_server')
        old_pass_widget = dialog.get_widget('old_passwd')
        new_pass_widget = dialog.get_widget('new_passwd')
        new_pass2_widget = dialog.get_widget('new_passwd2')
        change_button = dialog.get_widget('but_server_change')
        change_button.connect_after('clicked', \
                lambda a,b: _request_server(b, win), server_widget)

        host = CONFIG['login.server']
        port = int(CONFIG['login.port'])
        url = '%s:%d' % (host, port)
        server_widget.set_text(url)

        res = win.run()
        if res == gtk.RESPONSE_OK:
            url = server_widget.get_text()
            old_passwd = old_pass_widget.get_text()
            new_passwd = new_pass_widget.get_text()
            new_passwd2 = new_pass2_widget.get_text()
            if new_passwd != new_passwd2:
                common.warning(_("Confirmation password do not match " \
                        "new password, operation cancelled!"),
                        _("Validation Error."), parent=win)
            else:
                try:
                    rpc.db_exec(host, port, 'change_admin_password',
                            old_passwd, new_passwd)
                except Exception, exception:
                    rpc.logout()
                    common.warning(_('Change Admin password failed with ' \
                            'error message:\n') + str(exception[0]),
                            self.window, _('Change Admin password failed!'))
                self.refresh_ssl()
        else:
            rpc.logout()
            Main.get_main().refresh_ssl()
        self.window.present()
        win.destroy()

    def sig_db_dump(self, widget):
        url, dbname, passwd = self._choose_db_select(_('Backup a database'))
        if not dbname:
            rpc.logout()
            Main.get_main().refresh_ssl()
            return

        host, port = url.rsplit(':', 1)
        try:
            dump_b64 = rpc.db_exec(host, int(port), 'dump', passwd, dbname)
        except Exception, exception:
            rpc.logout()
            Main.get_main().refresh_ssl()
            common.warning(_('Database dump failed with error message:\n') + \
                    str(exception[0]), self.window, _('Database dump failed!'))
            return
        self.refresh_ssl()
        dump = base64.decodestring(dump_b64)

        filename = common.file_selection(_('Save As...'),
                action=gtk.FILE_CHOOSER_ACTION_SAVE, parent=self.window,
                preview=False)

        if filename:
            file_ = file(filename, 'wb')
            file_.write(dump)
            file_.close()
            common.message(_("Database backuped successfully !"),
                    parent=self.window)
        else:
            rpc.logout()
            Main.get_main().refresh_ssl()

    def _choose_db_select(self, title=_("Backup a database")):
        def refreshlist(widget, db_widget, label, host, port):
            res = _refresh_dblist(db_widget, host, port)
            if res == -1:
                label.set_label('<b>' + \
                        _('Could not connect to server !') + '</b>')
                db_widget.hide()
                label.show()
            elif res==0:
                label.set_label('<b>' + \
                        _('No database found, you must create one !') + '</b>')
                db_widget.hide()
                label.show()
            else:
                label.hide()
                db_widget.show()
            return res

        def refreshlist_ask(widget, server_widget, db_widget, label,
                parent=None):
            host, port = _request_server(server_widget, parent)
            if not url:
                return None
            refreshlist(widget, db_widget, label, host, port)
            return (host, port)

        dialog = glade.XML(GLADE, "win_db_select",
                gettext.textdomain())
        win = dialog.get_widget('win_db_select')
        win.set_icon(TRYTON_ICON)
        win.set_default_response(gtk.RESPONSE_OK)
        win.set_transient_for(self.window)
        win.show_all()

        pass_widget = dialog.get_widget('ent_passwd_select')
        server_widget = dialog.get_widget('ent_server_select')
        db_widget = dialog.get_widget('combo_db_select')
        label = dialog.get_widget('label_db_select')


        dialog.get_widget('db_select_label').set_markup('<b>'+title+'</b>')

        host = CONFIG['login.server']
        port = int(CONFIG['login.port'])
        url = '%s:%d' % (host, port)
        server_widget.set_text(url)

        liststore = gtk.ListStore(str)
        db_widget.set_model(liststore)

        refreshlist(None, db_widget, label, host, port)
        change_button = dialog.get_widget('but_server_select')
        change_button.connect_after('clicked', refreshlist_ask,
                server_widget, db_widget, label, win)

        cell = gtk.CellRendererText()
        db_widget.pack_start(cell, True)
        db_widget.add_attribute(cell, 'text', 0)

        res = win.run()

        database = False
        url = False
        passwd = False
        if res == gtk.RESPONSE_OK:
            database = db_widget.get_active_text()
            url = server_widget.get_text()
            passwd = pass_widget.get_text()
        self.window.present()
        win.destroy()
        return (url, database, passwd)

    def _choose_db_ent(self):
        dialog = glade.XML(GLADE, "win_db_ent",
                gettext.textdomain())
        win = dialog.get_widget('win_db_ent')
        win.set_icon(TRYTON_ICON)
        win.set_transient_for(self.window)
        win.show_all()

        db_widget = dialog.get_widget('ent_db')
        widget_pass = dialog.get_widget('ent_password')
        widget_url = dialog.get_widget('ent_server')

        url = '%s:%d' % (CONFIG['login.server'], int(CONFIG['login.port']))
        widget_url.set_text(url)

        change_button = dialog.get_widget('but_server_change')
        change_button.connect_after('clicked', lambda a, b: _request_server(b, win),
                widget_url)

        res = win.run()

        database = False
        passwd = False
        url = False
        if res == gtk.RESPONSE_OK:
            database = db_widget.get_text()
            url = widget_url.get_text()
            passwd = widget_pass.get_text()
        self.window.present()
        win.destroy()
        return url, database, passwd

