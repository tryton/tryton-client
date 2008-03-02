import gtk
from gtk import glade
import gobject
import gettext
import os
import logging
from tryton.config import CONFIG
from tryton.config import GLADE, TRYTON_ICON, PIXMAPS_DIR, DATA_DIR
import time
import sys

_ = gettext.gettext


def selection(title, values, parent, alwaysask=False):
    if not values or len(values)==0:
        return None
    elif len(values)==1 and (not alwaysask):
        key = values.keys()[0]
        return (key, values[key])

    xml = glade.XML(GLADE, "win_selection",
            gettext.textdomain())
    win = xml.get_widget('win_selection')
    win.set_icon(TRYTON_ICON)
    win.set_transient_for(parent)

    label = xml.get_widget('win_sel_title')
    if title:
        label.set_text(title)

    sel_tree = xml.get_widget('win_sel_tree')
    sel_tree.get_selection().set_mode('single')
    cell = gtk.CellRendererText()
    column = gtk.TreeViewColumn("Widget", cell, text=0)
    sel_tree.append_column(column)
    sel_tree.set_search_column(0)
    model = gtk.ListStore(gobject.TYPE_STRING)
    keys = values.keys()
    keys.sort()
    for val in keys:
        model.append([val])

    sel_tree.set_model(model)
    sel_tree.connect('row-activated',
            lambda x, y, z: win.response(gtk.RESPONSE_OK) or True)

    response = win.run()
    res = None
    if response == gtk.RESPONSE_OK:
        sel = sel_tree.get_selection().get_selected()
        if sel:
            (model, i) = sel
            if i:
                value = model.get_value(i, 0)
                res = (res, values[value])
    parent.present()
    win.destroy()
    return res

def tipoftheday(parent=None):
    class Tip(object):
        def __init__(self, parent=None):
            try:
                self.number = int(CONFIG['tip.position'])
            except:
                self.number = 0
                log = logging.getLogger('common.message')
                log.error(_('Invalid value for option tip.position!' \
                        'See ~/.trytonrc!'))
            winglade = glade.XML(GLADE, "win_tips",
                    gettext.textdomain())
            self.win = winglade.get_widget('win_tips')
            if parent:
                self.win.set_transient_for(parent)
            self.parent = parent
            self.win.show_all()
            self.label = winglade.get_widget('tip_label')
            self.check = winglade.get_widget('tip_checkbutton')
            img = winglade.get_widget('tip_image')
            img.set_from_file(os.path.join(PIXMAPS_DIR, 'tryton.png'))
            signals = {
                'on_but_next_activate': self.tip_next,
                'on_but_previous_activate': self.tip_previous,
                'on_but_close_activate': self.tip_close,
            }
            for signal in signals:
                winglade.signal_connect(signal, signals[signal])
            self.tip_set()
            self.win.show_all()

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
            tip = tips[self.number % len(tips)]
            del tips
            self.label.set_text(tip)
            self.label.set_use_markup( True )

        def tip_next(self, *args):
            self.number += 1
            self.tip_set()

        def tip_previous(self, *args):
            if self.number > 0:
                self.number -= 1
            self.tip_set()

        def tip_close(self, *args):
            check = self.check.get_active()
            CONFIG['tip.autostart'] = check
            CONFIG['tip.position'] = self.number+1
            CONFIG.save()
            parent.present()
            self.win.destroy()
    Tip(parent)
    return True

def file_selection(title, filename='', parent=None,
        action=gtk.FILE_CHOOSER_ACTION_OPEN, preview=True, multi=False,
        filters=None):
    if action == gtk.FILE_CHOOSER_ACTION_OPEN:
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_OPEN,gtk.RESPONSE_OK)
    else:
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_SAVE, gtk.RESPONSE_OK)
    win = gtk.FileChooserDialog(title, None, action, buttons)
    win.set_transient_for(parent)
    win.set_icon(TRYTON_ICON)
    win.set_current_folder(CONFIG['client.default_path'])
    if filename:
        win.set_current_name(filename)
    win.set_select_multiple(multi)
    win.set_default_response(gtk.RESPONSE_OK)
    if filters is not None:
        for filt in filters:
            win.add_filter(filt)

    def update_preview_cb(win, img):
        filename = win.get_preview_filename()
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, 128, 128)
            img.set_from_pixbuf(pixbuf)
            have_preview = True
        except:
            have_preview = False
        win.set_preview_widget_active(have_preview)
        return

    if preview:
        img_preview = gtk.Image()
        win.set_preview_widget(img_preview)
        win.connect('update-preview', update_preview_cb, img_preview)

    button = win.run()
    if button != gtk.RESPONSE_OK:
        win.destroy()
        return False
    if not multi:
        filepath = win.get_filename()
        if filepath:
            filepath = filepath.decode('utf-8')
            try:
                CONFIG['client.default_path'] = \
                        os.path.dirname(filepath)
            except:
                pass
        parent.present()
        win.destroy()
        return filepath
    else:
        filenames = win.get_filenames()
        if filenames:
            filenames = [x.decode('utf-8') for x in filenames]
            try:
                CONFIG['client.default_path'] = \
                        os.path.dirname(filenames[0])
            except:
                pass
        parent.present()
        win.destroy()
        return filenames

def file_open(filename, type, parent):
    cmd = ''
    if type in CONFIG['client.actions']:
        cmd = CONFIG['client.actions'][type]
    if not cmd:
        #TODO add dialog box
        pass
    if not cmd:
        save_name = file_selection(_('Save As...'), parent=parent,
                action=gtk.FILE_CHOOSER_ACTION_SAVE)
        if save_name:
            file_p = file(filename, 'rb')
            save_p = file(save_name, 'wb+')
            save_p.write(file_p.read())
            save_p.close()
            file_p.close()
        return
    cmd = cmd % filename
    pid = os.fork()
    if not pid:
        pid = os.fork()
        if not pid:
            prog, args = cmd.split(' ', 1)
            args = [os.path.basename(prog)] + args.split(' ')
            os.execv(prog, args)
        time.sleep(0.1)
        sys.exit(0)
    os.waitpid(pid, 0)

def error(title, msg, parent, details=''):
    log = logging.getLogger('common.message')
    log.error('MSG %s: %s' % (str(msg), details))

    xml = glade.XML(GLADE, "win_error", gettext.textdomain())
    win = xml.get_widget('win_error')
    win.set_transient_for(parent)
    win.set_icon(TRYTON_ICON)
    xml.get_widget('error_title').set_text(str(title))
    xml.get_widget('error_info').set_text(str(msg))
    buf = gtk.TextBuffer()
    buf.set_text(unicode(details,'latin1').encode('utf-8'))
    xml.get_widget('error_details').set_buffer(buf)

    xml.signal_connect('on_closebutton_clicked', lambda x : win.destroy())

    win.run()
    parent.present()
    win.destroy()
    return True

def message(msg, parent, msg_type=gtk.MESSAGE_INFO):
    dialog = gtk.MessageDialog(parent,
      gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
      msg_type, gtk.BUTTONS_OK,
      msg)
    dialog.set_icon(TRYTON_ICON)
    dialog.run()
    parent.present()
    dialog.destroy()
    return True

def to_xml(string):
    return string.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def message_box(title, msg, parent):
    dia = glade.XML(GLADE, "dia_message_box",
            gettext.textdomain())
    win = dia.get_widget('dia_message_box')
    label = dia.get_widget('msg_title')
    label.set_text(title)

    buf = dia.get_widget('msg_tv').get_buffer()
    iter_start = buf.get_start_iter()
    buf.insert(iter_start, msg)

    win.set_transient_for(parent)
    win.set_icon(TRYTON_ICON)

    win.run()
    parent.present()
    win.destroy()
    return True


def warning(msg, parent, title=''):
    dialog = gtk.MessageDialog(parent, gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_WARNING, gtk.BUTTONS_OK)
    dialog.set_icon(TRYTON_ICON)
    dialog.set_markup('<b>%s</b>\n\n%s' % (to_xml(title), to_xml(msg)))
    dialog.show_all()
    dialog.run()
    parent.present()
    dialog.destroy()
    return True

def sur(msg, parent):
    xml = glade.XML(GLADE, "win_sur", gettext.textdomain())
    win = xml.get_widget('win_sur')
    win.set_transient_for(parent)
    win.show_all()
    label = xml.get_widget('lab_question')
    label.set_text(msg)

    win.set_transient_for(parent)
    win.set_icon(TRYTON_ICON)

    response = win.run()
    parent.present()
    win.destroy()
    return response == gtk.RESPONSE_OK

def sur_3b(msg, parent):
    xml = glade.XML(GLADE, "win_quest_3b",
            gettext.textdomain())
    win = xml.get_widget('win_quest_3b')
    label = xml.get_widget('label')
    label.set_text(msg)

    win.set_transient_for(parent)
    win.set_icon(TRYTON_ICON)

    response = win.run()
    parent.present()
    win.destroy()
    if response == gtk.RESPONSE_YES:
        return 'ok'
    elif response == gtk.RESPONSE_NO:
        return 'ko'
    elif response == gtk.RESPONSE_CANCEL:
        return 'cancel'
    else:
        return 'cancel'

def ask(question, parent, visibility=True):
    win = gtk.Dialog(_('Tryton'), parent,
            gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))
    win.set_icon(TRYTON_ICON)
    win.set_default_response(gtk.RESPONSE_OK)

    hbox = gtk.HBox()
    image = gtk.Image()
    image.set_from_stock(gtk.STOCK_DIALOG_QUESTION,
            gtk.ICON_SIZE_DIALOG)
    hbox.pack_start(image)
    vbox = gtk.VBox()
    vbox.pack_start(gtk.Label(question))
    entry = gtk.Entry()
    entry.set_activates_default(True)
    entry.set_visibility(visibility)
    vbox.pack_start(entry)
    hbox.pack_start(vbox)
    win.vbox.pack_start(hbox)
    win.show_all()

    response = win.run()
    parent.present()
    win.destroy()
    if response == gtk.RESPONSE_OK:
        return entry.get_text()
    else:
        return None

def node_attributes(node):
    result = {}
    attrs = node.attributes
    if attrs is None:
        return {}
    for i in range(attrs.length):
        result[str(attrs.item(i).localName)] = str(attrs.item(i).nodeValue)
        if attrs.item(i).localName == "digits" \
                and isinstance(attrs.item(i).nodeValue, (str, unicode)):
            result[attrs.item(i).localName] = eval(attrs.item(i).nodeValue)
    return result


COLORS = {
    'invalid':'#ff6969',
    'readonly':'#eeebe7',
    'required':'#d2d2ff',
    'normal':'white'
}

DT_FORMAT = '%Y-%m-%d'
HM_FORMAT = '%H:%M:%S'
DHM_FORMAT = DT_FORMAT + ' ' + HM_FORMAT
