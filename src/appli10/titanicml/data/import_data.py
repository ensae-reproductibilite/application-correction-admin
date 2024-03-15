import os
import yaml


def import_yaml_config(filename: str = "toto.yaml") -> dict:
    """Import configuration from YAML file

    Args:
        filename (str, optional): _description_. Defaults to "toto.yaml".

    Returns:
        dict: _description_
    """
    dict_config = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as stream:
            dict_config = yaml.safe_load(stream)
    return dict_config
