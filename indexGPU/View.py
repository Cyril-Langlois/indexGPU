# -*- coding: utf-8 -*-

'Note: le programme ne renvoi rien vers la GUI principale pour le moment (sauf si cela devient necessaire)'

import os

from inspect import getsourcefile
from os.path import abspath

import numpy as np
import pyqtgraph as pg
import tifffile as tf
import time
import cupy as cp
import h5py
import diffpy
import Dans_Diffraction as da
from orix.quaternion import symmetry
from tkinter import filedialog
from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication, QLabel, QDialog, QVBoxLayout, QPushButton
from PyQt5 import QtCore, QtGui

from inichord import General_Functions as gf
import indexGPU.Xallo as xa
# import indexGPU.Indexation_lib as indGPU
import Indexation_lib as indGPU
# from indexGPU import Compute_IPF as IPF_computation
import Compute_IPF as IPF_computation
from indexGPU import Symetry as sy
# from indexGPU import phaseGUI_classes as phaseClass
# import phaseGUI_classes as phaseClass
import phaseGUI_classes_local as phaseClass

from pyquaternion import Quaternion

path2thisFile = abspath(getsourcefile(lambda:0))
uiclass, baseclass = pg.Qt.loadUiType(os.path.dirname(path2thisFile) + "/Indexation_GUI_tempo2.ui")

class MainWindow(uiclass, baseclass):
    def __init__(self, parent):
        super().__init__()
        
        self.setupUi(self)
        self.parent = parent
        
        self.setWindowIcon(QtGui.QIcon('icons/Indexation_icon.png'))
        self.Info_box.setFontPointSize(10) # Set fontsize of the information box
        
        self.lineROI_carto = pg.LineSegmentROI([[0, -10], [20, -10]], pen=(1,9)) # Create a segment in the IPF widget
        
                
        self.crosshair_v1 = pg.InfiniteLine(angle=90, movable=False, pen=self.parent.color5)
        self.crosshair_h1 = pg.InfiniteLine(angle=0, movable=False, pen=self.parent.color5)
        
        self.crosshair_v2 = pg.InfiniteLine(angle=90, movable=False, pen=self.parent.color5)
        self.crosshair_h2 = pg.InfiniteLine(angle=0, movable=False, pen=self.parent.color5)
        
        self.crosshair_v3 = pg.InfiniteLine(angle=90, movable=False, pen=self.parent.color5)
        self.crosshair_h3 = pg.InfiniteLine(angle=0, movable=False, pen=self.parent.color5)
        
        self.crosshair_v4 = pg.InfiniteLine(angle=90, movable=False, pen=self.parent.color5)
        self.crosshair_h4 = pg.InfiniteLine(angle=0, movable=False, pen=self.parent.color5)
        
        self.plotIt = self.profiles.getPlotItem()
        self.plotIt.addLine(x = self.expSeries.currentIndex) # Add vertical line to the CHORD profile widget
        
        self.defaultdrawCHORDprofiles()     # Default draw profile (when empty)
        self.defaultIV() # Default ImageView 
        
        self.progressBar.setVisible(False) # The progress bar is hidden for clarity
        self.mouseLock.setVisible(False)
        
        self.Cluster_index.setVisible(False) # Hide cluster choice 
        self.label_phases.setVisible(False) # Hide label phasemap
        self.PhaseMap.setVisible(False) # Hide phase map
        self.checkBox_otsu.setVisible(False) # Hide Z-contrast checkBox
        
        self.window_SpinBox.setVisible(False) # Hide window length for savgol
        self.poly_SpinBox.setVisible(False) # Hide order for savgol
        
        self.savgol_label1.setVisible(False) # Hide window label for savgol
        self.savgol_label2.setVisible(False) # Hide order label for savgol
        self.PresetBox.setVisible(False)

        app = QApplication.instance()
        screen = app.screenAt(self.pos())
        geometry = screen.availableGeometry()
        
        self.move(int(geometry.width() * 0.05), int(geometry.height() * 0.05))
        self.resize(int(geometry.width() * 0.9), int(geometry.height() * 0.8))
        self.screen = screen
        

#%% Functions

    def popup_message(self,title,text,icon):
        msg = QDialog(self) # Create a Qdialog box
        msg.setWindowTitle(title)
        msg.setWindowIcon(QtGui.QIcon(icon))
        
        label = QLabel(text) # Create a QLabel for the text
        
        font = label.font() # Modification of the font
        font.setPointSize(8)  # Font size modification
        label.setFont(font)
        
        label.setAlignment(QtCore.Qt.AlignCenter) # Text centering
        label.setWordWrap(False)  # Deactivate the line return

        ok_button = QPushButton("OK") # Creation of the Qpushbutton
        ok_button.clicked.connect(msg.accept)  # Close the box when pushed
        
        layout = QVBoxLayout() # Creation of the vertical layout
        layout.addWidget(label)       # Add text
        layout.addWidget(ok_button)   # Add button
        
        msg.setLayout(layout) # Apply position 
        msg.adjustSize() # Automatically adjust size of the window
        
        msg.exec_() # Display the message box
        
    def Reload_data(self): # Reload the H5 file - 2025_02_26
    
        # If a quality_map already exists, delete it
        try:
            del(self.quality_map)
        except:
            pass
    
        self.reloadH5 = True #a flag to select which operation to do to be specific to the reload situation
        self.Info_box.clear() # Clear the information box
        self.flag_folder = 0
        
        # Locate indexation file *.h5
        self.StackLoc, self.StackDir = gf.getFilePathDialog("Indexation result (*.hdf5)") # Ask for the H5 result file
    
        f = h5py.File(self.StackLoc[0], 'r') # In order to read the H5 file
        listKeys = gf.get_dataset_keys(f) # Extract the listKeys of the H5 files
        
        # load data from the h5 file        
        for i in listKeys:
            if "meanDisO" in i: # Extract meanDisO
                meanDisO = np.asarray(f[i])
            elif "nScoresDisO" in i: # Extract nScoresDisO
                nScoresDisO = np.asarray(f[i])
            elif "nScoresDist" in i: # Extract the distance
                nScoresDist = np.asarray(f[i])
            elif "nScoresStack" in i: # Extract the theoretical stack
                nScoresStack = np.asarray(f[i])
            elif "nScoresOri" in i: # Extract the quaternions
                nScoresOri = np.asarray(f[i])
            elif "rawImage" in i: # Extract the experimental stack
                rawImage = np.asarray(f[i])
            elif "Treatment_theo_prof" in i: # Extract the theoretical stack in it modified shape
                Treatment_theo_prof = np.asarray(f[i])
            elif "testArrayList" in i: # Extract the experimental stack in it modified shape
                testArrayList = np.asarray(f[i])
            elif "quality_map" in i: # Extract the quality map
                quality_map = np.asarray(f[i])
        
        try: # Try to open testArrayList (modified exp profiles). In case of it doesn't exist, it become the raw stack 
            testArrayList = testArrayList.reshape((len(testArrayList),len(rawImage[0]),len(rawImage[0][0])))
        except:
            testArrayList = rawImage
            
        try: # Try to open Treatment_theo_prof (modified theo profiles). In case of it doesn't exist, it become the theoretical stack 
            Treatment_theo_prof =Treatment_theo_prof.reshape((len(Treatment_theo_prof),len(Treatment_theo_prof[0]),len(rawImage[0]),len(rawImage[0][0])))
        except:
            Treatment_theo_prof = nScoresStack
        
        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 Data have been loaded.")
        QApplication.processEvents()
        
        # Crystal information (single phase only) in the H5 file
        self.CIFpath = []
        self.nPhases = 1

        for h in range(self.nPhases):
            listKeys = gf.get_group_keys(f) # Extract ListKeys in order to determine the path of the CIF location
            for i in listKeys:
                if "indexation" in i:
                    for k in f[i].attrs.keys():
                        if "CIF path" in k:
                            self.CIFpath.append(f[i].attrs[k])

        try: # Try to use this path to extract the wanted data
            self.SymQ = sy.get_proper_quaternions_from_CIF(self.CIFpath[0])
            
        except: # If the location is unreachable, then it is mandatory to search manually
            self.popup_message("Indexation","Please import the CIF file",'icons/Indexation_icon.png')
            self.CIFpath[0] = filedialog.askopenfilename(title='fichier CIF', multiple=True)[0]
            self.SymQ = sy.get_proper_quaternions_from_CIF(self.CIFpath[0])

        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 CIF file has been loaded.")
        QApplication.processEvents()

        # Create self.Current_stack with flip and rotation
        self.Current_stack = rawImage # Extract the stack of images
        self.Current_stack = np.flip(self.Current_stack, 1) # Flip the array
        self.Current_stack = np.rot90(self.Current_stack, k=1, axes=(2, 1)) # Rotate the array
        self.displayExpStack(self.Current_stack) # Display the 3D array

        self.slice_nbr = len(self.Current_stack) # Nbr of slice in the stack
        self.wind_NCC = int(np.round(0.1*self.slice_nbr)) # 1/10 of the total length 

        # Computation of quality map
        try : 
            self.quality_final = self.quality_map 
            
            self.quality_final = np.flip(self.quality_final, 0) # Flip the array
            self.quality_final = np.rot90(self.quality_final, k=1, axes=(1, 0)) # Rotate the array

        except :    
            self.progressBar.setVisible(True) # The progress bar is shown for clarity
            self.qualmap = self.NCC_computation(nScoresStack[0,:,:,:],rawImage, batchsize = 5000, Windows = self.wind_NCC)
    
            self.quality_map = self.qualmap *100 # X100 to display in %
            self.quality_final = self.quality_map  
            
            self.quality_final = np.flip(self.quality_final, 0) # Flip the array
            self.quality_final = np.rot90(self.quality_final, k=1, axes=(1, 0)) # Rotate the array
            
            self.Info_box.ensureCursorVisible()
            self.Info_box.insertPlainText("\n \u2022 Quality map has been computed.")
            QApplication.processEvents()
            self.progressBar.setVisible(False) # The progress bar is hidden for clarity
        
        self.displayQuality(self.quality_final) # Display the quality map

        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 Computation of IPF maps in progress.")
        QApplication.processEvents()

        # Creation of self.indexation.xxx to be as the run_indexation approach
        FakeIndexation = SimpleNamespace()
        self.indexation =  [FakeIndexation]

        self.indexation[0].nScoresDist = nScoresDist
        self.indexation[0].CIF = self.CIFpath[0]
        self.indexation[0].nScoresOri = nScoresOri
        self.indexation[0].nScoresStack = nScoresStack
        self.indexation[0].rawImage = rawImage
        self.indexation[0].Treatment_theo_prof = Treatment_theo_prof
        self.indexation[0].quality_final = self.quality_map
        self.indexation[0].quality_map = self.quality_map
        self.indexation[0].testArrayList = testArrayList

        # run phase_discrimination to compute appropriate data to mimick a pixel indexation
        self.listToIndex = [True]
        self.phase_discrimination()

        # Flip and rotate self.nScoresDist to be homogenenous (for computation)
        self.nScoresDist = nScoresDist
        self.nScoresDist = np.flip(self.nScoresDist, 1)
        self.nScoresDist = np.rot90(self.nScoresDist, k=1, axes=(2, 1))
                   
        # Keep the first and only score, then swapaxes
        self.ori = nScoresOri[0,:,:,:]
        self.ori = np.swapaxes(self.ori, 1, 2)
        
        # For viewing data diff or not OR theo profiles : extract of the first and only score then flip and rotate
        self.theo_stack = nScoresStack[0, :, :, :]
        self.theo_stack = np.flip(self.theo_stack, 1)
        self.theo_stack = np.rot90(self.theo_stack, k=1, axes=(2, 1))
        
        self.stack_mod = Treatment_theo_prof[0, :, :, :]
        self.stack_mod = np.flip(self.stack_mod, 1)
        self.stack_mod = np.rot90(self.stack_mod, k=1, axes=(2, 1))
        
        self.expStack_mod = testArrayList
        self.expStack_mod = np.flip(self.expStack_mod, 1)
        self.expStack_mod = np.rot90(self.expStack_mod, k=1, axes=(2, 1))
       
        # Display of IPF map 
        self.IPF_map = self.IPF_final_Z
        self.IPF_map = np.flip(self.IPF_map,1)
        self.IPF_map = np.rot90(self.IPF_map)
        
        self.displayIPFmap(self.IPF_map) 
        
    def savingRes_cluster(self):
        ti = time.strftime("%Y-%m-%d__%Hh-%Mm-%Ss")
        
        indexSTACK = h5py.File(self.indexation[0].savePath + '\Cluster_indexScores_'+ ti + '.hdf5', 'a')
        
        group = indexSTACK.create_group('indexation[0]')
        group.create_dataset(name='nScoresStack', data=self.indexation[0].nScoresStack)
        group.create_dataset(name='Treatment_theo_prof', data=self.indexation[0].Treatment_theo_prof) #Profil théo modifiés
        group.create_dataset(name='rawImage', data=self.indexation[0].rawImage)
        group.create_dataset(name='nScoresDist', data=self.indexation[0].nScoresDist)
        group.create_dataset(name='nScoresOri', data=self.indexation[0].nScoresOri)
        group.create_dataset(name='Ref_Pr_list3', data=self.indexation[0].Ref_Pr_list2)
        group.create_dataset(name='testArrayList', data=self.indexation[0].testArrayList) #Profil expé modifiés
        group.create_dataset(name='quality_map', data=self.indexation[0].quality_map) #Profil expé modifiés
                 
        group.attrs.create("profile length", self.indexation[0].actualProfLength)
        group.attrs.create("dbChunks", self.indexation[0].dbChunks)
        group.attrs.create("height", self.indexation[0].height)
        group.attrs.create("width", self.indexation[0].width)
        group.attrs.create("CIF path", self.indexation[0].CIF)
        group.attrs.create("stack path", self.indexation[0].savePath)
        group.attrs.create("database path", self.indexation[0].DB)
        group.attrs.create("normalization before indexation[0]", self.indexation[0].normType)
        group.attrs.create("metric for indexation[0]", "cosine")
        group.attrs.create("nbSTACK", self.indexation[0].nbSTACK)
        group.attrs.create("nbDB", self.indexation[0].nbDB)
        
        indexSTACK.flush()
        indexSTACK.close()

        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 Clustering H5 file saved.")
        QApplication.processEvents()
        
    def progression_bar(self): # Function for the ProgressBar uses
        # self.prgbar = self.ValSlice
        self.progressBar.setValue(self.prgbar)

    def Save_results(self):
        
        IPF_map_X = self.IPF_final_X
        IPF_map_Y = self.IPF_final_Y
        IPF_map_Z = self.IPF_final_Z
        phaseMap = self.phase_map
        
        IPF_map_X = (IPF_map_X * 255).astype(np.uint8)
        IPF_map_Y = (IPF_map_Y * 255).astype(np.uint8)
        IPF_map_Z = (IPF_map_Z * 255).astype(np.uint8)
        phaseMap = gf.convertToUint8(phaseMap)
    
        # Images saving step
                
        if self.flag_folder == 1:
            directory = self.PathDir
        else:
            directory = self.StackDir
        tf.imwrite(directory + '/Quality_map.tiff', np.rot90(np.flip(self.quality_final, 0), k=1, axes=(1, 0)))
        tf.imwrite(directory + '/Distance_map.tiff',1-self.dist)
        tf.imwrite(directory + '/IPF_X.tiff', IPF_map_X)
        tf.imwrite(directory + '/IPF_Y.tiff', IPF_map_Y)
        tf.imwrite(directory + '/IPF_Z.tiff', IPF_map_Z)
        if self.nPhases > 1:
            tf.imwrite(directory + '/Phase_map.tiff', np.rot90(np.flip(phaseMap, 0), k=1, axes=(1,0)))
            
        # Finished message
        self.popup_message("indexation[0]","Saving process is over.",'icons/indexation[0]_icon.png')


    def defaultdrawCHORDprofiles(self): # Default display of CHORDprofiles
        # Image serie
        self.profiles.clear()
        self.profiles.setBackground(self.parent.color2)
        
        self.profiles.getPlotItem().hideAxis('bottom')
        self.profiles.getPlotItem().hideAxis('left')
        
        # Distances
        self.Plot_distance.clear()
        self.Plot_distance.setBackground(self.parent.color2)
        
        self.Plot_distance.getPlotItem().hideAxis('bottom')
        self.Plot_distance.getPlotItem().hideAxis('left')
        
        # Misorientation profile
        self.Plot_misorientation.clear()
        self.Plot_misorientation.setBackground(self.parent.color2)
        
        self.Plot_misorientation.getPlotItem().hideAxis('bottom')
        self.Plot_misorientation.getPlotItem().hideAxis('left')


        
    def drawqual(self): # Display of distances
        try:
            self.Plot_distance.clear()           
                      
            pen = pg.mkPen(color=self.parent.color4, width=5) # Color and line width of the profile
            self.Plot_distance.plot(self.qualValue, pen=pen) # Plot of the profile
            
            styles = {"color": "black", "font-size": "15px", "font-family": "Noto Sans Cond"} # Style for labels
            
            self.Plot_distance.setLabel("left", "Quality (%)", **styles) # Import style for Y label
            
            font=QtGui.QFont('Noto Sans Cond', 9) # Font definition of the plot
            
            self.Plot_distance.getAxis("left").setTickFont(font) # Apply size of the ticks label
            self.Plot_distance.getAxis("left").setStyle(tickTextOffset = 10) # Apply a slight offset

            self.Plot_distance.getAxis("bottom").setTickFont(font) # Apply size of the ticks label
            self.Plot_distance.getAxis("bottom").setStyle(tickTextOffset = 10) # Apply a slight offset
            
            self.Plot_distance.getAxis('left').setTextPen('k') # Set the axis in black
            self.Plot_distance.getAxis('bottom').setTextPen('k') # Set the axis in black
            
            self.Plot_distance.setBackground(self.parent.color2)
            self.Plot_distance.showGrid(x=True, y=True)
            
        except:
            pass

    def drawMisO(self): # Display of misorientations
        try:
            self.Plot_misorientation.clear()           
                      
            pen = pg.mkPen(color=self.parent.color4, width=5) # Color and line width of the profile
            self.Plot_misorientation.plot(self.disOvalues, pen=pen) # Plot of the profile
            
            styles = {"color": "black", "font-size": "15px", "font-family": "Noto Sans Cond"} # Style for labels
            
            self.Plot_misorientation.setLabel("left", "Misorientation (°)", **styles) # Import style for Y label
            
            font=QtGui.QFont('Noto Sans Cond', 9) # Font definition of the plot
            
            self.Plot_misorientation.getAxis("left").setTickFont(font) # Apply size of the ticks label
            self.Plot_misorientation.getAxis("left").setStyle(tickTextOffset = 10) # Apply a slight offset

            self.Plot_misorientation.getAxis("bottom").setTickFont(font) # Apply size of the ticks label
            self.Plot_misorientation.getAxis("bottom").setStyle(tickTextOffset = 10) # Apply a slight offset
            
            self.Plot_misorientation.getAxis('left').setTextPen('k') # Set the axis in black
            self.Plot_misorientation.getAxis('bottom').setTextPen('k') # Set the axis in black
            
            self.Plot_misorientation.setBackground(self.parent.color2)
            self.Plot_misorientation.showGrid(x=True, y=True)
            
        except:
            pass

    def displayExpStack(self, exp_stack):
        
        # on place ici le flip-rot car ce n'est que de l'affichage
        # deux cas de figure selon que l'on a une stack 3D classique ou des 
        # profils issus de clustering / grains / otsu
        
        try:
            exp_stack = np.flip(exp_stack, 1) # Flip the array
            exp_stack = np.rot90(exp_stack, k=1, axes=(2, 1)) # Rotate the array
        except:
            exp_stack = np.rot90(np.flip(exp_stack, 1), k=-1, axes=(1,0))
            
        self.expSeries.addItem(self.crosshair_v1, ignoreBounds=True)
        self.expSeries.addItem(self.crosshair_h1, ignoreBounds=True) 
        
        self.expSeries.ui.histogram.hide()
        self.expSeries.ui.roiBtn.hide()
        self.expSeries.ui.menuBtn.hide()
        
        view = self.expSeries.getView()
        state = view.getState()        
        self.expSeries.setImage(exp_stack) 
        view.setState(state)
        
        view.setBackgroundColor(self.parent.color1)
        ROIplot = self.expSeries.getRoiPlot()
        ROIplot.setBackground(self.parent.color1)
        
        font=QtGui.QFont('Noto Sans Cond', 8)
        ROIplot.getAxis("bottom").setTextPen('k') # Apply size of the ticks label
        ROIplot.getAxis("bottom").setTickFont(font)
        
        self.expSeries.timeLine.setPen(color=self.parent.color3, width=15)
        self.expSeries.frameTicks.setPen(color=self.parent.color1, width=5)
        self.expSeries.frameTicks.setYRange((0, 1))

        s = self.expSeries.ui.splitter
        s.handle(1).setEnabled(True)
        s.setStyleSheet("background: 5px white;")
        s.setHandleWidth(5)
        
    def displayQuality(self, quality_map): # Display of initial KAD map
        self.QualSeries.addItem(self.crosshair_v2, ignoreBounds=True)
        self.QualSeries.addItem(self.crosshair_h2, ignoreBounds=True) 
        
        self.QualSeries.ui.histogram.show()
        self.QualSeries.ui.roiBtn.hide()
        self.QualSeries.ui.menuBtn.hide()
        
        view = self.QualSeries.getView()
        state = view.getState()        
        
        quality_map = np.flip(quality_map, 0) # Flip the array
        quality_map = np.rot90(quality_map, k=1, axes=(1, 0)) # Rotate the array
        
        self.QualSeries.setImage(quality_map) 
        view.setState(state)
        view.setBackgroundColor(self.parent.color1)
        
        histplot = self.QualSeries.getHistogramWidget()
        histplot.setBackground(self.parent.color1)
        
        histplot.region.setBrush(pg.mkBrush(self.parent.color5 + (120,)))
        histplot.region.setHoverBrush(pg.mkBrush(self.parent.color5 + (60,)))
        histplot.region.pen = pg.mkPen(self.parent.color5)
        histplot.region.lines[0].setPen(pg.mkPen(self.parent.color5, width=2))
        histplot.region.lines[1].setPen(pg.mkPen(self.parent.color5, width=2))
        histplot.fillHistogram(color = self.parent.color5)        
        histplot.autoHistogramRange()
        
        self.QualSeries.setColorMap(pg.colormap.get('CET-I3'))
        
    def displayIPFmap(self, IPF):
        self.IPF_serie.addItem(self.crosshair_v3, ignoreBounds=True)
        self.IPF_serie.addItem(self.crosshair_h3, ignoreBounds=True) 
        self.IPF_serie.addItem(self.lineROI_carto)
        
        self.IPF_serie.ui.histogram.hide()
        self.IPF_serie.ui.roiBtn.hide()
        self.IPF_serie.ui.menuBtn.hide()
        
        IPF = np.flip(IPF,1)
        IPF = np.rot90(IPF)
        
        self.IPF_serie.setImage(IPF)
        self.IPF_serie.autoRange()
        
    def displayPhaseMap(self, phase_map):
        
        phase_map = np.flip(phase_map, 1)
        phase_map = np.rot90(phase_map, k=1, axes=(0,1))
        
        self.PhaseMap.addItem(self.crosshair_v4, ignoreBounds=True)
        self.PhaseMap.addItem(self.crosshair_h4, ignoreBounds=True) 
        
        self.PhaseMap.ui.histogram.hide()
        self.PhaseMap.ui.roiBtn.hide()
        self.PhaseMap.ui.menuBtn.hide()
        
        view = self.PhaseMap.getView()
        state = view.getState()        
        self.PhaseMap.setImage(phase_map) 
        view.setState(state)
        view.setBackgroundColor(self.parent.color1)
        
        histplot = self.PhaseMap.getHistogramWidget()
        histplot.setBackground(self.parent.color1)
        
        self.PhaseMap.setColorMap(pg.colormap.get('CET-L10'))
        self.PhaseMap.autoRange()
        
    def defaultIV(self):
        # Image series
        self.expSeries.clear()
        self.expSeries.ui.histogram.hide()
        self.expSeries.ui.roiBtn.hide()
        self.expSeries.ui.menuBtn.hide()
        
        view = self.expSeries.getView()
        view.setBackgroundColor(self.parent.color1)
        
        ROIplot = self.expSeries.getRoiPlot()
        ROIplot.setBackground(self.parent.color1)
        
        # Quality index
        self.QualSeries.clear()
        self.QualSeries.ui.histogram.hide()
        self.QualSeries.ui.roiBtn.hide()
        self.QualSeries.ui.menuBtn.hide()
        
        view = self.QualSeries.getView()
        view.setBackgroundColor(self.parent.color1)
                
        # IPF orientation
        self.IPF_serie.clear()
        self.IPF_serie.ui.histogram.hide()
        self.IPF_serie.ui.roiBtn.hide()
        self.IPF_serie.ui.menuBtn.hide()
        
        view = self.IPF_serie.getView()
        view.setBackgroundColor(self.parent.color1)
        
        # Phase map
        self.PhaseMap.clear()
        self.PhaseMap.ui.histogram.hide()
        self.PhaseMap.ui.roiBtn.hide()
        self.PhaseMap.ui.menuBtn.hide()
        
        view = self.PhaseMap.getView()
        view.setBackgroundColor(self.parent.color1)
