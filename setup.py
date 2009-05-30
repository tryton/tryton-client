#!/usr/bin/env python
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from setuptools import setup, find_packages
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
    origIsSystemDLL = py2exe.build_exe.isSystemDLL
    def isSystemDLL(pathname):
        if os.path.basename(pathname).lower() in ("msvcp71.dll", "dwmapi.dll"):
            return 0
        return origIsSystemDLL(pathname)
    py2exe.build_exe.isSystemDLL = isSystemDLL

    args['windows'] = [{
        'script': os.path.join('bin', 'tryton'),
        'icon_resources': [(1, os.path.join('share', 'pixmaps', 'tryton', 'tryton.ico'))],
    }]
    args['options'] = {
        'py2exe': {
            'optimize': 0,
            'bundle_files': 3, #don't bundle because gtk doesn't support it
            'packages': [
                'encodings',
                'gtk',
                'pytz',
                'atk',
                'pango',
                'pangocairo',
            ],
        }
    }
    args['zipfile'] = None
elif os.name == 'mac' \
        or (hasattr(os, 'uname') and os.uname()[0] == 'Darwin'):
    import py2app
    from modulegraph.find_modules import PY_SUFFIXES
    PY_SUFFIXES.append('')
    args['app'] = [os.path.join('bin', 'tryton')]
    args['options'] = {
        'py2app': {
            'argv_emulation': True,
            'includes': 'pygtk, gtk, glib, cairo, pango, pangocairo, atk, ' \
                    'gobject, gio, gtk.keysyms',
            'resources': 'tryton/plugins',
            'frameworks': 'librsvg-2.2.dylib',
            'plist': {
                'CFBundleIdentifier': 'org.tryton',
            },
            'iconfile': os.path.join('share', 'pixmaps', 'tryton',
                'tryton.icns'),
        },
    }

execfile(os.path.join('tryton', 'version.py'))

dist = setup(name=PACKAGE,
    version=VERSION,
    description='Tryton client',
    author='B2CK',
    author_email='info@b2ck.com',
    url=WEBSITE,
    download_url="http://downloads.tryton.org/" + \
            VERSION.rsplit('.', 1)[0] + '/',
    packages=find_packages(),
    data_files=[
        ('share/pixmaps', glob.glob('share/pixmaps/tryton-icon.png')),
        ('share/pixmaps/tryton', glob.glob('share/pixmaps/tryton/*.png') + \
                glob.glob('share/pixmaps/tryton/*.svg')),
        ('share/locale/cs_CZ/LC_MESSAGES', glob.glob('share/locale/cs_CZ/LC_MESSAGES/*.mo')),
        ('share/locale/de_DE/LC_MESSAGES', glob.glob('share/locale/de_DE/LC_MESSAGES/*.mo')),
        ('share/locale/es_CO/LC_MESSAGES', glob.glob('share/locale/es_CO/LC_MESSAGES/*.mo')),
        ('share/locale/es_ES/LC_MESSAGES', glob.glob('share/locale/es_ES/LC_MESSAGES/*.mo')),
        ('share/locale/fr_FR/LC_MESSAGES', glob.glob('share/locale/fr_FR/LC_MESSAGES/*.mo')),
    ],
    scripts=['bin/tryton'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Natural Language :: French',
        'Natural Language :: German',
        'Natural Language :: Spanish',
        'Programming Language :: Python',
        'Topic :: Office/Business',
    ],
    license=LICENSE,
    install_requires=[
#        "pygtk >= 2.0",
        "egenix-mx-base",
    ],
    extras_require={
        'timezone': ['pytz'],
    },
    **args
)

if os.name == 'nt':
    def find_gtk_dir():
        for directory in os.environ['PATH'].split(';'):
            if not os.path.isdir(directory):
                continue
            for file in ('gtk-demo.exe',):
                if os.path.isfile(os.path.join(directory, file)):
                    return os.path.dirname(directory)
        return None

    if 'py2exe' in dist.commands:
        import shutil
        gtk_dir = find_gtk_dir()

        dist_dir = dist.command_obj['py2exe'].dist_dir

        if os.path.isdir(os.path.join(dist_dir, 'plugins')):
            shutil.rmtree(os.path.join(dist_dir, 'plugins'))
        shutil.copytree(os.path.join(os.path.dirname(__file__), 'tryton', 'plugins'),
            os.path.join(dist_dir, 'plugins'))

        if os.path.isdir(os.path.join(dist_dir, 'etc')):
            shutil.rmtree(os.path.join(dist_dir, 'etc'))
        shutil.copytree(os.path.join(gtk_dir, 'etc'),
            os.path.join(dist_dir, 'etc'))

        if os.path.isdir(os.path.join(dist_dir, 'lib')):
            shutil.rmtree(os.path.join(dist_dir, 'lib'))
        shutil.copytree(os.path.join(gtk_dir, 'lib'),
            os.path.join(dist_dir, 'lib'))

        for lang in ('de', 'es', 'fr'):
            if os.path.isdir(os.path.join(dist_dir, 'share', 'locale', lang)):
                shutil.rmtree(os.path.join(dist_dir, 'share', 'locale', lang))
            shutil.copytree(os.path.join(gtk_dir, 'share', 'locale', lang),
                os.path.join(dist_dir, 'share', 'locale', lang))

        if os.path.isdir(os.path.join(dist_dir, 'share', 'themes', 'MS-Windows')):
            shutil.rmtree(os.path.join(dist_dir, 'share', 'themes', 'MS-Windows'))
        shutil.copytree(os.path.join(gtk_dir, 'share', 'themes', 'MS-Windows'),
            os.path.join(dist_dir, 'share', 'themes', 'MS-Windows'))
