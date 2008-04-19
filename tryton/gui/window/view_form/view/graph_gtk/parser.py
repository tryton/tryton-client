from tryton.gui.window.view_form.view.interface import ParserInterface
import tryton.common as common
import gtk
from graph import Graph
from bar import VerticalBar, HorizontalBar

GRAPH_TYPE = {
    'vbar': VerticalBar,
    'hbar': HorizontalBar,
}


class ParserGraph(ParserInterface):

    def parse(self, model, root_node, fields):
        attrs = common.node_attributes(root_node)
        self.title = attrs.get('string', 'Unknown')
        xfield = None
        yfields = []

        for node in root_node.childNodes:
            if not node.nodeType == node.ELEMENT_NODE:
                continue

            if node.localName == 'x':
                for child in node.childNodes:
                    if not child.nodeType == child.ELEMENT_NODE:
                        continue
                    xfield = common.node_attributes(child)
                    xfield['string'] = fields[xfield['name']]['string']
                    break
            elif node.localName == 'y':
                for child in node.childNodes:
                    if not child.nodeType == child.ELEMENT_NODE:
                        continue
                    yattrs = common.node_attributes(child)
                    if yattrs['name'] == '#':
                        yattrs['string'] = '#'
                    else:
                        yattrs['string'] = fields[yattrs['name']]['string']
                    yfields.append(yattrs)

        widget = GRAPH_TYPE[attrs.get('type', 'vbar')](xfield, yfields, attrs)

        return widget, {'root': widget}, [], ''
