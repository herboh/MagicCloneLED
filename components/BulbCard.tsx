import React from "react";

interface BulbStatus {
  name: string;
  online: boolean;
  on: boolean;
  red: number;
  green: number;
  blue: number;
  warm_white: number;
  brightness_percent: number;
  color_hex: string;
  color_name: string;
}

interface BulbCardProps {
  bulb: BulbStatus;
  isSelected: boolean;
  onClick: () => void;
}

export const BulbCard: React.FC<BulbCardProps> = ({
  bulb,
  isSelected,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-2xl border backdrop-blur-sm transition-all duration-300 cursor-pointer transform hover:scale-[1.02] ${
        isSelected
          ? "bg-blue-500/30 border-blue-400/50 shadow-lg shadow-blue-500/25 scale-[1.02]"
          : "bg-white/10 border-white/20 hover:bg-white/15"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div
              className={`w-6 h-6 rounded-full border-2 transition-all duration-300 ${
                bulb.online
                  ? bulb.on
                    ? "border-white/50 shadow-lg animate-pulse"
                    : "border-gray-400/50"
                  : "border-red-400/50"
              }`}
              style={{
                backgroundColor:
                  bulb.online && bulb.on ? bulb.color_hex : "transparent",
                boxShadow:
                  bulb.online && bulb.on
                    ? `0 0 20px ${bulb.color_hex}60, 0 0 40px ${bulb.color_hex}40`
                    : "none",
              }}
            />
            {!bulb.online && (
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse" />
            )}
          </div>
          <div>
            <div className="text-white font-medium capitalize text-lg">
              {bulb.name}
            </div>
            <div className="text-white/70 text-sm">
              {!bulb.online ? (
                <span className="text-red-400">Offline</span>
              ) : !bulb.on ? (
                <span className="text-gray-400">Off</span>
              ) : (
                <span>
                  {bulb.brightness_percent}% • {bulb.color_name}
                </span>
              )}
            </div>
          </div>
        </div>

        {bulb.online && bulb.on && (
          <div className="flex flex-col items-end">
            <div
              className="w-8 h-8 rounded-lg border border-white/30 shadow-lg"
              style={{ backgroundColor: bulb.color_hex }}
            />
            <div className="text-white/60 text-xs mt-1 font-mono">
              {bulb.color_hex}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
