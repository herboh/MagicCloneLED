// pages/index.tsx
import { useState, useEffect, useRef } from "react";
import Head from "next/head";
import { WheelColorPicker } from "../components/WheelColorPicker";

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

interface Group {
  [key: string]: string[];
}

interface Colors {
  [key: string]: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [bulbs, setBulbs] = useState<BulbStatus[]>([]);
  const [groups, setGroups] = useState<Group>({});
  const [colors, setColors] = useState<Colors>({});
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const [currentColor, setCurrentColor] = useState("#FF6B6B");
  const [brightness, setBrightness] = useState(100);
  const [isWarmWhite, setIsWarmWhite] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Connect to WebSocket
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(`${API_BASE.replace("http", "ws")}/ws`);

      ws.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connected");
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "initial_status") {
          setBulbs(data.data);
        } else if (data.type === "bulb_update") {
          setBulbs((prev) =>
            prev.map((bulb) =>
              bulb.name === data.data.name ? data.data : bulb,
            ),
          );
        } else if (data.type === "group_update") {
          setBulbs((prev) => {
            const updated = [...prev];
            data.data.forEach((updatedBulb: BulbStatus) => {
              const index = updated.findIndex(
                (b) => b.name === updatedBulb.name,
              );
              if (index !== -1) {
                updated[index] = updatedBulb;
              }
            });
            return updated;
          });
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setTimeout(connectWebSocket, 3000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();
    return () => wsRef.current?.close();
  }, []);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        const [groupsRes, colorsRes] = await Promise.all([
          fetch(`${API_BASE}/groups`),
          fetch(`${API_BASE}/colors`),
        ]);

        const groupsData = await groupsRes.json();
        const colorsData = await colorsRes.json();

        setGroups(groupsData.groups);
        setColors(colorsData.colors);
      } catch (error) {
        console.error("Failed to load data:", error);
      }
    };

    loadData();
  }, []);

  const sendCommand = async (action: string, params: any = {}) => {
    try {
      if (selectedTargets.length === 0) return;

      const isGroup =
        selectedTargets.length > 1 ||
        Object.keys(groups).includes(selectedTargets[0]);

      if (isGroup) {
        await fetch(`${API_BASE}/groups/command`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            targets: selectedTargets,
            action,
            ...params,
          }),
        });
      } else {
        await fetch(`${API_BASE}/bulbs/${selectedTargets[0]}/command`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action,
            ...params,
          }),
        });
      }
    } catch (error) {
      console.error("Command failed:", error);
    }
  };

  const toggleTarget = (target: string) => {
    setSelectedTargets((prev) =>
      prev.includes(target)
        ? prev.filter((t) => t !== target)
        : [...prev, target],
    );
  };

  const selectGroup = (groupName: string) => {
    setSelectedTargets([groupName]);
  };

  const handleColorPickerChange = (
    color: string,
    newBrightness: number,
    warmWhite: boolean,
  ) => {
    setCurrentColor(color);
    setBrightness(newBrightness);
    setIsWarmWhite(warmWhite);

    if (warmWhite) {
      sendCommand("warm_white", { warm_white: newBrightness });
    } else {
      sendCommand("color", { color, brightness: newBrightness });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <Head>
        <title>LED Controller</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="container mx-auto px-4 py-8 max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <div
              className="w-3 h-3 rounded-full mr-2 transition-colors duration-300"
              style={{ backgroundColor: isConnected ? "#10b981" : "#ef4444" }}
            />
            <h1 className="text-3xl font-bold text-white">LED Controller</h1>
          </div>
          <p className="text-white/70">Control your smart lights</p>
        </div>

        {/* Quick Groups */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-white mb-3">
            Quick Groups
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(groups).map(([groupName, bulbNames]) => (
              <button
                key={groupName}
                onClick={() => selectGroup(groupName)}
                className={`p-4 rounded-2xl border backdrop-blur-sm transition-all duration-200 ${
                  selectedTargets.includes(groupName)
                    ? "bg-blue-500/30 border-blue-400/50 shadow-lg shadow-blue-500/25"
                    : "bg-white/10 border-white/20 hover:bg-white/15"
                }`}
              >
                <div className="text-white font-medium text-sm capitalize">
                  {groupName}
                </div>
                <div className="text-white/60 text-xs mt-1">
                  {bulbNames.length} bulbs
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Individual Bulbs */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-white mb-3">
            Individual Bulbs
          </h2>
          <div className="space-y-3">
            {bulbs.map((bulb) => (
              <div
                key={bulb.name}
                onClick={() => toggleTarget(bulb.name)}
                className={`p-4 rounded-2xl border backdrop-blur-sm transition-all duration-200 cursor-pointer ${
                  selectedTargets.includes(bulb.name)
                    ? "bg-blue-500/30 border-blue-400/50 shadow-lg shadow-blue-500/25"
                    : "bg-white/10 border-white/20 hover:bg-white/15"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <div
                        className={`w-4 h-4 rounded-full border-2 transition-all duration-300 ${
                          bulb.online
                            ? bulb.on
                              ? "border-white/50 shadow-lg"
                              : "border-gray-400/50"
                            : "border-red-400/50"
                        }`}
                        style={{
                          backgroundColor:
                            bulb.online && bulb.on
                              ? bulb.color_hex
                              : "transparent",
                          boxShadow:
                            bulb.online && bulb.on
                              ? `0 0 20px ${bulb.color_hex}40`
                              : "none",
                        }}
                      />
                      {!bulb.online && (
                        <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />
                      )}
                    </div>
                    <div>
                      <div className="text-white font-medium capitalize">
                        {bulb.name}
                      </div>
                      <div className="text-white/60 text-sm">
                        {!bulb.online
                          ? "Offline"
                          : !bulb.on
                            ? "Off"
                            : `${bulb.brightness_percent}% • ${bulb.color_name}`}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Controls */}
        {selectedTargets.length > 0 && (
          <div className="space-y-6">
            {/* Power Controls */}
            <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6">
              <h3 className="text-white font-semibold mb-4">Power</h3>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => sendCommand("on")}
                  className="bg-green-500/30 hover:bg-green-500/40 border border-green-400/50 text-white font-medium py-3 px-4 rounded-xl transition-all duration-200 hover:scale-105"
                >
                  On
                </button>
                <button
                  onClick={() => sendCommand("off")}
                  className="bg-red-500/30 hover:bg-red-500/40 border border-red-400/50 text-white font-medium py-3 px-4 rounded-xl transition-all duration-200 hover:scale-105"
                >
                  Off
                </button>
                <button
                  onClick={() => sendCommand("toggle")}
                  className="bg-blue-500/30 hover:bg-blue-500/40 border border-blue-400/50 text-white font-medium py-3 px-4 rounded-xl transition-all duration-200 hover:scale-105"
                >
                  Toggle
                </button>
              </div>
            </div>

            {/* Color Control */}
            <WheelColorPicker
              value={currentColor}
              brightness={brightness}
              isWarmWhite={isWarmWhite}
              onColorChange={handleColorPickerChange}
            />
          </div>
        )}

        {selectedTargets.length === 0 && (
          <div className="text-center py-8">
            <div className="text-white/60 text-lg">
              Select bulbs or groups to control
            </div>
          </div>
        )}
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
          box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
        }
        input[type="range"]::-moz-range-thumb {
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: #ffffff;
          cursor: pointer;
          border: none;
          box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
        }
      `}</style>
    </div>
  );
}
