# clldappconfig

Scripted deployment and management of [clld web apps](https://github.com/clld/clld).
This package provides the `appconfig` command line utility as well as
[fabric tasks](https://github.com/mathiasertl/fabric/)
which can be used in fabfiles for managing individual apps.

[![Tests](https://github.com/dlce-eva/clldappconfig/actions/workflows/tests.yml/badge.svg)](https://github.com/dlce-eva/clldappconfig/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/clldappconfig.svg)](https://pypi.org/project/clldappconfig)


## command line utility usage 

To show a help message run
```
appconfig --help
```

The `appconfig` command needs a configuration directory containing the global
configuration file (`apps.ini`) and the config scripts all managed apps.
I.e. the config directory (here `apps/`) should have the following structure:

```
apps
├── apps.ini
├── README.md
├── abvd
│   ├── fabfile.py
│   ├── README.md
│   └── requirements.txt
├── acc
│   ├── fabfile.py
│   ├── README.md
│   └── requirements.txt
.
.
.
```

The config discovery is done in the following order:
1.  use argument of `--config` / `-c`
2.  use the `APPCONFIG_DIR` environment variable
3.  by default the current working directory (`./`) is assumed to be the config
	directory

So both of the following commands do the same thing:
```
appconfig --config ./path/to/appconfig/apps/ ls
env APPCONFIG_DIR=./path/to/appconfig/apps/ appconfig ls
```


## using fabfiles

For every app should provide a subdirectory of the config directory, which
contains a `fabfile.py` with the following minimal structure:

```python
from clldappconfig.tasks import *

init()
```

Inside the directory containing the fabfile you can run `fab -l` to list all
available tasks for deployment, managing databases etc.

Config discovery for the fabfiles works as follows:
1.  use the `APPCONFIG_DIR` environment variable
2.  by default the parent of the current working directory (`../`) is assumed to
	be the config directory

If you use the config directory structure as described above, you can rely on
the default behavior and usually don't need to set the `APPCONFIG_DIR`
environment variable.


## TODO:

* describe structure and options of `apps.ini`
* describe some common workflows like deploying an app
