# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2014-2019, Lars Asplund lars.anders.asplund@gmail.com

"""
Functions to add builtin VHDL code to a project for compilation
"""


from os.path import join, abspath, dirname, basename
from glob import glob
from vunit.vhdl_standard import VHDL
from vunit.test.common import simulator_check

VHDL_PATH = abspath(join(dirname(__file__), "vhdl"))
VERILOG_PATH = abspath(join(dirname(__file__), "verilog"))


class Builtins(object):
    """
    Manage VUnit builtins and their dependencies
    """

    def __init__(self, vunit_obj, vhdl_standard, simulator_class):
        self._vunit_obj = vunit_obj
        self._vunit_lib = vunit_obj.add_library("vunit_lib")
        self._vhdl_standard = vhdl_standard
        self._simulator_class = simulator_class
        self._builtins_adder = BuiltinsAdder()

        def add(name, deps=tuple()):
            self._builtins_adder.add_type(name, getattr(self, "_add_%s" % name), deps)

        add("array_util")
        add("com")
        add("verification_components", ["com", "osvvm"])
        add("osvvm")
        add("random", ["osvvm"])
        add("json4vhdl")

    def add(self, name, args=None):
        self._builtins_adder.add(name, args)

    def _add_files(self, pattern):
        """
        Add files with naming convention to indicate which standard is supported
        """
        supports_context = (
            self._simulator_class.supports_vhdl_contexts()
            and self._vhdl_standard.supports_context
        )

        for file_name in glob(pattern):
            base_file_name = basename(file_name)

            standards = set()
            for standard in VHDL.STANDARDS:
                standard_name = str(standard)
                if standard_name + "p" in base_file_name:
                    standards.update(standard.and_later)
                elif standard_name in base_file_name:
                    standards.add(standard)

            if standards and self._vhdl_standard not in standards:
                continue

            if not supports_context and file_name.endswith("_context.vhd"):
                continue

            self._vunit_lib.add_source_file(file_name)

    def _add_data_types(self, external=None):
        """
        Add data types packages (sources corresponding to VHPIDIRECT arrays, or their placeholders)

        :param external: struct to select whether to enable external models for 'string' and/or 'integer' vectors.
                         {'string': <VAL>, 'integer': <VAL>}. Allowed values are: None, False/True or
                         ['path/to/custom/file'].
        """
        self._add_files(join(VHDL_PATH, "data_types", "src", "*.vhd"))

        use_ext = {"string": False, "integer": False}
        files = {"string": None, "integer": None}

        if external:
            for ind, val in external.items():
                if isinstance(val, bool):
                    use_ext[ind] = val
                else:
                    use_ext[ind] = True
                    files[ind] = val

        for _, val in use_ext.items():
            if val and simulator_check(lambda simclass: not simclass.supports_vhpi()):
                raise RuntimeError(
                    "the selected simulator does not support VHPI; must use non-VHPI packages..."
                )

        ext_path = join(VHDL_PATH, "data_types", "src", "external")

        def default_files(cond, type_str):
            """
            Return name of VHDL file with default VHPIDIRECT foreign declarations.
            """
            return [
                join(
                    ext_path,
                    "external_" + type_str + "-" + ("" if cond else "no") + "vhpi.vhd",
                ),
                join(ext_path, "external_" + type_str + "-body.vhd"),
            ]

        if not files["string"]:
            files["string"] = default_files(use_ext["string"], "string")

        if not files["integer"]:
            files["integer"] = default_files(use_ext["integer"], "integer_vector")

        for _, val in files.items():
            for name in val:
                self._add_files(name)

    def _add_array_util(self):
        """
        Add array utility
        """
        if not self._vhdl_standard >= VHDL.STD_2008:
            raise RuntimeError("Array util only supports vhdl 2008 and later")

        self._vunit_lib.add_source_files(join(VHDL_PATH, "array", "src", "*.vhd"))

    def _add_random(self):
        """
        Add random pkg
        """
        if not self._vhdl_standard >= VHDL.STD_2008:
            raise RuntimeError("Random only supports vhdl 2008 and later")

        self._vunit_lib.add_source_files(join(VHDL_PATH, "random", "src", "*.vhd"))

    def _add_com(self):
        """
        Add com library
        """
        if not self._vhdl_standard >= VHDL.STD_2008:
            raise RuntimeError(
                "Communication package only supports vhdl 2008 and later"
            )

        self._add_files(join(VHDL_PATH, "com", "src", "*.vhd"))

    def _add_verification_components(self):
        """
        Add verification component library
        """
        if not self._vhdl_standard >= VHDL.STD_2008:
            raise RuntimeError(
                "Verification component library only supports vhdl 2008 and later"
            )
        self._add_files(join(VHDL_PATH, "verification_components", "src", "*.vhd"))

    def _add_osvvm(self):
        """
        Add osvvm library
        """
        library_name = "osvvm"

        try:
            library = self._vunit_obj.library(library_name)
        except KeyError:
            library = self._vunit_obj.add_library(library_name)

        simulator_coverage_api = self._simulator_class.get_osvvm_coverage_api()
        supports_vhdl_package_generics = (
            self._simulator_class.supports_vhdl_package_generics()
        )

        if not osvvm_is_installed():
            raise RuntimeError(
                """
Found no OSVVM VHDL files. Did you forget to run

git submodule update --init --recursive

in your VUnit Git repository? You have to do this first if installing using setup.py."""
            )

        for file_name in glob(join(VHDL_PATH, "osvvm", "*.vhd")):
            if basename(file_name) == "AlertLogPkg_body_BVUL.vhd":
                continue

            if (simulator_coverage_api != "rivierapro") and (
                basename(file_name) == "VendorCovApiPkg_Aldec.vhd"
            ):
                continue

            if (simulator_coverage_api == "rivierapro") and (
                basename(file_name) == "VendorCovApiPkg.vhd"
            ):
                continue

            if not supports_vhdl_package_generics and (
                basename(file_name)
                in [
                    "ScoreboardGenericPkg.vhd",
                    "ScoreboardPkg_int.vhd",
                    "ScoreboardPkg_slv.vhd",
                ]
            ):
                continue

            library.add_source_files(file_name, preprocessors=[])

    def _add_json4vhdl(self):
        """
        Add JSON-for-VHDL library
        """
        library_name = "JSON"

        try:
            library = self._vunit_obj.library(library_name)
        except KeyError:
            library = self._vunit_obj.add_library(library_name)

        library.add_source_files(join(VHDL_PATH, "JSON-for-VHDL", "vhdl", "*.vhdl"))

    def add_verilog_builtins(self):
        """
        Add Verilog builtins
        """
        self._vunit_lib.add_source_files(join(VERILOG_PATH, "vunit_pkg.sv"))

    def add_vhdl_builtins(self, external=None):
        """
        Add vunit VHDL builtin libraries

        :param external: struct to select whether to enable external models for 'string' and/or 'integer' vectors.
                         {'string': <VAL>, 'integer': <VAL>}. Allowed values are: None, False/True or
                         ['path/to/custom/file'].
        """
        self._add_data_types(external=external)
        self._add_files(join(VHDL_PATH, "*.vhd"))
        for path in (
            "core",
            "logging",
            "string_ops",
            "check",
            "dictionary",
            "run",
            "path",
        ):
            self._add_files(join(VHDL_PATH, path, "src", "*.vhd"))


def osvvm_is_installed():
    """
    Checks if OSVVM is installed within the VUnit directory structure
    """
    return len(glob(join(VHDL_PATH, "osvvm", "*.vhd"))) != 0


def add_verilog_include_dir(include_dirs):
    """
    Add VUnit Verilog include directory
    """
    return [join(VERILOG_PATH, "include")] + include_dirs


class BuiltinsAdder(object):
    """
    Class to manage adding of builtins with dependencies
    """

    def __init__(self):
        self._already_added = {}
        self._types = {}

    def add_type(self, name, function, dependencies=tuple()):
        self._types[name] = (function, dependencies)

    def add(self, name, args=None):
        """
        Add builtin with arguments
        """
        args = {} if args is None else args

        if not self._add_check(name, args):
            function, dependencies = self._types[name]
            for dep_name in dependencies:
                self.add(dep_name)
            function(**args)

    def _add_check(self, name, args=None):
        """
        Check if this package has already been added,
        if it has already been added it must use the same parameters

        @returns False if not yet added
        """
        if name not in self._already_added:
            self._already_added[name] = args
            return False

        old_args = self._already_added[name]
        if args != old_args:
            raise RuntimeError(
                "Optional builtin %r added with arguments %r has already been added with arguments %r"
                % (name, args, old_args)
            )
        return True
