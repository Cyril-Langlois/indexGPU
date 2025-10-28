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


from orix.crystal_map import CrystalMap, PhaseList
from orix.quaternion import Rotation, symmetry
from orix import plot as orixPlot
from orix.vector import Vector3d

import tkinter as tk
from tkinter import filedialog, Tk

from inichord import General_Functions as gf

#------------------------------import for GitHub lib use-------------------------
# import indexGPU.Xallo as xa
# from indexGPU import Symetry as sy

#------------------------------import for local dev use------------------------
import Xallo as xa
import Symetry as sy



root = tk.Tk()       # initialisation du dialogue
root.withdraw()

#%% fonctions

def Display_IPF_GUI(CIFpath, quats, listCoord,  listToIndex, IPF_view):
    # CIFpath is the list of CIF paths for the analyse : list
    # nScoresOri is the final ori map : 
    # IPF_view is the axis for the IPF : string
    # listCoord is the list of groups of coordinates of pixels belonging to a given phase
    
    # Instanciation
    phase = []
    PhaseName = []
    numSG = []
    PG = []
    
    # Lists creation
    for i in range (len(CIFpath)):
        phase.append(diffpy.structure.loadStructure(CIFpath[i]))
    
        crys = da.functions_crystallography.readcif(CIFpath[i])
        name = crys["_chemical_formula_sum"]
        if name in PhaseName:
            PhaseName.append(name + "_" + str(i))
        else:
            PhaseName.append(name)
        numSG.append(crys["_space_group_IT_number"])
        PG.append(symmetry.get_point_group(int(numSG[i]), True).name)

    if IPF_view == "X":
        IPFim, xmap = IPF_Z_GUI(quats, PhaseName, PG, phase, listCoord, listToIndex, Ipf_dir = Vector3d.xvector())
    elif IPF_view == "Y":
        IPFim, xmap = IPF_Z_GUI(quats, PhaseName, PG, phase,  listCoord,listToIndex, Ipf_dir = Vector3d.yvector())
    elif IPF_view == "Z":
        IPFim, xmap = IPF_Z_GUI(quats, PhaseName, PG, phase, listCoord,listToIndex, Ipf_dir = Vector3d.zvector())

    return IPFim

def IPF_Z_GUI(simple_quats, PhaseName, PG, phase, listCoord, listToIndex, Ipf_dir = Vector3d.zvector()):

    # before these operations, quaternions (axe 0), height (axe 10), width (axe 2)
    simple_quats = np.rot90(simple_quats, 1, (1, 0))
    simple_quats = np.rot90(simple_quats, 1, (2, 1))
    # after these operations, height (axe 0), width (axe 1), quaternions (axe 2)
    
    width = len(simple_quats[0, :, 0])
    height = len(simple_quats[:, 0, 0])

    # from quaternion stack to quaternion along rows
    page = np.zeros((height * width, 7))
    k = 0
    
    for i, p in enumerate(listCoord):
        if listToIndex[i]:
            w = i
        else:
            w = -1
        for c in p:     
            page[k, 0] = w
            page[k, 1] = c[0]
            page[k, 2] = c[1]
            page[k, 3] = simple_quats[c[0], c[1], 0]
            page[k, 4] = simple_quats[c[0], c[1], 1]
            page[k, 5] = simple_quats[c[0], c[1], 2]
            page[k, 6] = simple_quats[c[0], c[1], 3]
    
            k += 1
      
    #Creation of the elements necessary to instance a CrystalMap        
    phase_id = page[:, 0]     # array storing phase corresponding to the quaternion 
    y = page[:, 2]            # array storing Y position corresponding the quaternion
    x = page[:, 1]            # array storing X position corresponding the quaternion
    quats = page[:, 3:]       # array storing quaternions along a row
    
        # conversion Quaternion -> axe-angle because Orix does not allow for direct quaternion loading
    axes_i = np.zeros((len(quats), 3))
    angles_i = np.zeros((len(quats),1))
    
    for i in range(len(quats)):
        a, b = xa.QuaternionToAxisAngle(quats[i, :])
        axes_i[i, :] = a
        angles_i[i] = b
 
    rotations_i = Rotation.from_axes_angles(axes_i, angles_i, degrees= True)
    
    phase_list = PhaseList(
        names=PhaseName,
        point_groups=PG,
        structures=phase)

    # Create a CrystalMap instance
    xmap2_i = CrystalMap(rotations=rotations_i, phase_id=phase_id, x=x, y=y, phase_list=phase_list)
    xmap2_i.scan_unit = "um"

    # select a correct color code according to the Point Group
    # Pick up the CrystalMap attribute
    pointGroups = xmap2_i.phases.point_groups
    
    # Pick up Phases attributes
    pg_laue = []
    o_Cu = []
    ipf_key = []
    rgb_i = []

    for i in range(len(PhaseName)):
        if -1 in phase_id:
            pg_laue.append(pointGroups[i+1].laue)
        else:
            pg_laue.append(pointGroups[i].laue)
        o_Cu.append(xmap2_i[PhaseName[i]].orientations)
        ipf_key.append(orixPlot.IPFColorKeyTSL(pg_laue[i], direction=Ipf_dir))
        rgb_i.append(ipf_key[i].orientation2color(o_Cu[i]))

    # rgb is flatten, it must be reshaped to be displayed in the GUI
    
    rgb = np.zeros((height, width, 3))
    i = 0
    p = 0
    for ph, val in enumerate(listToIndex):
        if val:
            for col in rgb_i[p]:
                rgb[int(x[i]), int(y[i]), :] = col
                i += 1
            p += 1
        else:
            i += len(listCoord[ph])

    return rgb, xmap2_i
