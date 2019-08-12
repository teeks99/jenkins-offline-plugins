__author__ = "Thomas Kent"
__copyright__ = "Copyright (C) 2019 Thomas Kent"
__license__ = "Apache 2.0"

import json
import urllib.request
import urllib.parse
import os
import argparse

official_update_list = "https://updates.jenkins.io/update-center.json"
official_plugin_location = "https://updates.jenkins-ci.org/download/plugins/"

class JenkinsDownloader(object):
    def __init__(self, update_list=official_update_list,
                 plugin_location=official_plugin_location,
                 plugins=[], headers={}):
        self.update_list = update_list
        self.plugin_location = plugin_location
        self.plugins = plugins
        self.headers = headers

        self._update_data_cache = None

    def get(self, download_location="."):
        self.to_download = {}

        for plugin in self.plugins:
            self.add_plugin(plugin)

        self.download_all(download_location)

    def add_plugin(self, plugin):
        if not plugin in self.plugin_dict:
            print("Invalid plugin lookup: " + plugin)
            return
        data = self.plugin_dict[plugin]
        self.to_download[plugin] = self.url(data)
        if "dependencies" in data:
            for dep in data["dependencies"]:
                self.add_plugin(dep["name"])

    @property
    def plugin_dict(self):
        if self._update_data_cache:
            return self._update_data_cache["plugins"]

        lines = []
        if self.update_list.startswith("http"):
            r = urllib.request.Request(self.update_list, headers=self.headers)
            with urllib.request.urlopen(r) as f:
                lines = f.readlines()
        else:
            with open(self.update_list, "rb") as f:
                lines = f.readlines()
        
        assert lines[0] == b"updateCenter.post(\n"
        assert lines[2] == b");"
        self._update_data_cache = json.loads(lines[1].strip())
        
        return self._update_data_cache["plugins"]

    def url(self, data):
        insecure_offical_plugins = "http" + official_plugin_location[5:]

        tail = ""
        original_url = data["url"]
        if original_url.startswith("http://"):
            tail = original_url.split(insecure_offical_plugins)[1]
        else:
            tail = original_url.split(official_plugin_location)[1]
        return self.plugin_location + tail

    def download_all(self, download_location):
        if not os.path.isdir(download_location):
            os.makedirs(download_location)

        for plugin in self.to_download.values():
            self.download_file(plugin, download_location)

    def download_file(self, url, download_location):
        print("Getting: " + url)
        if url.startswith("http"):
            r = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(r) as f:
                fname = os.path.basename(f.geturl())
                full_loc = os.path.join(download_location, fname)
                self.copy_file_local(f, full_loc)
        else:
            with open(url, "rb") as f:
                fname = os.path.split(url)
                full_loc = os.path.join(download_location, fname)
                self.copy_file_local(f, full_loc)

    def copy_file_local(self, fileobj, output_location):
            print(" to " + output_location)
            with open(output_location, 'wb') as out:
                out.write(fileobj.read())

if __name__ == "__main__":
    description = 'Download Jenkins plugins for an offline installation.'
    description += ' This will take the input list of plugins and recursively'
    description += ' find the dependencies needed for them.'

    parser = argparse.ArgumentParser(
        description=description)
    parser.add_argument(
        '-u', '--update-list', default=None,
        help='update list to use (default={})'.format(official_update_list))
    parser.add_argument(
        '-l', '--plugin-location', default=None,
        help='location to download plugins from (default={})'.format(
        official_plugin_location))
    parser.add_argument(
        '-c', '--config', default=None, help='config file with options')
    parser.add_argument(
        '-p', '--plugin', action='append', dest='plugins',
        help='plugin name (add this option as many times as needed')
    parser.add_argument(
        '-H', '--header', action='append', dest='headers',
        help='colon seperated curl header, e.g. -H X-First-Name:Joe')
    parser.add_argument(
        '-d', '--download', default='download',
        help="location to download plugins into (create if doesn't exist")

    args = parser.parse_args()

    plugins = []
    headers = {}
    update_list = official_update_list
    plugin_location = official_plugin_location

    if args.config:
        with open(args.config) as f:
            start_data = json.load(f)

        if "update_list" in start_data:
            update_list = start_data["update_list"]

        if "plugin_location" in start_data:
            plugin_location = start_data["plugin_location"]

        if "plugins" in start_data:
            plugins.extend(start_data["plugins"])

        if "headers" in start_data:
            headers.update(start_data["headers"])

    if args.update_list:
        update_list = args.update_list

    if args.plugin_location:
        plugin_location = args.plugin_location

    if args.plugins:
        plugins.extend(args.plugins)

    if args.headers:
        for hs in args.headers:
            key, value = hs.split(':')
            headers[key] = value

    j = JenkinsDownloader(
        update_list=update_list, plugin_location=plugin_location,
        plugins=plugins, headers=headers)
    j.get(args.download)