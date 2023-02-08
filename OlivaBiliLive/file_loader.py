import OlivOS
import OlivaBiliLive

from pathlib import Path
from genericpath import exists
import yaml

DEFAULT_CONFIG_YML = {
    'debug': False,
    'roomid': 21752074
}

def logg(msg:str,level=2):
    OlivaBiliLive.main.GlobalProc.log(level,f"[OlivaBiliLive] : {msg}")
    
def make_folder(folder: str) -> bool:
    path = Path(folder)
    if path.exists():
        return False
    path.mkdir(exist_ok=True, parents=True)
    return True


def load_config(yml: str, default_values: dict) -> any:
    make_folder('plugin/conf/OlivaBiliLive/config')
    path = f'plugin/conf/OlivaBiliLive/config/{yml}'
    data = {}
    if exists(path):
        with open(path, mode='r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    for (k, v) in data.items():
        default_values[k] = v
    if default_values.keys() != data.keys():
        with open(path, mode='w', encoding='utf-8') as f:
            yaml.safe_dump(default_values, f, allow_unicode=True)
    return default_values

def load_default_config() -> any:
    return load_config('config.yaml', DEFAULT_CONFIG_YML)