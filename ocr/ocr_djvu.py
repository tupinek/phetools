#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
sys.path.append('/home/phe/wsbot')
import os
import ocr
import multiprocessing
import utils
import traceback

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
    tiff_name = opt.out_dir + 'page_%04d.tif' % page_nr
    cmdline  = djvulibre_path + 'ddjvu -format=tiff -page=%d ' % page_nr
    cmdline += '"' + filename + '" ' + tiff_name

    do_exec(cmdline)

    ocr.ocr(tiff_name, opt.out_dir + 'page_%04d' % page_nr, opt.lang, opt.config)

    os.remove(tiff_name)

    if opt.compress:
        filename = opt.out_dir + "page_%04d" % page_nr
        if opt.config == 'hocr':
            filename += '.html'
        else:
            filename += '.txt'

        utils.compress_file(filename, filename, opt.compress)
        os.remove(filename)

def do_file(job_queue, opt, filename):
    while True:
        page_nr = job_queue.get()
        if page_nr == None:
            print "Stopping thread"
            return
        try:
            do_one_page(opt, page_nr, filename)
        except Exception, e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            try:
                print >> sys.stderr, 'TRACEBACK'
                print >> sys.stderr, filename
                traceback.print_exception(exc_type, exc_value, exc_tb)
            finally:
                del exc_tb

def ocr_djvu(opt, filename):

    fd = open('/home/phe/wsbot/log/tesseract.log', 'a')
    print >> fd, "Starting to process:", filename
    fd.close()

    if not opt.out_dir.endswith('/'):
        opt.out_dir += '/'

    nr_pages = get_nr_pages_djvu(filename)
    if opt.num_thread == 1:
        for nr in range(1, nr_pages + 1):
            if not opt.silent:
                print >> sys.stderr, str(nr) + '/' + str(nr_pages), '\r',
            do_one_page(opt, nr, filename)
    else:
        thread_array = []
        job_queue = multiprocessing.Queue(opt.num_thread * 16)
        args = (job_queue, opt, filename)
        for i in range(opt.num_thread):
            if not opt.silent:
                print "starting thread"
            t = multiprocessing.Process(target=do_file, args=args)
            t.daemon = True
            t.start()
            thread_array.append(t)

        for nr in range(1, nr_pages + 1):
            if not opt.silent:
                print >> sys.stderr, str(nr) + '/' + str(nr_pages), '\r',
            job_queue.put(nr)

        for i in range(opt.num_thread):
            job_queue.put(None)

        for t in thread_array:
            t.join()

        if not opt.silent:
            print "all thread finished"

    if not opt.silent:
        print >> sys.stderr

    return 0

def default_options():
    class Options:
        pass

    options = Options()
    options.config = ''
    options.num_thread = 1
    options.base_files = []
    options.compress = None
    options.silent = False
    options.out_dir = './'

    return options

if __name__ == "__main__":

    options = default_options()

    for arg in sys.argv[1:]:
        if arg == '-help':
            print sys.argv[0], "dir/djvu_name -config: -lang: -j: -compress"
            sys.exit(1)
        elif arg.startswith('-config:'):
            options.config = arg[len('-config:'):]
        elif arg.startswith('-lang:'):
            options.lang = arg[len('-lang:'):]
        elif arg.startswith('-j:'):
            options.num_thread = int(arg[len('-j:'):])
        elif arg.startswith('-compress:'):
            options.compress = arg[len('-compress:'):]
        else:
            options.base_files.append(arg)


    for filename in options.base_files:
        path = os.path.split(filename)
        options.out_dir = path[0]
        ocr_djvu(options, filename)
