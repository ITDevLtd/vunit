# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2014-2019, Lars Asplund lars.anders.asplund@gmail.com

"""
Generic simulator interface
"""

from __future__ import print_function
import sys
import os
import subprocess
from vunit.ostools import Process, simplify_path
from vunit.exceptions import CompileError
from vunit.color_printer import NO_COLOR_PRINTER


class SimulatorInterface(object):  # pylint: disable=too-many-public-methods
    """
    Generic simulator interface
    """

    name = None
    supports_gui_flag = False
    package_users_depend_on_bodies = False
    compile_options = []
    sim_options = []

    # True if simulator supports ANSI colors in GUI mode
    supports_colors_in_gui = False

    def __init__(self, output_path, gui):
        self._output_path = output_path
        self._gui = gui

    @property
    def output_path(self):
        return self._output_path

    @property
    def use_color(self):
        return (not self._gui) or self.supports_colors_in_gui

    @staticmethod
    def add_arguments(parser):
        """
        Add command line arguments
        """

    @staticmethod
    def supports_vhdl_contexts():
        """
        Returns True when this simulator supports VHDL contexts
        """
        return True

    @staticmethod
    def find_executable(executable):
        """
        Return a list of all executables found in PATH
        """
        path = os.environ.get("PATH", None)
        if path is None:
            return []

        paths = path.split(os.pathsep)
        _, ext = os.path.splitext(executable)

        if (sys.platform == "win32" or os.name == "os2") and (ext != ".exe"):
            executable = executable + ".exe"

        result = []
        if isfile(executable):
            result.append(executable)

        for prefix in paths:
            file_name = os.path.join(prefix, executable)
            if isfile(file_name):
                # the file exists, we have a shot at spawn working
                result.append(file_name)
        return result

    @classmethod
    def find_prefix(cls):
        """
        Find prefix by looking at VUNIT_<SIMULATOR_NAME>_PATH environment variable
        """
        prefix = os.environ.get("VUNIT_" + cls.name.upper() + "_PATH", None)
        if prefix is not None:
            return prefix
        return cls.find_prefix_from_path()

    @classmethod
    def find_prefix_from_path(cls):
        """
        Find simulator toolchain prefix from PATH environment variable
        """

    @classmethod
    def is_available(cls):
        """
        Returns True if simulator is available
        """
        return cls.find_prefix() is not None

    @classmethod
    def find_toolchain(cls, executables, constraints=None):
        """
        Find the first path prefix containing all executables
        """
        constraints = [] if constraints is None else constraints

        if not executables:
            return None

        all_paths = [
            [
                os.path.abspath(os.path.dirname(executables))
                for executables in cls.find_executable(name)
            ]
            for name in executables
        ]

        for path0 in all_paths[0]:
            if all(
                [path0 in paths for paths in all_paths]
                + [constraint(path0) for constraint in constraints]
            ):
                return path0
        return None

    @classmethod
    def get_osvvm_coverage_api(cls):
        """
        Returns simulator name when OSVVM coverage API is supported, None otherwise.
        """

    @classmethod
    def supports_vhdl_package_generics(cls):
        """
        Returns True when this simulator supports VHDL package generics
        """
        return False

    @staticmethod
    def has_valid_exit_code():
        """
        Return if the simulation should fail with nonzero exit codes
        """
        return False

    @staticmethod
    def supports_vhpi():
        """
        Return if the simulator supports VHPI
        """
        return False

    def merge_coverage(  # pylint: disable=unused-argument, no-self-use
        self, file_name, args
    ):
        """
        Hook for simulator interface to creating coverage reports
        """
        raise RuntimeError("This simulator does not support merging coverage")

    def add_simulator_specific(self, project):
        """
        Hook for the simulator interface to add simulator specific things to the project
        """

    def compile_project(
        self,
        project,
        printer=NO_COLOR_PRINTER,
        continue_on_error=False,
        target_files=None,
    ):
        """
        Compile the project
        param: target_files: Given a list of SourceFiles only these and dependent files are compiled
        """
        self.add_simulator_specific(project)
        self.setup_library_mapping(project)
        self.compile_source_files(
            project, printer, continue_on_error, target_files=target_files
        )

    def simulate(self, output_path, test_suite_name, config, elaborate_only):
        """
        Simulate
        """

    def setup_library_mapping(self, project):
        """
        Implemented by specific simulators
        """

    def __compile_source_file(self, source_file, printer):
        """
        Compiles a single source file and prints status information
        """
        try:
            command = self.compile_source_file_command(source_file)
        except CompileError:
            command = None
            printer.write("failed", fg="ri")
            printer.write("\n")
            printer.write("File type not supported by %s simulator\n" % (self.name))

            return False

        try:
            output = check_output(command, env=self.get_env())
            printer.write("passed", fg="gi")
            printer.write("\n")
            printer.write(output)

        except subprocess.CalledProcessError as err:
            printer.write("failed", fg="ri")
            printer.write("\n")
            printer.write(
                "=== Command used: ===\n%s\n" % (subprocess.list2cmdline(command))
            )
            printer.write("\n")
            printer.write("=== Command output: ===\n%s\n" % err.output)

            return False

        return True

    def compile_source_files(
        self,
        project,
        printer=NO_COLOR_PRINTER,
        continue_on_error=False,
        target_files=None,
    ):
        """
        Use compile_source_file_command to compile all source_files
        param: target_files: Given a list of SourceFiles only these and dependent files are compiled
        """
        dependency_graph = project.create_dependency_graph()
        failures = []

        if target_files is None:
            source_files = project.get_files_in_compile_order(
                dependency_graph=dependency_graph
            )
        else:
            source_files = project.get_minimal_file_set_in_compile_order(target_files)

        source_files_to_skip = set()

        max_library_name = 0
        max_source_file_name = 0
        if source_files:
            max_library_name = max(
                len(source_file.library.name) for source_file in source_files
            )
            max_source_file_name = max(
                len(simplify_path(source_file.name)) for source_file in source_files
            )

        for source_file in source_files:
            printer.write(
                "Compiling into %s %s "
                % (
                    (source_file.library.name + ":").ljust(max_library_name + 1),
                    simplify_path(source_file.name).ljust(max_source_file_name),
                )
            )
            sys.stdout.flush()

            if source_file in source_files_to_skip:
                printer.write("skipped", fg="rgi")
                printer.write("\n")
                continue

            if self.__compile_source_file(source_file, printer):
                project.update(source_file)
            else:
                source_files_to_skip.update(
                    dependency_graph.get_dependent([source_file])
                )
                failures.append(source_file)

                if not continue_on_error:
                    break

        if failures:
            printer.write("Compile failed\n", fg="ri")
            raise CompileError

        if source_files:
            printer.write("Compile passed\n", fg="gi")
        else:
            printer.write("Re-compile not needed\n")

    def compile_source_file_command(  # pylint: disable=unused-argument
        self, source_file
    ):
        raise NotImplementedError

    @staticmethod
    def get_env():
        """
        Allows inheriting classes to overload this to modify environment variables. Return None for default environment
        """


def isfile(file_name):
    """
    Case insensitive os.path.isfile
    """
    if not os.path.isfile(file_name):
        return False

    return os.path.basename(file_name) in os.listdir(os.path.dirname(file_name))


def run_command(command, cwd=None, env=None):
    """
    Run a command
    """
    try:
        proc = Process(command, cwd=cwd, env=env)
        proc.consume_output()
        return True
    except Process.NonZeroExitCode:
        pass
    return False


def check_output(command, env=None):
    """
    Wrapper arround subprocess.check_output
    """
    try:
        output = subprocess.check_output(  # pylint: disable=unexpected-keyword-arg
            command, env=env, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as err:
        err.output = err.output.decode("utf-8")
        raise err
    return output.decode("utf-8")


class Option(object):
    """
    A compile or sim option
    """

    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    def validate(self, value):
        pass


class BooleanOption(Option):
    """
    Must be a boolean
    """

    def validate(self, value):
        if value not in (True, False):
            raise ValueError("Option %r must be a boolean. Got %r" % (self.name, value))


class StringOption(Option):
    """
    Must be a string
    """

    def validate(self, value):
        if not is_string_not_iterable(value):
            raise ValueError("Option %r must be a string. Got %r" % (self.name, value))


class ListOfStringOption(Option):
    """
    Must be a list of strings
    """

    def validate(self, value):
        def fail():
            raise ValueError(
                "Option %r must be a list of strings. Got %r" % (self.name, value)
            )

        if is_string_not_iterable(value):
            fail()

        try:
            for elem in value:
                if not is_string_not_iterable(elem):
                    fail()
        except TypeError:
            fail()


class VHDLAssertLevelOption(Option):
    """
    VHDL assert level
    """

    _legal_values = ("warning", "error", "failure")

    def __init__(self):
        Option.__init__(self, "vhdl_assert_stop_level")

    def validate(self, value):
        if value not in self._legal_values:
            raise ValueError(
                "Option %r must be one of %s. Got %r"
                % (self.name, self._legal_values, value)
            )


def is_string_not_iterable(value):
    """
    Returns True if value is a string and not another iterable
    """
    if sys.version_info.major == 3:
        return isinstance(value, str)

    return isinstance(value, (str, unicode))  # pylint: disable=undefined-variable
