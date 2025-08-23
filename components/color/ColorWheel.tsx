import React, {
  useRef,
  useEffect,
  useState,
  useCallback,
} from "react";
import { BrightnessSlider } from "./BrightnessSlider";
import { QuickColors } from "./QuickColors";

interface ColorWheelProps {
  h: number; // HSV Hue 0-360
  s: number; // HSV Saturation 0-100  
  v: number; // HSV Value 0-100
  brightness: number; // Overall brightness 0-100
  isWarmWhite: boolean;
  onColorChange: (h: number, s: number, v: number) => void;
  onBrightnessChange: (brightness: number) => void;
  onWarmWhiteToggle: () => void;
  onPowerToggle?: () => void;
  onSyncRequest?: () => void;
  className?: string;
}

export const ColorWheel: React.FC<ColorWheelProps> = ({
  h,
  s, 
  v,
  brightness,
  isWarmWhite,
  onColorChange,
  onBrightnessChange,
  onWarmWhiteToggle,
  onPowerToggle,
  onSyncRequest,
  className = "",
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isSync, setSyncing] = useState(false);

  const wheelSize = 300;
  const centerX = wheelSize / 2;
  const centerY = wheelSize / 2;
  const outerRadius = wheelSize / 2 - 6;
  const innerRadius = outerRadius * 0.53;


  // HSV to RGB conversion
  const hsvToRgb = useCallback((h: number, s: number, v: number): [number, number, number] => {
    h = h % 360;
    s = Math.max(0, Math.min(100, s)) / 100;
    v = Math.max(0, Math.min(100, v)) / 100;
    
    if (s === 0) {
      const gray = Math.round(v * 255);
      return [gray, gray, gray];
    }
    
    const hSector = h / 60;
    const sector = Math.floor(hSector);
    const f = hSector - sector;
    
    const p = v * (1 - s);
    const q = v * (1 - s * f);
    const t = v * (1 - s * (1 - f));
    
    let r, g, b;
    switch (sector) {
      case 0: r = v; g = t; b = p; break;
      case 1: r = q; g = v; b = p; break;
      case 2: r = p; g = v; b = t; break;
      case 3: r = p; g = q; b = v; break;
      case 4: r = t; g = p; b = v; break;
      default: r = v; g = p; b = q; break;
    }
    
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
  }, []);

  // Get current hex color
  const currentHex = useCallback(() => {
    if (isWarmWhite) return "#FFF8DC";
    const [r, g, b] = hsvToRgb(h, s, v);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase();
  }, [h, s, v, isWarmWhite, hsvToRgb]);

  // Draw the HSV color wheel
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, wheelSize, wheelSize);

    // Draw HSV color wheel
    const imageData = ctx.createImageData(wheelSize, wheelSize);
    const data = imageData.data;

    for (let x = 0; x < wheelSize; x++) {
      for (let y = 0; y < wheelSize; y++) {
        const dx = x - centerX;
        const dy = y - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance >= innerRadius && distance <= outerRadius) {
          // Convert to HSV coordinates
          const angle = Math.atan2(dy, dx);
          const hue = ((angle * 180) / Math.PI + 360) % 360;
          const saturation = ((distance - innerRadius) / (outerRadius - innerRadius)) * 100;
          
          // Use current V (value) from props for the wheel brightness
          const [r, g, b] = hsvToRgb(hue, saturation, v);
          
          const pixelIndex = (y * wheelSize + x) * 4;
          data[pixelIndex] = r;     // R
          data[pixelIndex + 1] = g; // G
          data[pixelIndex + 2] = b; // B
          data[pixelIndex + 3] = 255; // A
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);

    // Draw wheel borders
    ctx.beginPath();
    ctx.arc(centerX + 1, centerY + 1, outerRadius + 1.4, 0, 2 * Math.PI);
    ctx.strokeStyle = "#504945";
    ctx.lineWidth = 5;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(centerX + 1, centerY + 1, innerRadius + 1.4, 0, 2 * Math.PI);
    ctx.strokeStyle = "#504945";
    ctx.lineWidth = 5;
    ctx.stroke();

    // Draw selection dot
    if (!isWarmWhite) {
      const angle = (h * Math.PI) / 180;
      const radius = innerRadius + (s / 100) * (outerRadius - innerRadius);
      const dotX = centerX + radius * Math.cos(angle);
      const dotY = centerY + radius * Math.sin(angle);

      ctx.beginPath();
      ctx.arc(dotX, dotY, 10, 0, 2 * Math.PI);
      ctx.fillStyle = "white";
      ctx.fill();
      ctx.strokeStyle = "#333";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }, [h, s, v, isWarmWhite, hsvToRgb]);

  // Handle color wheel interaction
  const handleColorSelection = useCallback((e: React.PointerEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const dx = x - centerX;
    const dy = y - centerY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < innerRadius || distance > outerRadius) return;

    const angle = Math.atan2(dy, dx);
    const newH = ((angle * 180) / Math.PI + 360) % 360;
    const newS = ((distance - innerRadius) / (outerRadius - innerRadius)) * 100;

    onColorChange(Math.round(newH), Math.round(newS), v);
  }, [v, onColorChange]);

  // Pointer event handlers
  const handlePointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    setIsDragging(true);
    handleColorSelection(e);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (isDragging) {
      handleColorSelection(e);
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    setIsDragging(false);
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
  };

  // Handle sync button
  const handleSync = async () => {
    if (!onSyncRequest) return;
    setSyncing(true);
    try {
      await onSyncRequest();
    } finally {
      setTimeout(() => setSyncing(false), 1000);
    }
  };


  return (
    <div
      className={`backdrop-blur-xl border rounded-3xl p-6 ${className} relative`}
      style={{
        backgroundColor: "#32302f",
        borderColor: "#504945",
      }}
    >
      {/* Sync Button - Top Left */}
      {onSyncRequest && (
        <button
          onClick={handleSync}
          disabled={isSync}
          className="absolute top-4 left-4 z-10 w-10 h-10 rounded-full border
             flex items-center justify-center cursor-pointer transition-all duration-200
             bg-[#3c3836] border-[#504945] text-[#8ec07c]
             hover:bg-[#458588] hover:text-[#ebdbb2] disabled:opacity-50"
          title="Force Sync with Bulbs"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={isSync ? "animate-spin" : ""}
          >
            <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
            <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
            <path d="M3 21v-5h5" />
          </svg>
        </button>
      )}

      {/* Power Toggle Button - Top Right */}
      {onPowerToggle && (
        <button
          onClick={onPowerToggle}
          className="absolute top-4 right-4 z-10 w-10 h-10 rounded-full border
             flex items-center justify-center cursor-pointer transition-all duration-200
             bg-[#3c3836] border-[#504945] text-[#8ec07c]
             hover:bg-[#fb4934] hover:text-[#ebdbb2]"
          title="Toggle Power"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
            <line x1="12" y1="2" x2="12" y2="12" />
          </svg>
        </button>
      )}

      {/* Color Wheel */}
      <div className="relative mb-6 flex justify-center">
        <div className="relative">
          <canvas
            ref={canvasRef}
            width={wheelSize}
            height={wheelSize}
            className="cursor-pointer rounded-full"
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            style={{
              touchAction: "none",
              imageRendering: "auto",
            }}
          />

          {/* Warm White Button in Center */}
          <button
            onClick={onWarmWhiteToggle}
            className="absolute top-1/2 left-1/2 w-24 h-24 rounded-full border-4 font-semibold text-sm"
            style={{
              transform: "translate(-50%, -50%)",
              transition: "background-color 0.3s ease, border-color 0.3s ease",
              backgroundColor: isWarmWhite ? "#fabd2f" : "#3c3836",
              borderColor: isWarmWhite ? "#d79921" : "#504945",
              color: isWarmWhite ? "#1d2021" : "#ebdbb2",
            }}
          >
            Warm
            <br />
            White
          </button>
        </div>
      </div>

      {/* Current Color Display */}
      <div className="flex items-center justify-center mb-4">
        <div
          className="w-16 h-8 rounded-lg border-2 border-white/30 shadow-lg"
          style={{
            backgroundColor: currentHex(),
          }}
        />
        <div className="ml-3" style={{ color: "#ebdbb2" }}>
          <div className="font-mono text-sm">
            {isWarmWhite ? "Warm White" : currentHex()}
          </div>
          <div className="text-xs" style={{ color: "#a89984" }}>
            {brightness}% brightness
          </div>
        </div>
      </div>

      {/* Brightness Slider */}
      <BrightnessSlider
        brightness={brightness}
        currentColor={currentHex()}
        isWarmWhite={isWarmWhite}
        onBrightnessChange={onBrightnessChange}
        className="mb-6"
      />

      {/* Quick Colors */}
      <QuickColors
        currentH={h}
        currentS={s}
        isWarmWhite={isWarmWhite}
        onColorSelect={(newH, newS, newV) => onColorChange(newH, newS, newV)}
      />

    </div>
  );
};