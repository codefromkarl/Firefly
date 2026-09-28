"""Join ordered self-recorded local clips without trimming, speed changes or crossfades."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import wave

from .store import ControlError, canonical, digest, utc_now
from . import video

VERSION = 'creator-audio-join-1'


def join_recordings(clips_manifest_path, output_dir):
    manifest_path = video._local(clips_manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as error:
        raise ControlError('Invalid recording clips manifest') from error
    clips = manifest.get('clips') if isinstance(manifest, dict) else None
    if not isinstance(manifest, dict) or manifest.get('schema') != 1 or not isinstance(clips, list) or not 1 <= len(clips) <= 100:
        raise ControlError('Expected schema 1 with 1..100 ordered recording clips')
    seen, inputs = set(), []
    for clip in clips:
        if not isinstance(clip, dict) or not isinstance(clip.get('id'), str) or not clip['id'] or clip['id'] in seen or not isinstance(clip.get('path'), str) or not clip['path']:
            raise ControlError('Recording clips need unique nonempty ids and local path strings')
        seen.add(clip['id'])
        path = video._local(manifest_path.parent / clip['path'])
        inputs.append({'id': clip['id'], 'path': path, 'probe': video.probe_audio(path)})
    # PCM WAV uses RIFF 32-bit sizes; four hours of 48k/stereo/s16 stays below 4 GiB.
    if sum(item['probe']['duration'] for item in inputs) > 4 * 3600:
        raise ControlError('Recording join is limited to four hours of PCM WAV audio')
    tool = shutil.which('ffmpeg')
    if not tool:
        raise ControlError('ffmpeg is required; no automatic installation')
    tool_version = video._run([tool, '-version'], timeout=10).decode().splitlines()[0]
    implementation_sha = video._hash_file(Path(__file__))
    video_sha = video._hash_file(Path(video.__file__))
    fingerprint = digest(canonical({'version': VERSION, 'manifest': manifest, 'ffmpeg': tool_version,
        'implementation_sha256': implementation_sha, 'media_helpers_sha256': video_sha,
        'sources': [{'id': item['id'], 'sha256': item['probe']['sha256']} for item in inputs]}).encode())
    output = video._local(output_dir, exists=False)
    project = Path(__file__).resolve().parents[2]
    if output.is_relative_to(project) and not output.is_relative_to(project / '.local'):
        raise ControlError('Project audio artifacts must stay under .local, never src/public/docs')
    if output.exists():
        try:
            report = json.loads(video._local(output / 'join-report.json').read_text())
        except (OSError, ValueError) as error:
            raise ControlError('Existing output is not an intact owned recording package') from error
        if report.get('tool') != VERSION or report.get('input_digest') != fingerprint or report.get('status') != 'joined':
            raise ControlError('Existing audio package has different inputs; choose a new output version')
        if set(report.get('hashes', {})) != {'joined.wav', 'clips.json'}:
            raise ControlError('Incomplete recording join cache')
        for name in ('joined.wav', 'clips.json'):
            if video._hash_file(video._local(output / name)) != report['hashes'][name]:
                raise ControlError('Recording package was modified; refusing overwrite')
        return {**report, 'cache_hit': True}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.creator-audio-join-', dir=output.parent) as directory:
        work = Path(directory)
        segments, cumulative_frames = [], 0
        joined_path = work / 'joined.wav'
        with wave.open(str(joined_path), 'wb') as joined:
            joined.setnchannels(2)
            joined.setsampwidth(2)
            joined.setframerate(48000)
            for index, item in enumerate(inputs):
                copied = work / f'input-{index:03}{item["path"].suffix.lower()}'
                shutil.copyfile(item['path'], copied)
                if video._hash_file(copied) != item['probe']['sha256']:
                    raise ControlError('Recording changed while capturing input')
                decoded = work / f'decoded-{index:03}.wav'
                args = [tool, '-hide_banner', '-loglevel', 'error', '-nostdin', '-threads', '2',
                        '-protocol_whitelist', 'file,pipe', '-format_whitelist', video.FORMATS,
                        '-i', str(copied), '-map', '0:a:0', '-map_metadata', '-1', '-map_metadata:s:a', '-1',
                        '-map_chapters', '-1', '-vn', '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2',
                        '-threads', '2', str(decoded)]
                video._run(args, timeout=max(120, min(3600, item['probe']['duration'] * 3)))
                with wave.open(str(decoded), 'rb') as source:
                    if source.getnchannels() != 2 or source.getsampwidth() != 2 or source.getframerate() != 48000 or source.getcomptype() != 'NONE':
                        raise ControlError('Decoded recording PCM format mismatch')
                    frames = source.getnframes()
                    if frames <= 0 or cumulative_frames + frames > 4 * 3600 * 48000:
                        raise ControlError('Decoded recording empty or exceeds WAV duration limit')
                    start_frame = cumulative_frames
                    copied_frames = 0
                    while True:
                        data = source.readframes(48000)
                        if not data:
                            break
                        joined.writeframesraw(data)
                        copied_frames += len(data) // 4
                    if copied_frames != frames:
                        raise ControlError('Decoded recording frame count mismatch')
                cumulative_frames += frames
                segments.append({'id': item['id'], 'source_sha256': item['probe']['sha256'],
                    'source_path': str(item['path']), 'source_duration_reported': item['probe']['duration'],
                    'start': start_frame / 48000, 'end': cumulative_frames / 48000,
                    'start_sample': start_frame, 'end_sample': cumulative_frames,
                    'decoded_frames': frames, 'decoded_duration': frames / 48000,
                    'decoded_sha256': video._hash_file(decoded)})
        with wave.open(str(joined_path), 'rb') as joined:
            if joined.getnframes() != cumulative_frames or joined.getframerate() != 48000 or joined.getnchannels() != 2:
                raise ControlError('Joined audio verification failed')
        actual = video.probe_audio(joined_path)
        if abs(actual['duration'] - cumulative_frames / 48000) > 0.001:
            raise ControlError('ffprobe disagrees with actual joined PCM duration')
        if any(video._hash_file(item['path']) != item['probe']['sha256'] for item in inputs) or json.loads(manifest_path.read_text()) != manifest:
            raise ControlError('Recording inputs changed during joining')
        (work / 'clips.json').write_text(json.dumps({'schema': 1, 'sample_rate': 48000, 'channels': 2,
            'duration': cumulative_frames / 48000, 'timing': 'decoded_sample_positions', 'clips': segments}, ensure_ascii=False, indent=2))
        report = {'tool': VERSION, 'status': 'joined', 'cache_hit': False, 'input_digest': fingerprint,
            'created_at': utc_now(), 'ffmpeg': tool_version, 'implementation_sha256': implementation_sha,
            'media_helpers_sha256': video_sha, 'clip_count': len(segments), 'duration': cumulative_frames / 48000,
            'sample_rate': 48000, 'channels': 2, 'codec': 'pcm_s16le',
            'input_metadata_copied': False, 'trimmed': False, 'retimed': False, 'crossfaded': False,
            'hashes': {name: video._hash_file(work / name) for name in ('joined.wav', 'clips.json')}}
        (work / 'join-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        package = work / 'package'; package.mkdir()
        for name in ('joined.wav', 'clips.json', 'join-report.json'):
            shutil.move(str(work / name), package / name)
        if output.exists():
            raise ControlError('Output appeared during recording join; refusing overwrite')
        os.rename(package, output)
        return report
