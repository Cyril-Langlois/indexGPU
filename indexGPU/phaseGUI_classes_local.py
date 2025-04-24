import os

from inspect import getsourcefile
from os.path import abspath
import pyqtgraph as pg
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QCheckBox, QSpinBox, QGroupBox, QTextEdit, QHBoxLayout, QVBoxLayout, QDialog, QRadioButton, QFileDialog, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QSize
# from indexGPU import Indexation_lib as il
# import indexGPU.Indexation_lib as il
import Indexation_lib as il

import numpy as np
import tifffile as tf
import h5py
from inichord import General_Functions as gf
import Dans_Diffraction as da

##############################  the following classes are used for indexation  ##########################################
path2thisFile = abspath(getsourcefile(lambda:0))
uiclass, baseclass = pg.Qt.loadUiType(os.path.dirname(path2thisFile) + "/phase_form_tempo.ui")

class phaseForm(uiclass, baseclass):
    def __init__(self, parent, nbPhases, otsu):
        super().__init__()
        self.setWindowTitle("Phases parameters")
        self.setupUi(self)
        self.parent = parent

        
        #INITIALISATION
        
        self.page = 0
        self.nbPhase = nbPhases
        self.otsu = otsu
        
        #VARIABLES DE STOCKAGE
        
        self.list_toIndex = [True]*self.nbPhase
        self.list_CIF = [None]*self.nbPhase
        self.list_phase_name = [""]*self.nbPhase
        self.list_DB = [None]*self.nbPhase
        self.list_DB_size = [None]*self.nbPhase
        self.list_DB_size_max = [10_000_000]*self.nbPhase
        self.list_diff = [0]*self.nbPhase
        self.list_SG = [False]*self.nbPhase
        self.list_poly = [2]*self.nbPhase
        self.list_window = [3]*self.nbPhase
        
        #SETTINGS FENETRE
        self.label_title_.setText(f"Phase n°: {self.page + 1} / {self.nbPhase} ")
        self.gB_otsu.setVisible(False) #gB otsu non visible par défaut
        self.gB_SG.setVisible(False) #Savgol non visible par défaut
        self.adjustSize()
        
        #Single or multiphase
        if self.nbPhase == 1 :
            self.previous_button.setVisible(False)
            self.next_button.setVisible(False)
        else :
            self.previous_button.setEnabled(False)
            self.save_button.setEnabled(False)
        
        # Otsu case
        if self.otsu :
            self.gB_otsu.setVisible(True)
            self.gB_cristallo.setVisible(False)
            self.gB_DB.setVisible(False)
            self.gB_workflow.setVisible(False)
            self.indexQuestion.setEnabled(False)
            self.LabelsSeries.ui.histogram.hide()
            self.LabelsSeries.ui.roiBtn.hide()
            self.LabelsSeries.ui.menuBtn.hide()
            if self.nbPhase > 1 : 
                self.next_button.setEnabled(False)
            self.adjustSize()


        #CONNEXIONS
        
        if self.nbPhase > 1 :
            self.previous_button.clicked.connect(self.previousPage)
            self.next_button.clicked.connect(self.nextPage)
        self.save_button.clicked.connect(self.saveClicked)
        self.load_CIF_button.clicked.connect(self.loadFile)
        self.load_DB_button.clicked.connect(self.loadFile)
        self.text_DB_size.textChanged.connect(self.DB_Size)
        self.checkBox_SG.stateChanged.connect(self.savgolParam)
        self.spinBox_diff.valueChanged.connect(self.SpinBox_changed)
        self.spinBox_window.valueChanged.connect(self.SpinBox_changed)
        self.spinBox_poly.valueChanged.connect(self.SpinBox_changed)
        self.label_bbtn.clicked.connect(self.importLabel)
        self.indexQuestion.stateChanged.connect(self.fillOrNot)
       
        
    #METHODES

    def setDBSizeMax(self):
        # Reads the DB file and sets the maximum value to write in the DB-size to the number of profiles
        # that the given file contains
        
        f = h5py.File(self.list_DB[self.page], 'r')
        listKeys = gf.get_dataset_keys(f)
        listChunkArrays = []
        for key in listKeys:
            if "DataChunk" in key:
                listChunkArrays.append(key)
        self.list_DB_size_max[self.page] = 250_000*len(listChunkArrays) # All chunks contain 250_000 profiles
        
    def setPhaseName(self):
        crys = da.functions_crystallography.readcif(self.list_CIF[self.page])
        self.list_phase_name[self.page] = crys["_chemical_formula_sum"] + "  " + crys["_space_group_IT_number"]
        
    def importLabel(self): 
        # Loads the otsu map
        
        options = QFileDialog.Options()
        path, _ = QFileDialog.getOpenFileName(self, f"Select a map :", "", "Tous les fichiers (*.tiff)", options=options)
        
        self.label_map_raw = tf.TiffFile(path).asarray()
        self.label_map = np.flip(self.label_map_raw, 0)
        self.label_map = np.rot90(self.label_map, k=1, axes=(1, 0))
        self.otsuListCreation()
        self.displaylabels(self.thresholded_maps[0])
        # self.label_title_.setText("Phase n°: 0")
        
        self.gB_cristallo.setVisible(True)
        self.gB_DB.setVisible(True)
        self.gB_workflow.setVisible(True)
        self.indexQuestion.setEnabled(True)
        if self.nbPhase == 1:
            self.save_button.setEnabled(True)
        else :
            self.next_button.setEnabled(True)
        self.adjustSize()
        
    def otsuListCreation (self):
        # Checks if the entered ostu matches with the given number of phases
        # Creates a list of maps with 2 values : 1 for the current phase to display, 0 for the others
        
        nbClass = int(np.max(self.label_map) + 1)
        if nbClass != self.nbPhase:
            self.showMsgBox(f"Number of class in otsu map is different from the number of phases. Number of class : {nbClass}")
        else:
            self.thresholded_maps = []
            for i in range (self.nbPhase):
                thresholded_map = np.where(self.label_map == i,1,0)
                self.thresholded_maps.append(thresholded_map)
                  
    def fillOrNot (self):
        # Updates the list telling the choice to index a phase or not
        
        if self.indexQuestion.isChecked():
            self.gB_cristallo.setVisible(True)
            self.gB_DB.setVisible(True)
            self.gB_workflow.setVisible(True)
            self.list_toIndex[self.page] = True

        else :
            self.gB_cristallo.setVisible(False)
            self.gB_DB.setVisible(False)
            self.gB_workflow.setVisible(False)
            self.list_toIndex[self.page] = False          
        self.adjustSize()
    
    def SpinBox_changed(self):
        sender = self.sender()
        if sender == self.spinBox_diff:
            self.list_diff[self.page] = self.spinBox_diff.value()
        elif sender == self.spinBox_window:
            self.list_window[self.page] = self.spinBox_window.value()
        else:
            self.list_poly[self.page] = self.spinBox_poly.value()
           
    def DB_Size(self, text):
        if text == '':
            text = '0'
        if int(text) <= self.list_DB_size_max[self.page] :
            self.list_DB_size[self.page] = self.text_DB_size.text()
        else :
            # self.list_DB_size[self.page] = self.list_DB_size_max[self.page]
            self.text_DB_size.setText(str(self.list_DB_size_max[self.page]))
   
    def savgolParam(self):
        if self.gB_SG.isVisible():
            self.gB_SG.setVisible(False)
            self.adjustSize()
            self.list_SG[self.page] = False
            self.list_poly[self.page] = None
            self.list_window[self.page] = None
        else:
            self.gB_SG.setVisible(True)
            self.adjustSize()
            self.list_SG[self.page] = True
        
    def previousPage (self):
        self.page -= 1
        print("current page is :", self.page + 1)
        self.text_CIF.setText(self.list_CIF[self.page])
        self.label_CIF.setText("CIF file : " + self.list_phase_name[self.page])
        self.text_DB_file.setText(self.list_DB[self.page])
        self.text_DB_size.setText(self.list_DB_size[self.page])
        self.spinBox_diff.setValue(self.list_diff[self.page])
        self.checkBox_SG.setChecked(self.list_SG[self.page])
        self.label_title_.setText(f"Phase n°: {self.page + 1} / {self.nbPhase} ")
        if self.list_SG[self.page] :
            self.spinBox_poly.setValue(self.list_poly[self.page])
            self.spinBox_window.setValue(self.list_window[self.page])
        if self.page == 0 :
            self.previous_button.setEnabled(False)
        if self.next_button.isEnabled() == False:
            self.next_button.setEnabled(True)
            self.save_button.setEnabled(False)
        if self.otsu :
            self.displaylabels(self.thresholded_maps[self.page])
            self.indexQuestion.setChecked(self.list_toIndex[self.page])
        self.adjustSize()
             
    def nextPage (self):
        self.page += 1
        print("current page is :", self.page + 1)
        self.text_CIF.setText(self.list_CIF[self.page])
        self.label_CIF.setText("CIF file : " + self.list_phase_name[self.page])
        self.text_DB_file.setText(self.list_DB[self.page])
        self.text_DB_size.setText(self.list_DB_size[self.page])
        self.spinBox_diff.setValue(self.list_diff[self.page])
        self.checkBox_SG.setChecked(self.list_SG[self.page])
        self.label_title_.setText(f"Phase n°: {self.page + 1} / {self.nbPhase} ")
        if self.list_SG[self.page] :
            self.spinBox_poly.setValue(self.list_poly[self.page])
            self.spinBox_window.setValue(self.list_window[self.page])
        if self.page == self.nbPhase -1 :
            self.next_button.setEnabled(False)
            self.save_button.setEnabled(True)
        if self.previous_button.isEnabled() == False:
            self.previous_button.setEnabled(True)
        if self.otsu :
            self.displaylabels(self.thresholded_maps[self.page])
            self.indexQuestion.setChecked(self.list_toIndex[self.page])
        self.adjustSize()
        
    def saveClicked (self):
        # Checks if the user has entered all the values
        empty = 0
        for i in range(self.nbPhase):
            if self.list_toIndex[i]:
                if self.list_CIF[i] == None or self.list_DB[i] == None or self.list_DB_size[i] == None:
                    empty += 1
                    
        if empty > 0:
            self.showMsgBox("At least one file or data base size is missing.")
            
        # Saving the data    
        else :
            for i in range (self.nbPhase):
                # Phase objects creation
                phaseO = il.phaseObject()
 
                # MAJ des attributs d'une phase i
                phaseO.CifLoc = self.list_CIF[i]
                phaseO.DatabaseLoc = self.list_DB[i]
                phaseO.DB_Size = self.list_DB_size[i]
                phaseO.diff = self.list_diff[i]
                phaseO.SG = self.list_SG[i]
                phaseO.SG_poly = self.list_poly[i]
                phaseO.SG_win = self.list_window[i]
                phaseO.workflowCreation()
                phaseO.name = self.list_phase_name[i]
                print(phaseO.name)
                
                #ajout de la phase i dans la liste de phases parente
                self.parent.phaseList.append(phaseO)
            
            self.parent.listToIndex = self.list_toIndex
            self.parent.DBsizeList = self.list_DB_size

            if self.otsu:
                self.parent.otsu_map = self.label_map_raw
            
            self.close()
    
    def showMsgBox (self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(message)
        msg.setWindowTitle("Critical MessageBox")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        retval = msg.exec()
             
    def loadFile (self):
        # Lets the user choose CIf or DB files
        
        sender = self.sender()
        options = QFileDialog.Options()
        if sender == self.load_CIF_button :
            path, _ = QFileDialog.getOpenFileName(self, f"Select a CIF file :", "", "Tous les fichiers (*.cif)", options=options)
            self.text_CIF.setText(path)
            self.list_CIF[self.page] = path
            self.setPhaseName()
            self.label_CIF.setText("CIF file : " + self.list_phase_name[self.page])
            
        else :
            path, _ = QFileDialog.getOpenFileName(self, f"Select a Data Base file :", "", "Tous les fichiers (*.crddb)", options=options)
            self.text_DB_file.setText(path)
            self.list_DB[self.page] = path
            #self.text_DB_size = taille de la DB du fichier choisi
            self.setDBSizeMax()
            self.text_DB_size.setText(str(self.list_DB_size_max[self.page]))
    
    def displaylabels(self, series):
        # Display of label map
        self.LabelsSeries.ui.histogram.hide()
        self.LabelsSeries.ui.roiBtn.hide()
        self.LabelsSeries.ui.menuBtn.hide()
        
        view = self.LabelsSeries.getView()
        state = view.getState()        
        self.LabelsSeries.setImage(series) 
        view.setState(state)
        
        # self.LabelsSeries.setColorMap(pg.colormap.get('CET-L13'))
        self.LabelsSeries.setColorMap(pg.colormap.getFromMatplotlib('copper'))
