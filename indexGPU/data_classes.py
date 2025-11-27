# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 12:33:53 2025

@author: clanglois1
"""
import os
import numpy as np
from inichord import General_Functions as gf

import tifffile as tf
import h5py

import time

#------------------------------import for GitHub use-------------------------
# import indexGPU.phaseGUI_classes_local as phaseClass
# import indexGPU.Indexation_lib as indGPU
# import indexGPU.Xallo as xa
# from indexGPU import Symetry as sy

#------------------------------import for local dev use------------------------
import phaseGUI_classes_local as phaseClass
import Indexation_lib as indGPU
import Xallo as xa
import Symetry as sy


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
        self.StackLoc, self.StackDir = gf.getFilePathDialog("Image series to index (*.tiff)")
        self.Stack = tf.TiffFile(self.StackLoc[0]).asarray() # Check for dimension. If 2 dimensions : 2D array. If 3 dimensions : stack of images
        self.Current_stack = self.Stack # Extract the stack of images 
        return self.Stack
    
    def loadData(self):
        self.preInd = preIndexation(self) # Ask to open phase form
    
    def reload_data(self):

        self.reloadH5 = True
        self.nPhases = 0

        # Locate indexation file *.h5
        self.StackLoc, self.StackDir = gf.getFilePathDialog("Indexation result (*.hdf5)") # Ask for the H5 result file
    
        f = h5py.File(self.StackLoc[0], 'r') # In order to read the H5 file
        list_dataset_Keys = gf.get_dataset_keys(f) # Extract the listKeys of the H5 files
        list_group_Keys = gf.get_group_keys(f) # Extract the listKeys of the H5 files

        self.CIF_path = []
        self.phase_names = []
        self.database_path = []
        self.database_size = []
        self.diff = []
        
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
                self.database_path.append(group.attrs['database path'])
                self.nPhases += 1
                
            if "database size" in list_attributs:    
                self.database_size.append(group.attrs['database size'])
                self.diff.append(group.attrs['index deriv'])
                self.phase_names.append(i)
                

        self.indexRes = Final_Index_res(self, self.height, self.width, self.lenProf)
        self.indexRes.CIF_path = self.CIF_path
        self.indexRes.savePath = self.StackDir
        self.indexRes.phase_names = self.phase_names
        self.indexRes.database_path = self.database_path
        self.indexRes.database_size = self.database_size
        self.indexRes.diff = self.diff
        self.indexRes.reloadH5 = True

        for i in list_group_Keys:
            group = f[i]
            list_attributs = list(group.attrs.keys())
            
            if "nPhases" in list_attributs:
                self.nPhases = group.attrs['nPhases']            
            if "cluster" in list_attributs:
                self.cluster = group.attrs['cluster']  
                print(f"correct reading cluster {self.cluster}")
            if "otsu" in list_attributs:
                self.otsu = group.attrs['otsu'] 
                print(f"correct reading otsu {self.otsu}")
            if "stack path" in list_attributs:
                self.indexRes.stack_path = group.attrs['stack path']
            if "normalization before indexation" in list_attributs:
                self.indexRes.normType = group.attrs['normalization before indexation']                
            if "metric for Indexation" in list_attributs:
                self.indexRes.metric = group.attrs['metric for Indexation']
         
        for i in list_dataset_Keys:
            if "dist" in i or "nScoresDist" in i: # Extract the distance
                self.indexRes.dist = np.asarray(f[i])
            if "theo_stack" in i or "nScoresStack" in i: # Extract the theoretical stack
                self.indexRes.theo_stack = np.asarray(f[i])
            if "ori_f" in i or "nScoresOri" in i: # Extract the quaternions
                self.indexRes.ori_f = np.asarray(f[i])
            if "rawImage" in i: # Extract the experimental stack
                self.indexRes.rawImage = np.asarray(f[i])
            if "theoStack_mod" in i or "Treatment_theo_prof" in i: # Extract the theoretical stack in it modified shape
                self.indexRes.theoStack_mod = np.asarray(f[i])
            if "expStack_mod" in i or "testArrayList" in i: # Extract the experimental stack in it modified shape
                self.indexRes.expStack_mod = np.asarray(f[i])
            if "quality_final" in i: # Extract the quality map
                self.indexRes.quality_final = np.asarray(f[i])
            if "phase_map" in i: # Extract the quality map
                self.indexRes.phase_map = np.asarray(f[i])
                self.indexRes.legacy = False
            if "IPF_final_X" in i: # Extract the quality map
                self.indexRes.IPF_final_X = np.asarray(f[i])
            if "IPF_final_Y" in i: # Extract the quality map
                self.indexRes.IPF_final_Y = np.asarray(f[i])
            if "IPF_final_Z" in i: # Extract the quality map
                self.indexRes.IPF_final_Z = np.asarray(f[i])
            if "labels" in i: # Extract the quality map
                self.indexRes.labels = np.asarray(f[i])
        
        # considering the cluster and otsu cases
        
        self.indexRes.cluster = self.cluster
        self.indexRes.otsu = self.otsu
        # print(f"flag cluster : {self.indexRes.cluster}, flag otsu : {self.indexRes.otsu}")
        
        if self.indexRes.cluster:
            self.indexRes.height = len(self.indexRes.labels)
            self.indexRes.width = len(self.indexRes.labels[0])
        
        # pour mettre kV et deg en attributs de l'objet res
        _ = self.indexRes.extract_conditions()

        # delete any pre-existing preInd object
        try:
            del self.preInd
        except:
            pass
        print(f" CIF_path list : {self.indexRes.CIF_path}")
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
        
        # paths and text attr
        self.savePath = ""
        self.CIF_path = ""
        self.stack_path = ""
        self.database_path = ""
        self.normType = "centered euclidian"
        self.metric = "cosine"
        

    def savingRes(self):
        ti = time.strftime("%Y-%m-%d__%Hh-%Mm-%Ss")
        self.saveName = ""
        for p in self.model.preInd.phaseList:
            self.saveName += "_" + p.name
            
        self.saveName += self.extract_conditions()

        # indexSTACK = h5py.File(self.savePath + '\IndexData_'+ ti + '.hdf5', 'a')
        # indexSTACK = h5py.File(self.savePath + "\Indexation_" + self.saveName +  ti + ".hdf5", 'a')
        indexSTACK = h5py.File(self.savePath + "\Indexation_" + ti + self.saveName + ".hdf5", 'a')
        
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
        group.attrs.create("normalization before indexation", self.normType)
        group.attrs.create("metric for Indexation", self.metric)
        
        i = 0
        for p in self.model.preInd.phaseList:
            try:
                group_p = indexSTACK.create_group(p.name)
                group_p.attrs.create("CIF path", p.CifLoc)
                group_p.attrs.create("database path", p.DatabaseLoc)
                group_p.attrs.create("database size", p.DB_Size)
                group_p.attrs.create("index deriv", p.diff)
                group_p.attrs.create("Savitzky Golay", p.SG)
                group_p.attrs.create("Savitzky Golay_poly", p.SG_poly)
                group_p.attrs.create("Savitzky Golay_window", p.SG_win)                
            except:
                group_p = indexSTACK.create_group(str(i))
                group_p.attrs.create("CIF path", "not indexed")
                group_p.attrs.create("database path", "not indexed")
                group_p.attrs.create("database size", "not indexed")
                group_p.attrs.create("index deriv", "not indexed")
                group_p.attrs.create("Savitzky Golay", "not indexed")
                group_p.attrs.create("Savitzky Golay_poly", "not indexed")
                group_p.attrs.create("Savitzky Golay_window", "not indexed")  
            i += 1

        indexSTACK.flush()
        indexSTACK.close()

    def extract_conditions(self):
        save_name = ""
        
        try:
            i = 0
            while self.model.preInd.phaseList[i].DatabaseLoc == None and i < 10:
                i +=1
        
            if i < 10:
                p = self.model.preInd.phaseList[i]
            dbName = os.path.basename(p.DatabaseLoc)
            
        except:
            i = 0
            while self.database_path[i] == 'not indexed':
                i +=1
            dbName = self.database_path[i]

        self.val_kV = self.extract_str(dbName, "kV")
        self.val_deg = self.extract_str(dbName, "deg")
    
        save_name = "_" + self.val_kV + "_" + self.val_deg + "_"
       
        return save_name
            
    def extract_str(self, string, mark):
            index = string.find(mark)
            try:
                val = int(string[index - 2])
                val = string[index - 2] + string[index - 1]
            except:
                val = string[index - 1]
            
            return val + mark
    
    def saving_info_txt(self):
        print("enter saving indexation info.txt")
        ti = time.strftime("%Y-%m-%d__%Hh-%Mm-%Ss")
        
        with open(self.savePath + '\Indexation_'+ ti + '_info.txt', 'w') as file:
            
            file.write("----------------- Indexation info  --------------------" + '\n')
            file.write("acc. voltage : " + str(self.val_kV) + '\n')
            file.write("tilt angle (deg) : " + str(self.val_deg) + '\n'*2)
            
            file.write("lenProf : " + str(self.lenProf) + '\n')
            file.write("height : " + str(self.height) + '\n')
            file.write("width : " + str(self.width) + '\n')
            file.write("nPhases : " + str(self.nPhases) + '\n')
            file.write("cluster : " + str(self.cluster) + '\n')
            file.write("otsu : " + str(self.otsu) + '\n')
            file.write("stack path : " + str(self.stack_path) + '\n')
            file.write("normalization before indexation : " + str(self.normType) + '\n')
            file.write("metric for Indexation : " + str(self.metric) + '\n')
            
            if self.metric != 'cosine':
                file.write("       if metric = NCC, window nb : " + str(self.nW) + '\n'*3)
            
            
            if not self.reloadH5:
                i = 0
                file.write("----------------- Phase(s) information --------------------" + '\n')
                for p in self.model.preInd.phaseList:
                    try:
                        file.write(str(p.name) + '\n')
                        file.write("     CIF path : " + str(p.CifLoc) + '\n')
                        file.write("     database path : " + str(p.DatabaseLoc) + '\n')
                        file.write("     database size : " + str(p.DB_Size) + '\n')
                        file.write("     index deriv : " + str(p.diff) + '\n')
                        file.write("     Savitzky Golay / " + str(p.SG) + '\n')
                        file.write("     Savitzky Golay_poly : " + str(p.SG_poly) + '\n')
                        file.write("     Savitzky Golay_window : " + str(p.SG_win) + '\n')              
                    except: 
                        file.write("Phase non indexed : " + str(i))
    
                    i += 1
            else:
                for i in range(len(self.phase_names)):
                    file.write('\n'*3 + "----------------- Phase(s) information --------------------" + '\n')
                    file.write(str(self.phase_names[i]) + '\n')
                    file.write("     CIF path : " + str(self.CIF_path[i]) + '\n')
                    try:
                        file.write("     database path : " + str(self.database_path[i]) + '\n')
                        file.write("     database size : " + str(self.database_size[i]) + '\n')
                        file.write("     index deriv : " + str(self.diff[i]) + '\n')
                    except:
                        file.write("--- legacy indexation - some info missing ---" + '\n')

                    
                
    def savingMTEX(self):
        
        Quat = self.ori_f
        x = len(Quat[0])
        y = len(Quat[0][0])

        ti = time.strftime("%Y-%m-%d__%Hh-%Mm-%Ss")
        
        self.saveName = ""
        for p in self.phase_names:
            self.saveName += p + "-"
        
        self.saveName = self.saveName + "_" + self.val_kV + "_" + self.val_deg + "_"

        with open(self.savePath + '\CHORD_'+ self.saveName + ti + '.quatCHORDv3-CTFxyConv.txt', 'w') as file:

            for i in range(x):
                for j in range(y):

                    # index = 1    
                    index = self.phase_map[i, j]
                    if Quat[0,i,j] ==0 :
                        index = 0
                    file.write(str(index) + '\t' + str(j) + '\t' + str(i) + '\t' + str(Quat[0, i, j]) +
                    '\t' + str(Quat[1, i, j])  + '\t' + str(Quat[2, i, j])  + '\t' + str(Quat[3, i, j]) + '\n')
            
            
                    
    
        