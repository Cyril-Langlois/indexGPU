# -*- coding: utf-8 -*-
"""
Created on Fri Nov 17 08:37:15 2023

@author: glhote1
"""
' See the version IPF_V2 for IPF display outside the iniCHORD GUI'

import os
import os.path
import h5py
import numpy as np

import matplotlib.pyplot as plt
import diffpy

import Dans_Diffraction as da
import indexGPU.Xallo as xa
from indexGPU import Symetry as sy

from orix.crystal_map import CrystalMap, PhaseList
from orix.quaternion import Rotation, symmetry
from orix import plot as orixPlot
from orix.vector import Vector3d

import tkinter as tk
from tkinter import filedialog, Tk

from inichord import General_Functions as gf

root = tk.Tk()       # initialisation du dialogue
root.withdraw()

print('hey')

#%% fonctions
def Display_IPF_GUI(CIFpath, nScoresOri, IPF_view = "X"):
    
    phase = diffpy.structure.loadStructure(CIFpath)
    
    crys = da.functions_crystallography.readcif(CIFpath)
    PhaseName = crys["_chemical_formula_sum"]
    numSG = crys["_space_group_IT_number"]
    PG = symmetry.get_point_group(int(numSG), True).name
    
    phaseNum = 1
    
    quats = nScoresOri[0, :, :, :]
    
    if IPF_view == "X":
        IPFim, xmap = IPF_Z_GUI(quats, PhaseName, PG, phase, phaseNum, Ipf_dir = Vector3d.xvector())
    elif IPF_view == "Y":
        IPFim, xmap = IPF_Z_GUI(quats, PhaseName, PG, phase, phaseNum, Ipf_dir = Vector3d.yvector())
    elif IPF_view == "Z":
        IPFim, xmap = IPF_Z_GUI(quats, PhaseName, PG, phase, phaseNum, Ipf_dir = Vector3d.zvector())

    return IPFim

def IPF_Z_GUI(simple_quats, PhaseName, PG, phase, phaseNum, Ipf_dir = Vector3d.zvector()):

    # before these operations, quaternions (axe 0), height (axe 10), width (axe 2)
    simple_quats = np.rot90(simple_quats, 1, (1, 0))
    simple_quats = np.rot90(simple_quats, 1, (2, 1))
    # after these operations, height (axe 0), width (axe 1), quaternions (axe 2)
    
    width = len(simple_quats[0, :, 0])
    height = len(simple_quats[:, 0, 0])

    # from quaternion stack to quaternion along rows
    page = np.zeros((height * width, 7))
    k = 0

    for i in range(height):
        for j in range(width):
            
            page[k, 0] = phaseNum
            page[k, 1] = i
            page[k, 2] = j
            page[k, 3] = simple_quats[i, j, 0]
            page[k, 4] = simple_quats[i, j, 1]
            page[k, 5] = simple_quats[i, j, 2]
            page[k, 6] = simple_quats[i, j, 3]
    
            k += 1

    phase_id = page[:, 0]     # array storing phase corresponding the quaternion 
    y = page[:, 1]            # array storing Y position corresponding the quaternion
    x = page[:, 2]            # array storing X position corresponding the quaternion
    quats = page[:, 3:]       # array storing quaternions along a row
    
    # conversion Quaternion -> axe-angle because Orix does not allow for direct quaternion loading
    axes_i = np.zeros((len(quats[0]), 3))
    angles_i = np.zeros((len(quats[0]),1))
    
    for i in range(len(quats[0])):
        a, b = xa.QuaternionToAxisAngle(quats[i, :])
        axes[i, :] = a
        angles[i] = b
 
    rotations_i = Rotation.from_axes_angles(axes_i, angles_i, degrees= True)
    
    phase_list = PhaseList(
        names=[PhaseName],
        point_groups=[PG],
        structures=phase)
    
    # Create a CrystalMap instance
    
    xmap2_i = CrystalMap(rotations=rotations_i, phase_id=phase_id, x=x, y=y, phase_list=phase_list)
    xmap2_i.scan_unit = "um"

    # select a correct color code according to the Point Group
    pg_laue = xmap2_i.phases[1].point_group.laue

    Var_o_Cu = xmap2[0][PhaseName].orientations
    
    # Orientation colors
    ipf_key = orixPlot.IPFColorKeyTSL(pg_laue, direction=Ipf_dir)

    rgb_i = ipf_key.orientation2color(o_Cu[0])
        
    # rgb is flatten, it must be reshaped to be displayed in the GUI
    rgb = np.reshape(rgb_i,(height, width, 3))

    rgb = np.flip(rgb,1)
    rgb = np.rot90(rgb)
    
    return rgb, xmap2_i