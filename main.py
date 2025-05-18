# main.py

import os
import vlc
import time
import PySide6.QtWidgets as QtWidgets
from moviepy import VideoFileClip

steamed_hams = os.path.join(os.path.dirname(__file__), 'resources', 'SteamedHams.mp4')

def main():
    instance = vlc.Instance()
    player = instance.media_player_new()
    media = instance.media_new(steamed_hams)
    player.set_media(media)

    vlcApp = QtWidgets.QApplication([])
    vlcWidget = QtWidgets.QFrame()
    vlcWidget.resize(700, 700)
    vlcWidget.show()

    player.set_nsobject(vlcWidget.winId())

    player.play()
    vlcApp.exec_()

if __name__ == '__main__':
    main()