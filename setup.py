from setuptools import setup, find_packages
from glob import glob


setup(
    name='indexGPU',
    version='0.1.60',
    packages=find_packages(),
    install_requires=[
        "inichord >= 0.1.40",
		"cupy-cuda12x >= 14.0.0",
		"orix >= 0.11",
		"Dans-Diffraction >=3.2",
		"pyquaternion >=0.9",
    ],
 	data_files=[('Lib/site-packages/indexGPU', ['indexGPU/Indexation_GUI.ui']),('Lib/site-packages/indexGPU', ['indexGPU/Indexation_GUI_tempo2.ui']),
              ('Lib/site-packages/indexGPU', ['indexGPU/phase_form_tempo.ui']),('Lib/site-packages/indexGPU', ['indexGPU/Indexation_lib.py']),
              ('Lib/site-packages/indexGPU', ['indexGPU/phaseGUI_classes_local.py']),
			  ('Lib/site-packages/indexGPU/icons', glob('indexGPU/icons/*'))
     ],
    
    # package_data={
    # 'indexGPU': ['Lib/site-packages/indexGPU/*.ui'],  # Inclure tous les fichiers .txt dans le dossier data
    # },
    
    
)