from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.append(['libellé','montant','date'])
ws.append(['Achat papier',120,'2024-02-12'])
ws.append(['Transport colis',220,'2024-03-03'])
wb.save('test_data/sample.xlsx')
print('xlsx written')

