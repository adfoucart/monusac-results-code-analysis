import os
import openslide

from enum import Enum
from typing import Tuple

from xml.dom import minidom
import xml.etree.ElementTree as ET

import numpy as np
from skimage import draw
from skimage.measure import label
from skimage.morphology import disk, dilation

### --- Methods related to nary mask generation from the .xml annotations --- ###

class LabelColours:
    cl_epithelial = np.array([255,0,0])
    cl_lymphocyte = np.array([255,255,0])
    cl_neutrophil = np.array([0,0,255])
    cl_macrophage = np.array([0,255,0])
    cl_classes = [cl_epithelial, cl_lymphocyte, cl_neutrophil, cl_macrophage]
    cl_border = np.array([139,69,19])

labels_channels = {'Epithelial': 0, 'Lymphocyte': 1, 'Neutrophil': 2, 'Macrophage': 3, 'Ambiguous': 4}

def get_xml_annotations(xml_file: str) -> list:
    '''Reads xml file & returns list of annotations in the form (label_name: str, coords: np.array)'''
    annotations = []
    tree = ET.parse(xml_file)
    root = tree.getroot()
    for attrs,regions,plots in root:
        label_name = attrs[0].attrib['Name']
        
        for region in regions:
            if( region.tag == 'RegionAttributeHeaders' ): continue
            vertices = region[1]
            coords = np.array([[int(float(vertex.attrib['X'])),int(float(vertex.attrib['Y']))] for vertex in vertices]).astype('int')
            
            annotations.append((label_name, coords))

    return annotations

def generate_mask(svs_file: str) -> np.array:
    '''Generate n-ary mask from a slide's annotations.'''

    wsi = openslide.OpenSlide(svs_file)
    size = wsi.level_dimensions[0]
    mask = np.zeros((size[1],size[0],len(labels_channels))).astype('int')
    annotations = get_xml_annotations(svs_file.replace('.svs', '.xml'))

    for idl,(label_name, coords) in enumerate(annotations):
        fill = draw.polygon(coords[:,1],coords[:,0],mask.shape)
        mask[fill[0],fill[1],labels_channels[label_name]] = idl+1

    return mask

def generate_masks(directory: str) -> None:
    '''Generate n-ary masks (labeled objects w/ 1 channel per class) from a directory which follows the structure:
    - directory
        - patient folder
            - slide.svs
            - slide.svs
            - ...
        - ...
    
    Masks are saved as _nary.npy files alongside the .svs file'''
    patients = os.listdir(directory)
    
    print(f"{len(patients)} patients in directory: {directory}")
    
    for ip,patient in enumerate(patients):
        print(f"{ip+1}/{len(patients)}", end="\r")
        
        patient_dir = os.path.join(directory, patient)
        slides = [f for f in os.listdir(patient_dir) if f.split('.')[1] == 'svs']
        
        for slide in slides:
            mask = generate_mask(os.path.join(patient_dir,slide))
            np.save(os.path.join(patient_dir,slide.replace('.svs','_nary.npy')), mask)
    
    return

### --- Methods related to nary mask generation from the colorcoded predictions --- ###

def nary_from_colormap_no_border(cl_im: np.array) -> np.array:
    '''Produce n-ary mask from the color-coded image by removing the borders and re-labeling the resulting objects.'''
    mask_ids = np.zeros(cl_im.shape[:2]+(4,))
    
    masks = [(cl_im[...,0]==cl[0]) * (cl_im[...,1]==cl[1]) * (cl_im[...,2]==cl[2]) for cl in LabelColours.cl_classes]
    masks = [label(mask) for mask in masks]
    
    for i,m in enumerate(masks):
        mask_ids[...,i] = m
    
    return mask_ids

def dilate_nary(nary: np.array, r: int) -> np.array:
    '''Increasing the size of the objects in the nary map by morphological dilation, to account for the removed borders.'''
    # dilate each object
    for i in range(4):
        for j in np.unique(nary[...,i]):
            if j==0: continue
            dilated_obj = dilation(nary[...,i]==j, disk(r))
            nary[...,i][dilated_obj] = j

    return nary

### --- Methods related to the matching of (gt,pred) object pairs & the PQ computation --- ###

def match_strict_iou_class(gt_im: np.array, pred_im: np.array) -> Tuple[list, int, int, int]:
    '''Find matching pairs of objects between two n-ary masks of the same class.
    
    Returns: list of IOUs, #TP, #FP & #FN'''
    TP = FP = FN = 0    
    IOUs = []
    
    matched_instances = {}# Create a dictionary to save ground truth indices in keys and predicted matched instances as velues
                        # It will also save IOU of the matched instance in [indx][1]

    # Find matched instances and save it in a dictionary
    for i in np.unique(gt_im):
        if i == 0:
            continue

        gt_obj_mask = gt_im == i
        pred_in_obj = gt_obj_mask * pred_im
    
        for j in np.unique(pred_in_obj):
            if j == 0:
                continue

            pred_obj_mask = pred_im == j
            intersection = (gt_obj_mask & pred_obj_mask).sum()
            union = (gt_obj_mask | pred_obj_mask).sum()
            IOU = intersection/union
            if IOU> 0.5:
                matched_instances[i] = j, IOU 

    # Compute TP, FP, FN and sum of IOU of the matched instances
    pred_indx_list = np.unique(pred_im)
    pred_indx_list = np.array(pred_indx_list[1:]) # np.unique returns sorted elements -> remove 0

    # Loop on ground truth instances
    for indx in np.unique(gt_im):
        if indx == 0:
            continue

        if indx in matched_instances.keys():
            pred_indx_list = np.delete(pred_indx_list, np.argwhere(pred_indx_list == matched_instances[indx][0]))
            TP = TP+1
            IOUs.append(matched_instances[indx][1])
        else:
            FN = FN+1
                
    FP = len(np.unique(pred_indx_list))
    
    return IOUs,TP,FP,FN

def match_strict_iou_class_with_error(gt_im: np.array, pred_im: np.array) -> Tuple[list, int, int, int]:
    '''Find matching pairs of objects between two n-ary masks of the same class.
    
    Returns: list of IOUs, #TP, #FP & #FN'''
    TP = FP = FN = 0    
    IOUs = []
    
    matched_instances = {}# Create a dictionary to save ground truth indices in keys and predicted matched instances as velues
                        # It will also save IOU of the matched instance in [indx][1]

    # Find matched instances and save it in a dictionary
    for i in np.unique(gt_im):
        if i == 0:
            continue

        gt_obj_mask = gt_im == i
        pred_in_obj = gt_obj_mask * pred_im
    
        for j in np.unique(pred_in_obj):
            if j == 0:
                continue

            pred_obj_mask = pred_im == j
            intersection = (gt_obj_mask & pred_obj_mask).sum()
            union = (gt_obj_mask | pred_obj_mask).sum()
            IOU = intersection/union
            if IOU> 0.5:
                matched_instances[i] = j, IOU 

    # Compute TP, FP, FN and sum of IOU of the matched instances
    pred_indx_list = np.unique(pred_im)
    pred_indx_list = np.array(pred_indx_list[1:]) # np.unique returns sorted elements -> remove 0

    # Loop on ground truth instances
    for indx in np.unique(gt_im):
        if indx == 0:
            continue

        if indx in matched_instances.keys():
            pred_indx_list = np.delete(pred_indx_list, np.argwhere(pred_indx_list == [indx][0]))
            TP = TP+1
            IOUs.append(matched_instances[indx][1])
        else:
            FN = FN+1
                
    FP = len(np.unique(pred_indx_list))
    
    return IOUs,TP,FP,FN

def compute_PQc(IOUs: list, TP: int, FP: int, FN: int) -> float:
    '''Computes the PQ for one class from the list of True Positives IoUs, and the number of TP/FP/FN.'''
    if( TP+FP+FN == 0 ): return 0
    return sum(IOUs)/(TP+0.5*FP+0.5*FN)