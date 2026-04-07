import { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

export default function ParticleField({ count = 2000 }) {
  const meshLayer = useRef();
  const { mouse, viewport } = useThree();

  const particles = useMemo(() => {
    const temp = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * 20;
      const y = (Math.random() - 0.5) * 20;
      const z = (Math.random() - 0.5) * 10;
      temp[i * 3] = x;
      temp[i * 3 + 1] = y;
      temp[i * 3 + 2] = z;
    }
    return temp;
  }, [count]);

  const materials = useMemo(() => {
    return new THREE.PointsMaterial({
      color: '#84cc16',
      size: 0.05,
      transparent: true,
      opacity: 0.4,
      blending: THREE.AdditiveBlending,
    });
  }, []);

  useFrame((state, delta) => {
    if (meshLayer.current) {
      meshLayer.current.rotation.y += delta * 0.05;
      meshLayer.current.rotation.x += delta * 0.02;
      
      // Subtle parallax mapped to mouse
      meshLayer.current.position.x = THREE.MathUtils.lerp(meshLayer.current.position.x, mouse.x * 0.5, 0.05);
      meshLayer.current.position.y = THREE.MathUtils.lerp(meshLayer.current.position.y, mouse.y * 0.5, 0.05);
    }
  });

  return (
    <points ref={meshLayer}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={particles.length / 3}
          array={particles}
          itemSize={3}
        />
      </bufferGeometry>
      <primitive object={materials} attach="material" />
    </points>
  );
}
