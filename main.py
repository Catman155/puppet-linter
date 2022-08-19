import os
import time
import argparse

from termcolor import colored

from constants import SPLIT_TOKEN, LOG_TYPE_FATAL, LOG_TYPE_ERROR, LOG_TYPE_WARNING, LOG_TYPE_INFO, LOG_TYPE_DEBUG
from parser import walk_content
from puppet_objects.puppet_file import PuppetFile
from utility import get_file_contents, get_all_files, add_log, clear_logs, get_logs
from validate import process_puppet_module


def process_file(path) -> PuppetFile:
    content = get_file_contents(path)
    puppet_file = PuppetFile(path)
    walk_content(content, puppet_file)
    return puppet_file


def print_logs(log_level=1):
    no_errors = True
    no_warnings = True

    for log_item in get_logs():
        typ = log_item[1]
        if typ >= log_level:
            if typ == LOG_TYPE_FATAL:
                print(colored(log_item, 'white', 'on_red'))
            if typ == LOG_TYPE_ERROR:
                print(colored(log_item, 'red'))
                no_errors = False
            if typ == LOG_TYPE_WARNING:
                print(colored(log_item, 'yellow'))
                no_warnings = False
            if typ == LOG_TYPE_INFO:
                print(colored(log_item, 'white'))
            if typ == LOG_TYPE_DEBUG:
                print(colored(log_item, 'cyan'))

    if no_errors and no_warnings:
        print(colored("No Errors/Warnings Found", "green"))

    clear_logs()


def main(path, module_name, log_level=LOG_TYPE_WARNING, print_tree=False, only_parse=True):
    files = get_all_files(path)
    puppet_files = [f for f in files if f.endswith(".pp") and not f.split(SPLIT_TOKEN)[-1].startswith(".")]

    path = os.path.normpath(path)
    path = os.path.abspath(path)

    start = time.time()

    total = []

    for f in puppet_files:
        print(colored("Processing file: .%s" % f.replace(path, ""), 'cyan'))

        try:
            total.append(process_file(f))
        except Exception as e:
            import traceback
            add_log(f, LOG_TYPE_FATAL, (0, 0), "FATAL: Panic during file parsing, " + str(e), "")
            traceback.print_exc()

        print_logs(log_level)

    print("parsing took %f seconds" % (time.time() - start))

    if print_tree:
        for i in total:
            print(i)
            i.print_items()

    if only_parse:
        return

    start = time.time()

    process_puppet_module(total, module_name, path)
    print_logs(log_level)

    print("validating took %f seconds" % (time.time() - start))


if __name__ == '__main__':
    my_parser = argparse.ArgumentParser(
        description="Puppet Tools, including parser, linter and validator functions"
    )

    my_parser.add_argument("-t",
                           "--print-tree",
                           action='store_true',
                           help="Print the tree of parsed objects")

    my_parser.add_argument("-op",
                           "--only-parse",
                           action='store_true',
                           help="Only parse for format validating/linting")

    my_parser.add_argument("-l",
                           "--log-level",
                           type=int,
                           default=2,
                           help="Set minimum log level (Info=2, Warning=3, Error=4, Fatal=5)")

    my_parser.add_argument("Path",
                           metavar="path",
                           type=str,
                           help="the path to a puppet module")

    my_parser.add_argument("ModuleName",
                           metavar="module_name",
                           type=str,
                           help="The name of the puppet module to be used")

    args = my_parser.parse_args()

    check_path = args.Path

    if not os.path.isdir(check_path):
        print("The path specified does not exist")
        exit(1)

    if not os.path.exists(os.path.join(check_path, "files")) or not os.path.exists(os.path.join(check_path, "manifests")):
        print("Not a valid puppet module structure at path")
        exit(1)

    main(check_path, args.ModuleName, log_level=args.log_level, print_tree=args.print_tree, only_parse=args.only_parse)
