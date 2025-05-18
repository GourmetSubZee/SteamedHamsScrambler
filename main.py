import os
import tempfile
import vlc
import random
import PySide6.QtWidgets as QtWidgets
from moviepy import VideoFileClip, concatenate_videoclips
import whisper
from rapidfuzz import fuzz, process
import csv

steamed_hams = os.path.join(os.path.dirname(__file__), 'resources', 'SteamedHams.mp4')
dialogue_csv = os.path.join(os.path.dirname(__file__), 'resources', 'dialogue.csv')

def load_dialogue_lines(dialogue_csv):
    dialogue_lines = []
    with open(dialogue_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            dialogue_lines.append((row['Speaker'], row['Line']))
    return dialogue_lines

def transcribe_audio(clip):
    audio_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    clip.audio.write_audiofile(audio_path)
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True)
    os.remove(audio_path)
    return result

def assign_speakers_to_segments(segments, dialogue_lines):
    lines_only = [line for _, line in dialogue_lines]
    for segment in segments:
        text = segment['text'].strip()
        match, score, idx = process.extractOne(text, lines_only, scorer=fuzz.token_sort_ratio)
        speaker = dialogue_lines[idx][0]
        segment['speaker'] = speaker
    return segments

def find_excluded_segments(segments, duration):
    excluded_segments = []
    for i in range(len(segments)):
        if i == 0:
            excluded_segments.append((0, segments[i]['start']))
        if i == len(segments) - 1:
            excluded_segments.append((segments[i]['end'], duration))
        else:
            excluded_segments.append((segments[i]['end'], segments[i + 1]['start']))
    return excluded_segments

def interleave_segments(segments, excluded_segments):
    #random.shuffle(segments)
    interleaved = []
    for i in range(len(excluded_segments)):
        interleaved.append(excluded_segments[i])
        if i < len(segments):
            s = segments[i]
            interleaved.append((s['start'], s['end'], s['text'], s['speaker']))
    return interleaved

def create_edited_clip(clip, interleaved_segments):
    clips = []
    for segment in interleaved_segments:
        if len(segment) == 2:
            start, end = segment
            clips.append(clip.subclipped(start, end))
        else:
            start, end, text, speaker = segment
            # Add text overlay consisting of the speaker's name and the text
            clips.append(clip.subclipped(start, end))
    return concatenate_videoclips(clips)

def play_video(edited_clip):
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    edited_path = temp_file.name
    edited_clip.write_videofile(edited_path, codec='libx264', audio_codec='aac')
    temp_file.close()

    instance = vlc.Instance()
    player = instance.media_player_new()
    media = instance.media_new(edited_path)
    player.set_media(media)

    vlcApp = QtWidgets.QApplication([])
    vlcWidget = QtWidgets.QFrame()
    vlcWidget.resize(700, 700)
    vlcWidget.setWindowTitle("You call hamburgers steamed hams?")
    vlcWidget.show()

    player.set_nsobject(vlcWidget.winId())
    player.play()
    vlcApp.exec_()
    os.remove(edited_path)

def main():
    dialogue_lines = load_dialogue_lines(dialogue_csv)
    clip = VideoFileClip(steamed_hams)
    result = transcribe_audio(clip)
    segments = assign_speakers_to_segments(result['segments'], dialogue_lines)
    excluded_segments = find_excluded_segments(segments, clip.duration)
    interleaved = interleave_segments(segments, excluded_segments)
    edited_clip = create_edited_clip(clip, interleaved)
    play_video(edited_clip)

if __name__ == '__main__':
    main()