import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

/**
 * Ciudad MinutoDesk en 3D con cámara isométrica fija (estilo juego de ciudad).
 * Cada lote es la obra de una persona: su modelo depende de la etapa (cimientos con vallas
 * y grúa, estructura, edificio con acabados o rascacielos entregado) y su altura de los pisos.
 * Modelos: Kenney City Kits (CC0), en public/ciudad/.
 */

const BASE = "/ciudad/";
const MODELOS = {
  calle: "calles/road-straight.glb",
  cruce: "calles/road-crossroad.glb",
  vereda: "calles/tile-low.glb",
  cono: "calles/construction-cone.glb",
  valla: "calles/construction-fence.glb",
  barrera: "calles/construction-barrier.glb",
  foco: "calles/construction-light.glb",
  farol: "calles/light-square.glb",
  semaforo: "calles/traffic-light.glb",
  pare: "calles/road-sign-stop.glb",
  letrero: "calles/sign-highway.glb",
  fondoB: "comercial/low-detail-building-b.glb",
  fondoD: "comercial/low-detail-building-d.glb",
  fondoE: "comercial/low-detail-building-e.glb",
  fondoF: "comercial/low-detail-building-f.glb",
  fondoG: "comercial/low-detail-building-g.glb",
  fondoAncho: "comercial/low-detail-building-wide-a.glb",
  sombrilla: "comercial/detail-parasol-a.glb",
  casaB: "suburbano/building-type-b.glb",
  casaD: "suburbano/building-type-d.glb",
  casaE: "suburbano/building-type-e.glb",
  caminito: "suburbano/path-stones-long.glb",
  cerca: "suburbano/fence-1x3.glb",
  arbol: "suburbano/tree-large.glb",
  arbolito: "suburbano/tree-small.glb",
  maceta: "suburbano/planter.glb",
  casaA: "suburbano/building-type-a.glb",
  casaC: "suburbano/building-type-c.glb",
  casaF: "suburbano/building-type-f.glb",
  casaH: "suburbano/building-type-h.glb",
  estructuraA: "comercial/low-detail-building-a.glb",
  estructuraC: "comercial/low-detail-building-c.glb",
  edificioA: "comercial/building-a.glb",
  edificioC: "comercial/building-c.glb",
  edificioE: "comercial/building-e.glb",
  edificioG: "comercial/building-g.glb",
  edificioH: "comercial/building-h.glb",
  edificioK: "comercial/building-k.glb",
  torreA: "comercial/building-skyscraper-a.glb",
  torreB: "comercial/building-skyscraper-b.glb",
  torreC: "comercial/building-skyscraper-c.glb",
  torreE: "comercial/building-skyscraper-e.glb",
};
const POR_ETAPA = {
  2: ["estructuraA", "estructuraC"],
  3: ["edificioA", "edificioC", "edificioE", "edificioG", "edificioH", "edificioK"],
  4: ["torreA", "torreB", "torreC", "torreE"],
};
// Centros de los lotes (las calles se cruzan en x=5, z=5). El 1.º queda más cerca de la cámara;
// el 6.º es para la obra propia cuando no está en el Top 5.
const LOTES = [
  [8, 8],
  [2, 8],
  [8, 2],
  [2, 2],
  [12.4, 8],
  [8, 12.4],
];
const DECORADO = [
  ["casaA", 0.2, 4.0, Math.PI / 2],
  ["casaC", 4.0, 0.2, 0],
  ["casaF", 0.3, 9.9, Math.PI / 2],
  ["casaH", 9.9, 0.3, 0],
  ["casaA", 3.8, 9.9, Math.PI],
  ["casaC", 9.9, 3.8, -Math.PI / 2],
  ["arbol", 3.9, 3.9, 0],
  ["arbol", 6.4, 3.6, 0],
  ["arbol", 3.6, 6.4, 0],
  ["arbolito", 0.2, 6.3, 0],
  ["arbolito", 6.3, 0.2, 0],
  ["arbol", 10.2, 10.2, 0],
  ["arbolito", 0.2, 0.2, 0],
  ["maceta", 4.2, 7.6, 0],
  ["maceta", 7.6, 4.2, 0],
  ["arbol", -2, 2, 0],
  ["arbol", 2, -2, 0],
  ["arbolito", -2.2, 8.5, 0],
  ["arbolito", 8.5, -2.2, 0],
  ["arbol", 12, 6, 0],
  ["arbol", 6, 12, 0],
  // Barrio de casas a los costados.
  ["casaB", -2.2, 4.0, Math.PI / 2],
  ["casaD", -2.2, 6.3, Math.PI / 2],
  ["casaE", 4.0, -2.2, 0],
  ["casaB", 6.3, -2.2, 0],
  ["cerca", -1.3, 5.2, Math.PI / 2],
  ["cerca", 5.2, -1.3, 0],
  ["caminito", 1.0, 1.0, Math.PI / 4],
  ["caminito", 9.0, 9.0, Math.PI / 4],
  ["sombrilla", 3.6, 3.0, 0],
  ["sombrilla", 7.0, 3.6, 0],
  ["arbolito", 12.2, 10.6, 0],
  ["arbolito", 10.6, 12.2, 0],
  ["arbol", 13.6, 3.2, 0],
  ["arbol", 3.2, 13.6, 0],
  ["arbolito", 13.4, 12.8, 0],
  ["letrero", 11.5, 4.4, -Math.PI / 2],
  ["pare", 4.4, 4.4, Math.PI / 4],
];
// Edificios de fondo (detrás de todo, lejos de la cámara): dan la silueta de ciudad.
const SILUETA = [
  ["fondoAncho", -4, -0.5, 0], ["fondoB", -4, 1.5, 0], ["fondoD", -4, 3.5, 0], ["fondoE", -4, 6.5, 0],
  ["fondoF", -4, 8.5, 0], ["fondoG", -4, 10.5, 0], ["fondoG", -0.5, -4, 0], ["fondoD", 1.5, -4, 0],
  ["fondoB", 3.5, -4, 0], ["fondoAncho", 6.5, -4, 0], ["fondoE", 8.5, -4, 0], ["fondoF", 10.5, -4, 0],
  ["fondoE", -4, -4, 0],
];
const COLORES_AUTO = [0xe4572e, 0x2f6bff, 0xf3c13a, 0x29a19c, 0xffffff, 0x8e5bd9];

const cargador = new GLTFLoader();
const cache = new Map();
function cargar(clave) {
  if (!cache.has(clave)) {
    cache.set(
      clave,
      new Promise((ok, mal) =>
        cargador.load(BASE + MODELOS[clave], (g) => ok(g.scene), undefined, mal)
      )
    );
  }
  return cache.get(clave).then((escena) => escena.clone(true));
}

/** Escala el modelo para que su base mida `ancho` y lo apoya en el suelo, centrado. */
function encajar(objeto, ancho) {
  const caja = new THREE.Box3().setFromObject(objeto);
  const tam = caja.getSize(new THREE.Vector3());
  const escala = ancho / Math.max(tam.x, tam.z, 0.0001);
  objeto.scale.setScalar(escala);
  const caja2 = new THREE.Box3().setFromObject(objeto);
  const centro = caja2.getCenter(new THREE.Vector3());
  objeto.position.set(-centro.x, -caja2.min.y, -centro.z);
  const envoltorio = new THREE.Group();
  envoltorio.add(objeto);
  return envoltorio;
}

function sombras(objeto) {
  objeto.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  return objeto;
}

function grua(altura) {
  const amarillo = new THREE.MeshStandardMaterial({ color: 0xf2b134, roughness: 0.6 });
  const g = new THREE.Group();
  const torre = new THREE.Mesh(new THREE.BoxGeometry(0.12, altura, 0.12), amarillo);
  torre.position.y = altura / 2;
  const brazo = new THREE.Group();
  const pluma = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.08, 0.08), amarillo);
  pluma.position.x = 0.5;
  const cable = new THREE.Mesh(
    new THREE.BoxGeometry(0.02, 0.5, 0.02),
    new THREE.MeshStandardMaterial({ color: 0x333333 })
  );
  cable.position.set(1.1, -0.25, 0);
  brazo.add(pluma, cable);
  brazo.position.y = altura;
  g.add(torre, brazo);
  g.userData.brazo = brazo;
  return sombras(g);
}

function auto(color) {
  const g = new THREE.Group();
  const pintura = new THREE.MeshStandardMaterial({ color, roughness: 0.4, metalness: 0.1 });
  const vidrio = new THREE.MeshStandardMaterial({ color: 0x2b3a55, roughness: 0.2 });
  const llanta = new THREE.MeshStandardMaterial({ color: 0x222222, roughness: 0.8 });
  const carro = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.12, 0.22), pintura);
  carro.position.y = 0.1;
  const cabina = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.1, 0.19), vidrio);
  cabina.position.set(-0.03, 0.21, 0);
  g.add(carro, cabina);
  for (const [x, z] of [[0.13, 0.11], [0.13, -0.11], [-0.13, 0.11], [-0.13, -0.11]]) {
    const r = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.04, 10), llanta);
    r.rotation.x = Math.PI / 2;
    r.position.set(x, 0.05, z);
    g.add(r);
  }
  return sombras(g);
}

function nube() {
  const g = new THREE.Group();
  const blanco = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, transparent: true, opacity: 0.92 });
  for (const [x, y, z, r] of [[0, 0, 0, 0.55], [0.55, 0.05, 0.1, 0.42], [-0.5, -0.05, 0.05, 0.4], [0.15, 0.3, -0.05, 0.38]]) {
    const b = new THREE.Mesh(new THREE.IcosahedronGeometry(r, 0), blanco);
    b.position.set(x, y, z);
    b.castShadow = true;
    g.add(b);
  }
  return g;
}

function bandera() {
  const g = new THREE.Group();
  const mastil = new THREE.Mesh(
    new THREE.CylinderGeometry(0.02, 0.02, 0.6),
    new THREE.MeshStandardMaterial({ color: 0xdddddd })
  );
  mastil.position.y = 0.3;
  const tela = new THREE.Mesh(
    new THREE.BoxGeometry(0.3, 0.18, 0.02),
    new THREE.MeshStandardMaterial({ color: 0x2f6bff })
  );
  tela.position.set(0.16, 0.5, 0);
  g.add(mastil, tela);
  g.userData.tela = tela;
  return g;
}

async function obraDe(lote, indice) {
  const g = new THREE.Group();
  const etapa = lote.numero_etapa;
  // Progreso dentro de la etapa: la altura crece con los pisos.
  const crecimiento = 0.75 + Math.min(1, (lote.pisos % 6) / 6) * 0.5;
  let alto = 0.3;

  if (etapa === 1) {
    const losa = new THREE.Mesh(
      new THREE.BoxGeometry(1.8, 0.12, 1.8),
      new THREE.MeshStandardMaterial({ color: 0xb9b2a6, roughness: 0.9 })
    );
    losa.position.y = 0.06;
    losa.receiveShadow = true;
    g.add(losa);
    const extras = await Promise.all([
      cargar("valla"), cargar("valla"), cargar("cono"), cargar("cono"), cargar("barrera"), cargar("foco"),
    ]);
    const pos = [[0, -1.15, 0], [0, 1.15, 0], [-0.9, -0.9, 0], [0.9, 0.95, 0], [-1.15, 0.3, Math.PI / 2], [1.1, -0.9, 0]];
    extras.forEach((m, i) => {
      const o = sombras(encajar(m, i < 2 ? 1.8 : 0.35));
      o.position.set(pos[i][0], 0, pos[i][1]);
      o.rotation.y = pos[i][2];
      g.add(o);
    });
    alto = 0.4;
  } else {
    const opciones = POR_ETAPA[etapa];
    const modelo = await cargar(opciones[indice % opciones.length]);
    const edificio = sombras(encajar(modelo, etapa === 4 ? 1.5 : 1.7));
    // Altura máxima por etapa (para que la torre no se salga de la vista) y crecimiento por pisos.
    const tope = { 2: 2.0, 3: 3.0, 4: 4.2 }[etapa];
    const altoModelo = new THREE.Box3().setFromObject(edificio).max.y;
    edificio.scale.y *= Math.min(1, tope / altoModelo) * crecimiento;
    g.add(edificio);
    alto = new THREE.Box3().setFromObject(edificio).max.y;
  }
  if (etapa <= 2) {
    const gr = grua(Math.max(1.6, alto + 0.8));
    gr.position.set(-0.75, 0, 0.75);
    g.add(gr);
    g.userData.grua = gr;
  }
  if (etapa === 4) {
    const b = bandera();
    b.position.y = alto;
    g.add(b);
    g.userData.bandera = b;
  }
  g.userData.alto = alto;
  return g;
}

export default function CiudadObras({ lotes, alElegir }) {
  const contenedor = useRef(null);
  const [etiquetas, setEtiquetas] = useState([]);
  const [tip, setTip] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const div = contenedor.current;
    if (!div) return undefined;
    let vivo = true;
    let ancho = div.clientWidth;
    let alto = div.clientHeight;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(ancho, alto);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    div.appendChild(renderer.domElement);

    const escena = new THREE.Scene();
    const centro = new THREE.Vector3(5, 0, 5);
    const mira = new THREE.Vector3(5, 1.2, 5);
    const vista = 9;
    const camara = new THREE.OrthographicCamera(-vista, vista, vista, -vista, 0.1, 200);
    const ajustarCamara = () => {
      const r = ancho / alto;
      camara.left = -vista * r;
      camara.right = vista * r;
      camara.top = vista;
      camara.bottom = -vista;
      camara.updateProjectionMatrix();
    };
    camara.position.set(mira.x + 20, mira.y + 18, mira.z + 20);
    camara.lookAt(mira);
    camara.zoom = 1.35;
    ajustarCamara();

    escena.add(new THREE.HemisphereLight(0xdfefff, 0x9a8f80, 1.4));
    const sol = new THREE.DirectionalLight(0xfff3dd, 2.2);
    sol.position.set(centro.x + 10, 20, centro.z - 6);
    sol.target.position.copy(centro);
    sol.castShadow = true;
    sol.shadow.mapSize.set(2048, 2048);
    Object.assign(sol.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 60 });
    sol.shadow.bias = -0.0005;
    escena.add(sol, sol.target);

    const pasto = new THREE.Mesh(
      new THREE.PlaneGeometry(200, 200),
      new THREE.MeshStandardMaterial({ color: 0x9fd18b, roughness: 1 })
    );
    pasto.rotation.x = -Math.PI / 2;
    pasto.position.set(centro.x, -0.01, centro.z);
    pasto.receiveShadow = true;
    escena.add(pasto);

    const obras = []; // { grupo, lote, objetivoY, inicio }
    const animables = [];
    const autos = []; // { a, ruta, fase, velocidad }
    const nubes = [];
    const relojInicio = performance.now();

    async function armar() {
      // Manzanas: veredas en los cuatro bloques que dejan las calles.
      for (const [x0, z0] of [[0, 0], [6, 0], [0, 6], [6, 6]]) {
        for (let x = x0; x < x0 + 5; x++) {
          for (let z = z0; z < z0 + 5; z++) {
            const v = encajar(await cargar("vereda"), 1.001);
            v.position.set(x, 0, z);
            v.traverse((o) => o.isMesh && (o.receiveShadow = true));
            escena.add(v);
          }
        }
      }
      // Calles en cruz.
      for (let i = -1; i <= 11; i++) {
        for (const [x, z, rot] of [[i, 5, Math.PI / 2], [5, i, 0]]) {
          if (x === 5 && z === 5) continue;
          const c = sombras(encajar(await cargar("calle"), 1.001));
          c.position.set(x, 0, z);
          c.rotation.y = rot;
          escena.add(c);
        }
      }
      const cruce = encajar(await cargar("cruce"), 1.001);
      cruce.position.set(5, 0, 5);
      escena.add(cruce);
      for (const [x, z] of [[4.3, 3.7], [5.7, 6.3], [3.7, 5.7], [6.3, 4.3]]) {
        const f = sombras(encajar(await cargar("farol"), 0.35));
        f.position.set(x, 0, z);
        escena.add(f);
      }
      // Semáforos en las esquinas del cruce y faroles a lo largo de las calles.
      for (const [x, z, rot] of [[4.4, 5.6, 0], [5.6, 4.4, Math.PI], [4.4, 4.4, -Math.PI / 2], [5.6, 5.6, Math.PI / 2]]) {
        const sem = sombras(encajar(await cargar("semaforo"), 0.3));
        sem.position.set(x, 0, z);
        sem.rotation.y = rot;
        escena.add(sem);
      }
      for (const k of [0.5, 2.5, 7.5, 9.5]) {
        for (const [x, z] of [[k, 4.45], [k, 5.55], [4.45, k], [5.55, k]]) {
          const f = sombras(encajar(await cargar("farol"), 0.3));
          f.position.set(x, 0, z);
          escena.add(f);
        }
      }
      for (const [clave, x, z, rot] of SILUETA) {
        const o = sombras(encajar(await cargar(clave), 1.3));
        const altoFondo = new THREE.Box3().setFromObject(o).max.y;
        o.scale.y *= Math.min(1, 1.8 / altoFondo); // de fondo: más bajos que las obras
        o.position.set(x, 0, z);
        o.rotation.y = rot;
        escena.add(o);
      }
      // Autos que circulan por las dos calles, en ambos sentidos.
      const carriles = [
        [(t) => [t, 4.82], 0],
        [(t) => [11 - t, 5.18], Math.PI],
        [(t) => [5.18, t], -Math.PI / 2],
        [(t) => [4.82, 11 - t], Math.PI / 2],
      ];
      for (let n = 0; n < 6; n++) {
        const a = auto(COLORES_AUTO[n % COLORES_AUTO.length]);
        const [ruta, rot] = carriles[n % carriles.length];
        a.rotation.y = rot;
        escena.add(a);
        autos.push({ a, ruta, fase: n * 2.7, velocidad: 0.9 + (n % 3) * 0.25 });
      }
      for (let n = 0; n < 4; n++) {
        const c = nube();
        // Detrás de la ciudad, para que no tapen las obras.
        c.position.set(-8 + n * 7, 5 + (n % 2) * 0.8, -7 - (n % 2) * 2);
        c.scale.setScalar(0.7 + (n % 3) * 0.2);
        escena.add(c);
        nubes.push(c);
      }
      for (const [clave, x, z, rot] of DECORADO) {
        const ancho = clave.startsWith("casa")
          ? 1.6
          : { maceta: 0.4, sombrilla: 0.5, pare: 0.25, letrero: 0.9, caminito: 1.2, cerca: 1.4 }[clave] ?? 0.9;
        const o = sombras(encajar(await cargar(clave), ancho));
        o.position.set(x, 0, z);
        o.rotation.y = rot;
        escena.add(o);
      }
      // Lotes.
      for (let i = 0; i < lotes.length && i < LOTES.length; i++) {
        const [x, z] = LOTES[i];
        // Terreno del lote: una losa clara un poco más alta que la vereda.
        const terreno = new THREE.Mesh(
          new THREE.BoxGeometry(2.5, 0.05, 2.5),
          new THREE.MeshStandardMaterial({ color: lotes[i].es_yo ? 0xcfe0ff : 0xe9e4da, roughness: 0.95 })
        );
        terreno.position.set(x, 0.025, z);
        terreno.receiveShadow = true;
        escena.add(terreno);
        const grupo = await obraDe(lotes[i], i);
        grupo.position.set(x, 0.05, z);
        grupo.scale.y = 0.01; // se levanta con una animación al entrar
        grupo.userData.indice = i;
        escena.add(grupo);
        obras.push({ grupo, inicio: 250 * i });
        if (grupo.userData.grua) animables.push(grupo.userData.grua.userData.brazo);
      }
    }

    const proyectar = () => {
      setEtiquetas(
        obras.map(({ grupo }) => {
          const p = grupo.position.clone();
          p.y = (grupo.userData.alto ?? 1) * grupo.scale.y + 0.6;
          p.project(camara);
          return {
            i: grupo.userData.indice,
            x: ((p.x + 1) / 2) * ancho,
            y: ((1 - p.y) / 2) * alto,
          };
        })
      );
    };

    let cuadro;
    const bucle = (t) => {
      if (!vivo) return;
      const ms = t - relojInicio;
      for (const o of obras) {
        const k = Math.min(1, Math.max(0, (ms - o.inicio) / 1100));
        o.grupo.scale.y = 0.01 + 0.99 * (1 - Math.pow(1 - k, 3));
      }
      animables.forEach((b, i) => (b.rotation.y = Math.sin(ms / 1800 + i) * 0.9));
      for (const { a, ruta, fase, velocidad } of autos) {
        const t = (((ms / 1000) * velocidad + fase) % 13) - 1.5; // de -1.5 a 11.5 y vuelve a empezar
        const [x, z] = ruta(t);
        a.position.set(x, 0.02, z);
        a.visible = t > -1.4 && t < 11.4;
      }
      nubes.forEach((c, i) => {
        c.position.x += 0.004 + i * 0.001;
        if (c.position.x > 16) c.position.x = -12;
      });
      renderer.render(escena, camara);
      if (Math.round(ms / 50) % 2 === 0) proyectar();
      cuadro = requestAnimationFrame(bucle);
    };

    armar()
      .then(() => {
        if (!vivo) return;
        setCargando(false);
        cuadro = requestAnimationFrame(bucle);
      })
      .catch((e) => vivo && setError(`No se pudo cargar la ciudad: ${e?.message ?? e}`));

    // Zoom con la rueda y desplazamiento arrastrando.
    const alRueda = (e) => {
      e.preventDefault();
      camara.zoom = Math.min(2.6, Math.max(0.7, camara.zoom * (e.deltaY > 0 ? 0.9 : 1.1)));
      camara.updateProjectionMatrix();
    };
    let arrastre = null;
    const alBajar = (e) => (arrastre = { x: e.clientX, y: e.clientY, pos: camara.position.clone(), mov: false });
    const rayo = new THREE.Raycaster();
    const alMover = (e) => {
      const r = div.getBoundingClientRect();
      if (arrastre) {
        const dx = (e.clientX - arrastre.x) / camara.zoom / 40;
        const dy = (e.clientY - arrastre.y) / camara.zoom / 40;
        if (Math.abs(dx) + Math.abs(dy) > 0.05) arrastre.mov = true;
        camara.position.set(arrastre.pos.x - dx - dy, arrastre.pos.y, arrastre.pos.z + dx - dy);
        return;
      }
      rayo.setFromCamera(
        new THREE.Vector2(((e.clientX - r.left) / ancho) * 2 - 1, -((e.clientY - r.top) / alto) * 2 + 1),
        camara
      );
      const golpe = rayo.intersectObjects(obras.map((o) => o.grupo), true)[0];
      let g = golpe?.object;
      while (g && g.userData.indice === undefined) g = g.parent;
      div.style.cursor = g ? "pointer" : "grab";
      setTip(g ? { i: g.userData.indice, x: e.clientX - r.left, y: e.clientY - r.top } : null);
    };
    const alSoltar = () => {
      if (arrastre && !arrastre.mov) setTip((t) => (t ? (alElegir?.(t.i), t) : t));
      arrastre = null;
    };
    const alSalir = () => {
      arrastre = null;
      setTip(null);
    };
    const alRedimensionar = () => {
      ancho = div.clientWidth;
      alto = div.clientHeight;
      renderer.setSize(ancho, alto);
      ajustarCamara();
    };
    div.addEventListener("wheel", alRueda, { passive: false });
    div.addEventListener("pointerdown", alBajar);
    div.addEventListener("pointermove", alMover);
    div.addEventListener("pointerup", alSoltar);
    div.addEventListener("pointerleave", alSalir);
    const observador = new ResizeObserver(alRedimensionar);
    observador.observe(div);

    return () => {
      vivo = false;
      cancelAnimationFrame(cuadro);
      observador.disconnect();
      div.removeEventListener("wheel", alRueda);
      div.removeEventListener("pointerdown", alBajar);
      div.removeEventListener("pointermove", alMover);
      div.removeEventListener("pointerup", alSoltar);
      div.removeEventListener("pointerleave", alSalir);
      escena.traverse((o) => {
        if (o.isMesh) {
          o.geometry.dispose();
          [].concat(o.material).forEach((m) => m.dispose());
        }
      });
      renderer.dispose();
      div.removeChild(renderer.domElement);
    };
  }, [lotes, alElegir]);

  const loteTip = tip ? lotes[tip.i] : null;

  return (
    <div
      ref={contenedor}
      className="relative h-[420px] w-full touch-none select-none overflow-hidden rounded-xl bg-gradient-to-b from-sky-100 to-sky-50 sm:h-[480px]"
      style={{ cursor: "grab" }}
    >
      {cargando && !error && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-500">
          Levantando la ciudad…
        </div>
      )}
      {error && <div className="absolute inset-0 flex items-center justify-center p-4 text-sm text-red-600">{error}</div>}
      {etiquetas.map((e) => {
        const l = lotes[e.i];
        return (
          <div
            key={e.i}
            className={`pointer-events-none absolute -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold shadow ${
              l.es_yo ? "bg-acento text-white" : "bg-white/90 text-noche"
            }`}
            style={{ left: e.x, top: e.y }}
          >
            {l.posicion === 1 ? "🏆 " : `#${l.posicion} `}
            {l.es_yo ? "⭐ Tú" : l.nombre}
          </div>
        );
      })}
      {loteTip && (
        <div
          className="pointer-events-none absolute z-10 min-w-[170px] rounded-xl border border-linea bg-white p-2.5 text-xs shadow-lg"
          style={{ left: `min(${tip.x + 12}px, calc(100% - 190px))`, top: tip.y + 12 }}
        >
          <div className="font-semibold text-noche">
            #{loteTip.posicion} · {loteTip.es_yo ? "Tu obra" : loteTip.nombre}
          </div>
          <div className="text-gray-600">{loteTip.etapa}</div>
          <div className="text-gray-600">
            {loteTip.puntos} puntos · {loteTip.pisos} pisos
          </div>
        </div>
      )}
      <div className="pointer-events-none absolute bottom-2 right-3 text-[10px] text-gray-500">
        Rueda: zoom · Arrastra: mover · Modelos: Kenney (CC0)
      </div>
    </div>
  );
}
