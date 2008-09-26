#!/usr/bin/env python
#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.

from distutils.core import setup
import os
import glob
import sys

args = {}

try:
    from babel.messages import frontend as babel

    args['cmdclass'] = {
            'compile_catalog': babel.compile_catalog,
            'extract_messages': babel.extract_messages,
            'init_catalog': babel.init_catalog,
            'update_catalog': babel.update_catalog,
        }

    args['message_extractors'] = {
            'tryton': [
                ('**.py', 'python', None),
            ],
        }

except ImportError:
        pass

if os.name == 'nt':
    import py2exe
    args['windows'] = [{
        'script': os.path.join('bin', 'tryton'),
    }]
    args['options'] = {
        'py2exe': {
            'optimize': 0,
            'bundle_files': 3, #don't bundle because gtk doesn't support it
            'packages': [
                'encodings',
                'gtk',
                'pytz',
            ],
            'includes': 'pango,atk,gobject,cairo,pangocairo',
            'dll_excludes': [
                'iconv.dll',
                'intl.dll',
                'libatk-1.0-0.dll',
                'libgdk_pixbuf-2.0-0.dll',
                'libgdk-win32-2.0-0.dll',
                'libglib-2.0-0.dll',
                'libgmodule-2.0-0.dll',
                'libgobject-2.0-0.dll',
                'libgthread-2.0-0.dll',
                'libgtk-win32-2.0-0.dll',
                'libpango-1.0-0.dll',
                'libpangowin32-1.0-0.dll',
            ],
        }
    }
    args['zipfile'] = None

execfile(os.path.join('tryton', 'version.py'))

setup(name=PACKAGE,
    version=VERSION,
    description='Tryton client',
    author='B2CK',
    author_email='info@b2ck.com',
    url=WEBSITE,
    packages=[
        'tryton',
        'tryton.action',
        'tryton.common',
        'tryton.gui',
        'tryton.gui.window',
        'tryton.gui.window.view_form',
        'tryton.gui.window.view_form.model',
        'tryton.gui.window.view_form.screen',
        'tryton.gui.window.view_form.view',
        'tryton.gui.window.view_form.view.form_gtk',
        'tryton.gui.window.view_form.view.list_gtk',
        'tryton.gui.window.view_form.view.graph_gtk',
        'tryton.gui.window.view_form.widget_search',
        'tryton.gui.window.view_tree',
        'tryton.gui.window.view_board',
        'tryton.plugins.translation',
        'tryton.plugins.workflow',
        'tryton.wizard',
    ],
    data_files=[
        ('share/pixmaps', glob.glob('share/pixmaps/*.png') + \
                glob.glob('share/pixmaps/*.svg')),
        ('share/tryton', glob.glob('share/tryton/tryton.glade') + \
                glob.glob('share/tryton/tipoftheday.txt')),
        ('share/locale/fr_FR/LC_MESSAGES', glob.glob('share/locale/fr_FR/LC_MESSAGES/*.mo')),
    ],
    scripts=['bin/tryton'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License Version 2 (GPL-2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Office/Business',
    ],
    license=LICENSE,
    #requires=[
    #    'pygtk (>2.0)',
    #],
    **args
)
