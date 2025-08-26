import React from "react";

interface QuickColor {
  name: string;
  h: number;
  s: number;
  v: number;
  displayColor: string;
}

interface QuickColorsProps {
  currentH: number;
  currentS: number;
  isWarmWhite: boolean;
  onColorSelect: (h: number, s: number, v: number) => void;
  className?: string;
}

export const QuickColors: React.FC<QuickColorsProps> = ({
  currentH,
  currentS,
  isWarmWhite,
  onColorSelect,
  className = "",
}) => {
  // Predefined colors with gruvbox display colors
  const quickColors: QuickColor[] = [
    { name: "Red", h: 0, s: 100, v: 100, displayColor: "#cc241d" },
    { name: "Blue", h: 240, s: 100, v: 100, displayColor: "#458588" },
    { name: "Green", h: 120, s: 100, v: 100, displayColor: "#98971a" },
    { name: "Purple", h: 280, s: 100, v: 88, displayColor: "#b16286" },
    { name: "Orange", h: 39, s: 100, v: 100, displayColor: "#d65d0e" },
  ];

  const handleColorSelect = (color: QuickColor) => {
    onColorSelect(color.h, color.s, color.v);
  };

  const isColorSelected = (color: QuickColor): boolean => {
    return Math.abs(currentH - color.h) < 5 && currentS > 90 && !isWarmWhite;
  };

  return (
    <div className={className}>
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
            onClick={() => handleColorSelect(color)}
            className={`w-12 h-12 rounded-xl border-2 transition-all duration-200 hover:scale-110 ${
              isColorSelected(color) ? "shadow-lg" : ""
            }`}
            style={{
              backgroundColor: color.displayColor,
              borderColor: isColorSelected(color) ? "#ebdbb2" : "#504945",
            }}
            title={color.name}
          />
        ))}
      </div>
    </div>
  );
};