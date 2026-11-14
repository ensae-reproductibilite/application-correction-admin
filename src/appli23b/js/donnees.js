// Accès aux données, exécuté dans le navigateur (aucun accès au DOM).
// DuckDB-WASM lit directement le fichier parquet DVF via HTTP : seules les
// colonnes et les lignes utiles sont téléchargées (requêtes "range").

const DUCKDB = "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0";
const URL_DVF =
  "https://minio.lab.sspcloud.fr/lgaliana/ensae-reproductibilite/data/raw/dvf.parquet";
const URL_CONTOURS = (dep) =>
  "https://minio.lab.sspcloud.fr/projet-cartiflette/production/provider=IGN/" +
  "dataset_family=ADMINEXPRESS/source=EXPRESS-COG-CARTO-TERRITOIRE/year=2022/" +
  `administrative_level=COMMUNE_ARRONDISSEMENT/crs=4326/DEPARTEMENT=${dep}/` +
  "vectorfile_format=geojson/territory=metropole/simplification=50/raw.geojson";
const DEPARTEMENTS = ["75", "92", "93", "94"];

// Démarre DuckDB-WASM, puis construit la table `ventes` (une ligne par ligne DVF).
// Le nettoyage reprend celui de l'entraînement (train.py et build_features.py) :
// ventes < 1 M€, prix au m² = valeur foncière / surface bâtie, puis suppression
// des 1 % de prix extrêmes les plus bas et les plus hauts (global puis par commune).
export async function chargerVentes() {
  const duckdb = await import(`${DUCKDB}/+esm`);
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  // Le worker doit être servi depuis la même origine : on passe par un blob
  const script = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" })
  );
  const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING), new Worker(script));
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  const conn = await db.connect();

  const deps = DEPARTEMENTS.map((d) => `'${d}'`).join(", ");
  await conn.query(`
    CREATE TABLE ventes AS
    WITH base AS (
      SELECT id_mutation, date_mutation, code_commune, nom_commune, id_parcelle,
             type_local, surface_reelle_bati AS surface,
             nombre_pieces_principales AS pieces, valeur_fonciere AS valeur,
             valeur_fonciere / surface_reelle_bati AS prix_m2
      FROM read_parquet('${URL_DVF}')
      WHERE code_departement IN (${deps})
        AND type_local IN ('Appartement', 'Maison')
        AND valeur_fonciere < 1e6 AND surface_reelle_bati > 0
    ),
    globale AS (
      SELECT * FROM base
      WHERE prix_m2 BETWEEN (SELECT quantile_cont(prix_m2, 0.01) FROM base)
                        AND (SELECT quantile_cont(prix_m2, 0.99) FROM base)
    ),
    bornes AS (
      SELECT *, quantile_cont(prix_m2, 0.01) OVER (PARTITION BY code_commune) AS bas,
                quantile_cont(prix_m2, 0.99) OVER (PARTITION BY code_commune) AS haut
      FROM globale
    )
    SELECT * EXCLUDE (bas, haut) FROM bornes WHERE prix_m2 BETWEEN bas AND haut
  `);
  return conn;
}

// Exécute une requête et renvoie un tableau d'objets JavaScript simples
async function requete(conn, sql) {
  const resultat = await conn.query(sql);
  return resultat.toArray().map((ligne) => ligne.toJSON());
}

// Les identifiants sont insérés dans le SQL : on n'accepte que lettres et chiffres
function sur(identifiant) {
  if (!/^[0-9A-Za-z]+$/.test(identifiant)) throw new Error("Identifiant invalide");
  return identifiant;
}

export async function nombreVentes(conn) {
  return (await requete(conn, "SELECT COUNT(*)::INTEGER AS n FROM ventes"))[0].n;
}

// Prix médian au m² et nombre de ventes par commune : [{code_commune, mediane, n}]
export function medianeParCommune(conn) {
  return requete(conn, `
    SELECT code_commune, median(prix_m2) AS mediane, COUNT(*)::INTEGER AS n
    FROM ventes GROUP BY code_commune`);
}

// Idem par parcelle : [{id_parcelle, mediane, n}] (pour une commune si précisée)
export function medianeParParcelle(conn, codeCommune = null) {
  const filtre = codeCommune ? `WHERE code_commune = '${sur(codeCommune)}'` : "";
  return requete(conn, `
    SELECT id_parcelle, median(prix_m2) AS mediane, COUNT(*)::INTEGER AS n
    FROM ventes ${filtre} GROUP BY id_parcelle`);
}

// Ventes d'une parcelle, de la plus récente à la plus ancienne
export function ventesDeParcelle(conn, idParcelle) {
  return requete(conn, `
    SELECT date_mutation, type_local, surface, pieces::INTEGER AS pieces, valeur, prix_m2
    FROM ventes WHERE id_parcelle = '${sur(idParcelle)}' ORDER BY date_mutation DESC`);
}

// Prix au m² de toutes les ventes d'une commune (pour un histogramme)
export async function prixDeCommune(conn, codeCommune) {
  const lignes = await requete(conn, `
    SELECT prix_m2 FROM ventes WHERE code_commune = '${sur(codeCommune)}'`);
  return lignes.map((l) => l.prix_m2);
}

// Contours des communes (Paris par arrondissement) : un fichier GeoJSON par département
export async function contoursCommunes() {
  const parts = await Promise.all(
    DEPARTEMENTS.map((dep) => fetch(URL_CONTOURS(dep)).then((r) => r.json()))
  );
  return { type: "FeatureCollection", features: parts.flatMap((p) => p.features) };
}

// Ajoute à chaque commune son prix médian (jointure INSEE_COG = code_commune)
export function joindrePrix(contours, medianes) {
  const parCode = new Map(medianes.map((m) => [m.code_commune, m]));
  const features = contours.features.map((f) => {
    const m = parCode.get(f.properties.INSEE_COG);
    return { ...f, properties: { ...f.properties, prix_m2: m?.mediane ?? null, n: m?.n ?? 0 } };
  });
  return { ...contours, features };
}
