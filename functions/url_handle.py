import json
import logging
from typing import List

from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)


tasks = BackgroundTasks()


class BuildUrlDict:
    components = {}
    path_dict = {}
    path_queries = {}
    path_headers = {}
    path_payload = {}

    @classmethod
    def get_path_dict(cls):
        return cls.path_dict

    @classmethod
    def get_path_queries(cls):
        return cls.path_queries

    @classmethod
    def get_path_headers(cls):
        return cls.path_headers

    @classmethod
    def sync(cls):
        with open("files/openapi.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            cls.components = data["components"]
            path_dict = data["paths"]
        cls.list_to_hierarchy_dict(path_dict)
        print("Paths Synced")

    @classmethod
    def _classify_parameters(cls, parameter: dict, parameters_queries: dict):
        if parameter.get("required", False):
            parameters_queries["required"].append(parameter["name"])
        parameters_queries["optional"].append(parameter["name"])
        return parameters_queries

    @classmethod
    def build_query_params(cls, parameters: List):
        path_queries = {"required": [], "optional": []}
        path_headers = {"required": [], "optional": []}
        for parameter in parameters:
            if "$ref" not in parameter.keys() and parameter["in"] == "query":
                path_queries = cls._classify_parameters(parameter, path_queries)
            elif "$ref" not in parameter.keys() and parameter["in"] == "header":
                path_headers = cls._classify_parameters(parameter, path_headers)
            elif "$ref" in parameter.keys():
                ref = parameter["$ref"].split("/")[2:]
                actual = cls.components
                for item in ref:
                    actual = actual[item]
                if actual["in"] == "query":
                    path_queries = cls._classify_parameters(actual, path_queries)
                elif actual["in"] == "header":
                    path_headers = cls._classify_parameters(actual, path_headers)
        cls.path_headers = path_headers
        return {"queries_param": path_queries, "headers_param": path_headers}

    @classmethod
    def build_actions(cls, path: str, actions: dict):
        cls.path_queries[path] = {}
        for item in actions.items():
            key = item[0].upper()
            cls.path_queries[path][key] = cls.build_query_params(item[1]["parameters"])

    @classmethod
    def list_to_hierarchy_dict(cls, url_patterns: dict):
        url_patterns_list = []

        for pattern in url_patterns.items():

            cls.build_actions(pattern[0], pattern[1])

            pattern_parts = pattern[0].split("/")
            if pattern_parts[0] == "":
                del pattern_parts[0]
            url_patterns_list.append(pattern_parts)

        cls._build_dict(url_patterns_list)

    @classmethod
    def _build_dict(cls, url_patterns: List):
        result = {}
        for path in url_patterns:
            current_dict = result
            for element in path:
                if element not in current_dict:
                    current_dict[element] = {}
                current_dict = current_dict[element]
        cls.path_dict = result


class UrlHandler:

    @classmethod
    def sync(cls) -> None:
        tasks.add_task(BuildUrlDict.sync())

    @classmethod
    async def find_matching_url(cls, url_param: str):

        url_parts = url_param.split("/")
        if url_parts[0] == "":
            del url_parts[0]

        path = ""
        initial_path = BuildUrlDict.get_path_dict()
        keys_values = []

        for item in url_parts:
            try:
                _ = initial_path[item]
                if path == "":
                    path = item
                else:
                    path = path + "/" + item
                initial_path = initial_path[item]
            except KeyError:
                for key in initial_path.items():
                    if "{" in key[0]:
                        keys_values.append(item)
                        path = path + "/" + key[0]
                        initial_path = initial_path[key[0]]
                        break
        if path == {}:
            return "NOT FOUND"
        return BuildUrlDict.get_path_queries()["/" + path]