"""
List registered apps.
"""
from clldutils.clilib import Table, add_format


def register(parser):
    parser.add_argument(
        "-p", "--port", default=False, action="store_true", help="Sort by port"
    )
    parser.add_argument(
        "-a",
        "--administrative",
        default=False,
        action="store_true",
        help="List administrative metadata",
    )
    add_format(parser, default="simple")


def run(args):
    cols = {
        "default": ["id", "url", "server", "port", "public"],
        "administrative": ["id", "url", "editors", "contact"],
    }["administrative" if args.administrative else "default"]
    table = []
    for a in args.apps.values():
        table.append(
            dict(
                id=a.name,
                url="https://{0}".format(a.domain),
                server=a.production,
                port="{0}".format(a.port),
                editors=a.editors,
                contact=a.contact,
                public="{0}".format(a.public),
            )
        )
        if a.test:
            table.append(
                dict(
                    id="{0} [test]".format(a.name),
                    url="http://{0}/{1}".format(a.test, a.name),
                    server=a.test,
                    port="{0}".format(a.port),
                    editors="",
                    contact="",
                    public="{0}".format(False),
                )
            )

    if args.port:
        sortkey = lambda t: int(t["port"])
    else:
        sortkey = lambda t: (t["server"], t["id"])

    with Table(args, "#", *cols) as t:
        for i, r in enumerate(sorted(table, key=sortkey)):
            t.append(["{0}".format(i + 1)] + [r[col] for col in cols])
