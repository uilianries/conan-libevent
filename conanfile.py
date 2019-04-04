# -*- coding: utf-8 -*-

import os
import shutil
from conans import ConanFile, AutoToolsBuildEnvironment, RunEnvironment, tools
from conans.errors import ConanInvalidConfiguration

class LibeventConan(ConanFile):
    name = "libevent"
    version = "2.0.22"
    description = 'libevent - an event notification library'
    url = "https://github.com/bincrafters/conan-libevent"
    homepage = "https://github.com/libevent/libevent"
    author = "Bincrafters <bincrafters@gmail.com>"
    topics = ("conan", "libevent", "event", "notification")
    license = "BSD-3-Clause"
    exports = ["LICENSE.md"]
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False],
               "fPIC": [True, False],
               "with_openssl": [True, False],
               "disable_threads": [True, False]}
    default_options = {"shared": False,
                       "fPIC": True,
                       "with_openssl": True,
                       "disable_threads": False}
    _source_subfolder = "source_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.remove("fPIC")
        # 2.0 cannot do openssl on Windows
        if self.settings.os == "Windows":
            self.options.with_openssl = False

    def configure(self):
        del self.settings.compiler.libcxx
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration("Shared builds on Windows are not supported")

    def requirements(self):
        if self.options.with_openssl:
            self.requires.add("OpenSSL/1.0.2r@conan/stable")
            if self.options.shared:
                # static OpenSSL cannot be properly detected because libevent picks up system ssl first
                # so enforce shared openssl
                self.output.warn("Enforce shared OpenSSL for shared build")
                self.options["OpenSSL"].shared = self.options.shared

    def source(self):
        sha256 = "71c2c49f0adadacfdbe6332a372c38cf9c8b7895bb73dabeaa53cdcc1d4e1fa3"
        tools.get("{0}/releases/download/release-{1}-stable/libevent-{1}-stable.tar.gz".format(self.homepage, self.version), sha256=sha256)
        os.rename("libevent-{0}-stable".format(self.version), self._source_subfolder)

    def build(self):
        if self.settings.os == "Linux" or self.settings.os == "Macos":
            env_build = AutoToolsBuildEnvironment(self)
            env_vars = env_build.vars.copy()
            # Configure script creates conftest that cannot execute without shared openssl binaries.
            # Ways to solve the problem:
            # 1. set *LD_LIBRARY_PATH (works with Linux with RunEnvironment but does not work on OS X 10.11 with SIP)
            # 2. copying dylib's to the build directory (fortunately works on OS X)
            imported_libs = []
            if self.options.shared and self.settings.os == "Macos":
                for dep in self.deps_cpp_info.deps:
                    for libname in os.listdir(self.deps_cpp_info[dep].lib_paths[0]):
                        if libname.endswith('.dylib'):
                            shutil.copy(self.deps_cpp_info[dep].lib_paths[0] + '/' + libname, self._source_subfolder)
                            imported_libs.append(libname)
                self.output.warn("Copying OpenSSL libraries to fix conftest: " + repr(imported_libs))

            # required to correctly find static libssl on Linux
            if self.options.with_openssl and self.settings.os == "Linux":
                env_vars['OPENSSL_LIBADD'] = '-ldl'

            # disable rpath build
            tools.replace_in_file(os.path.join(self._source_subfolder, "configure"), r"-install_name \$rpath/", "-install_name ")

            # compose configure options
            suffix = ''
            if not self.options.shared:
                suffix += " --disable-shared "
            if self.options.with_openssl:
                suffix += "--enable-openssl "
            else:
                suffix += "--disable-openssl "
            if self.options.disable_threads:
                suffix += "--disable-thread-support "

            with tools.environment_append(env_vars):

                with tools.chdir(self._source_subfolder):
                    # set LD_LIBRARY_PATH
                    with tools.environment_append(RunEnvironment(self).vars):
                        cmd = './configure %s' % (suffix)
                        self.output.warn('Running: ' + cmd)
                        self.run(cmd)

                        cmd = 'make'
                        self.output.warn('Running: ' + cmd)
                        self.run(cmd)

                    # now clean imported libs
                    for imported_lib in imported_libs:
                        os.unlink(imported_lib)

        elif self.settings.os == "Windows":
            vcvars = tools.vcvars_command(self.settings)
            suffix = ''
            # add runtime directives to runtime-unaware nmakefile
            tools.replace_in_file(os.path.join(self._source_subfolder, "Makefile.nmake"),
                                  'LIBFLAGS=/nologo',
                                  'LIBFLAGS=/nologo\n'
                                  'CFLAGS=$(CFLAGS) /%s' % str(self.settings.compiler.runtime))
            # do not build tests. static_libs is the only target, no shared libs at all
            make_command = "nmake %s -f Makefile.nmake static_libs" % suffix
            with tools.chdir(self._source_subfolder):
                self.run("%s && %s" % (vcvars, make_command))


    def package(self):
        self.copy("LICENSE", src=self._source_subfolder, dst="licenses", ignore_case=True, keep_path=False)
        self.copy("*.h", dst="include", src=os.path.join(self._source_subfolder, "include"))
        if self.settings.os == "Windows":
            # Windows build is not using configure, so event-config.h is copied from WIN32-Code folder
            self.copy("event-config.h", src=os.path.join(self._source_subfolder, "WIN32-Code", "event2"), dst="include/event2")
            self.copy("tree.h", src=os.path.join(self._source_subfolder, "WIN32-Code"), dst="include")
            self.copy(pattern="*.lib", dst="lib", keep_path=False)
        for header in ['evdns', 'event', 'evhttp', 'evrpc', 'evutil']:
            self.copy(header+'.h', dst="include", src=self._source_subfolder)
        if self.options.shared:
            if self.settings.os == "Macos":
                self.copy(pattern="*.dylib", dst="lib", keep_path=False)
            else:
                self.copy(pattern="*.so*", dst="lib", keep_path=False)
        else:
            self.copy(pattern="*.a", dst="lib", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if self.settings.os == "Linux":
            self.cpp_info.libs.extend(["rt"])

        if self.settings.os == "Windows":
            self.cpp_info.libs.append('ws2_32')
