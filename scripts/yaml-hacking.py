# %%
from pathlib import Path
from subprocess import CalledProcessError, check_output
import sys

from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter

# import yaml  # use ruamel for comment preservation


# %%
# # Custom representer to handle anchor references
# def anchor_rep(dumper, data):
#     """Represent all strings with '*' prefix as yaml anchor aliases."""
#     if isinstance(data, str) and data.startswith("*"):
#         return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=None)
#     return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# # Register the custom representer
# RoundTripRepresenter.add_representer(str, anchor_rep)

# %%
# Initialize the YAML object with round-trip capabilities
yaml = YAML(typ="rt")

# match linting expectations
yaml.explicit_start = True
yaml.indent(mapping=2, sequence=4, offset=2)


# %%
try:
    repo = check_output(["git", "rev-parse", "--show-toplevel"])  # NOQA: S603, S607
except CalledProcessError as e:
    raise IOError("Current working directory is not a git repository") from e
else:
    repo = Path(repo.decode("utf-8").strip()).resolve()

# %%
hrs = repo.glob("**/helmrelease.yaml")

for hr_file in hrs:
    with open(hr_file, "r") as file:
        hr = yaml.load(file)

        # remove field
        hr["metadata"].pop("namespace", None)

        # update to standardize
        hr["spec"].update({"interval": "15m"})
        # replace content
        hr["spec"]["install"] = {
            "remediation": {
                "retries": 3,
            },
        }
        hr["spec"]["upgrade"] = {
            "cleanupOnFail": True,
            "remediation": {
                "strategy": "rollback",
                "retries": 3,
            },
        }

        # ### not all hrs need driftDetection
        # # https://github.com/fluxcd/flux2/issues/4511
        # # https://github.com/fluxcd/helm-controller/issues/643
        # hr["spec"]["driftDetection"] = {
        #     "mode": "enabled",
        #     "ignore": [
        #         # allow resource limit mods w/o drift correction
        #         {
        #             "paths": ["/spec/containers/resources/limits"],
        #             "target": {
        #                 "kind": "Pod",
        #             },
        #         },
        #     ],
        # }

        # remove field
        hr["spec"].pop("uninstall", None)

        # ensure order of spec keys:
        keys = [
            "chart",
            "interval",
            "dependsOn",
            "install",
            "upgrade",
            "driftDetection",
            "uninstall",
            "valuesFrom",
            "values",
            "postRenderers",
        ]
        for key in keys:
            if key in hr["spec"]:
                data = hr["spec"].pop(key)  # NOQA: N816
                hr["spec"][key] = data

    with open(hr_file, "w") as file:
        yaml.dump(hr, file)

# %%
kss = repo.glob("**/ks.yaml")

for ks_file in kss:
    for i, subdoc in enumerate(yaml.load_all(ks_file)):
        # add 'targetNamespace', update so will see in git diffs
        if "targetNamespace" not in subdoc["spec"]:
            subdoc["spec"]["targetNamespace"] = ""

        # ensure commonMetadata is set
        subdoc["spec"]["commonMetadata"] = {
            "labels": {
                # "app.kubernetes.io/name": "*app",
                "app.kubernetes.io/name": subdoc["metadata"]["name"],  # pointing to another scalar value adds an alias
            }
        }

        # standardize
        subdoc["spec"].update(
            {
                "sourceRef": {
                    "kind": "GitRepository",
                    "name": "home-kubernetes",
                },
                "interval": "30m",
                "retryInterval": "1m",
                "timeout": "5m",
            }
        )

        if i == 0:
            with open(ks_file, "w") as file:
                yaml.dump(subdoc, file)
        else:
            with open(ks_file, "a") as file:
                yaml.dump(subdoc, file)

# %%
