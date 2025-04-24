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
import h5py

import time

import phaseGUI_classes_local as phaseClass
import Indexation_lib as indGPU


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
    
    def reload_data(self):

        self.nPhases = 0

        # Locate indexation file *.h5
        self.StackLoc, self.StackDir = gf.getFilePathDialog("Indexation result (*.hdf5)") # Ask for the H5 result file
    
        f = h5py.File(self.StackLoc[0], 'r') # In order to read the H5 file
        list_dataset_Keys = gf.get_dataset_keys(f) # Extract the listKeys of the H5 files
        list_group_Keys = gf.get_group_keys(f) # Extract the listKeys of the H5 files

        self.CIF_path = []
        self.phase_names = []
        # load data from the h5 file - from 2025_04_22  + legacy (without multiphase nor IPF maps)     
        for i in list_group_Keys:
            group = f[i]
            list_attributs = list(group.attrs.keys())
            if "lenProf" in list_attributs:
                self.lenProf = group.attrs['lenProf']
            if "profile length" in list_attributs:
                self.lenProf = group.attrs['profile length']
            if "height" in list_attributs:
                self.height = group.attrs['height']
            if "width" in list_attributs:
                self.width = group.attrs['width']
            if "CIF path" in list_attributs:
                self.CIF_path.append(group.attrs['CIF path'])
                self.phase_names.append(i)
                self.nPhases += 1

        self.indexRes = Final_Index_res(self, self.height, self.width, self.lenProf)
        self.indexRes.CIF_path = self.CIF_path
        self.indexRes.phase_names = self.phase_names

        for i in list_group_Keys:
            group = f[i]
            list_attributs = list(group.attrs.keys())
            if "nPhases" in list_attributs:
                self.nPhases = group.attrs['nPhases']            
            elif "cluster" in list_attributs:
                self.cluster = group.attrs['cluster']            
            elif "otsu" in list_attributs:
                self.otsu = group.attrs['otsu']            
            elif "stack path" in list_attributs:
                self.indexRes.stack_path = group.attrs['stack path']
            elif "normalization before indexation" in list_attributs:
                self.indexRes.normType = group.attrs['normalization before indexation']                
            elif "metric for Indexation" in list_attributs:
                self.indexRes.metric = group.attrs['metric for Indexation']
         
        for i in list_dataset_Keys:
            if "dist" in i or "nScoresDist" in i: # Extract the distance
                self.indexRes.dist = np.asarray(f[i])
            elif "theo_stack" in i or "nScoresStack" in i: # Extract the theoretical stack
                self.indexRes.theo_stack = np.asarray(f[i])
            elif "ori_f" in i or "nScoresOri" in i: # Extract the quaternions
                self.indexRes.ori_f = np.asarray(f[i])
            elif "rawImage" in i: # Extract the experimental stack
                self.indexRes.rawImage = np.asarray(f[i])
            elif "theoStack_mod" in i or "Treatment_theo_prof" in i: # Extract the theoretical stack in it modified shape
                self.indexRes.theoStack_mod = np.asarray(f[i])
            elif "expStack_mod" in i or "testArrayList" in i: # Extract the experimental stack in it modified shape
                self.indexRes.expStack_mod = np.asarray(f[i])
            elif "quality_final" in i: # Extract the quality map
                self.indexRes.quality_final = np.asarray(f[i])
            elif "phase_map" in i: # Extract the quality map
                self.indexRes.phase_map = np.asarray(f[i])
                self.indexRes.legacy = False
            elif "IPF_final_X" in i: # Extract the quality map
                self.indexRes.IPF_final_X = np.asarray(f[i])
            elif "IPF_final_Y" in i: # Extract the quality map
                self.indexRes.IPF_final_Y = np.asarray(f[i])
            elif "IPF_final_Z" in i: # Extract the quality map
                self.indexRes.IPF_final_Z = np.asarray(f[i])
            elif "labels" in i: # Extract the quality map
                self.indexRes.labels = np.asarray(f[i])
        
        return self.indexRes
        
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

class Final_Index_res:
    def __init__(self, model, height, width, lenProf):
        
        # initialization by defining attributes only
        self.height = height
        self.width = width
        self.nPhases =  model.nPhases
        self.lenProf = lenProf
        self.space_groups = []
        self.cluster = model.cluster
        self.otsu = model.otsu
        self.model = model
        self.legacy = True

                
        self.rawImage = np.zeros((self.lenProf, self.height, self.width))
        self.expStack_mod = np.zeros((self.lenProf, self.height, self.width))
        self.theo_stack = np.zeros((self.lenProf, self.height, self.width))
        self.theoStack_mod = np.zeros((self.lenProf, self.height, self.width))
        self.ori_f = np.zeros((4, self.height, self.width))
        
        # 2D arrays
        self.quality_final = np.zeros((self.height, self.width))
        self.dist = np.zeros((self.height, self.width))
        self.IPF_final_X = np.zeros((self.height, self.width))
        self.IPF_final_Y = np.zeros((self.height, self.width))
        self.IPF_final_Z = np.zeros((self.height, self.width))
        self.phase_map = np.zeros((self.height, self.width))
        
        self.labels = np.zeros((self.height, self.width))
        
        # paths
        self.savePath = ""
        self.CIF_path = ""
        self.stack_path = ""
        self.database_path = ""
        self.normType = "centered euclidian"
        self.metric = "cosine"
        

    def savingRes(self):
        ti = time.strftime("%Y-%m-%d__%Hh-%Mm-%Ss")
        
        indexSTACK = h5py.File(self.savePath + '\IndexData_'+ ti + '.hdf5', 'a')
        
        group = indexSTACK.create_group('indexation')
        
        group.create_dataset(name='theo_stack', data=self.theo_stack)
        group.create_dataset(name='theoStack_mod', data=self.theoStack_mod) #Profil théo modifiés
        group.create_dataset(name='rawImage', data=self.rawImage)
        group.create_dataset(name='dist', data=self.dist)
        group.create_dataset(name='ori_f', data=self.ori_f)
        group.create_dataset(name='expStack_mod', data=self.expStack_mod) #Profil expé modifiés
        group.create_dataset(name='quality_final', data=self.quality_final) #Profil expé modifiés
        group.create_dataset(name='phase_map', data=self.phase_map) #Profil expé modifiés
        group.create_dataset(name='IPF_final_X', data=self.IPF_final_X) #Profil expé modifiés
        group.create_dataset(name='IPF_final_Y', data=self.IPF_final_Y) #Profil expé modifiés
        group.create_dataset(name='IPF_final_Z', data=self.IPF_final_Z) #Profil expé modifiés
        group.create_dataset(name='labels', data=self.labels) #labels si cluster / grains
    
        group.attrs.create("lenProf", self.lenProf)
        group.attrs.create("height", self.height)
        group.attrs.create("width", self.width)
        group.attrs.create("nPhases", self.nPhases)
        group.attrs.create("cluster", self.cluster)
        group.attrs.create("otsu", self.otsu)
        group.attrs.create("stack path", self.stack_path)
        # group.attrs.create("database path", self.DB)
        group.attrs.create("normalization before indexation", self.normType)
        group.attrs.create("metric for Indexation", self.metric)
        # group.attrs.create("nbSTACK", self.nbSTACK)
        # group.attrs.create("nbDB", self.nbDB)
        
        i = 0
        for p in self.model.preInd.phaseList:
            try:
                group_p = indexSTACK.create_group(p.name)
            except:
                group_p = indexSTACK.create_group(str(i))
            i += 1
            group_p.attrs.create("CIF path", p.CifLoc)
            group_p.attrs.create("database path", p.DatabaseLoc)
            group_p.attrs.create("database size", p.DB_Size)
            group_p.attrs.create("index deriv", p.diff)
            group_p.attrs.create("Savitzky Golay", p.SG)
            group_p.attrs.create("Savitzky Golay_poly", p.SG_poly)
            group_p.attrs.create("Savitzky Golay_window", p.SG_win)
        
        indexSTACK.flush()
        indexSTACK.close()

