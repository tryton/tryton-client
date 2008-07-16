#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
from gtk import glade
import gettext
import re
import tryton.common as common
from tryton.config import CONFIG, GLADE, TRYTON_ICON, PIXMAPS_DIR
import tryton.rpc as rpc

_ = gettext.gettext


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
        host, port = common.request_server(self.server_widget, parent)
        try:
            if self.lang_widget and host and port:
                common.refresh_langlist(self.lang_widget, host, port)
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
            common.refresh_langlist(self.lang_widget, host, port)
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
                from tryton.gui.main import Main
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
            from tryton.gui.main import Main
            Main.get_main().refresh_ssl()

