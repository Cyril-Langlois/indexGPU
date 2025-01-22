import os

from inspect import getsourcefile
from os.path import abspath
import pyqtgraph as pg
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QCheckBox, QSpinBox, QGroupBox, QTextEdit, QHBoxLayout, QVBoxLayout, QDialog, QRadioButton, QFileDialog, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QSize
#from indexGPU import Indexation_lib as il
import indexGPU.Indexation_lib as il

import numpy as np
import tifffile as tf


##############################  the following classes are used for indexation  ##########################################
path2thisFile = abspath(getsourcefile(lambda:0))
uiclass, baseclass = pg.Qt.loadUiType(os.path.dirname(path2thisFile) + "/phase_form_tempo.ui")

class phaseForm(uiclass, baseclass):
    def __init__(self, parent, nbPhases):
        super().__init__()
        self.setWindowTitle("Phases parameters")
        self.setupUi(self)
        self.parent = parent

        
        #VARIABLES DE STOCKAGE
        
        self.page = 0
        self.nbPhase = nbPhases
        self.list_toIndex = [True]*self.nbPhase
        self.list_phase = [il.phaseObject()]*self.nbPhase
        self.list_CIF = [None]*self.nbPhase
        self.list_DB = [None]*self.nbPhase
        self.list_DB_size = [None]*self.nbPhase
        self.list_diff = [0]*self.nbPhase
        self.list_SG = [False]*self.nbPhase
        self.list_poly = [2]*self.nbPhase
        self.list_window = [3]*self.nbPhase
        self.otsu = False
        
        #SETTINGS FENETRE
        self.label_title_.setText(f"Phase n°: {self.page + 1} / {self.nbPhase} ")
        self.indexQuestion.setTristate(False)
        self.gB_otsu.setVisible(False) #gB otsu non visible par défaut
        self.gB_SG.setVisible(False) #Savgol non visible par défaut
 
        if self.nbPhase == 1 : #Gestion des boutons previous et next
            self.previous_button.setVisible(False)
            self.next_button.setVisible(False)
       
        if self.otsu :
            self.gB_otsu.setVisible(True)
            self.gB_cristallo.setVisible(False)
            self.gB_DB.setVisible(False)
            self.gB_workflow.setVisible(False)
            self.indexQuestion.setEnabled(False)
            self.save_button.setEnabled(False)
            if self.nbPhase > 1 : #Gestion des boutons previous et next
                self.previous_button.setEnabled(False)
                self.next_button.setEnabled(False)


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
        
    def importLabel(self): 
        # self.defaultIV() 
        options = QFileDialog.Options()
        path, _ = QFileDialog.getOpenFileName(self, f"Select a map :", "", "Tous les fichiers (*.tiff)", options=options)
        
        self.label_map = tf.TiffFile(path).asarray()
        self.label_map = np.flip(self.label_map, 0)
        self.label_map = np.rot90(self.label_map, k=1, axes=(1, 0))
        self.otsuListCreation()
        self.displaylabels(self.thresholded_maps[0])
        self.label_title_.setText("Phase n°: 0")
        
        self.gB_cristallo.setVisible(True)
        self.gB_DB.setVisible(True)
        self.gB_workflow.setVisible(True)
        self.indexQuestion.setEnabled(True)
        if self.nbPhase == 1:
            self.save_button.setEnabled(True)
        else :
            self.next_button.setEnabled(True)
        
    def otsuListCreation (self):
        nbClass = np.max(self.label_map) + 1
        if nbClass != self.nbPhase:
            self.showMsgBox("Number of class in otsu map is different from the number of phases.")
        else:
            self.thresholded_maps = []
            for i in range (self.nbPhase):
                thresholded_map = np.where(self.label_map == i,1,0)
                self.thresholded_maps.append(thresholded_map)
                  
    def fillOrNot (self):
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

            
    
    def SpinBox_changed(self):
        sender = self.sender()
        if sender == self.spinBox_diff:
            self.list_diff[self.page] = self.spinBox_diff.value()
        elif sender == self.spinBox_window:
            self.list_window[self.page] = self.spinBox_window.value()
        else:
            self.list_poly[self.page] = self.spinBox_poly.value()
           
    def DB_Size(self, text):
        self.list_DB_size[self.page] = self.text_DB_size.text()
   
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
             
    def nextPage (self):
        self.page += 1
        print("current page is :", self.page + 1)
        self.text_CIF.setText(self.list_CIF[self.page])
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
        
    def saveClicked (self):
        empty = 0
        for i in range(self.nbPhase):
            if self.list_toIndex[i]:
                if self.list_CIF[i] == None or self.list_DB[i] == None or self.list_DB_size[i] == None:
                    empty += 1
                    
        if empty > 0:
            self.showMsgBox("At least one file or data base size is missing.") 
        else :
            for i in range (self.nbPhase):
                #MAJ des attributs d'une phase i
                self.list_phase[i].CifLoc = self.list_CIF[i]
                self.list_phase[i].DatabaseLoc = self.list_DB[i]
                self.list_phase[i].DB_Size = self.list_DB_size[i]
                self.list_phase[i].diff = self.list_diff[i]
                self.list_phase[i].SG = self.list_SG[i]
                self.list_phase[i].SG_poly = self.list_poly[i]
                self.list_phase[i].SG_win = self.list_window[i]
                self.list_phase[i].workflowCreation()
                #ajout de la phase i dans la liste de phases parente
                self.parent.phaseList.append(self.list_phase[i])

            self.close()
    
    def showMsgBox (self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(message)
        msg.setWindowTitle("Critical MessageBox")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        retval = msg.exec()
             
    def loadFile (self):
        sender = self.sender()
        options = QFileDialog.Options()
        if sender == self.load_CIF_button :
            path, _ = QFileDialog.getOpenFileName(self, f"Select a CIF file :", "", "Tous les fichiers (*.cif)", options=options)
            self.text_CIF.setText(path)
            self.list_CIF[self.page] = path
        else :
            path, _ = QFileDialog.getOpenFileName(self, f"Select a Data Base file :", "", "Tous les fichiers (*.crddb)", options=options)
            self.text_DB_file.setText(path)
            self.list_DB[self.page] = path
            #self.text_DB_size = taille de la DB du fichier choisi
    
    def displaylabels(self, series): # Display of label map
        self.LabelsSeries.ui.roiBtn.hide()
        self.LabelsSeries.ui.menuBtn.hide()
        
        view = self.LabelsSeries.getView()
        state = view.getState()        
        self.LabelsSeries.setImage(series) 
        view.setState(state)
        
        # histplot = self.LabelsSeries.getHistogramWidget()
        self.LabelsSeries.setColorMap(pg.colormap.get('viridis'))
        # self.LabelsSeries.setColorMap(pg.colormap())

    


class phaseNum(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("phaseNum dialog")
        self.parent = parent

        layout = QVBoxLayout()

        # QSpinBox for phase number
        self.nPhases = QSpinBox()
        self.nPhases.setRange(1, 5)  # range from 0 to 100
        self.nPhases.setValue(1)  # Initial value
        
        self.nPhases_titre = QLabel(f"Enter phase number :")
        
        self.ok_button = QPushButton("Validate")
        
        # layout addition
        layout.addWidget(self.nPhases_titre)
        layout.addWidget(self.nPhases)
        layout.addWidget(self.ok_button)

        self.nPhases.valueChanged.connect(self.update_SpinBox_value)
        self.ok_button.clicked.connect(self.close)
        
        self.setLayout(layout)
        
    def update_SpinBox_value(self):
        
        self.parent.nPhases = self.nPhases.value()
    