#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
import gtk
import gettext
import tryton.rpc as rpc
import tryton.common as common
import thread, time
from tryton.gui.window.view_form.screen import Screen
import os

_ = gettext.gettext


class Dialog(object):
    "Dialog for wizard"

    def __init__(self, arch, fields, state, obj_name, parent,
            context=None):
        self.parent = parent
        self.states = []
        default = -1
        self.dia = gtk.Dialog(_('Wizard'), parent,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        if hasattr(self.dia, 'set_deletable') and os.name != 'nt':
            self.dia.set_deletable(False)

        self.accel_group = gtk.AccelGroup()
        self.dia.add_accel_group(self.accel_group)

        for i in state:
            but = gtk.Button(i[1])
            but.show()
            if len(i) >= 3:
                icon = gtk.Image()
                icon.set_from_stock(i[2], gtk.ICON_SIZE_BUTTON)
                but.set_image(icon)
            self.dia.add_action_widget(but, len(self.states))
            if len(i) >= 4 and i[3]:
                if default < 0:
                    default = len(self.states)
                    but.set_flags(gtk.CAN_DEFAULT)
                    but.add_accelerator('clicked', self.accel_group,
                            gtk.keysyms.Return, gtk.gdk.CONTROL_MASK,
                            gtk.ACCEL_VISIBLE)
                    self.dia.set_default_response(default)
            self.states.append(i[0])

        val = {}
        for i in fields:
            if 'value' in fields[i]:
                val[i] = fields[i]['value']

        self.screen = Screen(obj_name, self.dia, view_type=[], context=context)
        self.screen.add_view_custom(arch, fields, display=True)

        width, height = self.screen.screen_container.size_get()
        parent_width, parent_height = parent.get_size()
        self.screen.widget.set_size_request(min(parent_width - 20, width + 20),
                min(parent_height - 60, height + 25))
        self.screen.widget.show()

        self.dia.vbox.pack_start(self.screen.widget)
        self.dia.set_title(self.screen.current_view.title)
        self.dia.show()
        self.screen.new(default=False)
        self.screen.current_model.set(val)
        self.screen.current_view.set_cursor()

    def run(self, datas=None):
        if datas is None:
            datas = {}
        while True:
            res = self.dia.run()
            self.screen.current_view.set_value()
            if self.screen.current_model.validate() \
                    or (res<0) or (self.states[res]=='end'):
                break
            self.screen.display()
        if res < len(self.states) and res >= 0:
            datas.update(self.screen.get())
            self.dia.hide()
            self.parent.present()
            return (self.states[res], datas)
        else:
            self.dia.hide()
            self.parent.present()
            return False

    def destroy(self):
        self.dia.destroy()


class Wizard(object):

    @staticmethod
    def execute(action, datas, parent, state='init', context=None):
        from tryton.action import Action
        if not 'form' in datas:
            datas['form'] = {}
        try:
            wiz_id = rpc.execute('wizard', 'create', action)
        except Exception, exception:
            common.process_exception(exception, parent)
            return
        dia = None
        while state != 'end':
            ctx = context.copy()
            ctx['active_id'] = datas.get('id')
            ctx['active_ids'] = datas.get('ids')
            wizardprogress = WizardProgress(wiz_id, state, datas,
                    parent, ctx)
            res = wizardprogress.run()
            if not res:
                if dia:
                    res = {'type': 'form'}
                else:
                    return
            else:
                if dia:
                    dia.destroy()
                    dia = None

            if 'datas' in res:
                datas['form'] = res['datas']
            else:
                datas['form'] = {}
            if res['type'] == 'form':
                if not dia:
                    dia = Dialog(res['arch'], res['fields'], res['state'],
                            res['object'], parent, context=ctx)
                    dia.screen.current_model.set(datas['form'])
                res2 = dia.run(datas['form'])
                if not res2:
                    break
                (state, new_data) = res2
                for data in new_data:
                    if new_data[data] is None:
                        del new_data[data]
                datas['form'].update(new_data)
                del new_data
            elif res['type'] == 'action':
                Action._exec_action(res['action'], datas, context=ctx)
                state = res['state']
            elif res['type'] == 'print':
                datas['report_id'] = res.get('report_id', False)
                if res.get('get_id_from_action', False):
                    backup_ids = datas['ids']
                    datas['ids'] = datas['form']['ids']
                    Action.exec_report(res['report'], datas, context=ctx)
                    datas['ids'] = backup_ids
                else:
                    Action.exec_report(res['report'], datas, context=ctx)
                state = res['state']
            elif res['type'] == 'state':
                state = res['state']
        if dia:
            dia.destroy()
            dia = None
        try:
            rpc.execute('wizard', 'delete', wiz_id)
            #XXX to remove when company displayed in status bar
            rpc.context_reload()
        except:
            pass


class WizardProgress(object):

    def __init__(self, wizard_id, state, datas, parent, context):
        self.res = None
        self.error = False
        self.wizard_id = wizard_id
        self.state = state
        self.datas = datas
        self.parent = parent
        self.context = context
        self.exception = None

    def run(self):

        def start(wiz_id, datas, state, context):
            ctx = rpc.CONTEXT.copy()
            ctx.update(context)
            try:
                self.res = rpc.execute('wizard',
                        'execute', wiz_id, datas, state, ctx)
            except Exception, exception:
                self.error = True
                self.res = False
                self.exception = exception
                return True
            if not self.res:
                self.error = True
            return True

        thread.start_new_thread(start,
                (self.wizard_id, self.datas, self.state, self.context))

        i = 0
        win = None
        progressbar = None
        while (not self.res) and (not self.error):
            time.sleep(0.1)
            i += 1
            if i > 10:
                if not win or not progressbar:
                    win = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
                    win.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
                    vbox = gtk.VBox(False, 0)
                    hbox = gtk.HBox(False, 13)
                    hbox.set_border_width(10)
                    img = gtk.Image()
                    img.set_from_stock('tryton-dialog-information', gtk.ICON_SIZE_DIALOG)
                    hbox.pack_start(img, expand=True, fill=False)
                    vbox2 = gtk.VBox(False, 0)
                    label = gtk.Label()
                    label.set_markup('<b>'+_('Operation in progress')+'</b>')
                    label.set_alignment(0.0, 0.5)
                    vbox2.pack_start(label, expand=True, fill=False)
                    vbox2.pack_start(gtk.HSeparator(), expand=True, fill=True)
                    vbox2.pack_start(gtk.Label(_("Please wait,\n" \
                            "this operation may take a while...")),
                            expand=True, fill=False)
                    hbox.pack_start(vbox2, expand=True, fill=True)
                    vbox.pack_start(hbox)
                    progressbar = gtk.ProgressBar()
                    progressbar.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)
                    vbox.pack_start(progressbar, expand=True, fill=False)
                    win.add(vbox)
                    win.set_transient_for(self.parent)
                    win.show_all()
                progressbar.pulse()
                gtk.main_iteration()
        if win:
            win.destroy()
            gtk.main_iteration()
        if self.exception:
            common.process_exception(self.exception, self.parent)
        return self.res
