import vlc
import sys
import os.path
import vlc
from PyQt5 import QtWidgets, QtCore, QtGui
import subprocess
from video import  VideoModel
from superqt import QLabeledRangeSlider
from actions import UndoableAction, HistoryManager
from typing import List
import os
from datetime import datetime


history = HistoryManager()

class Player(QtWidgets.QMainWindow):
    """A simple Media Player using VLC and Qt
    """
    def __init__(self, master=None):
        QtWidgets.QMainWindow.__init__(self, master)
        self.setWindowTitle("Media Player")

        # creating a basic vlc instance
        self.instance = vlc.Instance()
        # creating an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()
        self.createUI()
        self.isPaused = False


    def createUI(self):
        """Set up the user interface, signals & slots
        """
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)

        # In this widget, the video will be drawn
        if sys.platform == "darwin": # for MacOS
            self.videoframe = QtWidgets.QMacCocoaViewContainer(0)
        else:
            self.videoframe = QtWidgets.QFrame()
        self.palette = self.videoframe.palette()
        self.palette.setColor (QtGui.QPalette.Window,
                               QtGui.QColor(0,0,0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.positionslider.setToolTip("Position")
        self.positionslider.setMaximum(1000)

        def mousePressEvent(event):
            if event.button() == QtCore.Qt.LeftButton:
                val = self.pixelPosToRangeValue(event.pos())
                self.setValue(val)

        self.positionslider.sliderMoved.connect(self.setPosition)
        self.positionslider.sliderPressed.connect(lambda *args: print(args))


        self.hbuttonbox = QtWidgets.QHBoxLayout()
        self.playbutton = QtWidgets.QPushButton("Play")
        self.hbuttonbox.addWidget(self.playbutton)
        self.playbutton.clicked.connect(self.PlayPause)

        self.hbuttonbox.addStretch(1)
        self.setVolume(100)

        self.videoplayerlayout = QtWidgets.QVBoxLayout()
        self.videoplayerlayout.addWidget(self.videoframe)
        self.videoplayerlayout.addWidget(self.positionslider)
        self.videoplayerlayout.addLayout(self.hbuttonbox)


        self.videoplayerlayoutWidget = QtWidgets.QWidget();
        self.videoplayerlayoutWidget.setLayout(self.videoplayerlayout);



        import dataclasses
        def move_current_frame(d_frames):
            before = self.mediaplayer.get_time()

            mspf = int(1000 // (self.mediaplayer.get_fps() or 25))
            d_time_ms = d_frames * mspf
            target = self.mediaplayer.get_time() + d_time_ms
            result = self.mediaplayer.set_time(target)

            print(before, target, result, self.mediaplayer.get_time())


        def pp():
            self.PlayPause()
            print(self.mediaplayer.get_time())

        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Space"), self)
        self.shortcut.activated.connect(pp)

        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Right"), self)
        self.shortcut.activated.connect(lambda : move_current_frame(1))


        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Left"), self)
        self.shortcut.activated.connect(lambda : move_current_frame(-1))


        def export_frame():
            print("XX")
            t = self.mediaplayer.get_time()
            print(t)
            ms = t % 1000
            t = t // 1000
            s = t % 60
            t = t // 60
            m = t % 60
            t = t // 60
            h = t % 60
            t = t // 60
            t_str = f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
            print("Exporting: ", self.filename, t_str)
            import os
            from datetime import timedelta

            def apply(filename, t_str):
                base_dir = os.path.expanduser(os.path.join("~", "Pictures", "video_exports"))

                print("W", filename, t_str)
                if not os.path.exists(base_dir):
                    os.makedirs(base_dir)
                print("W", filename, t_str)
                begin = datetime.now()
                base_name = os.path.splitext(os.path.basename(filename))[0]

                print("W", filename, t_str)
                print(base_name[:13])
                frame_datetime = datetime.strptime(base_name[:13], "%Y%m%d_%H%M") + timedelta(hours=h, minutes=m, seconds=s, milliseconds=ms)
                print(base_name[:13])
                frame_datetime_str = frame_datetime.strftime("%Y:%m:%d_%H:%M:%S")
                print(base_name[:13])

                print("W", filename, t_str)
                out =  os.path.join(base_dir,
                                 base_name +
                                                 f"{h:02d}{m:02d}{s:02d}{ms:03d}.png")
                print(out)
                subprocess.call([
                    "ffmpeg",
                    "-ss", t_str,
                    "-i",  filename,
                    "-vframes", "1",
                    "-c:v", "png",
                    out
                   ])
                subprocess.call([
                    "exiftool",
                    f"-CreateDate={frame_datetime_str}",
                    f"-DateTimeOriginal={frame_datetime_str}",
                    f"-PNG:CreationTime={frame_datetime_str}",
                    "-overwrite_original",
                    out
                ])
                print("Duration: ", datetime.now() - begin)
            from video import thumbnailer

            thumbnailer.pool.apply_async(apply, args=(self.filename, t_str))
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+e"), self)
        self.shortcut.activated.connect(lambda : export_frame())
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("f"), self)
        self.shortcut.activated.connect(lambda : self.mediaplayer.toggle_fullscreen())

        def slowmo():
            if self.mediaplayer.get_rate() < 0.7:
                print("rate", 1)
                self.mediaplayer.set_rate(1)
            else:
                print("rate", .5)
                self.mediaplayer.set_rate(0.5)

        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("s"), self)
        self.shortcut.activated.connect(slowmo)

        def change_size(diff):
            self.icon_size += diff
            print(self.icon_size < 64)
            if self.icon_size < 64:
                self.icon_size = 64
            if self.icon_size > 256:
                self.icon_size = 256
            print(self.icon_size)
            self.list_view.setIconSize(QtCore.QSize(self.icon_size, self.icon_size))

        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("+"), self)
        self.shortcut.activated.connect(lambda : change_size(64))
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("-"), self)
        self.shortcut.activated.connect(lambda : change_size(-64))
        from typing import Optional
        def undo():
            history.undo(self.model)
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+z"), self)
        self.shortcut.activated.connect(lambda : undo())
        def redo():
            history.redo(self.model)
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+z"), self)
        self.shortcut.activated.connect(lambda : redo())


        def set_rating(value):
            selected = self.list_view.selectedIndexes()

            stars = None
            actions = []
            for i, index in enumerate(sorted(selected, key=lambda r: -r.row())):
                video = self.model.video_files[index.row()]
                from actions import SetVideoStars
                stars = SetVideoStars((
                    video.fn,
                    video.metadata.rejected,
                    video.metadata.rating,
                    False if value >= 0 else not video.metadata.rejected,
                    value if value >= 0 else video.metadata.rating
                ), stars)
                stars.run(self.model)
                actions.append(stars)
            history.apply(self.model, *actions)

        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("0"), self)
        self.shortcut.activated.connect(lambda : set_rating(0))
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("1"), self)
        self.shortcut.activated.connect(lambda : set_rating(1))
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("2"), self)
        self.shortcut.activated.connect(lambda : set_rating(2))
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("3"), self)
        self.shortcut.activated.connect(lambda : set_rating(3))
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("4"), self)
        self.shortcut.activated.connect(lambda : set_rating(4))
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("5"), self)
        self.shortcut.activated.connect(lambda : set_rating(5))
        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("r"), self)
        self.shortcut.activated.connect(lambda : set_rating(-1))

        def link():
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self, "Open File", os.path.expanduser('~'))

            if not os.path.isdir(directory):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Not a directory",
                    "The selected item was not a directory. "
                    "You need to select an empty folder. ")
                return

            if os.listdir(directory):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Non-empty directory selected",
                    "The selected directory is not empty. "
                    "You need to select an empty folder. ")
                return

            print(directory)
            failure = False
            for index in self.list_view.selectedIndexes():
                video = self.model.video_files[index.row()]
                failure = failure or (
                    0 != subprocess.call([
                        "ln",
                        "-s",
                        video.fn,
                        os.path.join(directory, os.path.basename(video.fn)),
                    ])
                )
            if failure:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Linkage failure",
                    "Some files could not be linked.")


        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.shortcut.activated.connect(link)

        def delete():
            from actions import Trash
            selected = self.list_view.selectedIndexes()
            response = QtWidgets.QMessageBox.question(self, "Delete Items", "Do you really want to delete %d items?" % len(selected), defaultButton=QtWidgets.QMessageBox.No)
            if response == QtWidgets.QMessageBox.Yes:
                actions = []
                for i, index in enumerate(sorted(selected, key=lambda r: -r.row())):
                    video = self.model.video_files[index.row()]
                    action = Trash(video.fn, actions[-1] if len(actions) else None)
                    actions.append(action)
                history.apply(self.model, *actions)


        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Del"), self)
        self.shortcut.activated.connect(lambda : delete())

        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("F5"), self)
        self.shortcut.activated.connect(lambda : self.model.reload())

        self.model = VideoModel()

        def open_file(index):
            self.OpenFile(self.model.video_files[index.row()].fn)

        self.list_view = QtWidgets.QListView()
        self.list_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_view.doubleClicked.connect(open_file)
        self.list_view.setViewMode(QtWidgets.QListView.IconMode)
        self.list_view.setResizeMode(QtWidgets.QListView.Adjust)
        self.list_view.setFlow(QtWidgets.QListView.LeftToRight)
        self.list_view.setMovement(QtWidgets.QListView.Snap)
        self.list_view.setModel(self.model)
        # self.list_view.setGridSize(QtCore.QSize(256 + 10, 256 + 10))
        self.icon_size = 256
        self.list_view.setIconSize(QtCore.QSize(self.icon_size, self.icon_size))
        self.list_view.setWordWrap(True)

        self.hboxlayout = QtWidgets.QSplitter()
        self.hboxlayout.addWidget(self.list_view)
        self.hboxlayout.addWidget(self.videoplayerlayoutWidget)

        self.filter_slider = QLabeledRangeSlider(QtCore.Qt.Horizontal)
        self.filter_slider.setRange(0, 6)
        self.filter_slider.setValue((0, 6))
        self.filter_slider.setMaximum(6)
        self.filter_slider.setMinimum(-1)

        def set_rating_filter(v):
            self.model.filter_rating = v
        self.filter_slider.sliderMoved.connect(set_rating_filter)
        self.parentLayout = QtWidgets.QVBoxLayout()
        self.parentLayout.addWidget(self.filter_slider, 0)
        self.parentLayout.addWidget(self.hboxlayout, 2)
        self.widget.setLayout(self.parentLayout)

        exit = QtWidgets.QAction("&Exit", self)
        exit.triggered.connect(sys.exit)
        menubar = self.menuBar()
        filemenu = menubar.addMenu("&File")
        filemenu.addAction(exit)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.updateUI)

    def PlayPause(self):
        """Toggle play/pause status
        """
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.playbutton.setText("Play")
            self.isPaused = True
        else:
            if self.mediaplayer.play() == -1:
                self.OpenFile()
                return
            self.mediaplayer.play()
            self.playbutton.setText("Pause")
            self.timer.start()
            self.isPaused = False

    def Stop(self):
        """Stop player
        """
        self.mediaplayer.stop()
        self.playbutton.setText("Play")

    def OpenFile(self, filename=None):
        """Open a media file in a MediaPlayer
        """
        if filename is None:
            return
            filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", os.path.expanduser('~'))
        if not filename:
            return

        # create the media
        if sys.version < '3':
            filename = unicode(filename)
        self.filename = filename
        self.media = self.instance.media_new(filename)
        # put the media in the media player
        self.mediaplayer.set_media(self.media)

        # parse the metadata of the file
        self.media.parse()
        # set the title of the track as window title
        self.setWindowTitle(self.media.get_meta(0))

        # the media player has to be 'connected' to the QFrame
        # (otherwise a video would be displayed in it's own window)
        # this is platform specific!
        # you have to give the id of the QFrame (or similar object) to
        # vlc, different platforms have different functions for this
        if sys.platform.startswith('linux'): # for Linux using the X Server
            self.mediaplayer.set_xwindow(int(self.videoframe.winId()))
        elif sys.platform == "win32": # for Windows
            self.mediaplayer.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin": # for MacOS
            self.mediaplayer.set_nsobject(self.videoframe.winId())
        self.PlayPause()

    def setVolume(self, Volume):
        """Set the volume
        """
        self.mediaplayer.audio_set_volume(Volume)

    def setPosition(self, position):
        """Set the position
        """
        # setting the position to where the slider was dragged
        self.mediaplayer.set_position(position / 1000.0)
        # the vlc MediaPlayer needs a float value between 0 and 1, Qt
        # uses integer variables, so you need a factor; the higher the
        # factor, the more precise are the results
        # (1000 should be enough)

    def updateUI(self):
        """updates the user interface"""
        # setting the slider to the desired position
        self.positionslider.setValue(int(self.mediaplayer.get_position() * 1000))

        if not self.mediaplayer.is_playing():
            # no need to call this function if nothing is played
            self.timer.stop()
            if not self.isPaused:
                # after the video finished, the play button stills shows
                # "Pause", not the desired behavior of a media player
                # this will fix it
                self.Stop()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)



    player = Player()
    player.show()
    player.resize(640, 480)
    if sys.argv[1:]:
        player.OpenFile(sys.argv[1])
    sys.exit(app.exec_())
