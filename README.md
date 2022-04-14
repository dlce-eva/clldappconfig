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
configuration file (`apps.ini`) and the fabfiles for all managed apps.
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

The discovery of the configuration file is done in the following order:
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

Every app should provide a subdirectory in the config directory, which
contains a `fabfile.py` with the following minimal structure:

```python
from clldappconfig.tasks import *

init()
```

Inside the directory containing the fabfile you can run `fab -l` to list all
available tasks for deployment, managing databases etc.

Config discovery when using a fabfile works as follows:
1.  use the `APPCONFIG_DIR` environment variable
2.  by default the parent of the current working directory (`../`) is assumed to
	be the config directory

If you use the config directory structure as described above, you can rely on
the default behavior and usually don't need to set the `APPCONFIG_DIR`
environment variable.


## Common workflows


### Deploying new code

All new code must be pushed to the app's repository on GitHub.  While no local
installation of the app or a local database are required, it is recommended to
run the app's tests before deployment.

1. Activate the "remote control":
```
$ workon clldappconfig
```

2. Change into the config directory for the app:
```
$ cd $APPCONFIG_DIR/<app>
```

3. Run the `deploy` task, passing a deployment mode as argument.
There are three deployment modes:
- `production`: The app is deployed
  - under its specified domain
  - using a separate nginx site
  - forcing HTTPS.
- `test`: The app is deployed
  - mounted at the `app.name` path on the default server
  - forcing HTTPS (for the default server)
- `staging`: The app is deployed
  - under its specified domain
  - using a separate nginx site
  - serving via HTTP

Thus, `production` and `test` mode should only be used with the configured
servers, because otherwise retrieving the required certificates from letsencrypt
will fail.

To deploy the app to a custom server, e.g. a virtualbox on the local machine,
use `staging` mode with `fab`'s `-H` option, e.g.

```
$ fab -H vbox deploy:staging
```

Answer the prompts `Recreate database?` and `Upgrade database?` in the negative.

When you deploy production code, clldappconfig will create or update a
`requirements.txt` file inside the app's config directory, to allow accurate
assessment of the production environment.  If you manage your configuration in a
git repository, make sure to commit these changes.


### Deploying new data

New data can be deployed in two ways, either via alembic migrations, altering an
existing database, or by replacing the database wholesale.  In the first case,
the migration must be pushed to the app's repository on GitHub; in the second
case a local app database must be available.

As above, activate `appconfig`, change into the app's config directory and start
the `deploy` task. In case of a database migration, answer `Recreate database?`
in the negative and run the migrations on the host by confirming `Upgrade
database?`.  For wholesale replacemement, confirm `Recreate database?`.

Note: Deploying new data implies deploying new code.


## Moving an app

To move an app from one server to another, follow these steps:

1. Navigate to the app's config directory:
   ```
   cd apps/<app>
   ```

2. Retrieve the production database:
   ```
   fab load_db:production
   ```

3. Verify that the database has been received correctly by running the app tests
   locally.

4. Update the app's deployment target by editing the `production` option in the
   `[<app>]` section of your `$APPCONFIG_DIR/apps.ini`.

5. Update the DNS entry for the app. (This is required in order to be able to
   retrieve a certificate from letsencrypt upon deploy.)

6. Deploy the app running
   ```
   fab deploy:production
   ```
   answering `y` to recreate the database.

7. Temporarily re-set the deployment target to the old host and uninstall
   ```
   git checkout $APPCONFIG_DIR/apps.ini
   fab uninstall:production
   ```

8. Set app's deployment target in `$APPCONFIG_DIR/apps.ini`, review changes, commit and push:
   ```
   git diff
   git commit -a -m"moved app"
   git push origin
   ```
