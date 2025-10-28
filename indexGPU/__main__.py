# -*- coding: utf-8 -*-
"""
Created on Tue Oct 28 14:56:24 2025

@author: useradmin
"""
import sys
from PyQt5.QtWidgets import QApplication
import coreCalc as cc
import Indexation_GUI as ig
import data_classes as dc

class Indexation_orientation():
 # Run the indexing sub-gui
	def __init__(self):
	    # Colors will be applied to all the sub-gui
		self.color1 = (255, 255, 255) # Background color of imageView
		self.color2 = (255, 255, 255) # Background color of PlotWidget
		self.color3 = (243, 98, 64)   # PushButton color (for Qsplitter in ImageView)
		self.color4 = (243, 98, 64, 150) # Color of the line plot number 1
		self.color5 = (243, 98, 64)   # Color of the line plot number 2
		self.color6 = (193, 167, 181,50) # Brush Color for legend in plot
		
		self.model = dc.Model()
		self.w = ig.MainView(self)
		self.controller = cc.Controller(self.model, self.w)
		self.w.show()
		
				
		
#%% Opening of the initial data    
if __name__ == '__main__':
	app = QApplication(sys.argv)
	a = Indexation_orientation()
	app.setQuitOnLastWindowClosed(True)
	app.exec_()