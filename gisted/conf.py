# -*- coding: utf-8 -*-

import os
import ConfigParser

CONFIG_FILE_NAME = os.environ.get("API_CONFIG")
conf = ConfigParser.ConfigParser()
conf.readfp(open(CONFIG_FILE_NAME))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def credential(name):
    return conf.get("Credentials", name)

def data_path(name):
    return os.path.join(DATA_DIR, name)

def enable_debug_pages():
    return True
