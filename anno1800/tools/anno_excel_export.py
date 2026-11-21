'Export Excel workbooks with XlsxWriter.'
import os
from pathlib import Path

import xlsxwriter

REGIONS = ('Alte Welt', 'Neue Welt', 'Kap Trelawney', 'Arktis', 'Enbesa')
WIDTHS = (108, 78, 103, 101, 101, 113, 81, 81, 140, 91, 235, 99, 99, 99, 150,
          108, 157, 104, 315, 378, 350, 179, 179, 190, 190, 172, 190, 190, 350, 190)


def write_workbook(rows, settings, times, zone, stage, target, output, updated_at, logo, total_playtime, profiles):
    def regional_links(row):
        by_name = {link['label']: link for link in row['links']}
        other = [link for link in row['links'] if link['label'] not in REGIONS]
        return [by_name.get(name) for name in REGIONS], other

    extra_count = max(1, *(len(regional_links(row)[1]) for row in rows))
    headers = ['Seed', 'Variante', 'Spielmodus', *REGIONS, 'Szenario / weitere Region',
               'Spielstände', 'Profile', *settings, 'Spielstand für die Kartenbilder', *times,
               'Mehr Spielzeit im älteren Save']
    headers.extend(f'Weitere Region {i}' for i in range(2, extra_count + 1))

    with xlsxwriter.Workbook(stage/'report.xlsx', {
        'strings_to_formulas': False, 'strings_to_urls': False,
    }) as book:
        sheet = book.add_worksheet('Kartenseeds')
        sheet.hide_gridlines(2)
        sheet.set_tab_color('#19374B')
        sheet.freeze_panes(6, 2)
        common = {'font_name':'Arial', 'font_size':10, 'font_color':'#253C4B', 'valign':'vcenter'}
        body = book.add_format({**common, 'text_wrap':True})
        head = book.add_format({**common, 'font_color':'#FFFFFF', 'bg_color':'#19374B',
                                'bold':True, 'text_wrap':True, 'align':'center'})
        title = book.add_format({**common, 'font_color':'#19374B', 'bold':True, 'font_size':16})
        note = book.add_format({**common, 'italic':True})
        date = book.add_format({**common, 'num_format':'dd.mm.yyyy hh:mm:ss'})
        time = book.add_format({**common, 'num_format':'[h]:mm:ss'})
        delta_format = book.add_format({**common, 'num_format':'"+"[h]:mm:ss'})
        count = book.add_format({**common, 'num_format':'#,##0'})
        link_format = book.add_format({**common, 'font_color':'#125C93', 'underline':1, 'text_wrap':True})
        marker = book.add_format({'bg_color':'#FFEBBF', 'font_color':'#633900', 'bold':True})
        sheet.set_row(1, 24)
        sheet.set_row(5, 34)
        for i in range(len(headers)):
            sheet.set_column_pixels(i, i, WIDTHS[i] if i < len(WIDTHS) else 170)
        sheet.set_row(0, 11)
        sheet.set_row(2, 18)
        sheet.set_row(3, 18)
        sheet.set_row(4, 23)
        sheet.write('A2', 'Anno 1800 · Kartenseeds', title)
        seed_count = len({row['identity'][0] for row in rows})
        save_count = f"{sum(row['settings'][0] for row in rows):,}".replace(',', '’')
        sheet.write('A3', f'{len(rows)} Kartenvarianten aus {save_count} Spielstanddateien · {seed_count} Seeds', body)
        sheet.write('A4', 'Blaue Einträge öffnen die PNGs im Ordner map-images.', note)
        sheet.write('A5', 'Zuletzt aktualisiert am: ' + updated_at.strftime('%d.%m.%Y %H:%M') +
                    ' (Schweizer Lokalzeit) · Gesamtspielzeit: ' + total_playtime, note)
        sheet.add_table(5, 0, 5 + len(rows), len(headers) - 1, {
            'name':'KartenseedVarianten', 'style':'Table Style Light 9',
            'columns':[{'header':label, 'header_format':head} for label in headers],
        })
        for row_index, row in enumerate(rows, 6):
            regions, other = regional_links(row)
            values = [*row['identity'], *([None] * 6), *row['settings']]
            lines = 3
            for column, value in enumerate(values):
                if value is None:
                    continue
                fmt = (count if column == 9 else
                       date if column in (21, 22, 23, 24, 27) else
                       time if column in (25, 26) else body)
                sheet.write(row_index, column, value, fmt)
                if isinstance(value, str):
                    chars = max(1, WIDTHS[column] // 7)
                    lines = max(lines, sum(max(1, (len(line) + chars - 1) // chars)
                                           for line in value.split('\n')))
            sheet.set_row(row_index, min(400, max(45, lines * 13 + 6)))
            for column, link in [*enumerate(regions, 3),
                                 *((8 if i == 0 else 29 + i, link) for i, link in enumerate(other))]:
                if link is None:
                    continue
                relative = Path(link['path'])
                if not (stage/relative).is_file():
                    raise ValueError(f'Kartenbild fehlt: {relative}')
                address = os.path.relpath(output/relative, target.parent)
                status = sheet.write_url(row_index, column, 'external:' + address, link_format,
                                         link['label'].removeprefix('Szenario · '))
                if status != 0:
                    raise ValueError(f'Excel konnte den Kartenlink nicht speichern: {relative}')
            n = row_index + 1
            formula = f'=IF(AND(AB{n}<Y{n},AA{n}>Z{n}),ROUND((AA{n}-Z{n})*86400,0)/86400,"")'
            cached = row['delta']/86400 if row['delta'] else ''
            sheet.write_formula(row_index, 29, formula, delta_format, cached)
        for address in (f'A7:B{len(rows)+6}', f'AD7:AD{len(rows)+6}'):
            sheet.conditional_format(address, {'type':'formula', 'criteria':'=ISNUMBER($AD7)', 'format':marker})

        ranking = book.add_worksheet('Spielzeit pro Profil')
        ranking.hide_gridlines(2)
        ranking.freeze_panes(5, 0)
        ranking.set_column_pixels(0, 0, 85)
        ranking.set_column_pixels(1, 1, 320)
        ranking.set_column_pixels(2, 2, 100)
        ranking.set_column_pixels(3, 3, 150)
        ranking.set_row(1, 25)
        ranking.set_row(4, 25)
        ranking.write('A2', 'Spielzeit pro Profil', title)
        ranking.write('A3', 'Jede Partie zählt beim Profil ihres längsten gespeicherten Stands.', note)
        ranking.add_table(4, 0, 4 + len(profiles), 3, {
            'name':'Profilspielzeiten', 'style':'Table Style Light 9',
            'columns':[{'header':label, 'header_format':head}
                       for label in ('Rang', 'Profil', 'Partien', 'Spielzeit (h:mm:ss)')],
        })
        for index, (profile, games, milliseconds) in enumerate(profiles, 1):
            excel_row = index + 4
            ranking.set_row(excel_row, 19)
            ranking.write_row(excel_row, 0, (index, profile, games), body)
            ranking.write_number(excel_row, 3, (milliseconds // 1000) / 86400, time)
