// Rendu de la carte avec MapLibre GL JS. Aucune donnée n'est téléchargée ici
// (hors tuiles) : les données arrivent en arguments, les clics repartent par des callbacks.

const MAPLIBRE = "https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1";
const FOND = "https://data.geopf.fr/annexes/ressources/vectorTiles/styles/PLAN.IGN/gris.json";
const URL_CADASTRE = "https://openmaptiles.geo.data.gouv.fr/data/cadastre.json";
const POLICE = ["Source Sans Pro Bold"]; // police servie par le style IGN
const DEPARTEMENTS = ["75", "92", "93", "94"];
const ZOOM_PARCELLES = 13; // zoom minimal des parcelles dans les tuiles du cadastre

// Échelle de couleurs du prix médian au m² (€/m²)
const ECHELLE = [
  [3000, "#ffffb2"], [5000, "#fecc5c"], [7000, "#fd8d3c"], [10000, "#f03b20"], [14000, "#bd0026"],
];

// Charge MapLibre (module ESM + feuille de style). Le script UMD ne convient pas :
// Quarto charge un chargeur AMD (require.js) qui l'empêche de définir window.maplibregl.
async function chargerMaplibre() {
  const css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = `${MAPLIBRE}/dist/maplibre-gl.css`;
  document.head.append(css);
  return (await import(`${MAPLIBRE}/+esm`)).default;
}

function ajouterLegende(conteneur) {
  const legende = document.createElement("div");
  legende.className = "legende";
  const degrade = ECHELLE.map(([v, c]) => `${c} ${((v - 3000) / 11000) * 100}%`).join(", ");
  legende.innerHTML = `<strong>Prix médian au m² des parcelles</strong>
    <div class="degrade" style="background: linear-gradient(to right, ${degrade})"></div>
    <div class="bornes"><span>3 000 €</span><span>14 000 €</span></div>`;
  conteneur.append(legende);
}

// Emprise [[ouest, sud], [est, nord]] d'une liste de géométries GeoJSON
function emprise(geometries) {
  const points = geometries.flatMap((g) => g.coordinates.flat(g.type === "MultiPolygon" ? 2 : 1));
  const lons = points.map((p) => p[0]), lats = points.map((p) => p[1]);
  return [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]];
}

// Crée la carte dans `conteneur`.
// Callbacks : surSection(idSection), surParcelle(idParcelle).
export async function creerCarte(conteneur, { surSection, surParcelle }) {
  const maplibregl = await chargerMaplibre();
  const carte = new maplibregl.Map({
    container: conteneur, style: FOND, center: [2.34, 48.86], zoom: 11, maxZoom: 19,
    customAttribution: "© IGN, © DGFiP / Etalab (cadastre)",
  });
  carte.addControl(new maplibregl.NavigationControl({ showCompass: false }));
  carte.marqueur = new maplibregl.Marker({ color: "#2780e3" });
  carte.etat = { survol: null, section: null };
  ajouterLegende(conteneur);
  await new Promise((resolve) => carte.on("load", resolve));

  // Tuiles vectorielles du cadastre ; promoteId fait de la propriété `id` l'identifiant
  // des objets, ce qui permet d'y attacher un état (survol, sélection, prix)
  carte.addSource("cadastre", {
    type: "vector", url: URL_CADASTRE, promoteId: { sections: "id", parcelles: "id" },
  });
  const surDepartements = ["in", ["slice", ["get", "commune"], 0, 2], ["literal", DEPARTEMENTS]];
  const etat = (nom) => ["boolean", ["feature-state", nom], false];

  // Sections : remplissage invisible (pour le survol et le clic), contour et code
  carte.addLayer({
    id: "sections-fill", type: "fill", source: "cadastre", "source-layer": "sections",
    minzoom: 11, filter: surDepartements,
    paint: {
      "fill-color": "#2780e3",
      "fill-opacity": ["case", etat("selection"), 0.2, etat("survol"), 0.12, 0],
    },
  });
  carte.addLayer({
    id: "sections-line", type: "line", source: "cadastre", "source-layer": "sections",
    minzoom: 11, filter: surDepartements,
    paint: {
      "line-color": ["case", etat("selection"), "#1a5fb4", "#5b7a99"],
      "line-width": ["case", etat("selection"), 3, 1],
    },
  });
  carte.addLayer({
    id: "sections-label", type: "symbol", source: "cadastre", "source-layer": "sections",
    minzoom: 13, filter: surDepartements,
    layout: { "text-field": ["get", "code"], "text-font": POLICE, "text-size": 13 },
    paint: { "text-color": "#1a5fb4", "text-halo-color": "#fff", "text-halo-width": 1.5 },
  });

  // Parcelles : seulement celles de la section sélectionnée (filtre mis à jour à la sélection).
  // Elles sont colorées par leur prix médian si elles ont reçu un état `prix`.
  const aucune = ["==", ["get", "id"], ""];
  const prix = ["to-number", ["coalesce", ["feature-state", "prix"], -1]];
  const echelle = ["interpolate", ["linear"], prix, ...ECHELLE.flat()];
  carte.addLayer({
    id: "parcelles-fill", type: "fill", source: "cadastre", "source-layer": "parcelles",
    minzoom: ZOOM_PARCELLES, filter: aucune,
    paint: { "fill-color": ["case", [">", prix, 0], echelle, "rgba(0,0,0,0)"], "fill-opacity": 0.8 },
  });
  carte.addLayer({
    id: "parcelles-line", type: "line", source: "cadastre", "source-layer": "parcelles",
    minzoom: ZOOM_PARCELLES, filter: aucune, paint: { "line-color": "#666", "line-width": 0.6 },
  });
  carte.addLayer({
    id: "parcelle-choisie", type: "line", source: "cadastre", "source-layer": "parcelles",
    minzoom: ZOOM_PARCELLES, filter: aucune, paint: { "line-color": "#000", "line-width": 3 },
  });

  // Survol d'une section
  carte.on("mousemove", "sections-fill", (e) => {
    carte.getCanvas().style.cursor = "pointer";
    const id = e.features[0].id;
    if (carte.etat.survol === id) return;
    changerEtat(carte, "survol", id);
  });
  carte.on("mouseleave", "sections-fill", () => {
    carte.getCanvas().style.cursor = "";
    changerEtat(carte, "survol", null);
  });

  // Clic : une parcelle de la section sélectionnée sinon une section
  carte.on("click", (e) => {
    const parcelle = carte.queryRenderedFeatures(e.point, { layers: ["parcelles-fill"] })[0];
    if (parcelle) {
      carte.setFilter("parcelle-choisie", ["==", ["get", "id"], parcelle.id]);
      surParcelle(parcelle.id);
      return;
    }
    const section = carte.queryRenderedFeatures(e.point, { layers: ["sections-fill"] })[0];
    if (section) choisirSection(carte, section.id, surSection);
  });
  carte.surSection = surSection;
  return carte;
}

// Pose ou retire (id = null) l'état booléen `nom` (survol, selection) sur une section
function changerEtat(carte, nom, id) {
  const cle = nom === "survol" ? "survol" : "section";
  const source = { source: "cadastre", sourceLayer: "sections" };
  if (carte.etat[cle] !== null) carte.setFeatureState({ ...source, id: carte.etat[cle] }, { [nom]: false });
  if (id !== null) carte.setFeatureState({ ...source, id }, { [nom]: true });
  carte.etat[cle] = id;
}

// Sélectionne une section : surbrillance, zoom, et affichage de ses parcelles seules.
// L'emprise est calculée sur les morceaux de la section présents dans les tuiles chargées.
function choisirSection(carte, id, surSection) {
  changerEtat(carte, "selection", id);
  const filtre = ["==", ["slice", ["get", "id"], 0, 10], id];
  carte.setFilter("parcelles-fill", filtre);
  carte.setFilter("parcelles-line", filtre);
  carte.setFilter("parcelle-choisie", ["==", ["get", "id"], ""]);
  const morceaux = carte.queryRenderedFeatures({ layers: ["sections-fill"] }).filter((f) => f.id === id);
  if (morceaux.length) {
    carte.fitBounds(emprise(morceaux.map((f) => f.geometry)), { padding: 60, maxZoom: 17 });
  }
  surSection(id);
}

// Associe à chaque parcelle de la section son prix médian (efface les précédents)
export function colorerParcelles(carte, medianes) {
  carte.removeFeatureState({ source: "cadastre", sourceLayer: "parcelles" });
  for (const { id_parcelle, mediane } of medianes) {
    carte.setFeatureState(
      { source: "cadastre", sourceLayer: "parcelles", id: id_parcelle },
      { prix: mediane }
    );
  }
}

// Retire la surbrillance de la parcelle choisie (fermeture du bandeau)
export function deselectionnerParcelle(carte) {
  carte.setFilter("parcelle-choisie", ["==", ["get", "id"], ""]);
}

// Place le marqueur et centre la carte dessus
export function placerMarqueur(carte, lon, lat) {
  carte.marqueur.setLngLat([lon, lat]).addTo(carte);
}

// Va à une adresse : zoom, puis sélection de la section située au centre de la carte
export function allerA(carte, lon, lat) {
  placerMarqueur(carte, lon, lat);
  carte.once("moveend", () => {
    const section = carte.queryRenderedFeatures(carte.project([lon, lat]), { layers: ["sections-fill"] })[0];
    if (section) choisirSection(carte, section.id, carte.surSection);
  });
  carte.flyTo({ center: [lon, lat], zoom: 16 });
}
