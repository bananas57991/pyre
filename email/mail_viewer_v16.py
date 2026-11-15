#!/usr/bin/env python3
import os
import glob
import email
import urllib.request
import urllib.parse
from email import policy
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

INBOX_DIR = "/var/www/ftest/inbox"
MY_ADDRESS = "KCB@TAtBdL0A.papercup"


class ForceHttpRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if newurl.startswith("https://"):
            newurl = "http://" + newurl[8:]
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# =========================================================================
# HARDENED TRANSPORT CONTROLLER
# Forces the underlying socket execution engine to drop persistent connections
# completely, eliminating HTTP Keep-Alive hanging timeout bugs.
# =========================================================================
class StatelessHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        req.add_unredirected_header('Connection', 'close')
        return super().http_open(req)


class LocalMailApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Local Mail - {MY_ADDRESS}")
        self.root.geometry("950x600")
        self.messages = []

        # Top Toolbar
        toolbar = tk.Frame(root, bd=1, relief=tk.RAISED, bg="#e8eaed")
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(toolbar, text="⟳ Refresh", command=self.load_inbox, padx=10, pady=4).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="✉ Compose", command=self.open_compose, padx=10, pady=4).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="↩ Reply", command=self.reply_selected, padx=10, pady=4).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="🗑 Delete", command=self.delete_selected, padx=10, pady=4, fg="red").pack(side=tk.LEFT, padx=4, pady=4)

        # Split View (Left: Inbox List | Right: Reading Pane)
        paned = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(paned)
        columns = ("from", "subject", "date")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("from", text="From")
        self.tree.heading("subject", text="Subject")
        self.tree.heading("date", text="Date")
        self.tree.column("from", width=190)
        self.tree.column("subject", width=180)
        self.tree.column("date", width=130)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        paned.add(left_frame, width=500)

        right_frame = tk.Frame(paned, bg="white")
        self.header_label = tk.Label(
            right_frame, text="Select an email to read", justify=tk.LEFT,
            anchor="w", bg="#f4f6f8", font=("Sans", 10), padx=12, pady=10, relief=tk.GROOVE
        )
        self.header_label.pack(fill=tk.X)

        self.body_text = scrolledtext.ScrolledText(
            right_frame, wrap=tk.WORD, font=("Sans", 11), padx=12, pady=12, state=tk.DISABLED
        )
        self.body_text.pack(fill=tk.BOTH, expand=True)
        paned.add(right_frame)

        self.load_inbox()

    def load_inbox(self):
        self.tree.delete(*self.tree.get_children())
        self.messages.clear()

        if not os.path.isdir(INBOX_DIR):
            self.header_label.config(text=f"Folder not found: {INBOX_DIR}")
            return

        files = sorted(glob.glob(os.path.join(INBOX_DIR, "*.eml")), reverse=True)
        for idx, filepath in enumerate(files):
            try:
                with open(filepath, "rb") as f:
                    msg = email.message_from_binary_file(f, policy=policy.default)
                sender = msg.get("From", "Unknown")
                subject = msg.get("Subject", "(No Subject)")
                date = msg.get("Date", "")
                body = msg.get_body(preferencelist=("plain", "html"))
                content = body.get_content() if body else msg.get_payload()

                self.messages.append({
                    "path": filepath,
                    "from": sender,
                    "to": msg.get("To", MY_ADDRESS),
                    "subject": subject,
                    "date": date,
                    "body": content
                })
                self.tree.insert("", tk.END, iid=str(idx), values=(sender, subject, date))
            except Exception as e:
                print(f"Error reading {filepath}: {e}")

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        m = self.messages[int(selected[0])]
        header_info = (
            f"From:    {m['from']}\n"
            f"To:      {m['to']}\n"
            f"Date:    {m['date']}\n"
            f"Subject: {m['subject']}"
        )
        self.header_label.config(text=header_info)
        self.body_text.config(state=tk.NORMAL)
        self.body_text.delete("1.0", tk.END)
        self.body_text.insert(tk.END, m["body"])
        self.body_text.config(state=tk.DISABLED)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        m = self.messages[int(selected[0])]
        if messagebox.askyesno("Delete Email", f"Permanently delete '{m['subject']}'?"):
            os.remove(m["path"])
            self.header_label.config(text="Select an email to read")
            self.body_text.config(state=tk.NORMAL)
            self.body_text.delete("1.0", tk.END)
            self.body_text.config(state=tk.DISABLED)
            self.load_inbox()

    def reply_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Reply", "Select an email first to reply.")
            return
        m = self.messages[int(selected[0])]
        subj = m["subject"] if m["subject"].lower().startswith("re:") else f"Re: {m['subject']}"
        self.open_compose(to_addr=m["from"], subject=subj)

    def open_compose(self, to_addr="", subject=""):
        win = tk.Toplevel(self.root)
        win.title("Compose Message")
        win.geometry("550x420")

        tk.Label(win, text="To (user@host.*):").pack(anchor="w", padx=10, pady=(10, 0))
        to_entry = tk.Entry(win)
        to_entry.insert(0, to_addr)
        to_entry.pack(fill=tk.X, padx=10)

        tk.Label(win, text="Subject:").pack(anchor="w", padx=10, pady=(8, 0))
        subj_entry = tk.Entry(win)
        subj_entry.insert(0, subject)
        subj_entry.pack(fill=tk.X, padx=10)

        tk.Label(win, text="Message:").pack(anchor="w", padx=10, pady=(8, 0))
        msg_box = scrolledtext.ScrolledText(win, wrap=tk.WORD, height=12)
        msg_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def send_now():
            recipient = to_entry.get().strip()
            subj = subj_entry.get().strip()
            text = msg_box.get("1.0", tk.END).strip()

            if "@" not in recipient or not text:
                messagebox.showwarning("Invalid Input", "Enter a valid user@host address and message.")
                return

            user_part, host_part = recipient.rsplit("@", 1)
            host_part = host_part.strip()
            target_url = f"http://FALT/{host_part}/receive.php"

            eml = EmailMessage()
            eml["From"] = MY_ADDRESS
            eml["To"] = recipient
            eml["Date"] = formatdate(localtime=True)
            eml["Subject"] = subj
            
            my_user, my_domain = MY_ADDRESS.rsplit("@", 1)
            my_domain = my_domain.strip()
            eml["Message-ID"] = make_msgid(domain=my_domain)
            eml.set_content(text)

            form_payload = urllib.parse.urlencode({"email_data": eml.as_string()}).encode("utf-8")

            try:
                headers = {
                    "Host": host_part,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Content-Length": str(len(form_payload)),
                    "User-Agent": "FALT Mail Client v4.0"
                }

                req = urllib.request.Request(
                    target_url,
                    data=form_payload,
                    headers=headers,
                    method="POST"
                )
                
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}),
                    StatelessHTTPHandler(),
                    ForceHttpRedirectHandler()
                )
                
                with opener.open(req, timeout=15) as resp:
                    if resp.status in (200, 201):
                        if win.winfo_exists():
                            messagebox.showinfo("Sent", f"Delivered via {target_url}")
                            win.destroy()
                    else:
                        if win.winfo_exists():
                            messagebox.showerror("Error", f"Remote server returned HTTP status code: {resp.status}")
            except urllib.error.HTTPError as http_err:
                print(f"\n[!] SERVER RETURNED ERROR ENCOUNTERED: {http_err.code} {http_err.reason}\n")
                if win.winfo_exists():
                    messagebox.showerror("Server Code Error", f"Server rejected request with code: {http_err.code}")
            except Exception as e:
                print(f"\n[!] GENERAL NETWORK ERROR: {e}\n")
                if win.winfo_exists():
                    messagebox.showerror("FALT Connection Failed", f"Could not complete transmission sequence: {e}")

        tk.Button(win, text="🚀 Send Email", command=send_now, bg="#1a73e8", fg="white", padx=15, pady=5).pack(anchor="e", padx=10, pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = LocalMailApp(root)
    root.mainloop()
