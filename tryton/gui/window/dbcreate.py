#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gobject
import gettext
import re
import tryton.common as common
from tryton.config import CONFIG, GLADE, TRYTON_ICON, PIXMAPS_DIR
import tryton.rpc as rpc

_ = gettext.gettext

class DBCreate(object):
    def server_connection_state(self, state):
        """Method to set the server connection information depending on the 
        connection state. If state is True, the connection string will shown.
        Otherwise the wrong connection string will be shown plus an additional
        errormessage, colored in red."""
        if state:
            self.entry_server.modify_text(gtk.STATE_INSENSITIVE, \
                gtk.gdk.color_parse("#000000"))
            #self.button_db_ok.set_sensitive(True)
            
            #self.button_db_ok.set_flags(gtk.RECEIVES_DEFAULT)
        else:
            self.entry_server.set_editable(False)
            self.entry_server.set_sensitive(False)
            self.entry_server.set_text(self.entry_server.get_text() + " " \
                + _('Can not connect to server!'))
            self.entry_server.modify_text(gtk.STATE_INSENSITIVE, \
                gtk.gdk.color_parse("#ff0000"))
            self.button_db_ok.set_sensitive(False)
            #self.button_db_ok.unset_flags(gtk.CAN_DEFAULT)
            #self.button_db_ok.unset_flags(gtk.HAS_DEFAULT)
        return sensitive

    def server_change(self, widget, parent):
        """This method checks the server connection via host and port. If the 
        connection is successfull, it query the language list and pass true
        state to the GUI. Otherwise it pass false state to the GUI."""
        res = common.request_server(self.entry_server, parent)
        if not res:
            return False
        host, port = res
        try:
            if self.combo_default_lang and host and port:
                common.refresh_langlist(self.combo_default_lang, host, port)
            self.server_connection_state(True)
        except:
            self.server_connection_state(False)
            return False
        return True

    def event_passwd_clear(self, widget, event, data=None):
        """This event method clear the text in a widget if CTRL-u 
        is pressed."""
        if  event.keyval == gtk.keysyms.u:
            widget.set_text("")

    def event_show_button_create(self, widget, event, data=None):
        """This event method decide by rules if the Create button will be 
        sensitive or insensitive. The general rule is, all given fields 
        must be filled, then the Create button is set to sensitive. This
        event method doesn't check the valid of single entrys."""
        if  self.entry_server.get_text() !=  _("") \
            and self.entry_password_new.get_text() != "" \
            and self.entry_new_db.get_text() != "" \
            and self.combo_default_lang.get_active() != -1 \
            and self.ent_password_admin.get_text() != "" \
            and self.ent_re_password_admin.get_text() != "":
            self.button_db_ok.set_sensitive(True)

            self.button_db_ok.grab_default()
        else:
            self.button_db_ok.set_sensitive(False)
            self.button_db_ok.unset_flags(gtk.CAN_DEFAULT)
            self.button_db_ok.unset_flags(gtk.HAS_DEFAULT)

    # Some Postgres restrictions for the DB_Name


    def entry_insert_text(self, entry, new_text, new_text_length, position):
        """This event method checks each text input for the PostgreSQL
        database name. It allows the following rules: 
        - Allowed characters are alpha-nummeric [A-Za-z0-9] and underscore (_)
        - First character must be a letter"""
        def move_cursor(entry, pos):
            entry.set_position(pos)
            return False

        if (new_text.isalnum() or new_text == '_' ):
            _hid = entry.get_data('handlerid')
            entry.handler_block(_hid)
            _pos = entry.get_position()
            if _pos == 0 and not new_text.isalpha():
                new_text = ""
            _pos = entry.insert_text(new_text, _pos)
            entry.handler_unblock(_hid)
            gobject.idle_add(move_cursor, entry, _pos)
        entry.stop_emission("insert-text")


    def __init__(self, sig_login):
        """This method defines the complete GUI."""
        self.dialog = gtk.Dialog(
            title =  _("Create new database"),
            parent = None,
            flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT
            | gtk.WIN_POS_CENTER_ON_PARENT,
        )
        self.dialog.connect("key-press-event", self.event_show_button_create)
        self.dialog.connect("focus-in-event", self.event_show_button_create)
        self.dialog.connect("focus-out-event", self.event_show_button_create)

        tooltips = gtk.Tooltips()
        
        self.dialog.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.dialog.set_has_separator(False)

        dialog_vbox = gtk.VBox()

        table_main = gtk.Table(9, 3, False)
        table_main.set_border_width(10)
        table_main.set_row_spacings(3)
        table_main.set_col_spacings(3)
        dialog_vbox.pack_start(table_main)

        label_credentials = gtk.Label()
        label_credentials.set_markup("<b>" + _("Tryton Administration " \
            "Credentials") + "</b>")
        label_credentials.set_justify(gtk.JUSTIFY_LEFT)
        label_credentials.set_alignment(0, 1)
        label_credentials.set_padding( 9, 5)
        table_main.attach(label_credentials, 0, 3, 0, 1, xoptions=gtk.EXPAND \
            | gtk.FILL)

        label_server = gtk.Label(_("Server:"))
        label_server.set_alignment(1, 0.5)
        label_server.set_padding(3, 3)
        table_main.attach(label_server, 0, 1, 1, 2, xoptions=gtk.FILL)

        self.entry_server = gtk.Entry()
        self.entry_server.set_sensitive(False)

        self.entry_server.unset_flags(gtk.CAN_FOCUS)
        self.entry_server.set_editable(False)
        self.entry_server.set_text(_("http://localhost:8070"))
        self.entry_server.set_width_chars(16)
        table_main.attach(self.entry_server, 1, 2, 1, 2)
        tooltips.set_tip(self.entry_server, _("This is the URL of the Tryton " \
            "server. Use server 'localhost' and port '8070' if the server " \
            "is installed on this " \
            "computer. Click on 'Change' to change the address."), None)

        self.but_server_new = gtk.Button(_("C_hange"), stock=None, 
             use_underline=True)
        img_but_server_new = gtk.Image()
        img_but_server_new.set_from_stock('tryton-preferences-system', \
            gtk.ICON_SIZE_BUTTON)
        self.but_server_new.set_image(img_but_server_new)
        table_main.attach(self.but_server_new, 2, 3, 1, 2, xoptions=gtk.FILL)
        tooltips.set_tip(self.but_server_new, _("Setup the Tryton server " \
            "connection..."), None)

        label_server_password = gtk.Label(_("Server password:"))
        label_server_password.set_justify(gtk.JUSTIFY_RIGHT)
        label_server_password.set_alignment(1, 0.5)
        label_server_password.set_padding( 3, 3)
        table_main.attach(label_server_password, 0, 1, 2, 3)

        self.entry_password_new = gtk.Entry()
        self.entry_password_new.set_max_length(16)
        self.entry_password_new.set_visibility(False)
        self.entry_password_new.set_activates_default(True)

        self.entry_password_new.set_width_chars(16)
        table_main.attach(self.entry_password_new, 1, 3, 2, 3, yoptions=False,
            xoptions=gtk.EXPAND | gtk.FILL)
        tooltips.set_tip(self.entry_password_new, _("This is the " \
            "password for Tryton administration. It doesn't belong to a " \
            "Tryton user. This password is usually defined in the trytond" \
            "configuration."), None)
        self.entry_password_new.connect("key-press-event", \
            self.event_passwd_clear)

        hseparator = gtk.HSeparator()
        table_main.attach(hseparator, 0, 3, 3, 4, yoptions=False,
            xoptions=gtk.EXPAND | gtk.FILL)

        label_new_db = gtk.Label()
        label_new_db.set_markup("<b>" + _("New Database Settings") \
            + "</b>")
        label_new_db.set_justify(gtk.JUSTIFY_LEFT)
        label_new_db.set_alignment(0, 1)
        label_new_db.set_padding( 9, 5)
        table_main.attach(label_new_db, 0, 3, 4, 5, xoptions=gtk.EXPAND \
            | gtk.FILL)

        label_new_db_name = gtk.Label(_("Name:"))
        label_new_db_name.set_justify(gtk.JUSTIFY_RIGHT)
        label_new_db_name.set_padding( 3, 3)
        label_new_db_name.set_alignment(1, 0.5)
        table_main.attach(label_new_db_name, 0, 1, 5, 6, \
            xoptions=gtk.FILL)

        self.entry_new_db = gtk.Entry()
        self.entry_new_db.set_max_length(63)
        self.entry_new_db.set_width_chars(63)
        table_main.attach(self.entry_new_db, 1, 3, 5, 6, yoptions=False,
                    xoptions=gtk.EXPAND | gtk.FILL)
        tooltips.set_tip(self.entry_new_db, _("Choose the name of the new " \
            "database.\n" \
            "Allowed characters are alphanumerical or _ (underscore)\n" \
            "You need to avoid all accents, space or special characters! " \
            "Example: tryton"), None)
        handlerid = self.entry_new_db.connect("insert-text", \
            self.entry_insert_text)
        self.entry_new_db.set_data('handlerid', handlerid)

        label_default_lang = gtk.Label(_("Default language:"))
        label_default_lang.set_justify(gtk.JUSTIFY_RIGHT)
        label_default_lang.set_alignment(1, 0.5)
        label_default_lang.set_padding( 3, 3)
        table_main.attach(label_default_lang, 0, 1, 6, 7, xoptions=gtk.FILL)
        eventbox_default_lang = gtk.EventBox()

        self.combo_default_lang = gtk.combo_box_new_text()
        eventbox_default_lang.add(self.combo_default_lang)
        table_main.attach(eventbox_default_lang, 1, 3, 6, 7, \
            xoptions=gtk.EXPAND | gtk.FILL)
        tooltips.set_tip(eventbox_default_lang, _("Choose the default " \
            "language that will be installed for this database. You will " \
            "be able to install new languages after installation through " \
            "the administration menu."), None)

        label_admin_password = gtk.Label(_("Admin password:"))
        label_admin_password.set_justify(gtk.JUSTIFY_RIGHT)
        label_admin_password.set_padding( 3, 3)
        label_admin_password.set_alignment(1, 0.5)
        table_main.attach(label_admin_password, 0, 1, 7, 8, xoptions=gtk.FILL)

        self.ent_password_admin = gtk.Entry()
        self.ent_password_admin.set_visibility(False)
        tooltips.set_tip(self.ent_password_admin, _("Choose a password for " \
            "the admin user of the new database. With these credentials you " \
            "are later able to login into the database:\n" \
            "User name: admin\n" \
            "Password: <The password you set here>"), None)
        table_main.attach(self.ent_password_admin, 1, 3, 7, 8, \
            xoptions=gtk.EXPAND | gtk.FILL)
        self.ent_password_admin.connect("key-press-event", \
            self.event_passwd_clear)

        label_admin_re_password = gtk.Label(_("Confirm admin password:"))
        label_admin_re_password.set_justify(gtk.JUSTIFY_RIGHT)
        label_admin_re_password.set_padding( 3, 3)
        label_admin_re_password.set_alignment(1, 0.5)
        table_main.attach(label_admin_re_password, 0, 1, 8, 9, \
            xoptions=gtk.FILL)

        self.ent_re_password_admin = gtk.Entry()
        self.ent_re_password_admin.set_visibility(False)
        tooltips.set_tip(self.ent_re_password_admin, _("Type the Admin " \
            "password again"), None)
        table_main.attach(self.ent_re_password_admin, 1, 3, 8, 9, \
            xoptions=gtk.EXPAND | gtk.FILL)
        self.ent_re_password_admin.connect("key-press-event", \
            self.event_passwd_clear)

        self.dialog.add_button("gtk-cancel", \
            gtk.RESPONSE_CANCEL)

        self.button_db_ok = gtk.Button(_('C_reate'))
        self.button_db_ok.set_sensitive(False)
        img_connect = gtk.Image()
        img_connect.set_from_stock('tryton-new', gtk.ICON_SIZE_BUTTON)
        self.button_db_ok.set_image(img_connect)
        self.button_db_ok.set_flags(gtk.CAN_DEFAULT)
        tooltips.set_tip(self.button_db_ok, _('Create the new Tryton ' \
            'database.'))
        self.dialog.add_action_widget(self.button_db_ok, gtk.RESPONSE_OK)
        self.dialog.set_default_response(gtk.RESPONSE_OK)

        self.entry_password_new.grab_focus()
        self.dialog.vbox.pack_start(dialog_vbox)

        self.sig_login = sig_login

    def run(self, parent):
        self.dialog.set_default_response(gtk.RESPONSE_OK)
        self.dialog.set_transient_for(parent)
        self.dialog.show_all()
        
        pass_widget = self.entry_password_new
        change_button = self.but_server_new
        admin_passwd = self.ent_password_admin
        admin_passwd2 = self.ent_re_password_admin

        change_button.connect_after('clicked', self.server_change, self.dialog)
        host = CONFIG['login.server']
        port = int(CONFIG['login.port'])
        url = '%s:%d' % (host, port)
        self.entry_server.set_text(url)

        liststore = gtk.ListStore(str, str)
        self.combo_default_lang.set_model(liststore)
        try:
            common.refresh_langlist(self.combo_default_lang, host, port)
        except:
            self.button_db_ok.set_sensitive(False)

        while True:
            res = self.dialog.run()
            dbname = self.entry_new_db.get_text()
            url = self.entry_server.get_text()
            url_m = re.match('^([\w.\-]+):(\d{1,5})', \
                url or '')

            langidx = self.combo_default_lang.get_active_iter()
            langreal = langidx \
                and self.combo_default_lang.get_model().get_value(langidx, 1)
            passwd = pass_widget.get_text()
            if res == gtk.RESPONSE_OK:
                if (not dbname) \
                    or (not re.match('^[a-zA-Z][a-zA-Z0-9_]+$', dbname)):
                    common.warning(_('The database name is restricted to' \
                        'alpha-nummerical characters and "_" (underscore).' \
                        'It must begin with a letter and max. sized to 63 ' \
                        'characters at all.\n' \
                        'Try to avoid all accents, space ' \
                        'and any other special characters.'), parent, \
                        _('Wrong characters in database name!'))
                    continue
                elif admin_passwd.get_text() != admin_passwd2.get_text():
                    common.warning(_("The new admin password " \
                        "doesn't match to the retyped password.\n" \
                        "Try to type the same passwords in the " \
                        "admin password and the confirm admin password " \
                        "fields again."), parent, \
                        _("Passwords doesn't match!"))
                    continue
                elif not admin_passwd.get_text():
                    common.warning(_("Admin password and confirmation are " \
                        "required to create a new Tryton database\n"), \
                        parent, _('Missing admin password!'))
                    continue
                elif url_m.group(1) \
                    and int(url_m.group(2)) \
                    and dbname \
                    and langreal \
                    and passwd \
                    and admin_passwd.get_text():
                    try:
                        if rpc.db_exec( url_m.group(1), int(url_m.group(2)), \
                                'db_exist', dbname):
                            common.warning(_("Database with the same name " \
                                "already exists.\n"
                                "Try another database name."), parent, \
                                _("Databasename already exist!"))
                            self.entry_new_db.set_text("")
                            self.entry_new_db.grab_focus()
                            continue
                        else: # Everything runs fine, break the block here
                            if url_m:
                                CONFIG['login.server'] = host = url_m.group(1)
                                CONFIG['login.port'] = port = url_m.group(2)
                            rpc.db_exec(host, int(port), 'create', passwd, \
                                dbname, langreal, admin_passwd.get_text())
                            from tryton.gui.main import Main
                            Main.get_main().refresh_ssl()
                            common.message(_('You can now connect to the ' \
                                'new database, with the following login:\n' 
                                'User name: admin\n' \
                                'Password:<The password you set before>'), 
                                parent, _("Database created successful!"))
                            self.sig_login(dbname=dbname)
                            return True
                            break
                    except Exception, exception:
                        if str(exception[0]) == "AccessDenied":
                            common.warning(_("Sorry, the Tryton server "
                                "password seems wrong. Please type again.") \
                                , parent, _("Access denied!"))
                            self.entry_password_new.set_text("")
                            self.entry_password_new.grab_focus()
                            continue
                        else: # Unclassified error
                            common.warning(_("Can't request the Tryton " \ 
                                "server, caused by an unknown reason.\n" \
                                "If there is a database created, it could " \
                                "be broken. Please drop this database!" \
                                "Please check the error message for " \ 
                                "possible informations.\n" \
                                "Error message:\n") + str(exception[0]), \
                                parent, _("Error requesting Tryton server!"))
                        parent.present()
                        self.dialog.destroy()
                        rpc.logout()
                        from tryton.gui.main import Main
                        Main.get_main().refresh_ssl()
                    break
            break

        parent.present()
        self.dialog.destroy()




