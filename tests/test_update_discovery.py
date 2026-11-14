"""An unreachable or malformed update channel must preserve a usable installation."""
import json,subprocess,unittest
from unittest.mock import patch
from utils.skill_project_toolkit import available_update

class UpdateDiscovery(unittest.TestCase):
    config={'repository':'kwgjjeffrey/rsi','version':'0.1.3'}
    def latest(self,tag):
        def fetch(url,path,binary=False):path.write_text(json.dumps({'tag_name':tag}))
        with patch('utils.skill_project_toolkit.fetch',side_effect=fetch):return available_update(self.config)
    def test_a_newer_release_is_announced_without_activation(self):
        result=self.latest('v0.1.4')
        self.assertTrue(result['updateAvailable']);self.assertEqual(result['installed'],'0.1.3')
    def test_an_older_channel_never_suggests_a_downgrade(self):
        self.assertFalse(self.latest('v0.1.2')['updateAvailable'])
    def test_untrusted_tags_are_not_offered(self):
        self.assertEqual(self.latest('../../other')['status'],'unavailable')
    def test_network_failure_keeps_the_installed_version(self):
        with patch('utils.skill_project_toolkit.fetch',side_effect=subprocess.CalledProcessError(1,['curl'])):
            result=available_update(self.config)
        self.assertEqual(result['status'],'unavailable');self.assertEqual(result['installed'],'0.1.3')
if __name__=='__main__':unittest.main()
