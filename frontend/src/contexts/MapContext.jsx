import React, { createContext, useContext, useState } from "react";

const MapContext = createContext();

export const useMapContext = () => useContext(MapContext);

export const MapProvider = ({ children }) => {
  const [tileUrl, setTileUrl] = useState(null);
  const [projectGeojson, setProjectGeojson] = useState(null);
  const [zoom, setZoom] = useState(9);
  const [editModeMinZoom, setEditModeMinZoom] = useState(12);
  const [editMode, setEditMode] = useState(false);
  const [networkMeta, setNetworkMeta] = useState(null);

  return (
    <MapContext.Provider
      value={{ tileUrl, setTileUrl, 
        projectGeojson, setProjectGeojson, 
        zoom, setZoom, 
        editModeMinZoom, setEditModeMinZoom, 
        editMode, setEditMode, 
        networkMeta, setNetworkMeta }}
    >
      {children}
    </MapContext.Provider>
  );
};
