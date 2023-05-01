import os
import sys
import subprocess
import pathlib
import shutil
import zipfile
import tarfile


# Annoying and stupid globals to ease life in per-platform archiving.
DIST_PATH = pathlib.Path('dist')
TEMPLATES_PATH = pathlib.Path('templates')


def check_virtual_env() -> bool:
    return os.environ.get('PIPENV_ACTIVE', None) == '1'


def main() -> None:
    if not check_virtual_env():
        msg = '''This script can only be run with Pipenv.
You can run the script in one of two ways:
1. Directly through Pipenv:
\t$ pipenv run build_release
2. After activating a Pipenv shell:
\t$ pipenv shell
\t (guessinggame_ttv) $ python tools/build_release.py'''
        print(msg)
        sys.exit(1)

    print('Building GuessingGame_TTV...')

    subprocess.run([
        'pyinstaller',
        '--noconfirm',
        '--clean',
        '--log-level', 'WARN',
        'guessinggame_ttv.spec'],
        check=True)

    print('Building done, preparing assets for packaging.')


if __name__ == '__main__':
    main()
