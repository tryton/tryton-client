from tryton.gui.window import Window

def translate_view(datas, parent):
    model = datas['model']
    Window.create(False, 'ir.translation', [],
            [('model', '=', model)], 'form',
            mode=['tree', 'form'], window=parent)

def get_plugins(model):
    return [
        (_('Translate view'), translate_view),
    ]
