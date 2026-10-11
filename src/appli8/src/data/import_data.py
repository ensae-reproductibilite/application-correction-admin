"""
Fonctions de récupération des données
"""

import pandas as pd
import requests


def get_melodi_indicator(
    code: str,
    value_name: str,
    jeton_api: str,
    dataset: str = "DS_FILOSOFI_CC",
    dimension: str = "FILOSOFI_MEASURE",
    time_period: int = 2023,
    geo_level: tuple[str, ...] = ("COM", "ARM"),
) -> pd.DataFrame:
    """Récupère un indicateur communal depuis l'API Melodi de l'Insee

    Dans DVF, Paris est codé par arrondissement (75101 à 75120) : avec le seul
    niveau COM (Paris = 75056), toutes les ventes parisiennes perdraient leurs
    variables communales. On demande donc aussi, par défaut, le niveau ARM.
    """

    url = f"https://api.insee.fr/melodi/data/{dataset}"

    params = {
        "GEO": list(geo_level),
        dimension: code,
        "TIME_PERIOD": time_period,
        "maxResult": 40000,
    }

    headers = {"Authorization": f"Bearer {jeton_api}"}

    response = requests.get(url, params=params, headers=headers, timeout=60)
    response.raise_for_status()
    observations = response.json()["observations"]

    return pd.DataFrame(
        {
            "CODGEO": obs["dimensions"]["GEO"].split("-")[-1],
            value_name: obs["measures"]["OBS_VALUE_NIVEAU"].get("value"),
        }
        for obs in observations
    )
