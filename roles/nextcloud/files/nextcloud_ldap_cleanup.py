#!/usr/bin/python3
"""
Delete deleted nextcloud users after N dayes
"""

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

import json
import logging
import logging.handlers
import subprocess
import sys
from datetime import datetime, timedelta

N = 14

logger = None
def setup_logger(instance):
    global logger
    logger = logging.getLogger('nextcloud_ldap_cleanup_%s' % instance)
    logger.setLevel(logging.INFO)
    handler = logging.handlers.SysLogHandler(address='/dev/log')
    handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    logger.addHandler(handler)

def main():
    if len(sys.argv) != 2:
        print("Usage: %s <www dir name>", file=sys.stderr)
        sys.exit(2)

    instance = sys.argv[1]
    setup_logger(instance)
    nextcloud_dir = '/var/www/' + instance

    ret = subprocess.run(['sudo', '-u', 'www-data',
        'php', 'occ', 'ldap:show-remnants', '--json'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=nextcloud_dir,
        env={'LANG': 'C'})

    if ret.returncode != 0:
        logger.error("ldap:show-remnants failed: %s", ret.stdout.decode().strip())
        sys.exit(1)

    users = json.loads(ret.stdout.decode())
    if ret.stderr:
        logger.error(ret.stderr.decode())

    now = datetime.now().date()
    for u in users:
        name = u['ocName']
        dn = u['dn']
        detected = u['detectedOn']

        detected = datetime.strptime(detected, '%B %d, %Y').date()
        if now > detected + timedelta(days=N):
            logger.info("Deleting %s (%s) ...", name, dn)

            ret = subprocess.run(['sudo', '-u', 'www-data',
                'php', 'occ', 'user:delete', name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=nextcloud_dir,
                env={'LANG': 'C'})

            logger.info(ret.stdout.decode())

            if ret.returncode != 0:
                logger.error("user:delete failed.")
                sys.exit(1)


if __name__ == '__main__':
    main()
    sys.exit(0)
