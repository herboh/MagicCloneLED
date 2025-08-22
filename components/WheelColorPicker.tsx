// components/WheelColorPicker.tsx
import { ArrowDown10 } from "lucide-react";
import React, { useRef, useEffect, useState, useCallback } from "react";

interface WheelColorPickerProps {
  value: string;
  brightness: number;
  isWarmWhite: boolean;
  onColorChange: (
    color: string,
    brightness: number,
    isWarmWhite: boolean,
  ) => void;
  onPowerToggle?: () => void;
  className?: string;
}

export const WheelColorPicker: React.FC<WheelColorPickerProps> = ({
  value,
  brightness,
  isWarmWhite,
  onColorChange,
  onPowerToggle,
  className = "",
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [currentHue, setCurrentHue] = useState(0);
  const [currentSaturation, setCurrentSaturation] = useState(100);

  const wheelSize = 300;
  const centerX = wheelSize / 2;
  const centerY = wheelSize / 2;
  const outerRadius = wheelSize / 2 - 6; // Reduced from 10 to 15 to bring border in slightly
  const innerRadius = outerRadius * 0.53; // Creates the donut shape

  // Predefined colors - display gruvbox colors but send original hex values
  const quickColors = [
    { name: "Red", hex: "#FF0000", displayColor: "#cc241d" },
    { name: "Blue", hex: "#0000FF", displayColor: "#458588" },
    { name: "Green", hex: "#00FF00", displayColor: "#98971a" },
    { name: "Purple", hex: "#8A2BE2", displayColor: "#b16286" },
    { name: "Orange", hex: "#FFA500", displayColor: "#d65d0e" },
  ];

  // Convert hex to HSL
  const hexToHsl = useCallback((hex: string): [number, number, number] => {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h = 0,
      s = 0,
      l = (max + min) / 2;

    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r:
          h = (g - b) / d + (g < b ? 6 : 0);
          break;
        case g:
          h = (b - r) / d + 2;
          break;
        case b:
          h = (r - g) / d + 4;
          break;
      }
      h /= 6;
    }

    return [h * 360, s * 100, l * 100];
  }, []);

  // Convert HSL to hex
  const hslToHex = useCallback((h: number, s: number, l: number): string => {
    l /= 100;
    const a = (s * Math.min(l, 1 - l)) / 100;
    const f = (n: number) => {
      const k = (n + h / 30) % 12;
      const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
      return Math.round(255 * color)
        .toString(16)
        .padStart(2, "0");
    };
    return `#${f(0)}${f(8)}${f(4)}`;
  }, []);

  // Update current hue and saturation when value changes
  useEffect(() => {
    if (!isWarmWhite && value) {
      const [h, s] = hexToHsl(value);
      setCurrentHue(h);
      setCurrentSaturation(s);
    }
  }, [value, isWarmWhite, hexToHsl]);

  // Draw the color wheel
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, wheelSize, wheelSize);

    // Draw color wheel (donut shape)
    const imageData = ctx.createImageData(wheelSize, wheelSize);
    const data = imageData.data;

    for (let x = 0; x < wheelSize; x++) {
      for (let y = 0; y < wheelSize; y++) {
        const dx = x - centerX;
        const dy = y - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Only draw if within the donut area
        if (distance >= innerRadius && distance <= outerRadius) {
          const angle = Math.atan2(dy, dx);
          const hue = ((angle * 180) / Math.PI + 360) % 360;
          const saturation =
            ((distance - innerRadius) / (outerRadius - innerRadius)) * 100;

          // Convert HSL to RGB
          const h = hue / 60;
          const s = saturation / 100;
          const l = 0.5;

          const c = (1 - Math.abs(2 * l - 1)) * s;
          const x_val = c * (1 - Math.abs((h % 2) - 1));
          const m = l - c / 2;

          let r = 0,
            g = 0,
            b = 0;

          if (h >= 0 && h < 1) {
            r = c;
            g = x_val;
            b = 0;
          } else if (h >= 1 && h < 2) {
            r = x_val;
            g = c;
            b = 0;
          } else if (h >= 2 && h < 3) {
            r = 0;
            g = c;
            b = x_val;
          } else if (h >= 3 && h < 4) {
            r = 0;
            g = x_val;
            b = c;
          } else if (h >= 4 && h < 5) {
            r = x_val;
            g = 0;
            b = c;
          } else if (h >= 5 && h < 6) {
            r = c;
            g = 0;
            b = x_val;
          }

          const pixelIndex = (y * wheelSize + x) * 4;
          data[pixelIndex] = Math.round((r + m) * 255); // Red
          data[pixelIndex + 1] = Math.round((g + m) * 255); // Green
          data[pixelIndex + 2] = Math.round((b + m) * 255); // Blue
          data[pixelIndex + 3] = 255; // Alpha
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);

    // Apply blur after drawing the color wheel
    ctx.drawImage(canvas, 0, 0);
    ctx.filter = "none"; // reset filter so it doesn’t affect later drawings

    // Draw border after blur
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

    // Draw selection indicator if not warm white
    if (!isWarmWhite) {
      const angle = (currentHue * Math.PI) / 180;
      const radius =
        innerRadius + (currentSaturation / 100) * (outerRadius - innerRadius);
      const indicatorX = centerX + radius * Math.cos(angle);
      const indicatorY = centerY + radius * Math.sin(angle);

      ctx.beginPath();
      ctx.arc(indicatorX, indicatorY, 10, 0, 2 * Math.PI);
      ctx.fillStyle = "white";
      ctx.fill();
      ctx.strokeStyle = "#333";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }, [currentHue, currentSaturation, isWarmWhite, innerRadius, outerRadius]);

  // Handle mouse/touch events
  const handlePointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    setIsDragging(true);
    handleColorSelection(e);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (isDragging) {
      handleColorSelection(e);
    }
  };

  const handlePointerUp = () => {
    setIsDragging(false);
  };

  const handleColorSelection = (e: React.PointerEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const dx = x - centerX;
    const dy = y - centerY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    let finalDistance = distance;
    let hue: number;
    let saturation: number;

    // Calculate the angle regardless of distance
    const angle = Math.atan2(dy, dx);
    hue = ((angle * 180) / Math.PI + 360) % 360;

    // If within the donut area, use actual distance
    if (distance >= innerRadius && distance <= outerRadius) {
      saturation =
        ((distance - innerRadius) / (outerRadius - innerRadius)) * 100;
    }
    // If outside the donut but dragging, clamp to the nearest edge
    else if (isDragging) {
      if (distance < innerRadius) {
        // Too close to center - snap to inner edge
        finalDistance = innerRadius;
        saturation = 0;
      } else {
        // Too far from center - snap to outer edge
        finalDistance = outerRadius;
        saturation = 100;
      }
    }
    // If not dragging and outside donut, don't update
    else {
      return;
    }

    setCurrentHue(hue);
    setCurrentSaturation(saturation);

    const newColor = hslToHex(hue, saturation, 50);
    onColorChange(newColor, brightness, false);
  };

  const handleWarmWhiteToggle = () => {
    onColorChange(value, brightness, !isWarmWhite);
  };

  const handleBrightnessChange = (newBrightness: number) => {
    onColorChange(value, newBrightness, isWarmWhite);
  };

  const handleQuickColorSelect = (hex: string) => {
    const [h, s] = hexToHsl(hex);
    setCurrentHue(h);
    setCurrentSaturation(s);
    onColorChange(hex, brightness, false);
  };

  return (
    <div
      className={`backdrop-blur-xl border rounded-3xl p-6 ${className} relative`}
      style={{
        backgroundColor: "#32302f",
        borderColor: "#504945",
      }}
    >
      {/* Power Toggle Button */}
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
            onPointerLeave={handlePointerUp}
            style={{
              touchAction: "none",
              imageRendering: "auto",
            }}
          />

          {/* Inner circle border to clean up the donut hole */}
          {/* <div */}
          {/*   className="absolute rounded-full border-2 pointer-events-none" */}
          {/*   style={{ */}
          {/*     width: `${innerRadius * 2}px`, */}
          {/*     height: `${innerRadius * 2}px`, */}
          {/*     top: "50%", */}
          {/*     left: "50%", */}
          {/*     transform: "translate(-50%, -50%)", */}
          {/*     borderColor: "#504945", */}
          {/*   }} */}
          {/* /> */}
          {/**/}
          {/* Warm White Button in Center */}
          <button
            onClick={handleWarmWhiteToggle}
            className="absolute top-1/2 left-1/2 w-24 h-24 rounded-full border-4 font-semibold text-sm"
            style={{
              transform: "translate(-50%, -50%)",
              transition:
                "background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease",
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
            backgroundColor: isWarmWhite ? "#FFF8DC" : value,
          }}
        />
        <div className="ml-3" style={{ color: "#ebdbb2" }}>
          <div className="font-mono text-sm">
            {isWarmWhite ? "Warm White" : value}
          </div>
          <div className="text-xs" style={{ color: "#a89984" }}>
            {brightness}% brightness
          </div>
        </div>
      </div>

      {/* Brightness Slider */}
      <div className="mb-6">
        <label
          className="block text-sm font-medium mb-3"
          style={{ color: "#8ec07c" }}
        >
          Brightness: {brightness}%
        </label>
        <div className="relative">
          <input
            type="range"
            min="1"
            max="100"
            value={brightness}
            onChange={(e) => handleBrightnessChange(parseInt(e.target.value))}
            className="w-full h-4 rounded-lg appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(to right, #1a1a1a 0%, ${isWarmWhite ? "#FFF8DC" : value} 100%)`,
            }}
          />
        </div>
      </div>

      {/* Quick Colors */}
      <div>
        <label
          className="block text-sm font-medium mb-3"
          style={{ color: "#8ec07c" }}
        >
          Quick Colors
        </label>
        <div className="flex justify-between gap-2">
          {quickColors.map((color) => (
            <button
              key={color.name}
              onClick={() => handleQuickColorSelect(color.hex)}
              className={`w-12 h-12 rounded-xl border-2 transition-all duration-200 hover:scale-110 ${
                value === color.hex && !isWarmWhite ? "shadow-lg" : ""
              }`}
              style={{
                backgroundColor: color.displayColor,
                borderColor:
                  value === color.hex && !isWarmWhite ? "#ebdbb2" : "#504945",
              }}
              title={color.name}
            />
          ))}
        </div>
      </div>

      <style jsx>{`
        input[type="range"] {
          -webkit-appearance: none;
          appearance: none;
        }
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: #ffffff;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
        }
        input[type="range"]::-moz-range-thumb {
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: #ffffff;
          cursor: pointer;
          border: none;
          box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
        }
      `}</style>
    </div>
  );
};
