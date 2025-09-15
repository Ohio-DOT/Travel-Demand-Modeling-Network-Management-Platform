import React, { useEffect } from "react";
import { drawFeaturePreviews } from "./drawFeaturePreviews";

function estimateDirection(feature) {
  if (!feature?.geometry?.coordinates || feature.geometry.coordinates.length < 2) return null;
  const coords = feature.geometry.coordinates;
  const [x1, y1] = coords[coords.length - 2];
  const [x2, y2] = coords[coords.length - 1];
  const dx = x2 - x1;
  const dy = y2 - y1;
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
  if (angle >= -45 && angle < 45) return "EB";
  if (angle >= 45 && angle < 135) return "NB";
  if (angle >= -135 && angle < -45) return "SB";
  return "WB";
}

function sortFeaturesByDirection(features) {
  if (!features || features.length !== 2) return features;
  const [a, b] = features;
  const dirA = estimateDirection(a);
  return dirA === "SB" || dirA === "EB" ? [a, b] : [b, a];
}

export default function FeatureSidebar({ features, onClose }) {
  const sortedFeatures = sortFeaturesByDirection(features);

  useEffect(() => {
    if (!sortedFeatures || sortedFeatures.length === 0) return;
    requestAnimationFrame(() => drawFeaturePreviews(sortedFeatures));
  }, [sortedFeatures]);

  if (!sortedFeatures || sortedFeatures.length === 0) return null;

  const renderValue = (key, value) => {
    if (String(key).startsWith("__")) return null;
    return (
      <p key={key}>
        <strong>{key}:</strong> {String(value)}
      </p>
    );
  };

  return (
    <div>
      <div>
        <h3>Feature Details</h3>
        <div>
          <button onClick={onClose}>Close</button>
        </div>
      </div>

      <div>
        {sortedFeatures.map((f, i) => (
          <div key={i}>
            <div>
              <canvas height={100} width={200} id={`feature-preview-${i}`} />
            </div>
            <div>
              {Object.entries(f.properties).map(([key, value]) => renderValue(key, value))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
