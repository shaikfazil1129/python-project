import os
import pandas as pd
import logging
import openpyxl
from openpyxl.styles import PatternFill, Font
from .utils import sha256_of_file

def compare_excel_files(file_pairs, target_folder, failed_files_count):
    """
    Compare multiple pairs of Excel files and write differences to a new Excel file.
    Optimized using vectorized pandas operations for speed.
    """
    for fileA, fileB, batch in file_pairs:
        logging.info(f"Comparing batch: {batch} | FileA: {fileA} | FileB: {fileB}")

        # --- SHA-256 check to skip identical files ---
        try:
            sha_A = sha256_of_file(fileA)
            sha_B = sha256_of_file(fileB)
        except Exception as e:
            logging.error(f"Error computing SHA-256: {e}")
            failed_files_count += 1
            continue

        if sha_A == sha_B:
            logging.info(f"Skipping {fileA} and {fileB}: files are identical (SHA-256 match).")
            continue

        output_file = os.path.join(target_folder, f"comparison-{batch}.xlsx")

        # --- Read Excel files ---
        try:
            xlsA = pd.ExcelFile(fileA)
            xlsB = pd.ExcelFile(fileB)
        except Exception as e:
            logging.error(f"Error reading Excel files: {fileA}, {fileB} | {e}")
            failed_files_count += 1
            continue

        # Determine common sheets
        common_sheets = xlsA.sheet_names[:len(xlsB.sheet_names)]
        output_data = {}
        sheet_diff_map = {}

        for sheetA, sheetB in zip(xlsA.sheet_names, xlsB.sheet_names):
            logging.info(f"Comparing sheets: {sheetA} vs {sheetB}")
            try:
                dfA = xlsA.parse(sheet_name=sheetA)
                dfB = xlsB.parse(sheet_name=sheetB)
            except Exception as e:
                logging.error(f"Error parsing sheets: {sheetA}, {sheetB} | {e}")
                continue

            if dfA.empty and dfB.empty:
                logging.warning(f"Both sheets {sheetA} and {sheetB} are empty. Skipping.")
                continue

            # --- Align columns ---
            all_columns = list(pd.Index(dfA.columns).union(dfB.columns))
            dfA = dfA.reindex(columns=all_columns)
            dfB = dfB.reindex(columns=all_columns)

            # --- Vectorized difference computation ---
            diff_mask = dfA.ne(dfB) & ~(dfA.isna() & dfB.isna())
            if diff_mask.any().any():  # At least one difference
                df_out = dfB.copy()
                # Create a 'Difference' column with details
                diff_details = []
                for idx, row in df_out.iterrows():
                    cols_changed = diff_mask.loc[idx]
                    details = [f"{col}: A='{dfA.at[idx, col]}', B='{dfB.at[idx, col]}'"
                               for col in all_columns if cols_changed[col]]
                    diff_details.append("; ".join(details) if details else None)
                df_out['Difference'] = diff_details
                output_data[sheetB] = df_out

                # Store cell positions for highlighting
                cell_diff_map = {idx: list(diff_mask.loc[idx][diff_mask.loc[idx]].index)
                                 for idx in diff_mask.index if diff_mask.loc[idx].any()}
                sheet_diff_map[sheetB] = {'CellDifferences': cell_diff_map, 'Headers': all_columns}

            else:
                logging.info(f"No differences found in sheet {sheetA} vs {sheetB}.")

        # --- Write output Excel file once ---
        if output_data:
            wb = None
            if os.path.exists(output_file):
                try:
                    wb = openpyxl.load_workbook(output_file)
                except Exception:
                    os.remove(output_file)
                    wb = None

            with pd.ExcelWriter(output_file, engine='openpyxl', mode='a' if wb else 'w') as writer:
                if wb:
                    writer.book = wb
                for sheet_name, df_out in output_data.items():
                    if wb and sheet_name in writer.book.sheetnames:
                        std = writer.book[sheet_name]
                        writer.book.remove(std)
                    df_out.to_excel(writer, sheet_name=sheet_name, index=False)
            logging.info(f"Written differences to {output_file}")

        # --- Apply highlights ---
        if sheet_diff_map:
            wb = openpyxl.load_workbook(output_file)
            yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
            bold_font = Font(bold=True)

            for sheet_name, sheet_info in sheet_diff_map.items():
                ws = wb[sheet_name]
                headers = sheet_info['Headers']
                col_map = {header: idx + 1 for idx, header in enumerate(headers)}
                for row_idx, changed_cols in sheet_info['CellDifferences'].items():
                    for col in changed_cols:
                        cell = ws.cell(row=row_idx + 2, column=col_map[col])
                        cell.fill = yellow_fill
                        cell.font = bold_font
            wb.save(output_file)
            logging.info(f"Highlighted differences in {output_file}")
