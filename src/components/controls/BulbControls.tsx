import React, { useState, useEffect, useRef, useCallback } from "react";
import { ColorWheel } from "../color/ColorWheel";
import { hsvToHex } from "../../lib/color";

interface BulbState {
  name: string;
  online: boolean;
  on: boolean;
  r: number;
  g: number;
  b: number;
  warm_white: number;
  h: number;
  s: number;
  v: number;
  hex: string;
  brightness: number;
  is_warm_white: boolean;
}

interface BulbControlsProps {
  className?: string;
}

// Environment-based API configuration
const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export const BulbControls: React.FC<BulbControlsProps> = ({
  className = "",
}) => {
  const [bulbs, setBulbs] = useState<BulbState[]>([]);
  const [groups, setGroups] = useState<{ [key: string]: string[] }>({});
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const [currentH, setCurrentH] = useState(0);
  const [currentS, setCurrentS] = useState(100);
  const [currentV, setCurrentV] = useState(100);
  const [brightness, setBrightness] = useState(100);
  const [isWarmWhite, setIsWarmWhite] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isUnmountingRef = useRef(false);

  // Helper function for consistent timestamps
  const getTimestamp = () => {
    const now = new Date();
    const ms = now.getMilliseconds().toString().padStart(3, '0');
    const time = now.toLocaleTimeString("en-US", { hour12: false });
    return `${time}.${ms}`;
  };

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      // Environment-based WebSocket URL configuration
      let wsUrl = import.meta.env.VITE_WS_URL;

      if (!wsUrl) {
        // Fallback: auto-detect protocol and use relative path (for container deployment)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${window.location.host}/ws`;
      }

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        console.log(`${getTimestamp()} | FRONTEND: WebSocket connected`);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(
          `${getTimestamp()} | FRONTEND: WebSocket received - ${JSON.stringify(data)}`,
        );

        if (data.type === "initial_state" || data.type === "initial_status") {
          setBulbs(data.data);
          console.log(
            `${getTimestamp()} | FRONTEND: Updated bulb states - ${data.data.length} bulbs`,
          );
        } else if (data.type === "bulb_update") {
          setBulbs((prev) =>
            prev.map((bulb) =>
              bulb.name === data.data.name ? data.data : bulb,
            ),
          );
          console.log(
            `${getTimestamp()} | FRONTEND: Updated bulb '${data.data.name}' state`,
          );
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log(
          `${getTimestamp()} | FRONTEND: WebSocket disconnected, retrying...`,
        );
        if (!isUnmountingRef.current) {
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
        }
      };

      ws.onerror = (error) => {
        console.log(`${getTimestamp()} | FRONTEND: WebSocket error - ${error}`);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      isUnmountingRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Load groups on mount
  useEffect(() => {
    const fetchGroups = async () => {
      try {
        const response = await fetch(`${API_BASE}/groups`);
        const data = await response.json();
        setGroups(data.groups);
      } catch (error) {
        console.error("Failed to load groups:", error);
      }
    };

    fetchGroups();
  }, []);

  // Update current color when selection changes
  useEffect(() => {
    if (selectedTargets.length === 1) {
      const bulb = bulbs.find((b) => b.name === selectedTargets[0]);
      if (bulb) {
        setCurrentH(bulb.h);
        setCurrentS(bulb.s);
        setCurrentV(bulb.v);
        setBrightness(bulb.brightness);
        setIsWarmWhite(bulb.is_warm_white);
      }
    } else if (selectedTargets.length === 0 && bulbs.length > 0) {
      // Auto-select first bulb
      setSelectedTargets([bulbs[0].name]);
    }
  }, [selectedTargets, bulbs]);

  // API call helper with debug logging
  const sendCommand = async (endpoint: string, command: any) => {
    const timestamp = getTimestamp();
    console.log(
      `${timestamp} | FRONTEND: POST ${endpoint} - ${JSON.stringify(command)}`,
    );

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(command),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.log(
          `${timestamp} | FRONTEND: Command failed - ${response.status}: ${errorText}`,
        );
      } else {
        const result = await response.json();
        console.log(
          `${timestamp} | FRONTEND: Command successful - ${JSON.stringify(result)}`,
        );
      }
    } catch (error) {
      console.log(`${timestamp} | FRONTEND: API error - ${error}`);
    }
  };

  // Debounced API call helper
  const debouncedSendCommand = useCallback(
    (() => {
      let timeoutId: NodeJS.Timeout | null = null;

      return (endpoint: string, command: any) => {
        if (timeoutId) {
          clearTimeout(timeoutId);
        }

        timeoutId = setTimeout(() => {
          sendCommand(endpoint, command);
        }, 200);
      };
    })(),
    [],
  );

  // Color change handler
  const handleColorChange = (h: number, s: number, v: number) => {
    setCurrentH(h);
    setCurrentS(s);
    setCurrentV(v);
    setIsWarmWhite(false);

    if (selectedTargets.length === 1) {
      debouncedSendCommand(`/bulbs/${selectedTargets[0]}/command`, {
        action: "hsv",
        h,
        s,
        v,
      });
    } else if (selectedTargets.length > 1) {
      debouncedSendCommand("/groups/command", {
        targets: selectedTargets,
        action: "hsv",
        h,
        s,
        v,
      });
    }
  };

  // Brightness change handler
  const handleBrightnessChange = (newBrightness: number) => {
    setBrightness(newBrightness);

    if (isWarmWhite) {
      if (selectedTargets.length === 1) {
        debouncedSendCommand(`/bulbs/${selectedTargets[0]}/command`, {
          action: "warm_white",
          brightness: newBrightness,
        });
      } else if (selectedTargets.length > 1) {
        debouncedSendCommand("/groups/command", {
          targets: selectedTargets,
          action: "warm_white",
          brightness: newBrightness,
        });
      }
    } else {
      // For RGB mode, adjust the V component and sync it
      const newV = newBrightness;
      setCurrentV(newV);
      handleColorChange(currentH, currentS, newV);
    }
  };

  // Warm white toggle
  const handleWarmWhiteToggle = () => {
    const newWarmWhite = !isWarmWhite;
    setIsWarmWhite(newWarmWhite);

    if (newWarmWhite) {
      if (selectedTargets.length === 1) {
        sendCommand(`/bulbs/${selectedTargets[0]}/command`, {
          action: "warm_white",
          brightness: brightness,
        });
      } else if (selectedTargets.length > 1) {
        sendCommand("/groups/command", {
          targets: selectedTargets,
          action: "warm_white",
          brightness: brightness,
        });
      }
    } else {
      handleColorChange(currentH, currentS, currentV);
    }
  };

  // Power toggle
  const handlePowerToggle = () => {
    if (selectedTargets.length === 1) {
      sendCommand(`/bulbs/${selectedTargets[0]}/command`, { action: "toggle" });
    } else if (selectedTargets.length > 1) {
      sendCommand("/groups/command", {
        targets: selectedTargets,
        action: "toggle",
      });
    }
  };

  // Sync request
  const handleSyncRequest = async () => {
    const timestamp = getTimestamp();
    console.log(`${timestamp} | FRONTEND: POST /bulbs/sync - force refresh`);

    try {
      const response = await fetch(`${API_BASE}/bulbs/sync`, {
        method: "POST",
      });
      const result = await response.json();
      console.log(
        `${timestamp} | FRONTEND: Sync completed - ${JSON.stringify(result)}`,
      );
    } catch (error) {
      console.log(`${timestamp} | FRONTEND: Sync failed - ${error}`);
    }
  };

  // Toggle target selection
  const toggleTarget = (target: string) => {
    setSelectedTargets((prev) =>
      prev.includes(target)
        ? prev.filter((t) => t !== target)
        : [...prev, target],
    );
  };

  // Select group
  const selectGroup = (groupName: string) => {
    if (groupName in groups) {
      setSelectedTargets(groups[groupName]);
    }
  };

  const areTargetsEqual = (left: string[], right: string[]) => {
    if (left.length !== right.length) {
      return false;
    }
    const leftSorted = [...left].sort();
    const rightSorted = [...right].sort();
    return leftSorted.every((value, index) => value === rightSorted[index]);
  };

  const currentColorHex = hsvToHex(currentH, currentS, currentV);
  const connectionStatus = isConnected ? "Connected" : "Disconnected";

  return (
    <div className={`max-w-4xl mx-auto p-6 ${className}`}>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2" style={{ color: "#ebdbb2" }}>
          LED Controller
        </h1>
        <div className="flex items-center gap-4">
          <div
            className={`text-sm px-3 py-1 rounded-full ${isConnected ? "bg-green-600" : "bg-red-600"}`}
          >
            {connectionStatus}
          </div>
          <div className="text-sm" style={{ color: "#a89984" }}>
            {selectedTargets.length} target
            {selectedTargets.length !== 1 ? "s" : ""} selected
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Color Controls */}
        <div className="space-y-6">
          <ColorWheel
            h={currentH}
            s={currentS}
            v={currentV}
            brightness={brightness}
            isWarmWhite={isWarmWhite}
            onColorChange={handleColorChange}
            onBrightnessChange={handleBrightnessChange}
            onWarmWhiteToggle={handleWarmWhiteToggle}
            onPowerToggle={handlePowerToggle}
            onSyncRequest={handleSyncRequest}
          />
        </div>

        {/* Right Column - Bulb & Group Selection */}
        <div className="space-y-6">
          {/* Quick Groups */}
          <div
            className="backdrop-blur-xl border rounded-3xl p-6"
            style={{ backgroundColor: "#32302f", borderColor: "#504945" }}
          >
            <h3
              className="text-lg font-semibold mb-4"
              style={{ color: "#8ec07c" }}
            >
              Groups
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {Object.keys(groups).map((groupName) => (
                <button
                  key={groupName}
                  onClick={() => selectGroup(groupName)}
                  className={`p-3 rounded-xl border transition-all duration-200 hover:scale-105 ${
                    areTargetsEqual(selectedTargets, groups[groupName])
                      ? "border-[#8ec07c] bg-[#8ec07c]/20"
                      : "border-[#504945] bg-[#3c3836]"
                  }`}
                  style={{ color: "#ebdbb2" }}
                >
                  {groupName}
                  <div className="text-xs mt-1" style={{ color: "#a89984" }}>
                    {groups[groupName].length} bulb
                    {groups[groupName].length !== 1 ? "s" : ""}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Individual Bulbs */}
          <div
            className="backdrop-blur-xl border rounded-3xl p-6"
            style={{ backgroundColor: "#32302f", borderColor: "#504945" }}
          >
            <h3
              className="text-lg font-semibold mb-4"
              style={{ color: "#8ec07c" }}
            >
              Bulbs
            </h3>
            <div className="space-y-2">
              {bulbs.map((bulb) => (
                <button
                  key={bulb.name}
                  onClick={() => toggleTarget(bulb.name)}
                  className={`w-full p-3 rounded-xl border transition-all duration-200 hover:scale-[1.02] ${
                    selectedTargets.includes(bulb.name)
                      ? "border-[#8ec07c] bg-[#8ec07c]/20"
                      : "border-[#504945] bg-[#3c3836]"
                  }`}
                  style={{ color: "#ebdbb2" }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-4 h-4 rounded-full border-2"
                        style={{
                          backgroundColor:
                            bulb.online && bulb.on
                              ? bulb.is_warm_white
                                ? "#FFF8DC"
                                : bulb.hex
                              : "#3c3836",
                          borderColor: bulb.online
                            ? bulb.on
                              ? "#8ec07c"
                              : "#a89984"
                            : "#fb4934",
                        }}
                      />
                      <span className="font-medium">{bulb.name}</span>
                    </div>
                    <div
                      className="text-right text-xs"
                      style={{ color: "#a89984" }}
                    >
                      {bulb.online
                        ? bulb.on
                          ? `${bulb.brightness}%`
                          : "OFF"
                        : "OFFLINE"}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
