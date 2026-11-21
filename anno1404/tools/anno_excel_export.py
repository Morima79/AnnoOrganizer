'Export Excel workbooks with XlsxWriter.'
import xlsxwriter


def write_workbook(target, data):
    with xlsxwriter.Workbook(target, {'strings_to_formulas': False, 'strings_to_urls': False}) as book:
        sheet = book.add_worksheet('Kartenseeds')
        sheet.hide_gridlines(2)
        sheet.freeze_panes(5, 0)
        common = {'font_name': 'Arial', 'font_size': 10, 'font_color': '#25414b', 'valign': 'vcenter'}
        body = book.add_format({**common, 'text_wrap': True})
        title = book.add_format({**common, 'font_size': 16, 'bold': True})
        header = book.add_format({**common, 'bold': True, 'font_color': '#ffffff',
                                  'bg_color': '#25414b', 'text_wrap': True})
        link = book.add_format({**common, 'underline': 1, 'font_color': '#115c8c'})
        date = book.add_format({**common, 'num_format': 'dd.mm.yyyy hh:mm:ss'})
        hours = book.add_format({**common, 'num_format': '[h]:mm:ss'})
        delta = book.add_format({**common, 'num_format': '"+"[h]:mm:ss'})
        marker = book.add_format({'bg_color': '#ffedc4', 'font_color': '#633900', 'bold': True})
        sheet.write('A1', 'Anno 1404 · Venedig · History Edition', title)
        sheet.set_row(0, 26)
        sheet.write('A2', data['note'])
        sheet.write('A3', 'Zuletzt aktualisiert am ' + data['updated'] + ' · Gespeicherte Gesamtspielzeit ' + data['total'])
        sheet.write('A4', 'Datumsangaben stammen aus den Dateizeitstempeln. Karteneinstellungen zeigen die gespeicherten Werte.')
        formats = {**dict.fromkeys(data['dates'], date), **dict.fromkeys(data['times'], hours), 16: delta}
        sheet.set_row(4, 34)
        for i, _ in enumerate(data['headers']):
            sheet.set_column_pixels(i, i, data['widths'][i] if i < len(data['widths']) else 130)
        sheet.add_table(4, 0, len(data['rows'])+4, len(data['headers'])-1, {
            'name': 'Kartenvarianten', 'style': 'Table Style Light 9',
            'columns': [{'header': v, 'header_format': header} for v in data['headers']],
        })
        for i, row in enumerate(data['rows'], 5):
            sheet.set_row(i, 32)
            for column, value in enumerate(row['values']):
                sheet.write(i, column, value, formats.get(column, body))
            sheet.write_url(i, 4, 'external:' + row['image'].replace('/', '\\'), link, row['values'][4])
        for area in (f"A6:B{len(data['rows'])+5}", f"Q6:Q{len(data['rows'])+5}"):
            sheet.conditional_format(area, {'type': 'formula', 'criteria': '=ISNUMBER($Q6)', 'format': marker})

        ranking = book.add_worksheet('Spielzeit pro Profil')
        ranking.hide_gridlines(2)
        ranking.write('A1', 'Spielzeit pro Profil', title)
        ranking.set_row(0, 26)
        ranking.write('A2', 'Pro erkannter Partie zählt der längste gespeicherte Stand.')
        ranking.write_row('A4', ['Rang', 'Profil', 'Partien', 'Spielzeit'], header)
        for i, size in enumerate((75, 220, 80, 150)):
            ranking.set_column_pixels(i, i, size)
        for i, (name, count, milliseconds) in enumerate(data['ranking'], 4):
            ranking.write_row(i, 0, [i-3, name, count], body)
            ranking.write_number(i, 3, milliseconds/86400000, hours)
