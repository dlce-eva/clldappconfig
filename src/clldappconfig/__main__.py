import sys
import contextlib
import os

from clldutils.clilib import register_subcommands, get_parser_and_subparsers, ParserError
from clldutils.loglib import Logging

import clldappconfig as appconfig
import clldappconfig.commands


def main(args=None, catch_all=False, parsed_args=None, log=None):
    parser, subparsers = get_parser_and_subparsers('appconfig')
    register_subcommands(subparsers, clldappconfig.commands)

    parser.add_argument(
        '-c', '--config',
        nargs=1,
        default=[os.getenv('APPCONFIG_DIR', './')],
        help='path to apps dir, which also should contain apps.ini',
        dest='config_dir')

    args = parsed_args or parser.parse_args(args=args)

    if (not hasattr(args, 'main')) or (not hasattr(args, 'config_dir')):
        parser.print_help()
        return 1

    try:
        appconfig.init(args.config_dir[0])
    except (FileNotFoundError, ValueError) as e:
        print(e)
        return(1)

    args.apps = appconfig.APPS

    with contextlib.ExitStack() as stack:
        if not log:  # pragma: no cover
            stack.enter_context(Logging(args.log, level=args.log_level))
        else:
            args.log = log
        try:
            return args.main(args) or 0
        except KeyboardInterrupt:  # pragma: no cover
            return 0
        except ParserError as e:  # pragma: no cover
            print(e)
            return main([args._command, '-h'])
        except Exception as e:  # pragma: no cover
            if catch_all:
                print(e)
                return 1
            raise


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main() or 0)
