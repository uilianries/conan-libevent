#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bincrafters import build_template_default
from conans import tools
import copy

if __name__ == "__main__":

    builder = build_template_default.get_builder(pure_c=True)
    # Add Windows builds without OpenSSL too
    if tools.os_info.is_windows:
        items = []
        for item in builder.items:
            new_options = copy.copy(item.options)
            new_options["libevent:with_openssl"] = False
            items.append([item.settings, new_options, item.env_vars,
                item.build_requires, item.reference])
            builder.items = items

    builder.run()
