'use client';

import { useEffect, useRef } from 'react';
import Image from 'next/image';
import { createMotionLoop } from './motion-loop';

export default function EarthScene({
  paused,
  active = true,
  closeUp = false,
}: {
  paused: boolean;
  active?: boolean;
  closeUp?: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  const stopped = useRef(paused);
  const visible = useRef(active);
  const refresh = useRef(() => {});
  useEffect(() => {
    stopped.current = paused;
    visible.current = active;
    refresh.current();
  }, [paused, active]);
  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let cancelled = false;
    let dispose = () => {};
    void Promise.all([
      import('three'),
      import('three/addons/geometries/RoundedBoxGeometry.js'),
    ])
      .then(([T, { RoundedBoxGeometry }]) => {
        if (cancelled) return;
        let renderer: InstanceType<typeof T.WebGLRenderer>;
        try {
          renderer = new T.WebGLRenderer({
            alpha: true,
            antialias: true,
            powerPreference: 'low-power',
          });
        } catch {
          return;
        }
        renderer.outputColorSpace = T.SRGBColorSpace;
        renderer.toneMapping = T.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.05;
        element.appendChild(renderer.domElement);
        const scene = new T.Scene();
        const camera = new T.PerspectiveCamera(39, 1, 0.1, 30);
        // Keep the cinematic framing on every resize; motion never zooms out.
        camera.zoom = closeUp ? 1.72 : 1;
        camera.position.set(0, 1.1, 8.6);
        camera.lookAt(0, 0, 0);
        const world = new T.Group();
        scene.add(world);
        const globeTilt = new T.Group();
        globeTilt.rotation.z = 0.16;
        world.add(globeTilt);
        const vertexShader = `
        varying vec2 vUv;
        varying vec3 vWorldNormal;
        varying vec3 vWorldPosition;
        void main() {
          vUv = uv;
          vWorldNormal = normalize(mat3(modelMatrix) * normal);
          vec4 worldPosition = modelMatrix * vec4(position, 1.0);
          vWorldPosition = worldPosition.xyz;
          gl_Position = projectionMatrix * viewMatrix * worldPosition;
        }
      `;
        const sunDirection = new T.Vector3(0.9, 0.3, -0.48).normalize();
        const surface = new T.ShaderMaterial({
          uniforms: {
            dayMap: { value: null },
            nightMap: { value: null },
            sunDirection: { value: sunDirection },
          },
          vertexShader,
          fragmentShader: `
          uniform sampler2D dayMap;
          uniform sampler2D nightMap;
          uniform vec3 sunDirection;
          varying vec2 vUv;
          varying vec3 vWorldNormal;
          varying vec3 vWorldPosition;
          void main() {
            vec3 n = normalize(vWorldNormal);
            vec3 eye = normalize(cameraPosition - vWorldPosition);
            float solar = dot(n, sunDirection);
            float daylight = max(solar, 0.0);
            float night = 1.0 - smoothstep(-.18, .24, solar);
            vec3 land = texture2D(dayMap, vUv).rgb;
            float grey = dot(land, vec3(.2126, .7152, .0722));
            vec3 restrainedLand = mix(vec3(grey), land, .38);
            vec3 color = restrainedLand * (.009 + daylight * .36);
            vec3 lights = texture2D(nightMap, vUv).rgb;
            float cityMask = smoothstep(.006, .065, max(lights.r - lights.b * .75, 0.0));
            color += lights * vec3(1.15, 1.04, .84) * cityMask * night * 1.35;
            float rim = pow(1.0 - max(dot(n, eye), 0.0), 4.5);
            color += vec3(.065, .105, .15) * rim * smoothstep(-.4, .4, solar) * .55;
            gl_FragColor = vec4(color, 1.0);
            #include <tonemapping_fragment>
            #include <colorspace_fragment>
          }
        `,
        });
        const globe = new T.Mesh(new T.SphereGeometry(1.62, 112, 72), surface);
        globe.rotation.y = 0.08;
        globeTilt.add(globe);
        const cloudMaterial = new T.ShaderMaterial({
          uniforms: {
            cloudMap: { value: null },
            sunDirection: { value: sunDirection },
          },
          vertexShader,
          transparent: true,
          depthWrite: false,
          fragmentShader: `
          uniform sampler2D cloudMap;
          uniform vec3 sunDirection;
          varying vec2 vUv;
          varying vec3 vWorldNormal;
          varying vec3 vWorldPosition;
          void main() {
            float cloud = texture2D(cloudMap, vUv).r;
            float solar = dot(normalize(vWorldNormal), sunDirection);
            float light = .01 + max(solar, 0.0) * .46;
            gl_FragColor = vec4(vec3(.83, .88, .92) * light, smoothstep(.08, .85, cloud) * .68);
            #include <tonemapping_fragment>
            #include <colorspace_fragment>
          }
        `,
        });
        const clouds = new T.Mesh(
          new T.SphereGeometry(1.633, 112, 72),
          cloudMaterial,
        );
        globeTilt.add(clouds);
        scene.add(new T.AmbientLight(0xb5c9d2, 0.75));
        const sun = new T.DirectionalLight(0xe1edeb, 2.4);
        sun.position.set(-3, 4, 5);
        scene.add(sun);
        const rim = new T.DirectionalLight(0xb4b4b4, 0.8);
        rim.position.set(4, 0, -2);
        scene.add(rim);

        // Financial chart displayed in an orbital coordinate system.
        const market = new T.Group();
        market.rotation.set(0.26, 0, -0.36);
        world.add(market);
        const palette = getComputedStyle(element);
        const green = new T.Color(
          palette.getPropertyValue('--brand-green').trim(),
        );
        const red = new T.Color(palette.getPropertyValue('--brand-red').trim());
        const neutral = new T.Color(0x424648);
        const candleColor = new T.Color();
        const barMaterial = new T.MeshPhysicalMaterial({
          color: 0xffffff,
          roughness: 0.34,
          metalness: 0.3,
          clearcoat: 0.32,
          clearcoatRoughness: 0.36,
        });
        const wickMaterial = new T.MeshStandardMaterial({
          color: 0x8d9792,
          roughness: 0.5,
          metalness: 0.3,
        });
        const barGeometry = new RoundedBoxGeometry(0.045, 0.2, 0.04, 2, 0.004);
        const wickGeometry = new T.BoxGeometry(0.003, 1, 0.003);
        const bars = new T.InstancedMesh(barGeometry, barMaterial, 88);
        const wicks = new T.InstancedMesh(wickGeometry, wickMaterial, 88);
        bars.instanceMatrix.setUsage(T.DynamicDrawUsage);
        wicks.instanceMatrix.setUsage(T.DynamicDrawUsage);
        bars.frustumCulled = false;
        wicks.frustumCulled = false;
        market.add(bars, wicks);
        const pose = new T.Object3D();
        const linePositions = new Float32Array(89 * 3);
        const lineGeometry = new T.BufferGeometry();
        lineGeometry.setAttribute(
          'position',
          new T.BufferAttribute(linePositions, 3),
        );
        const lineMaterial = new T.LineBasicMaterial({
          color: 0x8e9792,
          transparent: true,
          opacity: 0.28,
        });
        const priceLine = new T.Line(lineGeometry, lineMaterial);
        priceLine.frustumCulled = false;
        market.add(priceLine);
        const guidePoints = Array.from({ length: 129 }, (_, i) => {
          const a = (i / 128) * Math.PI * 2;
          return new T.Vector3(Math.cos(a) * 2.55, -0.24, Math.sin(a) * 2.55);
        });
        const guideGeometry = new T.BufferGeometry().setFromPoints(guidePoints);
        const guideMaterial = new T.LineBasicMaterial({
          color: 0x7b8580,
          transparent: true,
          opacity: 0.16,
        });
        market.add(new T.Line(guideGeometry, guideMaterial));
        let time = 0,
          ready = false;
        let invalidate = () => {};
        const resize = () => {
          const width = element.clientWidth,
            height = element.clientHeight;
          const pixelBudget = matchMedia('(max-width: 640px)').matches
            ? 1_000_000
            : 3_200_000;
          renderer.setPixelRatio(
            Math.min(
              devicePixelRatio,
              2,
              Math.sqrt(pixelBudget / Math.max(1, width * height)),
            ),
          );
          renderer.setSize(width, height);
          camera.aspect = width / Math.max(1, height);
          camera.updateProjectionMatrix();
          invalidate();
        };
        const observer = new ResizeObserver(resize);
        observer.observe(element);
        resize();
        let loaded = 0;
        const loader = new T.TextureLoader();
        const assets = [
          {
            path: '/earth-blue-marble.jpg',
            uniform: surface.uniforms.dayMap,
            color: true,
          },
          {
            path: '/earth-night-2016.jpg',
            uniform: surface.uniforms.nightMap,
            color: true,
          },
          {
            path: '/earth-clouds.jpg',
            uniform: cloudMaterial.uniforms.cloudMap,
            color: false,
          },
        ];
        const textures = assets.map(({ path, uniform, color }) =>
          loader.load(path, (map) => {
            if (cancelled) {
              map.dispose();
              return;
            }
            if (color) map.colorSpace = T.SRGBColorSpace;
            map.anisotropy = Math.min(
              8,
              renderer.capabilities.getMaxAnisotropy(),
            );
            uniform.value = map;
            loaded += 1;
            ready = loaded === assets.length;
            invalidate();
          }),
        );
        const loop = createMotionLoop(
          element,
          (elapsed, moving) => {
            if (moving) time += elapsed;
            globe.rotation.y = 0.08 + time * 0.036;
            clouds.rotation.y = 0.08 + time * 0.039;
            market.rotation.y = -time * 0.018;
            world.rotation.x = Math.sin(time * 0.09) * 0.018;
            for (let i = 0; i < 88; i++) {
              const a = (i / 88) * Math.PI * 2;
              const level =
                Math.sin(a * 3 + time * 0.3) * 0.12 +
                Math.cos(a * 7 - time * 0.18) * 0.045;
              const change = Math.sin(a * 9 + time * 0.38);
              const height = 0.025 + Math.abs(change) * 0.16;
              pose.position.set(Math.cos(a) * 2.35, level, Math.sin(a) * 2.35);
              pose.rotation.set(0, -a, 0);
              pose.scale.set(1, height / 0.2, 1);
              pose.updateMatrix();
              bars.setMatrixAt(i, pose.matrix);
              // Color emerges from charcoal as the candle grows, avoiding abrupt red/green swaps.
              const strength = T.MathUtils.smoothstep(
                Math.abs(change),
                0,
                0.24,
              );
              const depth =
                0.65 + 0.35 * (Math.sin(a + market.rotation.y) * 0.5 + 0.5);
              candleColor
                .copy(neutral)
                .lerp(change > 0 ? green : red, strength)
                .multiplyScalar(depth);
              bars.setColorAt(i, candleColor);
              pose.scale.set(1, height + 0.075, 1);
              pose.updateMatrix();
              wicks.setMatrixAt(i, pose.matrix);
              linePositions[i * 3] = Math.cos(a) * 2.35;
              linePositions[i * 3 + 1] = level - height / 2 - 0.04;
              linePositions[i * 3 + 2] = Math.sin(a) * 2.35;
            }
            bars.instanceMatrix.needsUpdate = true;
            wicks.instanceMatrix.needsUpdate = true;
            if (bars.instanceColor) bars.instanceColor.needsUpdate = true;
            linePositions.set(linePositions.subarray(0, 3), 88 * 3);
            lineGeometry.attributes.position.needsUpdate = true;
            renderer.render(scene, camera);
            element.dataset.ready = 'true';
          },
          {
            paused: () => stopped.current,
            ready: () => ready && visible.current,
          },
        );
        invalidate = loop.invalidate;
        refresh.current = loop.invalidate;
        const lost = (event: Event) => {
          event.preventDefault();
          element.dataset.ready = 'false';
          ready = false;
          loop.invalidate();
        };
        const restored = () => {
          ready = loaded === assets.length;
          resize();
          loop.invalidate();
        };
        renderer.domElement.addEventListener('webglcontextlost', lost);
        renderer.domElement.addEventListener('webglcontextrestored', restored);
        dispose = () => {
          refresh.current = () => {};
          loop.dispose();
          observer.disconnect();
          renderer.domElement.removeEventListener('webglcontextlost', lost);
          renderer.domElement.removeEventListener(
            'webglcontextrestored',
            restored,
          );
          textures.forEach((texture) => texture.dispose());
          globe.geometry.dispose();
          surface.dispose();
          clouds.geometry.dispose();
          cloudMaterial.dispose();
          barGeometry.dispose();
          wickGeometry.dispose();
          bars.dispose();
          wicks.dispose();
          barMaterial.dispose();
          wickMaterial.dispose();
          lineGeometry.dispose();
          lineMaterial.dispose();
          guideGeometry.dispose();
          guideMaterial.dispose();
          renderer.dispose();
          renderer.domElement.remove();
        };
      })
      .catch(() => {
        /* Keep the brand composition when WebGL cannot load. */
      });
    return () => {
      cancelled = true;
      dispose();
    };
  }, [closeUp]);
  return (
    <div className="earth-render" ref={host}>
      <div className="earth-fallback" aria-hidden="true">
        <div className="earth-intro-mark">
          <Image
            src="/flipflop-hq-mark-v4.png"
            width={240}
            height={240}
            alt=""
            unoptimized
            loading="eager"
          />
          <span>FLIP FLOP / HQ</span>
        </div>
      </div>
    </div>
  );
}
