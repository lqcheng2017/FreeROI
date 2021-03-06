import os
import gzip
import numpy as np
import nibabel as nib

from ..algorithm.graph_tool import node_attr2array


def read_mgh_mgz(filepath):

    ext = os.path.splitext(filepath)[1]
    if ext == ".mgz":
        openfile = gzip.open
    elif ext == ".mgh":
        openfile = open
    else:
        raise ValueError("The data must be a mgh or mgz file!")

    fobj = openfile(filepath, "rb")
    # We have to use np.fromstring here as gzip fileobjects don't work
    # with np.fromfile; same goes for try/finally instead of with statement
    try:
        v = np.fromstring(fobj.read(4), ">i4")[0]
        if v != 1:
            # I don't actually know what versions this code will read, so to be
            # on the safe side, let's only let version 1 in for now.
            # Scalar data might also be in curv format (e.g. lh.thickness)
            # in which case the first item in the file is a magic number.
            raise NotImplementedError("Scalar data file version not supported")
        ndim1 = np.fromstring(fobj.read(4), ">i4")[0]
        ndim2 = np.fromstring(fobj.read(4), ">i4")[0]
        ndim3 = np.fromstring(fobj.read(4), ">i4")[0]
        nframes = np.fromstring(fobj.read(4), ">i4")[0]
        datatype = np.fromstring(fobj.read(4), ">i4")[0]
        # Set the number of bytes per voxel and numpy data type according to
        # FS codes
        databytes, typecode = {0: (1, ">i1"), 1: (4, ">i4"), 3: (4, ">f4"),
                               4: (2, ">h")}[datatype]
        # Ignore the rest of the header here, just seek to the data
        fobj.seek(284)
        nbytes = ndim1 * ndim2 * ndim3 * nframes * databytes
        # Read in all the data, keep it in flat representation
        # (is this ever a problem?)
        _data = np.fromstring(fobj.read(nbytes), typecode)
    finally:
        fobj.close()

    data = []
    if _data.ndim == 4:
        for idx in range(_data.shape[3]):
            data.append(np.ravel(_data[..., idx], order='F'))
    else:
        data.append(np.ravel(_data, order="F"))
    data = np.array(data).T

    return data


def read_scalar_data(fpath, n_vtx=None):

    fname = os.path.basename(fpath)
    suffix0 = fname.split('.')[-1]
    suffix1 = fname.split('.')[-2]
    islabel = False
    if suffix0 in ('curv', 'thickness'):
        data = nib.freesurfer.read_morph_data(fpath)
        data = data.astype(np.float64)

    elif suffix0 == 'label':
        data = nib.freesurfer.read_label(fpath)
        islabel = True

    elif suffix0 == 'nii':
        _data = nib.load(fpath).get_data()
        if suffix1 in ('dscalar', 'dtseries'):
            # data = np.array(_data).T
            raise RuntimeError('Unsupported data type.')
        elif suffix1 == 'dlabel':
            # data = np.array(_data.ravel())
            # islabel = True
            raise RuntimeError('Unsupported data type.')
        else:
            Warning('The data will be regarded as a nifti file.')
            data = []
            if _data.ndim == 4:
                for idx in range(_data.shape[3]):
                    data.append(np.ravel(_data[..., idx], order='F'))
            else:
                data.append(np.ravel(_data, order="F"))
            data = np.array(data).T

    elif suffix0 == 'gz' and suffix1 == 'nii':
        _data = nib.load(fpath).get_data()
        data = []
        if _data.ndim == 4:
            for idx in range(_data.shape[3]):
                data.append(np.ravel(_data[..., idx], order='F'))
        else:
            data.append(np.ravel(_data, order="F"))
        data = np.array(data).T

    elif suffix0 in ('mgh', 'mgz'):
        data = read_mgh_mgz(fpath)
        data = data.astype(np.float64)

    elif suffix0 == 'gii':
        gii_data = nib.gifti.read(fpath).darrays
        data = gii_data[0].data

    else:
        raise RuntimeError('Unsupported data type.')

    if n_vtx is None:
        if islabel:
            raise RuntimeError("Reading label as scalar data need specify the number of vertices.")
    else:
        if islabel:
            if np.max(data) <= n_vtx:
                label_array = np.zeros(n_vtx, np.int)
                label_array[data] = 1
                data = np.array([label_array]).T
            else:
                raise RuntimeError('vertices number mismatch!')
        else:
            if data.shape[0] != n_vtx:
                raise RuntimeError('vertices number mismatch!')

    if data.dtype.byteorder == '>':
        data.byteswap(True)

    return data, islabel


def node_attr2text(fpath, graph, attrs, fmt='%d', comments='#!ascii\n', **kwargs):
    """
    save nodes' attributes to text file
    :param fpath: str
        output file name
    :param graph: nx.Graph
    :param attrs: tuple e.g. ('ncut label', 'color')
        nodes' attributes which are going to be saved
    :param fmt: str or sequence of strs, optional
    :param comments: str, optional
    :param kwargs: key-word arguments for numpy.savetxt()
    :return:
    """
    header = ''
    for attr in attrs:
        header = header + attr + '\t'

    X = node_attr2array(graph, attrs)
    np.savetxt(fpath, X, fmt=fmt, header=header, comments=comments, **kwargs)
