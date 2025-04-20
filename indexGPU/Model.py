# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 12:33:53 2025

@author: clanglois1
"""
import numpy as np
from inichord import General_Functions as gf
import indexGPU.Xallo as xa
from indexGPU import Symetry as sy
import tifffile as tf

import phaseGUI_classes_local as phaseClass
import Indexation_lib_MVC as indGPU


from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5 import QtGui


class Model:
    def __init__(self):
        print("Model initiated")
        self.index_res = None
        
        #Initialisation des variables
        self.nPhases = 1
        self.otsu = False
        self.cluster = False
        
        
    def loadProfiles(self):
        # Loads the stack or clustered profiles
        self.StackLoc, self.StackDir = gf.getFilePathDialog("série d'images à indexer (*.tiff)")
        self.Stack = tf.TiffFile(self.StackLoc[0]).asarray() # Check for dimension. If 2 dimensions : 2D array. If 3 dimensions : stack of images
        self.Current_stack = self.Stack # Extract the stack of images 
        return self.Stack
    
    def loadData(self):
        self.preInd = preIndexation(self) # Ask to open phase form
        
class preIndexation:
    """
    Classe permettant d'entrer en mémoire la liste des phases, des phases à indexer
    et la carte otsu si nécessaire.
    Les dialogues "utilisateurs" se font au travers de la librairie 
    "General_functions".
    
    Ces infos figurent comme attributs de la classe preIndexation.
    """
    def __init__(self, parent):
        # Icons sizes management for pop-up windows (QMessageBox)
        self.pixmap = QPixmap("icons/Main_icon.png")
        self.pixmap = self.pixmap.scaled(100, 100)
        
        self.phaseList = []
        self.SymQ = []
        self.otsu_map = []
        self.listToIndex =[]
        self.DBsizeList = []
        self.chunksList = []
        
        # User interaction to load indexation parameters
        self.phaseIndex = phaseClass.phaseForm(self, parent.nPhases, parent.otsu)
        self.phaseIndex.exec_()
        
        for i, phase in enumerate(self.phaseList):
            self.SymQ.append(sy.get_proper_quaternions_from_CIF(phase.CifLoc)) # Get the variable symQ for symmetry of quaternions
          
        for i, val in enumerate (self.listToIndex):
            if val:
                self.chunksList.append(np.floor(int (self.DBsizeList[i])/250_000))
                if int(self.DBsizeList[i])%250_000 != 0 :
                    self.chunksList[i] += 1
            else :
                self.chunksList.append(None)           
        
        
    def popup_message(self,title,text,icon):
        msg = QMessageBox()
        msg.setIconPixmap(self.pixmap)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setWindowIcon(QtGui.QIcon(icon))
        msg.exec_()

class Indexation_result:
    def __init__(self, height, width, actualProfLength):
        
        # initialization by defining attributes only
        self.height = height
        self.width = width
        self.nbPhase =  1
        self.actualProfLength = actualProfLength
        self.space_groupe = None
        self.cluster = False

                
        self.exp_profiles = np.zeros(self.actualProfLength, self.height, self.width)
        self.exp_profiles_mod = np.zeros(self.actualProfLength, self.height, self.width)
        self.theo_profiles = np.zeros(self.actualProfLength, self.height, self.width)
        self.theo_profiles_mod = np.zeros(self.actualProfLength, self.height, self.width)
        self.nScoresDist = np.zeros((self.height, self.width))
        self.nScoresOri = np.zeros((4, self.height, self.width))
        
        # 2D arrays
        self.quality_map = np.zeros((self.height, self.width))
        self.nScoresDist = np.zeros((self.height, self.width))
        self.IPF_X = np.zeros((self.height, self.width))
        self.IPF_Y = np.zeros((self.height, self.width))
        self.IPF_Z = np.zeros((self.height, self.width))
        self.phase_map = np.zeros((self.height, self.width))
        self.otsu = None
        self.grain_map = np.zeros((self.height, self.width))
        self.cluster = False
        self.grains = False
        
        # paths
        self.CIF_path = ""
        self.stack_path = ""
        self.database_path = ""
        self.normType = "centered euclidian"
        self.metric = "cosine"
        
        