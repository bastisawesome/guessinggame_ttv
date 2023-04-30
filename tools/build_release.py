import os
import sys
import subprocess
import pathlib
import shutil


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

    dist_path = pathlib.Path('dist/')

    # 1. Run Pyinstaller to build the application
    print('Building GuessingGame_TTV...')

    subprocess.run([
        'pyinstaller',
        '--noconfirm',
        '--clean',
        '--log-level', 'WARN',
        'guessinggame_ttv.spec'],
        check=True)

    print('Building done, preparing assets for packaging.')
    # 2. Bundle extra application data such as the `templates/` and the readme

    # Prepare the directory to be compressed and archived
    ggttv_path = pathlib.Path('dist/guessinggame_ttv/')
    ggttv_path.mkdir(exist_ok=True)

    shutil.move(dist_path / 'guessinggame_ttv')

    # 3. Generate platform-specific compressed archives for distribution


if __name__ == '__main__':
    main()
