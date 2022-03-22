import sys
import os
import pickle
import unicodedata
import numpy as nm

# generate new bib record keys
new_key = True

# number of authors before "et al."
authors_others = 2

# use journal abbreviation database
journal_abbrv = True

# export only selected authors
selected_authors = []

# do not export the following fields
omit_fields = ['type', 'abstract', 'keywords', 'eprint', 'month',
               'language', 'article-number', 'researcherid-numbers',
               'orcid-numbers', 'unique-id', 'earlyaccessdate',
               'organization']

# translate 'Lukes' -> 'Lukeš'
czech_authors = ['Lukeš']

qchars = {'{': '}', '"': '"'}


def get_jabrrv_table():
    """
    Return journal abbreviation table. Generate it from .txt file or read from .pkl
    file if already generated (fast access).
    """
    jabrrv_fname_txt = 'jabref_wos_abbrev_dots.txt'
    # jabrrv_fname_txt = 'jabref_wos_abbrev.txt'
    jabrrv_fname_pkl = 'jabref_wos_abbrev.pkl'

    if os.path.exists(jabrrv_fname_pkl):
        with open(jabrrv_fname_pkl, 'rb') as f:
            table = pickle.load(f)
    else:
        table = {}
        with open(jabrrv_fname_txt, 'rt') as f:
            for line in f:
                j = line.split('=')
                table[j[0].strip().lower()] = j[1].strip()

        with open(jabrrv_fname_pkl, 'wb') as f:
            pickle.dump(table, f)

    return table


def get_ascii(s):
    """
    Return ascii representation of an unicode string.
    """
    return str(unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore'), 'ASCII')


def parse_authors(auths):
    """
    Parse the string containing arbitrary number of authors.
    Return list of authors: [['First', 'A.B.'], ['Second', 'C.'], ...]
    """
    out = []
    for auth in auths.split(' and '):
        if ',' in auth:
            out.append([k.strip() for k in auth.split(',')])
        else:
            aux = auth.split()
            out.append(aux[-1:] + [' '.join(aux[:-1])])

    # just inicials
    for a in out:
        aux = a[1].replace('.', '')
        if len(aux) > 1 and aux.upper() == aux:
            aux = list(aux)
        else:
            aux = a[1].replace('.', ' ').split()
        a[1] = '~'.join([f'{k[0]}.' for k in aux])

        for ka in czech_authors:
            kaa = get_ascii(ka)
            if kaa in a[0]:
                a[0] = a[0].replace(kaa, ka)

    return out


def get_items(s):
    """
    Return dict of items for a given bib record (string).
    """
    out = {}

    while True:
        idx = s.find('=')
        if idx < 0:
            break
        key = (s[:idx].split()[-1]).lower()
        s = s[(idx + 1):].strip()
        if s[0] not in qchars:
            idx = s.find(',')
            val = s[:idx]
        else:
            bs = qchars[s[0]] + ','
            s = s[1:]
            idx = s.find(bs)
            val = s[:idx]
        val = val.replace('{', '')
        val = val.replace('}', '')
        val = val.replace('\n', ' ')
        val = val.replace('\r', '')
        out[key] = ' '.join(val.strip().split())
        s = s[(idx + 1):].strip()

    return out


def get_jref(s):
    """
    Return initials of a journal name. Used in bib keys. 
    """
    for rm in [r'\&', 'of', 'and', 'in']:
        if f' {rm} ' in s:
            s = s.replace(rm, '')

    return '-' + ''.join([k[0] for k in s.split()])


def generate_latex_main(fname_latex, fname_bib, bib_keys):
    """
    Create the main LaTeX file with all references.
    """
    cits = ',\n'.join([r'\cite{%s}' % k for k in bib_keys])

    latex_main = r"""\documentclass[11pt]{article}
\usepackage{a4wide}
\begin{document}

%CITATIONS%

\bibliographystyle{plain}
\bibliography{%BIB_FILE%}

\end{document}
""".replace('%CITATIONS%', cits).replace('%BIB_FILE%', fname_bib)

    fout = open(fname_latex, 'wt')
    fout.write(latex_main)
    fout.close()


def main(fname):
    bibout = {}
    bib = open(fname, 'rt').read()
    bibitems = bib.split('@')

    bibitems_keys = {}
    if journal_abbrv:
        jabbrv_table = get_jabrrv_table()

    for bibitem in bibitems:
        if len(bibitem) < 10:
            continue

        idx = bibitem.find(',')
        itemtype, ikey = bibitem[:idx].split('{')
        itemtype = itemtype.lower()

        out = get_items(bibitem[(idx + 1):])
        out['type'] = itemtype

        if 'editor' in out:
            auths = parse_authors(out['editor'])
            out['editor'] = ' and '.join([f'{k[0]}, {k[1]}' for k in auths])

        if 'author' in out:
            auths = parse_authors(out['author'])

        if 'doi' in out:
            out['doi'] = out['doi'].replace('https://doi.org/', '')

        if 'journal' in out:
            if journal_abbrv:
                aux = out['journal'].lower().replace(r'\&', '&')
                if aux in jabbrv_table:
                    out['journal'] = jabbrv_table[aux]

        if new_key:
            year = out.get('year', 'XXXX')
            auth = auths[0][0].replace('~', '_')
            ref = get_jref(out['journal']) if out['type'] == 'article' else ''
            bkey = get_ascii(f'{auth}{year}{ref}')

            if bkey not in bibitems_keys:
                bibitems_keys[bkey] = 1
            else:
                bibitems_keys[bkey] += 1
                flag = '%c' % (96 + bibitems_keys[bkey])
                bkey = get_ascii(f'{auth}{year}{flag}{ref}')

        else:
            bkey = ikey

        nauths = len(auths)
        idx = nm.min([nauths, authors_others])
        out['author'] = ' and '.join([f'{k[0]}, {k[1]}' for k in auths[:idx]])
        if idx < nauths:
            out['author'] += ' and others'

        cont = True
        if len(selected_authors) > 0:
            cont = False
            for auth in selected_authors:
                if auth in out['author']:
                    cont = True
                    break

        if cont:
            print(f'Bibitem type: {itemtype}, {bkey}   ---> output')
        else:
            print(f'Bibitem type: {itemtype}, {bkey}')
            continue

        if bkey not in bibout:
            bibout[bkey] = out
        else:
            print(bibout[bkey])
            print(out)
            raise ValueError(f'duplicit items {bkey}!')

    # sort by year (if is present)
    aux = []
    for kk, (k, v) in enumerate(bibout.items()):
        if 'year' in v:
            year = int(v['year'])
        else:
            year = int(1e5 + kk)
        aux.append((k, year))

    aux = list(zip(*aux))
    keys = nm.array(aux[0])[nm.argsort(aux[1])]

    aux = fname.split('.')
    fname_out_base = '.'.join(aux[:-1])
    fname_out = fname_out_base + '_clean.bib'
    print(f'saved into: {fname_out}')

    fout = open(fname_out, 'wt')

    for k in keys:
        v = bibout[k]
        fout.write('@%s{%s,\n' % (v['type'], k))
        for ik, iv in v.items():
            if ik in omit_fields:
                continue
            fout.write('  %s = {%s},\n' % (ik, iv))

        fout.write('}\n\n')

    fout.close()

    generate_latex_main(f'main_{fname_out_base}.tex', fname_out, bibout.keys())


if __name__ == "__main__":
    main(sys.argv[1])
