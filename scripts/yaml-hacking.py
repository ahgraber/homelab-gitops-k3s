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
        hr["metadata"].pop("namespace", None)

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

    with open(hr_file, "w") as file:
        yaml.dump(hr, file)

# %%
