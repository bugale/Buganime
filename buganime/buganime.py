import os
import sys
import tempfile
import datetime
import contextlib
import logging
import re
import dataclasses
import json
import subprocess
import asyncio
import argparse
from typing import Iterator, Any

import win32event

from buganime import transcode


OUTPUT_DIR = os.getenv('BUGANIME_OUTPUT_DIR', '')
UPSCALE_MUTEX_NAME = 'anime4kconvert'

SUPPORTED_SUBTITLE_CODECS = ('ass', 'subrip')


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


def parse_streams(streams: Any, accept_no_subtitles: bool = False) -> transcode.VideoInfo:
    def _get_video_stream() -> Any:
        video_streams = [stream for stream in streams if stream['codec_type'] == 'video']
        if len(video_streams) == 1:
            return video_streams[0]
        for stream in video_streams:
            match stream:
                case {'disposition': {'default': 1}}:
                    return stream
        raise RuntimeError('No default video stream found')

    def _get_audio_stream() -> Any:
        audio_streams = [stream for stream in streams if stream['codec_type'] == 'audio']
        for stream in audio_streams:
            match stream:
                case {'tags': {'language': 'jpn'}}:
                    return stream
        if len(audio_streams) == 1:
            return audio_streams[0]
        raise RuntimeError('No Japanese audio stream found')

    def _get_subtitle_stream_index() -> int:
        subtitle_streams = [stream for stream in streams if stream['codec_type'] == 'subtitle']
        relevant_streams = []
        for i, stream in enumerate(subtitle_streams):
            match stream:
                case {'tags': {'language': str(lang)}} if lang in ('en', 'eng'):
                    if all(x not in stream['tags'].get('title', '').upper() for x in ('S&S', 'SIGNS', 'FORCED')) and \
                       stream['codec_name'].lower() in SUPPORTED_SUBTITLE_CODECS:
                        relevant_streams.append((i, stream))
        if not relevant_streams:
            if len(subtitle_streams) == 1:
                return 0
            raise RuntimeError('No English subtitle stream found')
        if len(relevant_streams) == 1:
            return relevant_streams[0][0]
        return max(relevant_streams, key=lambda x: int(x[1]['tags'].get('NUMBER_OF_BYTES-eng', '0')))[0]

    video = _get_video_stream()
    subtitle_index = None
    try:
        subtitle_index = _get_subtitle_stream_index()
    except RuntimeError:
        if not accept_no_subtitles:
            raise
    return transcode.VideoInfo(audio_index=_get_audio_stream()['index'], subtitle_index=subtitle_index,
                               width=video['width'], height=video['height'], fps=video['r_frame_rate'],
                               frames=int(video.get('tags', {}).get('NUMBER_OF_FRAMES') or video.get('tags', {}).get('NUMBER_OF_FRAMES-eng') or 0))


def parse_filename(input_path: str) -> TVShow | Movie:
    # Remove metadata in brackets/parentheses and extension (e.g. hash, resolution, etc.)
    input_path = os.path.splitext(input_path)[0]
    input_path = re.sub(r'[_\+-\. ]+', ' ', input_path)
    input_path = re.sub(r'\[[^\]]*\]', '', input_path)
    input_path = re.sub(r'\([^\)]*\)', '', input_path)
    input_path = re.sub(r'\d{3,4}p [^\\]*', '', input_path)
    input_path = re.sub(r' *\\ *', r'\\', input_path)
    input_path = input_path.strip(' -')

    # Remove directories
    input_name = os.path.basename(input_path).strip(' ')

    # Special/OVAs are season 0
    if match := re.match(r'^(?P<name>.+?) (?:S(?:eason ?)?\d{1,2} )?(?:Special|SP|OVA|OAV|Picture Drama)(?: E?(?P<episode>\d{1,3})?)?$',
                         input_name):
        return TVShow(name=match.group('name'), season=0, episode=int(match.group('episode') or 1))

    # Formatted standalone TV Shows
    if match := re.match(r'^(?P<name>.+?) S(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?: .*)?$', input_name):
        return TVShow(name=match.group('name'), season=int(match.group('season')), episode=int(match.group('episode')))

    # Structured TV Shows
    dir_re = r'(?P<name>[^\\]+?) S(?:eason ?)?\d{1,2}(?:P\d{1,2})?(?: [^\\]*)?'
    file_re = r'[^\\]*S(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?: [^\\]*)?'
    if match := re.match(fr'^.*\\{dir_re}(?:\\.*)?\\{file_re}$', input_path):
        return TVShow(name=match.group('name'), season=int(match.group('season')), episode=int(match.group('episode')))

    # Other standalone TV Shows
    if match := re.match(r'^(?P<name>.+?) (?:S(?:eason ?)?(?P<season>\d{1,2}) ?)?E?(?P<episode>\d{1,3})(?:v\d+)?(?!.* \d{2}(?: |$).*)(?: .*)?$', input_name):
        return TVShow(name=match.group('name'), season=int(match.group('season') or '1'), episode=int(match.group('episode')))

    return Movie(name=input_name)


def process_file(input_path: str, accept_no_subtitles: bool = False) -> None:
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

    proc = subprocess.run(['ffprobe', '-show_format', '-show_streams', '-of', 'json', input_path], text=True, capture_output=True, check=True,
                          encoding='utf-8')
    logging.info('ffprobe %s wrote %s, %s', str(proc.args), proc.stderr, proc.stdout)
    video_info = parse_streams(json.loads(proc.stdout)['streams'], accept_no_subtitles=accept_no_subtitles)

    try:
        with lock_mutex(name=UPSCALE_MUTEX_NAME):
            logging.info('Running Upscaler')
            asyncio.run(transcode.Transcoder(input_path=input_path, output_path=output_path, height_out=2160, width_out=3840, video_info=video_info).run())
            logging.info('Upscaler for %s finished', input_path)
    except Exception:
        logging.warning('Upscaler for %s failed. Deleting output %s', input_path, output_path)
        try:
            os.unlink(output_path)
        except Exception:
            pass
        raise


def process_path(input_path: str, accept_no_subtitles: bool = False) -> None:
    if os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                try:
                    process_file(input_path=os.path.join(root, file), accept_no_subtitles=accept_no_subtitles)
                except Exception:
                    logging.exception('Failed to convert %s', input_path)
    else:
        process_file(input_path=input_path, accept_no_subtitles=accept_no_subtitles)


def main(args: list[str]) -> int:
    argparser = argparse.ArgumentParser(description='Convert anime files to 4K')
    argparser.add_argument('input_path', type=str, help='Path to the input file or directory')
    argparser.add_argument('--accept-no-subtitles', action='store_true', help='Accept files with no subtitles')
    parsed = argparser.parse_args(args)

    input_path = parsed.input_path
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
    handler_file = logging.FileHandler(log_file.name, encoding='utf-8')
    handler_file.setLevel(logging.DEBUG)
    handler_file.setFormatter(formatter)
    root.addHandler(handler_file)

    logging.info('Buganime started running on %s', input_path)
    try:
        process_path(input_path=input_path, accept_no_subtitles=parsed.accept_no_subtitles)
        return 0
    except Exception:
        logging.exception('Failed to convert %s', input_path)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
