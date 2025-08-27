import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import pywifi
from pywifi import const
import time
import json
import os
import threading

CONFIG_FILE = "known_networks.json"
IGNORED_SSIDS_FILE = "ignored_ssids.json"
IGNORED_BSSIDS_FILE = "ignored_bssids.json"

AUTO_REFRESH_INTERVAL = 10 * 1000  # 30 seconds

def load_known_networks():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_known_networks(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_ignored_ssids():
    if os.path.exists(IGNORED_SSIDS_FILE):
        with open(IGNORED_SSIDS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_ignored_ssids(data):
    with open(IGNORED_SSIDS_FILE, "w") as f:
        json.dump(list(data), f, indent=4)

def load_ignored_bssids():
    if os.path.exists(IGNORED_BSSIDS_FILE):
        with open(IGNORED_BSSIDS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_ignored_bssids(data):
    with open(IGNORED_BSSIDS_FILE, "w") as f:
        json.dump(list(data), f, indent=4)

def prompt_color(ssid, bssid):
    result = messagebox.askyesno("New WiFi Detected", f"You just connected to '{ssid}'. Would you like to assign a color?")
    if result:
        color_code = colorchooser.askcolor(title=f"Pick a color for '{ssid}'")[1]
        if color_code:
            known[bssid] = {"ssid": ssid, "color": color_code}
            save_known_networks(known)
            messagebox.showinfo("Saved", f"Color saved for '{ssid}'")

def get_current_bssid(results):
    iface = pywifi.PyWiFi().interfaces()[0]
    if iface.status() == const.IFACE_CONNECTED:
        for net in results:
            if net.ssid:
                return net.bssid.lower()
    return None

def scan_wifi_async(user_triggered=False):
    if user_triggered:
        status_label.config(text="Scanning...")
    button.config(state="disabled")
    ignore_button.config(state="disabled")
    text_area.delete(*text_area.get_children())

    def scan():
        wifi = pywifi.PyWiFi()
        iface = wifi.interfaces()[0]
        iface.scan()
        time.sleep(8)
        results = iface.scan_results()
        current_bssid = get_current_bssid(results)

        if current_bssid and current_bssid not in known:
            for net in results:
                if net.bssid.lower() == current_bssid:
                    prompt_color(net.ssid, current_bssid)
                    break

        added_ssids = set()
        for net in results:
            ssid = net.ssid
            bssid = net.bssid.lower()
            if not ssid or ssid in ignored_ssids or bssid in ignored_bssids or ssid in added_ssids:
                continue
            tags = ()
            if bssid in known:
                tag_name = bssid.replace(":", "")
                tags = (tag_name,)
                text_area.tag_configure(tag_name, background=known[bssid]["color"])
            text_area.insert("", "end", values=(ssid,), tags=tags)
            added_ssids.add(ssid)

        root.after(0, lambda: status_label.config(text="Scan complete."))
        root.after(0, lambda: button.config(state="normal"))
        root.after(0, lambda: ignore_button.config(state="normal"))

        # Schedule next auto-refresh if enabled
        if auto_refresh_var.get():
            root.after(AUTO_REFRESH_INTERVAL, lambda: scan_wifi_async(user_triggered=False))

    threading.Thread(target=scan).start()

def ignore_selected():
    sel = text_area.selection()
    if not sel:
        messagebox.showwarning("Nothing selected", "Select a network first.")
        return
    for iid in sel:
        ssid = text_area.item(iid, "values")[0]
        for net in pywifi.PyWiFi().interfaces()[0].scan_results():
            if net.ssid == ssid:
                ignored_bssids.add(net.bssid.lower())
        ignored_ssids.add(ssid)
        text_area.delete(iid)
    save_ignored_ssids(ignored_ssids)
    save_ignored_bssids(ignored_bssids)

# Load saved data
known = load_known_networks()
ignored_ssids = load_ignored_ssids()
ignored_bssids = load_ignored_bssids()

# GUI setup
root = tk.Tk()
root.title("Smart WiFi Identifier")
root.geometry("460x580")
root.configure(bg="black")

# Title
label = tk.Label(root, text="WiFi Identifier", font=("Helvetica", 16, "bold"), fg="white", bg="black")
label.pack(pady=10)

# Status label
status_label = tk.Label(root, text="", font=("Helvetica", 10), fg="white", bg="black")
status_label.pack()

# Buttons
button_style = {
    "font": ("Helvetica", 12, "bold"),
    "bg": "black",
    "fg": "white",
    "activebackground": "#333333",
    "activeforeground": "white",
    "bd": 2,
    "relief": "groove",
    "highlightthickness": 1,
    "highlightbackground": "white",
    "highlightcolor": "white",
    "width": 18,
    "cursor": "hand2"
}

button = tk.Button(root, text="Scan WiFi", command=lambda: scan_wifi_async(user_triggered=True), **button_style)
button.pack(pady=5)

ignore_button = tk.Button(root, text="Ignore Network", command=ignore_selected, **button_style)
ignore_button.pack(pady=5)

# Auto-refresh toggle
auto_refresh_var = tk.BooleanVar()
auto_refresh_check = tk.Checkbutton(root, text="Auto-Refresh Every 10s", variable=auto_refresh_var,
                                    font=("Helvetica", 10), bg="black", fg="white", activebackground="black",
                                    activeforeground="lime", selectcolor="black")
auto_refresh_check.pack(pady=5)

# Treeview styling
style = ttk.Style()
style.theme_use("default")
style.configure("Treeview",
                background="black",
                fieldbackground="black",
                foreground="white",
                rowheight=25)
style.configure("Treeview.Heading",
                background="white",
                foreground="black",
                font=('Helvetica', 12, 'bold'))

columns = ("SSID",)
text_area = ttk.Treeview(root, columns=columns, show="headings", height=15)
text_area.heading("SSID", text="SSID")
text_area.column("SSID", anchor=tk.CENTER, width=400)
text_area.pack(pady=10)

root.mainloop()
