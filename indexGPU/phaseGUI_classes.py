import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QCheckBox, QSpinBox, QGroupBox, QTextEdit, QHBoxLayout, QVBoxLayout, QDialog, QRadioButton, QFileDialog, QLabel
from PyQt5.QtCore import Qt, QTimer, QSize

##############################  the following classes are used for indexation  ##########################################

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
