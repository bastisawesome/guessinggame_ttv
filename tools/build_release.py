import os
import sys
import subprocess
import pathlib
import zipfile
import tarfile
from guessinggame_ttv._version import version

# Annoying and stupid globals to ease life in per-platform archiving.
DIST_PATH = pathlib.Path('dist')
TEMPLATES_PATH = pathlib.Path('templates')
NIX_BINARY_NAME = 'guessinggame_ttv'
WINDOWS_BINARY_NAME = 'guessinggame_ttv.exe'


def check_virtual_env() -> bool:
    return os.environ.get('PIPENV_ACTIVE', None) == '1'


def get_os_and_arch() -> str:
    os_and_arch = ''
    os = ''
    arch = ''
    if '--os' in sys.argv:
        os = sys.argv[sys.argv.index('--os')+1]

    if '--arch' in sys.argv:
        arch = sys.argv[sys.argv.index('--arch')+1]

    if os:
        os_and_arch += f'{os}{"-" if arch else ""}'
    if arch:
        os_and_arch += arch

    return os_and_arch or 'unknown'


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

    os_and_arch = get_os_and_arch()

    subprocess.run([
        'pyinstaller',
        '--noconfirm',
        '--clean',
        '--log-level', 'WARN',
        'guessinggame_ttv.spec'],
        check=True)

    print('Building done, archiving application')

    if sys.platform.startswith('linux'):
        build_linux(os_and_arch)
    elif sys.platform.startswith('darwin'):
        build_macos(os_and_arch)
    elif sys.platform.startswith('win32'):
        build_windows(os_and_arch)
    else:
        print('Unsupported operating system. Feel free to make a pull request'
              'to add more supported platforms.')
        sys.exit(1)

    print('Archive created in `dist`')


def build_linux(os_and_arch: str) -> None:
    write_tarball(NIX_BINARY_NAME, os_and_arch)


def build_macos(os_and_arch: str) -> None:
    # In case of future differences, this build function will remain separate
    # from the Linux build function, despite both doing the same things.
    write_tarball(NIX_BINARY_NAME, os_and_arch)


def write_tarball(bin_name: str, os_and_arch: str) -> None:
    # 1. Add the executable to the tarball
    # 2. Add templates directory to the tarball
    # 3. Add readme to the tarball
    executable_path = DIST_PATH / bin_name
    readme_path = pathlib.Path('README.md')

    with tarfile.open(
            name=DIST_PATH / f'guessinggame_ttv-{version}-{os_and_arch}.tar.gz',
            mode='w:gz') as out_arc:
        out_arc.add(executable_path,
                    arcname=f'guessinggame_ttv/{bin_name}')
        out_arc.add(readme_path,
                    arcname=f'guessinggame_ttv/{readme_path}')
        out_arc.add(TEMPLATES_PATH,
                    arcname=f'guessinggame_ttv/{TEMPLATES_PATH}')


def build_windows(os_and_arch: str):
    executable_path = DIST_PATH / WINDOWS_BINARY_NAME
    readme_path = pathlib.Path('README.md')

    with zipfile.ZipFile(
            file=DIST_PATH / f'guessinggame_ttv-{version}-{os_and_arch}.zip',
            mode='w',
            compression=zipfile.ZIP_DEFLATED) as out_arc:
        out_arc.write(executable_path,
                      arcname=f'guessinggame_ttv/{WINDOWS_BINARY_NAME}')
        out_arc.write(readme_path,
                      arcname=f'guessinggame_ttv/{readme_path}')
        out_arc.write(TEMPLATES_PATH,
                      arcname=f'guessinggame_ttv/{TEMPLATES_PATH}')


if __name__ == '__main__':
    main()
