#!/usr/bin/env python

from distutils.core import setup
import os

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
        'tryton.gui.window.view_form.widget_search',
        'tryton.gui.window.view_tree',
        'tryton.plugins.translation',
        'tryton.plugins.workflow',
        'tryton.wizard',
    ],
    data_files=[
        ('share/pixmaps', [
            'share/pixmaps/*.png',
            ]),
        ('share/tryton', ['share/tryton/tryton.glade', 'share/tryton/tipoftheday.txt']),
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
    #    'xml',
    #    'pygtk (>2.0)',
    #],
)
