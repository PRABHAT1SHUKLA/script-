import React, { useEffect, useRef, useState } from 'react';

export default function CelestialCanvas() {
  const canvasRef = useRef(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);
  const particlesRef = useRef([]);
  const animationRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Initialize particles
    const initParticles = () => {
      particlesRef.current = Array.from({ length: 180 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        radius: Math.random() * 2 + 0.5,
        opacity: Math.random() * 0.5 + 0.3,
        color: `hsl(${Math.random() * 60 + 180}, 100%, ${Math.random() * 30 + 50}%)`,
        pulsePhase: Math.random() * Math.PI * 2,
      }));
    };

    initParticles();

    const animate = () => {
      // Clear with fade effect for trails
      ctx.fillStyle = 'rgba(5, 10, 25, 0.15)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw and update particles
      particlesRef.current.forEach((particle, i) => {
        // Physics
        particle.x += particle.vx;
        particle.y += particle.vy;

        // Bounce off edges
        if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;
        particle.x = Math.max(0, Math.min(canvas.width, particle.x));
        particle.y = Math.max(0, Math.min(canvas.height, particle.y));

        // Gravity towards mouse when hovering
        if (isHovering) {
          const dx = mousePos.x - particle.x;
          const dy = mousePos.y - particle.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          if (distance < 200) {
            const angle = Math.atan2(dy, dx);
            particle.vx += Math.cos(angle) * 0.3;
            particle.vy += Math.sin(angle) * 0.3;
          }
        }

        // Pulsing effect
        particle.pulsePhase += 0.02;
        const pulseFactor = Math.sin(particle.pulsePhase) * 0.4 + 0.8;
        const radius = particle.radius * pulseFactor;

        // Draw particle with glow
        const gradient = ctx.createRadialGradient(particle.x, particle.y, 0, particle.x, particle.y, radius * 3);
        gradient.addColorStop(0, particle.color.replace(')', ', 0.6)').replace('hsl', 'hsla'));
        gradient.addColorStop(1, particle.color.replace(')', ', 0)').replace('hsl', 'hsla'));
        
        ctx.fillStyle = gradient;
        ctx.fillRect(particle.x - radius * 3, particle.y - radius * 3, radius * 6, radius * 6);

        // Draw core
        ctx.fillStyle = particle.color;
        ctx.globalAlpha = particle.opacity * pulseFactor;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      });

      // Draw connections between nearby particles
      ctx.strokeStyle = 'rgba(100, 200, 255, 0.1)';
      ctx.lineWidth = 1;
      for (let i = 0; i < particlesRef.current.length; i++) {
        for (let j = i + 1; j < particlesRef.current.length; j++) {
          const p1 = particlesRef.current[i];
          const p2 = particlesRef.current[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          
          if (distance < 120) {
            ctx.globalAlpha = (1 - distance / 120) * 0.3;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }
      ctx.globalAlpha = 1;

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };

    const handleMouseEnter = () => setIsHovering(true);
    const handleMouseLeave = () => setIsHovering(false);

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseenter', handleMouseEnter);
    canvas.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseenter', handleMouseEnter);
      canvas.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationRef.current);
    };
  }, [isHovering, mousePos]);

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: 'linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #16213e 100%)', margin: 0, padding: 0 }}>
      <canvas
        ref={canvasRef}
        style={{ display: 'block', cursor: 'crosshair' }}
      />
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        textAlign: 'center',
        color: 'rgba(100, 200, 255, 0.8)',
        fontFamily: '"Courier New", monospace',
        fontSize: '24px',
        letterSpacing: '2px',
        pointerEvents: 'none',
        textShadow: '0 0 20px rgba(100, 200, 255, 0.5)',
      }}>
        <div style={{ marginBottom: '10px' }}>CELESTIAL CANVAS</div>
        <div style={{ fontSize: '12px', color: 'rgba(100, 200, 255, 0.6)' }}>
          Move your mouse to interact
        </div>
      </div>
    </div>
  );
}
