
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

import os


def split_path(path):
  if path[-1] == '/':
    return os.path.split(path[:-1])
  else:
    return os.path.split(path)
