#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import gtk
import gettext
from tryton.common import RPCExecute, RPCException
from tryton.gui.window.view_form.screen import Screen
from tryton.action import Action
from tryton.gui.window import Window
from tryton.gui.window.attachment import Attachment

_ = gettext.gettext



def populate(menu, model, record_id, title=''):
    '''
    Fill menu with the actions of model for the record id.
    If title is filled, the actions will be put in a submenu.
    '''
    if record_id is None or record_id < 0:
        return
    try:
        toolbar = RPCExecute('model', model, 'view_toolbar_get')
    except RPCException:
        return

    def activate(menuitem, action, atype):
        screen = Screen(model)
        screen.load([record_id])
        action = Action.evaluate(action, atype, screen.current_record)
        data = {
            'model': model,
            'id': record_id,
            'ids': [record_id],
            }
        event = gtk.get_current_event()
        allow_similar = False
        if (event.state & gtk.gdk.CONTROL_MASK
                or event.state & gtk.gdk.MOD1_MASK):
            allow_similar = True
        with Window(hide_current=True, allow_similar=allow_similar):
            Action._exec_action(action, data, {})

    def attachment(menuitem):
        Attachment(model, record_id, None)

    if title:
        if len(menu):
            menu.append(gtk.SeparatorMenuItem())
        title_item = gtk.MenuItem(title)
        menu.append(title_item)
        submenu = gtk.Menu()
        title_item.set_submenu(submenu)
        action_menu = submenu
    else:
        action_menu = menu

    if len(action_menu):
        action_menu.append(gtk.SeparatorMenuItem())
    attachment_item = gtk.ImageMenuItem('tryton-attachment')
    attachment_item.set_label(_('Attachments...'))
    action_menu.append(attachment_item)
    attachment_item.connect('activate', attachment)

    for atype, icon, label, flavor in (
            ('action', 'tryton-executable', _('Actions...'), None),
            ('relate', 'tryton-go-jump', _('Relate...'), None),
            ('print', 'tryton-print-open', _('Report...'), 'open'),
            ('print', 'tryton-print-email', _('E-Mail...'), 'email'),
            ('print', 'tryton-print', _('Print...'), 'print'),
            ):
        if len(action_menu):
            action_menu.append(gtk.SeparatorMenuItem())
        title_item = gtk.ImageMenuItem(icon)
        title_item.set_label(label)
        action_menu.append(title_item)
        if not toolbar[atype]:
            title_item.set_sensitive(False)
            continue
        submenu = gtk.Menu()
        title_item.set_submenu(submenu)
        for action in toolbar[atype]:
            action = action.copy()
            item = gtk.MenuItem(action['name'])
            submenu.append(item)
            if flavor == 'print':
                action['direct_print'] = True
            elif flavor == 'email':
                action['email_print'] = True
            item.connect('activate', activate, action, atype)

    menu.show_all()
