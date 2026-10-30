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
  toldo: "comercial/detail-awning-wide.glb",
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
// Trazado: calles cada 6 casillas (x y z = -1, 5, 11, 17) que dejan 3×3 manzanas de 5×5.
const CALLES = [-1, 5, 11, 17];
const MANZANAS = [0, 6, 12];
const EXTENSION = [-2, 18]; // hasta dónde llegan las calles
// Cada manzana tiene 4 lotes de 2×2. Orden: primero el más cercano a la cámara.
const enManzana = (x0, z0) => [
  [x0 + 3.05, z0 + 3.05],
  [x0 + 0.95, z0 + 3.05],
  [x0 + 3.05, z0 + 0.95],
  [x0 + 0.95, z0 + 0.95],
];
// Manzanas especiales: centro comercial (frente), lago (izquierda) y parque (derecha).
const MANZANA_MALL = [12, 12];
const MANZANA_LAGO = [0, 12];
const MANZANA_PARQUE = [12, 0];
// El Top 4 va en la manzana del centro; el resto de las obras, en las demás manzanas.
const LOTES_CENTRO = enManzana(6, 6);
const LOTES_RESTO = [[12, 6], [6, 12], [0, 6], [6, 0], [0, 0]].flatMap(([x, z]) => enManzana(x, z));
const LOTES = [...LOTES_CENTRO, ...LOTES_RESTO];
const ANCHO_LOTE = 2.0;
// Edificios de fondo (detrás de todo, lejos de la cámara): dan la silueta de ciudad.
const SILUETA = [];
for (let k = -3; k <= 17; k += 2) {
  const tipos = ["fondoB", "fondoD", "fondoE", "fondoF", "fondoG", "fondoAncho"];
  SILUETA.push([tipos[(k + 3) % tipos.length], -4, k, 0]);
  if (k > -3) SILUETA.push([tipos[(k + 6) % tipos.length], k, -4, 0]);
}
const CASAS = ["casaA", "casaB", "casaC", "casaD", "casaE", "casaF", "casaH"];
const COLORES_AUTO = [0xe4572e, 0x2f6bff, 0xf3c13a, 0x29a19c, 0xffffff, 0x8e5bd9];
// Tonos pastel para las casitas: se multiplican sobre la textura original.
const COLORES_CASA = [0xffb3b3, 0xffd59e, 0xfff0a0, 0xb8f0c2, 0xa8d8ff, 0xd9c2ff, 0xffc4e1];

function pintar(objeto, color) {
  objeto.traverse((o) => {
    if (o.isMesh) {
      o.material = o.material.clone();
      o.material.color = new THREE.Color(color);
    }
  });
  return objeto;
}

const material = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, ...extra });
function caja(ancho, alto, fondo, color, extra) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(ancho, alto, fondo), material(color, extra));
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

/** Parquecito: pasto, caminos en cruz, fuente con agua, bancas y un columpio. */
function parque() {
  const g = new THREE.Group();
  const pasto = caja(3.6, 0.06, 3.6, 0x7fc66b);
  pasto.position.y = 0.03;
  const caminoA = caja(3.6, 0.07, 0.45, 0xe8dcc0);
  const caminoB = caja(0.45, 0.07, 3.6, 0xe8dcc0);
  caminoA.position.y = caminoB.position.y = 0.04;
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.6, 0.18, 20), material(0xd9d2c3));
  base.position.y = 0.12;
  const agua = new THREE.Mesh(
    new THREE.CylinderGeometry(0.45, 0.45, 0.04, 20),
    material(0x5bc0eb, { roughness: 0.15, metalness: 0.1, transparent: true, opacity: 0.9 })
  );
  agua.position.y = 0.22;
  const chorro = new THREE.Mesh(
    new THREE.CylinderGeometry(0.04, 0.08, 0.45, 10),
    material(0xb7e9ff, { transparent: true, opacity: 0.8 })
  );
  chorro.position.y = 0.45;
  g.add(pasto, caminoA, caminoB, base, agua, chorro);
  g.userData.chorro = chorro;
  for (const [x, z, r] of [[-1.1, 0.5, 0], [1.1, -0.5, Math.PI], [0.5, 1.1, -Math.PI / 2], [-0.5, -1.1, Math.PI / 2]]) {
    const banca = new THREE.Group();
    const asiento = caja(0.5, 0.05, 0.16, 0xa0643c);
    asiento.position.y = 0.16;
    const respaldo = caja(0.5, 0.15, 0.04, 0xa0643c);
    respaldo.position.set(0, 0.26, -0.07);
    const pata1 = caja(0.04, 0.16, 0.14, 0x555555);
    const pata2 = pata1.clone();
    pata1.position.set(-0.2, 0.08, 0);
    pata2.position.set(0.2, 0.08, 0);
    banca.add(asiento, respaldo, pata1, pata2);
    banca.position.set(x, 0.06, z);
    banca.rotation.y = r;
    g.add(banca);
  }
  const columpio = new THREE.Group();
  const poste1 = caja(0.05, 0.6, 0.05, 0xe4572e);
  const poste2 = poste1.clone();
  poste1.position.set(-0.3, 0.3, 0);
  poste2.position.set(0.3, 0.3, 0);
  const travesano = caja(0.65, 0.05, 0.05, 0xe4572e);
  travesano.position.y = 0.6;
  const asientoC = caja(0.16, 0.03, 0.1, 0x2f6bff);
  asientoC.position.y = 0.2;
  columpio.add(poste1, poste2, travesano, asientoC);
  columpio.position.set(1.1, 0.06, 1.1);
  g.add(columpio);
  return g;
}

/** Lago con orilla de arena, rocas, un muelle y un botecito. */
function lago() {
  const g = new THREE.Group();
  const orilla = new THREE.Mesh(new THREE.CircleGeometry(1.9, 28), material(0xe9d8a6));
  orilla.rotation.x = -Math.PI / 2;
  orilla.scale.set(1.25, 0.85, 1);
  orilla.position.y = 0.012;
  orilla.receiveShadow = true;
  const agua = new THREE.Mesh(
    new THREE.CircleGeometry(1.6, 28),
    material(0x3fa7e0, { roughness: 0.1, metalness: 0.2, transparent: true, opacity: 0.92 })
  );
  agua.rotation.x = -Math.PI / 2;
  agua.scale.set(1.25, 0.85, 1);
  agua.position.y = 0.02;
  agua.receiveShadow = true;
  g.add(orilla, agua);
  g.userData.agua = agua;
  for (const [x, z, r] of [[1.6, 0.6, 0.18], [-1.7, -0.4, 0.14], [0.4, -1.3, 0.12], [-0.9, 1.1, 0.16]]) {
    const roca = new THREE.Mesh(new THREE.DodecahedronGeometry(r, 0), material(0x9a9a9a));
    roca.position.set(x, r * 0.6, z);
    roca.castShadow = true;
    g.add(roca);
  }
  const muelle = caja(0.3, 0.05, 0.9, 0xa0643c);
  muelle.position.set(-0.6, 0.06, 0.55);
  const bote = caja(0.35, 0.08, 0.16, 0xffffff);
  bote.position.set(0.5, 0.06, 0.1);
  g.add(muelle, bote);
  g.userData.bote = bote;
  return g;
}

/** Centro comercial: edificio bajo y ancho con vitrinas, letrero «PLAZA» y estacionamiento. */
function centroComercial() {
  const g = new THREE.Group();
  const estacionamiento = caja(3.4, 0.04, 1.3, 0x5d6370);
  estacionamiento.position.set(0, 0.02, 1.15);
  g.add(estacionamiento);
  for (let i = -3; i <= 3; i++) {
    const linea = caja(0.03, 0.045, 0.45, 0xffffff);
    linea.position.set(i * 0.42, 0.025, 1.3);
    g.add(linea);
  }
  const cuerpo = caja(3.2, 0.9, 1.6, 0xf4efe6);
  cuerpo.position.set(0, 0.45, -0.4);
  const vitrina = caja(3.0, 0.38, 0.02, 0x7cc4f2, { roughness: 0.1, metalness: 0.3 });
  vitrina.position.set(0, 0.3, 0.41);
  const franja = caja(3.2, 0.12, 1.62, 0xe4572e);
  franja.position.set(0, 0.85, -0.4);
  const techo = caja(1.1, 0.35, 0.8, 0xf4efe6);
  techo.position.set(0.6, 1.05, -0.5);
  const domo = caja(0.6, 0.06, 0.4, 0x9fd8ff, { roughness: 0.1, transparent: true, opacity: 0.85 });
  domo.position.set(-0.6, 0.93, -0.4);
  const letrero = caja(0.9, 0.28, 0.06, 0x2f6bff);
  letrero.position.set(-0.6, 1.2, 0.35);
  g.add(cuerpo, vitrina, franja, techo, domo, letrero);
  const lienzo = document.createElement("canvas");
  lienzo.width = 256;
  lienzo.height = 80;
  const ctx = lienzo.getContext("2d");
  ctx.fillStyle = "#2f6bff";
  ctx.fillRect(0, 0, 256, 80);
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 46px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("PLAZA", 128, 42);
  const textura = new THREE.CanvasTexture(lienzo);
  textura.colorSpace = THREE.SRGBColorSpace;
  const cartel = new THREE.Mesh(new THREE.PlaneGeometry(0.86, 0.26), new THREE.MeshBasicMaterial({ map: textura }));
  cartel.position.set(-0.6, 1.2, 0.385);
  g.add(cartel);
  return g;
}


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
    const centro = new THREE.Vector3(8, 0, 8);
    const mira = new THREE.Vector3(8.5, 0.3, 8.5);
    const vista = 9;
    const camara = new THREE.OrthographicCamera(-vista, vista, vista, -vista, 0.1, 200);
    // En pantallas angostas (celular) se aleja la cámara para que entre la ciudad a lo ancho.
    const anchoMinimo = vista * 1.35;
    const ajustarCamara = () => {
      const r = ancho / alto;
      const medioAlto = Math.max(vista, anchoMinimo / r);
      camara.left = -medioAlto * r;
      camara.right = medioAlto * r;
      camara.top = medioAlto;
      camara.bottom = -medioAlto;
      camara.updateProjectionMatrix();
    };
    camara.position.set(mira.x + 20, mira.y + 18, mira.z + 20);
    camara.lookAt(mira);
    camara.zoom = 1.0;
    ajustarCamara();

    escena.add(new THREE.HemisphereLight(0xdfefff, 0x9a8f80, 1.4));
    const sol = new THREE.DirectionalLight(0xfff3dd, 2.2);
    sol.position.set(centro.x + 10, 20, centro.z - 6);
    sol.target.position.copy(centro);
    sol.castShadow = true;
    sol.shadow.mapSize.set(3072, 3072);
    Object.assign(sol.shadow.camera, { left: -17, right: 17, top: 17, bottom: -17, near: 1, far: 80 });
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
    const efectos = []; // [chorro de la fuente, agua del lago, bote]
    const relojInicio = performance.now();

    async function armar() {
      const losa = (clave, ancho) => cargar(clave).then((m) => encajar(m, ancho));
      // Veredas en las 9 manzanas.
      for (const x0 of MANZANAS) {
        for (const z0 of MANZANAS) {
          for (let x = x0; x < x0 + 5; x++) {
            for (let z = z0; z < z0 + 5; z++) {
              const v = await losa("vereda", 1.001);
              v.position.set(x, 0, z);
              v.traverse((o) => o.isMesh && (o.receiveShadow = true));
              escena.add(v);
            }
          }
        }
      }
      // Calles: una cuadrícula con cruces en cada intersección.
      for (const fija of CALLES) {
        for (let i = EXTENSION[0]; i <= EXTENSION[1]; i++) {
          for (const [x, z, rot] of [[i, fija, Math.PI / 2], [fija, i, 0]]) {
            const esCruce = CALLES.includes(x) && CALLES.includes(z);
            if (esCruce && rot === 0) continue; // el cruce se pone una sola vez
            const c = sombras(await losa(esCruce ? "cruce" : "calle", 1.001));
            c.position.set(x, 0, z);
            if (!esCruce) c.rotation.y = rot;
            escena.add(c);
          }
        }
      }
      // Semáforos en los cruces interiores y faroles a lo largo de las calles.
      for (const cx of [5, 11]) {
        for (const cz of [5, 11]) {
          for (const [dx, dz, rot] of [[-0.6, 0.6, 0], [0.6, -0.6, Math.PI]]) {
            const sem = sombras(await losa("semaforo", 0.3));
            sem.position.set(cx + dx, 0, cz + dz);
            sem.rotation.y = rot;
            escena.add(sem);
          }
        }
      }
      for (const fija of [5, 11]) {
        for (let k = 0.5; k <= 16.5; k += 3) {
          for (const [x, z] of [[k, fija - 0.55], [fija + 0.55, k]]) {
            const f = sombras(await losa("farol", 0.3));
            f.position.set(x, 0, z);
            escena.add(f);
          }
        }
      }
      for (const [clave, x, z, rot] of SILUETA) {
        const o = sombras(await losa(clave, 1.3));
        const altoFondo = new THREE.Box3().setFromObject(o).max.y;
        o.scale.y *= Math.min(1, 1.8 / altoFondo); // de fondo: más bajos que las obras
        o.position.set(x, 0, z);
        o.rotation.y = rot;
        escena.add(o);
      }
      // Árboles en el borde de la ciudad.
      for (let k = -1; k <= 17; k += 2.5) {
        for (const [x, z] of [[18.8, k], [k, 18.8]]) {
          const a = sombras(await losa(Math.round(k) % 2 ? "arbol" : "arbolito", 0.8));
          a.position.set(x, 0, z);
          escena.add(a);
        }
      }
      // Autos que circulan por las calles interiores, en ambos sentidos.
      const largo = EXTENSION[1] - EXTENSION[0];
      const carriles = [];
      for (const fija of [5, 11, 17]) {
        carriles.push(
          [(t) => [EXTENSION[0] + t, fija - 0.18], 0],
          [(t) => [EXTENSION[1] - t, fija + 0.18], Math.PI],
          [(t) => [fija + 0.18, EXTENSION[0] + t], -Math.PI / 2],
          [(t) => [fija - 0.18, EXTENSION[1] - t], Math.PI / 2]
        );
      }
      for (let n = 0; n < 14; n++) {
        const a = auto(COLORES_AUTO[n % COLORES_AUTO.length]);
        const [ruta, rot] = carriles[n % carriles.length];
        a.rotation.y = rot;
        escena.add(a);
        autos.push({ a, ruta, fase: n * 3.1, velocidad: 0.9 + (n % 3) * 0.3, largo });
      }
      for (let n = 0; n < 5; n++) {
        const c = nube();
        // Detrás de la ciudad, para que no tapen las obras.
        c.position.set(-10 + n * 7, 6 + (n % 2) * 0.8, -8 - (n % 2) * 2);
        c.scale.setScalar(0.8 + (n % 3) * 0.2);
        escena.add(c);
        nubes.push(c);
      }
      // Manzanas especiales.
      const elParque = parque();
      elParque.position.set(MANZANA_PARQUE[0] + 2, 0, MANZANA_PARQUE[1] + 2);
      const elLago = lago();
      elLago.position.set(MANZANA_LAGO[0] + 2, 0, MANZANA_LAGO[1] + 2);
      const elMall = centroComercial();
      elMall.position.set(MANZANA_MALL[0] + 2, 0, MANZANA_MALL[1] + 1.6);
      escena.add(elParque, elLago, elMall);
      efectos.push(elParque.userData.chorro, elLago.userData.agua, elLago.userData.bote);
      for (const x of [-1, 1]) {
        const t = sombras(await losa("toldo", 0.8));
        t.position.set(MANZANA_MALL[0] + 2 + x, 0, MANZANA_MALL[1] + 1.25);
        escena.add(t);
      }
      for (const [x, z] of [[0.2, 12.4], [4, 16.2], [0.4, 16.2], [12.3, 0.2], [16.2, 3.8], [16.2, 0.3]]) {
        const a = sombras(await losa("arbol", 0.8));
        a.position.set(x, 0, z);
        escena.add(a);
      }

      // Lotes: obras de las personas; los que sobran, casitas de colores y árboles.
      for (let i = 0; i < LOTES.length; i++) {
        const [x, z] = LOTES[i];
        const lote = lotes[i];
        if (!lote) {
          if (i % 3 === 2) {
            const a = sombras(await losa(i % 2 ? "arbol" : "arbolito", 0.9));
            a.position.set(x, 0, z);
            escena.add(a);
          } else {
            const casa = sombras(await losa(CASAS[i % CASAS.length], 1.6));
            pintar(casa, COLORES_CASA[i % COLORES_CASA.length]);
            casa.position.set(x, 0, z);
            casa.rotation.y = (i % 4) * (Math.PI / 2);
            escena.add(casa);
          }
          continue;
        }
        // Terreno del lote: una losa clara un poco más alta que la vereda.
        const terreno = new THREE.Mesh(
          new THREE.BoxGeometry(ANCHO_LOTE, 0.05, ANCHO_LOTE),
          new THREE.MeshStandardMaterial({ color: lote.es_yo ? 0xcfe0ff : 0xe9e4da, roughness: 0.95 })
        );
        terreno.position.set(x, 0.025, z);
        terreno.receiveShadow = true;
        escena.add(terreno);
        const grupo = await obraDe(lote, i);
        grupo.position.set(x, 0.05, z);
        grupo.scale.set(0.85, 0.01, 0.85); // se levanta con una animación al entrar
        grupo.userData.indice = i;
        escena.add(grupo);
        obras.push({ grupo, inicio: 120 * i });
        if (grupo.userData.grua) animables.push(grupo.userData.grua.userData.brazo);
      }
    }

    const proyectar = () => {
      setEtiquetas(
        obras.filter(({ grupo }) => !lotes[grupo.userData.indice].anonimo).map(({ grupo }) => {
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
      for (const { a, ruta, fase, velocidad, largo } of autos) {
        const t = ((ms / 1000) * velocidad + fase) % largo; // recorre la calle y vuelve a empezar
        const [x, z] = ruta(t);
        a.position.set(x, 0.02, z);
        a.visible = t > 0.2 && t < largo - 0.2;
      }
      if (efectos.length) {
        const [chorro, agua, bote] = efectos;
        chorro.scale.y = 1 + Math.sin(ms / 250) * 0.15;
        agua.material.opacity = 0.88 + Math.sin(ms / 900) * 0.05;
        bote.position.x = 0.5 + Math.sin(ms / 2500) * 0.6;
        bote.position.z = 0.1 + Math.cos(ms / 2500) * 0.3;
      }
      nubes.forEach((c, i) => {
        c.position.x += 0.004 + i * 0.001;
        if (c.position.x > 24) c.position.x = -14;
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
    div.addEventListener("pointercancel", alSalir); // en celular, el navegador tomó el gesto para desplazar
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
      div.removeEventListener("pointercancel", alSalir);
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
      className="relative h-[360px] w-full touch-pan-y select-none overflow-hidden rounded-xl bg-gradient-to-b from-sky-100 to-sky-50 sm:h-[560px]"
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
            {loteTip.anonimo
              ? "Obra de un compañero"
              : `#${loteTip.posicion} · ${loteTip.es_yo ? "Tu obra" : loteTip.nombre}`}
          </div>
          <div className="text-gray-600">{loteTip.etapa}</div>
          <div className="text-gray-600">
            {loteTip.anonimo ? `${loteTip.pisos} pisos` : `${loteTip.puntos} puntos · ${loteTip.pisos} pisos`}
          </div>
        </div>
      )}
      <div className="pointer-events-none absolute bottom-2 right-3 text-[10px] text-gray-500">
        Rueda: zoom · Arrastra: mover · Modelos: Kenney (CC0)
      </div>
    </div>
  );
}
