#!/usr/bin/env python3
import re
from argparse import Namespace, ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


def main(logs: Dict[str, List[str]]):
    vrp_growth = parse_vrp_growth(logs)
    plot_vrp_growth(vrp_growth)

# TODO TAL info:
# TODO - repo sync duration


def parse_vrp_growth(logs: Dict[str, List[str]]) -> dict:
    data = {name: {"sync": {}, "agg": {}, "master": {}} for name in logs.keys()}
    current_tal, current_vrp_results = "", {}
    global_start = datetime.fromtimestamp(0)

    for name, log in logs.items():
        for line in log:
            match = re.match("([0-9T:.-]+)\s+/app/peering\.py\s+running", line)
            if match:
                global_start = max(global_start, datetime.fromisoformat(match.group(1)))
                continue

            match = re.match("([0-9T:.-]+)\s+/app/monitored_rp\.py\s+updated [^(]+ \(([0-9]+) unique entries from [0-9]+ TALs\)", line)
            if match:
                timestamp = datetime.fromisoformat(match.group(1))
                data[name]["sync"][timestamp] = int(match.group(2))
                continue

            match = re.match("([0-9T:.-]+)\s+/app/peering\.py\s+updated master VRP \(found ([0-9]+) unique entries among peers, ([0-9]+) with [0-9]+\+ votes\)", line)
            if match:
                timestamp = datetime.fromisoformat(match.group(1))
                data[name]["agg"][timestamp] = int(match.group(2))
                data[name]["master"][timestamp] = int(match.group(3))
                continue

    for name in logs.keys():
        for vrp_name in ("sync", "agg", "master"):
            data[name][vrp_name][global_start] = 0
    return data


def plot_vrp_growth(data: dict):
    colors = {"sync": "#555c9d", "agg": "#ff8c78", "master": "#842c61"}
    for name, vrps in list(data.items()):
        for vrp_name, timeline in vrps.items():
            t, n_entries = zip(*sorted(timeline.items()))
            plt.plot(t, n_entries, color=colors[vrp_name])

    patches = [mpatches.Patch(color=color, label=vrp_name) for vrp_name, color in colors.items()]
    plt.legend(handles=patches)
    # plt.title("VRP Growth by VRP Type and Container")
    plt.xlabel("time")
    plt.ylabel("# VRP entries")
    plt.grid(axis="y", color="gainsboro")
    plt.gca().set_axisbelow(True)
    plt.tight_layout()
    plt.savefig("vrp_growth.pdf")


def parse_args() -> Namespace:
    parser = ArgumentParser(description="evaluate byz-rpki logs")
    parser.add_argument("logs", metavar="FILE", nargs="+", type=Path, help="docker logs output per container")
    return parser.parse_args()


def read_lines(filename: Path) -> List[str]:
    try:
        with open(filename) as f:
            return [line.strip() for line in f]
    except FileNotFoundError:
        return []


if __name__ == '__main__':
    args = parse_args()
    main({file.name.rstrip(file.suffix): read_lines(file) for file in args.logs})
