import json
import urllib.request
import os
import argparse

official_update_list = "https://updates.jenkins.io/update-center.json"
official_plugin_location = "https://updates.jenkins-ci.org/download/plugins/"

class JenkinsDownloader(object):
    def __init__(self, update_list=official_update_list,
                 plugin_location=official_plugin_location,
                 plugins=[]):
        self.update_list = update_list
        self.plugin_location = plugin_location
        self.plugins = plugins

        self._update_data_cache = None

    def get(self, download_location="."):
        self.to_download = {}

        for plugin in self.plugins:
            self.add_plugin(plugin)

        self.download_all(download_location)

    def add_plugin(self, plugin):
        data = self.plugin_dict[plugin]
        self.to_download[plugin] = data["url"]
        if "dependencies" in data:
            for dep in data["dependencies"]:
                self.add_plugin(dep["name"])

    @property
    def plugin_dict(self):
        if self._update_data_cache:
            return self._update_data_cache["plugins"]

        with urllib.request.urlopen(self.update_list) as f:
            lines = f.readlines()
            assert lines[0] == b"updateCenter.post(\n"
            assert lines[2] == b");"
            self._update_data_cache = json.loads(lines[1].strip())
        
        return self._update_data_cache["plugins"]

    def download_all(self, download_location):
        if not os.path.isdir(download_location):
            os.makedirs(download_location)

        for plugin in self.to_download.values():
            self.download_file(plugin, download_location)

    def download_file(self, url, download_location):
        print("Getting: " + url)
        with urllib.request.urlopen(url) as f:
            fname = os.path.basename(f.geturl())
            full_loc = os.path.join(download_location, fname)
            print(" to " + full_loc)
            with open(full_loc, 'wb') as out:
                out.write(f.read())

if __name__ == "__main__":
    description = 'Download Jenkins plugins for an offline installation.'
    description += ' This will take the input list of plugins and recursively'
    description += ' find the dependencies needed for them.'

    parser = argparse.ArgumentParser(
        description=description)
    parser.add_argument('-u', '--update-list', default=official_update_list,
                        help='update list to use')
    parser.add_argument('-d', '--plugin-location',
                        default=official_plugin_location,
                        help='location to download plugins from')
    parser.add_argument('-c', '--config', default=None,
                        help='config file with options')
    parser.add_argument('-p', '--plugin', store="append",
                        help='plugin to search for')

    args = parser.parse_args()


    if args.config:
        with open(args.config) as f:
            start_data = json.load(f)

    j = JenkinsDownloader(
        update_list=start_data["update_list"],
        plugin_location=start_data["plugin_location"],
        plugins=start_data["plugins"])
    j.get("download")