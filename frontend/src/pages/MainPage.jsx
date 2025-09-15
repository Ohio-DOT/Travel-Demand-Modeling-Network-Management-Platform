import React, { useEffect, useState } from "react";
import api from "../services/api";
import Map from "../components/Map";
import { useMapContext } from "../contexts/MapContext";
import { ChevronRightIcon } from "@heroicons/react/20/solid";
import { logout } from "../services/auth";
import { useNavigate } from "react-router-dom";
import UploadShpModal from "../components/UploadShpModal";
import UploadChangeModal from "../components/UploadChangeModal";

const MainPage = () => {
  const [baseNetworks, setBaseNetworks] = useState([]);
  const [baseId, setBaseId] = useState("");
  const [tree, setTree] = useState([]);
  const [projectIds, setProjectIds] = useState(new Set());
  const [exporting, setExporting] = useState(false);
  const [buildError, setBuildError] = useState("");
  const [networkRendered, setNetworkRendered] = useState(false);
  const [showLoad, setShowLoad] = useState(true);
  const [showEdit, setShowEdit] = useState(true);
  const [showUpload, setShowUpload] = useState(true);

  const [showShpModal, setShowShpModal] = useState(false);
  const [showChangeModal, setShowChangeModal] = useState(false);

  const [openExportOptions, setOpenExportOptions] = useState(false);

  const [userProfile, setUserProfile] = useState({});

  const { setTileUrl, setProjectGeojson, zoom, editMode, setEditMode} = useMapContext();

  const navigate = useNavigate();

  // Set base network dropdown when page loads
  useEffect(() => {
    api.get("user-profile/").then((res) => {
      setUserProfile(res.data);
    });

    api.get("base-networks/").then((res) => {
      setBaseNetworks(res.data);
    });
  }, []); // this effect only runs once after initial render (empty array [])

  //  Update project changeset list
  const handleBaseNetworkChange = async (e) => {
    const selectedBaseId = e.target.value;
    setBaseId(selectedBaseId);
    setProjectIds(new Set());
    setTree([]);

    if (selectedBaseId === "") return;

    try {
      const res = await api.post("base-changesets/", { base_network_id: selectedBaseId });
      setTree(res.data.trees);
    } catch (err) {
      console.error("Tree fetching error:", err);
    }

    // Do not render tiles yet
    setTileUrl(null);
    setProjectGeojson(null);
    setNetworkRendered(false);
  };

  // Render combined base + project network as vector tiles
  const loadNetwork = () => {
    if (!baseId) return;

    const searchParams = new URLSearchParams();
    searchParams.append("base_changeset_id", baseId);
    Array.from(projectIds).forEach((csId) =>
      searchParams.append("project_changeset_ids[]", csId)
    );

    const token = localStorage.getItem("access_token");
    const urlTemplate = `http://localhost:8000/api/tiles/{z}/{x}/{y}.mvt?${searchParams.toString()}&token=${token}`;
    setTileUrl({ combined: urlTemplate });
    setProjectGeojson(null);
    setNetworkRendered(true);
  };

  // Render changeset tree
  const renderTree = (node) => (
    <div className="ml-4">
      <label className="">
        <input
          type="checkbox"
          checked={projectIds.has(node.id)}
          disabled={editMode}
          onChange={(e) => {
            const next = new Set(projectIds);
            e.target.checked ? next.add(node.id) : next.delete(node.id);
            setProjectIds(next);
          }}
        />
        {node.pid}
      </label>
      {node.children &&
        node.children.map((child) => (
          <React.Fragment key={child.id}>{renderTree(child)}</React.Fragment>
        ))}
    </div>
  );

  const editNetwork = () => {
    setEditMode(!editMode);    
  }

  // Build network 
  const buildNetwork = async (outputFormat = "shp") => {
    setExporting(true);
    setBuildError("");

    try {
        const res = await api.post(
            "network-export/",
            {
                base_changeset_id: baseId,
                project_changeset_ids: Array.from(projectIds),
                output_format: outputFormat
            },
            {
                responseType: "blob"
            }
        );

        const blob = new Blob([res.data], { type: "application/zip" });
        const downloadUrl = window.URL.createObjectURL(blob);

        const downloadLink = document.createElement("a");
        downloadLink.href = downloadUrl;
        downloadLink.download = `network_${outputFormat}.zip`;
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);

        window.URL.revokeObjectURL(downloadUrl);

    } catch (err) {
        console.error(err);
        setBuildError("Failed to build network");
    } finally {
        setExporting(false);
    }
  };

  const handleShpUpload = async (data) => {
    const formData = new FormData();
    formData.append("file", data.file);
    formData.append("base_changeset_id", baseId);
    formData.append("project_changeset_ids", projectIds.length > 0 ? [...projectIds] : "empty");
    formData.append("pid", data.pid)
    formData.append("comment", data.comment)
    formData.append("editor", data.editor !== "Other" ? data.editor : data.editorSpec)

    try {
      const response = await api.post("shp-to-netchange/", formData, {
        responseType: "blob",
      });

      // Create a blob URL and trigger download
      const blob = new Blob([response.data], { type: "application/zip" });
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = "network_changeset.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch {
      console.log("Upload or download failed.");
    }
  };

  const handleChangesetUpload = async (data) => {
    const file = data.file;
    const fileContent = await file.text()
    try {
      await api.post("netchange-upload/", fileContent, {
        headers: {
          "Content-Type": "application/json",
        },
      });
      console.log("Changeset upload successed.");
      setShowChangeModal(false)
    } catch {
      console.log("Changeset upload failed.");
    }
  };

  const handleLogout = () => {
    if (window.confirm("Confirm to logout.")) {
      logout();
      navigate('/login');
    }
  };

  return (
    <>
      {exporting && (
          <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50 h-screen w-screen">
            <div className="flex items-center justify-center bg-white rounded-xl p-6 w-full max-w-xl shadow-xl text-xl">
              <svg aria-hidden="true" className="w-6 h-6 text-gray-200 animate-spin dark:text-gray-600 fill-emerald-600 me-2" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
                  <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>
              </svg>
              Preparing network file...
            </div>
          </div>
        )}
      <div className="flex h-screen">
        <div className="min-w-72 bg-white border-r flex flex-col justify-between">
          <div>
            {/* Logo */}
            {/* <div className="p-4">
              <span className="text-emerald-600 text-3xl font-bold">〰️</span>
            </div> */}

            <p className="text-2xl text-center mt-6 mb-6">Network Manager</p>

            {/* Navigation */}
            <nav className="px-4 space-y-1">
              {/* Load Network */}
              <div>
                <button
                  onClick={() => setShowLoad(!showLoad)}
                  className="w-full mt-2 text-left text-gray-700 hover:text-emerald-600 font-medium flex justify-between items-center px-3 py-2 rounded-md cursor-default"
                >
                  <span>Load Network</span>
                  <ChevronRightIcon
                    className={`h-4 w-4 transition-transform ${showLoad ? "rotate-90" : ""}`}
                  />
                </button>
                {showLoad && (
                  <div className="ml-6 mt-2 space-y-1 text-sm text-gray-600">
                    <div>
                      <p className="mt-2 text-base">Select Base Network</p>
                      <select 
                        value={baseId} 
                        onChange={handleBaseNetworkChange} 
                        disabled={editMode}
                        className="mt-2 w-full mx-auto text-center rounded-md py-2 text-sm font-semibold text-emerald-800 outline outline-1 shadow-xs"
                      >
                        <option value="" disabled hidden>Select</option>
                        {baseNetworks.map((net) => (
                          <option key={net.id} value={net.id}>
                            {net.pid}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="overflow-y-auto max-h-[150px]">
                      <p className="mt-2 text-base">Select Projects by PID</p>
                      {(tree.length === 0 && baseId) && <p className="mt-2 mb-2 text-center text-yellow-600">No changesets found.</p>}
                      {tree.length > 0 && 
                        tree.map((root) => (
                          <React.Fragment key={root.id}>{renderTree(root)}</React.Fragment>
                        ))}
                    </div>
                    <button 
                      onClick={loadNetwork} 
                      disabled={!baseId || editMode} 
                      className={`flex w-full justify-center rounded-md px-3 py-2 text-sm font-semibold text-emerald-800 outline outline-1 shadow-xs ${baseId && !editMode ? 'hover:cursor-pointer hover:bg-emerald-600 hover:text-white' : 'bg-gray-300 hover:cursor-not-allowed'}`}
                    >
                      Load Network
                    </button>
                  </div>
                )}
              </div>

              {/* Edit & Export */}
              <div>
                <button
                  onClick={() => setShowEdit(!showEdit)}
                  className="w-full text-left text-gray-700 hover:text-emerald-600 font-medium flex justify-between items-center px-3 py-2 rounded-md cursor-default"
                >
                  <span>Edit & Export</span>
                  <ChevronRightIcon
                    className={`h-4 w-4 transition-transform ${showEdit ? "rotate-90" : ""}`}
                  />
                </button>
                {showEdit && (
                  <div className="ml-6 space-y-2 text-sm text-gray-600">
                    {/* Edit */}
                    <button onClick={editNetwork} disabled={!networkRendered || zoom<12} className={`flex w-full justify-center rounded-md ${networkRendered && zoom>=12 && !editMode ? 'hover:cursor-pointer hover:bg-emerald-600 hover:text-white' : editMode ? 'bg-orange-600 hover:cursor-pointer' : 'bg-gray-300 hover:cursor-not-allowed'} px-3 py-2 text-sm font-semibold ${!editMode ? 'text-emerald-800' : 'text-white'} outline outline-1 shadow-xs`}>
                      {!editMode ? "Edit" : "Stop Editing"}
                    </button>

                    {/* Export*/}
                    <div
                      className="relative group"
                      onMouseEnter={() => setOpenExportOptions(true)}
                      onMouseLeave={() => setOpenExportOptions(false)}
                    >
                      <button
                        disabled={!networkRendered || editMode}
                        className={`flex w-full justify-center rounded-md ${networkRendered && !editMode ? 'group-hover:cursor-pointer group-hover:bg-emerald-600 group-hover:text-white' : 'bg-gray-300 hover:cursor-not-allowed'} px-3 py-2 text-sm font-semibold text-emerald-800 outline outline-1 shadow-xs`}
                      >
                        Export As
                      </button>

                      {openExportOptions && networkRendered && !editMode && (
                        <div className="absolute top-0 left-full bg-white border rounded shadow-xl w-auto z-10">
                          <button
                            onClick={() => buildNetwork("shp")}
                            className="w-full block px-4 py-2 hover:bg-emerald-100 text-sm text-gray-700"
                          >
                            Shapefiles
                          </button>
                          <button
                            onClick={() => buildNetwork("shp")}
                            className="w-full block px-4 py-2 hover:bg-emerald-100 text-sm text-gray-700"
                          >
                            Geodatabase
                          </button>
                        </div>
                      )}

                    </div>

                    {/* Export SHP*/}
                    {/* <button onClick={() => buildNetwork("shp")} disabled={!networkRendered || editMode} className={`flex w-full justify-center rounded-md ${networkRendered && !editMode ? 'hover:cursor-pointer hover:bg-emerald-600 hover:text-white' : 'bg-gray-300 hover:cursor-not-allowed'} px-3 py-2 text-sm font-semibold text-emerald-800 outline outline-1 shadow-xs`}>
                      Export Shapefiles
                    </button>
                    {buildError && <p className="text-sm text-red-600">{buildError}</p>} */}
                    {/* Export GDB*/}
                    {/* <button onClick={() => buildNetwork("gdb")} disabled={!networkRendered || editMode} className={`flex w-full justify-center rounded-md ${networkRendered && !editMode ? 'hover:cursor-pointer hover:bg-emerald-600 hover:text-white' : 'bg-gray-300 hover:cursor-not-allowed'} px-3 py-2 text-sm font-semibold text-emerald-800 outline outline-1 shadow-xs`}>
                      Export Geodatabase
                    </button>
                    {buildError && <p className="text-sm text-red-600">{buildError}</p>} */}
                  </div>
                )}
              </div>

              {/* Upload Changes */}
              <div>
                <button
                  onClick={() => setShowUpload(!showUpload)}
                  className="w-full text-left text-gray-700 hover:text-emerald-600 font-medium flex justify-between items-center px-3 py-2 rounded-md cursor-default"
                >
                  <span>Upload Changes</span>
                  <ChevronRightIcon
                    className={`h-4 w-4 transition-transform ${showUpload ? "rotate-90" : ""}`}
                  />
                </button>
                {showUpload && (
                  <div className="ml-6 space-y-2 text-sm text-gray-600">
                    {/* Upload Shapefiles */}
                    <button
                      onClick={() => setShowShpModal(true)}
                      disabled={!networkRendered || editMode}
                      className={`flex w-full justify-center rounded-md ${networkRendered && !editMode ? 'hover:cursor-pointer hover:bg-emerald-600 hover:text-white' : 'bg-gray-300 hover:cursor-not-allowed'} px-3 py-2 text-sm font-semibold text-emerald-800 outline outline-1 shadow-xs`}
                    >
                      Shapefiles To Changeset
                    </button>
                    {/* Upload Changeset */}
                    <button
                      onClick={() => setShowChangeModal(true)}
                      disabled={editMode}
                      className={`flex w-full justify-center rounded-md ${!editMode ? 'hover:cursor-pointer hover:bg-emerald-600 hover:text-white' : 'bg-gray-300 hover:cursor-not-allowed '} px-3 py-2 text-sm font-semibold text-emerald-800 outline outline-1 shadow-xs`}
                    >
                      Import Changeset
                    </button>
                  </div>
                )}
              </div>


            </nav>
          </div>

          {/* User & Logout*/}
          <div className="py-3 border-t -mb-2 flex flex-col items-center">
            {zoom && <p id='zoom-level' className="text-sm text-center">{`Zoom: ${zoom.toFixed(2)}`}</p>}
            <p className="text-xs text-gray-500 mb-4">{"Edit mode is only available for Zoom >= 12"}</p>

            <div className="py-3 border-t flex flex-col items-center w-full">
              {/* <span className="text-sm text-gray-800">{`Username: ${userProfile.username}`}</span> */}
              <span className="text-sm text-gray-800">{`${userProfile.full_name}`}</span>
              <span className="text-sm text-gray-800">{`${userProfile.organization}`}</span>
              <span className="text-sm text-gray-800">{`${userProfile.email}`}</span>
              <button onClick={handleLogout} className="px-6 mt-2 mx-auto text-sm border border-gray-300 hover:text-red-600 hover:border-red-600">Logout</button>
            </div>
          </div>
          
        </div>

        <div className="flex-1">
            <Map />
        </div>

        {/* POPUP MODAL */}
        {/* UPLOAD SHAPEFILE MODAL */}
        <UploadShpModal
          isOpen={showShpModal}
          onClose={() => setShowShpModal(false)}
          onSubmit={handleShpUpload}
        />
        {/* UPLOAD CHANGESET MODAL */}
        <UploadChangeModal
          isOpen={showChangeModal}
          onClose={() => setShowChangeModal(false)}
          onSubmit={handleChangesetUpload}
        />
      </div>
    </>
  );
};

export default MainPage;
