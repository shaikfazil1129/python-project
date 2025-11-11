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
    # Safe directory listing (handles permission errors / unreadable dirs)
    try:
        list_src1 = os.listdir(src1)
    except Exception as e:
        logging.error(f"Failed to list directory {src1}: {e}")
        messagebox.showerror("Error", f"Cannot read source folder 1: {src1}\nSee log for details.")
        failed_files_count += 1
        return failed_files_count

    try:
        list_src2 = os.listdir(src2)
    except Exception as e:
        logging.error(f"Failed to list directory {src2}: {e}")
        messagebox.showerror("Error", f"Cannot read source folder 2: {src2}\nSee log for details.")
        failed_files_count += 1
        return failed_files_count

    # Build file maps with case-insensitive extension checks and skip invalid batch names
    files1_xlsx = {}
    for f in list_src1:
        if not f.lower().endswith('.xlsx'):
            continue
        batch = extract_batch(f)
        if batch:
            files1_xlsx[batch] = os.path.join(src1, f)

    files2_xlsx = {}
    for f in list_src2:
        if not f.lower().endswith('.xlsx'):
            continue
        batch = extract_batch(f)
        if batch:
            files2_xlsx[batch] = os.path.join(src2, f)

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
    # Same approach for PDFs
    files1_pdf = {}
    for f in list_src1:
        if not f.lower().endswith('.pdf'):
            continue
        batch = extract_batch(f)
        if batch:
            files1_pdf[batch] = os.path.join(src1, f)

    files2_pdf = {}
    for f in list_src2:
        if not f.lower().endswith('.pdf'):
            continue
        batch = extract_batch(f)
        if batch:
            files2_pdf[batch] = os.path.join(src2, f)

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
        return failed_files_count
    if file_pairs_xlsx:
        failed_files_count += compare_excel_files(file_pairs_xlsx, target)
    if file_pairs_pdf:
        failed_files_count += compare_pdf_files(file_pairs_pdf, target)
    return failed_files_count

def animate_spinner(frame_index=0, text_index=0):
    if not spinner_running:
        return
    # Mode 1: animated GIF frames available
    if spinner_frames:  # list of PhotoImage frames (maybe empty)
        try:
            frame = spinner_frames[frame_index]
            spinner_label.configure(image=frame, text="")  # ensure text cleared
            spinner_label.image = frame  # keep ref to avoid GC
        except Exception as e:
            logging.warning(f"Failed to set spinner image frame: {e}")

        next_index = (frame_index + 1) % len(spinner_frames)
        root.after(100, animate_spinner, next_index, 0)  # 100ms per frame

    # Mode 2: no frames -> text fallback animation (ellipsis)
    else:
        dots = ["", ".", "..", "..."]
        spinner_label.configure(text=f"Processing{dots[text_index]}")
        next_text_index = (text_index + 1) % len(dots)
        # slower cadence for text
        root.after(400, animate_spinner, 0, next_text_index)

def run_comparison_threaded():
    global spinner_running
    # Hide button, show spinner
    run_button.grid_remove()
    spinner_label.grid()
    spinner_running = True
    animate_spinner()  # Start animation
    root.update()

    def task():
        # Heavy work runs in background thread
        failed_count = run_comparison()  # returns int

        # Define a function that runs on the main thread to update UI
        def on_complete(fc):
            global spinner_running
            spinner_running = False
            spinner_label.grid_remove()
            run_button.grid()

            # show messageboxes from main thread (safe)
            target = target_entry.get()
            if fc > 0:
                messagebox.showwarning(
                    "Completed with Errors",
                    f"Count of files: {fc} failed to compare. Please check logs. Remaining results saved in {target}."
                )
            else:
                messagebox.showinfo(
                    "Completed",
                    f"Completed the comparisons. Results saved in {target}."
                )

        # Schedule the UI update to run on the main thread as soon as possible
        root.after(0, on_complete, failed_count)

    threading.Thread(target=task).start()

root = tk.Tk()
root.title("Excel Batch Comparison")

# --- Spinner setup (robust to missing/corrupt spinner.gif) ---
spinner_frames = []
spinner_path = "spinner.gif"

if os.path.exists(spinner_path):
    try:
        # Attempt to load all frames from the GIF
        i = 0
        while True:
            try:
                frame = tk.PhotoImage(file=spinner_path, format=f"gif -index {i}")
                spinner_frames.append(frame)
                i += 1
            except tk.TclError:
                break
    except Exception as e:
        logging.warning(f"Failed to load spinner.gif frames: {e}")
        spinner_frames = []
else:
    logging.warning("spinner.gif not found; using text fallback for progress indicator.")

# If no frames were loaded, use a safe text fallback label
if spinner_frames:
    spinner_label = tk.Label(root, image=spinner_frames[0])
else:
    spinner_label = tk.Label(root, text="Processing...", font=("Arial", 10, "italic"))

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
