from setuptools import setup, find_packages

setup(
    name='indexGPU',
    version='0.1.17',
    packages=find_packages(),
    install_requires=[
        "inichord >= 0.1.13",
		"cupy-cuda12x >= 13.3.0",
		"orix >= 0.11",
		"Dans-Diffraction >=3.2",
		"pyquaternion >=0.9",
    ],
 	data_files=[('Lib/site-packages/indexGPU', ['indexGPU/Indexation_GUI.ui']),
     ],
    
    # package_data={
    # 'indexGPU': ['Lib/site-packages/indexGPU/*.ui'],  # Inclure tous les fichiers .txt dans le dossier data
    # },
    
    
)