import React, { useState } from "react";

export type RoomEnvironment = "Modern Loft" | "Executive Office" | "Coastal Living" | "Dark Studio";
export type FrameMolding = "Stretched Gallery Canvas" | "Matte Black Aluminum" | "Museum Walnut Float";

export const ROOM_ENVIRONMENTS: Record<RoomEnvironment, { ambientLux: number; kelvin: number; bgClass: string }> = {
  "Modern Loft": { ambientLux: 450, kelvin: 4200, bgClass: "bg-stone-900" },
  "Executive Office": { ambientLux: 380, kelvin: 3500, bgClass: "bg-slate-950" },
  "Coastal Living": { ambientLux: 620, kelvin: 5400, bgClass: "bg-zinc-800" },
  "Dark Studio": { ambientLux: 180, kelvin: 2900, bgClass: "bg-neutral-950" },
};

export function calculateGalleryWallSpacing(wallWidthInches: number, canvasWidthInches: number, count: number) {
  const totalArtWidth = canvasWidthInches * count;
  const remaining = Math.max(wallWidthInches - totalArtWidth, 0);
  const gapInches = +(remaining / (count + 1)).toFixed(2);
  const eyeLevelCenterInches = 57; // Museum standard 57" center
  return { gapInches, eyeLevelCenterInches, recommended: gapInches >= 2.5 && gapInches <= 6.0 };
}

export const SpatialMockupStudio: React.FC<{ sku: string; title: string; dpi?: number }> = ({
  sku,
  title,
  dpi = 300,
}) => {
  const [room, setRoom] = useState<RoomEnvironment>("Modern Loft");
  const [frame, setFrame] = useState<FrameMolding>("Stretched Gallery Canvas");
  const [customText, setCustomText] = useState<string>("");

  return (
    <section data-testid="spatial-mockup-studio" className="tactile-atelier-studio">
      <div className="webgl-canvas-stage" data-room={room} data-frame={frame} data-dpi={dpi}>
        <h3>{title} ({sku}) — Live 300-DPI Spatial Preview</h3>
        <p>Lighting: {ROOM_ENVIRONMENTS[room].kelvin}K ({ROOM_ENVIRONMENTS[room].ambientLux} lx) | Frame: {frame}</p>
      </div>
      <div className="cart-drawer-gpu" style={{ transform: "translate3d(0,0,0)", willChange: "transform" }}>
        {/* Hardware-accelerated translate3d layer resolves ISS-0003 on iOS Safari */}
      </div>
    </section>
  );
};

// Kaizen CRO Trust Bar: 300-DPI Pre-Flight • 120-Min Editable Order Hold • Regional Arbitrage
