#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from conans import ConanFile, AutoToolsBuildEnvironment, RunEnvironment, tools
from conans.errors import ConanInvalidConfiguration

class LibeventConan(ConanFile):
    name = "libevent"
    version = "2.1.8"
    description = 'libevent - an event notification library'
    url = "https://github.com/bincrafters/conan-libevent"
    homepage = "https://github.com/libevent/libevent"
    author = "Bincrafters <bincrafters@gmail.com>"
    license = "BSD-3-Clause"
    exports = ["LICENSE.md"]
    exports_sources = ["print-winsock-errors.c"]
    source_subfolder = "source_subfolder"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False],
               "fPIC": [True, False],
               "with_openssl": [True, False],
               "disable_threads": [True, False]}
    default_options = {"shared": False,
                       "fPIC": True,
                       "with_openssl": True,
                       "disable_threads": False}

    @property
    def _is_shared(self):
        return self.settings.os != "Windows" and self.options.shared

    @property
    def _is_mingw(self):
        return self.settings.compiler == "gcc" and \
               self.settings.os == "Windows" and \
               os.name == "nt"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.shared

    def configure(self):
        del self.settings.compiler.libcxx

        if self.options.with_openssl and self._is_shared:
            # static OpenSSL cannot be properly detected because libevent picks up system ssl first
            # so enforce shared openssl
            self.output.warn("Enforce shared OpenSSL for shared build")
            self.options["OpenSSL"].shared = self._is_shared

    def requirements(self):
        if self.options.with_openssl:
            self.requires.add("OpenSSL/1.0.2o@conan/stable")

    def source(self):
        tools.get("{0}/releases/download/release-{1}-stable/libevent-{1}-stable.tar.gz".format(self.homepage, self.version))
        os.rename("libevent-{0}-stable".format(self.version), self.source_subfolder)
        shutil.copy("print-winsock-errors.c", os.path.join(self.source_subfolder, "test"))

    def imports(self):
        # Copy shared libraries for dependencies to fix DYLD_LIBRARY_PATH problems
        #
        # Configure script creates conftest that cannot execute without shared openssl binaries.
        # Ways to solve the problem:
        # 1. set *LD_LIBRARY_PATH (works with Linux with RunEnvironment
        #     but does not work on OS X 10.11 with SIP)
        # 2. copying dylib's to the build directory (fortunately works on OS X)

        if self.settings.os == "Macos":
            self.copy("*.dylib*", dst=self.source_subfolder, keep_path=False)

    def build(self):

        if self.settings.os == "Linux" or self.settings.os == "Macos" or self._is_mingw:

            autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
            env_vars = autotools.vars.copy()

            # required to correctly find static libssl on Linux
            if self.options.with_openssl and self.settings.os == "Linux":
                env_vars['OPENSSL_LIBADD'] = '-ldl'

            # disable rpath build
            tools.replace_in_file(os.path.join(self.source_subfolder, "configure"), r"-install_name \$rpath/", "-install_name ")

            # compose configure options
            configure_args = []
            if not self._is_shared:
                configure_args.append("--disable-shared")
            configure_args.append("--enable-openssl" if self.options.with_openssl else "--disable-openssl")
            if self.options.disable_threads:
                configure_args.append("--disable-thread-support")

            with tools.environment_append(env_vars):

                with tools.chdir(self.source_subfolder):
                    # set LD_LIBRARY_PATH
                    with tools.environment_append(RunEnvironment(self).vars):
                        autotools.configure(args=configure_args)
                        autotools.make()

        elif self.settings.os == "Windows":
            vcvars = tools.vcvars_command(self.settings)
            suffix = ''
            if self.options.with_openssl:
                suffix = "OPENSSL_DIR=" + self.deps_cpp_info['OpenSSL'].rootpath
            # add runtime directives to runtime-unaware nmakefile
            tools.replace_in_file(os.path.join(self.source_subfolder, "Makefile.nmake"),
                                  'LIBFLAGS=/nologo',
                                  'LIBFLAGS=/nologo\n'
                                  'CFLAGS=$(CFLAGS) /%s' % str(self.settings.compiler.runtime))
            # do not build tests. static_libs is the only target, no shared libs at all
            make_command = "nmake %s -f Makefile.nmake static_libs" % suffix
            with tools.chdir(self.source_subfolder):
                self.run("%s && %s" % (vcvars, make_command))


    def package(self):
        self.copy("LICENSE", src=self.source_subfolder, dst="licenses", ignore_case=True, keep_path=False)
        self.copy("*.h", dst="include", src=os.path.join(self.source_subfolder, "include"))
        if self.settings.os == "Windows":
            self.copy("event-config.h", src=os.path.join(self.source_subfolder, "WIN32-Code", "nmake", "event2"), dst="include/event2")
            self.copy("tree.h", src=os.path.join(self.source_subfolder, "WIN32-Code"), dst="include")
            self.copy(pattern="*.lib", dst="lib", keep_path=False)
        for header in ['evdns', 'event', 'evhttp', 'evrpc', 'evutil']:
            self.copy(header+'.h', dst="include", src=self.source_subfolder)
        if self._is_shared:
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
            if self.options.with_openssl:
                self.cpp_info.defines.append('EVENT__HAVE_OPENSSL=1')
