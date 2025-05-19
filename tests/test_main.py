import unittest
import os
from main import load_dialogue_lines, load_transcription_segments, assign_speakers_to_segments, transcribe_audio
from unittest.mock import patch, MagicMock

class TestTranscribeAudio(unittest.TestCase):
    @patch('main.whisper.load_model')
    @patch('main.tempfile.NamedTemporaryFile')
    def test_transcribe_audio(self, mock_tempfile, mock_load_model):
        # Mock the temp file
        mock_temp = MagicMock()
        mock_temp.name = 'fake_audio.wav'
        mock_tempfile.return_value = mock_temp

        # Mock the clip's audio.write_audiofile
        mock_clip = MagicMock()
        mock_clip.audio.write_audiofile = MagicMock()

        # Mock the whisper model and its transcribe method
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {'segments': [{'start': 0, 'end': 1, 'text': 'test'}]}
        mock_load_model.return_value = mock_model

        # Patch os.remove to avoid deleting real files
        with patch('main.os.remove') as mock_remove:
            result = transcribe_audio(mock_clip)

        mock_clip.audio.write_audiofile.assert_called_once_with('fake_audio.wav')
        mock_load_model.assert_called_once_with("base")
        mock_model.transcribe.assert_called_once_with(audio='fake_audio.wav', word_timestamps=True)
        mock_remove.assert_called_once_with('fake_audio.wav')
        self.assertIn('segments', result)
        self.assertEqual(result['segments'][0]['text'], 'test')


class TestMainFunctions(unittest.TestCase):
    def setUp(self):
        # Create a sample dialogue CSV
        self.dialogue_csv = 'test_dialogue.csv'
        with open(self.dialogue_csv, 'w', encoding='utf-8') as f:
            f.write('Speaker;Line\nSKINNER;Hello there!\nCHALMERS;Hi, Seymour.\n')

        # Create a sample transcription CSV
        self.transcription_csv = 'test_transcription.csv'
        with open(self.transcription_csv, 'w', encoding='utf-8') as f:
            f.write('start,end,text\n0.0,1.0,Hello there!\n1.0,2.0,Hi, Seymour.\n')

    def tearDown(self):
        os.remove(self.dialogue_csv)
        os.remove(self.transcription_csv)

    def test_load_dialogue_lines(self):
        lines = load_dialogue_lines(self.dialogue_csv)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], ('SKINNER', 'Hello there!'))
        self.assertEqual(lines[1], ('CHALMERS', 'Hi, Seymour.'))

    def test_load_transcription_segments(self):
        segments = load_transcription_segments(self.transcription_csv)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]['text'], 'Hello there!')
        self.assertAlmostEqual(segments[1]['start'], 1.0)

    def test_assign_speakers_to_segments(self):
        lines = load_dialogue_lines(self.dialogue_csv)
        segments = load_transcription_segments(self.transcription_csv)
        segments = assign_speakers_to_segments(segments, lines)
        self.assertIn('speaker', segments[0])
        self.assertEqual(segments[0]['speaker'], 'SKINNER')
        self.assertEqual(segments[1]['speaker'], 'CHALMERS')

if __name__ == '__main__':
    unittest.main()