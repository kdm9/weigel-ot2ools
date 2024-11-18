#!/usr/bin/env python3
#  Copyright Kevin Murray <foss@kdmurray.id.au> 2024
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ._version import version
__version__ = version

from sys import argv, exit, stderr
cmds = {}

from .variable_stock import main as variable_stock_main
cmds["variable_stock"] = variable_stock_main

#from .const_stock import main as const_stock_main
#cmds["constant_stock"] = const_stock_main

def mainhelp(argv=None):
    """Print this help message"""
    print("USAGE: ot2ools <subtool> [options...]\n\n")
    print("Where <subtool> is one of:\n")
    for tool, func in cmds.items():
        print("  {:<19}".format(tool + ":"), " ", func.__doc__.split("\n")[0])
    print("\n\nUse ot2ools subtool --help to get help about a specific tool")

cmds["help"] = mainhelp

def main():
    if len(argv) < 2:
        mainhelp()
        exit(0)
    if argv[1] not in cmds:
        print("ERROR:", argv[1], "is not a known subtool. See help below")
        mainhelp()
        exit(1)
    cmds[argv[1]](argv[2:])
