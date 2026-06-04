import tkinter as tk
from tkinter import ttk
import random
import platform

root = tk.Tk()
root.title("Advanced Dynamic MLFQ Simulator (with Aging & Arrivals)")
root.geometry("1200x850")

main_canvas = tk.Canvas(root)
main_scrollbar = tk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
main_canvas.configure(yscrollcommand=main_scrollbar.set)

main_scrollbar.pack(side="right", fill="y")
main_canvas.pack(side="left", fill="both", expand=True)

main_frame = tk.Frame(main_canvas)
main_canvas.create_window((0, 0), window=main_frame, anchor="nw")

def on_frame_configure(event):
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))
main_frame.bind("<Configure>", on_frame_configure)

def _on_mousewheel(event):
    if platform.system() == 'Darwin': 
        main_canvas.yview_scroll(int(-1 * event.delta), "units")
    else: 
        main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

# --- GLOBAL STATE ---
queues = []
queue_algorithms = []
queue_quantums = []

burst_remaining = {}
burst_original = {}
priority = {}
arrival_times = {}

not_arrived = []
wait_times = {} 
last_run_pid = None

gantt = []
current_time = 0
scale = 40

colors = {}
process_tokens = {} 
active_anims = {}
sim_running = False

# ---------------- TITLE ----------------
title = tk.Label(main_frame, text="Advanced MLFQ Simulator", font=("Arial", 18, "bold"))
title.pack(pady=5)

# ---------------- CONFIGURATION SETUP ----------------
config_frame = tk.Frame(main_frame)
config_frame.pack(pady=5)

tk.Label(config_frame, text="Number of Queues:").grid(row=0, column=0, padx=5)
queue_count_entry = tk.Entry(config_frame, width=5)
queue_count_entry.insert(0, "3")
queue_count_entry.grid(row=0, column=1, padx=5)

tk.Label(config_frame, text="Aging Threshold:").grid(row=0, column=2, padx=5)
aging_entry = tk.Entry(config_frame, width=5)
aging_entry.grid(row=0, column=3, padx=5)
tk.Label(config_frame, text="(blank to disable)").grid(row=0, column=4)

tk.Label(config_frame, text="Context Switch Time:").grid(row=0, column=5, padx=5)
cs_entry = tk.Entry(config_frame, width=5)
cs_entry.grid(row=0, column=6, padx=5)

queue_setup_frame = tk.Frame(main_frame)
queue_setup_frame.pack(pady=5)

def create_queues():
    for w in queue_setup_frame.winfo_children():
        w.destroy()

    queues.clear()
    queue_algorithms.clear()
    queue_quantums.clear()
    anim_canvas.delete("token")

    n = int(queue_count_entry.get())
    anim_canvas.config(height=max(300, n * 100 + 80))

    for i in range(n):
        queues.append([])
        tk.Label(queue_setup_frame, text=f"Queue {i+1} Algorithm").grid(row=i, column=0)
        algo_var = tk.StringVar()

        if i == n - 1:
            algo_var.set("FCFS")
            menu = tk.OptionMenu(queue_setup_frame, algo_var, "FCFS", "SJF", "Priority Non-Preemptive", "RR")
        else:
            menu = tk.OptionMenu(queue_setup_frame, algo_var, "RR", "FCFS", "SJF", "SRTF", "Priority Preemptive", "Priority Non-Preemptive")

        menu.grid(row=i, column=1)
        tk.Label(queue_setup_frame, text="Quantum").grid(row=i, column=2)
        quantum = tk.Entry(queue_setup_frame, width=5)
        quantum.grid(row=i, column=3)

        queue_algorithms.append(algo_var)
        queue_quantums.append(quantum)
        
    draw_static_animation_bg()

tk.Button(config_frame, text="Create Queues", command=create_queues, bg="lightblue").grid(row=0, column=7, padx=15)

# ---------------- PROCESS INPUT ----------------
proc_frame = tk.Frame(main_frame)
proc_frame.pack(pady=5)

tk.Label(proc_frame, text="PID").grid(row=0, column=0)
pid_entry = tk.Entry(proc_frame, width=6)
pid_entry.grid(row=0, column=1)

tk.Label(proc_frame, text="Arrival").grid(row=0, column=2)
arr_entry = tk.Entry(proc_frame, width=6)
arr_entry.grid(row=0, column=3)

tk.Label(proc_frame, text="Burst").grid(row=0, column=4)
burst_entry = tk.Entry(proc_frame, width=6)
burst_entry.grid(row=0, column=5)

tk.Label(proc_frame, text="Priority").grid(row=0, column=6)
priority_entry = tk.Entry(proc_frame, width=6)
priority_entry.grid(row=0, column=7)

def add_process():
    pid = pid_entry.get()
    if not pid: return
    
    arr_val = arr_entry.get()
    arr = float(arr_val) if arr_val else 0.0
    
    burst = float(burst_entry.get())
    pr = priority_entry.get()

    burst_remaining[pid] = burst
    burst_original[pid] = burst
    arrival_times[pid] = arr
    priority[pid] = 0 if pr == "" else int(pr)
    wait_times[pid] = 0
    colors[pid] = "#%06x" % random.randint(0, 0xFFFFFF)

    not_arrived.append(pid)

    token_rect = anim_canvas.create_rectangle(0, 0, 30, 30, fill=colors[pid], outline="black", width=2, tags=("token", pid))
    token_text = anim_canvas.create_text(15, 15, text=pid, fill="white", font=("Arial", 9, "bold"), tags=("token", f"text_{pid}"))
    process_tokens[pid] = (token_rect, token_text)

    pid_entry.delete(0, tk.END)
    arr_entry.delete(0, tk.END)
    burst_entry.delete(0, tk.END)
    priority_entry.delete(0, tk.END)

    refresh_queues()

tk.Button(proc_frame, text="Add Process", command=add_process).grid(row=0, column=8, padx=10)

# ---------------- ANIMATION BOARD ----------------
cpu_label = tk.Label(main_frame, text="CPU Running : None | Time: 0", font=("Arial", 14, "bold"))
cpu_label.pack(pady=2)

anim_canvas = tk.Canvas(main_frame, width=900, height=400, bg="white", highlightbackground="black", highlightthickness=1)
anim_canvas.pack(pady=5)

def draw_static_animation_bg():
    anim_canvas.delete("static")
    
    anim_canvas.create_rectangle(15, 10, 235, 100, outline="black", fill="#D3D3D3", tags="static", dash=(4,4))
    anim_canvas.create_text(125, 20, text="Incoming Pool (Not Arrived)", font=("Arial", 10, "bold"), fill="black", tags="static")

    n = len(queues)
    for i in range(n):
        y_offset = 130 + (i * 90) 
        anim_canvas.create_rectangle(250, y_offset, 600, y_offset+50, outline="#007ACC", fill="#E6F2FF", width=2, tags="static")
        
        algo = queue_algorithms[i].get()
        q_val = queue_quantums[i].get()
        label_text = f"Queue {i+1}: {algo}"
        if algo == "RR" and q_val: label_text += f" (Q={q_val})"
        anim_canvas.create_text(425, y_offset-15, text=label_text, font=("Arial", 10, "bold"), fill="#005C99", tags="static")

        anim_canvas.create_line(150, y_offset+25, 250, y_offset+25, arrow=tk.LAST, fill="gray", width=2, tags="static")
        anim_canvas.create_line(600, y_offset+15, 750, y_offset+15, arrow=tk.LAST, fill="gray", width=2, tags="static")
        anim_canvas.create_text(780, y_offset+15, text="Finished", font=("Arial", 9, "italic"), tags="static")

        if i < n - 1:
            anim_canvas.create_line(600, y_offset+35, 630, y_offset+35, 630, y_offset+75, 150, y_offset+75, 150, y_offset+115, arrow=tk.LAST, fill="#FF6666", width=2, tags="static")

def slide_token(pid, target_x, target_y, steps, callback):
    if pid not in process_tokens:
        if callback: callback()
        return
    rect, text = process_tokens[pid]
    coords = anim_canvas.coords(rect)
    if not coords:
        if callback: callback()
        return
        
    if pid in active_anims:
        root.after_cancel(active_anims[pid])
        
    current_x, current_y = coords[0], coords[1]
    dx, dy = (target_x - current_x) / steps, (target_y - current_y) / steps

    def step_move(current_step):
        if current_step < steps:
            anim_canvas.move(rect, dx, dy)
            anim_canvas.move(text, dx, dy)
            # FIX: Slowed the frame rate down to 30ms for smooth, readable animation
            active_anims[pid] = root.after(30, lambda: step_move(current_step + 1)) 
        else:
            if pid in active_anims: del active_anims[pid]
            if callback: callback()
            
    step_move(0)

def refresh_queues():
    for idx, pid in enumerate(not_arrived):
        if pid in process_tokens:
            row = idx // 5
            col = idx % 5
            # FIX: More steps = slower slide into the incoming pool
            slide_token(pid, 25 + (col*40), 35 + (row*35), steps=15, callback=None)

    for i, q in enumerate(queues):
        for idx, pid in enumerate(q):
            if pid in process_tokens:
                target_x = 260 + (idx * 40)
                target_y = 130 + (i * 90) 
                # FIX: More steps = slower slide within the queue
                slide_token(pid, target_x, target_y, steps=15, callback=None)

# ---------------- GANTT CHART & STATS ----------------
tk.Label(main_frame, text="Gantt Chart", font=("Arial", 12, "bold")).pack()
canvas_frame = tk.Frame(main_frame)
canvas_frame.pack()

scroll = tk.Scrollbar(canvas_frame, orient="horizontal")
scroll.pack(side="bottom", fill="x")
gantt_canvas = tk.Canvas(canvas_frame, width=1000, height=100, bg="white", xscrollcommand=scroll.set)
gantt_canvas.pack()
scroll.config(command=gantt_canvas.xview)

def draw_time_axis():
    gantt_canvas.delete("time")
    for p, start, end in gantt:
        x = start * scale + 20
        gantt_canvas.create_text(x, 20, text=str(round(start, 1)), font=("Arial", 9, "bold"), fill="black", tags="time")
        gantt_canvas.create_line(x, 30, x, 40, fill="black", tags="time", width=1)
    if gantt:
        final_time = gantt[-1][2]
        final_x = final_time * scale + 20
        gantt_canvas.create_text(final_x, 20, text=str(round(final_time, 1)), font=("Arial", 9, "bold"), fill="black", tags="time")
        gantt_canvas.create_line(final_x, 30, final_x, 40, fill="black", tags="time", width=1)

def draw_gantt_block(p, start, end):
    x1, x2 = start * scale + 20, end * scale + 20
    if p == "IDLE":
        gantt_canvas.create_rectangle(x1, 40, x2, 80, fill="#f0f0f0", stipple="gray50", outline="black")
        gantt_canvas.create_text((x1 + x2) / 2, 60, text="IDLE", fill="black", font=("Arial", 8))
    elif p == "CS":
        gantt_canvas.create_rectangle(x1, 40, x2, 80, fill="#404040", outline="black")
        gantt_canvas.create_text((x1 + x2) / 2, 60, text="CS", fill="white", font=("Arial", 8))
    else:
        gantt_canvas.create_rectangle(x1, 40, x2, 80, fill=colors[p], outline="black", width=2)
        gantt_canvas.create_text((x1 + x2) / 2, 60, text=p, fill="white", font=("Arial", 10, "bold"))
    
    draw_time_axis()
    gantt_canvas.config(scrollregion=gantt_canvas.bbox("all"))

table_frame = tk.Frame(main_frame)
table_frame.pack(pady=5)

columns = ("Process", "Arrival Time", "Burst Time", "Priority", "Finish Time", "Turnaround Time", "Waiting Time")
tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=4)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=110, anchor="center") 
tree.pack()

stats_label = tk.Label(main_frame, font=("Arial", 12, "bold"))
stats_label.pack()

def compute_stats():
    for row in tree.get_children(): tree.delete(row)
        
    completion = {p: end for p, start, end in gantt if p not in ["IDLE", "CS"]}
    total_wait = total_turn = 0
    
    def get_sort_key(pid):
        num_part = ''.join(filter(str.isdigit, pid))
        return int(num_part) if num_part else pid

    sorted_processes = sorted(completion.keys(), key=get_sort_key)
    n = len(sorted_processes)

    for p in sorted_processes:
        arr_time = arrival_times[p]
        burst = burst_original[p]
        pr_val = priority.get(p, 0)
        finish_time = completion[p]
        turnaround = finish_time - arr_time
        waiting = turnaround - burst
        total_wait += waiting
        total_turn += turnaround
        tree.insert("", "end", values=(p, arr_time, burst, pr_val, round(finish_time,1), round(turnaround,1), round(waiting,1)))

    avg_wait = total_wait / n if n > 0 else 0
    avg_turn = total_turn / n if n > 0 else 0
    stats_label.config(text=f"Average Waiting Time : {avg_wait:.2f}    Average Turnaround Time : {avg_turn:.2f}")

# ---------------- SIMULATION ENGINE ----------------
def simulate_step():
    global current_time, sim_running, last_run_pid 
    if not sim_running: return 
    
    cpu_label.config(text=f"CPU Running : Processing... | Time: {round(current_time,1)}")
    
    arrived_this_step = False
    for p in list(not_arrived):
        if arrival_times[p] <= current_time:
            not_arrived.remove(p)
            queues[0].append(p)
            wait_times[p] = 0
            arrived_this_step = True
            
    try:
        aging_thresh = float(aging_entry.get())
    except ValueError:
        aging_thresh = float('inf')

    aged_this_step = False
    if aging_thresh > 0 and aging_thresh != float('inf'):
        for i in range(1, len(queues)):
            for p in list(queues[i]):
                if wait_times.get(p, 0) >= aging_thresh:
                    queues[i].remove(p)
                    queues[0].append(p)
                    wait_times[p] = 0 
                    aged_this_step = True
                    
    if arrived_this_step or aged_this_step:
        refresh_queues()

    if all(len(q) == 0 for q in queues):
        if not_arrived:
            next_arr = min(arrival_times[p] for p in not_arrived)
            start = current_time
            current_time = next_arr
            gantt.append(("IDLE", start, current_time))
            draw_gantt_block("IDLE", start, current_time)
            last_run_pid = "IDLE"
            # FIX: Added a generous pause during idle jumps
            root.after(400, simulate_step) 
            return
        else:
            cpu_label.config(text=f"All Processes Finished | Total Time: {round(current_time,1)}")
            start_btn.config(state=tk.NORMAL) 
            sim_running = False
            compute_stats()
            return

    n = len(queues)
    selected_p, selected_q_idx = None, -1

    for i in range(n):
        if queues[i]:
            p = queues[i][0]
            algo = queue_algorithms[i].get()

            if algo == "RR":
                p = queues[i].pop(0)
            elif algo in ["FCFS", "Priority Non-Preemptive"]:
                if algo == "Priority Non-Preemptive":
                    p = min(queues[i], key=lambda x: priority[x])
                queues[i].remove(p)
            elif algo in ["SJF", "SRTF", "Priority Preemptive"]:
                key_func = lambda x: burst_remaining[x] if algo in ["SJF", "SRTF"] else lambda x: priority[x]
                p = min(queues[i], key=key_func)
                queues[i].remove(p)

            selected_p = p
            selected_q_idx = i
            break

    p = selected_p
    i = selected_q_idx

    try:
        cs_time = float(cs_entry.get())
    except ValueError:
        cs_time = 0

    if last_run_pid is not None and last_run_pid != p and last_run_pid != "IDLE" and cs_time > 0:
        start = current_time
        current_time += cs_time
        gantt.append(("CS", start, current_time))
        draw_gantt_block("CS", start, current_time)
        
        for q in queues:
            for wp in q:
                wait_times[wp] += cs_time

    last_run_pid = p

    try:
        q_str = queue_quantums[i].get()
        q_val = float(q_str) if q_str.strip() else float('inf')
        if q_val <= 0: q_val = float('inf')
    except ValueError:
        q_val = float('inf')
        
    run = min(q_val, burst_remaining[p])

    algo = queue_algorithms[i].get()
    was_preempted = False
    
    if not_arrived:
        next_arrival = min(arrival_times[x] for x in not_arrived)
        if current_time < next_arrival < current_time + run:
            if i > 0 or algo in ["SRTF", "Priority Preemptive", "RR"]: 
                run = next_arrival - current_time
                was_preempted = True

    for q in queues:
        for wp in q:
            wait_times[wp] += run

    run_x = 560 
    run_y = 130 + (i * 90)

    def process_and_continue():
        global current_time
        if not sim_running: return
        
        start = current_time
        end = current_time + run
        
        gantt.append((p, start, end))
        burst_remaining[p] -= run
        current_time = end
        
        draw_gantt_block(p, start, end)
        
        if burst_remaining[p] > 0:
            if was_preempted:
                target_queue = i
            else:
                target_queue = i + 1 if i + 1 < n else i
                
            queues[target_queue].append(p)
            wait_times[p] = 0 
            
            queue_pos_x = 260 + ((len(queues[target_queue]) - 1) * 40)
            queue_pos_y = 130 + (target_queue * 90)
            
            def return_to_queue_done():
                refresh_queues()
                # FIX: Pause before processing next step so user can digest the move
                root.after(300, simulate_step)

            # FIX: More steps = slower, smoother slide to queue
            slide_token(p, queue_pos_x, queue_pos_y, steps=20, callback=return_to_queue_done) 
        else:
            def finish_slide_done():
                if p in process_tokens:
                    anim_canvas.delete(process_tokens[p][0])
                    anim_canvas.delete(process_tokens[p][1])
                    del process_tokens[p]
                refresh_queues()
                # FIX: Pause before processing next step
                root.after(300, simulate_step)
            # FIX: More steps = slower, smoother exit
            slide_token(p, 800, run_y, steps=20, callback=finish_slide_done)

    cpu_label.config(text=f"CPU Running : {p} (Queue {i+1}) | Time: {round(current_time,1)}")
    
    # FIX: More steps = deliberate slide into the CPU
    slide_token(p, run_x, run_y, steps=25, callback=process_and_continue)

# ---------------- BUTTONS ----------------
btn_frame = tk.Frame(main_frame)
btn_frame.pack(pady=10)

def start_simulation():
    global sim_running
    sim_running = True
    start_btn.config(state=tk.DISABLED) 
    simulate_step()

def reset_sim():
    global current_time, gantt, sim_running, last_run_pid
    sim_running = False
    current_time = 0
    gantt = []
    last_run_pid = None

    for pid in active_anims: root.after_cancel(active_anims[pid])
    active_anims.clear()

    for pid in process_tokens:
        anim_canvas.delete(process_tokens[pid][0])
        anim_canvas.delete(process_tokens[pid][1])
    process_tokens.clear()

    burst_remaining.clear()
    burst_original.clear()
    priority.clear()
    arrival_times.clear()
    not_arrived.clear()
    wait_times.clear()
    colors.clear()
    for q in queues: q.clear()
    refresh_queues()

    cpu_label.config(text="CPU Running : None | Time: 0")
    gantt_canvas.delete("all")
    for row in tree.get_children(): tree.delete(row)
    stats_label.config(text="")
    start_btn.config(state=tk.NORMAL)

start_btn = tk.Button(btn_frame, text="Start Simulation", command=start_simulation, bg="lightgreen", font=("Arial", 10, "bold"))
start_btn.grid(row=0, column=0, padx=10)

reset_btn = tk.Button(btn_frame, text="Reset", command=reset_sim, bg="#FF6666", font=("Arial", 10, "bold"))
reset_btn.grid(row=0, column=1, padx=10)

root.update_idletasks()
main_canvas.configure(scrollregion=main_canvas.bbox("all"))
root.mainloop()