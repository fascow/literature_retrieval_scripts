# -*- coding: utf-8 -*-
'''
Springer Bookbinder

Download all chapters of a book from Springer and concatenate them

There are some books available on SpringerLink, which are split up into 
seperate files for all the chapters. This script aims at downloading them all 
and concatenating them into a single PDF file. It only works if you have access 
to the book of interest and is restricted to the 'referencework' type of books. 
Please, see the end of the script for examples of how to use the functions.
'''

import os
import re
import hashlib
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader, PdfFileWriter

import sys
sys.setrecursionlimit(10000)

t = re.compile('[a-zA-Z0-9.,_-]')

def down(url, path, name = None):
    '''
    Download all chapters from a Springer book
    
    url:  the base url of the book
    path: the directory to save all files
    name: not implemented yet
    '''
    counter = 1
    pp = 0
    ini = ''
    
    if not name:
        name = path
    
    while True:
        # TODO implement error codes on specific conditions
        # TODO autodetect the number of chapters to display the progress in percent
        pp += 1
        print('====== {0} ======\n'.format(pp))
        
        purl = '{0}/page/{1}'.format(url, pp)
        print(purl + '\n')
        r = requests.get(purl)
        page = r.content
        
        soup = BeautifulSoup(page, 'lxml')
        links = soup.find_all('a', href=re.compile('.pdf$'))
    
        # auto-detect the end of the book's website (npages)
        # in case there is a page without any accessible pdfs, which is still 
        #   not the last page, this approach will fail > better check the HTML 
        #   content for the max number of pages
        if len(links) == 0:
            print('No links to pdf files were found on this page.\n')
            break
        else:
            print('{0} links to pdf files were found on this page.\n'.format(len(links))) 
        
        for link in links:
            print(link['title'])
            print(link['href'])
            title = link['title'].replace('\s+', '_')#[0:20] # long filenames are bad
            # there are books where all chapters with the same first letter are 
            #   linking to the same PDF (that is already concatenated)
            # TODO this approach still duplicates pdfs on re-running the script            
            # TODO this does not catch chemical names (e.g. 4-Cyano-1,3-Butadiynyl 
            #   filed under 'C'), but the binder will ignore files with the same hash anyway
            # TODO detect when this code is needed automatically
            if title[0].upper() == ini:
                counter += 1
                continue
            ini = title[0]
            title = ''.join([ch for ch in title if t.match(ch)])
            surl = link['href']
            furl = 'http://link.springer.com' + surl
            filename = '{0:03d}_{1}.pdf'.format(counter, title)
            filename = os.path.join(path, filename)
            counter += 1
            #print(filename)
            if os.path.exists(filename) and os.path.isfile(filename):
                print('Skipping: %s already exists!\n' % filename)
                continue
            else:
                print('\n')
            b = requests.get(furl, stream = True)
            with open(filename, 'wb') as f:
                for chunk in b.iter_content(chunk_size = 1024): 
                    if chunk: # filter out keep-alive new chunks
                        #pass
                        f.write(chunk)
                        #f.flush() commented by recommendation from J.F.Sebastian
        
    
    print('\nNumber of chapters in total: {0}\n'.format(counter - 1))

    return 0


def bind(path, title, meta = None, verbose = False):
    '''
    Concatenate all PDF files from a folder into a single file
    
    path:  where to search for chapters and save the final PDF file
    title: name of the final PDF file
    meta:  dict to provide metadata to be written into the pdf
    
    from:  https://www.binpress.com/tutorial/manipulating-pdfs-with-python/167
    '''

    title = title[0:30]
    if title.endswith('.pdf'):
        filename = title
    else:
        filename = title + '.pdf'
    filepath = os.path.join(path, filename)
    #print(filepath)
    if os.path.isfile(filepath):
        print('Target file already exists. Aborting concatenation of PDF files!')
        return 1
    
    merger = PdfFileWriter()
    # TODO parse the meta meta from the webpage and combine with user input
    if meta:
        for k in meta.keys():
            if not k.startswith('/'):
                meta['/' + k] = meta.pop(k)
        merger.addMetadata(meta)
    # TODO add cover page from TIFF, not possible with PyPDF2
    files = [x for x in os.listdir(path) if x.endswith('.pdf')]
    #print(files)
    file_handles = []
    file_digests = []
    for fname in sorted(files):
        fil = open(os.path.join(path, fname), 'rb')
        dig = hashlib.md5(fil.read()).hexdigest()
        if dig in file_digests:
            print('Duplicate detected: {0}'.format(fname))
            fil.close()
            continue
        file_handles.append(fil)
        file_digests.append(dig)
        if verbose:
            doc = PdfFileReader(fil)
        else:
            doc = PdfFileReader(fil, warndest = open(os.devnull, 'w'))

        merger.appendPagesFromReader(doc)
        nupa = doc.numPages % 2
        if nupa == 1:
            merger.addBlankPage()

    out = open(filepath, 'wb')
    merger.write(out)
    out.close()

    for fh in file_handles:
        fh.close()
    
    print("Saved concatenated PDF files as '{0}' in '{1}'".format(filename, os.path.abspath(path)))

    return 0


def downbindSpringer(name, doi, path = os.getcwd(), meta = None):
    '''
    Download all chapters of a book from a given DOI and concatenate the PDFs
    
    name: name of the final PDF file
    doi:  DOI of the book of interest, tested to be working with Springer 
          "referencework" type of books
    path: path to save all chapters and the final PDF file. 
          default is the working directory. for each book a subfolder will be 
          created (path/name/name.pdf).
    meta: metadata of the book to be written into the final PDF file
    '''
    url = 'http://link.springer.com/referencework/' + doi
    
    # save everything relative to working directory, "wd/name/name.pdf"
    path = os.path.join(path, name)
    
    if not os.path.exists(path):
        os.makedirs(path)
    
    print(url)
    print(path)
    dres = down(url, path)
    
    if dres != 0:
        print('Download failed!')
        return 1
    
    bres = bind(path, name, meta)
    
    if bres != 0:
        print('Binding failed!')
        return 2
    
    print('File of the bound book: {0}\n'.format(name + '.pdf'))
    print('Fin')
    
    #print(os.path.join(path, name + '.pdf'))
    
    return 0


## examples
downbindSpringer('Ultrasonic', '10.1007/978-981-287-470-2', 'D:\Data\Literature',
                 {'/Title': 'Handbook of Ultrasonics and Sonochemistry', 
                  '/Editors': 'Muthupandian Ashokkumar', 
                  '/Edition': '1st', 
                  '/Year': '2016', 
                  '/DOI': '10.1007/978-981-287-470-2'})

downbindSpringer('Social Network Analysis', '10.1007/978-1-4614-6170-8', 'D:\Data\Literature')

# not working, python crashes
#downbindSpringer('Virus-Index', '10.1007/978-0-387-95919-1')


## resources
#
#http://link.springer.com/referencework/10.1007%2F978-4-431-54240-7
#http://www.springer.com/us/book/9784431542391
#
#http://stackoverflow.com/questions/7732694/find-specific-link-w-beautifulsoup
#http://stackoverflow.com/questions/13794532/python-regular-expression-for-beautiful-soup
#http://stackoverflow.com/questions/12982718/get-span-title-using-beautifulsoup
#http://stackoverflow.com/questions/16694907/how-to-download-large-file-in-python-with-requests-py




