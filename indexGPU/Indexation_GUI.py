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
from indexGPU import Compute_IPF as IPF_computation
from indexGPU import Symetry as sy
# from indexGPU import phaseGUI_classes as phaseClass
# import phaseGUI_classes as phaseClass
import phaseGUI_classes_local as phaseClass

from pyquaternion import Quaternion

path2thisFile = abspath(getsourcefile(lambda:0))
uiclass, baseclass = pg.Qt.loadUiType(os.path.dirname(path2thisFile) + "/Indexation_GUI_tempo.ui")

class MainWindow(uiclass, baseclass):
    def __init__(self, parent):
        super().__init__()
        
        self.setupUi(self)
        self.parent = parent
        
        self.setWindowIcon(QtGui.QIcon('icons/Indexation_icon.png'))
        self.Info_box.setFontPointSize(10) # Set fontsize of the information box
        
        self.lineROI_carto = pg.LineSegmentROI([[0, -10], [20, -10]], pen=(1,9)) # Create a segment in the IPF widget
        self.lineROI_carto.sigRegionChanged.connect(self.updateROI) # Allow the modification of the segment to drawback information
                
        self.crosshair_v1 = pg.InfiniteLine(angle=90, movable=False, pen=self.parent.color5)
        self.crosshair_h1 = pg.InfiniteLine(angle=0, movable=False, pen=self.parent.color5)
        
        self.crosshair_v2 = pg.InfiniteLine(angle=90, movable=False, pen=self.parent.color5)
        self.crosshair_h2 = pg.InfiniteLine(angle=0, movable=False, pen=self.parent.color5)
        
        self.crosshair_v3 = pg.InfiniteLine(angle=90, movable=False, pen=self.parent.color5)
        self.crosshair_h3 = pg.InfiniteLine(angle=0, movable=False, pen=self.parent.color5)
        
        self.plotIt = self.profiles.getPlotItem()
        self.plotIt.addLine(x = self.expSeries.currentIndex) # Add vertical line to the CHORD profile widget
        
        self.proxy1 = pg.SignalProxy(self.expSeries.scene.sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy4 = pg.SignalProxy(self.expSeries.ui.graphicsView.scene().sigMouseClicked, rateLimit=60, slot=self.mouseClick)

        self.proxy2 = pg.SignalProxy(self.QualSeries.scene.sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy5 = pg.SignalProxy(self.QualSeries.ui.graphicsView.scene().sigMouseClicked, rateLimit=60, slot=self.mouseClick)

        self.proxy3 = pg.SignalProxy(self.IPF_serie.scene.sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy6 = pg.SignalProxy(self.IPF_serie.ui.graphicsView.scene().sigMouseClicked, rateLimit=60, slot=self.mouseClick)

        self.expSeries.timeLine.sigPositionChanged.connect(self.drawCHORDprofiles)
        
        self.defaultdrawCHORDprofiles()     # Default draw profile (when empty)
        self.defaultIV() # Default ImageView 

        self.Open_data.clicked.connect(self.loaddata) # Load serie, CIF and database
        self.Reload_bttn.clicked.connect(self.Reload_data) # Load H5 and CIF if needed
        self.Save_bttn.clicked.connect(self.Save_results) # Saving process (processing steps, results, infos)
        self.Compute_indexation_bttn.clicked.connect(self.Run_indexation) # Run the indexation program
        self.OriBox.currentTextChanged.connect(self.Change_IPFView) # Allow different IPF map to be displayed
        self.progressBar.setVisible(False) # The progress bar is hidden for clarity
        self.mouseLock.setVisible(False)
        
        self.Cluster_index.setVisible(False) # Hide cluster choice 
        self.label_phases.setVisible(False) # Hide label phasemap
        self.PhaseMap.setVisible(False) # Hide phase map
        
        self.window_SpinBox.setVisible(False) # Hide window length for savgol
        self.poly_SpinBox.setVisible(False) # Hide order for savgol
        
        self.savgol_label1.setVisible(False) # Hide window label for savgol
        self.savgol_label2.setVisible(False) # Hide order label for savgol
        
        self.PresetBox.currentIndexChanged.connect(self.hide_and_show)

        self.TheoProfiles.stateChanged.connect(self.drawCHORDprofiles) # Allow the visualization of the theoretical profiles
        self.ModProfiles.stateChanged.connect(self.drawCHORDprofiles) # Allow the visualization of the profiles used for indexing
        self.treeWidget.itemSelectionChanged.connect(self.handle_item_tree) # Va regarder dans quel cas on est

        app = QApplication.instance()
        screen = app.screenAt(self.pos())
        geometry = screen.availableGeometry()
        
        self.move(int(geometry.width() * 0.05), int(geometry.height() * 0.05))
        self.resize(int(geometry.width() * 0.9), int(geometry.height() * 0.8))
        self.screen = screen

#%% Functions
    def hide_and_show(self):
        self.methodChoice = self.PresetBox.currentText() # Choice between diff0 or diff1
        
        if self.methodChoice == "Savgol derivative indexation":
            self.window_SpinBox.setVisible(True) # Show window length for savgol
            self.poly_SpinBox.setVisible(True) # Show order for savgol
            
            self.savgol_label1.setVisible(True) # Show window label for savgol
            self.savgol_label2.setVisible(True) # Show order label for savgol
        else : 
            self.window_SpinBox.setVisible(False) # Hide window length for savgol
            self.poly_SpinBox.setVisible(False) # Hide order for savgol
            
            self.savgol_label1.setVisible(False) # Hide window label for savgol
            self.savgol_label2.setVisible(False) # Hide order label for savgol

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
        
    def loaddata(self): # Allow to load the image serie, the CIF file and the database
        self.Info_box.clear() # Clear the information box
    
        self.nPhases = 1
        self.phaseNumGUI = phaseClass.phaseNum(self)
        self.phaseNumGUI.exec_()
        
        self.preInd = indGPU.preIndexation(self) # Ask to open the three files
        
        # Creation of self.Current_stack to be use elsewhere
        self.Current_stack = self.preInd.Stack # Extract the stack of images
        self.Current_stack = np.flip(self.Current_stack, 1) # Flip the array
        self.Current_stack = np.rot90(self.Current_stack, k=1, axes=(2, 1)) # Rotate the array
        
        if self.Cluster_index.isChecked(): # Specific to cluster indexation 
            self.expSeries.setVisible(False) # Hide the image serie display window
            
            self.Info_box.ensureCursorVisible()
            self.Info_box.insertPlainText("\n \u2022 Enter in clustering indexation mode.")
            QApplication.processEvents()
            
        else:
            self.displayExpStack(self.Current_stack) # Display the 3D array

        # # self.SymQ = sy.get_proper_quaternions_from_CIF(self.preInd.CifLoc) # Get the variable symQ for symmetry of quaternions
        # self.SymQ = sy.get_proper_quaternions_from_CIF(self.preInd.phaseList[0].CifLoc) # Get the variable symQ for symmetry of quaternions
        
        # Storage folder creation
        ti = time.strftime("%Y-%m-%d__%Hh-%Mm-%Ss") # Absolute time 
        
        directory = "Indexation_" + ti # Name of the main folder
        self.PathDir = os.path.join(self.preInd.StackDir, directory)  # where to create the main folder
        os.mkdir(self.PathDir)  # Create main folder
        
        self.flag_folder = 1 # Specify if a new folder has to be created when reload ancient data
        
        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 Data have been loaded.")
        QApplication.processEvents()

    def handle_item_tree(self):
        selected_items = self.treeWidget.selectedItems()
        if selected_items:
            item = selected_items[0]
            item_text = item.text(0)

            if item_text == "Raw indexation (SP)":
                self.Cluster_index.setChecked(False)
                self.Info_box.ensureCursorVisible()
                self.Info_box.insertPlainText("\n \u2022 Raw indexation on single phase.")
                QApplication.processEvents()
            elif item_text == "Indexation from label (SP)":
                self.Cluster_index.setChecked(True)
                self.Info_box.ensureCursorVisible()
                self.Info_box.insertPlainText("\n \u2022 Label based indexation on single phase.")
                QApplication.processEvents()
            elif item_text == "Raw indexation (ZA)":
                self.Cluster_index.setChecked(False)
                self.Info_box.ensureCursorVisible()
                self.Info_box.insertPlainText("\n \u2022 Z-Multiphase : raw indexation.")
                QApplication.processEvents()
            elif item_text == "Indexation from label (ZA)":
                self.Cluster_index.setChecked(True)
                self.Info_box.ensureCursorVisible()
                self.Info_box.insertPlainText("\n \u2022 Z-Multiphase : label based indexation.")
                QApplication.processEvents()
            elif item_text == "Raw indexation (PA)":
                self.Cluster_index.setChecked(False)
                self.Info_box.ensureCursorVisible()
                self.Info_box.insertPlainText("\n \u2022 Phase-Multiphase : raw indexation.")
                QApplication.processEvents()            
            elif item_text == "Indexation from label (PA)":
                self.Cluster_index.setChecked(True)
                self.Info_box.ensureCursorVisible()
                self.Info_box.insertPlainText("\n \u2022 Phase-Multiphase : label based indexation.")
                QApplication.processEvents()                 
            else :
                self.Info_box.ensureCursorVisible()
                self.Info_box.insertPlainText("\n \u2022 Not a method.")
                QApplication.processEvents()
                pass
            
        else:
            pass

    def Reload_data(self): # Reload the H5 file
        try:
            del(self.quality_map)
        except:
            pass
    
        self.Info_box.clear() # Clear the information box
        self.flag_folder = 0
        
        self.StackLoc, self.StackDir = gf.getFilePathDialog("Indexation result (*.hdf5)") # Ask for the H5 result file
    
        f = h5py.File(self.StackLoc[0], 'r') # In order to read the H5 file
        listKeys = gf.get_dataset_keys(f) # Extract the listKeys of the H5 files
                
        for i in listKeys:
            if "meanDisO" in i: # Extract meanDisO
                self.meanDisO = np.asarray(f[i])
            elif "nScoresDisO" in i: # Extract nScoresDisO
                self.nScoresDisO = np.asarray(f[i])
            elif "nScoresDist" in i: # Extract the distance
                self.nScoresDist = np.asarray(f[i])
            elif "nScoresStack" in i: # Extract the theoretical stack
                self.nScoresStack = np.asarray(f[i])
            elif "nScoresOri" in i: # Extract the quaternions
                self.nScoresOri = np.asarray(f[i])
            elif "rawImage" in i: # Extract the experimental stack
                self.rawImage = np.asarray(f[i])
            elif "Treatment_theo_prof" in i: # Extract the theoretical stack in it modified shape
                self.Treatment_theo_prof = np.asarray(f[i])
            elif "testArrayList" in i: # Extract the experimental stack in it modified shape
                self.testArrayList = np.asarray(f[i])
            elif "quality_map" in i: # Extract the quality map
                self.quality_map = np.asarray(f[i])
                    
        try: # Try to open testArrayList (modified exp profiles). In case of it doesn't exist, it become the raw stack 
            self.testArrayList = self.testArrayList.reshape((len(self.testArrayList),len(self.rawImage[0]),len(self.rawImage[0][0])))
        except:
            self.testArrayList = self.rawImage
            
        try: # Try to open Treatment_theo_prof (modified theo profiles). In case of it doesn't exist, it become the theoretical stack 
            self.Treatment_theo_prof = self.Treatment_theo_prof.reshape((len(self.Treatment_theo_prof),len(self.Treatment_theo_prof[0]),len(self.rawImage[0]),len(self.rawImage[0][0])))
        except:
            self.Treatment_theo_prof = self.nScoresStack
        
        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 Data have been loaded.")
        QApplication.processEvents()
        
        # Crystal information (single phase only) in the H5 file
        self.CIFpath = []
        self.nbPhases = 1
        self.phases = [] 

        for h in range(self.nbPhases):
            listKeys = gf.get_group_keys(f) # Extract ListKeys in order to determine the path of the CIF location
            for i in listKeys:
                if "indexation" in i:
                    for k in f[i].attrs.keys():
                        if "CIF path" in k:
                            self.CIFpath.append(f[i].attrs[k])

        try: # Try to use this path to extract the wanted data
            self.phases.append(diffpy.structure.loadStructure(self.CIFpath[0]))
            self.crys = da.functions_crystallography.readcif(self.CIFpath[0])
            self.SymQ = sy.get_proper_quaternions_from_CIF(self.CIFpath[0])
            
        except: # If the location is unreachable, then it is mandatory to search manually
            self.popup_message("Indexation","Please import the CIF file",'icons/Indexation_icon.png')
            self.CIFpath[0] = filedialog.askopenfilename(title='fichier CIF', multiple=True)[0]
            
            self.phases.append(diffpy.structure.loadStructure(self.CIFpath[0]))
            self.crys = da.functions_crystallography.readcif(self.CIFpath[0])
            self.SymQ = sy.get_proper_quaternions_from_CIF(self.CIFpath[0])

        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 CIF file has been loaded.")
        QApplication.processEvents()

        self.PhaseName = self.crys["_chemical_formula_sum"]
        self.numSG = self.crys["_space_group_IT_number"]
        self.PG = symmetry.get_point_group(int(self.numSG), True).name

        self.SymQ = sy.get_proper_quaternions_from_CIF(self.CIFpath[0]) # Get the variable symQ for symmetry of quaternions

        # Create self.Current_stack with flip and rotation
        self.Current_stack = self.rawImage # Extract the stack of images
        self.Current_stack = np.flip(self.Current_stack, 1) # Flip the array
        self.Current_stack = np.rot90(self.Current_stack, k=1, axes=(2, 1)) # Rotate the array
        
        self.displayExpStack(self.Current_stack) # Display the 3D array

        # Flip and rotate self.nScoresDist to be homogenenous (for computation)
        self.nScoresDist = np.flip(self.nScoresDist, 1)
        self.nScoresDist = np.rot90(self.nScoresDist, k=1, axes=(2, 1))
                   
        # Keep the first and only score, then swapaxes
        self.ori = self.nScoresOri[0,:,:,:]
        self.ori = np.swapaxes(self.ori, 1, 2)
        
        # For viewing data diff or not OR theo profiles : extract of the first and only score then flip and rotate
        self.theo_stack = self.nScoresStack[0, :, :, :]
        self.theo_stack = np.flip(self.theo_stack, 1)
        self.theo_stack = np.rot90(self.theo_stack, k=1, axes=(2, 1))
        
        self.stack_mod = self.Treatment_theo_prof[0, :, :, :]
        self.stack_mod = np.flip(self.stack_mod, 1)
        self.stack_mod = np.rot90(self.stack_mod, k=1, axes=(2, 1))
        
        self.expStack_mod = self.testArrayList
        self.expStack_mod = np.flip(self.expStack_mod, 1)
        self.expStack_mod = np.rot90(self.expStack_mod, k=1, axes=(2, 1))
        
        self.slice_nbr = len(self.Current_stack) # Nbr of slice in the stack
        self.wind_NCC = int(np.round(0.1*self.slice_nbr)) # 1/10 of the total length 
        # Computation of quality map
        try : 
            self.quality_map = np.flip(self.quality_map, 0) # Flip the array
            self.quality_map = np.rot90(self.quality_map, k=1, axes=(1, 0)) # Rotate the array
            
            self.displayQuality(self.quality_map) # Display the quality map
        except :    
            self.progressBar.setVisible(True) # The progress bar is shown for clarity
            self.qualmap = self.NCC_computation(self.nScoresStack[0,:,:,:],self.rawImage, batchsize = 5000, Windows = self.wind_NCC)
    
            self.quality_map = self.qualmap *100 # X100 to display in %
            self.quality_map = np.flip(self.quality_map, 0) # Flip the array
            self.quality_map = np.rot90(self.quality_map, k=1, axes=(1, 0)) # Rotate the array
            
            self.Info_box.ensureCursorVisible()
            self.Info_box.insertPlainText("\n \u2022 Quality map has been computed.")
            QApplication.processEvents()
            self.progressBar.setVisible(False) # The progress bar is hidden for clarity
        
        self.displayQuality(self.quality_map) # Display the quality map
        
        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 Computation of IPF maps in progress.")
        QApplication.processEvents()
        
        # Display of IPF map 
        self.IPF_map = IPF_computation.Display_IPF_GUI(self.CIFpath[0], self.nScoresOri, IPF_view='Z')
        self.IPF_map = np.flip(self.IPF_map,1)
        self.IPF_map = np.rot90(self.IPF_map)
        
        self.displayIPFmap(self.IPF_map)
               
        # Creation of self.indexation.xxx to be as the run_i dexation approach
        self.indexation = SimpleNamespace()
        self.indexation.nScoresDist = self.nScoresDist
        self.indexation.CIF = self.CIFpath[0]
        self.indexation.nScoresOri = self.nScoresOri
        self.indexation.nScoresStack = self.nScoresStack
        self.indexation.rawImage = self.rawImage
        self.indexation.Treatment_theo_prof = self.Treatment_theo_prof
        self.indexation.quality_map = self.quality_map
        
        
    def labelIndex(self):
        # Search for the labeled map or ask to import it
        try :
            labels = self.parent.Label_image
            labels = np.rot90(np.flip(labels, 0), k=1, axes=(1, 0))
        except:
            StackLoc, StackDir = gf.getFilePathDialog("labeled map") 
            labels = tf.TiffFile(StackLoc[0]).asarray() # Import the label map
        
        # Generation of the maps using the information of the clustered map          
        # Create the new arrays using np.where
        self.indexation[0].quality_map_tempo = np.zeros((len(labels),len(labels[0])))
        self.indexation[0].nScoresOri_tempo = np.zeros((1,4,len(labels),len(labels[0])))
        self.indexation[0].nScoresDist_tempo = np.zeros((1,len(labels),len(labels[0])))
        self.indexation[0].rawImage_tempo = np.zeros((len(self.indexation[0].rawImage),len(labels),len(labels[0])))
        self.indexation[0].nScoresStack_tempo = np.zeros((1,len(self.indexation[0].nScoresStack[0]),len(labels),len(labels[0])))
        self.indexation[0].Treatment_theo_prof_tempo = np.zeros((1,len(self.indexation[0].Treatment_theo_prof[0]),len(labels),len(labels[0])))
        self.indexation[0].testArrayList_tempo = np.zeros((len(self.indexation[0].testArrayList),len(labels),len(labels[0])))

        self.progressBar.setValue(0)
        self.progressBar.setFormat("Map formation: %p%")
        self.progressBar.setRange(0, int(np.max(labels))-1) # Set the range accordingly to the number of labels

        for i in range(1,int(np.max(labels))):
            
            QApplication.processEvents()    
            self.ValSlice = i
            self.progression_bar()
            
            var = np.where(labels == i)
            self.indexation[0].quality_map_tempo[var] = self.indexation[0].quality_map[:,i-1]
            self.indexation[0].nScoresOri_tempo[:,:,var[0],var[1]] = self.indexation[0].nScoresOri[:,:,:,i-1]
            self.indexation[0].nScoresDist_tempo[:,var[0],var[1]] = self.indexation[0].nScoresDist[:,:,i-1]
            self.indexation[0].rawImage_tempo[:,var[0],var[1]] = self.indexation[0].rawImage[:,:,i-1]
            self.indexation[0].nScoresStack_tempo[:,:,var[0],var[1]] = self.indexation[0].nScoresStack[:,:,:,i-1]
            self.indexation[0].Treatment_theo_prof_tempo[:,:,var[0],var[1]] = self.indexation[0].Treatment_theo_prof[:,:,:,i-1]
            self.indexation[0].testArrayList_tempo[:,var[0],var[1]] = self.indexation[0].testArrayList[:,:,i-1]
        
        # Then replace the arrays 
        self.indexation[0].quality_map = self.indexation[0].quality_map_tempo
        self.indexation[0].nScoresOri = self.indexation[0].nScoresOri_tempo
        self.indexation[0].nScoresDist = self.indexation[0].nScoresDist_tempo
        self.indexation[0].rawImage = self.indexation[0].rawImage_tempo
        self.indexation[0].nScoresStack = self.indexation[0].nScoresStack_tempo
        self.indexation[0].Treatment_theo_prof = self.indexation[0].Treatment_theo_prof_tempo
        self.indexation[0].testArrayList = self.indexation[0].testArrayList_tempo
        
        # Recreate an h5 file with the new data
        self.savingRes_cluster()

    def Run_indexation(self):
        
        self.progressBar.setVisible(True) # The progress bar is shown for clarity
        self.progressBar.setValue(0)
        self.progressBar.setFormat("Indexation")
        self.Info_box.clear() # Clear the information box
        self.methodChoice = self.PresetBox.currentText() # Choice between diff0 or diff1
        self.indexation =  []
        

        # self.savgol_window = self.window_SpinBox.value() # Window length of the filter
        # self.savgol_polyorder = self.poly_SpinBox.value() # Order of the polynomial
        
        # # Specify which type of indexation must be use
        # if self.methodChoice == "Classical indexation":
        #     Op1 = ['Diff', 0]
        # elif self.methodChoice == "Derivative indexation":
        #     Op1 = ['Diff', 1]   
        # elif self.methodChoice == "Savgol derivative indexation":
        #     Op1 = ['Diff', 1, self.savgol_window, self.savgol_polyorder]
            
        # Workflow = []
        # Workflow.append(Op1)
        
        self.BatchProfiles_value = self.Profiles_SpinBox.value() # Number of experimental profiles per batch
        self.BatchDatabase_value = self.Database_SpinBox.value() # Number of theoretical profiles per batch
        
        # Indexation preparation
        # self.indexation = indGPU.IndexationGPUderiv(self,self.preInd.Stack, self.PathDir, self.preInd.DatabaseLoc, self.preInd.CifLoc, Workflow = Workflow, normType = "centered euclidian", nbSTACK=self.BatchProfiles_value, nbDB = self.BatchDatabase_value)
        # self.indexation = indGPU.IndexationGPUderiv(self,self.preInd.Stack, 
        #                                             self.PathDir, self.preInd.phaseList[0].DatabaseLoc, 
        #                                             self.preInd.phaseList[0].CifLoc, 
        #                                             Workflow = Workflow, 
        #                                             normType = "centered euclidian", nbSTACK=self.BatchProfiles_value,
        #                                             nbDB = self.BatchDatabase_value)
        for i in range(self.nPhases):
            
            self.indexation.append(indGPU.IndexationGPUderiv(self,self.preInd.Stack, 
                                                        self.PathDir, self.preInd.phaseList[i].DatabaseLoc, 
                                                        self.preInd.phaseList[i].CifLoc, 
                                                        Workflow = self.preInd.phaseList[i].Workflow, 
                                                        normType = "centered euclidian", nbSTACK=self.BatchProfiles_value,
                                                        nbDB = self.BatchDatabase_value))
        
        # Run indexation matching step
        for i in range(self.nPhases):
            self.indexation[i].runIndexation()
            
        if self.Cluster_index.isChecked(): # Specific to cluster indexation 
            self.labelIndex()
            
        # Keep the first and only score, then swapaxes
        self.ori = self.indexation[0].nScoresOri[0,:,:,:]
        self.ori = np.swapaxes(self.ori, 1, 2)
                
        self.indexation[0].quality_map = np.flip(self.indexation[0].quality_map, 0) # Flip the array
        self.indexation[0].quality_map = np.rot90(self.indexation[0].quality_map, k=1, axes=(1, 0)) # Rotate the array
        
        self.displayQuality(self.indexation[0].quality_map) # Display the quality map
        
        self.expSeries.setVisible(True) # Show the image serie display window
        
        self.indexation[0].rawImage = np.flip(self.indexation[0].rawImage, 1) # Flip the array
        self.indexation[0].rawImage = np.rot90(self.indexation[0].rawImage, k=1, axes=(2, 1)) # Rotate the array
        self.displayExpStack(self.indexation[0].rawImage) # Display the 3D array
        
        self.Info_box.ensureCursorVisible()
        self.Info_box.insertPlainText("\n \u2022 Quality map has been computed.")
        QApplication.processEvents()
        
        # Flip and rotate self.nScoresDist to be homogenenous (for computation)
        self.indexation[0].nScoresDist = np.flip(self.indexation[0].nScoresDist, 1)
        self.indexation[0].nScoresDist = np.rot90(self.indexation[0].nScoresDist, k=1, axes=(2, 1))
        
        # For viewing data diff or not OR theo profiles : extract of the first and only score then flip and rotate       
        self.Current_stack = self.indexation[0].rawImage # Extract the stack of images
        
        self.theo_stack = self.indexation[0].nScoresStack[0, :, :, :]
        self.theo_stack = np.flip(self.theo_stack, 1)
        self.theo_stack = np.rot90(self.theo_stack, k=1, axes=(2, 1))
        
        self.stack_mod = self.indexation[0].Treatment_theo_prof[0, :, :, :]
        self.stack_mod = np.flip(self.stack_mod, 1)
        self.stack_mod = np.rot90(self.stack_mod, k=1, axes=(2, 1))
        
        self.expStack_mod = self.indexation[0].testArrayList
        self.expStack_mod = np.flip(self.expStack_mod, 1)
        self.expStack_mod = np.rot90(self.expStack_mod, k=1, axes=(2, 1))
        
        # Display of IPF map 
        self.IPF_map = IPF_computation.Display_IPF_GUI(self.indexation[0].CIF, self.indexation[0].nScoresOri, IPF_view='Z')
        self.IPF_map = np.flip(self.IPF_map,1)
        self.IPF_map = np.rot90(self.IPF_map)
         
        self.displayIPFmap(self.IPF_map)    
        self.progressBar.setVisible(False) # The progress bar is hidden for clarity
        
        
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
        
    def Change_IPFView(self):
        self.OriChoice = self.OriBox.currentText() # Choice between X-Y-Z
        
        if self.OriChoice == "IPF-X":
            self.IPF_map = IPF_computation.Display_IPF_GUI(self.indexation[0].CIF, self.indexation.nScoresOri, IPF_view='X')
            self.IPF_map = np.flip(self.IPF_map,1)
            self.IPF_map = np.rot90(self.IPF_map)
            self.displayIPFmap(self.IPF_map)
        elif self.OriChoice == "IPF-Y":
            self.IPF_map = IPF_computation.Display_IPF_GUI(self.indexation[0].CIF, self.indexation[0].nScoresOri, IPF_view='Y')
            self.IPF_map = np.flip(self.IPF_map,1)
            self.IPF_map = np.rot90(self.IPF_map)
            self.displayIPFmap(self.IPF_map)
        elif self.OriChoice == "IPF-Z":
            self.IPF_map = IPF_computation.Display_IPF_GUI(self.indexation[0].CIF, self.indexation[0].nScoresOri, IPF_view='Z')
            self.IPF_map = np.flip(self.IPF_map,1)
            self.IPF_map = np.rot90(self.IPF_map)
            self.displayIPFmap(self.IPF_map)
        
    def NCC_computation(self,Theo_stack,rawImage, batchsize = 5000, Windows = 18): # Normalized covariance correlation calculation
        var,batch_nbr = self.find_batch_nbr(len(Theo_stack[0]),len(Theo_stack[0][0]),batchsize) # Find optimal batch for cupy uses
        
        self.prgbar = 0 # Progress bar initial value
        self.progressBar.setValue(self.prgbar)
        self.progressBar.setFormat("Quality computation: %p%")
        self.progressBar.setRange(0, int(batch_nbr)-1) # Set the range accordingly to the number of labels
        
        mempool = cp.get_default_memory_pool()
        pinned_mempool = cp.get_default_pinned_memory_pool()
        
        incr = np.linspace(0,len(Theo_stack),Windows+1)
        corrcoeff = np.zeros((len(Theo_stack[0])*len(Theo_stack[0][0])))
        
        test_theo = Theo_stack.reshape((len(Theo_stack),len(Theo_stack[0])*len(Theo_stack[0][0])))
        test_exp = rawImage.reshape((len(rawImage),len(rawImage[0])*len(rawImage[0][0])))
        
        for i in range(int(batch_nbr)):
            QApplication.processEvents()    
            self.ValSlice = i
            self.progression_bar()
            
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

    def find_batch_nbr(self,height,width,batch):  # Find optimal batch for cupy uses
        i = 0
        while height*width % (batch-i) != 0:
            i += 1
        
        return batch-i, height*width/(batch-i)

    def updateROI(self, roi): # Specify what must be done when line segment is moved
        # Get coordinates
        Ori_LineROI, ROIcoords = roi.getArrayRegion(self.ori, self.IPF_serie.getImageItem(), axes=(1, 2), returnMappedCoords=True)

        ROIcoords = np.floor(ROIcoords)
        profileLength = len(Ori_LineROI[0, :])  
        
        # Create storage array
        self.disOvalues = np.zeros(profileLength) # Store the misorientation values
        OriValues = np.zeros((4, profileLength)) # Init the array for quaternions
        self.qualValue = np.zeros((1,profileLength))
        
        # Extract the row and column position and search for quality and quaternions values associated
        for i in range(profileLength):
            r = int(ROIcoords[0, i])
            c = int(ROIcoords[1, i])
            OriValues[:, i] = self.ori[:, r, c]
            self.qualValue[:, i] = self.indexation.quality_map[r, c]
        
        self.qualValue = self.qualValue[0,:] # Quality map values
        origineQuat = Quaternion(OriValues[:, 0]).inverse # Inversion of the quaternions
        
        for i in range(profileLength): # For each pixel, compute the disorientation from the origin quaternion
            currentQuat = Quaternion(OriValues[:, i]).inverse
            self.disOvalues[i] = xa.disOfromQuatSymNoMat(origineQuat, currentQuat, self.SymQ)[1]
        
        self.drawqual()
        self.drawMisO()

    def progression_bar(self): # Function for the ProgressBar uses
        self.prgbar = self.ValSlice
        self.progressBar.setValue(self.prgbar)

    def Save_results(self):
        IPF_map_X = IPF_computation.Display_IPF_GUI(self.indexation[0].CIF, self.indexation[0].nScoresOri, IPF_view='X')
        IPF_map_Y = IPF_computation.Display_IPF_GUI(self.indexation[0].CIF, self.indexation[0].nScoresOri, IPF_view='Y')
        IPF_map_Z = IPF_computation.Display_IPF_GUI(self.indexation[0].CIF, self.indexation[0].nScoresOri, IPF_view='Z')
        
        IPF_map_X = (IPF_map_X * 255).astype(np.uint8)
        IPF_map_Y = (IPF_map_Y * 255).astype(np.uint8)
        IPF_map_Z = (IPF_map_Z * 255).astype(np.uint8)
    
        # Images saving step
        if self.flag_folder == 1:
            tf.imwrite(self.PathDir + '/Quality_map.tiff', np.rot90(np.flip(self.indexation[0].quality_map, 0), k=1, axes=(1, 0)))
            tf.imwrite(self.PathDir + '/Distance_map.tiff',np.rot90(np.flip(1-self.indexation[0].nScoresDist, 1), k=1, axes=(2, 1)))
            tf.imwrite(self.PathDir + '/IPF_X.tiff',IPF_map_X)
            tf.imwrite(self.PathDir + '/IPF_Y.tiff',IPF_map_Y)
            tf.imwrite(self.PathDir + '/IPF_Z.tiff',IPF_map_Z)
        else: 
            tf.imwrite(self.StackDir + '/Quality_map.tiff', np.rot90(np.flip(self.indexation[0].quality_map, 0), k=1, axes=(1, 0)))
            tf.imwrite(self.StackDir + '/Distance_map.tiff',np.rot90(np.flip(1-self.indexation[0].nScoresDist, 1), k=1, axes=(2, 1)))
            tf.imwrite(self.StackDir + '/IPF_X.tiff',IPF_map_X)
            tf.imwrite(self.StackDir + '/IPF_Y.tiff',IPF_map_Y)
            tf.imwrite(self.StackDir + '/IPF_Z.tiff',IPF_map_Z)
            
        # Finished message
        self.popup_message("indexation[0]","Saving process is over.",'icons/indexation[0]_icon.png')

    def mouseMoved(self, e):
        pos = e[0]
        sender = self.sender()
        
        if not self.mouseLock.isChecked():
            if self.expSeries.view.sceneBoundingRect().contains(pos)\
                or self.QualSeries.view.sceneBoundingRect().contains(pos)\
                or self.IPF_serie.view.sceneBoundingRect().contains(pos):
    
                if sender == self.proxy1:
                    item = self.expSeries.view
                elif sender == self.proxy2:
                    item = self.QualSeries.view    
                elif sender == self.proxy3:
                    item = self.IPF_serie.view   
    
                mousePoint = item.mapSceneToView(pos) 
                     
                self.crosshair_v1.setPos(mousePoint.x())
                self.crosshair_h1.setPos(mousePoint.y())
                
                self.crosshair_v2.setPos(mousePoint.x())
                self.crosshair_h2.setPos(mousePoint.y())
                
                self.crosshair_v3.setPos(mousePoint.x())
                self.crosshair_h3.setPos(mousePoint.y())
    
            try:
                self.x = int(mousePoint.x())
                self.y = int(mousePoint.y())
                
                self.label_Quality.setText("Quality indice: " + str(np.round(self.indexation[0].quality_map[self.x, self.y],1)) + "%")
            except:
                pass

            try:
                if self.x >= 0 and self.y >= 0 and self.x < len(self.Current_stack[0, :, 0]) and self.y < len(self.Current_stack[0, 0, :]):
                    self.drawCHORDprofiles()
            except:
                pass
    
    def mouseClick(self, e):
        pos = e[0]
        sender = self.sender()
        
        self.mouseLock.toggle()
        
        fromPosX = pos.scenePos()[0]
        fromPosY = pos.scenePos()[1]
        
        posQpoint = QtCore.QPointF()
        posQpoint.setX(fromPosX)
        posQpoint.setY(fromPosY)

        if self.expSeries.view.sceneBoundingRect().contains(posQpoint)\
            or self.QualSeries.view.sceneBoundingRect().contains(posQpoint)\
            or self.IPF_serie.view.sceneBoundingRect().contains(posQpoint):
                
            if sender == self.proxy4:
                item = self.expSeries.view
            elif sender == self.proxy5:
                item = self.QualSeries.view
            elif sender == self.proxy6:
                item = self.IPF_serie.view  
            
            mousePoint = item.mapSceneToView(posQpoint) 

            self.crosshair_v1.setPos(mousePoint.x())
            self.crosshair_h1.setPos(mousePoint.y())
            
            self.crosshair_v2.setPos(mousePoint.x())
            self.crosshair_h2.setPos(mousePoint.y())
            
            self.crosshair_v3.setPos(mousePoint.x())
            self.crosshair_h3.setPos(mousePoint.y())
                 
            self.x = int(mousePoint.x())
            self.y = int(mousePoint.y())
            
            try:
                if self.x >= 0 and self.y >= 0 and self.x < len(self.Current_stack[0, :, 0])and self.y < len(self.Current_stack[0, 0, :]):
                    self.drawCHORDprofiles()
            except:
                pass

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

    def drawCHORDprofiles(self): # Display of CHORDprofiles
        try:
            self.profiles.clear()           
            line = self.plotIt.addLine(x = self.expSeries.currentIndex) # Line associated to the current slice
            line.setPen({'color': (42, 42, 42, 100), 'width': 2}) # Style of the line
            
            self.legend = self.profiles.addLegend(horSpacing = 30, labelTextSize = '10pt', colCount = 1, labelTextColor = 'black', brush = self.parent.color6, pen = pg.mkPen(color=(0, 0, 0), width=1))
                      
            pen = pg.mkPen(color=self.parent.color4, width=5) # Color and line width of the profile
            pen2 = pg.mkPen(color=(48,195,222), width=5) # Color and line width of the profile

            if self.TheoProfiles.isChecked():
                if self.ModProfiles.isChecked():
                    self.profiles.plot(self.stack_mod[:, self.x, self.y], pen=pen2, name='Modified theoretical profiles')
                else:
                    self.profiles.plot(self.theo_stack[:, self.x, self.y], pen=pen2, name='Theoretical profiles') # Plot of the profile
    
            if self.ModProfiles.isChecked():
                self.profiles.plot(self.expStack_mod[:, self.x, self.y], pen=pen, name='Modified raw profiles')
            else:
                self.profiles.plot(self.Current_stack[:, self.x, self.y], pen=pen, name='Raw profiles') # Plot of the raw profile
                    
            styles = {"color": "black", "font-size": "15px", "font-family": "Noto Sans Cond"} # Style for labels
            
            self.profiles.setLabel("left", "GrayScale value", **styles) # Import style for Y label
            self.profiles.setLabel("bottom", "Slice", **styles) # Import style for X label
            
            font=QtGui.QFont('Noto Sans Cond', 9) # Font definition of the plot
            
            self.profiles.getAxis("left").setTickFont(font) # Apply size of the ticks label
            self.profiles.getAxis("left").setStyle(tickTextOffset = 10) # Apply a slight offset

            self.profiles.getAxis("bottom").setTickFont(font) # Apply size of the ticks label
            self.profiles.getAxis("bottom").setStyle(tickTextOffset = 10) # Apply a slight offset
            
            self.profiles.getAxis('left').setTextPen('k') # Set the axis in black
            self.profiles.getAxis('bottom').setTextPen('k') # Set the axis in black
            
            self.profiles.setBackground(self.parent.color2)
            self.profiles.showGrid(x=True, y=True)
            
        except:
            pass
        
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

    def displayExpStack(self, series):
        self.expSeries.addItem(self.crosshair_v1, ignoreBounds=True)
        self.expSeries.addItem(self.crosshair_h1, ignoreBounds=True) 
        
        self.expSeries.ui.histogram.hide()
        self.expSeries.ui.roiBtn.hide()
        self.expSeries.ui.menuBtn.hide()
        
        view = self.expSeries.getView()
        state = view.getState()        
        self.expSeries.setImage(series) 
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
        
    def displayQuality(self, series): # Display of initial KAD map
        self.QualSeries.addItem(self.crosshair_v2, ignoreBounds=True)
        self.QualSeries.addItem(self.crosshair_h2, ignoreBounds=True) 
        
        self.QualSeries.ui.histogram.show()
        self.QualSeries.ui.roiBtn.hide()
        self.QualSeries.ui.menuBtn.hide()
        
        view = self.QualSeries.getView()
        state = view.getState()        
        self.QualSeries.setImage(series) 
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
        
    def displayIPFmap(self, Series):
        self.IPF_serie.addItem(self.crosshair_v3, ignoreBounds=True)
        self.IPF_serie.addItem(self.crosshair_h3, ignoreBounds=True) 
        self.IPF_serie.addItem(self.lineROI_carto)
        
        self.IPF_serie.ui.histogram.hide()
        self.IPF_serie.ui.roiBtn.hide()
        self.IPF_serie.ui.menuBtn.hide()
        
        self.IPF_serie.setImage(Series)
        self.IPF_serie.autoRange()    
        
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