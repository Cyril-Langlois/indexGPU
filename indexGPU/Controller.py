# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 12:34:09 2025

@author: clanglois1
"""
import os
import numpy as np
import pyqtgraph as pg
from inichord import General_Functions as gf
import indexGPU.Xallo as xa
import tifffile as tf
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore, QtGui
# import indexGPU.Indexation_lib as indGPU
import Indexation_lib_MVC as indGPU
import Compute_IPF as IPF_computation
import time
from pyquaternion import Quaternion

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
        self.view.Reload_bttn.clicked.connect(self.view.Reload_data) # Load H5 and CIF if needed
        self.view.Save_bttn.clicked.connect(self.view.Save_results) # Saving process (processing steps, results, infos)
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
                groupProfiles.append(self.model.Stack[:, c[1], c[0]])
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
        if  self.cluster and 0 in self.labels:
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

       
        print("lenProf : ", lenProf, "height : ", height, "  width : ", width)
        self.rawImage = np.zeros((lenProf, height, width))
        self.quality_final = np.zeros((height, width))
        self.ori_f = np.zeros((4, height, width))
        self.dist = np.zeros((1, height, width))
        self.theo_stack = np.zeros((lenProf, height, width))
        self.stack_mod = np.zeros((lenProf,height, width))
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
                
                #Construction des éléments finaux qui sont un mix des éléments de chaque phase
                for i, c in enumerate(self.listCoordPhases[p]): 
                    if self.model.otsu: # In otsu case, the quality map is an array of shape : (number of pix in phase p, 1)
                        x = i-1
                        y = 0
                        diffIm = self.indexation[p].diffImage2D.reshape((lenProf, len(self.listCoordPhases[p]), 1))
                    else:         # In normal case, the quality map is an array of shape : (height, width)
                        x = c[0]
                        y = c[1]
                        if self.model.cluster:
                            diffIm = self.indexation[p].testArrayList
                        else:
                            if not self.reloadH5:
                                diffIm = self.indexation[p].diffImage2D.reshape((lenProf, height, width))
                            else:
                                diffIm = self.indexation[p].rawImage
                        
                    self.rawImage[:, c[0], c[1]] = self.indexation[p].rawImage[:, x, y]
                    self.quality_final[c[0], c[1]] = self.indexation[p].quality_map[x, y]
                    self.ori_f[:, c[0], c[1]] = self.indexation[p].nScoresOri[0, :, x, y]
                    self.dist[0, c[0], c[1]] = self.indexation[p].nScoresDist[0, x, y]
                    self.theo_stack[:, c[0], c[1]] = self.indexation[p].nScoresStack[0, :, x, y]
                    self.stack_mod[:, c[0], c[1]] = self.indexation[p].Treatment_theo_prof[0, :, x, y]
                    
                    if not self.reloadH5:
                        self.expStack_mod[:, c[0], c[1]] = diffIm[:, x, y]
                    else:
                        self.expStack_mod[:, c[0], c[1]] = self.indexation[p].rawImage[:, x, y]
                     
                
        # self.IPF_final_X = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, self.preInd.listToIndex, 'X')
        # self.IPF_final_Y = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, self.preInd.listToIndex, 'Y')
        # self.IPF_final_Z = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, self.preInd.listToIndex, 'Z')
        
        self.IPF_final_X = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, toIndex, 'X')
        self.IPF_final_Y = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, toIndex, 'Y')
        self.IPF_final_Z = IPF_computation.Display_IPF_GUI(listCIF, self.ori_f, self.listCoordPhases, toIndex, 'Z')


    def Run_indexation(self):
        
        self.view.progressBar.setVisible(True) # The progress bar is shown for clarity
        self.view.progressBar.setValue(0)
        self.view.progressBar.setFormat("Indexation")
        self.view.Info_box.clear() # Clear the information box
        # self.methodChoice = self.PresetBox.currentText() # Choice between diff0 or diff1
        
        
        if self.model.otsu:
            self.creationListProfilesOtsu()
            self.view.displayPhaseMap(self.phase_map)
        
        # GPU settings
        self.BatchProfiles_value = self.view.Profiles_SpinBox.value() # Number of experimental profiles per batch
        self.BatchDatabase_value = self.view.Database_SpinBox.value() # Number of theoretical profiles per batch
        
        self.indexation =  []
        
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
                    
                self.indexation.append(indGPU.IndexationGPUderiv(self.view, a, 
                                                        self.PathDir, self.model.preInd.phaseList[p].DatabaseLoc, 
                                                        self.model.preInd.phaseList[p].CifLoc,
                                                        self.model.preInd.chunksList[p],
                                                        Workflow = self.model.preInd.phaseList[p].Workflow, 
                                                        normType = "centered euclidian", nbSTACK=self.BatchProfiles_value,
                                                        nbDB = self.BatchDatabase_value))
            else:
                self.indexation.append(None)
        
        # Run indexation matching step
        for p, val in enumerate(self.model.preInd.listToIndex):
            if val:
                self.indexation[p].runIndexation()
        
        if self.model.cluster: # Specific to cluster indexation 
            self.labelIndex()

        self.phase_discrimination()
            
        # Flip and rotate for display or computation
        
        # self.ori = np.swapaxes(self.ori_f, 1, 2)
        self.view.displayQuality(self.quality_final) # Display the quality map
                
        # self.expSeries.setVisible(True) # Show the image serie display window
        
#        self.displayExpStack(self.rawImage) # Display the 3D array
        
        self.view.Info_box.ensureCursorVisible()
        self.view.Info_box.insertPlainText("\n \u2022 Quality map has been computed.")
        QApplication.processEvents()
        
        # Flip and rotate self.nScoresDist to be homogenenous (for computation)
        self.dist = np.flip(self.dist, 1)
        self.dist = np.rot90(self.dist, k=1, axes=(2, 1))
        
        # For viewing data diff or not OR theo profiles : extract of the first and only score then flip and rotate       
        # self.Current_stack = self.rawImage # Extract the stack of images

        # self.rawImage = np.flip(self.rawImage, 1)
        # self.rawImage = np.rot90(self.rawImage, k=1, axes=(2, 1))
        
        self.theo_stack = self.indexation[0].nScoresStack[0, :, :, :]
        # self.theo_stack = np.flip(self.theo_stack, 1)
        # self.theo_stack = np.rot90(self.theo_stack, k=1, axes=(2, 1))
        
        self.stack_mod = self.indexation[0].Treatment_theo_prof[0, :, :, :]
        # self.stack_mod = np.flip(self.stack_mod, 1)
        # self.stack_mod = np.rot90(self.stack_mod, k=1, axes=(2, 1))
        
        self.expStack_mod = self.indexation[0].testArrayList
        # self.expStack_mod = np.flip(self.expStack_mod, 1)
        # self.expStack_mod = np.rot90(self.expStack_mod, k=1, axes=(2, 1))
        
        # Display of IPF map 
        self.IPF_map = self.IPF_final_Z
        self.view.displayIPFmap(self.IPF_map)   

        self.view.displayPhaseMap(self.phase_map)
        
        self.view.progressBar.setVisible(False) # The progress bar is hidden for clarity
   
    
    def loadProfiles(self):
        stack = self.model.loadProfiles()
        
        if stack.ndim != 3: # Check if the data is not an image series
            self.view.popup_message("IniCHORD","Please import a stack of images or profiles from labellisation / clustering.",'icons/Main_icon.png')
            return 
        else:
            if len(stack[1]) == 1: #pour cluster, (profiles, hauteur, largeur) avec hauteur=1 car ligne de profiles
                self.model.cluster = True
                # self.expSeries.setVisible(False) # Hide the image serie display window
                self.view.checkBox_otsu.setVisible(False)
                self.view.Info_box.ensureCursorVisible()
                self.view.Info_box.insertPlainText("\n \u2022 Enter in clustering indexation mode.")
                QApplication.processEvents()
                try :
                    labels = self.parent.Label_image
                    labels = np.rot90(np.flip(labels, 0), k=1, axes=(0, 1))
                except:
                    loc, _ = gf.getFilePathDialog("labeled map") 
                    labels = tf.TiffFile(loc[0]).asarray() # Import the label map
                    
                self.labels = labels

                self.view.Info_box.insertPlainText("\n \u2022 Labeled map loadded.")
                QApplication.processEvents()
            else: 
                self.cluster = False
                 # Display the 3D array
                print("Current Stack shape after import : ", stack.shape)

        print("traitement loadProfiles traité par Controleur")
        self.height = len(stack[0, :, 0])
        self.width = len(stack[0, 0, :])
        self.view.displayExpStack(stack)

    def loadData(self):
        # Open the phase form to create phases and set indexation parameters, CIF, data base...
        
        self.reloadH5 = False
        self.view.Info_box.clear() # Clear the information box
        self.model.loadData()
                
        # Storage folder creation
        ti = time.strftime("%Y-%m-%d__%Hh-%Mm-%Ss") # Absolute time 
        
        directory = "Indexation_" + ti # Name of the main folder
        try:
            self.PathDir = os.path.join(self.model.StackDir, directory)  # where to create the main folder
            os.mkdir(self.PathDir)  # Create main folder
            self.flag_folder = 1 # Specify if a new folder has to be created when reload ancient data
            self.view.Info_box.ensureCursorVisible()
            self.view.Info_box.insertPlainText("\n \u2022 Data have been loaded.")            
        except:
            self.view.Info_box.ensureCursorVisible()
            self.view.Info_box.insertPlainText("\n \u2022 Import experimental data first, then phase(s) info.")           

        QApplication.processEvents()  

    def updateROI(self, roi): # Specify what must be done when line segment is moved
        # Get coordinates
        Ori_LineROI, ROIcoords = roi.getArrayRegion(self.ori_f, self.IPF_serie.getImageItem(), axes=(1, 2), returnMappedCoords=True)

        ROIcoords = np.floor(ROIcoords)
        profileLength = len(Ori_LineROI[0, :])  
        
        # Create storage array
        self.disOvalues = np.zeros(profileLength) # Store the misorientation values
        OriValues = np.zeros((4, profileLength)) # Init the array for quaternions
        self.qualValue = np.zeros((1,profileLength))
        
        # Extract the row and column position and search for quality and quaternions values associated
        r_o = int(ROIcoords[0, 0])
        c_o = int(ROIcoords[1, 0])
        phase_o = int(self.phase_map[r_o, c_o])
        
        try:
            SymQ = self.preInd.SymQ[phase_o]
        except:
            SymQ = self.SymQ
        
        for i in range(profileLength):
            r = int(ROIcoords[0, i])
            c = int(ROIcoords[1, i])
            OriValues[:, i] = self.ori_f[:, r, c]
            self.qualValue[:, i] = self.quality_final[r, c]
        
        self.qualValue = self.qualValue[0,:] # Quality map values
        origineQuat = Quaternion(OriValues[:, 0]).inverse # Inversion of the quaternions
        
        for i in range(profileLength): # For each pixel, compute the disorientation from the origin quaternion
            currentQuat = Quaternion(OriValues[:, i]).inverse
            
            self.disOvalues[i] = xa.disOfromQuatSymNoMat(origineQuat, currentQuat, SymQ)[1]
        
        self.drawqual()
        self.drawMisO()

    def Change_IPFView(self):
        self.OriChoice = self.view.OriBox.currentText() # Choice between X-Y-Z
        
        if self.OriChoice == "IPF-X":
            self.IPF_map = self.IPF_final_X
        elif self.OriChoice == "IPF-Y":
            self.IPF_map = self.IPF_final_Y
        elif self.OriChoice == "IPF-Z":
            self.IPF_map = self.IPF_final_Z
            
        # self.IPF_map = np.flip(self.IPF_map,1)
        # self.IPF_map = np.rot90(self.IPF_map)
        self.view.displayIPFmap(self.IPF_map)

    def drawCHORDprofiles(self): # Display of CHORDprofiles
        # try:
        self.view.profiles.clear()           
        line = self.view.plotIt.addLine(x = self.view.expSeries.currentIndex) # Line associated to the current slice
        line.setPen({'color': (42, 42, 42, 100), 'width': 2}) # Style of the line
        
        self.legend = self.view.profiles.addLegend(horSpacing = 30, labelTextSize = '10pt', colCount = 1, labelTextColor = 'black', brush = self.view.parent.color6, pen = pg.mkPen(color=(0, 0, 0), width=1))
                  
        pen = pg.mkPen(color=self.view.parent.color4, width=5) # Color and line width of the profile
        pen2 = pg.mkPen(color=(48,195,222), width=5) # Color and line width of the profile

        if self.view.TheoProfiles.isChecked():
            if self.view.ModProfiles.isChecked():
                self.view.profiles.plot(self.stack_mod[:, self.y, self.x], pen=pen2, name='Modified theoretical profiles')
            else:
                self.view.profiles.plot(self.theo_stack[:, self.y, self.x], pen=pen2, name='Theoretical profiles') # Plot of the profile

        if self.view.ModProfiles.isChecked():
            self.view.profiles.plot(self.expStack_mod[:, self.y, self.x], pen=pen, name='Modified raw profiles')
        else:
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
            
        # except:
        #     pass

    def setPhaseNum(self):
        self.model.nPhases = self.view.spinBox_phase_num.value()
        if self.model.nPhases > 1:
            if self.model.cluster == False:
                self.view.checkBox_otsu.setVisible(True)
            self.view.label_phases.setVisible(True) # Show label phasemap
            self.view.PhaseMap.setVisible(True) # Show phase map
        else:
            self.view.checkBox_otsu.setVisible(False)
            self.view.label_phases.setVisible(False) # Show label phasemap
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
    
            try:
                self.x = int(mousePoint.x())
                self.y = int(mousePoint.y())
                    
            except:
                pass

            try:
                if self.x >= 0 and self.y >= 0 and self.x < self.width and self.y < self.height:
                    self.drawCHORDprofiles()
                    self.view.label_Quality.setText("Quality index: " + str(np.round(self.quality_final[self.y, self.x],1)) + "%")
                    if self.nPhases > 1:
                        p = int(self.phase_map[self.y, self.x])
                        if self.model.preInd.listToIndex[p]:
                            name = self.model.preInd.phaseList[p].name
                        else:
                            name = "Not indexed"
                        self.view.label_phases.setVisible(True)
                        self.view.label_phases.setText("Phase map: " + name)
            except:
                pass
    
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
            except:
                pass