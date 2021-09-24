# postgresql

Postgres is a ...

## Installation

Install using Helm chart.  Modify [configMap-init.yaml](configMap-init.yaml) to include any databases/users that need to be create on initial install (see `initdb` command at end).

## Create DB and User

### Prerequisites

Install psql cli with `homebrew`

```sh
brew install libpq

# symlink all tools from libpq into /usr/local/bin
brew link --force libpq
```

### Creation script

If additional databases are required after install, run below commands

```sh
# DB and User name
# export ROOT_PWD="${SECRETS_DB_ROOT_PWD}"
# export USER_PWD="${SECRETS_DB_USER_PWD}"
DB="authentik"

function initdb {
  echo "Creating \"$1\" user and database"

  # note: if this presents problems in the future, look into heredoc indentations
  psql "postgresql://postgres:${SECRETS_DB_ROOT_PWD}@${SETTINGS_METALLB_POSTGRES}:5432" -e <<EOSQL
CREATE USER $1 WITH LOGIN PASSWORD '${SECRETS_DB_USER_PWD}';
CREATE DATABASE "$1";
GRANT ALL PRIVILEGES ON DATABASE "$1" TO "$1";
EOSQL
}

initdb "${DB}"
unset DB
# unset ROOT_PWD
# unset USER_PWD

# # Variables contained in an unescaped or unquoted heredoc will be expanded
# # by the *local* shell *before* the local shell executes the ssh command
# # The solution is to use an escaped or single-quoted heredoc, <<\EOF or <<'EOF'
# # or only escape the variables in the heredoc that should *not* be expanded locally
# # Thus, variables listed above do NOT get escaped; all other variables DO get escaped
# ssh root@truenas.ninerealmlabs.com 'bash -s' << EOF
# # transfer variable data
# export DB="${DB}"
# export ROOT_PWD="${ROOT_PWD}"
# export USER_PWD="${ROOT_PWD}"

# function initdb {
#   echo "Creating \"$1\" user and database"

#   # note: if this presents problems in the future, look into heredoc indentations
#   psql "postgresql://postgres:$ROOT_PWD@localhost:5432" -e <<EOSQL
# CREATE USER $1 WITH LOGIN PASSWORD '$USER_PWD';
# CREATE DATABASE "$1";
# GRANT ALL PRIVILEGES ON DATABASE "$1" TO "$1";
# EOSQL
# }

# initdb \${DB}
# unset DB
# unset ROOT_PWD
# unset USER_PWD
```
