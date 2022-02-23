# https-pypi.org-project-clldappconfig-
Python package providing management functionality for clld apps

## usage

``sh
appconfig --config ./path/to/appconfig/apps/ ls

env APPCONFIG_DIR=./path/to/appconfig/apps appconfig ls
``

## TODO

* somehow call `appconfig.init` function from fabfiles
* adjust tests, maybe provide a test `apps/` dir
* make package installable, i.e. properly include datafiles, templates, etc