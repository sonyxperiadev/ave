#! /usr/bin/python2

import sys
import vcsjob

try:
    path = vcsjob.get_log_path()
except:
    sys.exit(0)
print path
sys.exit(1)
