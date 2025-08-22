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
  const statusUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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

  // Periodic status updates every 30 seconds
  useEffect(() => {
    const intervalId = setInterval(() => {
      updateBulbStatus();
    }, 30000);

    return () => {
      clearInterval(intervalId);
      if (statusUpdateTimeoutRef.current) {
        clearTimeout(statusUpdateTimeoutRef.current);
      }
    };
  }, [selectedTargets, groups, bulbs]);

  // Update status for selected bulbs
  const updateBulbStatus = async () => {
    try {
      if (selectedTargets.length === 0) return;

      // Get unique bulb names from selected targets
      const bulbNamesToUpdate = new Set<string>();
      
      selectedTargets.forEach(target => {
        if (target in groups) {
          // If it's a group, add all bulbs in the group
          groups[target].forEach(bulbName => bulbNamesToUpdate.add(bulbName));
        } else if (bulbs.some(b => b.name === target)) {
          // If it's an individual bulb
          bulbNamesToUpdate.add(target);
        }
      });

      // Fetch status for each bulb
      const statusPromises = Array.from(bulbNamesToUpdate).map(async (bulbName) => {
        try {
          const response = await fetch(`${API_BASE}/bulbs/${bulbName}`);
          if (response.ok) {
            return await response.json();
          }
        } catch (error) {
          console.error(`Failed to fetch status for ${bulbName}:`, error);
        }
        return null;
      });

      const statuses = await Promise.all(statusPromises);
      
      // Update bulbs state with fresh data
      setBulbs(prevBulbs => {
        const updatedBulbs = [...prevBulbs];
        statuses.forEach(status => {
          if (status) {
            const index = updatedBulbs.findIndex(b => b.name === status.name);
            if (index !== -1) {
              updatedBulbs[index] = status;
            }
          }
        });
        return updatedBulbs;
      });
    } catch (error) {
      console.error("Status update failed:", error);
    }
  };

  const sendCommand = async (action: string, params: any = {}) => {
    try {
      if (selectedTargets.length === 0) return;

      if (selectedTargets.length > 1) {
        // Multiple bulbs selected - use group command
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
        // Single bulb selected - use individual command
        await fetch(`${API_BASE}/bulbs/${selectedTargets[0]}/command`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action,
            ...params,
          }),
        });
      }

      // Schedule status update after command
      if (statusUpdateTimeoutRef.current) {
        clearTimeout(statusUpdateTimeoutRef.current);
      }
      statusUpdateTimeoutRef.current = setTimeout(updateBulbStatus, 1000);
    } catch (error) {
      console.error("Command failed:", error);
    }
  };

  const toggleTarget = (target: string) => {
    setSelectedTargets((prev) => {
      const newTargets = prev.includes(target)
        ? prev.filter((t) => t !== target)
        : [...prev, target];
      
      // Update colorwheel to reflect the state of the newly selected targets
      if (newTargets.length > 0) {
        // Find the first online and on bulb in the selection
        const selectedBulb = bulbs.find(b => 
          newTargets.includes(b.name) && b.online && b.on
        );
        
        if (selectedBulb) {
          setCurrentColor(selectedBulb.color_hex);
          setBrightness(selectedBulb.brightness_percent);
          setIsWarmWhite(selectedBulb.warm_white > 0);
        }
      }
      
      return newTargets;
    });
  };

  const selectGroup = (groupName: string) => {
    if (groupName in groups) {
      // Select all bulbs in the group instead of just the group name
      const bulbsInGroup = groups[groupName];
      setSelectedTargets(bulbsInGroup);
      
      // Update colorwheel to reflect the state of the first bulb in the group
      const firstBulb = bulbs.find(b => bulbsInGroup.includes(b.name));
      if (firstBulb && firstBulb.online && firstBulb.on) {
        setCurrentColor(firstBulb.color_hex);
        setBrightness(firstBulb.brightness_percent);
        setIsWarmWhite(firstBulb.warm_white > 0);
      }
    } else {
      setSelectedTargets([groupName]);
    }
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
    <div className="min-h-screen crt-monitor" style={{ background: '#1d2021' }}>
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
            <h1 className="text-3xl font-bold" style={{ color: '#b8bb26' }}>LED Controller</h1>
          </div>
          <p style={{ color: '#ebdbb2' }}>Control your smart lights</p>
        </div>

        {/* Color Control - Appears only when something is selected */}
        {selectedTargets.length > 0 && (
          <div className="mb-8 transition-all duration-300 ease-in-out">
            <WheelColorPicker
              value={currentColor}
              brightness={brightness}
              isWarmWhite={isWarmWhite}
              onColorChange={handleColorPickerChange}
              onPowerToggle={() => sendCommand("toggle")}
            />
          </div>
        )}

        {/* Quick Groups */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3" style={{ color: '#8ec07c' }}>
            Quick Groups
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(groups).map(([groupName, bulbNames]) => (
              <button
                key={groupName}
                onClick={() => selectGroup(groupName)}
                className="p-3 rounded-2xl border backdrop-blur-sm transition-all duration-200"
                style={{
                  backgroundColor: groupName in groups && groups[groupName].every(bulbName => selectedTargets.includes(bulbName))
                    ? '#3c3836'
                    : '#32302f',
                  borderColor: groupName in groups && groups[groupName].every(bulbName => selectedTargets.includes(bulbName))
                    ? '#d3869b'
                    : '#504945',
                  borderWidth: groupName in groups && groups[groupName].every(bulbName => selectedTargets.includes(bulbName))
                    ? '2px'
                    : '1px'
                }}
              >
                <div className="font-medium text-xs capitalize" style={{ color: '#ebdbb2' }}>
                  {groupName}
                </div>
                <div className="text-xs mt-1" style={{ color: '#a89984' }}>
                  {bulbNames.length} bulbs
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Individual Bulbs */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3" style={{ color: '#8ec07c' }}>
            Individual Bulbs
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {bulbs.map((bulb) => (
              <div
                key={bulb.name}
                onClick={() => toggleTarget(bulb.name)}
                className="p-4 rounded-2xl border backdrop-blur-sm transition-all duration-200 cursor-pointer"
                style={{
                  backgroundColor: selectedTargets.includes(bulb.name)
                    ? '#3c3836'
                    : '#32302f',
                  borderColor: selectedTargets.includes(bulb.name)
                    ? '#d3869b'
                    : '#504945',
                  borderWidth: selectedTargets.includes(bulb.name)
                    ? '2px'
                    : '1px'
                }}
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
                      <div className="font-medium capitalize text-sm" style={{ color: '#ebdbb2' }}>
                        {bulb.name}
                      </div>
                      <div className="text-xs" style={{ color: '#a89984' }}>
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

        {selectedTargets.length === 0 && (
          <div className="text-center py-8">
            <div className="text-lg" style={{ color: '#a89984' }}>
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
