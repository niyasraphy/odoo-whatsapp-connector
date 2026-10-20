"""Build the extension for each browser: dist/<browser>/ to load unpacked, and
dist/om-whatsapp-connector-<browser>-<version>.zip for the store.

    python3 build.py            # chrome and firefox
    python3 build.py firefox
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / 'src'
DIST = ROOT / 'dist'

BROWSERS = {
    'chrome': {
        'background': {'service_worker': 'background.js'},
    },
    'firefox': {
        'background': {'scripts': ['origins.js', 'background.js']},
        'browser_specific_settings': {
            'gecko': {
                'id': 'whatsapp-connector@odoomates.com', 'strict_min_version': '140.0',
                # the messages go to the Odoo of the user, which Mozilla counts as collected
                'data_collection_permissions': {'required': ['personalCommunications']},
            },
            # the data collection key needs Firefox for Android 142; desktop keeps 140 (ESR)
            'gecko_android': {'strict_min_version': '142.0'},
        },
    },
}


def build(browser):
    manifest = json.loads((SRC / 'manifest.json').read_text())
    manifest.update(BROWSERS[browser])
    target = DIST / browser
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(SRC, target, ignore=shutil.ignore_patterns('manifest.json'))
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=4) + '\n')
    archive = DIST / f"om-whatsapp-connector-{browser}-{manifest['version']}.zip"
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for path in sorted(target.rglob('*')):
            if path.is_file():
                zip_file.write(path, path.relative_to(target))
    print(f'{browser}: {target.relative_to(ROOT)}, {archive.relative_to(ROOT)}')


if __name__ == '__main__':
    for name in sys.argv[1:] or BROWSERS:
        build(name)
