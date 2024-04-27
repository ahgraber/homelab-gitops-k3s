# [Task](https://taskfile.dev/)

Task is a task runner / build tool that aims to be simple and easy to use.

## Use

Once the binary is installed, tasks can be listed with:

```sh
task --list
```

To get a summary of the task args and use:

```sh
task <namespace>:<taskname> --summary
```

### Variables

Variables can be provided in tasks with `<name>=<value>` notation:

```sh
task <namespace>:<taskname> var='value'
```

If allowed, additional arbitrary strings (i.e., cli flags, etc) can be passed following a `--`:

```sh
task <namespace>:<taskname> var='value' -- '--quiet'
```
