#!/usr/bin/env python
# -*- coding: utf-8 -*-


from bincrafters import build_template_default
import platform
import copy

if __name__ == "__main__":

    builder = build_template_default.get_builder()

    # libevent 2.0 doesn't support shared build on Windows
    # so remove those builds that have shared=True
    # and remove windows shared builds at all by now
    items = []
    for item in builder.items:
        if platform.system() == "Windows":
            #and item.reference.version.startswith('2.0.'):
            if not item.options.get('libevent:shared', False):
                items.append(item)
        else:
            items.append(item)
    builder.items = items

    # Add Windows builds without OpenSSL too
    if platform.system() == "Windows":
        items = []
        for item in builder.items:
            new_options = copy.copy(item.options)
            new_options["libevent:with_openssl"] = False
            items.append([item.settings, new_options, item.env_vars,
                item.build_requires, item.reference])
            builder.items = items

    builder.run()
