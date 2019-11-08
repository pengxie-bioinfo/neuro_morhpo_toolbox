import time
import os
import pickle
import numpy as np

# Custom functions and classes
from .image import image
from .brain_structure import brain_structure

# Load essential data
neurite_types = ['(basal) dendrite', 'apical dendrite', 'axon', 'soma']

# "Test: check the path"
package_path = os.path.realpath(__file__).replace("__init__.py", "")
print(package_path)

# Loading CCF data from raw image can be time consuming.
print("Loading CCF Atlas data...")
start = time.time()
# saved_ccf = package_path+"data/CCF_data.pickle"
# if os.path.exists(saved_ccf):
# # if False:
#     print("load image from array")
#     annotation = image(pickle_file=saved_ccf)
# else:
#     print("load image from nrrd")
#     annotation = image(package_path+"data/annotation_25.nrrd")
#     sparse_array = sparse.COO(annotation.array)
#     pickle.dump([sparse_array, list(annotation.space.values())], open(saved_ccf, 'wb'))
#     # pickle.dump([annotation.array, list(annotation.space.values())], open(saved_ccf, 'wb'))
# print(annotation.micron_size)
annotation = image(package_path+"data/annotation_25.nrrd")
# Use 25x downsampled data to improve loading efficiency. (~1s)
# Loading 10x downsampled data takes >10s and its actually upsampled from the 25x data.
end = time.time()
print("Loading time: %.2f" % (end-start))

print("Loading CCF brain structure data...")
saved_bs = package_path+"data/BrainStructure_data.pickle"
start = time.time()
if os.path.exists(saved_bs):
    [bs] = pickle.load(open(saved_bs, 'rb'))
else:
    bs = brain_structure(package_path+"data/Mouse.csv")
    bs.get_selected_regions(package_path+"data/CCFv3 Summary Structures.xlsx")
    pickle.dump([bs], open(saved_bs, 'wb'))
end = time.time()
print("Loading time: %.2f" % (end-start))


print("Loading selected CCF Atlas and Contour data...")
start = time.time()
saved_contour = package_path+"data/CCF_6_01.pickle"
Contour01 = pickle.load(open(saved_contour, 'rb'))[0]==1
saved_ccf25 = package_path+"data/ccf_25.pickle"
if os.path.exists(saved_ccf25):
    [ccfArray] = pickle.load(open(saved_ccf25, 'rb'))
else:
    ccfArray = annotation.array.copy()
    regionAll, count = np.unique(ccfArray, return_counts=True)
    regionAll = np.setdiff1d(regionAll,np.array([0]))
    for iterR in regionAll:
        ccfArray[ccfArray==int(iterR)] = bs.dict_to_selected[iterR]
    pickle.dump([ccfArray], open(saved_ccf25, 'wb'))
end = time.time()
print("Loading time: %.2f" % (end-start))

from .swc import neuron
from .neuron_features import features, projection_features, soma_features, dendrite_features, lm_dendrite_features, lm_axon_features
from .neuron_set import neuron_set
from .utilities import *
from .ml_utilities import *
from .plot import *
