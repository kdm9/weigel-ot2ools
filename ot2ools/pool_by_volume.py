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

Well = namedtuple("Well", ["plate", "well", "volume", "pool"])

def generate_protocols(wells, outdir, stock_pipette, min_volume, max_volume):
    if not outdir.is_dir():
        outdir.mkdir()

    pools = []
    plates = defaultdict(dict)
    for well in tqdm(wells):
        if well.volume < 0.01:
            print("SKIP empty well", well)
            continue
        if well.volume < min_volume:
            ValueError("Volume too small {well.plate}/{well.well}")
        if well.pool not in pools:
            pools.append(well.pool)
        plates[well.plate][well.well] = {
            "volume": well.volume,
            "pool": well.pool,
        }
    
    wells24 = [f"{y}{x}" for x in range(1, 7) for y in "ABCD"]
    if len(pools) > len(wells24):
        raise ValueError("Too many pools :(")
    pools = {k: v for v, k in zip(wells24, pools)}

    pool_vols = defaultdict(int)
    for plate in plates:
        for well in plates[plate]:
            pool_vols[plates[plate][well]["pool"]] += plates[plate][well]["volume"]
    for pool, vol in pool_vols.items():
        if vol > max_volume:
            ValueError("Overfull pool {pool}: {vol}")

    for batch in batched(plates, n=5):
        name = "__".join(batch)
        dat = {k: plates[k] for k in batch}
        script = template_script({
            "PLATES": dat,
            "POOL_POSITIONS": pools,
            "PROTOCOL_NAME": name,
            "STOCK_PIPETTE": stock_pipette,
        }, script=TEMPLATE_SCRIPT)
        with open(outdir / f"{name}.ot2.py", 'w') as fh:
            fh.write(script)
    print("PLEASE NOTE THE FOLLOWING DOWN!!!\n")
    print("Here are the mappings between the 'well' in the tube rack and your\n"
          "pool. This information is annoying to recover so write it down\n"
          "now.\n\n"
    )
    for pool, well in pools.items():
        print(f"  {pool} in {well}")


def read_instructions(args):
    dialect = "excel" if args.instructions.endswith(".csv") else "excel-tab"
    with open(args.instructions) as fh:
        for row in csv.DictReader(fh, dialect=dialect):
            try:
                yield Well(
                        plate=row[args.plate_column],
                        well=re.sub(r"([A-H])0(\d)", r"\1\2", row[args.well_column]),
                        volume=floatna(row[args.volume_column]),
                        pool=row[args.pool_column],
                    )
            except KeyError as exc:
                print(f"ERROR: column not found in file: {str(exc)}", file=stderr)
                print(f"you asked for: {args.plate_column}, {args.well_column}, {args.volume_column}, {args.pool_column}", file=stderr)
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
    ap.add_argument("-M", "--max-volume", type=float, default=2000,
            help="Maximum volume of destination well (combination of water+stock)")
    ap.add_argument("--pc", "--plate-column", dest="plate_column", type=str, default="plate",
            help="Column name for plate")
    ap.add_argument("--wc", "--well-column", dest="well_column", type=str, default="well",
            help="Column name for well")
    ap.add_argument("--vc", "--volume-column", dest="volume_column", type=str, default="volume",
            help="Column name for water volume")
    ap.add_argument("--lc", "--pool-column", dest="pool_column", type=str, default="pool",
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
pool_positions = __POOL_POSITIONS__
stock_pipette = "__STOCK_PIPETTE__"
metadata = {
        'protocolName': "__PROTOCOL_NAME__",
        'author': 'Kevin Murray',
        'apiLevel': '2.20',
}

def dispense(srcwell, dstwell, volume, pipette):
    if volume < pipette.min_volume:
        raise ValueError(f"Volume too small {dstwell} {volume}uL")
    if volume > 200:
        raise ValueError(f"ERROR! overfull well {dstwell} on plate {plate}")
    transferred = 0
    while transferred < volume:
        todo = volume-transferred
        if pipette.max_volume < todo < 1.9*pipette.max_volume:
            vol = todo/2
        else:
            vol = min(todo, pipette.max_volume)
        pipette.aspirate(vol, srcwell, rate=0.4)
        pipette.dispense(vol, dstwell.top(), rate=0.5)
        pipette.blow_out(dstwell.top())
        transferred += vol

def run(protocol: protocol_api.ProtocolContext):
    tipracks = []
    dest_tubes = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 11, label="Pool Tubes (2mL bullet eppie)")

    tips = 'standard_96_tiprack_10ul' if stock_pipette == "p10" else 'standard_96_tiprack_200ul'
    for i in range(len(plates)):
        tipracks.append(protocol.load_labware(tips, 10-i))

    if stock_pipette == "p10":
        pipette = protocol.load_instrument('p10_single', 'right', tip_racks=tipracks)
    else:
        pipette = protocol.load_instrument('p50_single', 'left', tip_racks=tipracks)

    pos = 1
    srcs = {}
    for plate_name in plates:
        srcs[plate_name] = protocol.load_labware('axygen_96_wellplate_200ul', pos, label=f"STOCK {plate_name}")
        pos += 1

    for plate_name, wellvols in plates.items():
        src = srcs[plate_name]

        # Stocks
        for well, dat in wellvols.items():
            if dat["volume"] < 0.01:
                continue
            dstwell = dest_tubes[pool_positions[dat["pool"]]]
            pipette.pick_up_tip()
            dispense(src[well], dstwell, dat["volume"], pipette)
            pipette.touch_tip(dstwell)
            pipette.drop_tip()
"""

if __name__ == "__main__":
    main()
