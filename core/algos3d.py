#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
MakeHuman 3D Transformation functions. 

**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Manuel Bastioni, Marc Flerackers

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

This module contains algorithms used to perform high-level 3D 
transformations on the 3D mesh that is used to represent the human 
figure in the MakeHuman application.
 
These currently include: 

  - morphing for anatomical variations 
  - pose deformations
  - mesh coherency tests (for use during the development cycle)
  - visualisation functions (for use during the development cycle)
  
This will also be where any future mesh transformation 
algorithms will be coded. For example: 

  - collision deformations
  - etc..

"""

__docformat__ = 'restructuredtext'

import os
import numpy as np
import log

NMHVerts = 18528

targetBuffer = {}

class Target:

    """
    This class is used to store morph targets.
    """

    def __init__(self, obj, name):
        """
        This method initializes an instance of the Target class.
            
        Parameters
        ----------
        
        obj:
            *3d object*. The base object (to which a target can be applied).
            This object is read to determine the number of vertices to
            use when initializing this data structure.
        
        name:
            *string*. The name of this target.
        
        
        """
        
        self.name = name
        self.morphFactor = -1

        try:
            self._load(self.name)
        except:
            self.verts = []
            log.error('Unable to open %s', name)
            return

        self.faces = obj.getFacesForVertices(self.verts)

    dtype = [('index','u4'),('vector','(3,)f4')]
    npzfile = None
    npztime = None

    def _load_text(self, name):
        data = []
        with open(name) as fd:
            for line in fd:
                translationData = line.split()
                if len(translationData) != 4:
                    continue
                vertIndex = int(translationData[0])
                translationVector = (float(translationData[1]), float(translationData[2]), float(translationData[3]))
                data.append((vertIndex, translationVector))

        raw = np.asarray(data, dtype=Target.dtype)
        self.verts = raw['index']
        self.data = raw['vector']

    def _load_binary_archive(self, name):
        name = name.replace('\\', '/')
        bname = os.path.splitext(name)[0]
        iname = '%s.index' % bname
        vname = '%s.vector' % bname
        if Target.npztime < os.path.getmtime(name):
            log.message('compiled file newer than archive: %s', name)
            raise RuntimeError()
        if iname not in Target.npzfile:
            log.message('compiled file missing: %s', iname)
            raise RuntimeError()
        if vector not in Target.npzfile:
            log.message('compiled file missing: %s', vname)
            raise RuntimeError()
        self.verts = Target.npzfile[iname]
        self.data = Target.npzfile[vname] * 1e-3

    def _load_binary_files(self, name):
        bname = os.path.splitext(name)[0]
        iname = '%s.index.npy' % bname
        vname = '%s.vector.npy' % bname
        if not os.path.exists(iname):
            log.message('compiled file missing: %s', name)
            raise RuntimeError()
        if not os.path.exists(vname):
            log.message('compiled file missing: %s', name)
            raise RuntimeError()
        if os.path.getmtime(iname) < path.getmtime(name):
            log.message('compiled file out of date: %s', iname)
            raise RuntimeError()
        if os.path.getmtime(vname) < path.getmtime(name):
            log.message('compiled file out of date: %s', vname)
            raise RuntimeError()
        self.verts = np.load(iname)
        self.data = np.load(vname) * 1e-3

    def _load_binary(self, name):
        if Target.npzfile is None:
            try:
                npzname = 'data/targets.npz'
                Target.npzfile = np.load(npzname)
                Target.npztime = os.path.getmtime(npzname)
            except:
                log.message('no compressed targets found')
                Target.npzfile = False
        if Target.npzfile == False:
            self._load_binary_files(name)
        else:
            self._load_binary_archive(name)

    def _save_binary(self, name):
        log.message('compiling %s', name)
        try:
            bname, ext = os.path.splitext(name)
            iname = '%s.index.npy' % bname
            vname = '%s.vector.npy' % bname
            index = np.ascontiguousarray(self.verts, dtype=np.uint16)
            vector = np.ascontiguousarray(np.round(self.data * 1e3), dtype=np.int16)
            np.save(iname, index)
            np.save(vname, vector)
            return iname, vname
        except StandardError, e:
            log.error('error saving %s', name)

    def _load(self, name):
        logger = log.getLogger('mh.load')
        logger.debug('loading target %s', name)
        try:
            self._load_binary(name)
        except StandardError, e:
            self._load_text(name)
        logger.debug('loaded target %s', name)

    def apply(self, obj, morphFactor, update=True, calcNormals=True, faceGroupToUpdateName=None, scale=(1.0,1.0,1.0)):
        self.morphFactor = morphFactor                

        if len(self.verts):
            
            if morphFactor or calcNormals or update:
            
                if faceGroupToUpdateName:
                    # if a facegroup is provided, apply it ONLY to the verts used
                    # by the specified facegroup.
                    vmask, fmask = obj.getVertexAndFaceMasksForGroups([faceGroupToUpdateName])

                    srcVerts = np.argwhere(vmask[self.verts])[...,0]
                    facesToRecalculate = self.faces[fmask[self.faces]]
                else:
                    # if a vertgroup is not provided, all verts affected by
                    # the targets will be modified

                    facesToRecalculate = self.faces
                    srcVerts = np.s_[...]

                dstVerts = self.verts[srcVerts]

            if morphFactor:
                # Adding the translation vector

                scale = np.array(scale) * morphFactor
                obj.coord[dstVerts] += self.data[srcVerts] * scale[None,:]
                obj.markCoords(dstVerts, coor=True)

            if calcNormals:
                obj.calcNormals(1, 1, dstVerts, facesToRecalculate)
            if update:
                obj.update(dstVerts)

            return True
            
        return False

def getTarget(obj, targetPath):
    """
    This function retrieves a set of translation vectors from a morphing 
    target file and stores them in a buffer. It is usually only called if 
    the translation vectors from this file have not yet been buffered during 
    the current session. 
    
    The translation target files contain lists of vertex indices and corresponding 
    3D translation vectors. The buffer is structured as a list of lists 
    (a dictionary of dictionaries) indexed using the morph target file name, so:
    \"targetBuffer[targetPath] = targetData\" and targetData is a list of vectors 
    keyed on their vertex indices. 
    
    For example, a translation direction vector
    of [0,5.67,2.34] for vertex 345 would be stored using 
    \"targetData[345] = [0,5.67,2.34]\".
    If this is taken from target file \"foo.target\", then this targetData could be
    assigned to the buffer with 'targetBuffer[\"c:/MH/foo.target\"] = targetData'. 
    
    Parameters
    ----------

    obj:
        *3d object*. The target object to which the translations are to be applied.
        This object is read by this function to define a list of the vertices 
        affected by this morph target file.

    targetPath:
        *string*. The file system path to the file containing the morphing targets. 
        The precise format of this string will be operating system dependant.
    """

    try:
        target = targetBuffer[targetPath]
    except KeyError:
        target = None
        
    if target:
        if hasattr(target, "isWarp"):
            target.reinit()
        return target

    target = Target(obj, targetPath)
    targetBuffer[targetPath] = target
    
    return target

def loadTranslationTarget(obj, targetPath, morphFactor, faceGroupToUpdateName=None, update=1, calcNorm=1, scale=[1.0,1.0,1.0]):
    """
    This function retrieves a set of translation vectors and applies those 
    translations to the specified vertices of the mesh object. This set of 
    translations corresponds to a particular morph target file.  
    If the file has already been loaded into memory then the translation 
    vectors are read from the target data buffer, otherwise a function is 
    first called to load the target data from disk into a buffer for 
    future use.
    
    The translation target files contain lists of vertex indices and corresponding 
    3D translation vectors. The translation vector for each vertex is multiplied 
    by a common factor (morphFactor) before being applied to the specified vertex.
    
    Parameters
    ----------

    obj:
        *3d object*. The target object to which the translations are to be applied.
        This object is read and updated by this function.

    targetPath:
        *string*. The file system path to the file containing the morphing targets. 
        The precise format of this string will be operating system dependant.

    morphFactor:
        *float*. A factor between 0 and 1 controlling the proportion of the translations 
        to be applied. If 0 then the object remains unmodified. If 1 the 'full' translations
        are applied. This parameter would normally be in the range 0-1 but can be greater 
        than 1 or less than 0 when used to produce extreme deformations (deformations 
        that extend beyond those modelled by the original artist).

    faceGroupToUpdateName:
        *string*. Optional: The name of a single facegroup to be affected by the target.
        If specified, then only transformations to faces contained by the specified 
        facegroup are applied. If not specified, all transformations contained within the
        morph target file are applied. This permits a single morph target file to contain
        transformations that affect multiple facegroups, but to only be selectively applied 
        to individual facegroups.

    update:
        *int flag*. A flag to indicate whether the update method on the object should be called.

    calcNorm:
        *int flag*. A flag to indicate whether the normals are to be recalculated (1/true) 
        or not (0/false).   

    """

    if not (morphFactor or update):
        return

    target = getTarget(obj, targetPath)

    target.apply(obj, morphFactor, update, calcNorm, faceGroupToUpdateName, scale)

def saveTranslationTarget(obj, targetPath, groupToSave=None, epsilon=0.001):
    """
    This function analyses an object to determine the differences between the current 
    set of vertices and the vertices contained in the *originalVerts* list, writing the
    differences out to disk as a morphing target file.

    Parameters
    ----------

    obj:
        *3d object*. The object from which the current set of vertices is to be determined.

    targetPath:
        *string*. The file system path to the output file into which the morphing targets
        will be written.

    groupToSave:
        *faceGroup*. It's possible to save only the changes made to a specific part of the 
        mesh object by indicating the face group to save.

    epsilon:
        *float*. The distance that a vertex has to have been moved for it to be 
        considered 'moved'
        by this function. The difference between the original vertex position and
        the current vertex position is compared to this value. If that difference is greater
        than the value of epsilon, the vertex is considered to have been modified and will be 
        saved in the output file as a morph target.   

    """

    if not groupToSave:
        vertsToSave = np.arange(len(obj.coord))
    else:
        pass  # TODO verts from group

    originalVerts = obj.orig_coord[vertsToSave]
    targetVerts = obj.coord[vertsToSave]

    delta = targetVerts - originalVerts
    dist2 = np.sum(delta ** 2, axis=-1)
    valid = dist2 > (epsilon ** 2)
    del dist2
    delta = delta[valid]
    vertsToSave = vertsToSave[valid]
    nVertsExported = len(vertsToSave)

    try:
        with open(targetPath, 'w') as fileDescriptor:
            for i in xrange(nVertsExported):
                fileDescriptor.write('%d %f %f %f\n' % (vertsToSave[i], delta[i,0], delta[i,1], delta[i,2]))

        if nVertsExported == 0:
            log.warning('Zero verts exported in file %s', targetPath)
    except:
        log.error('Unable to open %s', targetPath)
        return None


def resetObj(obj, update=None, calcNorm=None):
    """
    This function resets the positions of the vertices of an object to their original base positions.
    
    Parameters
    ----------
    
    obj:
        *3D object*. The object whose vertices are to be reset.

    update:
        *int*. An indicator to control whether to call the vectors update method.

    calcNorm:
        *int*. An indicator to control whether or not the normals should be recalculated

    """

    originalVerts = obj.orig_coord
    obj.changeCoords(originalVerts)
    if update:
        obj.update()
    if calcNorm:
        obj.calcNormals()
