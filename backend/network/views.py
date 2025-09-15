############################## Libraries ##############################
from django.utils import timezone
from django.http import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import GEOSGeometry, Point, LineString
from django.contrib.auth import get_user_model
from django.db.models.functions import RowNumber
from django.db.models import F, Window
from django.db import connection
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Changeset, Node, NodeVersion, Link, LinkVersion
from .serializers import ChangesetSerializer, CustomUserSignupSerializer, UserProfileSerializer
from .utils.scripts import detect_conflicts, build_network_from_changesets, build_dependency_tree

import os
import io
import zipfile
import tempfile
import json
import numpy as np
import math
import geopandas as gpd
import pandas as pd
import warnings
warnings.filterwarnings('ignore')
import time
from shapely.geometry import mapping

SRID = settings.USE_SRID

############################## Classes ##############################

# USERS
class IsSuperUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser

class SignupView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = CustomUserSignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User created successfully'}, status=201)
        return Response(serializer.errors, status=400)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

# LIST CHANGESETS

class BaseNetworkChangesetsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # user_area = request.user.auth_area
        base_changesets = Changeset.objects.filter(is_base_network=True) # , auth_area=user_area
        serializer = ChangesetSerializer(base_changesets, many=True)
        return Response(serializer.data)

class ChangesetAncestryTreeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        base_id = request.data.get("base_network_id")
        if not base_id:
            return Response({"error": "Missing 'base_network_id'"}, status=status.HTTP_400_BAD_REQUEST)

        user_area = request.user.auth_area

        # Filter project changesets for this base and auth_area
        project_changesets = Changeset.objects.filter(
            base_network=base_id,
            is_base_network=False,
            auth_area=user_area
        )

        _, trees_by_root = build_dependency_tree(project_changesets)

        return Response({"trees": trees_by_root})

# UPLOAD CHANGES

class ToChangeFileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            t0=time.time()
            format = request.data.get("format")
            base_id = request.data.get("base_changeset_id")
            project_ids = request.data.get("project_changeset_ids")
            project_ids = json.loads(project_ids) if project_ids != 'empty' else []
            pid_inp = request.data.get("pid")
            editor_inp = request.data.get("editor")
            comment_inp = request.data.get("comment")
            files = request.data.get("files")
            # auth_area = request.user.auth_area

            all_changeset_ids = [base_id] + project_ids
            changeset_ids_sql = ",".join([str(i) for i in all_changeset_ids])
            print(f"Inputs: {time.time()-t0:.2f} seconds")

            if base_id and files:
                if format == "shapefiles":
                    uploaded_nodes, uploaded_links = load_nodes_and_links_from_zip(files)
                # elif format == "cubelog":
                #     uploaded_nodes, uploaded_links = load_nodes_and_links_from_cubelogs(files)
                else:
                    return Response({"error": f"format {format} not accepted. Try shapefiles."}, status=400)
            else:
                return Response({"error": "Missing required fields."}, status=400)

            # Check for duplicates
            if 'node_id' in uploaded_nodes.columns and 'link_id' in uploaded_links.columns:
                raise Exception("NOT ACTIVE")
                # duplicated_nodes = uploaded_nodes.duplicated(subset=['id'])
                # duplicated_links = uploaded_links.duplicated(subset=['id'])
                # list_of_duplicated_nodes = list(set(uploaded_nodes.loc[duplicated_nodes, 'id']) - set(['-1']))
                # list_of_duplicated_links = list(set(uploaded_links.loc[duplicated_links, 'id']) - set(['-1']))
            else:
                if "n" in uploaded_nodes.columns:
                    node_df = pd.read_sql(f"""
                                            SELECT node_id, attributes
                                            FROM network_nodeversion nv 
                                            WHERE nv.changeset_id IN ({changeset_ids_sql}) 
                                            """, 
                                            connection)
                    node_atts = node_df['attributes'].apply(json.loads).tolist()
                    node_atts_df = pd.DataFrame(node_atts)
                    node_atts_df.columns = [c.lower() for c in node_atts_df.columns]
                    node_id_map = dict(zip(node_atts_df['n'], node_df['node_id']))
                    uploaded_nodes['node_id'] = uploaded_nodes['n'].apply(lambda n: node_id_map[n] if n in node_id_map else -1)
                    
                    link_df = pd.read_sql(f"""
                                            SELECT link_id, attributes
                                            FROM network_linkversion lv 
                                            WHERE lv.changeset_id IN ({changeset_ids_sql}) 
                                            """, 
                                            connection)
                    link_atts = link_df['attributes'].apply(json.loads).tolist()
                    link_atts_df = pd.DataFrame(link_atts)
                    link_atts_df.columns = [c.lower() for c in link_atts_df.columns]
                    link_atts_df['ab'] = link_atts_df['a'].astype(str) + '_' + link_atts_df['b'].astype(str)
                    link_id_map = dict(zip(link_atts_df['ab'], link_df['link_id']))
                    uploaded_links['link_id'] = uploaded_links[['a','b']].apply(lambda r: link_id_map[f"{r.a}_{r.b}"] if f"{r.a}_{r.b}" in link_id_map else -1, axis=1)
                else:
                    raise Exception('Your shapefiles must either have id or N, A and B.')

            print(f"ID: {time.time()-t0:.2f} seconds")

            # Pull reference network
            sql_lv = f"""
            WITH latest_links AS (
                SELECT DISTINCT ON (link_id) *
                FROM network_linkversion lv
                WHERE lv.changeset_id IN ({changeset_ids_sql})
                ORDER BY link_id, version DESC
            )
            SELECT * FROM latest_links;
            """

            sql_nv = f"""
            WITH latest_nodes AS (
                SELECT DISTINCT ON (node_id) *
                FROM network_nodeversion nv
                WHERE nv.changeset_id IN ({changeset_ids_sql})
                ORDER BY node_id, version DESC
            )
            SELECT * FROM latest_nodes;
            """

            with connection.cursor():
                ref_links = gpd.read_postgis(sql_lv, connection.connection, geom_col='geometry')
                ref_nodes = gpd.read_postgis(sql_nv, connection.connection, geom_col='geometry')
            ref_links = expand_attributes(ref_links)
            ref_nodes = expand_attributes(ref_nodes)
            print(f"Ref: {time.time()-t0:.2f} seconds")

            # Ensure CRS match
            uploaded_nodes = uploaded_nodes.to_crs(ref_nodes.crs)
            uploaded_links = uploaded_links.to_crs(ref_links.crs)

            # Compare and collect changes
            node_changes = compare_gdf(ref_nodes, uploaded_nodes, 'node')
            link_changes = compare_gdf(ref_links, uploaded_links, 'link')

            # Group by pid
            grouped = {}
            for change in node_changes + link_changes:
                pid = change["data"].get("properties", {}).get("pid")
                if not pid:
                    pid = pid_inp
                    # return Response({"error": "No valid 'pid' found in features."}, status=400) # temporary
                grouped.setdefault(pid, []).append(change)

            if not grouped:
                return Response({"error": "No valid 'pid' found in features."}, status=400)
            print(f"Group: {time.time()-t0:.2f} seconds")

            # Create temp dir and zip file
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "netchange_files.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                    for pid, operations in grouped.items():
                        netchange = {
                            "changeset": {
                                "base_network": str(base_id),
                                "depends_on": [str(p) for p in project_ids],
                                "pid": pid_inp,
                                "comment": comment_inp,
                                "user": request.user.username,
                                "editor": editor_inp,
                                "create_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z%z"),
                            },
                            "operations": operations
                        }
                        safe_pid = str(pid).replace("/", "").replace("\\", "").replace(":", "").replace("-", "")
                        file_path = os.path.join(tmpdir, f"netchange_{safe_pid}.json")
                        with open(file_path, "w") as f:
                            json.dump(netchange, f, indent=2)
                        zipf.write(file_path, arcname=os.path.basename(file_path))
                        print(f"Zip pid: {time.time()-t0:.2f} seconds")
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
            mem_zip = io.BytesIO(zip_data)
            response = FileResponse(mem_zip, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="netchange_files.zip"'
            response['X-File-Count'] = str(len(grouped))
            print(f"Response: {time.time()-t0:.2f} seconds")
            return response

        except Exception as e:
            print({"error": str(e)})
            return Response({"error": str(e)}, status=500)

def load_nodes_and_links_from_zip(file):
    """Extracts both 'nodes.shp' and 'links.shp' from a single zip file and returns them as GeoDataFrames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(file) as archive:
            archive.extractall(tmpdir)

        def find_shp(contains_txt):
            for fname in os.listdir(tmpdir):
                if contains_txt in fname.lower() and fname.endswith(".shp"):
                    return os.path.join(tmpdir, fname)
            raise ValueError(f"{contains_txt} shp not found in archive.")

        nodes_path = find_shp("node")
        links_path = find_shp("link")

        gdf_nodes = gpd.read_file(nodes_path, engine='pyogrio')
        gdf_links = gpd.read_file(links_path, engine='pyogrio')

        gdf_nodes.columns = [c.lower() for c in gdf_nodes.columns]
        gdf_links.columns = [c.lower() for c in gdf_links.columns]

        return gdf_nodes, gdf_links
    
def expand_attributes(gdf):
    gdf = gdf.copy()
    gdf.columns = [c.lower() for c in gdf.columns]
    if "attributes" in gdf.columns and not gdf["attributes"].isnull().all():
        parsed_dicts = [json.loads(s) for s in gdf["attributes"]]
        attr_df = pd.DataFrame(parsed_dicts)
        attr_df.columns = [c.lower() for c in attr_df.columns]
        overlapping_cols = set(attr_df.columns) & set(gdf.columns)
        attr_df.drop(columns=overlapping_cols, inplace=True)
        gdf = pd.concat([gdf.drop(columns=["attributes"]), attr_df], axis=1)
    return gdf

def geometry_to_dict(geom):
    geo = mapping(geom)
    return {
        "type": geo["type"],
        "coordinates": geo["coordinates"]
    }

def compare_gdf(original, edited, element_type, ignore=['geometry','geometrysou','geometrysource','x','y','dist','changeset_id','created_at','node_id','active','version'], geom_tol=1e-2, attr_tol=1e-2):
    # Rows (ids)
    if element_type == "node":
        id_col = "node_id"
    elif element_type == "link":
        id_col = "link_id"
    else:
        raise Exception(f"Invalid element_type {element_type}. Use 'node' or 'link'.")

    original.columns = [c for c in original.columns]
    edited.columns = [c for c in edited.columns]

    original = original.set_index(id_col)
    edited = edited.set_index(id_col)
    changes = []

    orig_ids = set(original.index)
    edit_ids = set(edited.index)

    ## Compare ids
    created = edit_ids - orig_ids
    deleted = orig_ids - edit_ids
    possibly_modified = edit_ids & orig_ids
    
    # Cols (fields)
    ignore = set([c for c in ignore])
    cols1 = set([c for c in original.columns])
    cols2 = set([c for c in edited.columns])
    
    ## Compare cols
    cols_inter = (cols1 & cols2) - ignore # intersection
    
    # Same shape possibly-modified dfs
    orig_mod = original.loc[list(possibly_modified), list(cols_inter)]
    edit_mod = edited.loc[list(possibly_modified), list(cols_inter)]
    
    # Geometry columns
    orig_mod_geom = original.loc[list(possibly_modified), 'geometry']
    edit_mod_geom = edited.loc[list(possibly_modified), 'geometry']

    # Compare cols but geometry
    comp_nongeom = compare_dataframes_with_tolerance(orig_mod, edit_mod, rtol=attr_tol, atol=attr_tol)
    ids_modified_nongeom = edit_mod.index[comp_nongeom.sum(axis=1)>0]

    # Compare geometry
    comp_geom = orig_mod_geom.geom_equals_exact(edit_mod_geom, tolerance=geom_tol)
    ids_modified_geom = edit_mod.index[~comp_geom]

    # Final confirmed list of ids modified
    ids_modified = set(ids_modified_nongeom) | set(ids_modified_geom)

    # Rename columns back to full name (>10 chars)
    # edited.columns = [edit_cols_map[c] for c in edited.columns]

    for obj_id in created:
        rows = edited.loc[[obj_id]]
        for r in range(rows.shape[0]):
            row = rows.iloc[r]
            changes.append({
                "id": obj_id,
                "type": element_type,
                "action": "create",
                "data": {
                    "geometry": geometry_to_dict(row.geometry),
                    "properties": row.drop("geometry").dropna().to_dict()
                    }
            })

    for obj_id in deleted:
        changes.append({
            "id": obj_id,
            "type": element_type,
            "action": "delete",
            "data": {}
        })

    for obj_id in ids_modified:
        row = edited.loc[obj_id]
        changes.append({
            "id": obj_id,
            "type": element_type,
            "action": "modify",
            "data": {
                "geometry": geometry_to_dict(row.geometry),
                "properties": row.drop("geometry").dropna().to_dict()
                }
        })
    return changes

def compare_dataframes_with_tolerance(df1, df2, rtol=1e-5, atol=1e-8):
    """
    Compares two pandas DataFrames element-wise, considering tolerance for numerical columns.
    Returns a DataFrame of booleans indicating where values are not close.
    """
    if not df1.shape == df2.shape:
        raise ValueError("DataFrames must have the same shape for element-wise comparison.")

    # Convert to numeric where possible to enable tolerance comparison
    df1_numeric = df1.apply(pd.to_numeric, errors='coerce')
    df2_numeric = df2.apply(pd.to_numeric, errors='coerce')

    # Compare numeric columns with tolerance
    numeric_diff = ~np.isclose(df1_numeric, df2_numeric, rtol=rtol, atol=atol, equal_nan=True)
    numeric_diff = pd.DataFrame(numeric_diff, index=df1.index, columns=df1.columns)

    # For non-numeric columns, perform exact comparison
    non_numeric_cols = df1.select_dtypes(exclude=[np.number]).columns
    if not non_numeric_cols.empty:
        non_numeric_diff = (df1[non_numeric_cols].fillna("None") != df2[non_numeric_cols].fillna("None")).astype(bool)
        non_numeric_diff = pd.DataFrame(non_numeric_diff, index=df1.index, columns=non_numeric_cols)
        # Combine results, prioritizing non-numeric differences where applicable
        combined_diff = numeric_diff.combine_first(non_numeric_diff)
    else:
        combined_diff = numeric_diff

    return combined_diff

class BaseNetworkUploadView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        try:
            # format = request.data.get("format") # use this in future if other formats are accepted. only shp for now.
            pid = request.data.get("pid")
            editor = request.data.get("editor")
            comment = request.data.get("comment")
            uploaded_file = request.data.get("file")
            if not uploaded_file:
                return Response({"error": "No file uploaded"}, status=400)
            
            # Load node and link shapefiles
            gdf_nodes, gdf_links = load_nodes_and_links_from_zip(uploaded_file)
            
            # Keep only nodes that exist in both sets
            n_nodes = set(gdf_nodes['n'].values.tolist())
            gdf_links = gdf_links[gdf_links[['a','b']].isin(list(n_nodes)).sum(axis=1)>1]
            gdf_nodes = gdf_nodes.drop_duplicates(subset='n')

            # Validate geometries
            if not all(gdf_nodes.geometry.type == 'Point'):
                raise ValueError("Nodes shapefile must contain only Point geometries.")
            if not all(gdf_links.geometry.type == 'LineString'):
                raise ValueError("Links shapefile must contain only LineString geometries.")

            # Convert geometries
            gdf_nodes["geometry_json"] = gdf_nodes.geometry.map(mapping)
            gdf_links["geometry_json"] = gdf_links.geometry.map(mapping)

            # ✅ Passed all checks — proceed to create models
            base_changeset = Changeset.objects.create(
                user=request.user,
                comment=comment if comment.strip()!="" else "Uploaded base network via Shapefiles",
                pid=pid,
                editor=editor,
                is_base_network=True,
                auth_area="all"
            )
            base_changeset.base_network = base_changeset
            base_changeset.save()

            created_nodes = {}
            created_links = []

            # Create nodes
            for _,row in gdf_nodes.iterrows():
                geometry = GEOSGeometry(json.dumps(row["geometry_json"]))
                geometry.srid = SRID
                props = {k: v for k, v in row.items() if k not in ["geometry", "geometry_json"]}
                node = Node.objects.create()
                NodeVersion.objects.create(
                    node=node,
                    version=1,
                    geometry=geometry,
                    attributes=props,
                    changeset=base_changeset
                )
                created_nodes[str(row.n)] = node

            # Create links
            for _,row in gdf_links.iterrows():
                geometry = GEOSGeometry(json.dumps(row["geometry_json"]))
                geometry.srid = SRID
                props = {k: v for k, v in row.items() if k not in ["geometry", "geometry_json"]}
                link = Link.objects.create()
                LinkVersion.objects.create(
                    link=link,
                    version=1,
                    f_node=created_nodes[str(row.a)],
                    t_node=created_nodes[str(row.b)],
                    geometry=geometry,
                    attributes=props,
                    changeset=base_changeset
                )
                created_links.append(link)

            return Response({
                "status": "success",
                "changeset_id": str(base_changeset.id),
                "nodes_created": len(created_nodes),
                "links_created": len(created_links)
            }, status=201)

        except Exception as e:
            print({"error": str(e)})
            return Response({"error": str(e)}, status=500)

class NetChangeUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data if isinstance(request.data, dict) else json.loads(request.body)

            # Extract changeset metadata
            cs_data = data.get("changeset", {})
            base_network_id = cs_data.get("base_network")
            depends_on_ids = cs_data.get("depends_on", [])
            operations = data.get("operations", [])

            # Check input data
            if not base_network_id:
                return Response({"error": "base_network is required."}, status=400)
            
            # Force ids to be integers
            base_network_id = int(base_network_id)
            if depends_on_ids:
                depends_on_ids = [int(i) for i in depends_on_ids]

            base_network = get_object_or_404(Changeset, id=base_network_id)

            # Fetch project changesets only (exclude base network from conflict resolution)
            dependent_changesets = list(Changeset.objects.filter(id__in=depends_on_ids))

            conflicts = detect_conflicts(dependent_changesets)
            if conflicts:
                return Response({"error": "Conflicts detected", "conflicts": conflicts}, status=409)
            
            # changeset = Changeset.objects.get(id=15) # debug only
            # Create the new changeset
            changeset = Changeset.objects.create(
                user=request.user,
                comment=cs_data.get("comment", ""),
                pid=cs_data.get("pid", ""),
                editor=cs_data.get("editor", ""),
                created_at=timezone.now(),
                base_network=base_network,
                auth_area="all"
            )
            if dependent_changesets: # depends_on is ManyToManyField and should be assigned after changeset is created using "set()".
                changeset.depends_on.set(dependent_changesets)

            # Apply the operations
            op_nodes = self._handle_node(operations, changeset)
            NodeVersion.objects.bulk_create(op_nodes)
            nodeversion_by_n = pull_node_map(base_network_id, depends_on_ids + [changeset.id], request.user.auth_area)
            op_links = self._handle_link(operations, changeset, nodeversion_by_n)
            LinkVersion.objects.bulk_create(op_links)

            return Response({"status": "ok", "changeset_id": changeset.id}, status=201)

        except Exception as e:
            print({"error": str(e)})
            return Response({"error": str(e)}, status=500)

    def _handle_node(self, operations, changeset):
        # Cache nodes and latest versions to avoid repeated DB hits
        node_cache = {}
        latest_version_cache = {}

        def get_node_and_latest_version(node_id):
            if node_id not in node_cache:
                node = Node.objects.get(id=node_id)
                latest_version = NodeVersion.objects.filter(node=node).order_by('-version').first()
                node_cache[node_id] = node
                latest_version_cache[node_id] = latest_version
            return node_cache[node_id], latest_version_cache[node_id]

        op_nodes_create = [
            NodeVersion(
                node=Node.objects.create(),
                changeset=changeset,
                geometry=Point(op['data']['geometry']['coordinates'], srid=SRID),
                attributes={k.lower(): v for k, v in op['data']['properties'].items()},
                active=True,
                version=1
            )
            for op in operations if op['type'] == 'node' and op['action'] == 'create'
        ]

        op_nodes_mod = []
        op_nodes_del = []

        for op in operations:
            if op['type'] != 'node':
                continue

            if op['action'] in ('modify', 'delete'):
                node, latest_version = get_node_and_latest_version(op['id'])
                next_version = latest_version.version + 1

                geometry = (
                    Point(op['data']['geometry']['coordinates'], srid=SRID)
                    if op['action'] == 'modify' else latest_version.geometry
                )

                attributes = (
                    {k.lower(): v for k, v in op['data']['properties'].items()}
                    if op['action'] == 'modify' else latest_version.attributes
                )

                active = (op['action'] == 'modify')

                node_version = NodeVersion(
                    node=node,
                    changeset=changeset,
                    geometry=geometry,
                    attributes=attributes,
                    active=active,
                    version=next_version
                )

                if op['action'] == 'modify':
                    op_nodes_mod.append(node_version)
                else:
                    op_nodes_del.append(node_version)

        return op_nodes_create + op_nodes_mod + op_nodes_del

    def _handle_link(self, operations, changeset, nodeversion_by_n):
        # Cache links and latest versions to avoid repeated DB hits
        link_cache = {}
        latest_version_cache = {}

        def get_link_and_latest_version(link_id):
            if link_id not in link_cache:
                link = Link.objects.get(id=link_id)
                latest_version = LinkVersion.objects.filter(link=link).order_by('-version').first()
                link_cache[link_id] = link
                latest_version_cache[link_id] = latest_version
            return link_cache[link_id], latest_version_cache[link_id]

        def resolve_node(n_key):
            return nodeversion_by_n[n_key].node

        op_links_create = [
            LinkVersion(
                link=Link.objects.create(),#Link.objects.get(id=664501),#Link.objects.create(), # debug only
                changeset=changeset,
                geometry=LineString(op['data']['geometry']['coordinates'], srid=SRID),
                attributes={k.lower(): v for k, v in op['data']['properties'].items()},
                active=True,
                version=1,
                f_node=resolve_node(op['data']['properties']['a']),
                t_node=resolve_node(op['data']['properties']['b'])
            )
            for op in operations if op['type'] == 'link' and op['action'] == 'create'
        ]

        op_links_mod = []
        op_links_del = []

        for op in operations:
            if op['type'] != 'link':
                continue

            if op['action'] in ('modify', 'delete'):
                link, latest_version = get_link_and_latest_version(op['id'])
                next_version = latest_version.version + 1

                geometry = (
                    LineString(op['data']['geometry']['coordinates'], srid=SRID)
                    if op['action'] == 'modify' else latest_version.geometry
                )

                attributes = (
                    {k.lower(): v for k, v in op['data']['properties'].items()}
                    if op['action'] == 'modify' else latest_version.attributes
                )

                f_node = (
                    resolve_node(op['data']['properties']['a'])
                    if op['action'] == 'modify' else latest_version.f_node
                )

                t_node = (
                    resolve_node(op['data']['properties']['b'])
                    if op['action'] == 'modify' else latest_version.t_node
                )

                active = (op['action'] == 'modify')

                link_version = LinkVersion(
                    link=link,
                    changeset=changeset,
                    geometry=geometry,
                    attributes=attributes,
                    active=active,
                    version=next_version,
                    f_node=f_node,
                    t_node=t_node
                )

                if op['action'] == 'modify':
                    op_links_mod.append(link_version)
                else:
                    op_links_del.append(link_version)

        return op_links_create + op_links_mod + op_links_del

def pull_node_map(base, projects, auth_area):
    all_changeset_ids = [base] + projects

    annotated_qs = NodeVersion.objects.filter(
        changeset_id__in=all_changeset_ids,
        active=True
    ).annotate(
        row_number=Window(
            expression=RowNumber(),
            partition_by=[F('node_id')],
            order_by=F('version').desc()
        )
    ).filter(row_number=1)

    nodeversion_by_n = {}

    for nv in annotated_qs:
        try:
            n_value = nv.attributes.get("n")
            if n_value is not None:
                nodeversion_by_n[n_value] = nv
        except json.JSONDecodeError:
            print(f"skip {nv.id}")
            continue  # skip malformed entries

    return nodeversion_by_n

# TILES

def get_simplification_tolerance(z):
    if z < 8:
        return 500
    elif z < 10:
        return 50
    elif z < 12:
        return 50
    return 0  # full detail

def get_detail_level(z):
    if z >= 12:
        return {
            "nodes":"node_id, version, attributes, changeset_id, active",
            "links":"link_id, version, f_node_id, t_node_id, attributes, changeset_id, active"
            }
    elif z >= 10:
        return {
            "nodes":"node_id, version, changeset_id, active",
            "links":"link_id, version, f_node_id, t_node_id, changeset_id, active"
            }
    return {
            "nodes":"node_id, version, changeset_id, active",
            "links":"link_id, version, f_node_id, t_node_id, changeset_id, active"
            }

def tile_to_bounds(x, y, z):
    n = 2 ** z
    lon1 = x / n * 360.0 - 180.0
    lat1 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lon2 = (x + 1) / n * 360.0 - 180.0
    lat2 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return lon1, lat2, lon2, lat1  # west, south, east, north

def get_project_changeset_ids(request):
    return [str(i) for i in request.GET.getlist("project_changeset_ids[]") if i]

class QueryStringJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        token = request.GET.get('token')
        if token:
            validated_token = self.get_validated_token(token)
            return self.get_user(validated_token), validated_token
        return None

class ValidateTilesView(APIView):
    authentication_classes = [QueryStringJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.GET.get("token")
        if token:
            try:
                access = AccessToken(token)
                user_model = get_user_model()
                user = user_model.objects.get(id=access["user_id"])
                request.user = user
            except Exception:
                return JsonResponse({"valid":False, "error": "Token invalid"}, status=200)

        base_id = request.GET.get("base_changeset_id")
        project_ids = get_project_changeset_ids(request)

        if not base_id:
            return JsonResponse({"valid":False, "error": "Missing base_changeset_id"}, status=200)

        try:
            Changeset.objects.get(id=base_id, is_base_network=True)
        except Changeset.DoesNotExist:
            return JsonResponse({"valid":False, "error": "Invalid base_changeset_id"}, status=200)
        
        # Conflict checking
        dependent_changesets = list(Changeset.objects.filter(id__in=project_ids))

        conflicts = detect_conflicts(dependent_changesets)
        if conflicts:
            return JsonResponse({"valid":False, "error": f"Conflicts detected {conflicts}"}, status=200)
        
        return JsonResponse({"valid":True, "error": ""}, status=200)

class MVTNetworkTileView(APIView):
    authentication_classes = [QueryStringJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, z, x, y):
        token = request.GET.get("token")
        if token:
            try:
                access = AccessToken(token)
                user_model = get_user_model()
                user = user_model.objects.get(id=access["user_id"])
                request.user = user
            except Exception:
                return JsonResponse({"error": "Token invalid"}, status=400)

        base_id = request.GET.get("base_changeset_id")
        project_ids = get_project_changeset_ids(request)

        if not base_id:
            return JsonResponse({"error": "Missing base_changeset_id"}, status=400)

        try:
            Changeset.objects.get(id=base_id, is_base_network=True)
        except Changeset.DoesNotExist:
            return JsonResponse({"error": "Invalid base_changeset_id"}, status=400)
        
        # Conflict checking
        dependent_changesets = list(Changeset.objects.filter(id__in=project_ids))

        conflicts = detect_conflicts(dependent_changesets)
        if conflicts:
            return JsonResponse({"error": "Conflicts detected", "conflicts": conflicts}, status=409)

        all_changeset_ids = [base_id] + project_ids
        auth_area = request.user.auth_area
        detail_level = get_detail_level(int(z))

        # Columns by detail level
        node_cols = detail_level["nodes"]
        link_cols = detail_level["links"]

        # Simplification tolerance
        tolerance = get_simplification_tolerance(int(z))
        geom_sql = (
            f"ST_Transform(ST_SimplifyPreserveTopology(geometry, {tolerance}), 3857)"
            if tolerance > 0 else
            "ST_Transform(geometry, 3857)"
        )

        sql = f"""
        WITH tile_bounds AS (
            SELECT ST_TileEnvelope({z}, {x}, {y}) AS tile_3857
        ),
        geom_SRID_bounds AS (
            SELECT ST_Transform(tile_3857, {SRID}) AS bounds_SRID FROM tile_bounds
        ),
        latest_links AS (
            SELECT DISTINCT ON (link_id) *
            FROM network_linkversion lv
            WHERE lv.changeset_id IN %s
            AND ST_IsValid(lv.geometry)
            AND ST_SRID(lv.geometry) = {SRID}
            AND lv.geometry && (SELECT bounds_SRID FROM geom_SRID_bounds)
            AND (SELECT auth_area FROM network_changeset WHERE id = lv.changeset_id) = %s
            ORDER BY link_id, version DESC
        ),
        latest_nodes AS (
            SELECT DISTINCT ON (node_id) *
            FROM network_nodeversion nv
            WHERE nv.changeset_id IN %s
            AND ST_IsValid(nv.geometry)
            AND ST_SRID(nv.geometry) = {SRID}
            AND nv.geometry && (SELECT bounds_SRID FROM geom_SRID_bounds)
            AND (SELECT auth_area FROM network_changeset WHERE id = nv.changeset_id) = %s
            ORDER BY node_id, version DESC
        ),
        mvt_links AS (
            SELECT ST_AsMVTGeom(
                {geom_sql},
                (SELECT tile_3857 FROM tile_bounds),
                4096, 256, true
            ) AS geom,
            {link_cols}
            FROM latest_links
        ),
        mvt_nodes AS (
            SELECT ST_AsMVTGeom(
                {geom_sql.replace("geometry", "nv.geometry")},
                (SELECT tile_3857 FROM tile_bounds),
                4096, 256, true
            ) AS geom,
            {node_cols}
            FROM latest_nodes nv
        )
        SELECT (
            SELECT ST_AsMVT(q1, 'links', 4096, 'geom') FROM mvt_links q1
        ) || (
            SELECT ST_AsMVT(q2, 'nodes', 4096, 'geom') FROM mvt_nodes q2
        ) AS tile;
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, [tuple(all_changeset_ids), auth_area, tuple(all_changeset_ids), auth_area])
            row = cursor.fetchone()

        tile_data = row[0] if row else None
        if not tile_data:
            return HttpResponse(status=204)

        return HttpResponse(tile_data, content_type="application/vnd.mapbox-vector-tile")

# BUILD NETWORKS

class NetworkExportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        base_id = request.data.get("base_changeset_id")
        project_ids = request.data.get("project_changeset_ids")
        output_format = request.data.get("output_format")

        print(output_format)

        project_ids = [int(pid) for pid in project_ids]

        nodes_gdf, links_gdf = build_network_from_changesets(base_id, project_ids)

        if output_format == "shp":
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "network_shp.zip")

                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    if not nodes_gdf.empty:
                        nodes_path = os.path.join(tmpdir, "nodes.shp")
                        nodes_gdf.to_file(nodes_path)
                        for ext in [".shp", ".shx", ".dbf", ".prj"]:
                            zipf.write(nodes_path.replace(".shp", ext), f"nodes{ext}")

                    if not links_gdf.empty:
                        links_path = os.path.join(tmpdir, "links.shp")
                        links_gdf.to_file(links_path)
                        for ext in [".shp", ".shx", ".dbf", ".prj"]:
                            zipf.write(links_path.replace(".shp", ext), f"links{ext}")

                with open(zip_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=network_shp.zip'
                    return response
        elif output_format == "gdb":
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "network_gdb.zip")
                gdb_path = os.path.join(tmpdir, "network.gdb")

                if not nodes_gdf.empty:
                    nodes_gdf.to_file(gdb_path, layer="nodes", driver="OpenFileGDB")

                if not links_gdf.empty:
                    links_gdf.to_file(gdb_path, layer="links", driver="OpenFileGDB")

                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    # Recursively add the .gdb folder contents
                    for root, dirs, files in os.walk(gdb_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Keep relative path to preserve folder structure inside the zip
                            arcname = os.path.relpath(file_path, start=tmpdir)
                            zipf.write(file_path, arcname)

                with open(zip_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=network_gdb.zip'
                    return response
        else:
            return Response({"error": f"output_format '{output_format}' not supported. use 'shp' or 'gdb' only."}, status=400)
