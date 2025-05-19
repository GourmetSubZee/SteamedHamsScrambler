import os
import tempfile
import vlc
import PySide6.QtWidgets as QtWidgets
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
import whisper
from rapidfuzz import fuzz, process
import csv

steamed_hams = os.path.join(os.path.dirname(__file__), 'resources', 'SteamedHams.mp4')
dialogue_file = os.path.join(os.path.dirname(__file__), 'resources', 'dialogue.csv')

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
    result = model.transcribe(audio=audio_path, word_timestamps=True)
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
            subclip = clip.subclipped(start, end)
            caption = f"{speaker}: {text}"
            txt_clip = TextClip(
                font='Arial.ttf',
                text=caption,
                font_size=32,
                color='white',
                bg_color='black',
                size=(subclip.w, 60),
                method='caption'
            ).with_duration(subclip.duration).with_position(('center', 'bottom'))
            composite = CompositeVideoClip([subclip, txt_clip])
            clips.append(composite)
    return concatenate_videoclips(clips)

def save_video(edited_clip):
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    # Create an incremental filename that appends the next number based on existing files starting with 001
    existing_files = [f for f in os.listdir(output_dir) if f.startswith('edited_') and f.endswith('.mp4')]
    existing_numbers = [int(f.split('_')[1].split('.')[0]) for f in existing_files]
    next_number = max(existing_numbers, default=0) + 1
    output_path = os.path.join(output_dir, f'edited_{next_number:03d}.mp4')
    edited_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
    return output_path

def play_video(final_path):
    instance = vlc.Instance()
    player = instance.media_player_new()
    media = instance.media_new(final_path)
    player.set_media(media)

    vlcapp = QtWidgets.QApplication([])
    vlcwidget = QtWidgets.QFrame()
    vlcwidget.resize(700, 700)
    vlcwidget.setWindowTitle("You call hamburgers steamed hams?")
    vlcwidget.show()

    player.set_nsobject(vlcwidget.winId())
    player.play()
    vlcapp.exec_()

def main():
    dialogue_lines = load_dialogue_lines(dialogue_file)
    clip = VideoFileClip(steamed_hams)
    result = transcribe_audio(clip)
    print("Transcription result keys:", result.keys())
    segments = assign_speakers_to_segments(result['segments'], dialogue_lines)
    excluded_segments = find_excluded_segments(segments, clip.duration)
    interleaved = interleave_segments(segments, excluded_segments)
    edited_clip = create_edited_clip(clip, interleaved)
    output_path = save_video(edited_clip)
    play_video(output_path)

if __name__ == '__main__':
    main()