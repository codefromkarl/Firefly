"""Real local FFmpeg assembly using generated color PNGs and a test tone, never a user's voice."""
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from PIL import Image

from creator_system.store import ControlError
from creator_system import video
from unittest.mock import patch
from creator_system.video import assemble_video, probe_audio, resolve_timeline, _subtitles


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Local FFmpeg tools required')
class VideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.audio = self.root / 'synthetic-test-tone.wav'
        with wave.open(str(self.audio), 'wb') as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000)
            output.writeframes(b''.join(struct.pack('<h', round(1200 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(16000)))
        for number, color in enumerate(('navy', 'maroon')):
            Image.new('RGB', (320, 180), color).save(self.root / f'{number}.png')
        self.manifest = {'schema':1, 'title':'Synthetic demo only', 'width':320, 'height':180, 'fps':30,
                         'demo_audio':True, 'timing_confirmed':False, 'audio':{'path':self.audio.name},
                         'scenes':[{'id':'one','image':'0.png','narration':'第一段技术测试'}, {'id':'two','image':'1.png','narration':'第二段技术测试'}]}
        self.path = self.root / 'frames.json'
        self.write()

    def tearDown(self): self.tmp.cleanup()
    def write(self): self.path.write_text(json.dumps(self.manifest, ensure_ascii=False))

    def test_real_ffmpeg_preview_codec_coverage_cache_and_changed_input(self):
        report = assemble_video(self.path, self.root / 'output', preview=True)
        self.assertEqual(report['status'], 'assembled')
        self.assertEqual(report['timing'], 'estimated')
        self.assertTrue(report['demo_audio'])
        self.assertIn('测试音频', report['watermark'])
        self.assertAlmostEqual(report['output_audio_duration'], 1, delta=.03)
        self.assertGreaterEqual(report['output_video_duration'], .97)
        self.assertEqual(set(p.name for p in (self.root / 'output').iterdir()), {'video.mp4','timeline.json','subtitles.srt','poster.jpg','build-report.json'})
        self.assertTrue(assemble_video(self.path, self.root / 'output', preview=True)['cache_hit'])
        real_hash = video._hash_file
        with patch.object(video, '_hash_file', side_effect=lambda p: 'f' * 64 if Path(p) == Path(video.__file__) else real_hash(p)):
            with self.assertRaisesRegex(ControlError, 'different inputs'):
                assemble_video(self.path, self.root / 'output', preview=True)
        Image.new('RGB',(320,180),'green').save(self.root/'0.png')
        with self.assertRaisesRegex(ControlError, 'different inputs'):
            assemble_video(self.path, self.root/'output',preview=True)

    def test_real_explicit_timing_assembly_and_mutated_output_refused(self):
        self.manifest.update(demo_audio=False,timing_confirmed=True)
        for scene, start, end in zip(self.manifest['scenes'], (0,.5),(.5,1)):
            scene.update(start=start,end=end)
        self.write()
        report=assemble_video(self.path,self.root/'output')
        self.assertEqual(report['timing'],'explicit')
        self.assertIsNone(report['watermark'])
        (self.root/'output/poster.jpg').write_bytes(b'modified')
        with self.assertRaisesRegex(ControlError,'modified'):
            assemble_video(self.path,self.root/'output')

    def test_real_mp3_and_m4a_keep_the_complete_recording(self):
        for extension in ('mp3', 'm4a'):
            path = self.root / ('encoded.' + extension)
            subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-i', str(self.audio), str(path)], check=True, capture_output=True)
            self.manifest['audio']['path'] = path.name
            self.write()
            report = assemble_video(self.path, self.root / extension, preview=True)
            self.assertGreaterEqual(report['output_audio_duration'], .97)
            self.assertLessEqual(abs(report['output_audio_duration'] - 1), .1)

    def test_unknown_output_directory_is_not_overwritten(self):
        target = self.root / 'output'; target.mkdir()
        (target / 'personal.txt').write_text('Keep me')
        with self.assertRaises(ControlError):assemble_video(self.path, target, preview=True)
        self.assertEqual((target / 'personal.txt').read_text(), 'Keep me')

    def test_parent_traversal_cannot_write_into_project_public(self):
        # Mock only the module location to model a project wholly inside the temp fixture.
        project = self.root / 'mock-project'
        (project / '.local').mkdir(parents=True)
        with patch.object(video, '__file__', str(project / 'scripts/creator_system/video.py')):
            # Bypass implementation hash only: fake module source need not be created.
            real_hash = video._hash_file
            with patch.object(video, '_hash_file', side_effect=lambda p: '0' * 64 if str(p).endswith('creator_system/video.py') else real_hash(p)):
                with self.assertRaisesRegex(ControlError, 'must stay under .local'):
                    assemble_video(self.path, project / '.local/../public/video', preview=True)
        self.assertFalse((project / 'public').exists())

    def test_audio_private_metadata_does_not_enter_mp4(self):
        tagged = self.root / 'tagged.mp3'
        private = '/home/private-user/voice-recordings/private-session.wav'
        subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-i', str(self.audio),
                        '-metadata', 'comment=' + private, '-metadata', 'title=PRIVATE_ID3_TITLE',
                        '-metadata', 'location=PRIVATE_LOCATION', str(tagged)], check=True, capture_output=True)
        before = subprocess.run([shutil.which('ffprobe'), '-v', 'error', '-show_entries', 'format_tags:stream_tags', '-of', 'json', str(tagged)], capture_output=True, check=True).stdout.decode()
        self.assertIn(private, before)
        self.manifest['audio']['path'] = tagged.name; self.write()
        report = assemble_video(self.path, self.root / 'metadata-clean', preview=True)
        after = subprocess.run([shutil.which('ffprobe'), '-v', 'error', '-show_entries', 'format_tags:stream_tags', '-of', 'json', str(self.root / 'metadata-clean/video.mp4')], capture_output=True, check=True).stdout.decode()
        for value in (private, 'PRIVATE_ID3_TITLE', 'PRIVATE_LOCATION'):
            self.assertNotIn(value, after)
        self.assertFalse(report['input_metadata_copied'])
        self.assertEqual(len(report['implementation_sha256']), 64)

    def test_missing_audio_never_creates_video(self):
        self.manifest.pop('audio');self.write()
        result=assemble_video(self.path,self.root/'output',preview=True)
        self.assertEqual(result['status'],'missing_audio')
        self.assertFalse((self.root/'output').exists())

    def test_invalid_audio_and_image_dimensions_rejected(self):
        self.audio.write_bytes(b'not audio')
        with self.assertRaises(ControlError):probe_audio(self.audio)
        with self.assertRaises(ControlError):probe_audio('https://example.org/a.wav')

    def test_time_confirmation_is_not_a_substitute_for_real_cues(self):
        self.manifest['timing_confirmed']=True
        with self.assertRaisesRegex(ControlError,'explicit'):
            resolve_timeline(self.manifest,1,preview=False)
        self.manifest['scenes'][0]['start']=0
        with self.assertRaisesRegex(ControlError,'Partial'):
            resolve_timeline(self.manifest,1,preview=True)

    def test_nan_gap_overlap_and_incomplete_coverage(self):
        for bounds in [((0,float('nan')),(.5,1)), ((0,.4),(.5,1)), ((0,.6),(.5,1)), ((0,.5),(.5,.9)), ((0,.5),(.5,1.2))]:
            scenes=[{**scene,'start':bound[0],'end':bound[1]} for scene,bound in zip(self.manifest['scenes'],bounds)]
            with self.assertRaises(ControlError):resolve_timeline({**self.manifest,'scenes':scenes},1,preview=True)

    def test_mismatched_frame_dimensions_and_demo_production_rejected(self):
        Image.new('RGB',(100,100),'black').save(self.root/'0.png')
        with self.assertRaisesRegex(ControlError,'dimensions'):
            assemble_video(self.path,self.root/'output',preview=True)
        with self.assertRaisesRegex(ControlError,'Demo/test'):
            assemble_video(self.path,self.root/'output',preview=False)

    def test_long_subtitles_are_two_lines_with_estimated_segments(self):
        value, timing=_subtitles([{'start':0,'end':12,'narration':'测'*200}])
        self.assertEqual(timing,'estimated_segments_within_scenes')
        for block in value.strip().split('\n\n'):
            text=block.splitlines()[2:]
            self.assertLessEqual(len(text),2)
            self.assertTrue(all(len(line)<=36 for line in text))


if __name__=='__main__':unittest.main()
