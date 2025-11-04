import os
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from comparer.utils import extract_batch, logging
from comparer.excel_compare import compare_excel_files
from comparer.pdf_compare import compare_pdf_files
# rest of your GUI and run_comparison logic — unchanged

# (Paste your GUI and run_comparison functions here exactly as in your code)

def select_folder(entry):
    folder = filedialog.askdirectory()
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)

def run_comparison():
    failed_files_count = 0  # Track files that fail to compare
    src1 = src1_entry.get()
    src2 = src2_entry.get()
    target = target_entry.get()
    if not (os.path.isdir(src1) and os.path.isdir(src2) and os.path.isdir(target)):
        messagebox.showerror("Error", "Please select valid folders.")
        return failed_files_count
    # Excel files
    files1_xlsx = {extract_batch(f): os.path.join(src1, f) for f in os.listdir(src1) if f.endswith('.xlsx') and extract_batch(f)}
    files2_xlsx = {extract_batch(f): os.path.join(src2, f) for f in os.listdir(src2) if f.endswith('.xlsx') and extract_batch(f)}
    common_batches_xlsx = set(files1_xlsx.keys()) & set(files2_xlsx.keys())
    # --- Log unmatched Excel files ---
    unmatched_xlsx_src1 = set(files1_xlsx.keys()) - common_batches_xlsx
    unmatched_xlsx_src2 = set(files2_xlsx.keys()) - common_batches_xlsx

    for batch in unmatched_xlsx_src1:
        logging.info(
            f"{os.path.basename(src1)} - File '{os.path.basename(files1_xlsx[batch])}' is not compared due to missing or inconsistent batch name in FolderB")
        failed_files_count += 1
    for batch in unmatched_xlsx_src2:
        logging.info(
            f"{os.path.basename(src2)} - File '{os.path.basename(files2_xlsx[batch])}' is not compared due to missing or inconsistent batch name in FolderA")
        failed_files_count += 1

    file_pairs_xlsx = [(files1_xlsx[batch], files2_xlsx[batch], batch) for batch in common_batches_xlsx]
    # PDF files
    files1_pdf = {extract_batch(f): os.path.join(src1, f) for f in os.listdir(src1) if f.endswith('.pdf') and extract_batch(f)}
    files2_pdf = {extract_batch(f): os.path.join(src2, f) for f in os.listdir(src2) if f.endswith('.pdf') and extract_batch(f)}
    common_batches_pdf = set(files1_pdf.keys()) & set(files2_pdf.keys())

    # --- Log unmatched PDF files ---
    unmatched_pdf_src1 = set(files1_pdf.keys()) - common_batches_pdf
    unmatched_pdf_src2 = set(files2_pdf.keys()) - common_batches_pdf

    for batch in unmatched_pdf_src1:
        logging.info(
            f"{os.path.basename(src1)} - File '{os.path.basename(files1_pdf[batch])}' is not compared due to missing or inconsistent batch name in FolderB")
        failed_files_count += 1
    for batch in unmatched_pdf_src2:
        logging.info(
            f"{os.path.basename(src2)} - File '{os.path.basename(files2_pdf[batch])}' is not compared due to missing or inconsistent batch name in FolderA")
        failed_files_count += 1

    file_pairs_pdf = [(files1_pdf[batch], files2_pdf[batch], batch) for batch in common_batches_pdf]
    if not file_pairs_xlsx and not file_pairs_pdf:
        messagebox.showinfo("Info", "No matching batch files found.")
        return
    if file_pairs_xlsx:
        compare_excel_files(file_pairs_xlsx, target, failed_files_count)
    if file_pairs_pdf:
        compare_pdf_files(file_pairs_pdf, target, failed_files_count)
    return failed_files_count

def animate_spinner(frame_index=0):
    if not spinner_running:
        return
    spinner_label.configure(image=spinner_frames[frame_index])
    next_index = (frame_index + 1) % len(spinner_frames)
    root.after(100, animate_spinner, next_index)  # adjust 100ms for speed

def run_comparison_threaded():
    global spinner_running
    # Hide button, show spinner
    run_button.grid_remove()
    spinner_label.grid()
    spinner_running = True
    animate_spinner()  # Start animation
    root.update()

    def task():
        failed_count = run_comparison()  # run_comparison now returns failure count

        global spinner_running
        spinner_running = False
        spinner_label.grid_remove()
        run_button.grid()

        # Show appropriate message
        target = target_entry.get()
        if failed_count > 0:
            messagebox.showwarning("Completed with Errors",
                                   f"Count of files: {failed_count} failed to compare. Please check logs. Remaining results saved in {target}.")
        else:
            messagebox.showinfo("Completed",
                                f"Completed the comparisons. Results saved in {target}.")

    threading.Thread(target=task).start()

root = tk.Tk()
root.title("Excel Batch Comparison")

# --- Spinner setup ---
spinner_frames = []
spinner_image = tk.PhotoImage(file="spinner.gif", format="gif -index 0")
spinner_frames.append(spinner_image)

i = 1
while True:
    try:
        frame = tk.PhotoImage(file="spinner.gif", format=f"gif -index {i}")
        spinner_frames.append(frame)
        i += 1
    except tk.TclError:
        break

spinner_label = tk.Label(root, image=spinner_frames[0])
spinner_label.grid(row=3, column=1, pady=10)
spinner_label.grid_remove()  # hide initially
spinner_running = False  # control flag for animation

tk.Label(root, text="Source Folder 1:").grid(row=0, column=0, sticky="e")
src1_entry = tk.Entry(root, width=50)
src1_entry.grid(row=0, column=1)
tk.Button(root, text="Browse", command=lambda: select_folder(src1_entry)).grid(row=0, column=2)

tk.Label(root, text="Source Folder 2:").grid(row=1, column=0, sticky="e")
src2_entry = tk.Entry(root, width=50)
src2_entry.grid(row=1, column=1)
tk.Button(root, text="Browse", command=lambda: select_folder(src2_entry)).grid(row=1, column=2)

tk.Label(root, text="Target Folder:").grid(row=2, column=0, sticky="e")
target_entry = tk.Entry(root, width=50)
target_entry.grid(row=2, column=1)
tk.Button(root, text="Browse", command=lambda: select_folder(target_entry)).grid(row=2, column=2)

run_button = tk.Button(root, text="Run Comparison", command=run_comparison_threaded, bg="lightgreen")
run_button.grid(row=3, column=1, pady=10)


root.mainloop()
