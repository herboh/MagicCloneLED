import React, { useRef, useEffect, useState } from "react";

interface ColorWheelProps {
  size: number;
  value: string;
  onChange: (color: string) => void;
}

export const ColorWheel: React.FC<ColorWheelProps> = ({
  size,
  value,
  onChange,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const centerX = size / 2;
    const centerY = size / 2;
    const radius = size / 2 - 10;

    // Clear canvas
    ctx.clearRect(0, 0, size, size);

    // Draw color wheel
    for (let angle = 0; angle < 360; angle += 1) {
      const startAngle = ((angle - 1) * Math.PI) / 180;
      const endAngle = (angle * Math.PI) / 180;

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.lineWidth = 20;
      ctx.strokeStyle = `hsl(${angle}, 100%, 50%)`;
      ctx.stroke();
    }

    // Draw inner circle for brightness
    const gradient = ctx.createRadialGradient(
      centerX,
      centerY,
      0,
      centerX,
      centerY,
      radius - 20,
    );
    gradient.addColorStop(0, "white");
    gradient.addColorStop(1, "transparent");

    ctx.beginPath();
    ctx.arc(centerX, centerY, radius - 20, 0, 2 * Math.PI);
    ctx.fillStyle = gradient;
    ctx.fill();
  }, [size]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    handleColorSelection(e);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      handleColorSelection(e);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleColorSelection = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const centerX = size / 2;
    const centerY = size / 2;
    const x = e.clientX - rect.left - centerX;
    const y = e.clientY - rect.top - centerY;

    const angle = (Math.atan2(y, x) * 180) / Math.PI;
    const distance = Math.sqrt(x * x + y * y);
    const maxDistance = size / 2 - 10;

    if (distance <= maxDistance) {
      const hue = (angle + 360) % 360;
      const saturation = Math.min(100, (distance / maxDistance) * 100);
      const lightness = 50;

      const color = hslToHex(hue, saturation, lightness);
      onChange(color);
    }
  };

  const hslToHex = (h: number, s: number, l: number) => {
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
  };

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      className="cursor-pointer rounded-full"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    />
  );
};
