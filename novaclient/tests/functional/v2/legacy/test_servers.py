#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime

from oslo_utils import timeutils
from oslo_utils import uuidutils

from novaclient.tests.functional import base


class TestServersBootNovaClient(base.ClientTestBase):
    """Servers boot functional tests."""

    COMPUTE_API_VERSION = "2.1"

    def _boot_server_with_legacy_bdm(self, bdm_params=()):
        volume_size = 1
        volume_name = uuidutils.generate_uuid()
        volume = self.cinder.volumes.create(size=volume_size,
                                            name=volume_name,
                                            imageRef=self.image.id)
        self.wait_for_volume_status(volume, "available")

        bdm_params = ':'.join(bdm_params)
        if bdm_params:
            bdm_params = ''.join((':', bdm_params))

        server_info = self.nova("boot", params=(
            "%(name)s --flavor %(flavor)s --poll "
            "--block-device-mapping vda=%(volume_id)s%(bdm_params)s" % {
                "name": uuidutils.generate_uuid(), "flavor":
                    self.flavor.id,
                "volume_id": volume.id,
                "bdm_params": bdm_params}))
        server_id = self._get_value_from_the_table(server_info, "id")

        self.client.servers.delete(server_id)
        self.wait_for_resource_delete(server_id, self.client.servers)

    def test_boot_server_with_legacy_bdm(self):
        # bdm v1 format
        # <id>:<type>:<size(GB)>:<delete-on-terminate>
        # params = (type, size, delete-on-terminate)
        params = ('', '', '1')
        self._boot_server_with_legacy_bdm(bdm_params=params)

    def test_boot_server_with_legacy_bdm_volume_id_only(self):
        self._boot_server_with_legacy_bdm()

    def test_boot_server_with_net_name(self):
        server_info = self.nova("boot", params=(
            "%(name)s --flavor %(flavor)s --image %(image)s --poll "
            "--nic net-name=%(net-name)s" % {"name": uuidutils.generate_uuid(),
                                             "image": self.image.id,
                                             "flavor": self.flavor.id,
                                             "net-name": self.network.label}))
        server_id = self._get_value_from_the_table(server_info, "id")

        self.client.servers.delete(server_id)
        self.wait_for_resource_delete(server_id, self.client.servers)


class TestServersListNovaClient(base.ClientTestBase):
    """Servers list functional tests."""

    COMPUTE_API_VERSION = "2.1"

    def _create_servers(self, name, number):
        return [self._create_server(name) for i in range(number)]

    def test_list_with_limit(self):
        name = uuidutils.generate_uuid()
        self._create_servers(name, 2)
        output = self.nova("list", params="--limit 1 --name %s" % name)
        # Cut header and footer of the table
        servers = output.split("\n")[3:-2]
        self.assertEqual(1, len(servers), output)

    def test_list_with_changes_since(self):
        now = datetime.datetime.isoformat(timeutils.utcnow())
        name = uuidutils.generate_uuid()
        self._create_servers(name, 1)
        output = self.nova("list", params="--changes-since %s" % now)
        self.assertIn(name, output, output)
        now = datetime.datetime.isoformat(timeutils.utcnow())
        output = self.nova("list", params="--changes-since %s" % now)
        self.assertNotIn(name, output, output)

    def test_list_all_servers(self):
        name = uuidutils.generate_uuid()
        precreated_servers = self._create_servers(name, 3)
        # there are no possibility to exceed the limit on API side, so just
        # check that "-1" limit processes by novaclient side
        output = self.nova("list", params="--limit -1 --name %s" % name)
        # Cut header and footer of the table
        for server in precreated_servers:
            self.assertIn(server.id, output)
