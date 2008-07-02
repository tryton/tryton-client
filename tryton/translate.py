#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
"Translate"
import os
import locale
import gettext
from version import PACKAGE
from tryton import CURRENT_DIR, PREFIX
import logging
import gtk

_ = gettext.gettext

_LOCALE2WIN32 = {
    'af_ZA': 'Afrikaans_South Africa',
    'sq_AL': 'Albanian_Albania',
    'ar_SA': 'Arabic_Saudi Arabia',
    'eu_ES': 'Basque_Spain',
    'be_BY': 'Belarusian_Belarus',
    'bs_BA': 'Serbian (Latin)',
    'bg_BG': 'Bulgarian_Bulgaria',
    'ca_ES': 'Catalan_Spain',
    'hr_HR': 'Croatian_Croatia',
    'zh_CN': 'Chinese_China',
    'zh_TW': 'Chinese_Taiwan',
    'cs_CZ': 'Czech_Czech Republic',
    'da_DK': 'Danish_Denmark',
    'nl_NL': 'Dutch_Netherlands',
    'et_EE': 'Estonian_Estonia',
    'fa_IR': 'Farsi_Iran',
    'ph_PH': 'Filipino_Philippines',
    'fi_FI': 'Finnish_Finland',
    'fr_FR': 'French_France',
    'fr_BE': 'French_France',
    'fr_CH': 'French_France',
    'fr_CA': 'French_France',
    'ga': 'Scottish Gaelic',
    'gl_ES': 'Galician_Spain',
    'ka_GE': 'Georgian_Georgia',
    'de_DE': 'German_Germany',
    'el_GR': 'Greek_Greece',
    'gu': 'Gujarati_India',
    'he_IL': 'Hebrew_Israel',
    'hi_IN': 'Hindi',
    'hu': 'Hungarian_Hungary',
    'is_IS': 'Icelandic_Iceland',
    'id_ID': 'Indonesian_indonesia',
    'it_IT': 'Italian_Italy',
    'ja_JP': 'Japanese_Japan',
    'kn_IN': 'Kannada',
    'km_KH': 'Khmer',
    'ko_KR': 'Korean_Korea',
    'lo_LA': 'Lao_Laos',
    'lt_LT': 'Lithuanian_Lithuania',
    'lat': 'Latvian_Latvia',
    'ml_IN': 'Malayalam_India',
    'id_ID': 'Indonesian_indonesia',
    'mi_NZ': 'Maori',
    'mn': 'Cyrillic_Mongolian',
    'no_NO': 'Norwegian_Norway',
    'nn_NO': 'Norwegian-Nynorsk_Norway',
    'pl': 'Polish_Poland',
    'pt_PT': 'Portuguese_Portugal',
    'pt_BR': 'Portuguese_Brazil',
    'ro_RO': 'Romanian_Romania',
    'ru_RU': 'Russian_Russia',
    'mi_NZ': 'Maori',
    'sr_CS': 'Serbian (Cyrillic)_Serbia and Montenegro',
    'sk_SK': 'Slovak_Slovakia',
    'sl_SI': 'Slovenian_Slovenia',
    'es_ES': 'Spanish_Spain',
    'sv_SE': 'Swedish_Sweden',
    'ta_IN': 'English_Australia',
    'th_TH': 'Thai_Thailand',
    'mi_NZ': 'Maori',
    'tr_TR': 'Turkish_Turkey',
    'uk_UA': 'Ukrainian_Ukraine',
    'vi_VN': 'Vietnamese_Viet Nam',
}


def setlang(lang=None):
    "Set language"
    locale_dir = os.path.join(CURRENT_DIR, 'share/locale')
    if not os.path.isdir(locale_dir):
        locale_dir = os.path.join(PREFIX, 'share/locale')
    if lang:
        encoding = locale.getdefaultlocale()[1]
        if encoding == 'utf':
            encoding = 'UTF-8'
        if encoding == 'cp1252':
            encoding = '1252'
        try:
            lang2 = lang
            if os.name == 'nt':
                lang2 = _LOCALE2WIN32.get(lang, lang)
            locale.setlocale(locale.LC_ALL, lang2 + '.' + encoding)
        except:
            logging.getLogger('translate').warn(
                    _('Unable to set locale %s') % lang2 + '.' + encoding)
        if not os.path.isdir(locale_dir):
            gettext.install(PACKAGE, unicode=1)
        else:
            lang = gettext.translation(PACKAGE, locale_dir, languages=[lang],
                    fallback=True)
            lang.install(unicode=1)
    else:
        try:
            locale.setlocale(locale.LC_ALL, '')
        except:
            logging.getLogger('translate').warn(
                    _('Unable to unset locale'))
        if os.path.isdir(locale_dir):
            gettext.bindtextdomain(PACKAGE, locale_dir)
        gettext.textdomain(PACKAGE)
        gettext.install(PACKAGE, unicode=1)
    if os.path.isdir(locale_dir):
        gtk.glade.bindtextdomain(PACKAGE, locale_dir)

def set_language_direction(direction):
    if direction == 'rtl':
        gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)
    else:
        gtk.widget_set_default_direction(gtk.TEXT_DIR_LTR)
