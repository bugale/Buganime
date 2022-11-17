import os
import sys
import tempfile
import datetime
import contextlib
import logging
import re
import dataclasses
from typing import Iterator

import win32event

from buganime import transcode


OUTPUT_DIR = os.getenv('BUGANIME_OUTPUT_DIR', '')
UPSCALE_MUTEX_NAME = 'anime4kconvert'


@contextlib.contextmanager
def lock_mutex(name: str) -> Iterator[None]:
    mutex = win32event.CreateMutex(None, 1, name)
    try:
        win32event.WaitForSingleObject(mutex, -1)
        yield
    finally:
        mutex.close()


@dataclasses.dataclass
class TVShow:
    name: str
    season: int
    episode: int


@dataclasses.dataclass
class Movie:
    name: str


def parse_filename(input_path: str) -> TVShow | Movie:
    # Remove metadata in brackets/parentheses and extension (e.g. hash, resolution, etc.)
    input_path = input_path.replace('_', ' ')
    input_path = re.sub(r'\[[^\]]*\]', '', input_path)
    input_path = re.sub(r'\([^\)]*\)', '', input_path)
    input_path = re.sub(r'\d{3,4}p[ -][^\\]*', '', input_path)
    input_path = os.path.splitext(input_path)[0].strip(' -')

    # Remove extension and directories
    input_name = os.path.basename(input_path).strip(' -')

    # Special/OVAs are season 0
    if match := re.match(r'^(?P<name>.+?)[ -]+(?:S(?:eason ?)?\d{1,2}[ -]+)?(?:Special|SP|OVA|OAV|Picture Drama)(?:[ -]+E?(?P<episode>\d{1,3})?)?$',
                         input_name):
        return TVShow(name=match.group('name'), season=0, episode=int(match.group('episode') or 1))

    # Other standalone TV Shows
    if match := re.match(r'^(?P<name>.+?)[ -]+(?:S(?:eason ?)?(?P<season>\d{1,2})[ -]*)?E?(?P<episode>\d{1,3})(?:v\d+)?$', input_name):
        return TVShow(name=match.group('name'), season=int(match.group('season') or '1'), episode=int(match.group('episode')))

    # Structured TV Shows
    dir_re = r'(?P<name>[^\\]+?)[ -]+S(?:eason ?)?(?P<season>\d{1,2})[ -][^\\]*'
    file_re = r'[^\\]*S\d{1,2}?E(?P<episode>\d{1,3})(?:[ -][^\\]*)?'
    if match := re.match(fr'^.*\\{dir_re}\\{file_re}$', input_path):
        return TVShow(name=match.group('name'), season=int(match.group('season')), episode=int(match.group('episode')))

    return Movie(name=input_name)


def process_file(input_path: str) -> None:
    if not input_path.endswith('.mkv'):
        return

    logging.info('Converting %s', input_path)

    # Put in the correct path
    parsed = parse_filename(input_path=input_path)
    if isinstance(parsed, TVShow):
        output_path = os.path.join(OUTPUT_DIR, 'TV Shows', parsed.name, f'{parsed.name} S{parsed.season:02d}E{parsed.episode:02d}.mkv')
    else:
        output_path = os.path.join(OUTPUT_DIR, 'Movies', f'{parsed.name}.mkv')
    if not os.path.isdir(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))

    logging.info('Output is %s', output_path)

    try:
        with lock_mutex(name=UPSCALE_MUTEX_NAME):
            logging.info('Running Upscaler')
            transcode.main([input_path, output_path])
            logging.info('Upscaler for %s finished', input_path)
    except Exception:
        logging.exception('Failed to convert %s', input_path)


def process_path(input_path: str) -> None:
    if os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                process_file(input_path=os.path.join(root, file))
    else:
        process_file(input_path=input_path)


def main(args: list[str]) -> int:
    if len(args) != 1:
        print("Usage: buganime.py <input_path>")
        return 1

    input_path = args[0]
    log_prefix = f'buganime_{os.path.basename(input_path)}_{datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")}'
    with tempfile.NamedTemporaryFile(mode='w', prefix=log_prefix, suffix='.txt', delete=False) as log_file:
        pass
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler_stream = logging.StreamHandler(sys.stdout)
    handler_stream.setLevel(logging.DEBUG)
    handler_stream.setFormatter(formatter)
    root.addHandler(handler_stream)
    handler_file = logging.FileHandler(log_file.name)
    handler_file.setLevel(logging.DEBUG)
    handler_file.setFormatter(formatter)
    root.addHandler(handler_file)

    logging.info('Buganime started running on %s', input_path)
    try:
        process_path(input_path=input_path)
        return 0
    except Exception:
        logging.exception('Failed to convert %s', input_path)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
