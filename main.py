from modules.utils import clean_output, create_incremental_filename

import argparse
import os
import tempfile
import vlc
import PySide6.QtWidgets as QtWidgets
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
import whisper
from rapidfuzz import fuzz, process
import csv
import random

steamed_hams = os.path.join(os.path.dirname(__file__), 'resources', 'SteamedHams.mp4')
dialogue_file = os.path.join(os.path.dirname(__file__), 'resources', 'dialogue.csv')
ALLOWED_SPEAKERS = {"SKINNER", "CHALMERS", "AGNES", "SINGERS"}

def load_dialogue_lines(dialogue_csv):
    dialogue_lines = []
    with open(dialogue_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            dialogue_lines.append((row['Speaker'], row['Line']))
    return dialogue_lines

def load_transcription_segments(csv_path):
    segments = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            segments.append({
                'start': float(row['start']),
                'end': float(row['end']),
                'text': row['text']
            })
    return segments

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

def save_transcription(segments):
    output_dir = os.path.join(os.path.dirname(__file__), 'output/transcriptions')
    os.makedirs(output_dir, exist_ok=True)
    output_path = create_incremental_filename(output_dir, "transcription", ".csv")

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['start', 'end', 'speaker', 'text']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for segment in segments:
            writer.writerow({
                'start': segment['start'],
                'end': segment['end'],
                'speaker': segment['speaker'],
                'text': segment['text']
            })

def shuffle_segments(segments, speaker):
    # Find indices and collect segments for the target speaker
    speaker_indices = [i for i, seg in enumerate(segments) if seg.get('speaker') == speaker]
    speaker_segments = [segments[i] for i in speaker_indices]
    # Shuffle the speaker's segments
    random.shuffle(speaker_segments)
    # Create a copy to avoid mutating the original list
    shuffled = segments.copy()
    # Replace the original speaker segments with shuffled ones
    for idx, seg_idx in enumerate(speaker_indices):
        shuffled[seg_idx] = speaker_segments[idx]
    return shuffled


def find_quiet_segments(segments, duration):
    quiet_segments = []
    for i in range(len(segments)):
        if i == 0:
            quiet_segments.append((0, segments[i]['start']))
        if i == len(segments) - 1:
            quiet_segments.append((segments[i]['end'], duration))
        else:
            quiet_segments.append((segments[i]['end'], segments[i + 1]['start']))
    return quiet_segments

def interleave_segments(segments, excluded_segments):
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

def save_video(edited_clip, output_filename=None):
    output_dir = os.path.join(os.path.dirname(__file__), 'output/videos')
    os.makedirs(output_dir, exist_ok=True)
    if output_filename:
        # Strip extension if provided
        if '.' in output_filename:
            output_filename = output_filename.split('.')[0]
        # Create incremental filename with mp4 extension
        output_path = create_incremental_filename(output_dir, output_filename, ".mp4")
    else:
        output_path = create_incremental_filename(output_dir, "steamed_hams_edited", ".mp4")
    edited_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', threads=16)
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

def main(transcription_csv=None, output_filename=None,shuffle_speakers=None):
    dialogue_lines = load_dialogue_lines(dialogue_file)
    clip = VideoFileClip(steamed_hams)
    if transcription_csv:
        speaking_segments = load_transcription_segments(transcription_csv)
    else:
        result = transcribe_audio(clip)
        segments = result['segments']
        speaking_segments = assign_speakers_to_segments(segments, dialogue_lines)
        save_transcription(speaking_segments)
    quiet_segments = find_quiet_segments(speaking_segments, clip.duration)

    # Shuffle segments for each speaker in the list
    if shuffle_speakers:
        for speaker in shuffle_speakers:
            speaking_segments = shuffle_segments(speaking_segments, speaker)

    interleaved_segments = interleave_segments(speaking_segments, quiet_segments)
    edited_clip = create_edited_clip(clip, interleaved_segments)
    output_path = save_video(edited_clip, output_filename=output_filename)
    play_video(output_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs='?', default=None)
    parser.add_argument('--transcription', type=str, help='Path to transcription CSV')
    parser.add_argument('--output', type=str, help='Output MP4 filename (optional)')
    parser.add_argument('--shuffle', type=str, help='Comma-separated list of speakers to shuffle')
    args = parser.parse_args()

    shuffle_speakers = None
    if args.shuffle:
        shuffle_speakers = [s.strip().upper() for s in args.shuffle.split(',')]
        invalid = [s for s in shuffle_speakers if s not in ALLOWED_SPEAKERS]
        if invalid:
            raise ValueError(f"Invalid speakers in --shuffle: {', '.join(invalid)}")


    if args.command == 'clean':
        clean_output('output')
    else:
        main(transcription_csv=args.transcription, output_filename=args.output, shuffle_speakers=shuffle_speakers)