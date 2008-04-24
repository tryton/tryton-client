from graph import Graph
from tryton.common import hex2rgb, lighten
import locale


class Bar(Graph):

    def drawGraph(self, cr, width, height):

        def drawBar(bar):
            cr.set_line_width(1.0)

            x = self.area.w * bar.x + self.area.x
            y = self.area.h * bar.y + self.area.y
            w = self.area.w * bar.w
            h = self.area.h * bar.h

            if w < 1 or h <1:
                return # don't draw too small

            cr.set_source_rgba(0, 0, 0, 0.15)
            rectangle = self._getShadowRectangle(x, y, w, h)
            cr.rectangle(*rectangle)
            cr.fill()

            cr.rectangle(x, y, w, h)
            color = self.colorScheme[bar.yname]
            if bar.highlight:
                color = self.colorScheme['__highlight']
            cr.set_source_rgb(*color)
            cr.fill_preserve()
            cr.stroke()

        cr.save()
        for bar in self.bars:
            drawBar(bar)
        cr.restore()

    def motion(self, widget, event):
        super(Bar, self).motion(widget, event)

        def intersect(bar, event):
            x = self.area.w * bar.x + self.area.x
            y = self.area.h * bar.y + self.area.y
            w = self.area.w * bar.w
            h = self.area.h * bar.h

            if x <= event.x <= x + w and y <= event.y <= y + h:
                return True
            return False

        highlight = False
        draw_bars = []
        for bar in self.bars:
            if intersect(bar, event):
                if not bar.highlight:
                    bar.highlight = True
                    label = locale.format('%.2f', bar.yval, True)
                    label += '\n'
                    label += str(self.labels[bar.xname])
                    self.popup.set_text(label)
                    draw_bars.append(bar)
            else:
                if bar.highlight:
                    bar.highlight = False
                    draw_bars.append(bar)
            if bar.highlight:
                highlight = True
        if draw_bars:
            minx = self.area.w + self.area.x
            miny = self.area.h + self.area.y
            maxx = maxy = 0.0
            for bar in draw_bars:
                x = self.area.w * bar.x + self.area.x
                y = self.area.h * bar.y + self.area.y
                minx = min(x, minx)
                miny = min(y, miny)
                maxx = max(x + self.area.w * bar.w, maxx)
                maxy = max(y + self.area.h * bar.h, maxy)
            self.queue_draw_area(int(minx), int(miny),
                    int(maxx - minx), int(maxy - miny))
        if highlight:
            self.popup.show()
        else:
            self.popup.hide()


class VerticalBar(Bar):
    'Vertical Bar Graph'

    def updateGraph(self):

        barWidth = self.xscale * 0.9
        barMargin = self.xscale * (1.0 - 0.9) / 2

        self.bars = []
        i = 0
        keys = self.datas.keys()
        keys.sort()
        for xfield in keys:
            j = 0
            barWidthForSet = barWidth / len(self.datas[xfield])
            for yfield in self._getDatasKeys():
                xval = i
                yval = self.datas[xfield][yfield]

                x = (xval - self.minxval) * self.xscale + \
                        barMargin + (j * barWidthForSet)
                y = 1.0 - (yval - self.minyval) * self.yscale
                w = barWidthForSet
                h = yval * self.yscale

                if h < 0:
                    h = abs(h)
                    y -= h

                rect = Rect(x, y, w, h, xval, yval, xfield, yfield)
                if (0.0 <= rect.x <= 1.0) and (0.0 <= rect.y <= 1.0):
                    self.bars.append(rect)

                j += 1
            i += 1

    def XLabels(self):
        xlabels = super(VerticalBar, self).XLabels()
        return [(x[0] + (self.xscale / 2), x[1]) for x in xlabels]

    def _getShadowRectangle(self, x, y, w, h):
        return (x-2, y-2, w+4, h+2)


class HorizontalBar(Bar):
    'Horizontal Bar Graph'

    def updateGraph(self):

        barWidth = self.xscale * 0.9
        barMargin = self.xscale * (1.0 - 0.9) / 2

        self.bars = []
        i = 0
        keys = self.datas.keys()
        keys.sort()
        for xfield in keys:
            j = 0
            barWidthForSet = barWidth / len(self.datas[xfield])
            for yfield in self._getDatasKeys():
                xval = i
                yval = self.datas[xfield][yfield]

                x = - self.minyval * self.yscale
                y = (xval - self.minxval) * self.xscale + \
                        barMargin + (j * barWidthForSet)
                w = yval * self.yscale
                h = barWidthForSet

                if w < 0:
                    w = abs(w)
                    x -= w

                rect = Rect(x, y, w, h, xval, yval, xfield, yfield)
                if (0.0 <= rect.x <= 1.0) and (0.0 <= rect.y <= 1.0):
                    self.bars.append(rect)

                j += 1
            i += 1

    def YLabels(self):
        xlabels = super(HorizontalBar, self).XLabels()
        return [(1 - (x[0] + (self.xscale / 2)), x[1]) for x in xlabels]

    def XLabels(self):
        ylabels = super(HorizontalBar, self).YLabels()
        return [(x[0], x[1]) for x in ylabels]

    def _getShadowRectangle(self, x, y, w, h):
        return (x, y-2, w+2, h+4)

    def _getLegendPosition(self, width, height):
        return self.area.x + self.area.w * 0.95 - width, \
                self.area.y + self.area.h * 0.05

    def drawLines(self, cr, width, height):
        for w, label in self.XLabels():
            self.drawLine(cr, w, 0)


class Rect(object):

    def __init__(self, x, y, w, h, xval, yval, xname, yname):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.xval, self.yval = xval, yval
        self.yname = yname
        self.xname = xname
        self.highlight = False
