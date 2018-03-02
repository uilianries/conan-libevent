#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, AutoToolsBuildEnvironment, RunEnvironment, tools
import os
import shutil

class LibeventConan(ConanFile):
    name = "libevent"
    version = "2.0.22"
    description = 'libevent - an event notification library'
    url = "https://github.com/bincrafters/conan-libevent"
    homepage = "https://libevent.org"
    license = "BSD 3-Clause"
    exports = ["LICENSE.md"]
    exports_sources = ["print-winsock-errors.c", "FindLibEvent.cmake"]
    source_subfolder = "source_subfolder"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False],
               "with_openssl": [True, False],
               "disable_threads": [True, False]}
    default_options = "shared=False", "with_openssl=True", "disable_threads=False"

    @property
    def is_v21(self):
        return self.version.startswith('2.1.')

    @property
    def is_v20(self):
        return self.version.startswith('2.0.')

    def config_options(self):
        del self.settings.compiler.libcxx
        # 2.0 cannot do openssl on Windows
        if self.settings.os == "Windows" and self.is_v20:
            self.options.with_openssl = False

    def requirements(self):
        if self.options.with_openssl:
            self.requires.add("OpenSSL/[>1.0.2a,<1.0.3]@conan/stable")
            if self.options.shared:
                # static OpenSSL cannot be properly detected because libevent picks up system ssl first
                # so enforce shared openssl
                self.output.warn("Enforce shared OpenSSL for shared build")
                self.options["OpenSSL"].shared = self.options.shared

    def source(self):
        tools.get("https://github.com/libevent/libevent/releases/download/release-{0}-stable/libevent-{0}-stable.tar.gz".format(self.version))
        os.rename("libevent-{0}-stable".format(self.version), self.source_subfolder)
        if self.is_v21:
            # copy missing test source, https://github.com/libevent/libevent/issues/523
            shutil.copy("print-winsock-errors.c", os.path.join(self.source_subfolder,"test/"))

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
                            shutil.copy(self.deps_cpp_info[dep].lib_paths[0] + '/' + libname, self.source_subfolder)
                            imported_libs.append(libname)
                self.output.warn("Copying OpenSSL libraries to fix conftest: " + repr(imported_libs))

            # required to correctly find static libssl on Linux
            if self.options.with_openssl and self.settings.os == "Linux":
                env_vars['OPENSSL_LIBADD'] = '-ldl'

            # disable rpath build
            tools.replace_in_file(os.path.join(self.source_subfolder, "configure"), r"-install_name \$rpath/", "-install_name ")

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

                with tools.chdir(self.source_subfolder):
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
            if self.is_v21 and self.options.with_openssl:
                suffix = "OPENSSL_DIR=" + self.deps_cpp_info['OpenSSL'].rootpath
            make_command = "nmake %s -f Makefile.nmake" % suffix
            with tools.chdir(self.source_subfolder):
                self.run("%s && %s" % (vcvars, make_command))


    def package(self):
        self.copy("LICENSE", dst="licenses", ignore_case=True, keep_path=False)
        self.copy("FindLibEvent.cmake", dst=".", ignore_case=True, keep_path=False)
        self.copy("*.h", dst="include", src=os.path.join(self.source_subfolder, "include"))
        if self.settings.os == "Windows":
            if self.is_v21:
                self.copy("event-config.h", src=os.path.join(self.source_subfolder, "WIN32-Code", "nmake", "event2"), dst="include/event2")
            else:
                # Windows build is not using configure, so event-config.h is copied from WIN32-Code folder
                self.copy("event-config.h", src=os.path.join(self.source_subfolder, "WIN32-Code", "event2"), dst="include/event2")
            self.copy("tree.h", src=os.path.join(self.source_subfolder, "WIN32-Code"), dst="include")
            self.copy(pattern="*.lib", dst="lib", keep_path=False)
        for header in ['evdns', 'event', 'evhttp', 'evrpc', 'evutil']:
            self.copy(header+'.h', dst="include", src=self.source_subfolder)
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
            if self.is_v21 and self.options.with_openssl:
                self.cpp_info.defines.append('EVENT__HAVE_OPENSSL=1')
