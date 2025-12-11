#!/usr/bin/env python3
# ----------------------------------------------
# pathfix.py
# v1.0.0xg  2025/12/08  XdG / MIS Center
# ----------------------------------------------
#
"""
Change the #! line (shebang) occurring in Python scripts.  The new interpreter
pathname must be given with a -i option.

Command line arguments are files or directories to be processed.
Directories are searched recursively for files whose name looks
like a python module.
Symbolic links are always ignored (except as explicit directory
arguments).
The original file is kept as a back-up (with a "~" attached to its name),
-n flag can be used to disable this.

Sometimes you may find shebangs with flags such as `#! /usr/bin/env python -si`.
Normally, pathfix overwrites the entire line, including the flags.
To change interpreter and keep flags from the original shebang line, use -k.
If you want to keep flags and add to them one single literal flag, use option -a.


Undoubtedly you can do this using find and sed or perl, but this is
a nice example of Python code that recurses down a directory tree
and uses regular expressions.  Also note several subtleties like
preserving the file's mode and avoiding to even write a temp file
when no changes are needed for a file.

NB: by changing only the function fixfile() you can turn this
into a program for a different change to Python programs...
"""

import sys
import re
import os
from stat import ST_MODE
import getopt

err = sys.stderr.write
dbg = err
rep = sys.stdout.write

NEW_INTERPRETER = None
PRESERVE_TIMESTAMPS = False
CREATE_BACKUP = True
KEEP_FLAGS = False
ADD_FLAGS = b''


def main():  # pylint: disable=too-many-branches
    """Main program entry point."""
    global NEW_INTERPRETER  # pylint: disable=global-statement
    global PRESERVE_TIMESTAMPS  # pylint: disable=global-statement
    global CREATE_BACKUP  # pylint: disable=global-statement
    global KEEP_FLAGS  # pylint: disable=global-statement
    global ADD_FLAGS  # pylint: disable=global-statement

    usage = f'usage: {sys.argv[0]} -i /interpreter -p -n -k -a file-or-directory ...\n'
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'i:a:kpn')
    except getopt.error as msg:
        err(f'{msg}\n')
        err(usage)
        sys.exit(2)
    for o, a in opts:
        if o == '-i':
            NEW_INTERPRETER = a.encode()
        if o == '-p':
            PRESERVE_TIMESTAMPS = True
        if o == '-n':
            CREATE_BACKUP = False
        if o == '-k':
            KEEP_FLAGS = True
        if o == '-a':
            ADD_FLAGS = a.encode()
            if b' ' in ADD_FLAGS:
                err("-a option doesn't support whitespaces")
                sys.exit(2)
    if not NEW_INTERPRETER or not NEW_INTERPRETER.startswith(b'/') or \
           not args:
        err('-i option or file-or-directory missing\n')
        err(usage)
        sys.exit(2)
    bad = 0
    for arg in args:
        if os.path.isdir(arg):
            if recursedown(arg):
                bad = 1
        elif os.path.islink(arg):
            err(arg + ': will not process symbolic links\n')
            bad = 1
        else:
            if fix(arg):
                bad = 1
    sys.exit(bad)


ispythonprog = re.compile(r'^[a-zA-Z0-9_]+\.py$')


def ispython(name):
    """Check if the file is a Python script."""
    return bool(ispythonprog.match(name))


def recursedown(dirname):
    """Recursively process a directory."""
    dbg(f'recursedown({dirname!r})\n')
    bad = 0
    try:
        names = os.listdir(dirname)
    except OSError as msg:
        err(f'{dirname}: cannot list directory: {msg!r}\n')
        return 1
    names.sort()
    subdirs = []
    for name in names:
        if name in (os.curdir, os.pardir):
            continue
        fullname = os.path.join(dirname, name)
        if os.path.islink(fullname):
            pass
        elif os.path.isdir(fullname):
            subdirs.append(fullname)
        elif ispython(name):
            if fix(fullname):
                bad = 1
    for fullname in subdirs:
        if recursedown(fullname):
            bad = 1
    return bad


def fix(filename):  # pylint: disable=too-many-branches,too-many-statements,inconsistent-return-statements
    """Fix the shebang line in a file."""
##  dbg(f'fix({filename!r})\n')
    try:
        with open(filename, 'rb') as f:
            line = f.readline()
            fixed = fixline(line)
            if line == fixed:
                rep(f'{filename}: no change\n')
                return 0

            head, tail = os.path.split(filename)
            tempname = os.path.join(head, '@' + tail)
            try:
                with open(tempname, 'wb') as g:
                    rep(f'{filename}: updating\n')
                    g.write(fixed)
                    bufsize = 8*1024
                    while 1:
                        buf = f.read(bufsize)
                        if not buf:
                            break
                        g.write(buf)
            except IOError as msg:
                err(f'{tempname}: cannot create: {msg!r}\n')
                return 1
    except IOError as msg:
        err(f'{filename}: cannot open: {msg!r}\n')
        return 1

    # Finishing touch -- move files

    mtime = None
    atime = None
    # First copy the file's mode to the temp file
    try:
        statbuf = os.stat(filename)
        mtime = statbuf.st_mtime
        atime = statbuf.st_atime
        os.chmod(tempname, statbuf[ST_MODE] & 0o7777)
    except OSError as msg:
        err(f'{tempname}: warning: chmod failed ({msg!r})\n')
    # Then make a backup of the original file as filename~
    if CREATE_BACKUP:
        try:
            os.rename(filename, filename + '~')
        except OSError as msg:
            err(f'{filename}: warning: backup failed ({msg!r})\n')
    else:
        try:
            os.remove(filename)
        except OSError as msg:
            err(f'{filename}: warning: removing failed ({msg!r})\n')
    # Now move the temp file to the original file
    try:
        os.rename(tempname, filename)
    except OSError as msg:
        err(f'{filename}: rename failed ({msg!r})\n')
        return 1
    if PRESERVE_TIMESTAMPS:
        if atime and mtime:
            try:
                os.utime(filename, (atime, mtime))
            except OSError as msg:
                err(f'{filename}: reset of timestamp failed ({msg!r})\n')
                return 1
    # Return success
    return 0


def parse_shebang(shebangline):
    """Parse the shebang line."""
    shebangline = shebangline.rstrip(b'\n')
    start = shebangline.find(b' -')
    if start == -1:
        return b''
    return shebangline[start:]


def populate_flags(shebangline):
    """Populate flags for the new shebang line."""
    old_flags = b''
    if KEEP_FLAGS:
        old_flags = parse_shebang(shebangline)
        if old_flags:
            old_flags = old_flags[2:]
    if not (old_flags or ADD_FLAGS):
        return b''
    # On Linux, the entire string following the interpreter name
    # is passed as a single argument to the interpreter.
    # e.g. "#! /usr/bin/python3 -W Error -s" runs "/usr/bin/python3 "-W Error -s"
    # so shebang should have single '-' where flags are given and
    # flag might need argument for that reasons adding new flags is
    # between '-' and original flags
    # e.g. #! /usr/bin/python3 -sW Error
    return b' -' + ADD_FLAGS + old_flags


def fixline(line):
    """Fix the shebang line."""
    if not line.startswith(b'#!'):
        return line

    if b"python" not in line:
        return line

    flags = populate_flags(line)
    if NEW_INTERPRETER is None:
        return line
    return b'#! ' + NEW_INTERPRETER + flags + b'\n'


if __name__ == '__main__':
    main()
