import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Union, Iterable, Set

from json import JSONDecodeError

PathLike = Union[str, Path]
RPKI_OBJTYPES = ["roas", "aspas", "bgpsec_keys"]


def read_lines(filename: PathLike) -> Set[str]:
    try:
        with open(filename) as f:
            return {line.strip() for line in f}
    except FileNotFoundError:
        return set()


def write_lines(data: Iterable[str], filename: PathLike):
    with open(filename, "w") as f:
        f.write("\n".join(data) + "\n")


def write_metrics(metrics: dict, filename: PathLike):
    with open(filename, "w") as f:
        for metric_name, count in metrics.items():
            f.write(f"# HELP {metric_name} {help_from_metric_name(metric_name)}\n"
                    f"# TYPE {metric_name} counter\n"
                    f"{metric_name} {count}\n\n")


def help_from_metric_name(metric_name: str) -> str:
    if any(metric_name.startswith(count_type) for count_type in ["union", "intersection", "consensus"]):
        count_type, obj_type = metric_name.split("_", maxsplit=1)
        return f"Number of {obj_type} in {count_type} of nodes"
    else:
        return f"Number of {metric_name} seen by this node"


def read_json(filename: PathLike) -> dict:
    try:
        with open(filename) as f:
            return json.load(f)
    except FileNotFoundError:
        log(__file__, f"warning: {filename} not found, resetting to empty")
        return {}
    except JSONDecodeError as e:
        log(__file__, f"warning: parsing {filename} failed, resetting to empty - {e}")
        return {}


def write_json(data: Union[dict, list], filename: PathLike):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def log(src: str, text: str):
    text = text.replace("\n", "\\n")
    print(f"{datetime.now().isoformat()}\t{src}\t{text}")


def get_host_ip() -> str:
    return subprocess.check_output(["hostname", "-i"], text=True).strip()
