#!/usr/bin/env python3
#  Copyright Kevin Murray <foss@kdmurray.id.au> 2024
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

#!/usr/bin/env python3
import json
import csv
import argparse
import re
from pathlib import Path
from ._utils import *
try:
    from tqdm.auto import tqdm
except ImportError:
    def tqdm(i, *args, **kwargs):
        yield from i

Well = namedtuple("Well", ["plate_name", "well", "conc"])


def read_instructions(args):
    dialect = "excel" if args.instructions.endswith(".csv") else "excel-tab"
    with open(args.instructions) as fh:
        for row in csv.DictReader(fh, dialect=dialect):
            try:
                yield Well(
                        plate_name=row[args.plate_column],
                        well=re.sub(r"([A-H])0(\d)", r"\1\2", row[args.well_column]),
                        conc=floatna(row[args.conc_column]),
                    )
            except KeyError as exc:
                print(f"ERROR: column not found in file: {str(exc)}", file=stderr)
                print(f"you asked for: {args.plate_column}, {args.well_column}, {args.conc_column}", file=stderr)
                print(f"instructions file has: {', '.join(list(row.keys()))}", file=stderr)
                exit(1)


def main(argv=None):
    """Pipette variable amounts of diluent into plates, ready to add a constant stock volume."""
    ap = argparse.ArgumentParser()
    ap.add_argument("-b", "--batchsize", default=9, type=int,
            help="Number of plates per batch")
    ap.add_argument("-o", "--protocol-script-dir", type=Path, default=Path("protocols"),
            help="Output dir")
    ap.add_argument("-c", "--target-conc", default=5, type=float,
            help="Target concentration in ng/uL")
    ap.add_argument("-v", "--volume", default=10, type=float,
            help="Constant volume of source DNA to transfer (uL)")
    ap.add_argument("-m", "--min-volume", type=float, default=5,
            help="Minimum volume to transfer")
    ap.add_argument("-M", "--max-volume", type=float, default=200,
            help="Maximum volume of destination well (combination of water+stock)")
    ap.add_argument("-t", "--summary-table", type=argparse.FileType("w"), required=True,
            help="Summary of actions table (tsv)")
    ap.add_argument("--pc", "--plate-column", dest="plate_column", type=str, default="plate_name",
            help="Column name for plate")
    ap.add_argument("--wc", "--well-column", dest="well_column", type=str, default="well",
            help="Column name for well")
    ap.add_argument("--cc", "--conc-column", dest="conc_column", type=str, default="conc",
            help="Column name for water volume")
    ap.add_argument("instructions",
            help="Instructions file csv")
    args = ap.parse_args(argv)

    if not args.protocol_script_dir.is_dir():
         args.protocol_script_dir.mkdir()

    plate_pos = {}
    data = {}
    print("plate", "well", "status", "stock_conc", "diluent_vol", "final_vol", "final_conc", sep="\t", file=args.summary_table)
    for well in tqdm(read_instructions(args)):
        if well.plate_name not in data:
            data[well.plate_name] = {}
        final_vol = well.conc/args.target_conc * args.volume
        tfr_vol = final_vol - args.volume
        if well.conc < args.target_conc:
            tfr_vol = 0
            status = "conc below target"
        elif tfr_vol < args.min_volume:
            tfr_vol = 0
            status = "transfer too small"
        elif tfr_vol > args.max_volume:
            tfr_vol = args.max_volume
            status = "transfer too large"
        else:
            status = "OK"
        final_vol = args.volume + tfr_vol
        final_conc = well.conc * (args.volume/final_vol)
        well_no0 = re.sub(r"([A-H])0(\d)", r"\1\2", well.well)
        print(well.plate_name, well_no0, status, R(well.conc), R(tfr_vol, 1), R(final_vol), R(final_conc), sep="\t", file=args.summary_table)
        data[well.plate_name][well_no0] = R(tfr_vol, 1)

    for plates in batched(data, n=args.batchsize):
        name = "__".join(plates)
        #name = f"{name}__stockvol={args.volume}"
        dat = {p: data[p] for p in plates}
        script = template_script({
            "PLATES": dat,
            "NPLATES": len(dat),
            "STOCKVOLUME": args.volume,
            "WELL_MAX_VOLUME": args.max_volume,
            "PROTOCOL_NAME": name,
        }, script=TEMPLATE_SCRIPT)
        with open(args.protocol_script_dir / f"{name}.ot2.py", 'w') as fh:
            fh.write(script)

TEMPLATE_SCRIPT = """\
from opentrons import protocol_api

config = {
    "PLATES": __PLATES__,
    "WELL_MAX_VOLUME": __WELL_MAX_VOLUME__,
}

metadata = {
        'protocolName': "__PROTOCOL_NAME__",
        'description': "Constant volume dilution for __NPLATES__ plates, using __STOCKVOLUME__ uL of stock DNA.",
        'author': 'Kevin Murray',
        'apiLevel': '2.9',
}

def dispense_water_to(plate, water, well_vols, pipette):
    pipette.pick_up_tip()
    for well, volume in well_vols.items():
        if volume < pipette.min_volume:
            continue
        if volume > config["WELL_MAX_VOLUME"]:
            raise ValueError(f"ERROR! overfull well {well} on plate {plate}")
        transferred = 0
        while transferred < volume:
            todo = volume-transferred
            if todo > pipette.max_volume and todo <= pipette.max_volume*2:
                vol = todo/2
            else:
                vol = min(todo, pipette.max_volume)
            pipette.aspirate(vol, water["A1"], rate=1)
            pipette.dispense(vol, plate[well], rate=1)
            transferred += vol
        pipette.blow_out(plate[well])
        pipette.touch_tip(plate[well])
    pipette.drop_tip()


def run(protocol: protocol_api.ProtocolContext):
    water = protocol.load_labware('integra_1_reservoir_150ml', 11)

    tiprack_p200 = protocol.load_labware('standard_96_tiprack_200ul', 10)
    p50 = protocol.load_instrument('p50_single', 'left', tip_racks=[tiprack_p200])
    p50.well_bottom_clearance.aspirate = 0
    p50.well_bottom_clearance.dispense = 0

    pos = 1
    for plate_name, well_vols in config["PLATES"].items():
        dest_plate = protocol.load_labware('axygen_96_wellplate_200ul', pos, label=plate_name)
        dispense_water_to(dest_plate, water, well_vols, p50)
        pos += 1
"""


if __name__ == "__main__":
    main()
