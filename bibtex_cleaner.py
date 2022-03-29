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
journal_abbrv_dots = False

# export only selected authors
selected_authors = []

# do not export the following fields
omit_fields = ['type', 'abstract', 'keywords', 'eprint', 'month',
               'language', 'article-number', 'researcherid-numbers',
               'orcid-numbers', 'unique-id', 'earlyaccessdate',
               'organization']

# translate 'Lukes' -> 'Lukeš'
czech_authors = ['Lukeš']

wdir = os.path.dirname(__file__)


def get_jabrrv_table():
    """
    Return journal abbreviation table. Generate it from .txt file or read from .pkl
    file if already generated (fast access).
    """
    jabrrv_fname_txt = os.path.join(wdir, 'jabref_wos_abbrev_dots.txt')
    jabrrv_fname_pkl = os.path.join(wdir, 'jabref_wos_abbrev.pkl')

    if os.path.exists(jabrrv_fname_pkl):
        with open(jabrrv_fname_pkl, 'rb') as f:
            table = pickle.load(f)
    else:
        table = {}
        with open(jabrrv_fname_txt, 'rt') as f:
            for line in f:
                j = line.split('=')
                table[j[0].strip()] = j[1].strip()

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
            out.append([k.strip().replace('. ', '.').replace('~', '')
                        for k in auth.split(',')])
        else:
            aux = auth.split()
            out.append(aux[-1:] + [' '.join(aux[:-1])])

    # just inicials
    for a in out:
        aux = a[1].replace('.', '')
        if len(aux) > 1 and aux.upper() == aux:
            aux = list(aux.replace('-', ''))
        else:
            aux = (a[1].replace('-', ' ').replace('.', ' ')).split()
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

    s = s.strip().replace(r'\"', '@@')
    s = s.replace('{', '|').replace('}', '|').replace('"', '|')
    s = s.replace('@@', r'\"')
    parts = s.split('=')

    key = parts.pop(0).strip().lower()
    aval = []
    while len(parts) > 0:
        next = parts.pop(0).strip()
        aux = next.split()
        if len(parts) > 0 and len(aux) > 1 and aux[-2][-1] == ',':
            out[key] = '='.join(aval + [' '.join(aux[:-1])])
            key = aux[-1].strip().lower()
            aval = []
        else:
            aval.append(' '.join(aux))

    out[key] = '='.join(aval)

    for k in out.keys():
        out[k] = out[k].strip().replace('|', '')
        if len(out[k]) > 0 and out[k][-1] == ',':
            out[k] = out[k][:-1]

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
    bibitems = [k.strip() for k in bib.split('@')]

    if journal_abbrv:
        jabbrv_table = {k.lower(): v
                        for k, v in get_jabrrv_table().items()}
        jabbrv_table_vals = {v.lower().replace('.', ''): v
                             for v in jabbrv_table.values()}
    else:
        jabbrv_table_inv = {v.lower().replace('.', ''): k
                            for k, v in get_jabrrv_table().items()}

    bibitems_keys = {}

    for bibitem in bibitems:
        if len(bibitem) < 10:
            continue

        idx = bibitem.find(',')
        itemtype, ikey = bibitem[:idx].split('{')
        itemtype = itemtype.lower()

        out = get_items(bibitem[(idx + 1):-1])
        out['type'] = itemtype

        if 'editor' in out:
            auths = parse_authors(out['editor'])
            out['editor'] = ' and '.join([f'{k[0]}, {k[1]}' for k in auths])

        if 'author' in out:
            auths = parse_authors(out['author'])

        if 'doi' in out:
            out['doi'] = out['doi'].replace('https://doi.org/', '')

        if 'journal' in out:
            aux = out['journal'].lower().replace(r'\&', '&')
            aux2 = aux.replace('.', '')
            if journal_abbrv:
                if aux in jabbrv_table:
                    if journal_abbrv_dots:
                        out['journal'] = jabbrv_table[aux]
                    else:
                        out['journal'] = jabbrv_table[aux].replace('.', '')
                elif aux2 in jabbrv_table_vals:
                    if journal_abbrv_dots:
                        out['journal'] = jabbrv_table_vals[aux2]
                    else:
                        out['journal'] = out['journal'].replace('.', '')
                else:
                    print(f"  journal name not abbreviated: {out['journal']}")
            else:
                if aux2 in jabbrv_table_inv:
                    out['journal'] = jabbrv_table_inv[aux2]

        if new_key:
            year = out.get('year', 'XXXX')
            auth = auths[0][0].replace('~', '').replace(' ', '')
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
