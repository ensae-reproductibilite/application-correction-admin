// Rendu de la carte avec MapLibre GL JS. Aucune donnée n'est téléchargée ici :
// les fonctions reçoivent les données en arguments et renvoient les clics par des callbacks.

const MAPLIBRE = "https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist";
const URL_CADASTRE = "https://openmaptiles.geo.data.gouv.fr/data/cadastre.json";
const ZOOM_PARCELLES = 14; // à partir de ce zoom, un clic désigne un point, plus une commune

// Échelle de couleurs commune aux communes et aux parcelles (€/m²)
const ECHELLE = [
  [3000, "#ffffb2"], [5000, "#fecc5c"], [7000, "#fd8d3c"], [10000, "#f03b20"], [14000, "#bd0026"],
];
const interpolation = (valeur) => ["interpolate", ["linear"], valeur, ...ECHELLE.flat()];

// Charge MapLibre (script UMD + feuille de style) une seule fois
function chargerMaplibre() {
  if (window.maplibregl) return Promise.resolve(window.maplibregl);
  const css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = `${MAPLIBRE}/maplibre-gl.css`;
  document.head.append(css);
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `${MAPLIBRE}/maplibre-gl.js`;
    script.onload = () => resolve(window.maplibregl);
    script.onerror = () => reject(new Error("Chargement de MapLibre impossible"));
    document.head.append(script);
  });
}

// Fond de carte clair (tuiles raster) sans clé d'API
const FOND = {
  version: 8,
  sources: {
    fond: {
      type: "raster",
      tiles: ["https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap, © CARTO",
    },
  },
  layers: [{ id: "fond", type: "raster", source: "fond" }],
};

function ajouterLegende(conteneur) {
  const legende = document.createElement("div");
  legende.className = "legende";
  const degrade = ECHELLE.map(([v, c]) => `${c} ${((v - 3000) / 11000) * 100}%`).join(", ");
  legende.innerHTML = `<strong>Prix médian (€/m²)</strong>
    <div class="degrade" style="background: linear-gradient(to right, ${degrade})"></div>
    <div class="bornes"><span>3 000</span><span>14 000</span></div>`;
  conteneur.append(legende);
}

// Emprise [[ouest, sud], [est, nord]] d'une géométrie GeoJSON
function emprise(geometrie) {
  const points = geometrie.coordinates.flat(geometrie.type === "MultiPolygon" ? 2 : 1);
  const lons = points.map((p) => p[0]), lats = points.map((p) => p[1]);
  return [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]];
}

// Crée la carte dans `conteneur`.
// Callbacks : surClic(lon, lat) pour un clic à fort zoom, surParcelle(idParcelle) pour une parcelle.
export async function creerCarte(conteneur, { surClic, surParcelle }) {
  const maplibregl = await chargerMaplibre();
  const carte = new maplibregl.Map({
    container: conteneur, style: FOND, center: [2.3488, 48.8534], zoom: 10, maxZoom: 19,
  });
  carte.addControl(new maplibregl.NavigationControl({ showCompass: false }));
  carte.marqueur = new maplibregl.Marker({ color: "#2780e3" });
  ajouterLegende(conteneur);
  await new Promise((resolve) => carte.on("load", resolve));

  // Parcelles cadastrales (tuiles vectorielles) : contour partout, remplissage coloré
  // seulement pour les parcelles ayant reçu un prix via setFeatureState
  carte.addSource("cadastre", { type: "vector", url: URL_CADASTRE, promoteId: { parcelles: "id" } });
  const prixParcelle = ["to-number", ["coalesce", ["feature-state", "prix"], -1]];
  carte.addLayer({
    id: "parcelles-fill", type: "fill", source: "cadastre", "source-layer": "parcelles",
    minzoom: ZOOM_PARCELLES - 1,
    paint: {
      "fill-color": ["case", [">", prixParcelle, 0], interpolation(prixParcelle), "rgba(0,0,0,0)"],
      "fill-opacity": 0.8,
    },
  });
  carte.addLayer({
    id: "parcelles-line", type: "line", source: "cadastre", "source-layer": "parcelles",
    minzoom: ZOOM_PARCELLES - 1, paint: { "line-color": "#666", "line-width": 0.5 },
  });

  const info = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
  carte.on("mousemove", "communes-fill", (e) => {
    const p = e.features[0].properties;
    const prix = p.prix_m2 ? `${Math.round(p.prix_m2).toLocaleString("fr-FR")} €/m² (${p.n} ventes)` : "pas de vente";
    info.setLngLat(e.lngLat).setHTML(`<strong>${p.NOM}</strong><br>${prix}`).addTo(carte);
  });
  carte.on("mouseleave", "communes-fill", () => info.remove());

  carte.on("click", (e) => {
    if (carte.getZoom() >= ZOOM_PARCELLES) {
      surClic(e.lngLat.lng, e.lngLat.lat);
      const parcelle = carte.queryRenderedFeatures(e.point, { layers: ["parcelles-fill"] })[0];
      if (parcelle) surParcelle(parcelle.properties.id);
    } else {
      // Zoom faible : le clic zoome sur la commune cliquée
      const commune = carte.queryRenderedFeatures(e.point, { layers: ["communes-fill"] })[0];
      if (commune) carte.fitBounds(emprise(commune.geometry), { padding: 40, maxZoom: ZOOM_PARCELLES });
    }
  });
  return carte;
}

// Choroplèthe des communes. `contours` contient déjà la propriété prix_m2.
export function afficherCommunes(carte, contours) {
  carte.addSource("communes", { type: "geojson", data: contours });
  const prix = ["to-number", ["get", "prix_m2"]];
  carte.addLayer({
    id: "communes-fill", type: "fill", source: "communes",
    paint: {
      "fill-color": ["case", ["!=", ["get", "prix_m2"], null], interpolation(prix), "#cccccc"],
      // La couche s'efface progressivement pour laisser voir les parcelles
      "fill-opacity": ["interpolate", ["linear"], ["zoom"], 12, 0.7, ZOOM_PARCELLES, 0.1],
    },
  }, "parcelles-fill");
  carte.addLayer({
    id: "communes-line", type: "line", source: "communes",
    paint: { "line-color": "#444", "line-width": 1 },
  });
}

// Associe à chaque parcelle son prix médian ; les tuiles s'en servent à l'affichage
export function colorerParcelles(carte, medianes) {
  for (const { id_parcelle, mediane } of medianes) {
    carte.setFeatureState(
      { source: "cadastre", sourceLayer: "parcelles", id: id_parcelle },
      { prix: mediane }
    );
  }
}

// Place le marqueur (adresse estimée ou point cliqué) et centre la carte dessus
export function placerMarqueur(carte, lon, lat) {
  carte.marqueur.setLngLat([lon, lat]).addTo(carte);
  carte.flyTo({ center: [lon, lat], zoom: Math.max(carte.getZoom(), ZOOM_PARCELLES) });
}
