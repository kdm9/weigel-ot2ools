# WeigelWorld Opentron2 duct-tape

These duct-tape scripts go between [tecanalyze](https://kdm9.shinyapps.io/tecanalyze) and the opentron protocol language itself.

There are two main ways of doing dilutions: constant-stock and variable-stock.

**Constant stock** only pipettes water into plates with the opentron, after which we use the viaflow to transfer across a constant volume of stock DNA/RNA. This is faster, easier, and better if you have labile stocks like RNA you don't want hanging around in the opentron for hours. However, it has limited dynamic range (i.e. can only do up to 20-fold dilutions), and produces highly varying amounts of diluted DNA/RNA.

**Variable stock** has the opposite properties: by pipetting variable amounts of both stock and diluent, we can have much greater dilution ratios (up to 200x), and we can (but don't have to) produce a constant volume of diluted DNA/RNA. However, it's slower (max 3 plates at a time), and you need to have your stock open to the world and at room temp for much longer, so can cause problems with particularly sensitive things like dirty RNA extractions.

To use these tools (CLI only for now), first install with `python3 -m pip install weigel-ot2tools`. If that fails, you can do this on a linux server as it needs no GUI. If *that* fails, email me.

Then, use either `ot2ools variable_stock` or `ot2ools constant_stock` to generate the ot2 scripts.


## Manual

### `ot2ools variable_stock`

First, prepare a csv or tsv with at least the following columns: plate, well, stock_volume, water_volume. The column names can vary, you just need to give the actual names with `--plate-column` etc. You'll get an error if there's a mismatch.

Then, run the script as follows:

```
ot2tools variable_stock \
	--protocol-script-dir protocols/ \
	--pc Plate_name --wc Well \
	--hc Water --sc DNA quantification.csv
```

Full help follows

```
$ ot2ools variable_stock --help
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
