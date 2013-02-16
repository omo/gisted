# -*- coding: utf-8 -*-

import os, sys
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base)

import gisted.cli

gisted.cli.run(sys.argv)
