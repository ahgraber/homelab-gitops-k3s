# %%
from pathlib import Path
from subprocess import CalledProcessError, check_output

from ruamel.yaml import YAML

# import yaml  # use ruamel for comment preservation

# %%
# Initialize the YAML object with round-trip capabilities
yaml = YAML(typ="rt")

# match linting expectations
yaml.explicit_start = True
yaml.indent(mapping=2, sequence=4, offset=2)

# %%
try:
    repo = check_output("git rev-parse --show-toplevel", shell=True)
except CalledProcessError:
    raise IOError("Current working directory is not a git repository")
else:
    repo = Path(repo.decode("utf-8").strip()).resolve()

# %%
hrs = repo.glob("**/helmrelease.yaml")

# %%
for hr_file in hrs:
    with open(hr_file, "r") as file:
        hr = yaml.load(file)

        # replace content
        hr["metadata"].pop("namespace", None)  # remove field

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
        hr["spec"].pop("uninstall", None)  # remove field

    with open(hr_file, "w") as file:
        yaml.dump(hr, file)

# %%
kss = repo.glob("**/ks.yaml")

# %%
for ks_file in kss:
    for i, subdoc in enumerate(yaml.load_all(Path(ks_file))):
        # replace content
        if "targetNamespace" not in subdoc["spec"]:
            subdoc["spec"]["targetNamespace"] = ""

        subdoc["spec"]["commonMetadata"] = {
            "labels": {"app.kubernetes.io/name": "*app"}
        }

        if i == 0:
            with open(ks_file, "w") as file:
                yaml.dump(subdoc, file)
        else:
            with open(ks_file, "a") as file:
                yaml.dump(subdoc, file)

# %%
