# main.py

import os
import tempfile
import vlc
import random
import PySide6.QtWidgets as QtWidgets
from moviepy import *

steamed_hams = os.path.join(os.path.dirname(__file__), 'resources', 'SteamedHams.mp4')

def main():
    clip = VideoFileClip(steamed_hams)

    # Split the video into 1 second segments
    segments = []
    for i in range(0, int(clip.duration), 1):
        segment = clip.subclipped(i, i + 1)
        segments.append(segment)

    # Shuffle the segments
    random.shuffle(segments)

    # Concatenate the segments back together
    edited_clip = concatenate_videoclips(segments)

    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    edited_path = temp_file.name
    edited_clip.write_videofile(edited_path, codec='libx264', audio_codec='aac')
    temp_file.close()

    # Play edited video
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

    os.remove(edited_path)  # Clean up


if __name__ == '__main__':
    main()