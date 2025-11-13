import os
import fitz
import logging
from .utils import sha256_of_file, delete_if_exists


def compare_pdf_files(file_pairs, target_folder):
    failed_files_count = 0
    for fileA, fileB, batch, rel_path in file_pairs:
        try:
            logging.info(f"Comparing PDF batch: {batch} | FileA: {fileA} | FileB: {fileB}")
            sha_A = sha256_of_file(fileA)
            sha_B = sha256_of_file(fileB)
            logging.info(f"SHA-256 for {fileA}: {sha_A}")
            logging.info(f"SHA-256 for {fileB}: {sha_B}")
            if sha_A == sha_B:
                logging.info(f"Skipping {fileA} and {fileB}: files are identical (SHA-256 match).")
                continue

            # Extract all words from both PDFs
            docA = fitz.open(fileA)
            docB = fitz.open(fileB)
            mismatches = []

            try:
                for page_num in range(len(docB)):
                    try:
                        pageA = docA[page_num] if page_num < len(docA) else None
                        pageB = docB[page_num]

                        wordsA = pageA.get_text("words") if pageA else []
                        wordsB = pageB.get_text("words") or []

                        # Ensure words entries are sequences with expected index 4 for word text
                        min_words = min(len(wordsA), len(wordsB))
                        for i in range(min_words):
                            try:
                                wordA = wordsA[i][4]
                                wordB = wordsB[i][4]
                            except Exception:
                                # malformed word tuple — skip this word but log it
                                logging.warning(f"Malformed word tuple on page {page_num + 1}, word idx {i}")
                                continue

                            if wordA != wordB:
                                # safe bounding for rect coords
                                try:
                                    x0, y0, x1, y1 = wordsB[i][0], wordsB[i][1], wordsB[i][2], wordsB[i][3]
                                    rect = fitz.Rect(x0, y0, x1, y1)
                                    pageB.add_highlight_annot(rect)
                                except Exception as e:
                                    logging.warning(f"Failed to highlight word on page {page_num + 1}, idx {i}: {e}")
                                mismatches.append(f"Page {page_num + 1}, Word {i + 1}: A: {wordA} | B: {wordB}")

                        # handle extra words in B
                        for i in range(min_words, len(wordsB)):
                            try:
                                x0, y0, x1, y1 = wordsB[i][0], wordsB[i][1], wordsB[i][2], wordsB[i][3]
                                rect = fitz.Rect(x0, y0, x1, y1)
                                pageB.add_highlight_annot(rect)
                                wordb = wordsB[i][4] if len(wordsB[i]) > 4 else "<unknown>"
                                mismatches.append(f"Page {page_num + 1}, Word {i + 1}: A: <none> | B: {wordb}")
                            except Exception as e:
                                logging.warning(f"Failed to process extra word on page {page_num + 1}, idx {i}: {e}")
                                continue

                    except Exception as page_err:
                        logging.error(f"Error processing page {page_num + 1} for {fileA} vs {fileB}: {page_err}")
                        # continue with next page instead of failing entire compare
                        continue

                # Add a summary page at the end
                if mismatches:
                    summary_text = "Summary of Mismatches:\n\n" + "\n".join(mismatches)
                    try:
                        summary_page = docB.new_page(-1)
                        summary_page.insert_text((72, 72), summary_text, fontsize=10)
                    except Exception as e:
                        logging.error(f"Failed to add summary page: {e}")

                # --- NEW: Create nested output directory ---
                try:
                    rel_dir = os.path.dirname(rel_path)
                    output_dir = os.path.join(target_folder, rel_dir)
                    os.makedirs(output_dir, exist_ok=True)

                    base_name = f"comparison-{batch}.pdf"
                    outputFile = os.path.join(output_dir, base_name)
                except Exception as e:
                    logging.error(f"Failed to create output directory for {rel_path}: {e}")
                    failed_files_count += 1
                    continue  # Skip this file pair
                # --- END NEW ---
                delete_if_exists(outputFile)
                try:
                    docB.save(outputFile)
                    logging.info(f"Written PDF differences to {outputFile}")
                except Exception as e:
                    logging.error(f"Failed to save PDF comparison file {outputFile}: {e}")
                    failed_files_count += 1

            finally:
                try:
                    docA.close()
                except Exception:
                    pass
                try:
                    docB.close()
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Failed to compare PDFs {fileA} and {fileB}: {e}")
            failed_files_count += 1
    return failed_files_count