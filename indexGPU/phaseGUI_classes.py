import os

from inspect import getsourcefile
from os.path import abspath
import pyqtgraph as pg
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QCheckBox, QSpinBox, QGroupBox, QTextEdit, QHBoxLayout, QVBoxLayout, QDialog, QRadioButton, QFileDialog, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QSize
#from indexGPU import Indexation_lib as il
import indexGPU.Indexation_lib as il
from inichord import General_Functions as gf 
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
       
        self.nbPhase = nbPhases
        self.list_phase = [il.phaseObject()]*self.nbPhase
        self.list_CIF = [None]*self.nbPhase
        self.list_DB = [None]*self.nbPhase
        self.list_DB_size = [None]*self.nbPhase
        self.list_diff = [0]*self.nbPhase
        self.list_SG = [False]*self.nbPhase
        self.list_poly = [2]*self.nbPhase
        self.list_window = [3]*self.nbPhase
        self.otsu = True
        
        #SETTINGS FENETRE
        self.gB_SG.setVisible(False) #Savgol non visible par défaut
        
        self.label_bbtn.setVisible(False) #Bouton chargement otsu non visible par défaut
 
        if self.nbPhase == 1 : #Gestion des boutons previous et next
            self.previous_button.setVisible(False)
            self.next_button.setVisible(False)
        # else :
        #     self.list_pages = []
        #     for i in range(self.nbPhase):
        #         self.list_pages.append(QWidget())
        #         self.stackedW.addWidget(self.list_pages[i])
        #         self.stackedWSettings(i)
        
        if self.otsu :
            self.label_bbtn.setVisible(True)

            
 
 
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
       
        
    #METHODES    
        
    def importLabel(self): 
        # self.defaultIV() 
        options = QFileDialog.Options()
        #self.StackLoc, self.StackDir = gf.getFilePathDialog("Open map (*.tiff)")
        path, _ = QFileDialog.getOpenFileName(self, f"Select a map :", "", "Tous les fichiers (*.tiff)", options=options)
        
        self.label_map = tf.TiffFile(path).asarray()
        self.label_map = np.flip(self.label_map, 0)
        self.label_map = np.rot90(self.label_map, k=1, axes=(1, 0))
        self.otsuListCreation()
        self.displaylabels(self.thresholded_maps[0])
        self.label_title.setText("Phase n°: 0")
        
    def otsuListCreation (self):
        thresholds = []
        
        for i in range(0,self.nbPhase):
            var = i
            thresholds.append(i)
        
        self.thresholded_maps = []
        for threshold in thresholds:
            thresholded_map = np.where(self.label_map == threshold,1,0)
            self.thresholded_maps.append(thresholded_map)

    
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
        self.list_DB_size[i] = self.text_DB_size.text()
   
    def savgolParam(self):
        i = self.stackedW.currentIndex()
        if self.gB_SG.isVisible():
            self.gB_SG.setVisible(False)
            self.adjustSize()
            self.list_SG[i] = False
            self.list_poly[i] = None
            self.list_window[i] = None
        else:
            self.gB_SG.setVisible(True)
            self.adjustSize()
            self.list_SG[i] = True
        
    def previousPage (self):
        prevIndex = self.stackedW.currentIndex() - 1
        self.stackedW.setCurrentIndex(prevIndex)
        print("current page is :", self.stackedW.currentIndex() + 1)
        self.text_CIF.setText(self.list_CIF[prevIndex])
        self.text_DB_file.setText(self.list_DB[prevIndex])
        self.text_DB_size.setText(self.list_DB_size[prevIndex])
        self.spinBox_diff.setValue(self.list_diff[prevIndex])
        self.checkBox_SG.setChecked(self.list_SG[prevIndex])
        if self.list_SG[prevIndex] :
            self.spinBox_poly.setValue(self.list_poly[prevIndex])
            self.spinBox_window.setValue(self.list_window[prevIndex])
        if prevIndex == 0 :
            self.previous_button.setEnabled(False)
        if self.next_button.isEnabled() == False:
            self.next_button.setEnabled(True)
            self.save_button.setEnabled(False)
        if self.otsu :
            self.displaylabels(self.thresholded_maps[prevIndex])
            self.label_title.setText("Phase n°: " + str(prevIndex))
             
    def nextPage (self):
        nextIndex = self.stackedW.currentIndex() + 1
        self.stackedW.setCurrentIndex(nextIndex)
        print("current page is :", self.stackedW.currentIndex() + 1)
        self.text_CIF.setText(self.list_CIF[nextIndex])
        self.text_DB_file.setText(self.list_DB[nextIndex])
        self.text_DB_size.setText(self.list_DB_size[nextIndex])
        self.spinBox_diff.setValue(self.list_diff[nextIndex])
        self.checkBox_SG.setChecked(self.list_SG[nextIndex])
        if self.list_SG[nextIndex] :
            self.spinBox_poly.setValue(self.list_poly[nextIndex])
            self.spinBox_window.setValue(self.list_window[nextIndex])
        if nextIndex == self.nbPhase -1 :
            self.next_button.setEnabled(False)
            self.save_button.setEnabled(True)
        if self.previous_button.isEnabled() == False:
            self.previous_button.setEnabled(True)
        if self.otsu :
            self.displaylabels(self.thresholded_maps[nextIndex])
            self.label_title.setText("Phase n°: " + str(nextIndex))
        
    def saveClicked (self) :
        empty = self.list_CIF.count(None) + self.list_DB.count(None) + self.list_DB_size.count(None)
        if empty >0 :
            self.showMsgBox()
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
        #layout_page.addWidget(self.gB_viewing)
        self.list_pages[index].setLayout(layout_page)
             
    def loadFile (self):
        i = self.stackedW.currentIndex()
        sender = self.sender()
        options = QFileDialog.Options()
        if sender == self.load_CIF_button :
            path, _ = QFileDialog.getOpenFileName(self, f"Select a CIF file :", "", "Tous les fichiers (*.cif)", options=options)
            self.text_CIF.setText(path)
            self.list_CIF[i] = path
        else :
            path, _ = QFileDialog.getOpenFileName(self, f"Select a Data Base file :", "", "Tous les fichiers (*.crddb)", options=options)
            self.text_DB_file.setText(path)
            self.list_DB[i] = path
            #self.text_DB_size = taille de la DB du fichier choisi
    
    def displaylabels(self, series): # Display of label map
        self.LabelsSeries.ui.roiBtn.hide()
        self.LabelsSeries.ui.menuBtn.hide()
        
        view = self.LabelsSeries.getView()
        state = view.getState()        
        self.LabelsSeries.setImage(series) 
        view.setState(state)
        
        histplot = self.LabelsSeries.getHistogramWidget()
        self.LabelsSeries.setColorMap(pg.colormap.get('viridis'))

    
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
    
class phaseIndexParam(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("Indexation parameters")
        self.parent = parent
        
        layout = QVBoxLayout()
        
        self.groupBoxNPROF = QGroupBox("Database subsampling")
        self.NPROFlayout = QVBoxLayout()
        self.DBnb = QLineEdit("# DB profiles to be considered")
                
        self.NPROFlayout.addWidget(self.DBnb)
        self.groupBoxNPROF.setLayout((self.NPROFlayout))
        
        # Création de la groupBox générale de diff
        self.groupboxDiff = QGroupBox("Profile differentiation parameters")
        self.Diff_layout = QVBoxLayout()
        
        self.diffInd = QLabel("Order (0: no differentiation")
               
        self.counterDiff = QSpinBox()
        self.counterDiff.setRange(0, 3)  # Plage de 0 à 100
        self.counterDiff.setValue(0)  # Valeur initiale
        
        self.checkboxSG = QCheckBox("Savitzky-Golay differentiation ?")
        self.checkboxSG.setChecked(False)
        self.checkboxSG.setVisible(True)
        
        
        self.Diff_layout.addWidget(self.diffInd)
        self.Diff_layout.addWidget(self.counterDiff)
        self.Diff_layout.addWidget(self.checkboxSG)        
        
        self.groupboxDiff.setLayout(self.Diff_layout)
        
        
        # Création de la groupBox générale de SG
        self.groupboxSG = QGroupBox("SG Parameters")
        self.groupboxSG.setVisible(False)
        self.SG_layout = QVBoxLayout()
        self.SGvis = False
        
        self.SGwin_layout = QHBoxLayout()
        self.SGwin_Label = QLabel("Window size : ")
        self.counterSGwin = QSpinBox()
        self.counterSGwin.setRange(2, 8)  # Plage de 0 à 100
        self.counterSGwin.setValue(3)  # Valeur initiale
        
        self.SGwin_layout.addWidget(self.SGwin_Label)
        self.SGwin_layout.addWidget(self.counterSGwin)
        
        self.SGpoly_layout = QHBoxLayout()
        self.SGpoly_Label = QLabel("Polynome order : ")
        self.counterSGpoly = QSpinBox()
        self.counterSGpoly.setRange(0, 7)  # Plage de 0 à 100
        self.counterSGpoly.setValue(2)  # Valeur initiale
  
        self.SGpoly_layout.addWidget(self.SGpoly_Label)
        self.SGpoly_layout.addWidget(self.counterSGpoly)
        
        self.SG_layout.addLayout(self.SGwin_layout)
        self.SG_layout.addLayout(self.SGpoly_layout)
        self.groupboxSG.setLayout(self.SG_layout)    
        
        self.ok_button = QPushButton("Validate")
        
        layout.addWidget(self.groupBoxNPROF)
        layout.addWidget(self.groupboxDiff)
        layout.addWidget(self.groupboxSG)
        layout.addWidget(self.ok_button)      
        

        self.setLayout(layout)
        
        # connections
        self.DBnb.textChanged.connect(self.DB_Size)
        self.checkboxSG.stateChanged.connect(self.savgolParam)
        
        self.counterDiff.valueChanged.connect(self.SpinBox_changed)
        self.counterSGwin.valueChanged.connect(self.SpinBox_changed)
        self.counterSGpoly.valueChanged.connect(self.SpinBox_changed)
        
        self.ok_button.clicked.connect(self.close)
        
    def SpinBox_changed(self):
        sender = self.sender()
        if sender == self.counterDiff:
            self.parent.diff = self.counterDiff.value()
        elif sender == self.counterSGwin:
            self.parent.SG_win = self.counterSGwin.value()
        else:
            self.parent.SG_poly = self.counterSGpoly.value()
        
    
    def DB_Size(self, text):
        self.database_size = int(text)
        self.parent.DB_Size = self.database_size
   
    def savgolParam(self):
        if self.groupboxSG.isVisible():
            self.groupboxSG.setVisible(False)
            self.adjustSize()
        else:
            self.groupboxSG.setVisible(True)
            self.adjustSize()
        self.parent.SG = self.checkboxSG.isChecked()


##############################  the following classes are used for testing the above classes ##########################################
        
class phasesLoading(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("Fenêtre secondaire")
        self.parent = parent
        
        # Data to be gathered
        
        self.DB_Size = 1
        self.SG = False
        self.diff = 0
        self.SG_win = 3
        self.SG_poly = 2
        
        layout = QVBoxLayout()
        
        # Bouton pour ouvrir un fichier
        self.openButton = QPushButton("Open phase files")
        self.openButton.clicked.connect(self.open_file)
        
        # Création d'un spinBox pour le nb de phases
        self.nPhases = QSpinBox()
        self.nPhases.setRange(1, 5)  # Plage de 0 à 100
        self.nPhases.setValue(1)  # Valeur initiale
        
        # Ajouter un label général
        self.nPhases_titre = QLabel(f"Enter phase number :")
        
        # Ajout au layout
        layout.addWidget(self.nPhases_titre)
        layout.addWidget(self.nPhases)
        layout.addWidget(self.openButton)
              
        # Connecter le signal de changement de valeur du slider
        self.nPhases.valueChanged.connect(self.update_SpinBox_value)
        
        self.setLayout(layout)
        
    def update_SpinBox_value(self):
        self.parent.nPhases = self.nPhases.value()

    def open_file(self):
        # Dialogue pour ouvrir un fichier
        options = QFileDialog.Options()
        
        self.parent.text_edit.clear()
        self.parent.text_edit.moveCursor(self.parent.text_edit.textCursor().Start)
        
        for i in range(self.parent.nPhases):
            # CIF_path, _ = QFileDialog.getOpenFileName(self, f"Select CIF file of phase {i}", "", "Tous les fichiers (*)", options=options)
            # DB_path, _ = QFileDialog.getOpenFileName(self, f"Select database file of phase {i}", "", "Tous les fichiers (*)", options=options)
            CIF_path = "yy"
            DB_path = "ee"
            
            if CIF_path:
                self.parent.nPhasesList.append([CIF_path, DB_path])
                self.parent.text_edit.append(CIF_path + '\n')
                self.parent.text_edit.append(DB_path + '\n')
                self.parent.text_edit.append('\n')
            
            self.phasesIndex = phaseIndexParam(self)
            self.phasesIndex.exec_()  # Affiche la fenêtre secondaire en mode modale
            print(f"phaseLoading.DB_Size : {self.DB_Size}")
            print(f"phaseLoading.SG : {self.SG}")
            print(f"phaseLoading.diff : {self.diff}")
            print(f"phaseLoading.SG_win : {self.SG_win}")
            print(f"phaseLoading.SG_poly : {self.SG_poly}")
            
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fenêtre principale")
        
        self.nPhases = 1
        self.nPhasesList = []
        
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
