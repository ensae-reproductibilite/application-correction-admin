// Visualisations. `Plot` (Observable Plot) est passé en argument depuis la page.

const euros = (x) => Math.round(x).toLocaleString("fr-FR");

// Histogramme des prix au m² d'une commune, avec le prix estimé en trait vertical
export function histogrammePrix(Plot, prix, prixEstime, nomCommune) {
  return Plot.plot({
    title: `Prix au m² des ventes à ${nomCommune}`,
    width: 640,
    height: 300,
    x: { label: "Prix au m² (€)" },
    y: { label: "Nombre de ventes" },
    marks: [
      Plot.rectY(prix, Plot.binX({ y: "count" }, { x: (d) => d, fill: "#9ecae1", thresholds: 30 })),
      Plot.ruleX([prixEstime], { stroke: "#bd0026", strokeWidth: 2 }),
      Plot.text([prixEstime], { x: (d) => d, text: () => "estimation", frameAnchor: "top", dy: -8, fill: "#bd0026" }),
      Plot.ruleY([0]),
    ],
  });
}

// Tableau des ventes d'une parcelle
export function tableVentes(idParcelle, ventes) {
  const div = document.createElement("div");
  const lignes = ventes.map((v) => `<tr><td>${v.date_mutation}</td><td>${v.type_local}</td>
    <td>${v.surface} m²</td><td>${v.pieces} p.</td><td>${euros(v.valeur)} €</td>
    <td>${euros(v.prix_m2)} €/m²</td></tr>`).join("");
  div.innerHTML = ventes.length
    ? `<p><strong>Parcelle ${idParcelle}</strong> : ${ventes.length} vente(s) en 2022</p>
       <table class="table table-sm"><tbody>${lignes}</tbody></table>`
    : `<p>Parcelle ${idParcelle} : aucune vente.</p>`;
  return div;
}
