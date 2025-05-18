# main.py

import os
import tempfile
import vlc
import random
import PySide6.QtWidgets as QtWidgets
from moviepy import *
import whisper
from rapidfuzz import fuzz, process
import csv


# Path to the video file
steamed_hams = os.path.join(os.path.dirname(__file__), 'resources', 'SteamedHams.mp4')

# Dialogue CSV file
dialogue_csv = os.path.join(os.path.dirname(__file__), 'resources', 'dialogue.csv')

def main():
    # 1. Load dialogue lines
    dialogue_lines = []
    with open(dialogue_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            dialogue_lines.append((row['Speaker'], row['Line']))
    # 2. Prepare just the lines for matching
    lines_only = [line for _, line in dialogue_lines]

    clip = VideoFileClip(steamed_hams)

    # Extract audio and transcribe it
    audio_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=True).name
    clip.audio.write_audiofile(audio_path)

    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True)

    # 3. For each Whisper segment, find the closest line and assign speaker
    for segment in result['segments']:
        text = segment['text'].strip()
        match, score, idx = process.extractOne(text, lines_only, scorer=fuzz.token_sort_ratio)
        speaker = dialogue_lines[idx][0]
        segment['speaker'] = speaker
        print(f"Segment: {text}\nSpeaker: {speaker} (Score: {score})\n")

    # Print the transcription
    # for segment in result['segments']:
    #     print(f"Start: {segment['start']:.2f}, End: {segment['end']:.2f}, Text: {segment['text']}")

    # Create a list of all the segment times that are not included in the transcription, including from the start of the video to the first segment and from the last segment to the end of the video
    excluded_segments = []
    for i in range(len(result['segments'])):
        if i == 0:
            excluded_segments.append((0, result['segments'][i]['start']))
        if i == len(result['segments']) - 1:
            excluded_segments.append((result['segments'][i]['end'], clip.duration))
        else:
            excluded_segments.append((result['segments'][i]['end'], result['segments'][i + 1]['start']))

    # Print the excluded segments
    #print("Excluded segments:")
    # for start, end in excluded_segments:
    #     print(f"Start: {start:.2f}, End: {end:.2f}")

    # Shuffle the result['segments'] list
    random.shuffle(result['segments'])

    # Interleave the shuffled segments with the excluded segments, keeping the excluded segments in their original order
    interleaved_segments = []
    for i in range(len(excluded_segments)):
        interleaved_segments.append(excluded_segments[i])
        if i < len(result['segments']):
            interleaved_segments.append((result['segments'][i]['start'], result['segments'][i]['end'], result['segments'][i]['text']))

    # Print the interleaved segments
    print("Interleaved segments:")
    for segment in interleaved_segments:
        if len(segment) == 2:
            print(f"Excluded Segment - Start: {segment[0]:.2f}, End: {segment[1]:.2f}")
        else:
            print(f"Segment - Start: {segment[0]:.2f}, End: {segment[1]:.2f}, Text: {segment[2]}")

    # Create a new video clip with the interleaved segments
    edited_clip = []
    for segment in interleaved_segments:
        if len(segment) == 2:
            # Excluded segment
            start, end = segment
            edited_clip.append(clip.subclipped(start, end))
        else:
            # Transcribed segment
            start, end, text = segment
            edited_clip.append(clip.subclipped(start, end))

    # Concatenate the edited clips
    edited_clip = concatenate_videoclips(edited_clip)

    # Clean up the audio file
    os.remove(audio_path)

    # Save the edited video to a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    edited_path = temp_file.name
    edited_clip.write_videofile(edited_path, codec='libx264', audio_codec='aac')
    temp_file.close()

    # Play edited video
    instance = vlc.Instance()
    player = instance.media_player_new()
    media = instance.media_new(edited_path)
    player.set_media(media)

    # Create a PySide6 application and a frame to display the video
    vlcApp = QtWidgets.QApplication([])
    vlcWidget = QtWidgets.QFrame()
    vlcWidget.resize(700, 700)
    vlcWidget.setWindowTitle("You call hamburgers steamed hams?")
    vlcWidget.show()

    player.set_nsobject(vlcWidget.winId())

    player.play()
    vlcApp.exec_()

    os.remove(edited_path)  # Clean up


if __name__ == '__main__':
    main()