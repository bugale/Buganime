import json
import contextlib
import os
import tempfile
import sys
import asyncio
import subprocess
import logging
from typing import AsyncIterator, cast, Optional

import retry
import torch
import cv2
import requests
from tqdm import tqdm


MODEL_URL = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth'
MODEL_PATH = os.path.join(tempfile.gettempdir(), 'realesr-animevideov3.pth')
FFMPEG_OUTPUT_ARGS = ('-vcodec', 'libx265', '-pix_fmt', 'yuv420p')


class Transcoder:
    class Module(torch.nn.Module):
        def __init__(self, num_in_ch: int = 3, num_out_ch: int = 3, num_feat: int = 64, num_conv: int = 16, upscale: int = 4):
            super().__init__()
            self.__upsampler = torch.nn.PixelShuffle(upscale)
            self.body = torch.nn.ModuleList(
                [torch.nn.Conv2d(num_in_ch, num_feat, 3, 1, 1), torch.nn.PReLU(num_parameters=num_feat)] +
                sum(([torch.nn.Conv2d(num_feat, num_feat, 3, 1, 1), torch.nn.PReLU(num_parameters=num_feat)] for _ in range(num_conv)), []) +
                [torch.nn.Conv2d(num_feat, num_out_ch * upscale * upscale, 3, 1, 1)])

        def forward(self, tensor: torch.Tensor) -> torch.Tensor:
            base = torch.nn.functional.interpolate(tensor, scale_factor=self.__upsampler.upscale_factor, mode='nearest')
            for body in self.body:
                tensor = body(tensor)
            return cast(torch.Tensor, self.__upsampler(tensor) + base)

    def __init__(self, input_path: str, output_path: str, height_out: int) -> None:
        if not os.path.isfile(MODEL_PATH):
            with open(MODEL_PATH, 'wb') as file:
                file.write(requests.get(MODEL_URL, timeout=600).content)
        self.__input_path, self.__output_path = input_path, output_path
        self.__parse_input_streams()
        self.__height_out = height_out
        self.__width_out = int(self.__width * self.__height_out / self.__height)
        model = Transcoder.Module(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=16, upscale=4)
        model.load_state_dict(torch.load(MODEL_PATH)['params'], strict=True)
        self.__model = model.eval().cuda().half()
        self.__gpu_lock: Optional[asyncio.Lock] = None
        self.__frame_tasks_queue: Optional[asyncio.Queue[Optional[asyncio.Task[bytes]]]] = None

    def __parse_input_streams(self) -> None:
        current_subtitle_index = 0
        video, self.__audio_index, self.__subtitle_index = None, None, None
        proc = subprocess.run(['ffprobe', '-show_format', '-show_streams', '-of', 'json', self.__input_path], text=True, capture_output=True, check=True)
        logging.info('ffprobe %s wrote %s', str(proc.args), proc.stderr)
        for stream in json.loads(proc.stdout)['streams']:
            match stream:
                case {'codec_type': 'video', 'disposition': {'default': 1}}:
                    video = stream
                case {'codec_type': 'audio', 'tags': {'language': 'jpn'}}:
                    self.__audio_index = stream['index']
                case {'codec_type': 'subtitle', 'tags': {'language': 'eng', 'title': str(title)}} if 'S&S' not in title.upper():
                    self.__subtitle_index = current_subtitle_index
                    current_subtitle_index += 1
                case {'codec_type': 'subtitle'}:
                    current_subtitle_index += 1
        assert video is not None
        assert self.__audio_index is not None
        assert self.__subtitle_index is not None
        self.__width, self.__height, self.__fps = video['width'], video['height'], video['r_frame_rate']
        self.__frames = int(video['tags'].get('NUMBER_OF_FRAMES') or video['tags'].get('NUMBER_OF_FRAMES-eng') or 0)

    async def __read_input_frames(self) -> AsyncIterator[bytes]:
        args = ('-i', self.__input_path,
                '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:',
                '-loglevel', 'warning')
        proc = await asyncio.subprocess.create_subprocess_exec('ffmpeg', *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        assert proc.stdout
        assert proc.stderr
        try:
            frame_length = self.__width * self.__height * 3
            with contextlib.suppress(asyncio.IncompleteReadError):
                while True:
                    yield await proc.stdout.readexactly(frame_length)
        finally:
            with contextlib.suppress(ProcessLookupError):
                proc.terminate()
            logging.info('ffmpeg input: %s', str(await proc.stderr.read()))
            await proc.wait()

    async def __write_output_frames(self, frames: AsyncIterator[bytes]) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            os.link(self.__input_path, os.path.join(temp_dir, 'input.mkv'))
            args = ('-f', 'rawvideo', '-framerate', str(self.__fps), '-pix_fmt', 'rgb24', '-s', f'{self.__width_out}x{self.__height_out}', '-i', 'pipe:',
                    '-i', 'input.mkv',
                    '-map', '0', '-map', f'1:{self.__audio_index}', '-vf', f'subtitles=input.mkv:si={self.__subtitle_index}',
                    *FFMPEG_OUTPUT_ARGS, self.__output_path,
                    '-loglevel', 'warning', '-y')
            proc = await asyncio.subprocess.create_subprocess_exec('ffmpeg', *args, stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                                                                   stdout=asyncio.subprocess.PIPE, cwd=temp_dir)
            assert proc.stdin
            assert proc.stdout
            assert proc.stderr
            pbar: 'tqdm[None]' = tqdm(total=self.__frames, unit='frame', desc='transcoding')
            try:
                async for frame in frames:
                    proc.stdin.write(frame)
                    await proc.stdin.drain()
                    pbar.update(1)
            finally:
                proc.stdin.close()
                logging.info('ffmpeg output: %s%s', str(await proc.stdout.read()), str(await proc.stderr.read()))
                await proc.wait()

    @retry.retry(RuntimeError, tries=10, delay=1)
    def __gpu_upscale(self, frame: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            frame_float = frame.cuda().permute(2, 0, 1).half() / 255
            frame_upscaled_float = cast(torch.Tensor, self.__model(frame_float.unsqueeze(0)).data).squeeze().clamp_(0, 1)
            return (frame_upscaled_float * 255.0).round().byte().permute(1, 2, 0).cpu()

    async def __upscale_frame(self, frame: bytes) -> bytes:
        if self.__height == self.__height_out:
            return frame
        with torch.no_grad():
            frame_arr = torch.frombuffer(frame, dtype=torch.uint8).reshape([self.__height, self.__width, 3])
        assert self.__gpu_lock
        async with self.__gpu_lock:
            frame_cpu = await asyncio.to_thread(self.__gpu_upscale, frame_arr)
        return cast(bytes, await asyncio.to_thread(
            lambda: cv2.resize(frame_cpu.numpy(), (self.__width_out, self.__height_out), interpolation=cv2.INTER_LANCZOS4).tobytes()))

    async def __generate_upscaling_tasks(self) -> None:
        assert self.__frame_tasks_queue
        async for frame in self.__read_input_frames():
            await self.__frame_tasks_queue.put(asyncio.create_task(self.__upscale_frame(frame)))
        await self.__frame_tasks_queue.put(None)

    async def __get_output_frames(self) -> AsyncIterator[bytes]:
        assert self.__frame_tasks_queue
        while True:
            frame = await self.__frame_tasks_queue.get()
            if frame is None:
                break
            yield await frame

    async def run(self) -> None:
        self.__gpu_lock = asyncio.Lock()
        self.__frame_tasks_queue = asyncio.Queue(maxsize=10)
        gen_task = asyncio.create_task(self.__generate_upscaling_tasks())
        await self.__write_output_frames(self.__get_output_frames())
        await gen_task


def main(args: list[str]) -> int:
    if len(args) != 2:
        print("Usage: transcode.py <input_path> <output_path>")
        return 1

    asyncio.run(Transcoder(input_path=args[0], output_path=args[1], height_out=2160).run())
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
