import numpy as np
import pandas as pd

import time
import os
from sklearn import metrics
    
from neuro_morpho_toolbox import neuron, soma_features, projection_features
import neuro_morpho_toolbox as nmt

def load_swc_list(swc_path, zyx=False):
    '''
    load all the swc files under a folder
    :param swc_path:
    :return: dict of neurons
    '''
    neurons = {}
    start = time.time()
    for swc_file in sorted(os.listdir(swc_path)):
        if not swc_file.endswith(("swc", "SWC")):
            continue
        # print(os.path.join(swc_path, swc_file))
        cur_neuron = neuron(os.path.join(swc_path, swc_file))
        if cur_neuron.pass_qc():
            neurons[cur_neuron.name] = cur_neuron
        else:
            print("QC failed: %s" % (swc_file))
        if len(neurons) % 100 == 0:
            print("%d loaded: %.1fs" % (len(neurons), time.time()-start))
            start = time.time()
        # # Test:
        # if len(neurons)>=100:
        #     break
    return neurons

class neuron_set:
    def __init__(self, swc_path=None, zyx=False):
        '''
        load all the
        :param path:
        :param zyx:
        '''
        self.names = []
        self.neurons = {}
        self.metadata = pd.DataFrame()
        self.features = {}
        if swc_path is None:
            return
        print("Loading...")
        self.neurons = load_swc_list(swc_path, zyx)
        self.names = list(self.neurons.keys())
        self.metadata = pd.DataFrame(index=self.names)
        print("Finding soma locations...")
        sf = soma_features()
        sf.load_data_from_neuron_dict(self.neurons)
        self.features['soma_features'] = sf
        print("Getting projection features...")
        pf = projection_features()
        pf.load_data_from_neuron_dict(self.neurons)
        self.features['projection_features'] = pf
        print("Getting metadata...")
        self.metadata['SomaRegion'] = self.features['soma_features'].region.loc[self.names, 'Region']
        hemi_dict = {1:'Left', 2:'Right'}
        self.metadata['Hemisphere'] = [hemi_dict[i] for i in self.features['soma_features'].region.loc[self.names, 'Hemisphere'].tolist()]
        self.metadata['CellType'] = self.features['soma_features'].region.loc[self.names, 'Region'] # Initialized as SomaRegion
        self.metadata['Cluster'] = [0]*len(self.metadata)

        return

    def ReduceDimPCA(self, feature_set='projection_features'):
        assert feature_set in self.features.keys(), "Invalid feature_set name."
        if feature_set=='projection_features':
            df = self.features[feature_set].scaled_data
        else:
            df = self.features[feature_set].raw_data
        self.PCA = nmt.PCA_wrapper(df)
        return self.PCA

    def ReduceDimUMAP(self, feature_set='projection_features',
                      n_neighbors=3, min_dist=0.1, n_components=2, metric='euclidean'):
                      #PCA_first=True,
                      #n_PC=100 # TODO: more reasonable n_PC choice
                      
        assert feature_set in self.features.keys(), "Invalid feature_set name."
        if feature_set=='projection_features':
            df = self.features[feature_set].scaled_data
        else:
            df = self.features[feature_set].raw_data
        self.UMAP = nmt.UMAP_wrapper(df,
                                     n_neighbors=n_neighbors,
                                     min_dist=min_dist,
                                     n_components=n_components,
                                     metric=metric,
                                     PCA_first=PCA_first,
                                     n_PC=n_PC
                                     )
        return self.UMAP

    def get_clusters(self,
                     method='SNN_community',
                     karg_dict={'knn':5,
                                'metric':'minkowski',
                                'method':'FastGreedy'}
                     ):
        if method=='SNN_community':
            if 'knn' in karg_dict.keys():
                knn = karg_dict['knn']
            else:
                knn = 5
            if 'metric' in karg_dict.keys():
                metric = karg_dict['metric']
            else:
                metric = 'minkowski'
            if 'method' in karg_dict.keys():
                community_method = karg_dict['method']
            else:
                community_method = 'FastGreedy'
            cur_clusters = nmt.get_clusters_SNN_community(self.UMAP, knn=knn, metric=metric, method=community_method)
            self.metadata['Cluster'] = ['C' + str(i) for i in cur_clusters]
            print("Homogeneity: %0.3f" % metrics.homogeneity_score(self.metadata['CellType'],self.metadata['Cluster']))
            print("Completeness: %0.3f" % metrics.completeness_score(self.metadata['CellType'],self.metadata['Cluster']))
            print("V-measure: %0.3f" % metrics.v_measure_score(self.metadata['CellType'],self.metadata['Cluster']))
            print("Adjusted Rand Index: %0.3f"
              % metrics.adjusted_rand_score(self.metadata['CellType'],self.metadata['Cluster']))
            print("Adjusted Mutual Information: %0.3f"
              % metrics.adjusted_mutual_info_score(self.metadata['CellType'],self.metadata['Cluster']))
            print("Silhouette Coefficient: %0.3f"
              % metrics.silhouette_score(self.UMAP, self.metadata['Cluster'], metric='sqeuclidean'))        
            return
        # TODO: other clustering methods...



    def get_feature_values(self, feature_name):
        # Search in feature tables
        for cur_featureset_name, cur_featureset in self.features.items():
            if feature_name in cur_featureset.raw_data.columns.tolist():
                if cur_featureset_name == 'projection_features':
                    return pd.DataFrame(cur_featureset.scaled_data[feature_name])
                else:
                    return pd.DataFrame(cur_featureset.raw_data[feature_name])
        # Search in the metadata table
        if feature_name in self.metadata.columns.tolist():
            return pd.DataFrame(self.metadata[feature_name])
        # If cannot find given feature name, return empty dataframe.
        # assert True, "neuron_set.get_feature_values(self, feature_name): Invalid feature_name."
        return pd.DataFrame(index=self.names)

    def get_feature_list_values(self, feature_list):
        assert type(feature_list) == list, "neuron_set.get_feature_list_values: Input must be a list"
        res = pd.DataFrame(index=self.names)
        for feature_name in feature_list:
            tp = self.get_feature_values(feature_name)
            if tp.shape[1]>0:
                res = pd.concat([res, tp], axis=1)
        return res

    def FeatureScatter(self, feature_name, map="UMAP"):
        # Find feature values
        if type(feature_name) == list:
            z = self.get_feature_list_values(feature_list=feature_name)
        else:
            z = self.get_feature_values(feature_name=feature_name)
        # Find reduced dimension data
        if map == "UMAP":
            x = self.UMAP.iloc[:,0]
            y = self.UMAP.iloc[:,1]
        elif map == "PCA":
            x = self.PCA.iloc[:, 0]
            y = self.PCA.iloc[:, 1]
        else:
            assert True, "neuron_set.FeatureScatter(self, feature_name, map='UMAP'): Invalid map."
            return
        # If feature is categorical
        if z.select_dtypes(include=['float', 'int']).shape[1] == z.shape[1]: # If all values are numeric
            fig = nmt.quantitative_scatter(x, y, z)
        else:
            fig = nmt.qualitative_scatter(x, y, z)
        return fig

'''
    def MetricCal(self, feature_name, map="UMAP"):
        '''