# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
__version__ = "6.4.5"
import locale

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_foreign('cairo')
try:
    gi.require_version('GtkSpell', '3.0')
except ValueError:
    pass
try:
    gi.require_version('EvinceDocument', '3.0')
    gi.require_version('EvinceView', '3.0')
except ValueError:
    pass

try:
    # Import earlier otherwise there is a segmentation fault on MSYS2
    import goocalendar  # noqa: F401
except ImportError:
    pass

if not hasattr(locale, 'localize'):
    def localize(formatted, grouping=False, monetary=False):
        if '.' in formatted:
            seps = 0
            parts = formatted.split('.')
            if grouping:
                parts[0], seps = locale._group(parts[0], monetary=monetary)
            decimal_point = locale.localeconv()[
                monetary and 'mon_decimal_point' or 'decimal_point']
            formatted = decimal_point.join(parts)
            if seps:
                formatted = locale._strip_padding(formatted, seps)
        else:
            seps = 0
            if grouping:
                formatted, seps = locale._group(formatted, monetary=monetary)
            if seps:
                formatted = locale._strip_padding(formatted, seps)
        return formatted
    setattr(locale, 'localize', localize)


def delocalize(string, monetary=False):
    conv = locale.localeconv()

    # First, get rid of the grouping
    ts = conv[monetary and 'mon_thousands_sep' or 'thousands_sep']
    if ts:
        string = string.replace(ts, '')
    # next, replace the decimal point with a dot
    dd = conv[monetary and 'mon_decimal_point' or 'decimal_point']
    if dd:
        string = string.replace(dd, '.')
    return string


setattr(locale, 'delocalize', delocalize)
