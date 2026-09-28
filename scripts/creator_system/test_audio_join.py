"""Real joining of two distinct synthesized tones; no user recording is accessed."""
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave

from creator_system.audio_join import join_recordings
from creator_system.store import ControlError


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Local FFmpeg required')
class AudioJoinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        for index, hz in enumerate((220, 660)):
            path = self.root / f'{index}.wav'
            with wave.open(str(path), 'wb') as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
                audio.writeframes(b''.join(struct.pack('<h', int(2000 * math.sin(2 * math.pi * hz * i / 16000))) for i in range(8000)))
        self.manifest = {'schema':1,'clips':[{'id':'first','path':'0.wav'},{'id':'second','path':'1.wav'}]}
        self.path = self.root / 'recordings.json'; self.write()

    def tearDown(self): self.tmp.cleanup()
    def write(self): self.path.write_text(json.dumps(self.manifest))

    def test_real_join_duration_tone_order_and_cache(self):
        report = join_recordings(self.path, self.root / 'out')
        self.assertEqual(report['duration'], 1)
        cues = json.loads((self.root/'out/clips.json').read_text())['clips']
        self.assertEqual([(c['id'],c['start'],c['end']) for c in cues], [('first',0,.5),('second',.5,1)])
        with wave.open(str(self.root/'out/joined.wav'),'rb') as audio:
            self.assertEqual((audio.getnchannels(),audio.getframerate(),audio.getnframes()),(2,48000,48000))
            values=struct.unpack('<'+'h'*96000,audio.readframes(48000))
        left=values[::2]
        frequencies=[]
        for segment in (left[:24000],left[24000:]):
            crossings=sum(a<=0<b for a,b in zip(segment,segment[1:]))
            frequencies.append(crossings/.5)
        self.assertAlmostEqual(frequencies[0],220,delta=4)
        self.assertAlmostEqual(frequencies[1],660,delta=4)
        self.assertTrue(join_recordings(self.path,self.root/'out')['cache_hit'])
        self.manifest['clips'].reverse();self.write()
        with self.assertRaisesRegex(ControlError,'different inputs'):join_recordings(self.path,self.root/'out')

    def test_unknown_output_and_changed_input_refused(self):
        target=self.root/'unknown';target.mkdir();(target/'keep.txt').write_text('mine')
        with self.assertRaises(ControlError):join_recordings(self.path,target)
        self.assertEqual((target/'keep.txt').read_text(),'mine')
        join_recordings(self.path,self.root/'out')
        with wave.open(str(self.root/'0.wav'),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0\0'*8000)
        with self.assertRaisesRegex(ControlError,'different inputs'):join_recordings(self.path,self.root/'out')

    def test_invalid_and_multiple_tracks_rejected(self):
        (self.root/'0.wav').write_bytes(b'not audio')
        with self.assertRaises(ControlError):join_recordings(self.path,self.root/'bad')
        multitrack=self.root/'multi.m4a'
        subprocess.run([shutil.which('ffmpeg'),'-v','error','-i',str(self.root/'1.wav'),'-i',str(self.root/'1.wav'),'-map','0:a','-map','1:a','-c:a','aac',str(multitrack)],check=True,capture_output=True)
        self.manifest['clips']=[{'id':'multi','path':'multi.m4a'}];self.write()
        with self.assertRaisesRegex(ControlError,'exactly one'):join_recordings(self.path,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())

    def test_tags_removed_and_clips_keep_source_hashes(self):
        tagged=self.root/'tagged.mp3';secret='/private/test-voice-source'
        subprocess.run([shutil.which('ffmpeg'),'-v','error','-i',str(self.root/'0.wav'),'-metadata','comment='+secret,str(tagged)],check=True,capture_output=True)
        self.manifest['clips'][0]['path']='tagged.mp3';self.write()
        report=join_recordings(self.path,self.root/'out')
        tags=subprocess.run([shutil.which('ffprobe'),'-v','error','-show_entries','format_tags:stream_tags','-of','json',str(self.root/'out/joined.wav')],check=True,capture_output=True).stdout.decode()
        self.assertNotIn(secret,tags)
        self.assertFalse(report['input_metadata_copied'])
        cues=json.loads((self.root/'out/clips.json').read_text())['clips']
        self.assertTrue(all(len(c['source_sha256'])==64 for c in cues))


if __name__=='__main__':unittest.main()
