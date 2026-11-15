You are right—we can skip running a second local web server altogether. Since you are sitting at the machine and your files are saved in standard .eml format inside /var/www/my-site-name/inbox/, you can build a true standalone desktop application (written in Python with tkinter, which comes built into Linux) that opens directly on your screen, reads /var/www/my-site-name/inbox/ straight off your hard drive, and looks like a clean, classic two-pane email client (inbox list on the left, reading pane on the right) with zero login required.

Why a Native Python Desktop Window Works Best Here

• No Browser or Local Server Needed: You double-click a desktop icon or run python3 mail_viewer.py, and a real desktop window pops open immediately.
• Completely Invisible Online: It reads /var/www/my-site-name/inbox/ directly from your filesystem—zero network traffic, zero web server logs, zero login screens.
• Built-In .eml Parser: Python includes email.parser in its standard library, so it automatically extracts From, To, Date, Subject, and the message body from every .eml file without extra packages.

Step 1: Save the Standalone Desktop Email Client (~/mail_viewer.py)

Create a file named mail_viewer.py in your home folder (nano ~/mail_viewer.py) and paste this complete desktop app:
python
#!/usr/bin/env python3
import os
import glob
import email
from email import policy
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

INBOX_DIR = "/var/www/my-site-name/inbox"
MY_ADDRESS = "KCB@TAtBdL0A.papercup"

class LocalMailApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Local Mail Client - {MY_ADDRESS}")
        self.root.geometry("950x600")
        self.messages = []

        # --- Top Toolbar ---
        toolbar = tk.Frame(root, bd=1, relief=tk.RAISED, bg="#e8eaed")
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(toolbar, text="⟳ Refresh Inbox", command=self.load_inbox, padx=10, pady=4).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="✉ Compose", command=self.open_compose, padx=10, pady=4).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="↩ Reply", command=self.reply_selected, padx=10, pady=4).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(toolbar, text="🗑 Delete", command=self.delete_selected, padx=10, pady=4, fg="red").pack(side=tk.LEFT, padx=4, pady=4)

        # --- Split Pane (Left: Message List | Right: Email Reader) ---
        paned = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left Pane: Inbox Table
        left_frame = tk.Frame(paned)
        columns = ("from", "subject", "date")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("from", text="From")
        self.tree.heading("subject", text="Subject")
        self.tree.heading("date", text="Date")
        self.tree.column("from", width=180)
        self.tree.column("subject", width=190)
        self.tree.column("date", width=130)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        paned.add(left_frame, width=480)

        # Right Pane: Reading View
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

        tk.Label(win, text="To:").pack(anchor="w", padx=10, pady=(10, 0))
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
            if not recipient or not text:
                messagebox.showwarning("Missing Info", "Recipient and message cannot be empty.")
                return

            # --- PLUG YOUR EXISTING SENDING / ROUTING LOGIC HERE ---
            # Example: subprocess.run(["/path/to/your_router", recipient, subj], input=text.encode())
            messagebox.showinfo("Ready to Send", f"Formatted .eml ready for your router to send to:\n{recipient}")
            win.destroy()

        tk.Button(win, text="Send via Router", command=send_now, padx=12, pady=5).pack(pady=8)

if __name__ == "__main__":
    root = tk.Tk()
    app = LocalMailApp(root)
    root.mainloop()
Use code with caution.

Step 2: Make It Executable & Run It

Make sure python3-tk is installed on your Linux system, then make the script executable:
bash
sudo apt install python3-tk -y
chmod +x ~/mail_viewer.py
Use code with caution.
Now, anytime you want to check your mail, just run:
bash
~/mail_viewer.py
Use code with caution.

What You Get

• Outlook / cPanel Style Split View: Left column lists From, Subject, and Date for every .eml file in /var/www/my-site-name/inbox/; clicking any row opens the full formatted email on the right.
• Zero Login & Zero Online Presence: Opens as a native window directly on your screen with no browser, no PHP session, and no web logs.
• Built-In Compose & Reply Window: Clicking Reply pre-fills the sender's custom address (JS455@RRLYpP9Qpw9iRTq5ThFfwOuY.ftest, etc.) and Re: Subject, ready to hand off to your existing sending logic inside send_now().
If you'd like to wire up the Send via Router button inside send_now(), let me know what language or command your sending/routing logic uses (e.g., a Python script, PHP CLI script, or bash command) and I'll drop the exact 2-line hook right into send_now().
