import React, { useState } from "react";

export default function UploadCubeLogModal({ isOpen, onClose, onSubmit }) {
  const [uploadFormat, setUploadFormat] = useState("cubelog");
  const [file, setFile] = useState(null);
  const [pid, setPid] = useState("");
  const [comment, setComment] = useState("");
  const [editor, setEditor] = useState("Cube");

  const handleSubmit = () => {
    if (file && comment && pid && editor) {
      console.log(comment, pid, editor);
      onSubmit({ 
        "format":uploadFormat,
        "file":file, 
        "pid":pid, 
        "comment":comment,
        "editor":editor
      });
      document.getElementById("getCubeLogFile").value = "";
      setFile(null);
      setPid("");
      setComment("");
      onClose();
    } else {
      alert("Please upload a file and enter all information requested.");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-xl shadow-xl">
        <h2 className="text-xl font-semibold mb-4">Create Changeset file from CUBE Log files</h2>
        <div className="text-sm mb-4">Multiple .log files are accepted.</div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Select File(s):</label>
          <input
            type="file"
            id="getCubeLogFile"
            multiple
            accept=".log"
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
