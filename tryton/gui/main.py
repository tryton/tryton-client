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
from tryton.action import Action
from tryton.gui.window import Window
from tryton.gui.window.preference import Preference
from tryton.gui.window import FilesActions
from tryton.gui.window.dblogin import DBLogin
from tryton.gui.window.dbcreate import DBCreate
from tryton.gui.window.tips import Tips
from tryton.gui.window.credits import Credits
import re
import base64
import tryton.translate as translate
import tryton.plugin
import pango

_ = gettext.gettext


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
        self.previous_pages = {}
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
            'on_opt_spellcheck_activate': (fnc_menuitem, 'client.spellcheck',
                'opt_spellcheck'),
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

        if os.name in ('nt', 'mac') or os.uname()[0] == 'Darwin':
            # Disable actions, on win32 we use os.startfile
            # and on mac we use /usr/bin/open
            self.glade.get_widget('actions').set_sensitive(False)

        # Adding a timer the check to requests
        gobject.timeout_add(5 * 60 * 1000, self.request_set)
        _MAIN.append(self)

    @staticmethod
    def get_main():
        return _MAIN[0]

    def shortcut_set(self, shortcuts=None):
        def _action_shortcut(widget, action):
            Action.exec_keyword('tree_open', self.window, {
                'model': 'ir.ui.menu',
                'id': action,
                'ids': [action],
                })
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
        ctx = {}
        ctx.update(rpc.CONTEXT)
        ctx['active_test'] = False
        return Window.create(None, 'res.request', False,
                [('act_from', '=', rpc._USER)], 'form',
                mode=['form', 'tree'], window=self.window,
                context=ctx)

    def sig_request_open(self, widget):
        ctx = {}
        ctx.update(rpc.CONTEXT)
        ctx['active_test'] = False
        ids = self.request_set()[0]
        return Window.create(False, 'res.request', ids,
                [('act_to', '=', rpc._USER), ('active', '=', True)],
                'form', mode=['tree', 'form'], window=self.window,
                context=ctx)

    def sig_request_wait(self, widget):
        ctx = {}
        ctx.update(rpc.CONTEXT)
        ctx['active_test'] = False
        ids = self.request_set()[0]
        return Window.create(False, 'res.request', ids,
                [('act_from', '=', rpc._USER),
                    ('state', '=', 'waiting'), ('active', '=', True)],
                'form', mode=['tree', 'form'], window=self.window,
                context=ctx)

    def request_set(self):
        try:
            ids, ids2 = rpc.execute('object', 'execute',
                    'res.request', 'request_get')
            if len(ids):
                if len(ids) == 1:
                    message = _('%s request') % len(ids)
                else:
                    message = _('%s requests') % len(ids)
            else:
                message = _('No request')
            if len(ids2):
                if len(ids2) == 1:
                    message += _(' - %s request sended') % len(ids2)
                else:
                    message += _(' - %s requests sended') % len(ids2)
            sb_id = self.sb_requests.get_context_id('message')
            self.sb_requests.push(sb_id, message)
            return (ids, ids2)
        except:
            return ([], [])

    def sig_login(self, widget=None, dbname=False, res=None):
        if not res:
            try:
                dblogin = DBLogin(self.window)
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
                translate.setlang(prefs['language'], prefs.get('locale'))
                CONFIG['client.lang'] = prefs['language']
            CONFIG.save()
        elif log_response == -1:
            common.message(_('Connection error!\n' \
                    'Unable to connect to the server!'), self.window)
        elif log_response == -2:
            common.message(_('Connection error!\n' \
                    'Bad username or password!'), self.window)
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
        self.sb_username.push(sb_id, _('Not logged!'))
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
            self.tooltips.set_tip(self.secure_img, _('SSL connection') + \
                    '\n' + str(rpc._SOCK.ssl_sock.server()))
            self.secure_img.show()
        else:
            self.tooltips.set_tip(self.secure_img, '')
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
            common.warning(_('You can not log into the system!\n' \
                    'Verify if you have an menu defined on your user.'),
                    'Access Denied!', self.window)
            rpc.logout()
            self.refresh_ssl()
            return False
        act_id = prefs[menu_type]
        if except_id and act_id == except_id:
            return act_id
        Action.execute(act_id, {}, self.window)
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
        if common.sur(_("Do you really want to quit?"), parent=self.window):
            if not self.sig_logout(widget):
                return False
            CONFIG.save()
            gtk.main_quit()

    def sig_delete(self, widget, event):
        if common.sur(_("Do you really want to quit?"), parent=self.window):
            if not self.sig_logout(widget):
                return True
            return False
        return True

    def win_add(self, page):
        previous_page_id = self.notebook.get_current_page()
        previous_widget = self.notebook.get_nth_page(previous_page_id)
        self.previous_pages[page] = previous_widget
        self.pages.append(page)
        hbox = gtk.HBox()
        name = page.name
        label = gtk.Label(name)
        self.tooltips.set_tip(label, page.name)
        self.tooltips.enable()
        label.set_alignment(0.0, 0.5)
        hbox.pack_start(label, expand=True, fill=True)
        layout = label.get_layout()
        w, h = layout.get_size()
        icon_w, icon_h = gtk.icon_size_lookup(gtk.ICON_SIZE_SMALL_TOOLBAR)
        if (w / pango.SCALE) > 120 - icon_w:
            label2 = gtk.Label('...')
            self.tooltips.set_tip(label2, page.name)
            hbox.pack_start(label2, expand=False, fill=False)
        eb = gtk.EventBox()
        self.tooltips.set_tip(eb, _('Close Tab'))
        eb.set_events(gtk.gdk.BUTTON_PRESS)
        eb.set_border_width(1)

        img = gtk.Image()
        img.set_from_stock('tryton-close', gtk.ICON_SIZE_SMALL_TOOLBAR)
        eb.add(img)

        def enter(widget, event, img):
            img.set_from_stock('tryton-close-hi', gtk.ICON_SIZE_SMALL_TOOLBAR)

        def leave(widget, event, img):
            img.set_from_stock('tryton-close', gtk.ICON_SIZE_SMALL_TOOLBAR)

        eb.connect('button_release_event', self._sig_remove_book, page.widget)
        eb.connect('enter_notify_event', enter, img)
        eb.connect('leave_notify_event', leave, img)

        hbox.pack_start(eb, expand=False, fill=False)
        hbox.show_all()
        hbox.set_size_request(120, -1)
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

    def _sig_remove_book(self, widget, event, page_widget):
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

            next_page_id = -1
            to_pop = []
            for i in self.previous_pages:
                if self.previous_pages[i] == page_widget:
                    to_pop.append(i)
                if i.widget == page_widget:
                    if self.previous_pages[i]:
                        next_page_id = self.notebook.page_num(
                                self.previous_pages[i])
                    to_pop.append(i)
            to_pop.reverse()
            for i in to_pop:
                self.previous_pages.pop(i)

            if hasattr(page, 'destroy'):
                page.destroy()
            del page

            self.notebook.set_current_page(next_page_id)
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
        title = 'Tryton'
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
                lambda a,b: common.request_server(b, win), server_widget)

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
                        "new password, operation cancelled!"), win,
                        _("Validation Error."))
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
            common.message(_("Database backuped successfully!"),
                    parent=self.window)
        else:
            rpc.logout()
            Main.get_main().refresh_ssl()

    def _choose_db_select(self, title=_("Backup a database")):
        def refreshlist(widget, db_widget, label, host, port):
            res = common.refresh_dblist(db_widget, host, port)
            if res is None or res == -1:
                if res is None:
                    label.set_label('<b>' + _('Could not connect to server!') +\
                            '</b>')
                else:
                    label.set_label('<b>' + \
                            _('Incompatible version of the server!') + '</b>')
                db_widget.hide()
                label.show()
            elif res == 0:
                label.set_label('<b>' + \
                        _('No database found, you must create one!') + '</b>')
                db_widget.hide()
                label.show()
            else:
                label.hide()
                db_widget.show()
            return res

        def refreshlist_ask(widget, server_widget, db_widget, label,
                parent=None):
            res = common.request_server(server_widget, parent)
            if not res:
                return None
            host, port = res
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
        change_button.connect_after('clicked',
                lambda a, b: common.request_server(b, win), widget_url)

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

