#!/usr/bin/python3

# Copyright 2022 Thomas Erbesdobler <t.erbesdobler@gmx.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Assume that only complete arrays shall be replaced
# NOTE: The config file parser/generator has a lot of simplifications

import argparse
import logging
import math
import os
import re
import sys
from datetime import datetime

logger = logging.getLogger(__name__)
logging_handler = logging.StreamHandler(stream=sys.stderr)
logging_handler.setLevel(logging.INFO)
logger.addHandler(logging_handler)
logger.setLevel(logging.INFO)


def format_dict(d, line_prefix=''):
    output = '{\n'
    for k in sorted(d):
        v = d[k]
        if isinstance(v, dict):
            v = {k: v[k] for k in sorted(v)}

        output += "%s    %s: %s\n" % (line_prefix, k, v)

    output += line_prefix + "}\n"
    return output


def parse_args():
    parser = argparse.ArgumentParser("Adapt nextcloud config.php")
    parser.add_argument("dst", nargs=1, help='config.php-file to alter')

    args = parser.parse_args()
    args.dst = args.dst[0]
    return args

def file_generator(filename):
    with open(filename, 'r', encoding='utf8') as f:
        for line in f:
            yield line

def stdin_generator():
    for line in sys.stdin:
        yield line

def parse_text(filename, generator):
    state = 0
    cfg = {}
    tmp_state = None

    def _parse_line(line, error):
        nonlocal tmp_state
        line_stripped = line.strip(' ')

        # Regular line
        m = re.fullmatch(r"'([^']+)'[ ]*=>[ ]*((?:'[^']*')|true|false|[0-9]+),", line_stripped)
        if m:
            cfg[m[1]] = m[2]
            return 2

        m = re.fullmatch(r"'([^']+)'[ ]*=>", line_stripped)
        if m:
            tmp_state = (m[1], {})
            return 10

        error("Failed to parse line '%s'" % line_stripped)

    def _parse_line_array(line, error):
        line_stripped = line.strip(' ')

        # Line within array
        m = re.fullmatch(r"((?:[0-9]|(?:[1-9][0-9]+))|(?:'(?:[^']+)'))[ ]*=>[ ]*"
                r"((?:'[^']*')|true|false|[0-9]+(?:\.[0-9]+)?),",
                line_stripped)
        if m:
            k = m[1]
            v = m[2]

            if k in tmp_state[1]:
                error("Duplicate array element '%s'" % k)

            tmp_state[1][k] = v

        else:
            error("Failed to parse line in array: '%s'" % line_stripped)

    for lineno,line in enumerate(generator):
        line = line.rstrip("\n").rstrip("\r")

        def error(msg):
            raise InvalidConfigFile(filename, lineno, msg)

        if state == 0:
            if line != "<?php":
                error("Invalid first line")
            state = 1

        elif state == 1:
            if line != "$CONFIG = array (":
                error("Invalid second line")
            state = 2

        elif state == 2:
            if line == ");":
                state = math.inf
            else:
                state = _parse_line(line, error)

        elif state == 10:
            if line.strip(' ') == "array (":
                state = 11
            else:
                error("Expected start of array")

        elif state == 11:
            if line.strip() == "),":
                cfg[tmp_state[0]] = tmp_state[1]
                tmp_state = None
                state = 2
            else:
                _parse_line_array(line, error)

        elif state == math.inf:
            error("Unexpected text near EOF")

        else:
            raise RuntimeError("invalid state")

    if state != math.inf:
        error("Unexpected EOF")

    return cfg

def update_config(src, dst):
    changed = False
    for k,v in src.items():
        if k in dst:
            if v != dst[k]:
                changed = True
                logger.info("Updating %s: %s -> %s", k, dst[k], v)
                dst[k] = v

        else:
            changed = True
            logger.info("Adding   %s: %s", k, v)
            dst[k] = v

    return changed

def _backup_file(filename):
    d = os.path.dirname(filename)
    b = os.path.basename(filename) + ".old." + datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")

    if d:
        b = os.path.join(d, b)

    if os.path.exists(b):
        print("Backup file '%s' exists already." % b, file=sys.stderr)
        sys.exit(1)

    eff_uid = os.getuid()
    if os.lstat(filename).st_uid != eff_uid and eff_uid != 0:
        print("The target file is not owned by the current effective uid, "
                "hence script must be run as root.", file=sys.stderr)
        sys.exit(1)

    fd = os.open(b, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode=0o600)
    with open(fd, 'wb') as bf:
        with open(filename, 'rb') as ff:
            while True:
                buf = ff.read(10240)
                if len(buf) == 0:
                    break

                bf.write(buf)

def write_file(cfg, filename):
    _backup_file(filename)

    with open(filename, 'w', encoding='utf8') as f:
        f.write("<?php\n$CONFIG = array (\n")
        for k,v in cfg.items():
            if isinstance(v, dict):
                # NOTE: Nextcloud's automatic config tool(s?) seem to add a
                # trailing whitespace after '=>'. Do the same to not
                # unnecessarily alter files.
                f.write("  '%s' => \n  array (\n" % (k,))
                for k2,v2 in v.items():
                    f.write("    %s => %s,\n" % (k2, v2))

                f.write("  ),\n")

            else:
                f.write("  '%s' => %s,\n" % (k, v))

        f.write(");\n")

def main():
    args = parse_args()

    try:
        src = parse_text('stdin', stdin_generator())
        dst = parse_text(args.dst, file_generator(args.dst))

        if update_config(src, dst):
            logger.info("Writing updated '%s'.", args.dst)
            write_file(dst, args.dst)
            sys.exit(20)

        else:
            logger.info("No changes detected.")
            sys.exit(0)

    except InvalidConfigFile as e:
        print(e, file=sys.stderr)
        sys.exit(1)


#********************************** Exceptions ********************************
class InvalidConfigFile(Exception):
    def __init__(self, filename, lineno, msg):
        super().__init__("error in %s:%s: %s" % (filename, lineno + 1, msg))


if __name__ == '__main__':
    main()
    sys.exit(0)
