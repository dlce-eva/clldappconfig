# https-pypi.org-project-clldappconfig-
Python package providing management functionality for clld apps

## usage

```
appconfig --config ./path/to/appconfig/apps/ ls
env APPCONFIG_DIR=./path/to/appconfig/apps appconfig ls
```

Using the old fabfiles works seemlessly with this version of appconfig.  It is
expected that the apps dir has follows the old structure, ie. it should contain
an `apps.ini` file and subdirectories for each app containing the individual
fabfiles.

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

## TODO

* make package installable, i.e. properly include datafiles, templates, etc
