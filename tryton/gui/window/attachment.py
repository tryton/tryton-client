#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
"Attachment"
import gtk
from gtk import glade
import gobject
import gettext
import copy
import os
import base64
import urllib
import tempfile
from tryton.gui.window.view_tree.parse import Parse
import tryton.rpc as rpc
import tryton.common as common
from tryton.config import GLADE, TRYTON_ICON

_ = gettext.gettext


class Attachment(object):
    "Attachment window"

    def __init__(self, model, obj_id, parent):
        self.glade = glade.XML(GLADE, 'win_attach',
                gettext.textdomain())
        self.win = self.glade.get_widget('win_attach')
        self.win.set_icon(TRYTON_ICON)
        self.win.set_transient_for(parent)
        self.parent = parent
        self.resource = (model, obj_id)

        self.view = gtk.TreeView()
        viewport = self.glade.get_widget('vp_attach')
        viewport.add(self.view)

        selection = self.view.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect('changed', self._sig_changed)

        try:
            view = rpc.execute('object', 'execute',
                    'ir.attachment', 'fields_view_get', False, 'tree')
        except Exception, exception:
            common.process_exception(exception, parent)
            raise

        parse = Parse(view['fields'])
        parse.parse(view['arch'], self.view)
        self.view.set_headers_visible(True)
        self.fields_order = parse.fields_order

        types = [gobject.TYPE_STRING]
        for i in self.fields_order:
            types.append(gobject.TYPE_STRING)
        self.view_name = view['name']
        self.model_name = model
        self.model = gtk.ListStore(*types)


        self.view.set_model(self.model)
        self.view.connect('row-activated', self.sig_activate)
        self.view.show_all()
        self.reload(preview=False)

        signals = {
            'on_attach_but_del_activate': self._sig_del,
            'on_attach_but_add_activate': self._sig_add,
            'on_attach_but_save_activate': self._sig_save,
            'on_attach_but_link_activate': self._sig_link,
            'comment_save': self._sig_comment,
        }
        for signal in signals:
            self.glade.signal_connect(signal, signals[signal])

    def _sig_comment(self, widget):
        textview = self.glade.get_widget('attach_tv')
        start = textview.get_buffer().get_start_iter()
        end = textview.get_buffer().get_end_iter()
        comment = textview.get_buffer().get_text(start, end)
        model, iter = self.view.get_selection().get_selected()
        context = copy.copy(rpc.CONTEXT)
        if not iter:
            common.warning(_('You must put a text comment to an attachement.'),
                    self.win, _('Text not saved!'))
            return None
        obj_id = model.get_value(iter, 0)
        if obj_id:
            args = ('object', 'execute',
                    'ir.attachment', 'write', [int(obj_id)],
                    {'description': comment}, context)
            try:
                rpc.execute(*args)
            except Exception, exception:
                common.process_exception(exception, self.win, *args)
        else:
            common.warning(_('You must put a text comment to an attachement.'),
                    self.win, _('Text not saved!'))

    def _sig_del(self, widget):
        model, iter = self.view.get_selection().get_selected()
        if not iter:
            return None
        obj_id = model.get_value(iter, 0)
        if obj_id:
            if common.sur(_('Are you sure you want to remove this attachment?'),
                    self.win):
                try:
                    rpc.execute('object', 'execute',
                            'ir.attachment', 'unlink', [int(obj_id)])
                except Exception, exception:
                    common.process_exception(exception, self.win, *args)
        self.reload()

    def _sig_link(self, widget):
        filename = common.file_selection(_('Select file'), parent=self.win)
        if not filename:
            return
        try:
            if filename:
                fname = os.path.basename(filename)
                args = ('object', 'execute',
                        'ir.attachment', 'create', {
                            'name': fname,
                            'res_model': self.resource[0],
                            'res_id': self.resource[1],
                            'link': filename,
                            })
                try:
                    obj_id = rpc.execute(*args)
                except Exception, exception:
                    obj_id = common.process_exception(exception, self.win, *args)
                    if not obj_id:
                        return
                self.reload(preview=False)
                self.preview(int(obj_id))
        except IOError:
            common.message(_('Can not open file!'), self.win, gtk.MESSAGE_ERROR)

    def _sig_save(self, widget):
        model, iter = self.view.get_selection().get_selected()
        if not iter:
            return None
        obj_id = model.get_value(iter, 0)
        if obj_id:
            try:
                data = rpc.execute('object', 'execute',
                        'ir.attachment', 'read', int(obj_id))
            except Exception, exception:
                common.process_exception(exception, self.win)
                return None
            if not data:
                return None
            filename = common.file_selection(_('Save As...'),
                    filename=data['name'], parent=self.win,
                    action=gtk.FILE_CHOOSER_ACTION_SAVE)
            if not filename:
                return None
            try:
                if not data['link']:
                    file(filename, 'wb+').write(
                            base64.decodestring(data['datas']))
                else:
                    file(filename, 'wb+').write(
                            urllib.urlopen(data['link']).read())
            except IOError:
                common.message(_('Can not write file!'), self.win,
                        gtk.MESSAGE_ERROR)

    def _sig_add(self, widget):
        filter_all = gtk.FileFilter()
        filter_all.set_name(_('All files'))
        filter_all.add_pattern("*")

        filter_image = gtk.FileFilter()
        filter_image.set_name(_('Images'))
        for mime in ("image/png", "image/jpeg", "image/gif"):
            filter_image.add_mime_type(mime)
        for pat in ("*.png", "*.jpg", "*.gif", "*.tif", "*.xpm"):
            filter_image.add_pattern(pat)

        filenames = common.file_selection(_('Open...'), preview=True,
                multi=True, parent=self.win,
                filters=[filter_all, filter_image])
        for filename in filenames:
            value = file(filename, 'rb').read()
            name = os.path.basename(filename)
            args = ('object', 'execute',
                    'ir.attachment', 'create', {
                        'name': name,
                        'datas': base64.encodestring(value),
                        'res_model': self.resource[0],
                        'res_id': self.resource[1],
                        })
            try:
                obj_id = rpc.execute(*args)
            except Exception, exception:
                obj_id = common.process_exception(exception, self.win, *args)
                if not obj_id:
                    return
            self.reload(preview=False)
            self.preview(int(obj_id))

    def _sig_changed(self, widget):
        model, iters = self.view.get_selection().get_selected_rows()
        if not iters:
            return None
        obj_id = model.get_value(model.get_iter(iters[0]), 0)
        self.preview(int(obj_id))

    def sig_activate(self, widget, path, view_column):
        iter = self.model.get_iter(path)
        obj_id = self.model.get_value(iter, 0)
        if obj_id:
            try:
                data = rpc.execute('object', 'execute',
                        'ir.attachment', 'read', int(obj_id))
            except Exception, exception:
                common.process_exception(exception, self.win)
                return None
            if not data:
                return None
            file_name = data['link']
            if not data['link']:
                (fileno, file_name) = tempfile.mkstemp(
                        data['name'], 'tryton_')
                file_p = file(file_name, 'wb+')
                file_p.write(base64.decodestring(data['datas']))
                file_p.close()
                os.close(fileno)
            ext = file_name.split('.')[-1].lower()
            common.file_open(file_name, ext, self.parent)

    def preview(self, obj_id):
        try:
            data = rpc.execute('object', 'execute',
                    'ir.attachment', 'read', obj_id)
        except Exception, exception:
            common.process_exception(exception, self.win)
            return None
        if not data:
            return None

        buf = self.glade.get_widget('attach_tv').get_buffer()
        buf.delete(buf.get_start_iter(), buf.get_end_iter())
        iter_start = buf.get_start_iter()
        buf.insert(iter_start, data['description'] or '')

        fname = str(data['name'])
        label = self.glade.get_widget('attach_filename')
        label.set_text(fname)

        label = self.glade.get_widget('attach_title')
        label.set_text(str(data['name']))

        decoder = {
                'jpg': 'jpeg',
                'jpeg': 'jpeg',
                'gif': 'gif',
                'png': 'png',
                'bmp': 'bmp',
                }
        ext = fname.split('.')[-1].lower()
        img = self.glade.get_widget('attach_image')
        img.clear()
        if ext in ('jpg', 'jpeg', 'png', 'gif', 'bmp'):
            try:
                if not data['link']:
                    value = base64.decodestring(data['datas'])
                else:
                    value = urllib.urlopen(data['link']).read()

                def set_size(widget, width, height):
                    allocation = self.win.get_allocation()
                    scale1 = 0.3 * float(allocation.width) / float(width)
                    scale2 = 0.3 * float(allocation.height) / float(height)
                    scale = min(scale1, scale2)
                    if int(scale * width) > 0 and int(scale * height) > 0:
                        widget.set_size(int(scale * width), int(scale * height))

                loader = gtk.gdk.PixbufLoader(decoder[ext])
                loader.connect_after('size-prepared', set_size)

                loader.write(value, len(value))
                pixbuf = loader.get_pixbuf()
                loader.close()

                img.set_from_pixbuf(pixbuf)
            except:
                img.set_from_icon_name('gtk-cancel', gtk.ICON_SIZE_DIALOG)

    def reload(self, preview=True):
        self.model.clear()
        try:
            ids = rpc.execute('object', 'execute',
                    'ir.attachment', 'search', [
                        ('res_model', '=', self.resource[0]),
                        ('res_id', '=', self.resource[1]),
                        ])
        except Exception, exception:
            common.process_exception(exception, self.win)
            return
        try:
            res_ids = rpc.execute('object', 'execute',
                    'ir.attachment', 'read', ids,
                    self.fields_order + ['link'])
        except Exception, exception:
            common.process_exception(exception, self.win)
            return
        for res in res_ids:
            num = self.model.append()
            args = []
            for i in range(len(self.fields_order)):
                args.append(i + 1)
                if res['link']:
                    args.append(_('link: ') + str(res[self.fields_order[i]]))
                else:
                    args.append(str(res[self.fields_order[i]]))
            self.model.set(num, 0, res['id'], *args)
        if preview and len(res_ids):
            self.preview(int(res_ids[0]['id']))

    def run(self):
        self.win.run()
        self.parent.present()
        self.win.destroy()
