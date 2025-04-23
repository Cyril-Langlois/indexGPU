# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 12:35:11 2025

@author: clanglois1
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from View import MainView
from Model import Model
from Controller import Controller

class Colors:
    def __init__(self):
        self.color1 = (255, 255, 255) # Background color of imageView
        self.color2 = (255, 255, 255) # Background color of PlotWidget
        self.color3 = (243, 98, 64)   # PushButton color (for Qsplitter in ImageView)
        self.color4 = (243, 98, 64, 150) # Color of the line plot number 1
        self.color5 = (243, 98, 64)   # Color of the line plot number 2 
        self.color6 = (193, 167, 181,50) # Brush Color for legend in plot



def main():
    # app = QApplication(sys.argv)
    model = Model()
    color = Colors()
    view = MainView(color)
    # view = MainView(inichord_parent)
    controller = Controller(model, view)
    view.show()
    # sys.exit(app.exec_())

if __name__ == '__main__':
    main()