import React, { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import FeatureSidebar from "./FeatureSideBar";
import { useMapContext } from "../contexts/MapContext";
import { logout } from "../services/auth";

const basemaps = {
  carto: { id: "carto_light", name: "Carto Light", tiles: ["https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"], attribution: "©OpenStreetMap contributors ©CARTO" },
  stadia: { id: "stadia_light", name: "Stadia Smooth", tiles: ["https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}.png"], attribution: "©OpenStreetMap contributors, ©Stadia Maps" },
  osm: { id: "osm", name: "OSM Standard", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], attribution: "©OpenStreetMap contributors" },
  google_sat: { id: "google_sat", name: "Google Satellite", tiles: ["https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"], attribution: "" },
  google_road: { id: "google_road", name: "Google Road", tiles: ["https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"], attribution: "" },
  google_hybrid: { id: "google_hybrid", name: "Google (Sat+Rd)", tiles: ["https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"], attribution: "" },
  usgs: { id: "usgs", name: "USGS Satellite", tiles: ["https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"], attribution: "" },
};

const Map = () => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [selectedBasemap, setSelectedBasemap] = useState("carto");
  const [selectedFeatures, setSelectedFeatures] = useState([]);
  const { tileUrl, setZoom, editModeMinZoom, editMode } = useMapContext();

  const addBasemapLayer = (map, key) => {
    const config = basemaps[key];
    if (map.getSource("basemap")) {
      map.getSource("basemap").setTiles(config.tiles);
    } else {
      map.addSource("basemap", {
        type: "raster",
        tiles: config.tiles,
        tileSize: 256,
        attribution: config.attribution,
      });
      map.addLayer({ id: "basemap", type: "raster", source: "basemap" });
    }
  };

  useEffect(() => {
    if (mapInstanceRef.current) return;

    const map = new maplibregl.Map({
      container: mapRef.current,
      style: { version: 8, sources: {}, layers: [] },
      center: [-82.9988, 39.9612],
      zoom: 9,
      minZoom: 2,
      maxZoom: 19,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapInstanceRef.current = map;

    map.on("load", () => {
      addBasemapLayer(map, selectedBasemap);

      map.addSource("highlight_links", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "highlight_links_layer",
        type: "line",
        source: "highlight_links",
        paint: { "line-color": "#32CD32", "line-width": 5, "line-opacity": 0.8 },
      });

      map.addSource("highlight_nodes", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "highlight_nodes_layer",
        type: "circle",
        source: "highlight_nodes",
        paint: {
          "circle-radius": 7,
          "circle-color": "#32CD32",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#000",
        },
      });
    });

    map.on("zoom", () => setZoom(map.getZoom()));

    map.on("click", (e) => {
      const layersToQuery = [];
      if (map.getLayer("combined_nodes")) layersToQuery.push("combined_nodes");
      if (map.getLayer("combined_links")) layersToQuery.push("combined_links");
      if (layersToQuery.length === 0) return;

      const features = map.queryRenderedFeatures(e.point, { layers: layersToQuery });

      const nodeFeatures = features.filter(f => f.layer.id === "combined_nodes");
      const linkFeatures = features.filter(f => f.layer.id === "combined_links").slice(0, 2);

      if (nodeFeatures.length > 0) {
        setSelectedFeatures([nodeFeatures[0]]);
        map.getSource("highlight_nodes").setData({ type: "FeatureCollection", features: [nodeFeatures[0]] });
        map.getSource("highlight_links").setData({ type: "FeatureCollection", features: [] });
      } else if (linkFeatures.length > 0) {
        setSelectedFeatures(linkFeatures);
        map.getSource("highlight_links").setData({ type: "FeatureCollection", features: linkFeatures });
        map.getSource("highlight_nodes").setData({ type: "FeatureCollection", features: [] });
      } else {
        setSelectedFeatures([]);
        map.getSource("highlight_links").setData({ type: "FeatureCollection", features: [] });
        map.getSource("highlight_nodes").setData({ type: "FeatureCollection", features: [] });
      }
    });

    map.on("mousemove", (e) => {
      const layersToQuery = [];
      if (map.getLayer("combined_nodes")) layersToQuery.push("combined_nodes");
      if (map.getLayer("combined_links")) layersToQuery.push("combined_links");

      if (layersToQuery.length > 0) {
        const features = map.queryRenderedFeatures(e.point, { layers: layersToQuery });
        map.getCanvas().style.cursor = features.length ? "pointer" : "";
      } else {
        map.getCanvas().style.cursor = "";
      }
    });

    map.on('error', (e) => {
      if (e.error && (e.error.status === 401 || e.error.status === 403)) {
        logout();
      }
    });

    return () => map.remove();
  }, []);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (map && map.isStyleLoaded()) {
      addBasemapLayer(map, selectedBasemap);  // ✅ Enable dynamic basemap switching
    }
  }, [selectedBasemap]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !map.isStyleLoaded()) return;

    if (map.getLayer("combined_links")) map.removeLayer("combined_links");
    if (map.getLayer("combined_nodes")) map.removeLayer("combined_nodes");
    if (map.getSource("combined_network")) map.removeSource("combined_network");

    if (tileUrl?.combined) {
      map.addSource("combined_network", {
        type: "vector",
        tiles: [tileUrl.combined],
      });

      map.addLayer({
        id: "combined_links",
        type: "line",
        source: "combined_network",
        "source-layer": "links",
        paint: {
          "line-color": "#000088",
          "line-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            8, 0.5,
            19, 2.5,
          ],
        },
        filter: ["!=", "active", false],
      });

      map.addLayer({
        id: "combined_nodes",
        type: "circle",
        source: "combined_network",
        "source-layer": "nodes",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            12, 2.5,
            19, 6,
          ],
          "circle-color": "#FFD700",
          "circle-stroke-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            12, 1,
            19, 2,
          ],
          "circle-stroke-color": "#FF8000",
        },
        minzoom: 12,
        filter: ["!=", "active", false],
      });
    }
  }, [tileUrl]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (map) {
      map.setMinZoom(editMode ? editModeMinZoom : 2);
    }
  }, [editMode, editModeMinZoom]);

  return (
    <>
      <div className="absolute z-30 ml-2 mt-2 py-1 rounded-md px-2 font-base bg-white border border-[#e5e7eb] shadow-sm">
        <div className="flex">
          <p>🗺️</p>
          <select value={selectedBasemap} onChange={(e) => setSelectedBasemap(e.target.value)} className="bg-opacity-0">
            {Object.keys(basemaps).map((key) => (
              <option key={key} value={key}>{basemaps[key].name}</option>
            ))}
          </select>
        </div>
      </div>
      <div ref={mapRef} style={{ width: "100%", height: "100vh" }} />
      <FeatureSidebar features={selectedFeatures} onClose={() => setSelectedFeatures([])} />
    </>
  );
};

export default Map;
