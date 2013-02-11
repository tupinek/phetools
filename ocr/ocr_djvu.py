#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
sys.path.append('/home/phe/wsbot')
import os
import ocr
import wshocr
import hashlib
import multiprocessing

djvulibre_path = '/home/phe/bin/'

def get_nr_pages_djvu(filename):
    text = ''
    cmdline = djvulibre_path + 'djvused -e n "' + filename + '"'
    fd = os.popen(cmdline)
    for t in fd.readlines():
        text += t
    ret = fd.close()
    if ret != None:
        print "Error:", cmdline, "fail to exec", ret
        return None
    return int(text)

def do_exec(cmdline):
    fd = os.popen(cmdline)
    for t in fd.readlines():
        print t.strip("\n")
    ret = fd.close()
    if ret != None:
        # on error ret is a tuple (pid, status) status low byte is signal
        # number, high byte is exit status (if low byte = 0), bit 7 of low
        # byte is set if a core file has been generated
        print "Error:", cmdline, "fail to exec", ret
        return False
    return True

def do_one_page(opt, page_nr, filename):
    tiff_name = 'page_%04d.tif' % page_nr
    cmdline  = djvulibre_path + 'ddjvu -format=tiff -page=%d ' % page_nr
    cmdline += '"' + filename + '" ' + tiff_name

    do_exec(cmdline)

    ocr.ocr(tiff_name, 'page_%04d' % page_nr, opt.lang, opt.config)

    os.remove(tiff_name)

def do_file(job_queue, opt, filename):
    while True:
        page_nr = job_queue.get()
        if page_nr == None:
            print "Stopping thread"
            return
        do_one_page(opt, page_nr, filename)

def sha1(filename):
    # FIXME: inefficient in memory usage
    fd = open(filename)
    h = hashlib.sha1()
    h.update(fd.read())
    fd.close()
    h = h.hexdigest()

    return h

def write_sha1(sha1):
    fd = open('sha1.sum', 'w')
    fd.write(sha1)
    fd.close()

def ocr_djvu(opt, filename):
    write_sha1(sha1(filename))

    # informative only, unused at the moment
    cache_path = wshocr.cache_path(unicode(filename, 'utf-8'))
    print cache_path

    nr_pages = get_nr_pages_djvu(filename)
    if opt.num_thread == 1:
        for nr in range(1, nr_pages + 1):
            print >> sys.stderr, str(nr) + '/' + str(nr_pages), '\r',
            do_one_page(opt, nr, filename)
    else:
        thread_array = []
        job_queue = multiprocessing.Queue(opt.num_thread * 16)
        args = (job_queue, opt, filename)
        for i in range(opt.num_thread):
            print "starting thread"
            t = multiprocessing.Process(target=do_file, args=args)
            t.daemon = True
            t.start()
            thread_array.append(t)

        for nr in range(1, nr_pages + 1):
            print >> sys.stderr, str(nr) + '/' + str(nr_pages), '\r',
            job_queue.put(nr)

        for i in range(opt.num_thread):
            job_queue.put(None)

        for t in thread_array:
            t.join()

        print "all thread finished"

    print >> sys.stderr

def default_options():
    class Options:
        pass

    options = Options()
    options.config = ''
    options.nim_thread = 1
    options.base_files = []

    return options

if __name__ == "__main__":

    options = default_options()

    for arg in sys.argv[1:]:
        if arg == '-help':
            print sys.argv[0], "dir/djvu_name -config: -lang: -j:"
            sys.exit(1)
        elif arg.startswith('-config:'):
            options.config = arg[len('-config:'):]
        elif arg.startswith('-lang:'):
            options.lang = arg[len('-lang:'):]
        elif arg.startswith('-j:'):
            options.num_thread = int(arg[len('-j:'):])
        else:
            options.base_files.append(arg)


    for filename in options.base_files:
        path = os.path.split(filename)
        old_cwd = os.getcwd()
        os.chdir(path[0])

        ocr_djvu(options, path[1])

        os.chdir(old_cwd)
