# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 09:10:47 2025

@author: useradmin
"""
import os

from inspect import getsourcefile
from os.path import abspath
import pyqtgraph as pg
import sys
# from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLineEdit, QCheckBox, QSpinBox, QGroupBox, QTextEdit,
#                              QHBoxLayout, QVBoxLayout, QDialog, QRadioButton, QFileDialog, QLabel, QTextBrowser, QStackedWidget)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon

path2thisFile = abspath(getsourcefile(lambda:0))
#uiclass, baseclass = pg.Qt.loadUiType(os.path.dirname(path2thisFile) + "/Indexation_GUI.ui")

##############################  the following classes are used for indexation  ##########################################
class phasesLoading(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("Sample Informations")
        self.parent = parent
        
        # Data to be gathered
        
        self.DB_Size = 1
        self.SG = False
        self.diff = 0
        self.SG_win = 3
        self.SG_poly = 2
        
        layout = QVBoxLayout()
        
        # Bouton pour ouvrir un fichier
        self.label_stack = QLabel("Please, select an image serie :")
        self.text_stack = QLineEdit()
        self.load_stack_button = QPushButton(" ")
        self.load_stack_button.setIcon(QIcon('file_icon.png'))
        self.openButton = QPushButton("Open phase files")
        
        # Création d'un spinBox pour le nb de phases
        self.nPhases = QSpinBox()
        self.nPhases.setRange(1, 5)  # Plage de 0 à 100
        self.nPhases.setValue(1)  # Valeur initiale
        
        # Ajouter un label général
        self.nPhases_titre = QLabel(f"Enter phase number :")
        
        # Ajout au layout
        layout.addWidget(self.label_stack)
        layout.addWidget(self.text_stack)
        layout.addWidget(self.load_stack_button)
        layout.addWidget(self.nPhases_titre)
        layout.addWidget(self.nPhases)
        layout.addWidget(self.openButton)
              
        # Connecter le signal de changement de valeur du slider
        self.nPhases.valueChanged.connect(self.update_SpinBox_value)
        self.load_stack_button.clicked.connect(self.open_explorer)
        self.openButton.clicked.connect(self.open_form)
        
        self.setLayout(layout)
        
    def update_SpinBox_value(self):
        self.parent.nPhases = self.nPhases.value()
   
    def open_explorer(self):
        #dir_ = QFileDialog.getExistingDirectory(None, 'Select an image serie :', 'F:\\', QFileDialog.ShowDirsOnly)
        options = QFileDialog.Options()
        stack_path, _ = QFileDialog.getOpenFileName(self, f"Select an image serie :", "", "Tous les fichiers (*)", options=options)
        self.text_stack.setText(stack_path)        
   
    def open_form (self):
        self.form = phaseIndexParam(self)
        self.form.exec_()

path2thisFile = abspath(getsourcefile(lambda:0))
# inv = "".join(reversed(path2thisFile))
# index = inv.find('\\')
# total = len((inv))
# newindex = total-index
# print(path2thisFile[:newindex] + "phase_form.ui")
# uiclass2, baseclass2 = pg.Qt.loadUiType(os.path.dirname(path2thisFile[:newindex] + "phase_form.ui")) 
uiclass2, baseclass2 = pg.Qt.loadUiType(os.path.dirname(path2thisFile) + "/phase_form.ui")
   
class phaseIndexParam(uiclass2, baseclass2):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("Phases parameters")
        self.setupUi(self)
        self.parent = parent
        #VARIABLES DE STOCKAGE
       
        self.nbPhase = self.parent.nPhases.value()
        self.list_CIF = [None]*self.nbPhase
        self.list_DB = [None]*self.nbPhase
        self.list_DB_size = [None]*self.nbPhase
        self.list_diff = [0]*self.nbPhase
        self.list_SG = [False]*self.nbPhase
        self.list_poly = [2]*self.nbPhase
        self.list_window = [3]*self.nbPhase
        

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
       
        
    #METHODES    
        
    def SpinBox_changed(self):
        i = self.stackedW.currentIndex()
        sender = self.sender()
        if sender == self.spinBox_diff:
            self.list_diff[i] = self.spinBox_diff.value()
        elif sender == self.spinBox_window:
            self.list_window[i] = self.spinBox_window.value()
        else:
            self.list_poly[i] = self.spinBox_poly.value()
           
    def DB_Size(self, text):
        i = self.stackedW.currentIndex()
        self.list_DB_size[i] = self.text_DB_size
   
    def savgolParam(self):
        i = self.stackedW.currentIndex()
        if self.gB_SG.isVisible():
            self.gB_SG.setVisible(False)
            self.adjustSize()
            self.list_SG[i] = True
        else:
            self.gB_SG.setVisible(True)
            self.adjustSize()
            self.list_SG[i] = False
            self.list_poly[i] = None
            self.list_window[i] = None
        
    def previousPage (self):
        prevIndex = self.stackedW.currentIndex() - 1
        self.stackedW.setCurrentIndex(prevIndex)
        print("current page is :", self.stackedW.currentIndex() + 1)
        self.text_CIF.setText(self.list_CIF[prevIndex])
        self.text_DB_file.setText(self.list_DB[prevIndex])
        #self.text_DB_size.setText(self.list_DB_size[prevIndex])
        # self.spinBox_diff.setValue(self.list_diff[prevIndex])
        # self.checkBox_SG.setChecked(self.list_SG[prevIndex])
        # self.spinBox_poly.setValue(self.list_poly[prevIndex])
        # self.spinBox_window.setValue(self.list_window[prevIndex])
        if prevIndex == 0 :
            self.previous_button.setEnabled(False)
        if self.next_button.isEnabled() == False:
            self.next_button.setEnabled(True)
            self.save_button.setEnabled(False)
             
    def nextPage (self):
        nextIndex = self.stackedW.currentIndex() + 1
        self.stackedW.setCurrentIndex(nextIndex)
        print("current page is :", self.stackedW.currentIndex() + 1)
        self.text_CIF.setText(self.list_CIF[nextIndex])
        self.text_DB_file.setText(self.list_DB[nextIndex])
        #self.text_DB_size.setText(self.list_DB_size[nextIndex])
        # self.spinBox_diff.setValue(self.list_diff[nextIndex])
        # self.checkBox_SG.setChecked(self.list_SG[nextIndex])
        # self.spinBox_poly.setValue(self.list_poly[nextIndex])
        # self.spinBox_window.setValue(self.list_window[nextIndex])
        if nextIndex == self.nbPhase -1 :
            self.next_button.setEnabled(False)
            self.save_button.setEnabled(True)
        if self.previous_button.isEnabled() == False:
            self.previous_button.setEnabled(True)
        
    def saveClicked (self) :
        empty = self.list_CIF.count(None) + self.list_DB.count(None) + self.list_DB_size.count(None)
        if empty >0 :
            self.showMsgBox()
        else :
            self.parent.listCIF.setValue(self.list_CIF)
            self.parent.listDB.setValue(self.list_DB)
            self.parent.listDBsize.setValue(self.list_DB_size)
            self.parent.listDiff.setValue(self.list_diff)
            self.parent.listSG.setValue(self.list_SG)
            self.parent.listPoly.setValue(self.list_poly)
            self.parent.listWindow.setValue(self.list_window)
            self.close

    def showMsgBox (self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText("At least one file or data base size is missing.")
        msg.setWindowTitle("Critical MessageBox")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        retval = msg.exec()
    
    def stackedWSettings (self, index):
        layout_page = QVBoxLayout()
        string = f'Phase {index}'
        layout_page.addWidget(QLabel(string))
        layout_page.addWidget(self.gB_viewing)
        self.list_pages[index].setLayout(layout_page)
             
    def loadFile (self):
        i = self.stackedW.currentIndex()
        sender = self.sender()
        options = QFileDialog.Options()
        if sender == self.load_CIF_button :
            path, _ = QFileDialog.getOpenFileName(self, f"Select a CIF file :", "", "Tous les fichiers (*)", options=options)
            self.text_CIF.setText(path)
            self.list_CIF[i] = path
        else :
            path, _ = QFileDialog.getOpenFileName(self, f"Select a Data Base file :", "", "Tous les fichiers (*)", options=options)
            self.text_DB_file.setText(path)
            self.list_DB[i] = path
            #self.text_DB_size = taille de la DB du fichier choisi
             
 ##############################  the following classes are used for testing the above classes ########################################## 
         
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fenêtre principale")
         
        self.nPhases = 1
        self.nPhasesList = []
        self.listCIF = [""]
        self.listDB = [""]
        self.listDB_size = [0]
        self.listDiff = [0]
        self.listSG = [False]
        self.listPoly = [None]
        self.listWindow = [None]
         
        # Layout de la fenêtre principale
        layout = QVBoxLayout()
         
        # Bouton pour ouvrir la fenêtre secondaire
        self.button = QPushButton("Ouvrir la fenêtre secondaire")
        self.button.clicked.connect(self.open_secondary_window)
         
        self.nPhases_label = QLabel(f"nPhases : {self.nPhases}")
         
        # Ajout d'un QTextEdit pour l'entrée de texte
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("Entrez votre texte ici...")  # Texte d'exemple
        self.text_edit.setText("no phase entered")  # Exemple de texte initial
         
         
         
        layout.addWidget(self.nPhases_label)
        layout.addWidget(self.button)
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

    def open_secondary_window(self):
        # Créer et afficher la fenêtre secondaire
        self.phasesLoad = phasesLoading(self)
        self.phasesLoad.exec_()  # Affiche la fenêtre secondaire en mode modale

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())   
    

