from setuptools import setup

APP = ['zenbreak/app.py']
DATA_FILES = [
    ('assets', ['assets/menubar-icon.png', 'assets/menubar-icon.svg']),
    ('assets/sounds', []),
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': 'ZenBreak',
        'CFBundleDisplayName': 'ZenBreak',
        'CFBundleIdentifier': 'com.zenbreak.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # menu bar app, no dock icon
        'NSHumanReadableCopyright': 'Copyright 2026 Lei Chen. MIT License.',
    },
    'packages': ['zenbreak'],
    'includes': [
        'rumps',
        'AppKit',
        'Foundation',
        'Quartz',
        'WebKit',
        'objc',
    ],
}

setup(
    app=APP,
    name='ZenBreak',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
