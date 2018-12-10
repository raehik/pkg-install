#!/usr/bin/env python3
#
# Install selected packages using files from a directory.
#

import sys
import os
import argparse
import subprocess
import time

FILENAME = sys.argv[0]

CMD_FILE_IDENT = "# COMMAND FILE"

GH_FILE_IDENT = "# GITHUB FILE"
GH_URL = "https://github.com"
GH_TMPDIR = "/tmp"

COMMENT_IDENT = "#"
AUR_IDENT = "aur: "
INCLUDE_IDENT = "include: "

ORIG_PWD = os.getcwd()

def_pkgfile_dir = "packages"
aur_helper_cmd = "yay"
pkg_install_cmd = "sudo pacman -Sy"

pkg_list = []
aur_pkg_list = []



"""Argparse override to print usage to stderr on argument error."""
class ArgumentParserUsage(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        self.print_help(sys.stderr)
        sys.exit(2)

"""Print usage and exit depending on given exit code."""
def usage(exit_code):
    if exit_code == 0:
        pipe = sys.stdout
    else:
        # if argument was non-zero, print to STDERR instead
        pipe = sys.stderr

    parser.print_help(pipe)
    sys.exit(exit_code)

"""Log a message to a specific pipe (defaulting to stdout)."""
def log_message(message, pipe=sys.stdout):
    print(message, file=pipe)

"""If verbose, log an event."""
def log(message):
    #if not args.verbose:
    #    return
    log_message(message)

"""Log an error. If given a 2nd argument, exit using that error code."""
def error(message, exit_code=None):
    log_message("error: " + message, sys.stderr)
    if exit_code:
        sys.exit(exit_code)

def process_files(pkg_files):
    for f in pkg_files:
        filename = os.path.join(pkgfile_dir, f)
        log("FILE: %s" % filename)

        # get first line of file
        cur_file = open(filename, "r")
        first_line = cur_file.readline().strip()

        if first_line.startswith(CMD_FILE_IDENT):
            process_command_file(filename)
        elif first_line.startswith(GH_FILE_IDENT):
            process_gh_file(filename)
        else:
            # not special, assume 'normal' package file
            process_pkg_file(filename)

def process_pkg_file(filename):
    log("PACKAGE FILE: %s" % filename)
    for line in open(filename, "r"):
        line = line.strip()
        if line == "":
            # empty line, skip w/o logging
            continue
        if line.startswith(INCLUDE_IDENT):
            # specifying package file(s) to include
            process_include(line[len(INCLUDE_IDENT):])
        elif line.startswith(AUR_IDENT):
            # aur package(s)
            process_aur_pkg(line[len(AUR_IDENT):])
        elif line.startswith(COMMENT_IDENT):
            # comment
            process_comment(line[len(COMMENT_IDENT):])
        else:
            # normal line indicating package(s)
            process_pkg(line)

def process_comment(line):
    log("COMMENT: %s" % line.strip())

def process_include(line):
    log("INCLUDE: %s" % line)
    # recursion boyssss
    process_files(line.split())

def process_aur_pkg(line):
    log("AUR: %s" % line)
    for pkg in line.split():
        aur_pkg_list.append(pkg)

def process_pkg(line):
    log("PACKAGES: %s" % line)
    for pkg in line.split():
        pkg_list.append(pkg)

def process_command_file(filename):
    log("COMMAND FILE: %s" % filename)
    try:
        subprocess.call(["bash", "%s" % filename])
    except KeyboardInterrupt:
        log("cancelled command file execution")

def process_gh_file(filename):
    log("GITHUB FILE: %s" % filename)
    with open(filename, "r") as f:
        # skip first line (= identifier)
        f.readline()
        raw_info = f.read().splitlines()
        repo_info = process_gh_info(raw_info)

    for repo in repo_info:
        repo_name = repo[0]
        repo_dir = repo[1]
        post_cmd = repo[2]

        if not repo_dir:
            log("No repo directory given, using %s" % GH_TMPDIR)
            repo_dir = GH_TMPDIR + "/pkg-install-" + time.strftime("%s")

        repo_url = os.path.join(GH_URL, repo_name)
        log("Cloning {} into {}...".format(repo_url, repo_dir))
        subprocess.call("git clone '" + repo_url + "' " + repo_dir, shell=True)

        if post_cmd:
            log("Post command found: %s" % post_cmd)
            subprocess.call("cd " + repo_dir + "; " + post_cmd, shell=True)

def process_gh_info(raw_info):
    info = []

    for i in range(0, len(raw_info), 3):
        line_1 = raw_info[i]

        try:
            line_2 = raw_info[i+1]
        except IndexError:
            line_2 = ""

        try:
            line_3 = raw_info[i+2]
        except IndexError:
            line_3 = ""

        info.append([line_1, line_2, line_3])

    return info


def install_aur_pkgs(pkgs):
    cmd = aur_helper_cmd.split()
    cmd.extend(pkgs)
    log("INSTALL CMD: %s" % " ".join(cmd))
    try:
        subprocess.call(cmd)
    except KeyboardInterrupt:
        log("cancelled AUR package install")

def install_pkgs(pkgs):
    cmd = pkg_install_cmd.split()
    cmd.extend(pkgs)
    log("INSTALL CMD: %s" % " ".join(cmd))
    try:
        subprocess.call(cmd)
    except KeyboardInterrupt:
        log("cancelled normal package install")



parser = ArgumentParserUsage(description="Install selected packages using files from a directory.")

# add arguments
parser.add_argument("-a", "--all", help="use all files found in the package file directory (default %s)" % def_pkgfile_dir,
                    action="store_true")
parser.add_argument("-d", "--pkg-dir", help="change package file directory",
                    action="store")
parser.add_argument("-v", "--verbose", help="be verbose",
                    action="store_true")
parser.add_argument("file", nargs="+", help="file(s) to use")

# parse arguments
args = parser.parse_args()



if args.pkg_dir:
    pkgfile_dir = args.pkg_dir
else:
    pkgfile_dir = def_pkgfile_dir

if args.file == ["all"]:
    # only file specified was 'all': special meaning, use all package files
    pkg_files = [ f for f in os.listdir(pkgfile_dir) if os.path.isfile(os.path.join(pkgfile_dir, f)) ]
else:
    # args = package files to use
    pkg_files = args.file

process_files(pkg_files)

# AUR packages
if len(aur_pkg_list) > 0:
    install_aur_pkgs(aur_pkg_list)

# normal packages
if len(pkg_list) > 0:
    install_pkgs(pkg_list)
