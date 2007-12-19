"Translate"
import os
import locale
import gettext
from version import PACKAGE
from tryton import CURRENT_DIR, PREFIX
import logging
import gtk

_ = gettext.gettext

def setlang(lang=None):
    "Set language"
    locale_dir = os.path.join(CURRENT_DIR, 'share/locale')
    if not os.path.isdir(locale_dir):
        locale_dir = os.path.join(PREFIX, 'share/locale')
    if not os.path.isdir(locale_dir):
        gettext.install(PACKAGE, unicode=1)
        return False
    if lang:
        encoding = locale.getdefaultlocale()[1]
        if encoding == 'utf':
            encoding = 'UTF-8'
        try:
            locale.setlocale(locale.LC_ALL, lang+'.'+encoding)
        except:
            logging.getLogger('translate').warn(
                    _('Unable to set locale %s') % lang+'.'+encoding)
        lang = gettext.translation(PACKAGE, locale_dir, languages=lang,
                fallback=True)
        lang.install(unicode=1)
    else:
        try:
            locale.setlocale(locale.LC_ALL, '')
        except:
            logging.getLogger('translate').warn(
                    _('Unable to unset locale'))
        gettext.bindtextdomain(PACKAGE, locale_dir)
        gettext.textdomain(PACKAGE)
        gettext.install(PACKAGE, unicode=1)
    gtk.glade.bindtextdomain(PACKAGE, locale_dir)
