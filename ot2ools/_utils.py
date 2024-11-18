#!/usr/bin/env python3
#  Copyright Kevin Murray <foss@kdmurray.id.au> 2024
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


import json
import re
from sys import stderr, stdout, stdin, exit
from pathlib import Path
from itertools import islice
from collections import defaultdict, namedtuple

def R(decimal, place=2):
    return round(decimal, place)

def template_script(jsondat, file=None, script=None):
    if script is None:
        with open(file) as fh:
            script = fh.read()
    for key, val in jsondat.items():
        needle = f"__{key}__"
        if isinstance(val, dict):
            val = json.dumps(val)
        script = re.sub(needle, str(val), script)
    return script

def floatna(s):
    try:
        return R(float(s))
    except Exception as exc:
        return float(0)

def batched(iterable, n=1):
    if n < 1:
        raise ValueError('n must be at least one')
    it = iter(iterable)
    while (batch := tuple(islice(it, n))):
        yield batch

Well = namedtuple("Well", ["plate", "well", "water_vol", "stock_vol"])


