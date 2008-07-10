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
    'af_ZA': 'Afrikaans',
    'ar_AE': 'Arabic_UAE',
    'ar_BH': 'Arabic_Bahrain',
    'ar_DZ': 'Arabic_Algeria',
    'ar_EG': 'Arabic_Egypt',
    'ar_IQ': 'Arabic_Iraq',
    'ar_JO': 'Arabic_Jordan',
    'ar_KW': 'Arabic_Kuwait',
    'ar_LB': 'Arabic_Lebanon',
    'ar_LY': 'Arabic_Libya',
    'ar_MA': 'Arabic_Morocco',
    'ar_OM': 'Arabic_Oman',
    'ar_QA': 'Arabic_Qatar',
    'ar_SA': 'Arabic_Saudi_Arabia',
    'ar_SY': 'Arabic_Syria',
    'ar_TN': 'Arabic_Tunisia',
    'ar_YE': 'Arabic_Yemen',
    'az-Cyrl-AZ': 'Azeri_Cyrillic',
    'az-Latn-AZ': 'Azeri_Latin',
    'be_BY': 'Belarusian',
    'bg_BG': 'Bulgarian',
    'bs_BA': 'Serbian (Latin)',
    'ca_ES': 'Catalan',
    'cs_CZ': 'Czech',
    'da_DK': 'Danish',
    'de_AT': 'German_Austrian',
    'de_CH': 'German_Swiss',
    'de_DE': 'German_Standard',
    'de_LI': 'German_Liechtenstein',
    'de_LU': 'German_Luxembourg',
    'el_GR': 'Greek_Greece',
    'en_AU': 'English_Australian',
    'en_BZ': 'English_Belize',
    'en_CA': 'English_Canadian',
    'en_IE': 'English_Irish',
    'en_JM': 'English_Jamaica',
    'en_TT': 'English_Trinidad',
    'en_US': 'English_USA',
    'en_ZW': 'English_Zimbabwe',
    'es_AR': 'Spanish_Argentina',
    'es_BO': 'Spanish_Bolivia',
    'es_CL': 'Spanish_Chile',
    'es_CO': 'Spanish_Colombia',
    'es_CR': 'Spanish_Costa_Rica',
    'es_DO': 'Spanish_Dominican_Republic',
    'es_EC': 'Spanish_Ecuador',
    'es_ES': 'Spanish_Modern_Sort',
    'es_ES_tradnl': 'Spanish_Traditional_Sort',
    'es_GT': 'Spanish_Guatemala',
    'es_HN': 'Spanish_Honduras',
    'es_MX': 'Spanish_Mexican',
    'es_NI': 'Spanish_Nicaragua',
    'es_PA': 'Spanish_Panama',
    'es_PE': 'Spanish_Peru',
    'es_PR': 'Spanish_Puerto_Rico',
    'es_PY': 'Spanish_Paraguay',
    'es_SV': 'Spanish_El_Salvador',
    'es_UY': 'Spanish_Uruguay',
    'es_VE': 'Spanish_Venezuela',
    'et_EE': 'Estonian_Estonia',
    'eu_ES': 'Basque',
    'fa_IR': 'Farsi_Iran',
    'fi_FI': 'Finnish_Finland',
    'fr_BE': 'French_Belgian',
    'fr_CA': 'French_Canadian',
    'fr_CH': 'French_Swiss',
    'fr_FR': 'French_Standard',
    'fr_LU': 'French_Luxembourg',
    'fr_MC': 'French_Monaco',
    'ga': 'Scottish Gaelic',
    'gl_ES': 'Galician_Spain',
    'gu': 'Gujarati_India',
    'he_IL': 'Hebrew',
    'he_IL': 'Hebrew_Israel',
    'hi_IN': 'Hindi',
    'hi_IN': 'Hindi',
    'hr_HR': 'Croatian',
    'hu_HU': 'Hungarian',
    'hu': 'Hungarian_Hungary',
    'hy_AM': 'Armenian',
    'id_ID': 'Indonesian',
    'is_IS': 'Icelandic',
    'it_CH': 'Italian_Swiss',
    'it_IT': 'Italian_Standard',
    'ja_JP': 'Japanese',
    'ka_GE': 'Georgian_Georgia',
    'kk_KZ': 'Kazakh',
    'km_KH': 'Khmer',
    'kn_IN': 'Kannada',
    'ko_IN': 'Konkani',
    'ko_KR': 'Korean',
    'lo_LA': 'Lao_Laos',
    'lt_LT': 'Lithuanian',
    'lv_LV': 'Latvian',
    'mi_NZ': 'Maori',
    'mi_NZ': 'Maori',
    'mi_NZ': 'Maori',
    'mk_MK': 'Macedonian',
    'ml_IN': 'Malayalam_India',
    'mn': 'Cyrillic_Mongolian',
    'mr_IN': 'Marathi',
    'ms_BN': 'Malay_Brunei_Darussalam',
    'ms_MY': 'Malay_Malaysia',
    'nb_NO': 'Norwegian_Bokmal',
    'nl_BE': 'Dutch_Belgian',
    'nl_NL': 'Dutch_Standard',
    'nn_NO': 'Norwegian-Nynorsk',
    'ph_PH': 'Filipino_Philippines',
    'pl_PL': 'Polish',
    'pt_BR': 'Portuguese_Brazil',
    'pt_PT': 'Portuguese_Standard',
    'ro_RO': 'Romanian',
    'ru_RU': 'Russian',
    'sa_IN': 'Sanskrit',
    'sk_SK': 'Slovak',
    'sl_SI': 'Slovenian',
    'sq_AL': 'Albanian',
    'sr_CS': 'Serbian_Latin',
    'sv_FI': 'Swedish_Finland',
    'sv_SE': 'Swedish',
    'sw_KE': 'Swahili',
    'ta_IN': 'Tamil',
    'th_TH': 'Thai',
    'tr_IN': 'Urdu',
    'tr_TR': 'Turkish',
    'tt_RU': 'Tatar',
    'uk_UA': 'Ukrainian',
    'uz-Cyrl_UZ': 'Uzbek_Cyrillic',
    'uz-Latn_UZ': 'Uzbek_Latin',
    'vi_VN': 'Vietnamese',
    'zh_CN': 'Chinese_PRC',
    'zh_HK': 'Chinese_Hong_Kong',
    'zh_MO': 'Chinese_Macau',
    'zh_SG': 'Chinese_Singapore',
    'zh_TW': 'Chinese_Taiwan',
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
            logging.getLogger('translate').info(
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
