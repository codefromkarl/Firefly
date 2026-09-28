"""Assemble local still frames with an uncut, unretimed self-recorded audio track."""
from __future__ import annotations

import hashlib
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION

from .store import ControlError, canonical, digest, utc_now

VERSION = 'creator-video-1'
AUDIO_SUFFIXES = {'.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.opus', '.aiff', '.aif', '.wma', '.webm', '.mp4'}
FORMATS = 'wav,mp3,mov,aac,flac,ogg,aiff,asf,matroska,webm'
OUTPUTS = ('video.mp4', 'timeline.json', 'subtitles.srt', 'poster.jpg')


def _local(path, *, exists=True):
    value = str(path)
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*://', value):
        raise ControlError('Only ordinary local files/directories are accepted')
    result = Path(os.path.abspath(os.path.expanduser(value)))
    for candidate in (result, *result.parents):
        if candidate.is_symlink():
            raise ControlError('Symlink paths are not accepted for video assembly')
    if exists and not result.is_file():
        raise ControlError('Expected an ordinary local input file')
    return result


def _hash_file(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def _run(argv, timeout=120):
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ControlError(f'Video tool unavailable or timed out: {Path(argv[0]).name}') from error
    if result.returncode:
        raise ControlError(f'{Path(argv[0]).name} failed: ' + result.stderr.decode('utf8', errors='replace')[-1200:])
    return result.stdout


def _probe(path, *, audio_input=False):
    tool = shutil.which('ffprobe')
    if not tool:
        raise ControlError('ffprobe is required; no automatic installation')
    args = [tool, '-v', 'error', '-protocol_whitelist', 'file,pipe']
    if audio_input:
        args += ['-format_whitelist', FORMATS]
    args += ['-show_entries', 'format=duration,format_name:stream=index,codec_type,codec_name,duration,start_time,sample_rate,channels,width,height,pix_fmt,r_frame_rate', '-of', 'json', str(path)]
    try:
        return json.loads(_run(args, timeout=60))
    except (ValueError, KeyError) as error:
        raise ControlError('ffprobe returned invalid metadata') from error


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ControlError(f'{label} must be finite numeric seconds')
    return float(value)


def probe_audio(path):
    path = _local(path)
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        raise ControlError('Unsupported local audio format')
    metadata = _probe(path, audio_input=True)
    streams = [s for s in metadata.get('streams', []) if s.get('codec_type') == 'audio']
    if len(streams) != 1:
        raise ControlError('Audio input must contain exactly one unambiguous audio stream')
    stream = streams[0]
    try:
        duration = float(stream.get('duration', metadata['format']['duration']))
        start = float(stream.get('start_time', 0))
    except (KeyError, ValueError, TypeError) as error:
        raise ControlError('Audio duration/start time unavailable') from error
    if not math.isfinite(duration) or not 0 < duration <= 24 * 3600 or not math.isfinite(start):
        raise ControlError('Audio duration must be finite, positive and at most 24 hours')
    if abs(start) > 0.1:
        raise ControlError('Nonzero audio start requires explicit source normalization; no automatic trimming')
    return {'duration': duration, 'start_time': start, 'codec': stream.get('codec_name'),
            'sample_rate': int(stream.get('sample_rate', 0)), 'channels': stream.get('channels'),
            'sha256': _hash_file(path), 'bytes': path.stat().st_size}


def resolve_timeline(manifest, audio_duration, *, preview=False):
    duration = _number(audio_duration, 'audio_duration')
    scenes = manifest.get('scenes')
    if duration <= 0 or not isinstance(scenes, list) or not scenes:
        raise ControlError('Positive audio duration and nonempty scenes are required')
    if any(not isinstance(scene, dict) for scene in scenes):
        raise ControlError('Every scene must be an object')
    if len(scenes) > 500:
        raise ControlError('At most 500 scenes are supported')
    ids = [s.get('id') for s in scenes]
    if not all(isinstance(x, str) and x for x in ids) or len(set(ids)) != len(ids):
        raise ControlError('Scene IDs must be nonempty and unique')
    for scene in scenes:
        if not isinstance(scene.get('narration', ''), str) or len(scene.get('narration', '')) > 20000:
            raise ControlError('Narration must be text of at most 20000 characters per scene')
    absent = all('start' not in s and 'end' not in s for s in scenes)
    timing = 'explicit'
    if absent:
        if not preview:
            raise ControlError('Production requires explicit scene timings, not only a confirmation flag')
        timing = 'estimated'
        weights = [max(1, len(s.get('narration', '').strip())) for s in scenes]
        total = sum(weights)
        cumulative = 0
        resolved = []
        for scene, weight in zip(scenes, weights):
            start = duration * cumulative / total
            cumulative += weight
            resolved.append({**scene, 'start': start, 'end': duration * cumulative / total})
    else:
        if any('start' not in s or 'end' not in s for s in scenes):
            raise ControlError('Partial scene timings are not accepted')
        resolved = [dict(s) for s in scenes]
    if not preview and manifest.get('timing_confirmed') is not True:
        raise ControlError('Production requires timing_confirmed=true and explicit reviewed timings')
    previous = 0.0
    for scene in resolved:
        start, end = _number(scene['start'], 'scene start'), _number(scene['end'], 'scene end')
        if abs(start - previous) > 0.001 or end <= start or end > duration + 0.001:
            raise ControlError('Timeline must be continuous, positive, nonoverlapping and within the full audio')
        scene['start'], scene['end'] = start, end
        previous = end
    if abs(previous - duration) > 0.001:
        raise ControlError('Final scene must cover the full audio duration; audio is never silently cut')
    return {'timing': timing, 'timing_confirmed': manifest.get('timing_confirmed') is True,
            'audio_duration': duration, 'scenes': resolved}


def _srt_time(seconds):
    milliseconds = round(seconds * 1000)
    hours, rest = divmod(milliseconds, 3600000)
    minutes, rest = divmod(rest, 60000)
    seconds, milliseconds = divmod(rest, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'


def _subtitles(scenes):
    cues, split_estimated = [], False
    for scene in scenes:
        text = re.sub(r'\s+', ' ', scene.get('narration', '')).strip()
        if not text:
            continue
        chunks = [text[i:i + 36] for i in range(0, len(text), 36)]
        blocks = ['\n'.join(chunks[i:i + 2]) for i in range(0, len(chunks), 2)]
        split_estimated |= len(blocks) > 1
        length = scene['end'] - scene['start']
        if length / len(blocks) < 0.01:
            raise ControlError('Narration too dense for nonzero subtitle cues; split/re-time scenes')
        for index, block in enumerate(blocks):
            start = scene['start'] + length * index / len(blocks)
            end = scene['start'] + length * (index + 1) / len(blocks)
            cues.append(f'{len(cues)+1}\n{_srt_time(start)} --> {_srt_time(end)}\n{block}\n')
    return '\n'.join(cues), 'estimated_segments_within_scenes' if split_estimated else 'scene_level_not_word_alignment'


def _font_path():
    return next((p for p in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') if Path(p).is_file()), None)


def _watermark(image, text, font_path):
    result = image.convert('RGB').copy()
    draw = ImageDraw.Draw(result)
    size = max(12, round(result.height * 0.029))
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    band = max(30, round(result.height * 0.065))
    draw.rectangle((0, 0, result.width, band), fill=(30, 30, 30))
    draw.text((max(8, result.width // 50), max(4, band // 7)), text, font=font, fill=(255, 220, 100))
    return result


def assemble_video(frames_manifest_path, output_dir, *, preview=False):
    manifest_path = _local(frames_manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text())
    except (ValueError, OSError) as error:
        raise ControlError('Invalid frames manifest') from error
    if not isinstance(manifest, dict) or manifest.get('schema') != 1:
        raise ControlError('Unsupported frames manifest schema')
    audio_spec = manifest.get('audio')
    if not isinstance(audio_spec, dict) or not audio_spec.get('path'):
        return {'status': 'missing_audio', 'preview': preview, 'video_created': False,
                'message': 'Supply your recorded local audio; no substitute voice was generated'}
    if not isinstance(audio_spec['path'], str):
        raise ControlError('Audio path must be a local filename string')
    audio_path = _local(manifest_path.parent / audio_spec['path'])
    if manifest.get('demo_audio') is True and not preview:
        raise ControlError('Demo/test audio may only be assembled as a watermarked preview')
    audio = probe_audio(audio_path)
    timeline = resolve_timeline(manifest, audio['duration'], preview=preview)
    width, height, fps = manifest.get('width', 1920), manifest.get('height', 1080), manifest.get('fps', 30)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (width, height, fps)) or width < 64 or height < 64 or width > 7680 or height > 4320 or width % 2 or height % 2 or not 1 <= fps <= 60:
        raise ControlError('Video requires even dimensions 64..7680 × 64..4320 and integer fps 1..60')
    if any(scene['end'] - scene['start'] < 1 / fps - 0.000001 for scene in timeline['scenes']):
        raise ControlError('Each scene must span at least one output video frame')
    image_paths, hashes = [], []
    for scene in timeline['scenes']:
        if not isinstance(scene.get('image'), str):
            raise ControlError('Every scene needs a local PNG image')
        path = _local(manifest_path.parent / scene['image'])
        if path.suffix.lower() != '.png':
            raise ControlError('Scene images must be PNG')
        try:
            with Image.open(path) as image:
                if image.format != 'PNG' or image.size != (width, height):
                    raise ControlError('All scene dimensions must exactly match manifest width and height')
                image.verify()
        except ControlError:
            raise
        except (OSError, ValueError) as error:
            raise ControlError('Unreadable scene image') from error
        image_paths.append(path)
        hashes.append(_hash_file(path))
    tool = shutil.which('ffmpeg')
    if not tool:
        raise ControlError('ffmpeg is required; no automatic installation')
    version = _run([tool, '-version'], timeout=10).decode().splitlines()[0]
    implementation_sha = _hash_file(Path(__file__))
    font_path = _font_path() if preview else None
    font_sha = _hash_file(font_path) if font_path else None
    fingerprint = digest(canonical({'version': VERSION, 'implementation_sha256': implementation_sha,
                                    'watermark_font_sha256': font_sha, 'pillow_version': PILLOW_VERSION, 'manifest': manifest, 'audio_sha256': audio['sha256'],
                                    'images_sha256': hashes, 'preview': preview, 'ffmpeg': version}).encode())
    output = _local(output_dir, exists=False)
    project = Path(__file__).resolve().parents[2]
    if output.is_relative_to(project) and not output.is_relative_to(project / '.local'):
        raise ControlError('Project video artifacts must stay under .local, never src/public/docs')
    if output.exists():
        report_path = _local(output / 'build-report.json')
        try:
            report = json.loads(report_path.read_text())
        except (ValueError, OSError) as error:
            raise ControlError('Existing output directory is not an intact owned video package') from error
        if report.get('tool') != VERSION or report.get('input_digest') != fingerprint or report.get('status') != 'assembled':
            raise ControlError('Output exists for different inputs; choose a new version directory')
        if set(report.get('hashes', {})) != set(OUTPUTS):
            raise ControlError('Incomplete video cache report')
        for name in OUTPUTS:
            if _hash_file(_local(output / name)) != report['hashes'][name]:
                raise ControlError('Existing video output was modified; refusing overwrite')
        return {**report, 'cache_hit': True}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.creator-video-', dir=output.parent) as tmp:
        work = Path(tmp)
        audio_copy = work / ('input-audio' + audio_path.suffix.lower())
        shutil.copyfile(audio_path, audio_copy)
        if _hash_file(audio_copy) != audio['sha256']:
            raise ControlError('Audio changed during assembly')
        concat = ['ffconcat version 1.0']
        watermark = ('预览 · 测试音频' if manifest.get('demo_audio') else '预览 · 时间轴待确认') if preview else None
        for index, (scene, path, sha) in enumerate(zip(timeline['scenes'], image_paths, hashes)):
            if _hash_file(path) != sha:
                raise ControlError('Image changed during assembly')
            captured = work / f'original-{index:04}.png'
            shutil.copyfile(path, captured)
            if _hash_file(captured) != sha:
                raise ControlError('Image changed during capture')
            target = work / f'frame-{index:04}.png'
            with Image.open(captured) as image:
                frame = _watermark(image, watermark, font_path) if watermark else image.convert('RGB')
                frame.save(target)
                if index == 0:
                    frame.save(work / 'poster.jpg', quality=92)
            concat += [f"file '{target.name}'", f'option framerate {fps}', f"duration {scene['end']-scene['start']:.9f}"]
        concat.extend([f"file 'frame-{len(image_paths)-1:04}.png'", f'option framerate {fps}'])
        (work / 'frames.ffconcat').write_text('\n'.join(concat) + '\n')
        srt, subtitle_timing = _subtitles(timeline['scenes'])
        (work / 'subtitles.srt').write_text(srt)
        (work / 'timeline.json').write_text(json.dumps({**timeline, 'subtitle_timing': subtitle_timing}, ensure_ascii=False, indent=2))
        # safe=0 enables per-file framerate; concat text contains only our generated basenames.
        args = [tool, '-hide_banner', '-loglevel', 'error', '-nostdin', '-threads', '2', '-filter_threads', '2',
                '-protocol_whitelist', 'file,pipe', '-f', 'concat', '-safe', '0', '-i', str(work / 'frames.ffconcat'),
                '-protocol_whitelist', 'file,pipe', '-format_whitelist', FORMATS, '-i', str(audio_copy),
                '-map', '0:v:0', '-map', '1:a:0', '-map_metadata', '-1',
                '-map_metadata:s:v', '-1', '-map_metadata:s:a', '-1', '-map_chapters', '-1', '-c:v', 'libx264', '-threads:v', '2', '-preset', 'medium',
                '-crf', '20', '-pix_fmt', 'yuv420p', '-vf', f'fps={fps},tpad=stop_mode=clone:stop_duration=1,trim=end_frame={math.ceil(audio["duration"] * fps)},setpts=PTS-STARTPTS', '-r', str(fps), '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
                '-movflags', '+faststart', str(work / 'video.mp4')]
        _run(args, timeout=max(120, min(7200, audio['duration'] * 5)))
        metadata = _probe(work / 'video.mp4')
        video_stream = next((s for s in metadata.get('streams', []) if s.get('codec_type') == 'video'), {})
        sound_stream = next((s for s in metadata.get('streams', []) if s.get('codec_type') == 'audio'), {})
        if video_stream.get('codec_name') != 'h264' or video_stream.get('pix_fmt') != 'yuv420p' or sound_stream.get('codec_name') != 'aac' or sound_stream.get('sample_rate') != '48000' or sound_stream.get('channels') != 2:
            raise ControlError('Output codec verification failed')
        if video_stream.get('width') != width or video_stream.get('height') != height or Fraction(video_stream.get('r_frame_rate', '0')) != fps:
            raise ControlError('Output dimensions/frame-rate verification failed')
        vd, ad = float(video_stream.get('duration', 0)), float(sound_stream.get('duration', 0))
        tolerance = max(0.1, 2 / fps)
        if min(vd, ad) < audio['duration'] - 0.03 or abs(vd - audio['duration']) > tolerance or abs(ad - audio['duration']) > tolerance or abs(float(video_stream.get('start_time', 0))) > tolerance or abs(float(sound_stream.get('start_time', 0))) > tolerance:
            raise ControlError(f'Output coverage failed: input={audio["duration"]}, video={vd}, audio={ad}, starts={video_stream.get("start_time")}/{sound_stream.get("start_time")}')
        if _hash_file(audio_path) != audio['sha256'] or any(_hash_file(path) != sha for path, sha in zip(image_paths, hashes)) or json.loads(manifest_path.read_text()) != manifest:
            raise ControlError('Inputs changed during rendering; choose an unchanged input revision')
        report = {'tool': VERSION, 'status': 'assembled', 'preview': preview, 'demo_audio': manifest.get('demo_audio') is True,
                  'input_digest': fingerprint, 'implementation_sha256': implementation_sha,
                  'watermark_font_sha256': font_sha, 'pillow_version': PILLOW_VERSION, 'input_metadata_copied': False, 'created_at': utc_now(), 'ffmpeg': version, 'cache_hit': False,
                  'audio': audio, 'timing': timeline['timing'], 'timing_confirmed': timeline['timing_confirmed'],
                  'subtitle_timing': subtitle_timing, 'subtitles_burned_in': False, 'watermark': watermark,
                  'width': width, 'height': height, 'fps': fps, 'audio_uncut_unretimed': True,
                  'output_audio_duration': ad, 'output_video_duration': vd, 'platform_uploaded': False,
                  'hashes': {name: _hash_file(work / name) for name in OUTPUTS}}
        (work / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        # Publish only the verified final package, never inputs or temporary concat files.
        package = work / 'package'; package.mkdir()
        for name in (*OUTPUTS, 'build-report.json'):
            shutil.move(str(work / name), package / name)
        if output.exists():
            raise ControlError('Output appeared during assembly; refusing overwrite')
        os.rename(package, output)
        return report
