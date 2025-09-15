export function drawFeaturePreviews(features) {
  features.forEach((feature, idx) => {
    const canvas = document.getElementById(`feature-preview-${idx}`);
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (feature.geometry.type === "LineString") {
      const coords = feature.geometry.coordinates;

      const [minX, minY, maxX, maxY] = coords.reduce(
        ([minX, minY, maxX, maxY], [x, y]) => [
          Math.min(minX, x),
          Math.min(minY, y),
          Math.max(maxX, x),
          Math.max(maxY, y)
        ],
        [Infinity, Infinity, -Infinity, -Infinity]
      );

      const scale = Math.min(
        canvas.width / (maxX - minX || 1),
        canvas.height / (maxY - minY || 1)
      ) * 0.8;

      const offsetX = (canvas.width - (maxX - minX) * scale) / 2;
      const offsetY = (canvas.height - (maxY - minY) * scale) / 2;

      ctx.beginPath();
      
      coords.forEach(([x, y], i) => {
        const px = offsetX + (x - minX) * scale;
        const py = offsetY + (maxY - y) * scale;
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      });
      ctx.strokeStyle = "#e11";
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 2]);
      ctx.stroke();

      // Draw arrowhead
      // Draw arrowhead using canvas-space coordinates
      if (coords.length >= 2) {
        const [x1, y1] = coords[coords.length - 2];
        const [x2, y2] = coords[coords.length - 1];

        const px1 = offsetX + (x1 - minX) * scale;
        const py1 = offsetY + (maxY - y1) * scale;
        const px2 = offsetX + (x2 - minX) * scale;
        const py2 = offsetY + (maxY - y2) * scale;

        const angle = Math.atan2(py2 - py1, px2 - px1); // ← use canvas Y-coordinates

        ctx.fillStyle = "#e11";
        ctx.beginPath();
        ctx.moveTo(px2, py2);
        ctx.lineTo(
          px2 - 10 * Math.cos(angle - 0.3),
          py2 - 10 * Math.sin(angle - 0.3)
        );
        ctx.lineTo(
          px2 - 10 * Math.cos(angle + 0.3),
          py2 - 10 * Math.sin(angle + 0.3)
        );
        ctx.closePath();
        ctx.fill();
      }

    }

    if (feature.geometry.type === "Point") {
      ctx.beginPath();
      ctx.arc(canvas.width / 2, canvas.height / 2, 10, 0, 2 * Math.PI);
      ctx.fillStyle = "#00996A";
      ctx.fill();
      ctx.strokeStyle = "#000";
      ctx.stroke();
    }
  });
}
