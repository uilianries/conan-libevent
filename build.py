#!/usr/bin/env python
# -*- coding: utf-8 -*-
from bincrafters import build_template_default
import platform

if __name__ == "__main__":

    shared_option_name = False if platform.system() == "Windows" else "libevent:shared"
    builder = build_template_default.get_builder(pure_c=True, shared_option_name=shared_option_name)
    if platform.system() == "Windows":
        for settings, options, env_vars, build_requires, reference in reversed(builder.items):
            builder.add(settings, {"libevent:with_openssl": False}, env_vars, build_requires)
    builder.run()
