import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import json
import os
import sys
import threading
import socket
import select
import paramiko
import requests


# Ścieżka do pliku JSON uwzględniająca PyInstaller
if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_PATH, "connections.json")


# --- Tunel SSH ---
class ForwardServer(threading.Thread):
    def __init__(self, local_port, remote_host, remote_port, ssh_client):
        super().__init__()
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.ssh_client = ssh_client
        self.running = True
        self.daemon = True

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', self.local_port))
        sock.listen(5)

        while self.running:
            rlist, _, _ = select.select([sock], [], [], 1)
            if sock in rlist:
                client_sock, _ = sock.accept()
                threading.Thread(
                    target=self.forward_handler,
                    args=(client_sock,),
                    daemon=True
                ).start()

        sock.close()

    def forward_handler(self, client_sock):
        try:
            chan = self.ssh_client.get_transport().open_channel(
                "direct-tcpip",
                (self.remote_host, self.remote_port),
                client_sock.getpeername()
            )
        except Exception as e:
            print("SSH error:", e)
            client_sock.close()
            return

        while self.running:
            rlist, _, _ = select.select([client_sock, chan], [], [], 1)

            if client_sock in rlist:
                data = client_sock.recv(1024)
                if not data:
                    break
                chan.send(data)

            if chan in rlist:
                data = chan.recv(1024)
                if not data:
                    break
                client_sock.send(data)

        chan.close()
        client_sock.close()

    def stop(self):
        self.running = False


# --- GUI ---
class PortForwardApp:

    def __init__(self, root):

        self.root = root
        self.root.title("TunnelDesk v1.1")
        self.root.geometry("900x520")

        self.active_forwardings = {}
        self.jumphosts = []
        self.services = {}

        self.load_config()

        tk.Label(root, text="Select Jumphost:", font=("Arial", 12)).pack(pady=5)

        self.jumphost_var = tk.StringVar(
            value=self.jumphosts[0] if self.jumphosts else ""
        )

        self.jumphost_menu = ttk.Combobox(
            root,
            textvariable=self.jumphost_var,
            values=self.jumphosts,
            state="readonly"
        )

        self.jumphost_menu.pack(pady=5)

        tk.Label(root, text="Jumphost Password:", font=("Arial", 12)).pack(pady=5)

        self.password_var = tk.StringVar()

        self.password_entry = tk.Entry(
            root,
            textvariable=self.password_var,
            show="*",
            width=30,
            font=("Arial", 12)
        )

        self.password_entry.pack(pady=5)

        tk.Label(root,
                 text="Services to forward:",
                 font=("Arial", 14)).pack(pady=10)

        self.service_names = list(self.services.keys())

        columns = ("Service", "Port", "Remote Host", "Status", "URL")

        self.tree = ttk.Treeview(
            root,
            columns=columns,
            show="headings",
            height=10
        )

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160)

        self.tree.pack(fill="x", padx=20)

        self.refresh_tree()

        button_frame = tk.Frame(root)
        button_frame.pack(pady=10, fill="x")

        btn_style = {"font": ("Arial", 11), "width": 20, "height": 2}

        tk.Button(button_frame,
                  text="Start Forwarding",
                  command=self.start_forwarding,
                  bg="#4CAF50",
                  **btn_style).pack(side="left", padx=5)

        tk.Button(button_frame,
                  text="Stop Forwarding",
                  command=self.stop_forwarding,
                  bg="#d9534f",
                  **btn_style).pack(side="left", padx=5)

        tk.Button(button_frame,
                  text="Open in Browser",
                  command=self.open_browser,
                  bg="#2196F3",
                  **btn_style).pack(side="left", padx=5)

        tk.Button(button_frame,
                  text="Stop All",
                  command=self.stop_all_forwardings,
                  bg="#f57c00",
                  **btn_style).pack(side="left", padx=5)

        tk.Button(button_frame,
                  text="Refresh Active",
                  command=self.refresh_active_forwardings,
                  bg="#9C27B0",
                  **btn_style).pack(side="left", padx=5)

        self.status_label = tk.Label(
            root,
            text="Status: 0 active tunnels",
            font=("Arial", 12)
        )

        self.status_label.pack(pady=5)

    # ---------------- CONFIG ----------------

    def load_config(self):

        GCP_URL = "https://europe-west1-mcrtechsystem-development.cloudfunctions.net/getConfigs?topic=connections"

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                self.jumphosts = data.get("jumphosts", [])
                self.services = data.get("services", {})
                return
            except Exception as e:
                messagebox.showwarning(
                    "Config error",
                    f"Failed to read connections.json:\n{e}"
                )

        try:
            r = requests.get(GCP_URL, timeout=5)
            r.raise_for_status()
            data = r.json()
            self.jumphosts = data.get("jumphosts", [])
            self.services = data.get("services", {})
        except Exception as e:
            self.jumphosts = []
            self.services = {}
            messagebox.showwarning(
                "Config error",
                f"Failed to fetch remote config:\n{e}"
            )

    # ---------------- TREE ----------------

    def refresh_tree(self):

        for i in self.tree.get_children():
            self.tree.delete(i)

        for name in self.service_names:

            local_port, remote_host, remote_port, url = self.services[name]

            status = "Running" if name in self.active_forwardings else "Stopped"

            self.tree.insert(
                "",
                "end",
                iid=name,
                values=(name,
                        local_port,
                        remote_host,
                        status,
                        url or "")
            )

    # ---------------- SELECT ----------------

    def get_selected_service(self):

        sel = self.tree.selection()

        if not sel:
            messagebox.showerror("Error", "Please select a service")
            return None

        return sel[0]

    # ---------------- START ----------------

    def start_forwarding(self):

        name = self.get_selected_service()

        if not name:
            return

        if name in self.active_forwardings:
            messagebox.showinfo("Info", "Already running")
            return

        password = self.password_var.get()

        if not password:
            messagebox.showerror("Error", "Please enter the password")
            return

        local_port, remote_host, remote_port, url = self.services[name]

        userhost = self.jumphost_var.get()

        username, host = userhost.split("@") if "@" in userhost else (userhost, userhost)

        try:

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh_client.connect(
                hostname=host,
                username=username,
                password=password
            )

            forward_thread = ForwardServer(
                local_port,
                remote_host,
                remote_port,
                ssh_client
            )

            forward_thread.start()

            self.active_forwardings[name] = (ssh_client, forward_thread)

            self.refresh_tree()
            self.update_status()

        except Exception as e:

            messagebox.showerror("SSH error", str(e))

    # ---------------- STOP ----------------

    def stop_forwarding(self):

        name = self.get_selected_service()

        if not name:
            return

        if name not in self.active_forwardings:
            messagebox.showinfo("Info", "Not running")
            return

        ssh_client, forward_thread = self.active_forwardings[name]

        forward_thread.stop()
        ssh_client.close()

        del self.active_forwardings[name]

        self.refresh_tree()
        self.update_status()

    # ---------------- STOP ALL ----------------

    def stop_all_forwardings(self):

        for name, (ssh_client, forward_thread) in list(self.active_forwardings.items()):

            forward_thread.stop()
            ssh_client.close()

        self.active_forwardings.clear()

        self.refresh_tree()
        self.update_status()

    # ---------------- REFRESH ACTIVE ----------------

    def refresh_active_forwardings(self):

        if not self.active_forwardings:
            messagebox.showinfo("Info", "No active tunnels")
            return

        running = list(self.active_forwardings.keys())

        password = self.password_var.get()

        if not password:
            messagebox.showerror("Error", "Please enter the password")
            return

        userhost = self.jumphost_var.get()

        username, host = userhost.split("@") if "@" in userhost else (userhost, userhost)

        # stop
        for name, (ssh_client, forward_thread) in list(self.active_forwardings.items()):

            forward_thread.stop()
            ssh_client.close()

        self.active_forwardings.clear()

        # restart
        for name in running:

            local_port, remote_host, remote_port, url = self.services[name]

            try:

                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                ssh_client.connect(
                    hostname=host,
                    username=username,
                    password=password
                )

                forward_thread = ForwardServer(
                    local_port,
                    remote_host,
                    remote_port,
                    ssh_client
                )

                forward_thread.start()

                self.active_forwardings[name] = (
                    ssh_client,
                    forward_thread
                )

            except Exception as e:

                messagebox.showerror("SSH error", f"{name}\n{e}")

        self.refresh_tree()
        self.update_status()

        messagebox.showinfo("Info", "Active tunnels refreshed")

    # ---------------- BROWSER ----------------

    def open_browser(self):

        name = self.get_selected_service()

        if not name:
            return

        url = self.services[name][3]

        if url:
            webbrowser.open(url)

    # ---------------- STATUS ----------------

    def update_status(self):

        self.status_label.config(
            text=f"Status: {len(self.active_forwardings)} active tunnel(s)"
        )


if __name__ == "__main__":

    root = tk.Tk()

    app = PortForwardApp(root)

    root.mainloop()