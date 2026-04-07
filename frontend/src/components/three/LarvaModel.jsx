import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';

export default function LarvaModel(props) {
  const mesh = useRef();

  useFrame((state, delta) => {
    if (mesh.current) {
      mesh.current.rotation.x += delta * 0.2;
      mesh.current.rotation.y += delta * 0.3;
    }
  });

  return (
    <mesh ref={mesh} {...props}>
      <capsuleGeometry args={[0.2, 1, 4, 8]} />
      <meshStandardMaterial color="#84cc16" wireframe />
    </mesh>
  );
}
