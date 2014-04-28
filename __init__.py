"""
PyISY - Python Library for the ISY Controller

DESCRIPTION:
	This module is a set of Python bindings for the ISY's REST API. The
	ISY is developed by Universal Devices and is a home automation
	controller for Insteon and X10 devices.

AUTHOR: Automicus (Ryan M. Kraus)
COPYRIGHT: (C) 2014
WRITTEN: December, 2014
"""

from ISY import ISY
import tests


def install(*args, **kwargs):
    mod = ISY(*args, **kwargs)
    mod.auto_update = True
    return mod
