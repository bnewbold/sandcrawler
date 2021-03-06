#!/usr/bin/env python3

"""
NB: adapted to work as a library for PDF extraction. Will probably be
re-written eventually to be correct, complete, and robust; this is just a
first iteration.

This script tries to extract everything from a GROBID TEI XML fulltext dump:

- header metadata
- affiliations
- references (with context)
- abstract
- fulltext
- tables, figures, equations

A flag can be specified to disable copyright encumbered bits (--no-emcumbered):

- abstract
- fulltext
- tables, figures, equations

Prints JSON to stdout, errors to stderr
"""

import io
import json
import argparse
import xml.etree.ElementTree as ET

ns = "http://www.tei-c.org/ns/1.0"

def all_authors(elem):
    names = []
    for e in elem.findall('.//{%s}author/{%s}persName' % (ns, ns)):
        given_name = e.findtext('./{%s}forename' % ns) or None
        surname = e.findtext('./{%s}surname' % ns) or None
        full_name = '{} {}'.format(given_name or '', surname or '').strip()
        names.append(dict(name=full_name, given_name=given_name, surname=surname))
    return names


def journal_info(elem):
    journal = dict()
    journal['name'] = elem.findtext('.//{%s}monogr/{%s}title' % (ns, ns))
    journal['publisher'] = elem.findtext('.//{%s}publicationStmt/{%s}publisher' % (ns, ns))
    if journal['publisher'] == '':
        journal['publisher'] = None
    journal['issn'] = elem.findtext('.//{%s}idno[@type="ISSN"]' % ns)
    journal['eissn'] = elem.findtext('.//{%s}idno[@type="eISSN"]' % ns)
    journal['volume'] = elem.findtext('.//{%s}biblScope[@unit="volume"]' % ns)
    journal['issue'] = elem.findtext('.//{%s}biblScope[@unit="issue"]' % ns)
    return journal


def biblio_info(elem):
    ref = dict()
    ref['id'] = elem.attrib.get('{http://www.w3.org/XML/1998/namespace}id')
    # Title stuff is messy in references...
    ref['title'] = elem.findtext('.//{%s}analytic/{%s}title' % (ns, ns))
    other_title = elem.findtext('.//{%s}monogr/{%s}title' % (ns, ns))
    if other_title:
        if ref['title']:
            ref['journal'] = other_title
        else:
            ref['journal'] = None
            ref['title'] = other_title
    ref['authors'] = all_authors(elem)
    ref['publisher'] = elem.findtext('.//{%s}publicationStmt/{%s}publisher' % (ns, ns))
    if ref['publisher'] == '':
        ref['publisher'] = None
    date = elem.find('.//{%s}date[@type="published"]' % ns)
    ref['date'] = (date != None) and date.attrib.get('when')
    ref['volume'] = elem.findtext('.//{%s}biblScope[@unit="volume"]' % ns)
    ref['issue'] = elem.findtext('.//{%s}biblScope[@unit="issue"]' % ns)
    el = elem.find('.//{%s}ptr[@target]' % ns)
    if el is not None:
        ref['url'] = el.attrib['target']
        # Hand correction
        if ref['url'].endswith(".Lastaccessed"):
            ref['url'] = ref['url'].replace(".Lastaccessed", "")
    else:
        ref['url'] = None
    return ref


def teixml2json(content, encumbered=True):

    if type(content) == str:
        content = io.StringIO(content)
    elif type(content) == bytes:
        content = io.BytesIO(content)

    info = dict()

    #print(content)
    #print(content.getvalue())
    tree = ET.parse(content)
    tei = tree.getroot()

    header = tei.find('.//{%s}teiHeader' % ns)
    if header is None:
        raise ValueError("XML does not look like TEI format")
    application_tag = header.findall('.//{%s}appInfo/{%s}application' % (ns, ns))[0]
    info['grobid_version'] = application_tag.attrib['version']
    info['grobid_timestamp'] = application_tag.attrib['when']
    info['title'] = header.findtext('.//{%s}analytic/{%s}title' % (ns, ns))
    info['authors'] = all_authors(header.find('.//{%s}sourceDesc/{%s}biblStruct' % (ns, ns)))
    info['journal'] = journal_info(header)
    date = header.find('.//{%s}date[@type="published"]' % ns)
    info['date'] = (date != None) and date.attrib.get('when')
    info['fatcat_release'] = header.findtext('.//{%s}idno[@type="fatcat"]' % ns)
    info['doi'] = header.findtext('.//{%s}idno[@type="DOI"]' % ns)
    if info['doi']:
        info['doi'] = info['doi'].lower()

    refs = []
    for (i, bs) in enumerate(tei.findall('.//{%s}listBibl/{%s}biblStruct' % (ns, ns))):
        ref = biblio_info(bs)
        ref['index'] = i
        refs.append(ref)
    info['citations'] = refs

    if encumbered:
        el = tei.find('.//{%s}profileDesc/{%s}abstract' % (ns, ns))
        info['abstract'] = (el or None) and " ".join(el.itertext()).strip()
        el = tei.find('.//{%s}text/{%s}body' % (ns, ns))
        info['body'] = (el or None) and " ".join(el.itertext()).strip()
        el = tei.find('.//{%s}back/{%s}div[@type="acknowledgement"]' % (ns, ns))
        info['acknowledgement'] = (el or None) and " ".join(el.itertext()).strip()
        el = tei.find('.//{%s}back/{%s}div[@type="annex"]' % (ns, ns))
        info['annex'] = (el or None) and " ".join(el.itertext()).strip()

    return info

def main():   # pragma no cover
    parser = argparse.ArgumentParser(
        description="GROBID TEI XML to JSON",
        usage="%(prog)s [options] <teifile>...")
    parser.add_argument("--no-encumbered",
        action="store_true",
        help="don't include ambiguously copyright encumbered fields (eg, abstract, body)")
    parser.add_argument("teifiles", nargs='+')

    args = parser.parse_args()

    for filename in args.teifiles:
        content = open(filename, 'r')
        print(json.dumps(
            teixml2json(content,
               encumbered=(not args.no_encumbered))))

if __name__=='__main__':   # pragma no cover
    main()
