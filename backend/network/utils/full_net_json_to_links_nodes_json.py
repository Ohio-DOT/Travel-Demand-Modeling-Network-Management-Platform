# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import geopandas as gpd

gdf = gpd.read_file('C:/dgaldino/2025_06_TDM_NETWORK_VERSIONING_PLATFORM/tdm_nvp/backend/media/networks/0982bc43-9f9d-42d2-b514-5ff4b39751f4.json', engine='pyogrio')

gdf_nodes = gdf[gdf.geometry.type == 'Point']
gdf_links = gdf[gdf.geometry.type != 'Point']

gdf_nodes.to_file('C:/dgaldino/2025_06_TDM_NETWORK_VERSIONING_PLATFORM/tdm_nvp/backend/media/networks/0982bc43-9f9d-42d2-b514-5ff4b39751f4_nodes.json', engine='pyogrio')
gdf_links.to_file('C:/dgaldino/2025_06_TDM_NETWORK_VERSIONING_PLATFORM/tdm_nvp/backend/media/networks/0982bc43-9f9d-42d2-b514-5ff4b39751f4_links.json', engine='pyogrio')