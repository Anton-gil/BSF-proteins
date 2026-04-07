import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export default function LarvaModel(props) {
  const group = useRef();
  
  // Create segments for the larva
  const segments = useMemo(() => {
    const count = 11;
    return Array.from({ length: count }, (_, i) => {
      // Tapering: Head is small, middle is thick, tail is tapered
      const t = i / (count - 1);
      const scale = Math.sin(t * Math.PI * 0.8 + 0.2) * 0.25 + 0.1;
      const xPos = (i - count / 2) * 0.22;
      return { id: i, position: [xPos, 0, 0], scale };
    });
  }, []);

  useFrame((state, delta) => {
    if (group.current) {
      // Drift the whole group
      group.current.rotation.y += delta * 0.2;
      group.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.5) * 0.1;
      
      // Animate individual segments for a crawling pulse effect
      group.current.children.forEach((child, i) => {
        const offset = i * 0.4;
        const pulse = Math.sin(state.clock.elapsedTime * 2 + offset) * 0.05 + 1;
        child.scale.set(pulse, pulse, pulse);
      });
    }
  });

  return (
    <group ref={group} {...props}>
      {segments.map((s) => (
        <mesh key={s.id} position={s.position}>
          <sphereGeometry args={[s.scale, 32, 32]} />
          <meshStandardMaterial 
            color="#84cc16" 
            emissive="#166534"
            emissiveIntensity={0.2}
            roughness={0.3}
            metalness={0.1}
          />
        </mesh>
      ))}
      
      {/* Decorative segments for texture/highlights */}
      <mesh position={[0, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
        <capsuleGeometry args={[0.15, 2.2, 4, 8]} />
        <meshStandardMaterial color="#84cc16" transparent opacity={0.1} wireframe />
      </mesh>
    </group>
  );
}
