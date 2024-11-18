#!/usr/bin/env python3
#  Copyright Kevin Murray <foss@kdmurray.id.au> 2024
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import csv
from sys import stderr, stdout, stdin, exit
import argparse
import re
from pathlib import Path
from collections import defaultdict, namedtuple
from ._utils import *
try:
    from tqdm.auto import tqdm
except ImportError:
    def tqdm(i, *args, **kwargs):
        yield from i

def generate_protocols(wells, outdir, stock_pipette, min_volume, max_volume):
    if not outdir.is_dir():
        outdir.mkdir()

    plates = defaultdict(dict)
    for well in tqdm(wells):
        if well.stock_vol + well.water_vol < 1:
            print("SKIP empty well", well)
            continue
        if (well.stock_vol + well.water_vol) > max_volume:
            ValueError("Overfull well {well.plate}/{well.well}")
        if well.water_vol < min_volume or well.stock_vol < min_volume:
            ValueError("Volume too small {well.plate}/{well.well}")
        plates[well.plate][well.well] = {
            "water": well.water_vol,
            "stock": well.stock_vol,
        }


    for batch in batched(plates, n=3):
        name = "__".join(batch)
        dat = {k: plates[k] for k in batch}
        script = template_script({
            "PLATES": dat,
            "PROTOCOL_NAME": name,
            "STOCK_PIPETTE": stock_pipette,
        }, script=TEMPLATE_SCRIPT)
        with open(outdir / f"{name}.ot2.py", 'w') as fh:
            fh.write(script)

def read_instructions(args):
    dialect = "excel" if args.instructions.endswith(".csv") else "excel-tab"
    with open(args.instructions) as fh:
        for row in csv.DictReader(fh, dialect=dialect):
            try:
                yield Well(
                        plate=row[args.plate_column],
                        well=re.sub(r"([A-H])0(\d)", r"\1\2", row[args.well_column]),
                        water_vol=floatna(row[args.water_column]),
                        stock_vol=floatna(row[args.stock_column]),
                    )
            except KeyError as exc:
                print(f"ERROR: column not found in file: {str(exc)}", file=stderr)
                print(f"you asked for: {args.plate_column}, {args.well_column}, {args.water_column}, {args.stock_column}", file=stderr)
                print(f"instructions file has: {', '.join(list(row.keys()))}", file=stderr)
                exit(1)

def main(argv=None):
    """Pipette variable amounts of diluent and stock between plates, in batches of 3 plates"""
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--protocol-script-dir", type=Path, default=Path("."),
            help="Output dir")
    ap.add_argument("-p", "--stock-pipette", choices=["p10", "p50"], default="p10",
            help="Which pipette to use for stock pipetting")
    ap.add_argument("-m", "--min-volume", type=float, default=1,
            help="Minimum volume to transfer")
    ap.add_argument("-M", "--max-volume", type=float, default=200,
            help="Maximum volume of destination well (combination of water+stock)")
    ap.add_argument("--pc", "--plate-column", dest="plate_column", type=str, default="plate",
            help="Column name for plate")
    ap.add_argument("--wc", "--well-column", dest="well_column", type=str, default="well",
            help="Column name for well")
    ap.add_argument("--hc", "--water-column", dest="water_column", type=str, default="water_vol",
            help="Column name for water volume")
    ap.add_argument("--sc", "--stock-column", dest="stock_column", type=str, default="stock_vol",
            help="Column name for stock volume")
    ap.add_argument("instructions",
            help="Instructions file csv")
    args = ap.parse_args(argv)

    generate_protocols(
        read_instructions(args),
        args.protocol_script_dir,
        args.stock_pipette,
        args.min_volume,
        args.max_volume,
    )
        

TEMPLATE_SCRIPT="""
from opentrons import protocol_api
plates = __PLATES__
stock_pipette = "__STOCK_PIPETTE__"
metadata = {
        'protocolName': "__PROTOCOL_NAME__",
        'author': 'Kevin Murray',
        'apiLevel': '2.9',
}

def dispense(srcwell, dstwell, volume, pipette):
    if volume < pipette.min_volume:
        raise ValueError(f"Volume too small {dstwell} {volume}uL")
    if volume > 200:
        raise ValueError(f"ERROR! overfull well {dstwell} on plate {plate}")
    transferred = 0
    while transferred < volume:
        vol = min(volume-transferred, pipette.max_volume)
        pipette.aspirate(vol, srcwell, rate=0.4)
        pipette.dispense(vol, dstwell, rate=0.5)
        pipette.blow_out(dstwell)
        pipette.touch_tip(dstwell)
        transferred += vol

def run(protocol: protocol_api.ProtocolContext):
    water = protocol.load_labware('integra_1_reservoir_150ml', 11)

    tipracks = {"p10": [], "p50": []}
    # for the water
    tipracks["p50"].append(protocol.load_labware('standard_96_tiprack_200ul', 10))

    labware = 'standard_96_tiprack_10ul' if stock_pipette == "p10" else 'standard_96_tiprack_200ul'
    for i, _ in enumerate(plates):
        tipracks[stock_pipette].append(protocol.load_labware(labware, 9-i))
    pipettes = {
        "p50": protocol.load_instrument('p50_single', 'left', tip_racks=tipracks["p50"])
    }
    if stock_pipette == "p10":
        pipettes["p10"] = protocol.load_instrument('p10_single', 'right', tip_racks=tipracks["p10"])

    pos = 1
    srcs = {}
    dests = {}
    for plate_name in plates:
        srcs[plate_name] = protocol.load_labware('axygen_96_wellplate_200ul', pos, label=f"STOCK {plate_name}")
        dests[plate_name] = protocol.load_labware('axygen_96_wellplate_200ul', pos+1, label=f"DILUTED {plate_name}")
        pos += 2

    for plate_name, wellvols in plates.items():
        src = srcs[plate_name]
        dst = dests[plate_name]

        # Waters
        pipette = pipettes["p50"]
        pipette.pick_up_tip()
        for well, vols in wellvols.items():
            if vols["water"] < 0.01:
                continue
            dispense(water["A1"], dst[well], vols["water"], pipette)
        pipette.drop_tip()

        # Stocks
        pipette = pipettes[stock_pipette]
        for well, vols in wellvols.items():
            if vols["stock"] < 0.01:
                continue
            pipette.pick_up_tip()
            dispense(src[well], dst[well], vols["stock"], pipette)
            pipette.drop_tip()
"""

if __name__ == "__main__":
    main()
