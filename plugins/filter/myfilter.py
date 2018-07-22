# -*- coding: utf-8 -*-
# pylint: disable=C0111,E0611

# (c) 2018, Takamitsu IIDA (@takamitsu-iida)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re

from ansible.module_utils.six import string_types
from ansible.errors import AnsibleFilterError

try:
  from __main__ import display
except ImportError:
  from ansible.utils.display import Display
  display = Display()


def intf_status(stdout):

  if isinstance(stdout, string_types):
    stdout = list(stdout)

  if not isinstance(stdout, list):
    raise AnsibleFilterError("filter input should be a list of string, but was given a input of %s" % (type(stdout)))

  updown_list = []

  for s in stdout:
    if not isinstance(s, string_types):
      raise AnsibleFilterError("filter input should be a string, but was given a input of %s" % (type(s)))

    match = re.match(r'.* line protocol is (.*)', s)
    if match:
      updown_list.append(match.group(1) == "up")
    else:
      raise AnsibleFilterError("failed to parse interface status, %s" % s)

  if not updown_list:
    AnsibleFilterError("unknown interface status")

  display.vvvv("intf_status updown_list: %s " % ' '.join([str(x) for x in updown_list]))

  return all(updown_list)


# ---- Ansible filters ----

class FilterModule(object):
  """Filters for working with output from network devices
  """

  filter_map = {
    'intf_status': intf_status,
  }

  def filters(self):
    return self.filter_map
