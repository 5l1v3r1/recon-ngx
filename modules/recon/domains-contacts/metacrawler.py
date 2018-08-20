from recon.core.module import BaseModule
from recon.mixins.search import GoogleWebMixin
import recon.utils.parsers as parsers
import itertools
import os

# to do:
# extract email addresses from text
# add info to database

class Module(BaseModule, GoogleWebMixin):

    meta = {
        'name': 'Meta Data Extractor',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'description': 'Searches for files associated with the provided domain(s) and extracts any contact related metadata.',
        'comments': (
            'Currently supports doc, docx, xls, xlsx, ppt, pptx, and pdf file types.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (
            ('extract', False, True, 'edownload files into default directory and xtract metadata from discovered files'),
        ),
    }

    def module_run(self, domains):
        exts = {
            'ole': ['doc', 'xls', 'ppt'],
            'ooxml': ['docx', 'xlsx', 'pptx'],
            'pdf': ['pdf'],
        }
        search = 'site:%s ' + ' OR '.join(['filetype:%s' % (ext) for ext in list(itertools.chain.from_iterable(exts.values()))])
        for domain in domains:
            self.heading(domain, level=0)
            results = self.search_google_web(search % domain)
            if results and self.options['extract']:
                path = '{0}/{1}'.format(self.workspace, domain)
                if not os.path.exists(path):
                    os.makedirs(path)
                self.alert('Files are downloaded into {0}'.format(path))
            for result in results:
                self.output(result)
                # metadata extraction
                if self.options['extract']:
                    # parse the extension of the discovered file
                    ext = result.split('.')[-1]
                    # search for the extension in the extensions dictionary
                    # the extensions dictionary key indicates the file type
                    for key in exts:
                        if ext in exts[key]:
                            # check to see if a parser exists for the file type
                            if hasattr(parsers, key+'_parser'):
                                try:
                                    func = getattr(parsers, key + '_parser')
                                    resp = self.request(result)
                                    # write files into direrctory
                                    filename = result.split('/')[-1]
                                    if len(filename) > 200:
                                        filename = filename[-200:]
                                    filepath = '{0}/{1}/{2}'.format(self.workspace, domain, filename)
                                    dl = open(filepath, 'wb')
                                    dl.write(resp.raw)
                                    dl.close()
                                    # validate that the url resulted in a file 
                                    if resp.headers['content-type'].startswith('application'):
                                        meta = func(resp.raw)
                                        # display the extracted metadata
                                        for key in meta:
                                            if meta[key]:
                                                self.alert('%s: %s' % (key.title(), meta[key]))
                                        if 'Author' in meta and 'Creating_Application' in meta:
                                            self.add_contacts(first_name=meta['Author'], middle_name=meta['Creating_Application'],
                                                          last_name=result)
                                        if 'Author' in meta and 'Creator' in meta:
                                            self.add_contacts(first_name=meta['Author'], middle_name=meta['Creator'],
                                                          last_name=result)
                                    else:
                                        self.error('Resource not a valid file.')
                                except Exception:
                                    self.print_exception()
                            else:
                                self.alert('No parser available for file type: %s' % ext)
                            break
            self.alert('%d files found on \'%s\'.' % (len(results), domain))