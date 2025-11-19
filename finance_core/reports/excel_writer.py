import pandas as pd
from pathlib import Path
import xlsxwriter

class ExcelReportWriter:
    """
    Класс для генерации Excel отчетов.
    """
    
    def save_consolidated_report(self, 
                               consolidated_df: pd.DataFrame, 
                               external_df: pd.DataFrame, 
                               internal_df: pd.DataFrame, 
                               output_path: Path):
        """
        Сохраняет консолидированный отчет в Excel с форматированием.
        """
        # Добавляем итоговую строку к консолидированному отчету
        if not consolidated_df.empty:
            totals = pd.DataFrame([{
                'Компания': 'ИТОГО ПО ГРУППЕ',
                'начальное_сальдо_дт': consolidated_df['начальное_сальдо_дт'].sum(),
                'начальное_сальдо_кт': consolidated_df['начальное_сальдо_кт'].sum(),
                'выручка_всего': consolidated_df['выручка_всего'].sum(),
                'внутригрупповая_выручка': consolidated_df['внутригрупповая_выручка'].sum(),
                'внешняя_выручка': consolidated_df['внешняя_выручка'].sum(),
                'счет_90_основная': consolidated_df['счет_90_основная'].sum(),
                'счет_91_прочие': consolidated_df['счет_91_прочие'].sum(),
                'оплачено_51': consolidated_df['оплачено_51'].sum(),
                'взаимозачет_60': consolidated_df['взаимозачет_60'].sum(),
                'оплачено_76': consolidated_df['оплачено_76'].sum(),
                'возврат_аванса': consolidated_df['возврат_аванса'].sum(),
                'конечное_сальдо_дт': consolidated_df['конечное_сальдо_дт'].sum(),
                'конечное_сальдо_кт': consolidated_df['конечное_сальдо_кт'].sum(),
                'документов': consolidated_df['документов'].sum()
            }])
            result_with_totals = pd.concat([consolidated_df, totals], ignore_index=True)
        else:
            result_with_totals = consolidated_df

        # Создаем директорию, если нужно
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            # Лист 1: Консолидация
            result_with_totals.to_excel(writer, index=False, sheet_name='Консолидация')
            
            # Лист 2: Внешняя выручка
            external_df.to_excel(writer, index=False, sheet_name='Внешняя выручка')
            
            # Лист 3: Внутригрупповая
            if not internal_df.empty:
                internal_df.to_excel(writer, index=False, sheet_name='Внутригрупповая')

            workbook = writer.book
            
            # Форматы
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })

            money_format = workbook.add_format({
                'num_format': '#,##0.00',
                'border': 1
            })

            total_format = workbook.add_format({
                'num_format': '#,##0.00',
                'border': 1,
                'bold': True,
                'bg_color': '#FFF2CC'
            })
            
            # === Форматирование листа "Консолидация" ===
            worksheet = writer.sheets['Консолидация']
            
            for col_num, value in enumerate(result_with_totals.columns.values):
                worksheet.write(0, col_num, value, header_format)

            for row_num in range(1, len(result_with_totals)):
                worksheet.write(row_num, 0, result_with_totals.iloc[row_num-1, 0])
                for col_num in range(1, len(result_with_totals.columns)):
                    worksheet.write(row_num, col_num, 
                                  result_with_totals.iloc[row_num-1, col_num], 
                                  money_format)

            # Итоговая строка
            total_row = len(result_with_totals)
            worksheet.write(total_row, 0, result_with_totals.iloc[-1, 0], total_format)
            for col_num in range(1, len(result_with_totals.columns)):
                worksheet.write(total_row, col_num, 
                              result_with_totals.iloc[-1, col_num], 
                              total_format)

            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:P', 18)
            
            # === Форматирование листа "Внешняя выручка" ===
            worksheet2 = writer.sheets['Внешняя выручка']
            
            header_format2 = workbook.add_format({
                'bold': True,
                'bg_color': '#70AD47',
                'font_color': 'white',
                'border': 1,
                'align': 'center'
            })
            
            for col_num, value in enumerate(external_df.columns.values):
                worksheet2.write(0, col_num, value, header_format2)

            for row_num in range(1, len(external_df) + 1):
                for col_num in range(3): # Первые 3 колонки (Компания, Контрагент, Документ) - текст
                    worksheet2.write(row_num, col_num, external_df.iloc[row_num-1, col_num])
                for col_num in range(3, len(external_df.columns)): # Остальные - деньги
                    worksheet2.write(row_num, col_num, 
                                  external_df.iloc[row_num-1, col_num], 
                                  money_format)

            worksheet2.set_column('A:A', 25)
            worksheet2.set_column('B:B', 40)
            worksheet2.set_column('C:C', 50)
            worksheet2.set_column('D:L', 16)
            
            # === Форматирование листа "Внутригрупповая" ===
            if not internal_df.empty:
                worksheet3 = writer.sheets['Внутригрупповая']
                
                header_format3 = workbook.add_format({
                    'bold': True,
                    'bg_color': '#FFC000',
                    'font_color': 'white',
                    'border': 1,
                    'align': 'center'
                })
                
                for col_num, value in enumerate(internal_df.columns.values):
                    worksheet3.write(0, col_num, value, header_format3)

                for row_num in range(1, len(internal_df) + 1):
                    for col_num in range(3):
                        worksheet3.write(row_num, col_num, internal_df.iloc[row_num-1, col_num])
                    for col_num in range(3, len(internal_df.columns)):
                        worksheet3.write(row_num, col_num, 
                                      internal_df.iloc[row_num-1, col_num], 
                                      money_format)

                worksheet3.set_column('A:A', 25)
                worksheet3.set_column('B:B', 40)
                worksheet3.set_column('C:C', 50)
                worksheet3.set_column('D:L', 16)
        
        print(f"💾 Отчет сохранен: {output_path}")
