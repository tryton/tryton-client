import os
import gettext
import urlparse
import gobject
import gtk
from gtk import glade
import tryton.rpc as rpc
from tryton.config import CONFIG, GLADE, TRYTON_ICON, PIXMAPS_DIR
import tryton.common as common
from tryton.version import VERSION
from tryton.action import Action
from tryton.gui.window import Window
from tryton.gui.window import Preference
from tryton.gui.window import FilesActions
import re
import base64

_ = gettext.gettext

def _refresh_dblist(db_widget, url, dbtoload=None):
    if not dbtoload:
        dbtoload = CONFIG['login.db']
    index = 0
    liststore = db_widget.get_model()
    liststore.clear()
    result = rpc.session.list_db(url)
    if result == -1:
        return -1
    for db_num, dbname in enumerate(result):
        liststore.append([dbname])
        if dbname == dbtoload:
            index = db_num
    db_widget.set_active(index)
    return len(liststore)

def _refresh_langlist(lang_widget, url):
    liststore = lang_widget.get_model()
    liststore.clear()
    lang_list = rpc.session.db_exec_no_except(url, 'list_lang')
    for key, val in lang_list:
        liststore.insert(0, (val, key))
    lang_widget.set_active(0)
    return lang_list

def _server_ask(server_widget, parent):
    result = False
    win_gl = glade.XML(GLADE, "win_server", gettext.textdomain())
    win = win_gl.get_widget('win_server')
    win.set_transient_for(parent)
    win.set_icon(TRYTON_ICON)
    win.show_all()
    win.set_default_response(gtk.RESPONSE_OK)
    host_widget = win_gl.get_widget('ent_host')
    port_widget = win_gl.get_widget('ent_port')
    protocol_widget = win_gl.get_widget('protocol')

    protocols = {
            'XML-RPC': 'http://',
            'XML-RPC secure': 'https://',
            'NET-RPC (faster)': 'socket://',
            }
    listprotocol = gtk.ListStore(str)
    protocol_widget.set_model(listprotocol)


    url_m = re.match('^(http[s]?://|socket://)([\w.-]+):(\d{1,5})$',
            server_widget.get_text())
    if url_m:
        host_widget.set_text(url_m.group(2))
        port_widget.set_text(url_m.group(3))

    index = 0
    i = 0
    for protocol in protocols:
        listprotocol.append([protocol])
        if url_m and protocols[protocol] == url_m.group(1):
            index = i
        i += 1
    protocol_widget.set_active(index)

    res = win.run()
    if res == gtk.RESPONSE_OK:
        protocol = protocols[protocol_widget.get_active_text()]
        url = '%s%s:%s' % (protocol, host_widget.get_text(),
                port_widget.get_text())
        server_widget.set_text(url)
        result = url
    parent.present()
    win.destroy()
    return result


class DBLogin(object):

    def __init__(self):
        self.win_gl = glade.XML(GLADE, "win_login", gettext.textdomain())

    @staticmethod
    def refreshlist(widget, db_widget, label, url, butconnect=None):
        res = _refresh_dblist(db_widget, url)
        if res == -1:
            label.set_label('<b>'+_('Could not connect to server !')+'</b>')
            db_widget.hide()
            label.show()
            if butconnect:
                butconnect.set_sensitive(False)
        elif res==0:
            label.set_label('<b>' + \
                    _('No database found, you must create one !') + '</b>')
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
            butconnect=False, url=False, parent=None):
        url = _server_ask(server_widget, parent) or url
        return DBLogin.refreshlist(widget, db_widget, label, url, butconnect)

    def run(self, dbname, parent):
        win = self.win_gl.get_widget('win_login')
        win.set_transient_for(parent)
        win.set_icon(TRYTON_ICON)
        win.show_all()
        img = self.win_gl.get_widget('image_tryton')
        img.set_from_file(os.path.join(PIXMAPS_DIR, 'tryton.png'))
        login = self.win_gl.get_widget('ent_login')
        passwd = self.win_gl.get_widget('ent_passwd')
        server_widget = self.win_gl.get_widget('ent_server')
        but_connect = self.win_gl.get_widget('button_connect')
        db_widget = self.win_gl.get_widget('combo_db')
        change_button = self.win_gl.get_widget('but_server')
        label = self.win_gl.get_widget('combo_label')
        label.hide()

        host = CONFIG['login.server']
        port = CONFIG['login.port']
        protocol = CONFIG['login.protocol']

        url = '%s%s:%s' % (protocol, host, port)
        server_widget.set_text(url)
        login.set_text(CONFIG['login.login'])

        # construct the list of available db and select the last one used
        liststore = gtk.ListStore(str)
        db_widget.set_model(liststore)
        cell = gtk.CellRendererText()
        db_widget.pack_start(cell, True)
        db_widget.add_attribute(cell, 'text', 0)

        res = self.refreshlist(None, db_widget, label, url, but_connect)
        change_button.connect_after('clicked', DBLogin.refreshlist_ask,
                server_widget, db_widget, label, but_connect, url, win)

        if dbname:
            i = liststore.get_iter_root()
            while i:
                if liststore.get_value(i, 0)==dbname:
                    db_widget.set_active_iter(i)
                    break
                i = liststore.iter_next(i)

        res = win.run()
        url_m = re.match('^(http[s]?://|socket://)([\w.\-]+):(\d{1,5})$',
                server_widget.get_text() or '')
        if url_m:
            CONFIG['login.server'] = url_m.group(2)
            CONFIG['login.login'] = login.get_text()
            CONFIG['login.port'] = url_m.group(3)
            CONFIG['login.protocol'] = url_m.group(1)
            CONFIG['login.db'] = db_widget.get_active_text()
            result = (login.get_text(), passwd.get_text(), url_m.group(2),
                    url_m.group(3), url_m.group(1), db_widget.get_active_text())
        else:
            parent.present()
            win.destroy()
            raise Exception('QueryCanceled')
        if res != gtk.RESPONSE_OK:
            parent.present()
            win.destroy()
            raise Exception('QueryCanceled')
        parent.present()
        win.destroy()
        return result

class DBCreate(object):
    def set_sensitive(self, sensitive):
        if sensitive:
            label = self.dialog.get_widget('db_label_info')
            label.set_text(_('Do not use special characters !'))
            self.dialog.get_widget('button_db_ok').set_sensitive(True)
        else:
            label = self.dialog.get_widget('db_label_info')
            label.set_markup('<b>' + \
                    _('Can not connect to server, please change it !') + '</b>')
            self.dialog.get_widget('button_db_ok').set_sensitive(False)
        return sensitive

    def server_change(self, widget, parent):
        url = _server_ask(self.server_widget, parent)
        try:
            if self.lang_widget and url:
                _refresh_langlist(self.lang_widget, url)
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
        protocol = CONFIG['login.protocol']
        url = '%s%s:%s' % (protocol, CONFIG['login.server'],
                CONFIG['login.port'])

        self.server_widget.set_text(url)
        liststore = gtk.ListStore(str, str)
        self.lang_widget.set_model(liststore)
        try:
            _refresh_langlist(self.lang_widget, url)
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
                        'or special characters.'), _('Bad database name !'),
                        parent=parent)

            else:
                break

        langidx = self.lang_widget.get_active_iter()
        langreal = langidx \
                and self.lang_widget.get_model().get_value(langidx, 1)
        passwd = pass_widget.get_text()
        url = self.server_widget.get_text()
        url_m = re.match('^(http[s]?://|socket://)([\w.\-]+):(\d{1,5})$',
                url or '')
        if url_m:
            CONFIG['login.server'] = url_m.group(2)
            CONFIG['login.port'] = url_m.group(3)
            CONFIG['login.protocol'] = url_m.group(1)
        parent.present()
        win.destroy()

        if res == gtk.RESPONSE_OK:
            try:
                users = rpc.session.db_exec_no_except(url, 'create', passwd, dbname,
                            langreal)
            except:
                common.warning(_('The server crashed during installation.\n' \
                        'We suggest you to drop this database.'), parent,
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
        self.secure_img.hide()

        window = self.glade.get_widget('win_main')
        window.connect("destroy", Main.sig_quit)
        window.connect("delete_event", self.sig_delete)
        self.window = window
        self.window.set_icon(TRYTON_ICON)

        self.notebook = gtk.Notebook()
        self.notebook.popup_enable()
        self.notebook.set_scrollable(True)
        self.sig_id = self.notebook.connect_after('switch-page',
                self._sig_page_changt)
        vbox = self.glade.get_widget('vbox_main')
        vbox.pack_start(self.notebook, expand=True, fill=True)

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
            'on_help_licence_activate': self.sig_licence,
            'on_about_activate': self.sig_about,
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
            'form_print': 'but_print',
            'form_print_html': 'but_print_html',
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
        }
        self.glade.get_widget('menubar_'+(CONFIG['client.toolbar'] or \
                'both')).set_active(True)
        self.sig_menubar(CONFIG['client.toolbar'] or 'both')
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

        # Adding a timer the check to requests
        gobject.timeout_add(5 * 60 * 1000, self.request_set)
        _MAIN.append(self)

    @staticmethod
    def get_main():
        return _MAIN[0]

    def shortcut_set(self):
        def _action_shortcut(widget, action):
            ctx = rpc.session.context.copy()
            Action.exec_keyword('tree_open', {'model': 'ir.ui.menu',
                'id': action, 'ids': [action],
                'window': self.window}, context=ctx)
        user = rpc.session.user
        shortcuts = rpc.session.rpc_exec_auth_try('/object', 'execute',
                'ir.ui.view_sc', 'get_sc', user, 'ir.ui.menu',
                rpc.session.context)
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
        if option == 'both':
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
        win = Preference(rpc.session.user, self.window)
        if win.run():
            rpc.session.context_reload()
        self.window.present()
        return True

    def sig_win_close(self, widget):
        self._sig_child_call(widget, 'but_close')

    def sig_request_new(self, widget):
        return Window.create(None, 'res.request', False,
                [('act_from', '=', rpc.session.user)], 'form',
                mode=['form', 'tree'], window=self.window,
                context={'active_test': False})

    def sig_request_open(self, widget):
        ids = self.request_set()[0]
        return Window.create(False, 'res.request', ids,
                [('act_to', '=', rpc.session.user), ('active', '=', True)],
                'form', mode=['tree', 'form'], window=self.window,
                context={'active_test': False})

    def sig_request_wait(self, widget):
        ids = self.request_set()[0]
        return Window.create(False, 'res.request', ids,
                [('act_from', '=', rpc.session.user),
                    ('state', '=', 'waiting'), ('active', '=', True)],
                'form', mode=['tree', 'form'], window=self.window,
                context={'active_test': False})

    def request_set(self):
        try:
            ids, ids2 = rpc.session.rpc_exec_auth_try('/object', 'execute',
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
        try:
            if not res:
                try:
                    dblogin = DBLogin()
                    res = dblogin.run(dbname, self.window)
                except Exception, exception:
                    if exception.args == ('QueryCanceled',):
                        return False
                    raise
            self.window.present()
            self.sig_logout(widget)
            log_response = rpc.session.login(*res)
            if log_response == 1:
                CONFIG.save()
                menu_id = self.sig_win_menu(quiet=False)
                if menu_id:
                    self.sig_home_new(quiet=True, except_id=menu_id)
                if res[4] == 'https://':
                    self.secure_img.show()
                else:
                    self.secure_img.hide()
                self.request_set()
            elif log_response==-1:
                common.message(_('Connection error !\n' \
                        'Unable to connect to the server !'), self.window)
            elif log_response==-2:
                common.message(_('Connection error !\n' \
                        'Bad username or password !'), self.window)
            self.shortcut_set()
        except rpc.RPCException:
            rpc.session.logout()
        self.glade.get_widget('but_menu').set_sensitive(True)
        self.glade.get_widget('user').set_sensitive(True)
        self.glade.get_widget('form').set_sensitive(True)
        self.glade.get_widget('plugins').set_sensitive(True)
        return True

    def sig_logout(self, widget):
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
        self.secure_img.hide()
        self.shortcut_unset()
        self.glade.get_widget('but_menu').set_sensitive(False)
        self.glade.get_widget('user').set_sensitive(False)
        self.glade.get_widget('form').set_sensitive(False)
        self.glade.get_widget('plugins').set_sensitive(False)
        rpc.session.logout()
        return True

    def sig_tips(self, *args):
        common.tipoftheday(self.window)

    def sig_licence(self, widget):
        dialog = glade.XML(GLADE, "win_licence", gettext.textdomain())
        dialog.signal_connect("on_but_ok_pressed",
                lambda obj: dialog.get_widget('win_licence').destroy())

        win = dialog.get_widget('win_licence')
        win.set_transient_for(self.window)
        win.show_all()

    def sig_about(self, widget):
        about = glade.XML(GLADE, "win_about", gettext.textdomain())
        buf = about.get_widget('textview2').get_buffer()
        about_txt = buf.get_text(buf.get_start_iter(),
                buf.get_end_iter())
        buf.set_text(about_txt % VERSION)
        about.signal_connect("on_but_ok_pressed",
                lambda obj: about.get_widget('win_about').destroy())

        win = about.get_widget('win_about')
        win.set_transient_for(self.window)
        win.show_all()

    def sig_shortcuts(self, widget):
        shortcuts_win = glade.XML(GLADE, 'shortcuts_dia', gettext.textdomain())
        shortcuts_win.signal_connect("on_but_ok_pressed",
                lambda obj: shortcuts_win.get_widget('shortcuts_dia').destroy())

        win = shortcuts_win.get_widget('shortcuts_dia')
        win.set_transient_for(self.window)
        win.show_all()

    def sig_win_menu(self, widget=None, quiet=True):
        for page in range(len(self.pages)):
            if self.pages[page].model == 'ir.ui.menu':
                self.notebook.set_current_page(page)
                return True
        res = self.sig_win_new(widget, menu_type='menu', quiet=quiet)
        if not res:
            return self.sig_win_new(widget, menu_type='action', quiet=quiet)
        return res

    def sig_win_new(self, widget=None, menu_type='menu', quiet=True,
            except_id=False):
        try:
            prefs = rpc.session.rpc_exec_auth('/object', 'execute',
                    'res.user', 'get_preferences', False, rpc.session.context)
        except:
            return False
        sb_id = self.sb_username.get_context_id('message')
        self.sb_username.push(sb_id, prefs['name'] or '')
        sb_id = self.sb_servername.get_context_id('message')
        data = urlparse.urlsplit(rpc.session._url)
        self.sb_servername.push(sb_id, data[0]+':'+(data[1] and '//'+data[1] \
                or data[2])+' ['+CONFIG['login.db']+']')
        if not prefs[menu_type]:
            if quiet:
                return False
            common.warning(_('You can not log into the system !\n' \
                    'Ask the administrator to verify\n' \
                    'you have an action defined for your user.'),
                    'Access Denied!', self.window)
            rpc.session.logout()
            return False
        act_id = prefs[menu_type]
        if except_id and act_id == except_id:
            return act_id
        Action.execute(act_id, {'window': self.window})
        try:
            prefs = rpc.session.rpc_exec_auth_wo('/object', 'execute',
                    'res.user', 'get_preferences', False, rpc.session.context)
            if prefs[menu_type]:
                act_id = prefs[menu_type]
        except:
            pass
        return act_id

    def sig_home_new(self, widget=None, quiet=True, except_id=False):
        return self.sig_win_new(widget, menu_type='action', quiet=quiet,
                except_id=except_id)

    def sig_plugin_execute(self, widget):
        import tryton.plugin
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
        label = gtk.Label(page.name)
        label.set_alignment(0.0, 0.5)
        hbox.pack_start(label, expand=True, fill=True)
        button = gtk.Button()
        img = gtk.Image()
        img.set_from_stock('gtk-close', gtk.ICON_SIZE_MENU)
        button.set_relief(gtk.RELIEF_NONE)
        button.add(img)
        hbox.pack_start(button, expand=False, fill=False)
        hbox.show_all()
        hbox.set_size_request(120, -1)
        button.connect('clicked', self._sig_remove_book, page.widget)
        label_menu = gtk.Label(page.name)
        label_menu.set_alignment(0.0, 0.5)
        self.notebook.append_page_menu(page.widget, hbox, label_menu)
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

    def _attachment_count(self, widget, signal_data):
        label = _('Attachment(%d)') % signal_data
        self.buttons['but_attach'].set_label(label)

    def _sig_remove_book(self, widget, page_widget):
        self._win_del(page_widget)

    def _win_del(self, page_widget=None):
        if page_widget:
            page_id = self.notebook.page_num(page_widget)
        else:
            page_id = int(self.notebook.get_current_page())
            page_widget = self.notebook.get_nth_page(page_id)
        if page_id != -1:
            self.notebook.disconnect(self.sig_id)
            page = None
            for i in range(len(self.pages)):
                if self.pages[i].widget == page_widget:
                    page = self.pages.pop(i)
                    page.signal_unconnect(self)
                    break
            self.notebook.remove_page(page_id)
            self.sig_id = self.notebook.connect_after('switch-page',
                    self._sig_page_changt)
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
            return

        rpc.session.db_exec(url, 'drop', passwd, dbname)
        common.message(_("Database dropped successfully !"),
                parent=self.window)

    def sig_db_restore(self, widget):
        filename = common.file_selection(_('Open...'), parent=self.window,
                preview=False)
        if not filename:
            return

        url, dbname, passwd = self._choose_db_ent()
        if dbname:
            file_p = file(filename, 'rb')
            data_b64 = base64.encodestring(file_p.read())
            file_p.close()
            rpc.session.db_exec(url, 'restore', passwd, dbname, data_b64)
            common.message(_("Database restored successfully !"),
                    parent=self.window)

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
                lambda a,b: _server_ask(b, win), server_widget)

        host = CONFIG['login.server']
        port = CONFIG['login.port']
        protocol = CONFIG['login.protocol']
        url = '%s%s:%s' % (protocol, host, port)
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
                rpc.session.db_exec(url, 'change_admin_password',
                        old_passwd, new_passwd)
        self.window.present()
        win.destroy()

    def sig_db_dump(self, widget):
        url, dbname, passwd = self._choose_db_select(_('Backup a database'))
        if not dbname:
            return
        filename = common.file_selection(_('Save As...'),
                action=gtk.FILE_CHOOSER_ACTION_SAVE, parent=self.window,
                preview=False)

        if filename:
            dump_b64 = rpc.session.db_exec(url, 'dump', passwd, dbname)
            dump = base64.decodestring(dump_b64)
            file_ = file(filename, 'wb')
            file_.write(dump)
            file_.close()
            common.message(_("Database backuped successfully !"),
                    parent=self.window)

    def _choose_db_select(self, title=_("Backup a database")):
        def refreshlist(widget, db_widget, label, url):
            res = _refresh_dblist(db_widget, url)
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
            url = _server_ask(server_widget, parent)
            if not url:
                return None
            refreshlist(widget, db_widget, label, url)
            return  url

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

        protocol = CONFIG['login.protocol']
        url = '%s%s:%s' % (protocol, CONFIG['login.server'],
                CONFIG['login.port'])
        server_widget.set_text(url)

        liststore = gtk.ListStore(str)
        db_widget.set_model(liststore)

        refreshlist(None, db_widget, label, url)
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

        protocol = CONFIG['login.protocol']
        url = '%s%s:%s' % (protocol, CONFIG['login.server'],
                CONFIG['login.port'])
        widget_url.set_text(url)

        change_button = dialog.get_widget('but_server_change')
        change_button.connect_after('clicked', lambda a, b: _server_ask(b, win),
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

