"""
Data retrieval functions
"""

from pathlib import Path

import pandas as pd
import requests


def download_sources(url_fichier: str, cible: Path) -> None:
    """Download url_fichier and write it to cible"""
    r = requests.get(url_fichier, timeout=120)
    r.raise_for_status()
    with open(cible, "wb") as f:
        f.write(r.content)


def get_melodi_indicator(
    code: str,
    value_name: str,
    jeton_api: str,
    dataset: str = "DS_FILOSOFI_CC",
    dimension: str = "FILOSOFI_MEASURE",
    time_period: int = 2023,
    geo_level: tuple[str, ...] = ("COM", "ARM"),
) -> pd.DataFrame:
    """Fetch a municipality-level indicator from the Insee Melodi API

    DVF codes Paris by arrondissement (75101 to 75120), not as one municipality
    (75056): without the ARM level, Paris sales would get no municipality data.
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
