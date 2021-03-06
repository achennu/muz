# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import logging, shutil, os
log = logging.getLogger(__name__)

import muz
import muz.vfs
import muz.beatmap

name = "μz beatmap"
extensions = ["beatmap"]
inferExtensions = extensions
locations = ["beatmaps"]

VERSION = "1"

class ParseError(Exception):
    pass

def read(fobj, filename, bare=False, options=None):
    buf = b""
    bmap = muz.beatmap.Beatmap(None, 1)
    initialized = False
    essentialParsed = False
    maxnotes = 0

    while True:
        byte = fobj.read(1)

        if not byte:
            break

        if byte in (b'\r', b'\n'):
            if buf:
                buf = buf.decode('utf-8')

                if buf[0] != '#':
                    s, args = buf.split(' ', 1)

                    if s == "version":
                        if initialized:
                            log.warning("duplicate 'version' statement ignored")
                        else:
                            initialized = True
                            if args != VERSION:
                                log.warning("unsupported version %s", repr(args))
                    elif not initialized:
                        raise ParseError("statement %s encountered before 'version'" % s)
                    elif s == "meta":
                        key, val = args.split(' ', 1)
                        bmap.meta[key] = val
                    elif s == "essential":
                        if essentialParsed:
                            log.warning("duplicate 'essential' statement ignored")
                        elif not bare:
                            args = args.split(' ', 2)

                            maxnotes = int(args[0])
                            bmap.numbands = int(args[1])
                            bmap.music = args[2]

                        essentialParsed = True
                    elif s == "rate":
                        bmap.noterate = float(args)
                    elif s == "note":
                        if not bare and essentialParsed:
                            args = args.split(' ')
                            bmap.append(muz.beatmap.Note(
                                *(int(a) for a in args[:2] + [args[2] if len(args) > 2 else 0])
                            ))
                    else:
                        log.warning("unknown statement %s ignored", repr(s))
            buf = b""
            continue

        buf += byte
    
    if not bare:
        if len(bmap) < maxnotes:
            log.warning("premature EOF: expected %i notes, got %i", maxnotes, len(bmap))

        if not essentialParsed or not maxnotes > 0:
            raise ParseError("empty beatmap")

    bmap.applyMeta()
    return bmap

def write(bmap, fobj, options=None):
    mus = bmap.music.encode('utf-8')

    fobj.write(("# generated by %s-%s\nversion 1\nessential %i %i %s\nrate %f\n" %
                (muz.NAME, muz.VERSION, len(bmap), bmap.numbands, mus, bmap.noterate)
               ).encode('utf-8'))

    for key, val in sorted(bmap.meta.items(), key=lambda p: p[0]):
        fobj.write("meta %s %s\n" % (key, val.encode('utf-8')))

    for note in bmap:
        fobj.write("note %i %i%s\n" % (note.band, note.hitTime, (" " + str(note.holdTime)) if note.holdTime else ""))

    return bmap.name, "%s/%s.%s" % (locations[0], bmap.name, extensions[0]), "%s/%s" % (locations[0], os.path.splitext(mus)[0])
