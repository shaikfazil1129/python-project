import os
import fitz
import logging
from .utils import sha256_of_file

def compare_pdf_files(file_pairs, target_folder, failed_files_count):
    for fileA, fileB, batch in file_pairs:
        try:
            logging.info(f"Comparing PDF batch: {batch} | FileA: {fileA} | FileB: {fileB}")
            sha_A = sha256_of_file(fileA)
            sha_B = sha256_of_file(fileB)
            if sha_A == sha_B:
                logging.info(f"Skipping identical PDFs {fileA} and {fileB}")
                continue

            docA, docB = fitz.open(fileA), fitz.open(fileB)
            mismatches = []

            for page_num in range(len(docB)):
                pageA = docA[page_num] if page_num < len(docA) else None
                pageB = docB[page_num]
                wordsA = pageA.get_text("words") if pageA else []
                wordsB = pageB.get_text("words")

                min_words = min(len(wordsA), len(wordsB))
                for i in range(min_words):
                    wordA, wordB = wordsA[i][4], wordsB[i][4]
                    if wordA != wordB:
                        rect = fitz.Rect(wordsB[i][0], wordsB[i][1], wordsB[i][2], wordsB[i][3])
                        pageB.add_highlight_annot(rect)
                        mismatches.append(f"Page {page_num+1}, Word {i+1}: A: {wordA} | B: {wordB}")
                for i in range(min_words, len(wordsB)):
                    rect = fitz.Rect(wordsB[i][0], wordsB[i][1], wordsB[i][2], wordsB[i][3])
                    pageB.add_highlight_annot(rect)
                    mismatches.append(f"Page {page_num+1}, Word {i+1}: A: <none> | B: {wordsB[i][4]}")

            if mismatches:
                summary_page = docB.new_page(-1)
                summary_text = "Summary of Mismatches:\n\n" + "\n".join(mismatches)
                summary_page.insert_text((72, 72), summary_text, fontsize=10)

            outputFile = os.path.join(target_folder, f"comparison-{batch}.pdf")
            docB.save(outputFile)
            docA.close()
            docB.close()
            logging.info(f"Written PDF differences to {outputFile}")

        except Exception as e:
            logging.error(f"Failed to compare PDFs {fileA} and {fileB}: {e}")
            failed_files_count += 1
