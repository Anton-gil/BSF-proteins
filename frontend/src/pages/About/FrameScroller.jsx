import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';



export default function FrameScroller() {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  
  const [frames, setFrames] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [loadProgress, setLoadProgress] = useState(0);
  const [scrollProgress, setScrollProgress] = useState(0);

  const FRAME_COUNT = import.meta.env.VITE_FRAME_COUNT || 120;
  
  // Preload images
  useEffect(() => {
    let loadedCount = 0;
    const loadedImages = [];
    let isCancelled = false;

    // Simulate preloading with empty canvases or colored blocks if images don't exist
    // Because we might not have actual images in /frames/ yet
    const generateFallbackFrame = (index) => {
      const canvas = document.createElement('canvas');
      canvas.width = 1920;
      canvas.height = 1080;
      const ctx = canvas.getContext('2d');
      // Create interesting gradient/color based on index
      const hue = (index / FRAME_COUNT) * 60 + 80; // 80 to 140 (greenish)
      ctx.fillStyle = `hsl(${hue}, 80%, 15%)`;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Draw grid
      ctx.strokeStyle = `hsla(${hue}, 80%, 40%, 0.2)`;
      ctx.lineWidth = 2;
      for(let x=0; x<1920; x+=100) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,1080); ctx.stroke(); }
      for(let y=0; y<1080; y+=100) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(1920,y); ctx.stroke(); }
      
      ctx.fillStyle = `hsla(${hue}, 80%, 60%, 0.8)`;
      ctx.font = 'bold 120px "Space Grotesk"';
      ctx.textAlign = 'center';
      ctx.fillText(`FRAME ${index}`, 1920/2, 1080/2);
      
      return canvas;
    };

    const loadFrames = async () => {
      for (let i = 1; i <= FRAME_COUNT; i++) {
        if (isCancelled) break;
        
        try {
          // Attempt to load real image, fallback to generated canvas if it fails
          const img = new Image();
          const frameStr = String(i).padStart(3, '0');
          img.src = `/frames/ezgif-frame-${frameStr}.jpg`;
          
          await new Promise((resolve, reject) => {
            img.onload = () => resolve();
            img.onerror = () => {
              // Create fallback image when real image fails to load
              const fallback = generateFallbackFrame(i);
              const fallbackImg = new Image();
              fallbackImg.src = fallback.toDataURL();
              fallbackImg.onload = resolve;
              loadedImages[i-1] = fallbackImg;
            };
          });
          
          if (!loadedImages[i-1]) loadedImages[i-1] = img;
          
          loadedCount++;
          setLoadProgress((loadedCount / FRAME_COUNT) * 100);
        } catch (e) {
          console.error("Frame load error", e);
        }
      }
      
      if (!isCancelled) {
        setFrames(loadedImages);
        setLoaded(true);
      }
    };

    loadFrames();
    
    return () => { isCancelled = true; };
  }, [FRAME_COUNT]);

  // Scroll handler & draw
  useEffect(() => {
    if (!loaded || frames.length === 0) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    const renderFrame = (index) => {
      if (!frames[index]) return;
      const img = frames[index];
      
      // Calculate object-fit: cover equivalent for canvas
      const cw = canvas.width;
      const ch = canvas.height;
      const iw = img.width || 1920;
      const ih = img.height || 1080;
      
      const cratio = cw / ch;
      const iratio = iw / ih;
      
      let rw, rh, rx, ry;
      
      if (cratio > iratio) {
        rw = cw;
        rh = cw / iratio;
        rx = 0;
        ry = (ch - rh) / 2;
      } else {
        rh = ch;
        rw = ch * iratio;
        ry = 0;
        rx = (cw - rw) / 2;
      }
      
      ctx.clearRect(0, 0, cw, ch);
      ctx.drawImage(img, rx, ry, rw, rh);
    };

    const handleScroll = () => {
      if (!containerRef.current) return;
      
      // Calculation assumes window.scrollY is absolute, but usually components use relative.
      // So we use getBoundingClientRect on container
      const rect = containerRef.current.getBoundingClientRect();
      
      // Start pinning when top reaches 0
      const startPin = 0; 
      let progress = 0;
      
      if (rect.top <= startPin) {
        // Scrolled into container
        const totalScrollDistance = rect.height - window.innerHeight;
        const scrolledDistance = -rect.top + startPin;
        progress = Math.min(Math.max(scrolledDistance / totalScrollDistance, 0), 1);
      }
      
      setScrollProgress(progress);
      
      const frameIndex = Math.min(
        Math.floor(progress * (FRAME_COUNT - 1)),
        FRAME_COUNT - 1
      );
      
      requestAnimationFrame(() => renderFrame(frameIndex));
      

    };

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      handleScroll(); // re-render current frame
    };
    
    window.addEventListener('resize', resizeCanvas);
    window.addEventListener('scroll', handleScroll, { passive: true });
    
    // Initial setup
    resizeCanvas();
    
    return () => {
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('scroll', handleScroll);
    };
  }, [loaded, frames, FRAME_COUNT]);

  if (!loaded) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center pt-16">
        <h2 className="text-2xl font-display text-primary mb-6">Loading Sequence</h2>
        <div className="w-64 h-2 bg-surface-2 rounded-full overflow-hidden">
          <motion.div 
            className="h-full bg-primary"
            style={{ width: `${loadProgress}%` }}
          />
        </div>
        <p className="text-text-muted mt-4 text-sm font-mono">{Math.round(loadProgress)}% loaded</p>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef} 
      style={{ height: `${FRAME_COUNT * 12 + window.innerHeight}px` }} 
      className="relative w-full"
    >
      <div className="sticky top-0 w-full h-screen overflow-hidden">
        <canvas ref={canvasRef} className="w-full h-full block" />
        
        {/* Progress Bar (Top) */}
        <div className="absolute top-0 left-0 w-full h-1 bg-surface-2/50 z-10">
          <div 
            className="h-full bg-primary"
            style={{ width: `${scrollProgress * 100}%` }}
          />
        </div>

        {/* Hide Veo Watermark overlay */}
        <div className="absolute bottom-0 right-0 w-64 h-32 bg-[#050a05] z-10 blur-sm pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-48 h-24 bg-[#050a05] z-20 pointer-events-none" />

        {/* Text Overlay */}
        <div className="absolute top-12 left-0 w-full z-20 flex justify-center pointer-events-none">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: scrollProgress < 0.9 ? 1 : 0, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center"
          >
            <h3 className="text-4xl md:text-6xl font-display font-medium text-accent tracking-wide drop-shadow-lg opacity-90 uppercase">
              Life Cycle of Black Soldier Fly
            </h3>
          </motion.div>
        </div>

        {/* Smooth gradient blend to bottom content */ }
        <motion.div 
          className="absolute bottom-0 left-0 w-full h-[30vh] pointer-events-none z-30" 
          style={{ 
            background: 'linear-gradient(to top, #050a05 0%, transparent 100%)',
            opacity: Math.max(0, Math.min(1, (scrollProgress - 0.7) * 4)) // Fades in forcefully near the end 
          }}
        />
      </div>
    </div>
  );
}
