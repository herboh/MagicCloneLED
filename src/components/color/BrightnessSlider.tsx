import React from "react";

interface BrightnessSliderProps {
  brightness: number;
  currentColor: string;
  isWarmWhite: boolean;
  onBrightnessChange: (brightness: number) => void;
  className?: string;
}

export const BrightnessSlider: React.FC<BrightnessSliderProps> = ({
  brightness,
  currentColor,
  isWarmWhite,
  onBrightnessChange,
  className = "",
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onBrightnessChange(parseInt(e.target.value));
  };

  const gradientColor = isWarmWhite ? "#FFF8DC" : currentColor;

  return (
    <div className={className}>
      <label
        className="block text-sm font-medium mb-3"
        style={{ color: "#8ec07c" }}
      >
        Brightness: {brightness}%
      </label>
      <div className="relative">
        <input
          type="range"
          min="0"
          max="100"
          value={brightness}
          onChange={handleChange}
          className="w-full h-4 rounded-lg appearance-none cursor-pointer brightness-slider"
          style={{
            background: `linear-gradient(to right, #1a1a1a 0%, ${gradientColor} 100%)`,
          }}
        />
      </div>
    </div>
  );
};
