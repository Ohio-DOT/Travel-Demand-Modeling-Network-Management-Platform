from network.models import NodeVersion, LinkVersion
import tempfile
import os
import zipfile
import uuid
import pandas as pd
import geopandas as gpd
from shapely.wkb import loads as wkb_loads
import io
import time

from django.db import connection
from django.conf import settings
SRID = settings.USE_SRID

############################## Detect Conflicts in Changesets ##############################

def build_dependency_tree(objects):
    # Step 1: Create a lookup for all objects by ID
    obj_map = {obj.id: {"id": obj.id, "pid": obj.pid, "parents": [d.id for d in list(obj.depends_on.all())], "children": []} for obj in objects}

    # Step 2: Build the tree by linking dependencies
    for obj in objects:
        current = obj_map[obj.id]
        depends_on_list = list(obj.depends_on.all())
        for dep in depends_on_list:
            parent = obj_map[dep.id]
            parent["children"].append(current)

    # Step 3: Helper to collect all descendant IDs of a node
    def collect_descendant_ids(node, visited=None):
        if visited is None:
            visited = set()
        for child in node["children"]:
            if child["id"] not in visited:
                visited.add(child["id"])
                collect_descendant_ids(child, visited)
        return visited

    # Step 4: Prune redundant children
    for node in obj_map.values():
        pruned_children = []
        all_other_descendants = {}

        # Precompute descendants of each child
        for child in node["children"]:
            all_other_descendants[child["id"]] = collect_descendant_ids(child)

        for child in node["children"]:
            # Check if this child is a descendant of any other child
            is_redundant = any(
                child["id"] in desc_ids
                for other_id, desc_ids in all_other_descendants.items()
                if other_id != child["id"]
            )
            if not is_redundant:
                pruned_children.append(child)

        node["children"] = pruned_children

    # Step 5: Prune non-roots
    roots_map = []
    for obj in obj_map:
        if len(obj_map[obj]["parents"]) == 0:
            roots_map.append(obj_map[obj])

    return obj_map, roots_map

def get_lineages_from_tree(roots_map):
    lineages = []

    def dfs(node, path):
        path.append(node["id"])
        if not node["children"]:
            # Leaf node: save the current path as a lineage
            lineages.append(path.copy())
        else:
            for child in node["children"]:
                dfs(child, path)
        path.pop()  # Backtrack

    # Start DFS from root nodes (nodes with no parents)
    for node in roots_map:
        if not node["parents"]:
            dfs(node, [])

    return lineages

def detect_conflicts(changesets):
    '''
    Detects three types of conflicts:
    1. Node-level conflicts: same node modified by changesets in different lineages.
    2. Link-level conflicts: same link modified by changesets in different lineages.
    3. Base network conflicts: all changesets must share the same base_network.
    '''

    def _collect_conflicts(obj_map, obj_type, cs_objects, lineages):
        conflicts = []
        for obj_id, cs_ids in obj_map.items():
            if len(cs_ids) <= 1:
                continue
            
            different_lineages_check = True
            for l in lineages:
                if set(cs_ids).issubset(set(l)):
                    different_lineages_check = False
                    break
            
            if different_lineages_check:
                conflicts.append({
                    "type": obj_type,
                    "id": obj_id,
                    "conflicting_changesets": [cs_objects[cs_id].pid for cs_id in cs_ids]
                })
        return conflicts

    # Step 2: Check for base network mismatches
    base_groups = {}
    for cs in changesets:
        base_id = str(cs.base_network_id) if cs.base_network_id else "None"
        base_groups.setdefault(base_id, []).append(str(cs.id))

    base_conflicts = []
    if len(base_groups) > 1:
        base_conflicts.append({
            "type": "base_network",
            "conflicting_changesets": list(base_groups.values())
        })

    # Step 3: Map node/link modifications to changesets
    node_map = {}
    link_map = {}
    for cs in changesets:
        for nv in NodeVersion.objects.filter(changeset=cs):
            node_map.setdefault(nv.node_id, set()).add(cs.id)
        for lv in LinkVersion.objects.filter(changeset=cs):
            link_map.setdefault(lv.link_id, set()).add(cs.id)

    # Step 4: Build dependency tree and lineages list
    _, roots_map = build_dependency_tree(changesets)
    lineages = get_lineages_from_tree(roots_map)

    # Step 5: Conflict collection
    cs_objects = {cs.id:cs for cs in changesets}
    node_conflicts = _collect_conflicts(node_map, "node", cs_objects, lineages)
    link_conflicts = _collect_conflicts(link_map, "link", cs_objects, lineages)

    return base_conflicts + node_conflicts + link_conflicts

def queryset_to_gdf(qs, geometry_field='geom_wkb', crs=f'EPSG:{SRID}'):
    t0 = time.time()
    df = pd.DataFrame(list(qs.values()))

    df["geometry"] = df[geometry_field].map(
        lambda x: wkb_loads(x.tobytes() if isinstance(x, memoryview) else x) if x else None
    )
    df.drop(columns=[geometry_field], inplace=True)

    if "attributes" in df.columns and not df["attributes"].isnull().all():
        attr_df = pd.json_normalize(df["attributes"])
        overlapping_cols = set(attr_df.columns) & set(df.columns)
        attr_df.drop(columns=overlapping_cols, inplace=True)
        df = pd.concat([df.drop(columns=["attributes"]), attr_df], axis=1)

    for col in df.columns:
        if df[col].dtype == object and df[col].apply(lambda x: isinstance(x, uuid.UUID)).any():
            df[col] = df[col].astype(str)
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%Y-%m-%dT%H:%M:%S')

    return gpd.GeoDataFrame(df, geometry="geometry", crs=crs)

def create_shapefile_zip_on_disk(nodes_gdf, links_gdf) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        node_path = os.path.join(tmpdir, "nodes")
        link_path = os.path.join(tmpdir, "links")

        nodes_gdf = nodes_gdf.reset_index(drop=True).copy()
        links_gdf = links_gdf.reset_index(drop=True).copy()

        nodes_gdf.to_file(node_path, driver="ESRI Shapefile", index=False, engine="pyogrio")
        links_gdf.to_file(link_path, driver="ESRI Shapefile", index=False, engine="pyogrio")

        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for folder in [node_path, link_path]:
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    arcname = filename
                    zf.write(filepath, arcname=arcname)

        mem_zip.seek(0)
        return mem_zip.read()

############################## Build Network from Changesets ##############################
def build_network_from_changesets(base_id, project_ids):
    changeset_ids = [base_id] + project_ids
    changeset_ids_sql = ",".join([str(i) for i in changeset_ids])

    nodes_sql = f"""
        WITH ranked_nodes AS (
            SELECT DISTINCT ON (node_id) *
            FROM network_nodeversion
            WHERE changeset_id IN ({changeset_ids_sql}) AND active = TRUE
            ORDER BY node_id, version DESC
        )
        SELECT id, node_id, geometry, attributes
        FROM ranked_nodes
    """

    links_sql = f"""
        WITH ranked_links AS (
            SELECT DISTINCT ON (link_id) *
            FROM network_linkversion
            WHERE changeset_id IN ({changeset_ids_sql}) AND active = TRUE
            ORDER BY link_id, version DESC
        )
        SELECT id, link_id, f_node_id, t_node_id, geometry, attributes
        FROM ranked_links
    """
    with connection.cursor():
        nodes_gdf = gpd.read_postgis(nodes_sql, connection.connection, geom_col='geometry')
        links_gdf = gpd.read_postgis(links_sql, connection.connection, geom_col='geometry')

    nodes_gdf.set_crs(epsg=SRID, inplace=True)
    links_gdf.set_crs(epsg=SRID, inplace=True)

    return nodes_gdf, links_gdf