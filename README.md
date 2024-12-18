# WeigelWorld Opentron2 duct-tape

These duct-tape scripts go between [tecanalyze](https://kdm9.shinyapps.io/tecanalyze)
and the opentron protocol language itself.

## Installation

tl;dr:

    python3 -m pip install weigel-ot2tools

To use these tools (CLI only for now), first install with `python3 -m pip
install weigel-ot2tools`. If you know what pipx is, use that. If pip install
fails on your laptop, you can do this on a linux server as these tools need
no GUI. If *that* fails, email me.

Then, use either `ot2ools variable_stock` or `ot2ools constant_stock` to
generate the ot2 scripts.


## Manual

There are two main ways of doing dilutions: constant-stock and variable-stock.

**Constant stock** only pipettes water into plates with the opentron, after
which we use the viaflow to transfer across a constant volume of stock DNA/RNA.
This is faster, easier, and better if you have labile stocks like RNA you don't
want hanging around in the opentron for hours. However, it has limited dynamic
range (i.e. can only do up to 20-fold dilutions), and produces highly varying
amounts of diluted DNA/RNA.

**Variable stock** has the opposite properties: by pipetting variable amounts
of both stock and diluent, we can have much greater dilution ratios (up to
200x), and we can (but don't have to) produce a constant volume of diluted
DNA/RNA. However, it's slower (max 3 plates at a time), and you need to have
your stock open to the world and at room temp for much longer, so can cause
problems with particularly sensitive things like dirty RNA extractions.


### `ot2ools constant_stock`

This is the "normal" Pathocom way to do dilutions. We use the opentron only to
pipette a varying amount of water, then use the viaflow 96 head to transfer
a constant amount of stock across. This can be used with the files directly out
of [tecanalyze](https://kdm9.shinyapps.io/tecanalyze). You need only columns
`plate_name`, `well`, `conc` (these can be called something else and there can
be extra columns in the file, see the CLI `--help` output).


```
ot2tools constant_stock \
	--protocol-script-dir protocols/ \
	--conc 5 \
	--volume 10 \
	--pc plate_name --wc well \
	--cc conc \
	quantifications.csv
```


Full help follows:

```
$ ot2ools constant_stock --help
usage: ot2ools [-h] [-b BATCHSIZE] [-o PROTOCOL_SCRIPT_DIR] [-c TARGET_CONC] [-v VOLUME] [-m MIN_VOLUME] [-M MAX_VOLUME] -t SUMMARY_TABLE [--pc PLATE_COLUMN] [--wc WELL_COLUMN] [--cc CONC_COLUMN] instructions

positional arguments:
  instructions          Instructions file csv

options:
  -h, --help            show this help message and exit
  -b BATCHSIZE, --batchsize BATCHSIZE
                        Number of plates per batch
  -o PROTOCOL_SCRIPT_DIR, --protocol-script-dir PROTOCOL_SCRIPT_DIR
                        Output dir
  -c TARGET_CONC, --target-conc TARGET_CONC
                        Target concentration in ng/uL
  -v VOLUME, --volume VOLUME
                        Constant volume of source DNA to transfer (uL)
  -m MIN_VOLUME, --min-volume MIN_VOLUME
                        Minimum volume to transfer
  -M MAX_VOLUME, --max-volume MAX_VOLUME
                        Maximum volume of destination well (combination of water+stock)
  -t SUMMARY_TABLE, --summary-table SUMMARY_TABLE
                        Summary of actions table (tsv)
  --pc PLATE_COLUMN, --plate-column PLATE_COLUMN
                        Column name for plate
  --wc WELL_COLUMN, --well-column WELL_COLUMN
                        Column name for well
  --cc CONC_COLUMN, --conc-column CONC_COLUMN
                        Column name for water volume
```


### `ot2ools variable_stock`

First, prepare a csv or tsv with at least the following columns: plate, well,
stock_volume, water_volume. The column names can vary, you just need to give
the actual names with `--plate-column` etc. You'll get an error if there's
a mismatch.


```
ot2tools variable_stock \
	--protocol-script-dir protocols/ \
	--pc Plate_name --wc Well \
	--hc Water --sc DNA quantification.csv
```

Full help follows

```
$ ot2ools variable-stock --help
usage: ot2ools [-h] [-o PROTOCOL_SCRIPT_DIR] [-p {p10,p50}] [-m MIN_VOLUME] [-M MAX_VOLUME] [--pc PLATE_COLUMN] [--wc WELL_COLUMN] [--hc WATER_COLUMN] [--sc STOCK_COLUMN] instructions

positional arguments:
  instructions          Instructions file csv

options:
  -h, --help            show this help message and exit
  -o PROTOCOL_SCRIPT_DIR, --protocol-script-dir PROTOCOL_SCRIPT_DIR
                        Output dir
  -p {p10,p50}, --stock-pipette {p10,p50}
                        Which pipette to use for stock pipetting
  -m MIN_VOLUME, --min-volume MIN_VOLUME
                        Minimum volume to transfer
  -M MAX_VOLUME, --max-volume MAX_VOLUME
                        Maximum volume of destination well (combination of water+stock)
  --pc PLATE_COLUMN, --plate-column PLATE_COLUMN
                        Column name for plate
  --wc WELL_COLUMN, --well-column WELL_COLUMN
                        Column name for well
  --hc WATER_COLUMN, --water-column WATER_COLUMN
                        Column name for water volume
  --sc STOCK_COLUMN, --stock-column STOCK_COLUMN
                        Column name for stock volume
```


### `ot2ools pool_by_volume`

This script is for pooling a plate of libraries according to their
concentrations. This needs a csv with the following columns: plate, well,
volume, pool. Like above, these names can be changed with CLI arguments. This
requires that you've already calculated how much volume you need from each
sample. The labware layout is a 24-well rack of eppies, with up to 5 plates of
source libraries and 5 boxes of tips to be pooled into up to 24 pools.

**PLEASE NOTE**: your quantifications need to be reasonably accurate, and need
to be taken **after** individual SPRI cleanup for this to be accurate. If you
just do picogreen on the post-PCR libraries, the amount of library is often
much less than the amount of dimer, defeating the entire purpose of this
pooling. If need be, use a larger volume of DNA (e.g. 3uL) for quantification
of low-concentration libraries.


```
$ ot2ools pool-to-eppies --help
usage: ot2ools [-h] [-o PROTOCOL_SCRIPT_DIR] [-p {p10,p50}] [-m MIN_VOLUME] [-M MAX_VOLUME] [--pc PLATE_COLUMN] [--wc WELL_COLUMN] [--vc VOLUME_COLUMN] [--lc POOL_COLUMN] instructions

positional arguments:
  instructions          Instructions file csv

options:
  -h, --help            show this help message and exit
  -o PROTOCOL_SCRIPT_DIR, --protocol-script-dir PROTOCOL_SCRIPT_DIR
                        Output dir
  -p {p10,p50}, --stock-pipette {p10,p50}
                        Which pipette to use for stock pipetting
  -m MIN_VOLUME, --min-volume MIN_VOLUME
                        Minimum volume to transfer
  -M MAX_VOLUME, --max-volume MAX_VOLUME
                        Maximum volume of destination well (combination of water+stock)
  --pc PLATE_COLUMN, --plate-column PLATE_COLUMN
                        Column name for plate
  --wc WELL_COLUMN, --well-column WELL_COLUMN
                        Column name for well
  --vc VOLUME_COLUMN, --volume-column VOLUME_COLUMN
                        Column name for water volume
  --lc POOL_COLUMN, --pool-column POOL_COLUMN
                        Column name for stock volume
```
