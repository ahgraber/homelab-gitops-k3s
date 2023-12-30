# [Logseq](https://github.com/logseq/logseq)

A privacy-first, open-source platform for knowledge management and collaboration

[Logseq docs](https://docs.logseq.com/#/page/new%20to%20logseq%3F)

## Sync

Options:

1. Logseq Sync (paid)
2. **Git**
3. Syncthing
4. iCloud / Google Drive / OneDrive

[How to sync logseq with devices](https://facedragons.com/foss/sync-logseq-with-devices-free/)
[Sync logseq with git](https://hub.logseq.com/integrations/aV9AgETypcPcf8avYcHXQT/logseq-sync-with-git-and-github/krMyU6jSEN8jG2Yjvifu9i)
[Logseq Git Sync 101](https://github.com/CharlesChiuGit/Logseq-Git-Sync-101?tab=readme-ov-file)

### Sync with Git

#### Configure Repo

1. Create git repository
2. Create commit hooks in `<logseq_repo>/.git/hooks`
   1. `pre-commit`:

      ```sh
      #!/bin/sh
      #
      #
      # Pull before committing
      # Credential handling options:
      #  - hardcode credentials in URL
      #  - use ssh with key auth
      #  - https://git-scm.com/docs/git-credential-store
      #  - git credential helper on windows

      # Redirect output to stderr, uncomment for more output for debugging
      # exec 1>&2

      output=$(git pull --no-rebase)

      # Handle non error output as otherwise it gets shown with any exit code by logseq
      if [ "$output" = "Already up to date." ]; then
          # no output
          :
      else
          # probably error print it to screen
          echo "${output}"
      fi

      git add -A
      ```

   2. `post-commit`:

      ```sh
      #!/bin/sh

      git push origin main
      ```

3. Make commit hooks executable

   ```sh
   chmod +x ./pre-commit
   chmod +x ./post-commit
   ```

#### Configure Logseq App

1. Open git repo in logseq app
2. `Enable Git auto commit` in Logseq > Settings > Version Control

## Plugins

Useful plugins:

- Link Preview
- Git
- Omnivore
- Markdown Table Editor
- logseq-toc-plugin

## Self-hosting

To self-host a webapp editor, follow [docker web app guide](https://github.com/logseq/logseq/blob/master/docs/docker-web-app-guide.md).
Note that this is simply the logseq app hosted as a webapp, and the data sync must still happen externally
