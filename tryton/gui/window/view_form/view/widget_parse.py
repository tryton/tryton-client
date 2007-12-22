from interface import ParserInterface
#import form_gtk
import tree_gtk
#import graph_gtk
#import calendar_gtk
#from form import ViewForm
from list import ViewList
#from graph import ViewGraph
#from calendar import ViewCalendar

PARSERS = {
#    'form': form_gtk.parser_form,
    'tree': tree_gtk.parser_tree,
#    'graph': graph_gtk.parser_graph,
#    'calendar': calendar_gtk.parser_calendar,
}

PARSERS2 = {
#    'form': ViewForm,
    'tree': ViewList,
#    'graph': ViewGraph,
#    'calendar': ViewCalendar,
}


class WidgetParse(ParserInterface):

    def parse(self, screen, root_node, fields, toolbar=None):
        widget = None
        for node in root_node.childNodes:
            if not node.nodeType == node.ELEMENT_NODE:
                continue
            if node.localName in PARSERS:
                widget = PARSERS[node.localName](self.window, self.parent,
                        self.attrs, screen)
                wid, child, buttons, on_write = widget.parse(screen.resource,
                        node, fields)
                screen.set_on_write(on_write)
                res = PARSERS2[node.localName](self.window, screen, wid, child,
                        buttons, toolbar)
                res.title = widget.title
                widget = res
                break
            else:
                pass
        return widget
