# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2014-2019, Lars Asplund lars.anders.asplund@gmail.com

"""
PyPI setup script
"""

import os
from logging import warning
from setuptools import setup
from vunit.about import version, doc
from vunit.builtins import osvvm_is_installed


def find_all_files(directory, endings=None):
    """
    Recursively find all files within directory
    """
    result = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            ending = os.path.splitext(filename)[-1]
            if endings is None or ending in endings:
                result.append(os.path.join(root, filename))
    return result


DATA_FILES = []
DATA_FILES += find_all_files(os.path.join("vunit"), endings=[".tcl"])
DATA_FILES += find_all_files(os.path.join("vunit", "vhdl"))
DATA_FILES += find_all_files(
    os.path.join("vunit", "verilog"), endings=[".v", ".sv", ".svh"]
)
DATA_FILES = [os.path.relpath(file_name, "vunit") for file_name in DATA_FILES]

setup(
    name="vunit_hdl",
    version=version(),
    packages=[
        "vunit",
        "vunit.com",
        "vunit.parsing",
        "vunit.parsing.verilog",
        "vunit.test",
        "vunit.test.lint",
        "vunit.test.unit",
        "vunit.test.acceptance",
        "vunit.ui",
        "vunit.vivado",
    ],
    package_data={"vunit": DATA_FILES},
    zip_safe=False,
    url="https://github.com/VUnit/vunit",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Topic :: Software Development :: Testing",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
    install_requires=["colorama"],
    requires=["colorama"],
    license=["Mozilla Public License 2.0 (MPL 2.0)"],
    author="Lars Asplund",
    author_email="lars.anders.asplund@gmail.com",
    description="VUnit is an open source unit testing framework for VHDL/SystemVerilog.",
    long_description=doc(),
)

if not osvvm_is_installed():
    warning(
        """
Found no OSVVM VHDL files. If you're installing from a Git repository and plan to use VUnit's integration
of OSVVM you should run

git submodule update --init --recursive

in your VUnit repository before running setup.py."""
    )
