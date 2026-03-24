# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 12:34:09 2025

@author: clanglois1
"""
import os
import sys
import numpy as np
import pyqtgraph as pg
from inichord import General_Functions as gf
from inichord import Edit_Tools as sm

import tifffile as tf
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5 import QtCore, QtGui

#------------------------------import for GitHub lib use-------------------------
# import indexGPU.Indexation_lib as indGPU
# from indexGPU.data_classes import Final_Index_res
# import indexGPU.Compute_IPF as IPF_computation
# import indexGPU.Xallo as xa
# from indexGPU import Symetry as sy

#------------------------------import for local dev use------------------------
import Indexation_lib as indGPU
from data_classes import Final_Index_res
import Compute_IPF as IPF_computation
import Xallo as xa
import Symetry as sy
import Dans_Diffraction as da
from Indexation_GUI import MainView
from data_classes import Model

import time
from pyquaternion import Quaternion
import cupy as cp

class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.height = 0
        self.width = 0
        # marker of Controller init
        print("Controller initiated")
        
                
        # Actions, signals and events
        self.view.lineROI_carto.sigRegionChanged.connect(self.updateROI) # Allow the modification of the segment to drawback information
        self.view.expSeries.timeLine.sigPositionChanged.connect(self.drawCHORDprofiles)
        
        self.view.Open_profiles.clicked.connect(self.loadProfiles) # Load serie
        self.view.spinBox_phase_num.valueChanged.connect(self.setPhaseNum)
        self.view.checkBox_otsu.stateChanged.connect(self.setOtsu)
        self.view.Open_data.clicked.connect(self.loadData) # CIF, database, workflow, otsu if necessary
        self.view.Reload_bttn.clicked.connect(self.reload_data) # Load H5 and CIF if needed
        self.view.Save_bttn.clicked.connect(self.Save_results) # Saving process (processing steps, results, infos)
        self.view.Compute_indexation_bttn.clicked.connect(self.Run_indexation) # Run the indexation program
        self.view.OriBox.currentTextChanged.connect(self.Change_IPFView) # Allow different IPF map to be displayed
        
        self.view.TheoProfiles.stateChanged.connect(self.drawCHORDprofiles) # Allow the visualization of the theoretical profiles
        self.view.ModProfiles.stateChanged.connect(self.drawCHORDprofiles) # Allow the visualization of the profiles used for indexing

        self.proxy1 = pg.SignalProxy(self.view.expSeries.scene.sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy4 = pg.SignalProxy(self.view.expSeries.ui.graphicsView.scene().sigMouseClicked, rateLimit=60, slot=self.mouseClick)

        self.proxy2 = pg.SignalProxy(self.view.QualSeries.scene.sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy5 = pg.SignalProxy(self.view.QualSeries.ui.graphicsView.scene().sigMouseClicked, rateLimit=60, slot=self.mouseClick)

        self.proxy3 = pg.SignalProxy(self.view.IPF_serie.scene.sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy6 = pg.SignalProxy(self.view.IPF_serie.ui.graphicsView.scene().sigMouseClicked, rateLimit=60, slot=self.mouseClick)
        
        self.proxy7 = pg.SignalProxy(self.view.PhaseMap.scene.sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy8 = pg.SignalProxy(self.view.PhaseMap.ui.graphicsView.scene().sigMouseClicked, rateLimit=60, slot=self.mouseClick)
        
    def creationListProfilesOtsu(self):
        # Sets the phase map to Otsu map, creates a list of list of coordinates and a list of list of profiles
        self.listCoordPhases = []
        self.phase_map = self.model.preInd.otsu_map

        self.profilesRaw = []
        for i in range (self.model.nPhases):
            coord_phase = np.argwhere(self.phase_map == i)
            self.listCoordPhases.append(coord_phase)
           
            groupProfiles = [] # one group for each phase
            for c in coord_phase:
                groupProfiles.append(self.model.Stack[:, c[0], c[1]])
            self.profilesRaw.append(groupProfiles)

    def labelIndex(self):
        # Search for the labeled map or ask to import it
        # try :
        #     labels = self.parent.Label_image
        #     labels = np.rot90(np.flip(labels, 0), k=1, axes=(1, 0))
        # except:
        #     StackLoc, StackDir = gf.getFilePathDialog("labeled map") 
        #     labels = tf.TiffFile(StackLoc[0]).asarray() # Import the label map
        # self.labels = labels
        
        # Generation of the maps using the information of the clustered map          
        # Create the new arrays using np.where
        for p in range (0, self.model.nPhases):
            self.indexation[p].quality_map_tempo = np.zeros((len(self.labels),len(self.labels[0])))
            self.indexation[p].nScoresOri_tempo = np.zeros((1,4,len(self.labels),len(self.labels[0])))
            self.indexation[p].nScoresDist_tempo = np.zeros((1,len(self.labels),len(self.labels[0])))
            self.indexation[p].rawImage_tempo = np.zeros((len(self.indexation[p].rawImage),len(self.labels),len(self.labels[0])))
            self.indexation[p].nScoresStack_tempo = np.zeros((1,len(self.indexation[p].nScoresStack[0]),len(self.labels),len(self.labels[0])))
            self.indexation[p].Treatment_theo_prof_tempo = np.zeros((1,len(self.indexation[p].Treatment_theo_prof[0]),len(self.labels),len(self.labels[0])))
            self.indexation[p].testArrayList_tempo = np.zeros((len(self.indexation[p].testArrayList),len(self.labels),len(self.labels[0])))
    
            self.view.progressBar.setValue(0)
            self.view.progressBar.setFormat("Map formation: %p%")
            self.view.progressBar.setRange(0, int(np.max(self.labels))-1) # Set the range accordingly to the number of labels
    
            for i in range(1,int(np.max(self.labels))):
                
                QApplication.processEvents()    
                self.view.prgbar = i
                self.view.progression_bar()
                
                var = np.where(self.labels == i)
                self.indexation[p].quality_map_tempo[var] = self.indexation[p].quality_map[:,i-1]
                self.indexation[p].nScoresOri_tempo[:,:,var[0],var[1]] = self.indexation[p].nScoresOri[:,:,:,i-1]
                self.indexation[p].nScoresDist_tempo[:,var[0],var[1]] = self.indexation[p].nScoresDist[:,:,i-1]
                self.indexation[p].rawImage_tempo[:,var[0],var[1]] = self.indexation[p].rawImage[:,:,i-1]
                self.indexation[p].nScoresStack_tempo[:,:,var[0],var[1]] = self.indexation[p].nScoresStack[:,:,:,i-1]
                self.indexation[p].Treatment_theo_prof_tempo[:,:,var[0],var[1]] = self.indexation[p].Treatment_theo_prof[:,:,:,i-1]
                self.indexation[p].testArrayList_tempo[:,var[0],var[1]] = self.indexation[p].testArrayList[:,:,i-1]
            
            # Then replace the arrays 
            self.indexation[p].quality_map = self.indexation[p].quality_map_tempo
            self.indexation[p].nScoresOri = self.indexation[p].nScoresOri_tempo
            self.indexation[p].nScoresDist = self.indexation[p].nScoresDist_tempo
            self.indexation[p].rawImage = self.indexation[p].rawImage_tempo
            self.indexation[p].nScoresStack = self.indexation[p].nScoresStack_tempo
            self.indexation[p].Treatment_theo_prof = self.indexation[p].Treatment_theo_prof_tempo
            self.indexation[p].testArrayList = self.indexation[p].testArrayList_tempo
    
    def phase_map_normal(self):
        # Discrimination based on quality maps
        # Creates a phase map and listCoordPhases 
        
        self.listCoordPhases = []
        
        qualityShape = self.indexation[0].nScoresDist.shape
        
        # If no Grain Boundaries, labels start at 1, else at 0
        # Creation of a new not indexed phase corresponding to GB
        # Creation of a phase map for this new phase
        if  self.model.cluster and 0 in self.labels:
            self.model.nPhases += 1
            self.model.preInd.listToIndex.append(False)
            qual = np.zeros((qualityShape[1], qualityShape[2])) #Creation of a fictive quality map for this new phase
            qual[self.labels == 0] = 1
        
        # Initialisation of the quality map stack
        quality = np.zeros ((self.model.nPhases, qualityShape[1], qualityShape[2]))
        
        # Creation of a quality map stack
        for i in range (self.model.nPhases):
            if self.model.cluster and 0 in self.labels and i == self.model.nPhases-1:
                quality[i, :, :] = qual
            else :
                quality[i, :, :] = self.indexation[i].quality_map
        
        # on prend celui d'indice i, avec i contenant la dernière valeur de la boucle précédente
        # warning : il faut prendre une phase qui n'est pas 'not indexed' !!
        # Run indexation matching step
        try:
            for p, val in enumerate(self.model.preInd.listToIndex):
                if val:
                    self.metric = self.indexation[i].metric
                    self.nW = self.indexation[i].nW
        except:
            self.metric = "cosine"
            self.nW = 10
            
            
        # Table of indices (=phase number) where the quality map is the greatest = phase map
        self.phase_map = np.argmax(quality, axis = 0) 
        for i in range (self.model.nPhases):
            coord_phase = np.argwhere(self.phase_map == i)
            self.listCoordPhases.append(coord_phase)

    def phase_discrimination(self):
        # Rebuild the final objects
        
        if self.model.otsu == False:
            self.phase_map_normal()
            
        # Initialisation of objects
        if  self.model.cluster:
            lenProf = self.indexation[0].rawImage.shape[0]
            width = self.indexation[0].rawImage.shape[2]
            height = self.indexation[0].rawImage.shape[1]
        else:
            lenProf = self.model.Stack.shape[0]
            width = self.model.Stack.shape[2]
            height = self.model.Stack.shape[1]
       
        self.rawImage = np.zeros((lenProf, height, width))
        self.quality_final = np.zeros((height, width))
        self.ori_f = np.zeros((4, height, width))
        self.dist = np.zeros((1, height, width))
        self.theo_stack = np.zeros((lenProf, height, width))
        self.theoStack_mod = np.zeros((lenProf,height, width))
        self.expStack_mod = np.zeros((lenProf, height, width))
        
        listCIF = []
        
        try:
            toIndex = self.model.preInd.listToIndex
        except:
            toIndex = self.listToIndex
        
        
        # for p, val in enumerate(self.preInd.listToIndex):
        for p, val in enumerate(toIndex):
            if val:
                listCIF.append(self.indexation[p].CIF)
                self.metric = self.indexation[p].metric
                self.nW = self.indexation[p].nW                
                #Construction des éléments finaux qui sont un mix des éléments de chaque phase
                for i, c in enumerate(self.listCoordPhases[p]): 
                    if self.model.otsu: # In otsu case, the quality map is an array of shape : (number of pix in phase p, 1)
                        x = i-1
                        y = 0
                    else:         # In normal case, the quality map is an array of shape : (height, width)
                        x = c[0]
                        y = c[1]
                        
                    self.rawImage[:, c[0], c[1]] = self.indexation[p].rawImage[:, x, y]
                    self.quality_final[c[0], c[1]] = self.indexation[p].quality_map[x, y]
                    self.ori_f[:, c[0], c[1]] = self.indexation[p].nScoresOri[0, :, x, y]
                    self.dist[0, c[0], c[1]] = self.indexation[p].nScoresDist[0, x, y]
                    self.theo_stack[:, c[0], c[1]] = self.indexation[p].nScoresStack[0, :, x, y]
                    self.theoStack_mod[:, c[0], c[1]] = self.indexation[p].Treatment_theo_prof[0, :, x, y]
                    self.expStack_mod[:, c[0], c[1]] = self.indexation[p].testArrayList[:, x, y]
                    # on prend celui d'indice i, avec i contenant la dernière valeur de la boucle précédente

        self.view.Info_box.ensureCursorVisible()
        self.view.Info_box.insertPlainText("\n \u2022 Quality map has been computed.")
        QApplication.processEvents()
        
        self.IPF_final_X = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, toIndex, 'X')
        self.IPF_final_Y = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, toIndex, 'Y')
        self.IPF_final_Z = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, toIndex, 'Z')

        self.height = height
        self.width = width
        self.lenProf = lenProf

    def Run_indexation(self):
        
        self.view.progressBar.setVisible(True) # The progress bar is shown for clarity
        self.view.progressBar.setValue(0)
        self.view.progressBar.setFormat("Indexation")
        self.view.Info_box.clear() # Clear the information box
        
        if self.model.otsu:
            self.creationListProfilesOtsu()
        
        # GPU settings
        self.BatchProfiles_value = self.view.Profiles_SpinBox.value() # Number of experimental profiles per batch
        self.BatchDatabase_value = self.view.Database_SpinBox.value() # Number of theoretical profiles per batch
        
        # # instanciation of a Final_Index_res object, to be used for all displays
        # self.res = Final_Index_res(self.model, self.height, self.width, self.lenProf)
        
        self.indexation =  []
        self.metric = self.view.metricCB.currentText()        
        
        # Indexation preparation
        for p, val in enumerate(self.model.preInd.listToIndex):
            if val:
                # "a" is the array of profiles to index
                if self.model.otsu:
                    # créer un sous-ensemble des profils des pixels appartenant à la phase à partir de la carte Otsu.
                    pixInPhase = len(self.listCoordPhases[p])
                    lenProf = len(self.model.Stack)
                    b = np.zeros((pixInPhase, lenProf))
                    b[:, :] = self.profilesRaw[p]
                    
                    a = np.zeros((lenProf, pixInPhase, 1))
                    a[:, :, 0] =  b.T
                else:
                    a = self.model.Stack
                
                self.normType = "centered euclidian"
                self.indexation.append(indGPU.IndexationGPUderiv(self.view, a, 
                                                        self.PathDir, self.model.preInd.phaseList[p].DatabaseLoc, 
                                                        self.model.preInd.phaseList[p].CifLoc,
                                                        self.model.preInd.chunksList[p],
                                                        Workflow = self.model.preInd.phaseList[p].Workflow, 
                                                        normType = self.normType, nbSTACK=self.BatchProfiles_value,
                                                        nbDB = self.BatchDatabase_value, metric = self.metric))
            else:
                self.indexation.append(None)
        
        # Run indexation matching step
        for p, val in enumerate(self.model.preInd.listToIndex):
            if val:
                self.indexation[p].runIndexation()
        
        if self.model.cluster: # Specific to cluster indexation 
            self.labelIndex()

        self.phase_discrimination()
        
        # fill the Final_Index_res with all the data
        self.res.rawImage = self.rawImage
        self.res.expStack_mod = self.expStack_mod
        self.res.theo_stack = self.theo_stack
        self.res.theoStack_mod = self.theoStack_mod
        
        self.res.quality_final = self.quality_final
        self.res.ori_f = self.ori_f
        self.res.dist = self.dist
        self.res.phase_map = self.phase_map
        self.res.IPF_final_X = self.IPF_final_X
        self.res.IPF_final_Y = self.IPF_final_Y
        self.res.IPF_final_Z = self.IPF_final_Z
        self.res.metric = self.metric
        self.res.nW = self.nW
        
        self.res.phase_names = self.model.preInd.phaseIndex.list_phase_name
        
        self.res.savePath = self.PathDir
        self.res.stack_path = self.model.StackDir
        self.res.normType = self.normType
        
        if self.model.cluster:
            self.res.labels = self.labels
        
        self.res.reloadH5 = False
        self.res.savingRes()
        self.res.saving_info_txt()
        
        self.view.Info_box.ensureCursorVisible()
        self.view.Info_box.insertPlainText("\n \u2022 H5 file saved.")
        QApplication.processEvents()

        # display all maps
        self.display_final()

    def quality_map_computation(self, lenProf, theo_stack, rawImage):
        wind_NCC = int(np.round(0.1*lenProf)) # 1/10 of the total length 
        # Computation of quality map
        qualmap = self.NCC_computation(theo_stack, rawImage,  Windows = wind_NCC)
        
        quality_map = qualmap *100 # X100 to display in %
        return quality_map

    def NCC_computation(self, Theo_stack, rawImage, Windows = 18, batchsize = 5000): # Normalized covariance correlation calculation
        
        var, batch_nbr = self.find_batch_nbr(self.height, self.width, batchsize) # Find optimal batch for cupy uses
        
        self.view.prgbar = 0 # Progress bar initial value
        self.view.progressBar.setValue(self.view.prgbar)
        self.view.progressBar.setFormat("Quality computation: %p%")
        self.view.progressBar.setRange(0, int(batch_nbr)-1) # Set the range accordingly to the number of labels
        
        mempool = cp.get_default_memory_pool()
        pinned_mempool = cp.get_default_pinned_memory_pool()
        
        incr = np.linspace(0,len(Theo_stack),Windows+1)
        corrcoeff = np.zeros((len(Theo_stack[0])*len(Theo_stack[0][0])))
        
        test_theo = Theo_stack.reshape((len(Theo_stack),len(Theo_stack[0])*len(Theo_stack[0][0])))
        test_exp = rawImage.reshape((len(rawImage),len(rawImage[0])*len(rawImage[0][0])))
        
        for i in range(int(batch_nbr)):
            QApplication.processEvents()    
            self.view.prgbar = i
            self.view.progression_bar()
            
            NCC = np.zeros(var) # NCC for Normalized Covariance Correlation
            
            mempool.free_all_blocks()
            pinned_mempool.free_all_blocks()
            
            for k in range(0,Windows):
                Theo_stack_wind = cp.asarray(test_theo[int(incr[k]) : int(incr[k+1]) ,var*i:var*(i+1)])
                rawImage_wind = cp.asarray(test_exp[int(incr[k]) : int(incr[k+1]) ,var*i:var*(i+1)])
                
                NCC_var = cp.corrcoef(Theo_stack_wind,rawImage_wind, rowvar = False)
                NCC_var2 = cp.diag(NCC_var[:len(NCC_var)//2, len(NCC_var)//2:])
                NCC_var2 = cp.asnumpy(NCC_var2)
                
                NCC = NCC + NCC_var2
                
                del(NCC_var,NCC_var2)
                
            NCC = NCC/Windows
            
            corrcoeff[var*i:var*(i+1)] = NCC
            
        corrcoeff2 = corrcoeff.reshape((len(Theo_stack[0]),len(Theo_stack[0][0])))
        
        return corrcoeff2
    
    def find_batch_nbr(self, height, width, batch = 5000):  # Find optimal batch for cupy uses
        i = 0
        while height*width % (batch-i) != 0:
            i += 1
        return batch-i, height*width/(batch-i)
    
    def reload_data(self): # Reload the H5 file - 2025_02_26
    
        # If a quality_map already exists, delete it
        try:
            del(self.quality_map)
        except:
            pass
    
        self.reloadH5 = True #a flag to select which operation to do to be specific to the reload situation
        self.flag_folder = 0
        self.view.setWindowTitle("H5 file loading...")
        
        # creation of instance of Final_Index_res
        self.res = self.model.reload_data()
        print("reload nPhases : ", len(self.res.CIF_path))
        
        self.height = self.res.height
        self.width = self.res.width
        self.lenProf = len(self.res.rawImage)
        self.rawImage = self.res.rawImage
        
        self.view.lineROI_carto.setVisible(True)
        self.view.label_phases.setVisible(True)
     
        self.activate_ROI_plots(True)
        self.res.phaseSG = []
        # if len(self.res.CIF_path) > 1:
        #     self.activate_ROI_plots(False)
 
        for p, cif in enumerate(self.res.CIF_path):
            if cif != 'not indexed':
                try:
                    crys = da.functions_crystallography.readcif(cif)
                    self.res.phaseSG.append(crys["_space_group_IT_number"])
                    self.SymQ = sy.get_proper_quaternions_from_CIF(self.res.CIF_path[p])
                    print("CIF found", self.res.CIF_path[p])
                except:
                    CIF_Loc, _ = gf.getFilePathDialog(f"CIF file (*.cif) - disO and phase name (legacy) // actual CIF path : {cif}")
                    print("manual CIF", CIF_Loc[0])
                    self.SymQ = sy.get_proper_quaternions_from_CIF(CIF_Loc[0])
                    self.model.CIF_path = CIF_Loc
                    self.res.CIF_path[p] = CIF_Loc[0]
                    crys = da.functions_crystallography.readcif(CIF_Loc[0])
                    self.res.phaseSG.append(crys["_space_group_IT_number"])
                    
                    
                
 
        # for cif in self.res.CIF_path:
        #     if cif != 'not indexed':
        #         crys = da.functions_crystallography.readcif(cif)
        #         self.res.phaseSG.append(crys["_space_group_IT_number"])
        
        SG = int(self.res.phaseSG[0])
        PG_p = IPF_computation.get_pg_p(SG)
        print(f"ref space group : {SG}, ref point groupe : {PG_p}")
        for sg in self.res.phaseSG:
            # if sg != SG:
            pg_p = IPF_computation.get_pg_p(int(sg))
            print(f"phase space group : {sg}, phase point groupe : {pg_p}")
            if pg_p != PG_p:
                self.activate_ROI_plots(False)
                print("not same proper point group")
         
        self.view.progressBar.setVisible(True) # The progress bar is hidden for clarity
        
        self.view.Info_box.clear() # Clear the information box
        self.view.Info_box.ensureCursorVisible()
        self.view.Info_box.insertPlainText("\n \u2022 Data have been loaded.")
        QApplication.processEvents()

        # recover the unique CIF path, unique because disorientations are (for now) only for one phase
        # or phases with identical space group
        
        # i = 0
        # while self.res.CIF_path[i] == "not indexed":
        #     i += 1
            
        # try:
        #     self.SymQ = sy.get_proper_quaternions_from_CIF(self.res.CIF_path[i])
        #     print("CIF found", self.res.CIF_path[i])
            
        # except:
        #     CIF_Loc, _ = gf.getFilePathDialog("CIF file (*.cif) considered for disO and phase name (legacy)")
        #     print("manual CIF", CIF_Loc[0])
        #     self.SymQ = sy.get_proper_quaternions_from_CIF(CIF_Loc[0])
        #     self.model.CIF_path = CIF_Loc   
        
        
        
        if self.res.legacy:
            print("legacy indexation")
            # Correct data arrays from nScores extra dimension
            self.res.theoStack_mod = self.res.theoStack_mod[0]
            self.res.theo_stack = self.res.theo_stack[0]
            self.res.ori_f = self.res.ori_f[0]

            # Compute IPFs
            toIndex = [True]
            listCIF = self.model.CIF_path
            self.listCoordPhases = []
            self.res.phase_map = np.ones((self.res.height, self.width))
            coord_phase = np.argwhere(self.res.phase_map == 1)
            self.listCoordPhases.append(coord_phase)

            self.view.Info_box.ensureCursorVisible()
            self.view.Info_box.insertPlainText("\n \u2022 Computing IPFs...")
            QApplication.processEvents()
            
            self.view.progressBar.setFormat("IPFs computation: %p%")
            self.view.progressBar.setRange(0, 3)
            self.view.prgbar = 0
            self.view.progression_bar()
            
            self.res.IPF_final_X = IPF_computation.Display_IPF_GUI(listCIF, self.res.ori_f, self.listCoordPhases, toIndex, 'X')
            self.view.prgbar = 1
            self.view.progression_bar()
            
            self.res.IPF_final_Y = IPF_computation.Display_IPF_GUI(listCIF, self.res.ori_f, self.listCoordPhases, toIndex, 'Y')
            self.view.prgbar = 2
            self.view.progression_bar()
            
            self.res.IPF_final_Z = IPF_computation.Display_IPF_GUI(listCIF, self.res.ori_f, self.listCoordPhases, toIndex, 'Z')
            self.view.prgbar = 3
            self.view.progression_bar()
            
            self.view.Info_box.ensureCursorVisible()
            self.view.Info_box.insertPlainText("\n \u2022 IPFs have been computed.")
            QApplication.processEvents()
            
            # Compute Quality map
            self.view.Info_box.ensureCursorVisible()
            self.view.Info_box.insertPlainText("\n \u2022 Computing Quality map...")
            QApplication.processEvents()
            
            self.res.quality_final = self.quality_map_computation(self.res.lenProf, self.res.theo_stack, self.res.rawImage)

            # retrieving the unique phase name from unique CIF
            crys = da.functions_crystallography.readcif(listCIF[0])
            self.res.phase_names.append(crys["_chemical_name_mineral"] + "-" + crys["_space_group_IT_number"])
            print("legacy phase name found : ", self.res.phase_names)

            self.view.Info_box.ensureCursorVisible()
            self.view.Info_box.insertPlainText("\n \u2022 Quality map has been computed")
            QApplication.processEvents()
        else:
            print("not legacy")

        self.view.displayExpStack(self.res.rawImage)
        self.view.displayQuality(self.res.quality_final) # Display the quality map
        self.view.displayIPFmap(self.res.IPF_final_Z)   
        self.view.displayPhaseMap(self.res.phase_map)

        if self.res.legacy:
            self.view.PhaseMap.setVisible(False)
            
        # self.res.saving_info_txt()
        self.view.progressBar.setVisible(False)
        self.updateWindowTitle()

    def activate_ROI_plots(self, b):
        self.view.lineROI_carto.setVisible(b)
        self.view.Plot_distance.setVisible(b)
        self.view.Plot_misorientation.setVisible(b)
        self.view.label_distance.setVisible(b)
        self.view.label_misorientation.setVisible(b)  

    def display_final(self):
        
        self.view.displayExpStack(self.res.rawImage)
        self.view.displayQuality(self.res.quality_final) # Display the quality map
        self.view.displayIPFmap(self.res.IPF_final_Z)   
        self.view.displayPhaseMap(self.res.phase_map)
        self.drawCHORDprofiles()
        self.view.progressBar.setVisible(False) # The progress bar is hidden for clarity
    
    def loadProfiles(self):
        self.rawImage = self.model.loadProfiles()
        
        if self.rawImage.ndim != 3: # Check if the data is not an image series
            self.view.popup_message("IniCHORD","Please import a stack of images or profiles from labellisation / clustering.",'icons/Main_icon.png')
            return 
        else:
            if len(self.rawImage[1]) == 1: #pour cluster, (profiles, hauteur, largeur) avec hauteur=1 car ligne de profiles
                self.model.cluster = True
                # self.expSeries.setVisible(False) # Hide the image serie display window
                self.view.checkBox_otsu.setVisible(False)
                self.view.Info_box.ensureCursorVisible()
                self.view.Info_box.insertPlainText("\n \u2022 Enter in clustering indexation mode.")
                QApplication.processEvents()
                try :
                    labels = self.parent.Label_image
                except:
                    loc, _ = gf.getFilePathDialog("labeled map") 
                    labels = tf.TiffFile(loc[0]).asarray() # Import the label map
                    
                self.labels = labels
                self.view.Info_box.insertPlainText("\n \u2022 Labeled map loadded.")
                QApplication.processEvents()
                
                self.view.displayExpStack(self.labels)

            else: 
                self.cluster = False
                self.view.displayExpStack(self.rawImage)
        self.height = len(self.rawImage[0, :, 0])
        self.width = len(self.rawImage[0, 0, :])
        self.lenProf = len(self.rawImage)
        self.view.setWindowTitle(self.model.StackLoc[0])
        self.Current_stack = self.rawImage

    def loadData(self):
        # Open the phase form to create phases and set indexation parameters, CIF, data base...
        
        self.view.Info_box.clear() # Clear the information box
        self.model.loadData()
        
        # instanciation of a Final_Index_res object, to be used for all displays
        self.res = Final_Index_res(self.model, self.height, self.width, self.lenProf)
        _ = self.res.extract_conditions()
        # Storage folder creation
        ti = time.strftime("%Y-%m-%d__%Hh-%Mm-%Ss") # Absolute time 
        title, phaseInfo = self.updateWindowTitle()
        
        # directory = "Indexation_" + ti # Name of the main folder
        directory = "Indexation_" + ti + phaseInfo # Name of the main folder
        
        self.dir_name = QFileDialog.getExistingDirectory(self.view, "Select a Directory to save indexation results")

        try:
            # self.PathDir = os.path.join(self.model.StackDir, directory)  # where to create the main folder
            self.PathDir = os.path.join(self.dir_name, directory)  # where to create the main folder
            os.mkdir(self.PathDir)  # Create main folder
            self.flag_folder = 1 # Specify if a new folder has to be created when reload ancient data
            self.view.Info_box.ensureCursorVisible()
            self.view.Info_box.insertPlainText("\n \u2022 Data have been loaded.")            
        except:
            self.view.Info_box.ensureCursorVisible()
            self.view.Info_box.insertPlainText("\n \u2022 Import experimental data first, then phase(s) info.")           
        
        
        
        
        QApplication.processEvents()  

    def updateWindowTitle(self):
        # changing the window title with database info
        saveName = ""
        saveName_short = ""
        try: # phase loading wizard just executed so preInd is present
            for p in self.model.preInd.phaseList:
                saveName += "_" + p.name + "_" + str(p.DB_Size) + "  "
                saveName_short += "_" + p.name
        except: # a reLoad has been executed, phase objects not present
            if not self.res.legacy:
                for i, phase in enumerate(self.res.phase_names):
                    print(i, phase)
                    saveName += " " + phase + " " + str(self.res.database_size[i]) + ' diff ' + str(self.res.diff[i]) + '  | '
                    saveName_short += "_" + phase
            else:
                print(self.res.phase_names[0])
                saveName += " " + str(self.res.phase_names[0]) + "  "
                saveName_short += "_" + phase
    
        databasesInfo = saveName[:-2] + " ------------ " + str(self.res.val_kV) + " " + str(self.res.val_deg)
        
        # réduction du chemin de StackLoc
        stackPath = os.path.basename(self.model.StackLoc[0])
                 
        title = stackPath + "    //    Setup :  " + databasesInfo[1:]
        self.view.setWindowTitle(title)
        return title, saveName_short
        

    def updateROI(self, roi): # Specify what must be done when line segment is moved
        # Get coordinates
        Ori_LineROI, ROIcoords = roi.getArrayRegion(self.res.ori_f, self.view.IPF_serie.getImageItem(), axes=(1, 2), returnMappedCoords=True)

        ROIcoords = np.floor(ROIcoords)
        profileLength = len(Ori_LineROI[0, :])  
        
        # Create storage array
        self.disOvalues = np.zeros(profileLength) # Store the misorientation values
        OriValues = np.zeros((4, profileLength)) # Init the array for quaternions
        self.qualValue = np.zeros((1,profileLength))
        
        # Extract the row and column position and search for quality and quaternions values associated
        r_o = int(ROIcoords[0, 0])
        c_o = int(ROIcoords[1, 0])
        
        # print("coords for the array (start): ", r_o, c_o)
        # print("all pure coordinates : ", ROIcoords )
        phase_o = int(self.res.phase_map[c_o, r_o])
        
        try:
            SymQ = self.model.preInd.SymQ[phase_o]
        except:
            SymQ = self.SymQ
        
        for i in range(profileLength):
            r = int(ROIcoords[0, i])
            c = int(ROIcoords[1, i])
            
            # OriValues[:, i] = self.ori_f[:, c, r]
            OriValues[:, i] = self.res.ori_f[:, c, r]
            # self.qualValue[:, i] = self.quality_final[c, r]
            self.qualValue[:, i] = self.res.quality_final[c, r]
        
        self.qualValue = self.qualValue[0,:] # Quality map values
        origineQuat = Quaternion(OriValues[:, 0]).inverse # Inversion of the quaternions
        
        for i in range(profileLength): # For each pixel, compute the disorientation from the origin quaternion
            currentQuat = Quaternion(OriValues[:, i]).inverse
            
            self.disOvalues[i] = xa.disOfromQuatSymNoMat(origineQuat, currentQuat, SymQ)[1]
        
        self.drawqual()
        self.drawMisO()

    def Save_results(self):
        
        self.res.saving_info_txt()
        
        IPF_map_X = self.res.IPF_final_X
        IPF_map_Y = self.res.IPF_final_Y
        IPF_map_Z = self.res.IPF_final_Z
        phaseMap = self.res.phase_map
        quality_map = self.res.quality_final
        dist = self.res.dist
        
        IPF_map_X = (IPF_map_X * 255).astype(np.uint8)
        IPF_map_Y = (IPF_map_Y * 255).astype(np.uint8)
        IPF_map_Z = (IPF_map_Z * 255).astype(np.uint8)
        phaseMap = gf.convertToUint8(phaseMap)
        quality_map = gf.convertToUint8(quality_map)
        dist = gf.convertToUint8(1 - dist)
    
        # Images saving step
                
        # if self.flag_folder == 1:
        #     directory = self.PathDir
        # else:
        #     directory = self.StackDir
        directory = self.res.savePath
        # tf.imwrite(directory + '/Quality_map.tiff', np.rot90(np.flip(self.quality_final, 0), k=1, axes=(1, 0)))
        tf.imwrite(directory + '/Quality_map.tiff', quality_map)
        tf.imwrite(directory + '/Distance_map.tiff', dist)
        tf.imwrite(directory + '/IPF_X.tiff', IPF_map_X)
        tf.imwrite(directory + '/IPF_Y.tiff', IPF_map_Y)
        tf.imwrite(directory + '/IPF_Z.tiff', IPF_map_Z)
        if self.model.nPhases > 1:
            # tf.imwrite(directory + '/Phase_map.tiff', np.rot90(np.flip(phaseMap, 0), k=1, axes=(1,0)))
            tf.imwrite(directory + '/Phase_map.tiff', phaseMap)

        self.res.savingMTEX()

        self.view.Info_box.ensureCursorVisible()
        self.view.Info_box.insertPlainText("\n \u2022 MTex file saved.")
        QApplication.processEvents() 
            
        # Finished message
        self.view.popup_message("indexation[0]","Saving process is over.",'icons/indexation[0]_icon.png')

    def Change_IPFView(self):
        self.OriChoice = self.view.OriBox.currentText() # Choice between X-Y-Z
        
        if self.OriChoice == "IPF-X":
            self.IPF_map = self.res.IPF_final_X
        elif self.OriChoice == "IPF-Y":
            self.IPF_map = self.res.IPF_final_Y
        elif self.OriChoice == "IPF-Z":
            self.IPF_map = self.res.IPF_final_Z
            
        # self.IPF_map = np.flip(self.IPF_map,1)
        # self.IPF_map = np.rot90(self.IPF_map)
        self.view.displayIPFmap(self.IPF_map)

    def drawqual(self): # Display of distances
        try:
            self.view.Plot_distance.clear()           
                      
            pen = pg.mkPen(color=self.view.parent.color4, width=5) # Color and line width of the profile
            self.view.Plot_distance.plot(self.qualValue, pen=pen) # Plot of the profile
            
            styles = {"color": "black", "font-size": "15px", "font-family": "Noto Sans Cond"} # Style for labels
            
            self.view.Plot_distance.setLabel("left", "Quality (%)", **styles) # Import style for Y label
            
            font=QtGui.QFont('Noto Sans Cond', 9) # Font definition of the plot
            
            self.view.Plot_distance.getAxis("left").setTickFont(font) # Apply size of the ticks label
            self.view.Plot_distance.getAxis("left").setStyle(tickTextOffset = 10) # Apply a slight offset

            self.view.Plot_distance.getAxis("bottom").setTickFont(font) # Apply size of the ticks label
            self.view.Plot_distance.getAxis("bottom").setStyle(tickTextOffset = 10) # Apply a slight offset
            
            self.view.Plot_distance.getAxis('left').setTextPen('k') # Set the axis in black
            self.view.Plot_distance.getAxis('bottom').setTextPen('k') # Set the axis in black
            
            self.view.Plot_distance.setBackground(self.view.parent.color2)
            self.view.Plot_distance.showGrid(x=True, y=True)
            
        except:
            pass

    def drawMisO(self): # Display of misorientations

        self.view.Plot_misorientation.clear()           
                  
        pen = pg.mkPen(color=self.view.parent.color4, width=5) # Color and line width of the profile
        self.view.Plot_misorientation.plot(self.disOvalues, pen=pen) # Plot of the profile
        
        styles = {"color": "black", "font-size": "15px", "font-family": "Noto Sans Cond"} # Style for labels
        
        self.view.Plot_misorientation.setLabel("left", "Misorientation (°)", **styles) # Import style for Y label
        
        font=QtGui.QFont('Noto Sans Cond', 9) # Font definition of the plot
        
        self.view.Plot_misorientation.getAxis("left").setTickFont(font) # Apply size of the ticks label
        self.view.Plot_misorientation.getAxis("left").setStyle(tickTextOffset = 10) # Apply a slight offset

        self.view.Plot_misorientation.getAxis("bottom").setTickFont(font) # Apply size of the ticks label
        self.view.Plot_misorientation.getAxis("bottom").setStyle(tickTextOffset = 10) # Apply a slight offset
        
        self.view.Plot_misorientation.getAxis('left').setTextPen('k') # Set the axis in black
        self.view.Plot_misorientation.getAxis('bottom').setTextPen('k') # Set the axis in black
        
        self.view.Plot_misorientation.setBackground(self.view.parent.color2)
        self.view.Plot_misorientation.showGrid(x=True, y=True)

    def drawCHORDprofiles(self): # Display of CHORDprofiles
        
        self.view.profiles.clear()           
        line = self.view.plotIt.addLine(x = self.view.expSeries.currentIndex) # Line associated to the current slice
        line.setPen({'color': (42, 42, 42, 100), 'width': 2}) # Style of the line
        
        self.legend = self.view.profiles.addLegend(horSpacing = 30, labelTextSize = '10pt', colCount = 1, labelTextColor = 'black', brush = self.view.parent.color6, pen = pg.mkPen(color=(0, 0, 0), width=1))
                  
        pen = pg.mkPen(color=self.view.parent.color4, width=5) # Color and line width of the profile
        pen2 = pg.mkPen(color=(48,195,222), width=5) # Color and line width of the profile

        if self.view.TheoProfiles.isChecked():
            if self.view.ModProfiles.isChecked():
                self.view.profiles.plot(self.res.theoStack_mod[:, self.y, self.x], pen=pen2, name='Modified theoretical profiles')
            else:
                self.view.profiles.plot(self.res.theo_stack[:, self.y, self.x], pen=pen2, name='Theoretical profiles') # Plot of the profile

        if self.view.ModProfiles.isChecked():
            self.view.profiles.plot(self.res.expStack_mod[:, self.y, self.x], pen=pen, name='Modified raw profiles')
        else:
            try:
                self.view.profiles.plot(self.res.rawImage[:, self.y, self.x], pen=pen, name='Raw profiles') # Plot of the raw profile
            except:
                self.view.profiles.plot(self.rawImage[:, self.y, self.x], pen=pen, name='Raw profiles') # Plot of the raw profile
        
        styles = {"color": "black", "font-size": "15px", "font-family": "Noto Sans Cond"} # Style for labels
        
        self.view.profiles.setLabel("left", "GrayScale value", **styles) # Import style for Y label
        self.view.profiles.setLabel("bottom", "Slice", **styles) # Import style for X label
        
        font=QtGui.QFont('Noto Sans Cond', 9) # Font definition of the plot
        
        self.view.profiles.getAxis("left").setTickFont(font) # Apply size of the ticks label
        self.view.profiles.getAxis("left").setStyle(tickTextOffset = 10) # Apply a slight offset

        self.view.profiles.getAxis("bottom").setTickFont(font) # Apply size of the ticks label
        self.view.profiles.getAxis("bottom").setStyle(tickTextOffset = 10) # Apply a slight offset
        
        self.view.profiles.getAxis('left').setTextPen('k') # Set the axis in black
        self.view.profiles.getAxis('bottom').setTextPen('k') # Set the axis in black
        
        self.view.profiles.setBackground(self.view.parent.color2)
        self.view.profiles.showGrid(x=True, y=True)
            
    def setPhaseNum(self):
        self.model.nPhases = self.view.spinBox_phase_num.value()
        if self.model.nPhases > 1:
            if self.model.cluster == False:
                self.view.checkBox_otsu.setVisible(True)
            self.view.label_phases.setVisible(True) # Show label phasemap
            self.view.PhaseMap.setVisible(True) # Show phase map
        else:
            self.view.checkBox_otsu.setVisible(False)
            # self.view.label_phases.setVisible(False) # Show label phasemap
            self.view.PhaseMap.setVisible(False) # Show phase map
            self.model.otsu = False

    def setOtsu(self):
        self.model.otsu = self.view.checkBox_otsu.isChecked()

    def mouseMoved(self, e):
        pos = e[0]
        sender = self.view.sender()
       
        if not self.view.mouseLock.isChecked():
            if self.view.expSeries.view.sceneBoundingRect().contains(pos)\
                or self.view.QualSeries.view.sceneBoundingRect().contains(pos)\
                or self.view.IPF_serie.view.sceneBoundingRect().contains(pos)\
                or self.view.PhaseMap.view.sceneBoundingRect().contains(pos):
    
                if sender == self.proxy1:
                    item = self.view.expSeries.view
                elif sender == self.proxy2:
                    item = self.view.QualSeries.view    
                elif sender == self.proxy3:
                    item = self.view.IPF_serie.view
                elif sender == self.proxy7:
                    item = self.view.PhaseMap.view
    
                mousePoint = item.mapSceneToView(pos) 
                     
                self.view.crosshair_v1.setPos(mousePoint.x())
                self.view.crosshair_h1.setPos(mousePoint.y())
                
                self.view.crosshair_v2.setPos(mousePoint.x())
                self.view.crosshair_h2.setPos(mousePoint.y())
                
                self.view.crosshair_v3.setPos(mousePoint.x())
                self.view.crosshair_h3.setPos(mousePoint.y())
                
                self.view.crosshair_v4.setPos(mousePoint.x())
                self.view.crosshair_h4.setPos(mousePoint.y())
    
            self.x = int(mousePoint.x())
            self.y = int(mousePoint.y())

            # if self.x >= 0 and self.y >= 0 and self.x < self.width and self.y < self.height:
            if self.x >= 0 and self.y >= 0 and self.x < self.width and self.y < self.height:

                self.drawCHORDprofiles()
                    
                try:
                    self.view.label_Quality.setText("Quality index: " + str(np.round(self.res.quality_final[self.y, self.x],1)) + "%")
                except:
                    self.view.label_Quality.setText("Quality index: not available yet")
                
                self.view.label_phases.setVisible(True)

                try:
                    p = int(self.res.phase_map[self.y, self.x])
                    name = self.res.phase_names[p]
                except: 
                    name = "not available"

                self.view.label_phases.setText("Phase map: " + name)
    
    def mouseClick(self, e):
        pos = e[0]
        sender = self.view.sender()
        
        self.view.mouseLock.toggle()
        
        fromPosX = pos.scenePos()[0]
        fromPosY = pos.scenePos()[1]
        
        posQpoint = QtCore.QPointF()
        posQpoint.setX(fromPosX)
        posQpoint.setY(fromPosY)

        if self.view.expSeries.view.sceneBoundingRect().contains(posQpoint)\
            or self.view.QualSeries.view.sceneBoundingRect().contains(posQpoint)\
            or self.view.IPF_serie.view.sceneBoundingRect().contains(posQpoint)\
            or self.view.PhaseMap.view.sceneBoundingRect().contains(posQpoint):
                
            if sender == self.proxy4:
                item = self.view.expSeries.view
            elif sender == self.proxy5:
                item = self.view.QualSeries.view
            elif sender == self.proxy6:
                item = self.view.IPF_serie.view
            elif sender == self.proxy8:
                item = self.view.PhaseMap.view
            
            mousePoint = item.mapSceneToView(posQpoint) 

            self.view.crosshair_v1.setPos(mousePoint.x())
            self.view.crosshair_h1.setPos(mousePoint.y())
            
            self.view.crosshair_v2.setPos(mousePoint.x())
            self.view.crosshair_h2.setPos(mousePoint.y())
            
            self.view.crosshair_v3.setPos(mousePoint.x())
            self.view.crosshair_h3.setPos(mousePoint.y())
            
            self.view.crosshair_v4.setPos(mousePoint.x())
            self.view.crosshair_h4.setPos(mousePoint.y())
                 
            self.x = int(mousePoint.x())
            self.y = int(mousePoint.y())
            
            try:
                if self.x >= 0 and self.y >= 0 and self.x < self.width and self.y < self.height:
                    self.drawCHORDprofiles()
                   
                    self.view.quat_textEdit.ensureCursorVisible()
                    formatted_string = ", ".join(f"{nombre:.5f}" for nombre in self.res.ori_f[:, self.y, self.x])
                    # self.view.quat_textEdit.insertPlainText(f"\n \u2022 Quaternion [{self.x}, {self.y}] :\n  {self.res.ori_f[:, self.y, self.x]:.5f}") 
                    self.view.quat_textEdit.insertPlainText(f"\n \u2022 Quaternion [{self.x}, {self.y}] :\n  {formatted_string}") 
                    self.view.quat_textEdit.ensureCursorVisible()
                QApplication.processEvents()
            except:
                pass

                

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
		
		self.model = Model()
		self.w = MainView(self)
		self.controller = Controller(self.model, self.w)
		self.w.show()
		
				
		
#%% Opening of the initial data    
if __name__ == '__main__':
	app = QApplication(sys.argv)
	a = Indexation_orientation()
	app.setQuitOnLastWindowClosed(True)
	app.exec_() 	