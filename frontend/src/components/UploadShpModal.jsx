import React, { useState } from "react";

export default function UploadShpModal({ isOpen, onClose, onSubmit }) {
  const [uploadFormat, setUploadFormat] = useState("shapefiles");
  const [file, setFile] = useState(null);
  const [pid, setPid] = useState("");
  const [comment, setComment] = useState("");
  const [editor, setEditor] = useState("");
  const [editorSpec, setEditorSpec] = useState("");

  const handleSubmit = () => {
    if (file && pid && (editor || editorSpec)) {
      console.log(comment, pid, editor, editorSpec);
      onSubmit({ 
        "format":uploadFormat,
        "file":file, 
        "pid":pid, 
        "comment":comment,
        "editor":editor,
        "editorSpec":editorSpec
      });
      // document.getElementById("getShpFile").value = "";
      // setFile(null);
      // setPid("");
      // setComment("");
      // setEditor("");
      // setEditorSpec("");
      // onClose();
    } else {
      alert("Please upload a file and enter all information requested.");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-xl shadow-xl">
        <h2 className="text-xl font-semibold mb-4">Create Changeset file from Shapefiles</h2>
        <div className="text-sm mb-4">Multiple .zip files are accepted. <br/> Each .zip file should contain shapefiles named with the partial words "node" and "link" (not case sensitive). <br/> <div className="mt-2 text-center">E.g., ✅ "nodes" or "NODES" ❌ "nod" or "NOD"</div></div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Select File:</label>
          <input
            type="file"
            id="getShpFile"
            // multiple
            accept=".zip"
            onChange={(e) => setFile(e.target.files)}
            required
            className="block w-full border rounded p-2"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">PID</label>
          <input
            type="text"
            value={pid}
            onChange={(e) => setPid(e.target.value)}
            required
            placeholder="Enter a PID code"
            className="w-full border rounded p-2"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Editor Used</label>
          <select onChange={(e) => setEditor(e.target.value)} className="w-full border rounded p-2">
            <option value="" disabled selected hidden>Choose an option</option>
            <option value="Cube">Bentley Cube</option>
            <option value="Transcad">Caliper TransCAD</option>
            <option value="Other">Other (Specify below)</option>
          </select>
        </div>

        {editor === "Other" && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1 ">*Specify which editor was used</label>
            <input
              type="text"
              value={editorSpec}
              onChange={(e) => setEditorSpec(e.target.value)}
              required
              placeholder="Enter an editor name"
              className="w-full border rounded p-2"
            />
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Comment</label>
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            required
            placeholder="Enter any comment"
            className="w-full border rounded p-2"
          />
        </div>

        <div className="flex justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-gray-200 hover:bg-gray-300 text-sm/6 font-semibold shadow-xs"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-700 text-sm/6 font-semibold text-white shadow-xs"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
}
