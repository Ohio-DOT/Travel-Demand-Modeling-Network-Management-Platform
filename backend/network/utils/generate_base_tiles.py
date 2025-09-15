import os, tempfile, subprocess
import geopandas as gpd
# from network.models import NodeVersion, LinkVersion
# from .scripts import queryset_to_gdf
import pandas as pd
from django.contrib.gis.db.models.functions import AsWKB
from django.conf import settings

def generate_base_mbtiles(base_changeset_id):
    try:
        # Query
        # base_nodes = NodeVersion.objects.filter(changeset_id=base_changeset_id).annotate(geom_wkb=AsWKB("geometry"))
        # base_links = LinkVersion.objects.filter(changeset_id=base_changeset_id).annotate(geom_wkb=AsWKB("geometry"))
        
        base_nodes=''
        base_links=''

        # gdf_nodes = queryset_to_gdf(base_nodes, geometry_field='geom_wkb', crs='EPSG:4326')
        # gdf_links = queryset_to_gdf(base_links, geometry_field='geom_wkb', crs='EPSG:4326')
        # gdf = gpd.GeoDataFrame(pd.concat([gdf_nodes, gdf_links]), crs="EPSG:4326")

        geojson_path = os.path.join(settings.MEDIA_ROOT, 'networks', f"{base_changeset_id}.json")
        gdf = gpd.read_file(geojson_path, engine='pyogrio')
        gdf.to_crs("EPSG:4326").to_file(geojson_path, driver="GeoJSON", engine='pyogrio')

        # mbtiles_path = os.path.join(settings.MEDIA_ROOT, 'tiles', f"{base_changeset_id}.mbtiles")
        # mbtiles_path = os.path.join(r'C:\dgaldino\2025_06_TDM_NETWORK_VERSIONING_PLATFORM\tdm_nvp\backend\media\tiles', f"{base_changeset_id}.mbtiles")

        # cmd = [
        #     "docker", "run"
        #     "-o", mbtiles_path,
        #     "-l", "base_network",
        #     "-Z", "6", "-z", "16",
        #     "--drop-densest-as-needed",
        #     geojson_path,
        # ]

        # subprocess.run(cmd, check=True)
        # print(f"MBTiles written to: {mbtiles_path}")
    except Exception as e:
        print(e)