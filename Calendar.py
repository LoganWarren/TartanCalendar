import tkinter as tk
from tkinter import ttk, messagebox
from ttkthemes import ThemedTk
from tkcalendar import Calendar
import sqlite3
import datetime
import requests  # Import the requests library for making API requests
import ics
import requests
import re
# Replace with your Canvas API URL and access token
CANVAS_API_URL = 'https://canvas.pitt.edu'
CANVAS_ACCESS_TOKEN = '13997~RlJMaoAlVWtHlWbt4EWqu4xAYy6nd6EVWhT6pAH03VjN1qrX1ex88dpcbTt7MHzH'

def init_db():
    with sqlite3.connect('calendar_app.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT
            )
        ''')
        conn.commit()

class CalendarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Integrated Calendar App")
        self.root.geometry("1200x800")  # Adjust the size of the main window
        self.root.config(bg="#f0f0f0")

        style = ttk.Style(self.root)
        style.configure("Treeview", background="#EEEEEE", foreground="blue", rowheight=25, fieldbackground="#EEEEEE")
        style.map("Treeview", background=[('selected', '#4a6984')])

        self.initialize_ui()
        self.initialize_view_mode_selector()
        self.highlight_event_days()
        
        # Initialize Canvas assignments
        self.initialize_canvas_assignments()  # Call this method to fetch and display Canvas assignments

    def initialize_ui(self):
        self.calendar_frame = ttk.Frame(self.root, padding="10")
        self.calendar_frame.pack(side="left", fill="both", expand=True)

        # Make the calendar bigger by increasing height and width
        self.calendar = Calendar(self.calendar_frame, selectmode='day', year=2024, month=2, day=3, height=18, width=36)
        self.calendar.pack(fill="both", expand=True)
        self.calendar.bind("<<CalendarSelected>>", self.on_date_select)

        self.details_frame = ttk.Frame(self.root, padding="10")
        self.details_frame.pack(side="right", fill="both", expand=True)

        self.add_event_button = ttk.Button(self.details_frame, text="Add Event", command=self.open_add_event_form)
        self.add_event_button.pack(pady=10)

        self.event_tree = ttk.Treeview(self.details_frame, columns=("ID", "Title", "Description"), show="headings", selectmode="extended")
        self.event_tree.heading("ID", text="ID")
        self.event_tree.heading("Title", text="Title")
        self.event_tree.heading("Description", text="Description")
        self.event_tree.column("ID", width=0, stretch=tk.NO)  # Hide the ID column
        self.event_tree.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.delete_button = ttk.Button(self.details_frame, text="Delete Selected", command=self.delete_selected_events)
        self.delete_button.pack(pady=10)

    def open_add_event_form(self):
        self.show_add_event_form(self.calendar.get_date())

    def initialize_view_mode_selector(self):
        # Placeholder for view mode selector
        pass

    def on_date_select(self, event):
        self.show_events_for_date(self.calendar.get_date())

    def show_events_for_date(self, date):
        for item in self.event_tree.get_children():
            self.event_tree.delete(item)
        
        with sqlite3.connect('calendar_app.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id, title, description FROM events WHERE date=?", (date,))
            for event in c.fetchall():
                self.event_tree.insert("", tk.END, values=(event[0], event[1], event[2]))

    def delete_selected_events(self):
        selected_items = self.event_tree.selection()
        if not selected_items:
            messagebox.showinfo("Information", "No event selected.")
            return
        
        if messagebox.askyesno("Confirm", "Delete selected events?"):
            with sqlite3.connect('calendar_app.db') as conn:
                c = conn.cursor()
                for item in selected_items:
                    event_id = self.event_tree.item(item, "values")[0]  # ID is the first value
                    c.execute("DELETE FROM events WHERE id=?", (event_id,))
                conn.commit()

            self.show_events_for_date(self.calendar.get_date())
            self.highlight_event_days()

    def show_add_event_form(self, date):
        add_event_frame = tk.Toplevel(self.root)
        add_event_frame.title("Add Event")
        add_event_frame.geometry("300x200")

        tk.Label(add_event_frame, text="Title").pack()
        event_title_entry = tk.Entry(add_event_frame)
        event_title_entry.pack()

        tk.Label(add_event_frame, text="Description").pack()
        event_description_text = tk.Text(add_event_frame, height=4, width=20)
        event_description_text.pack()

        add_button = tk.Button(add_event_frame, text="Add Event",
                               command=lambda: self.add_event(date, event_title_entry.get(), event_description_text.get("1.0", tk.END), add_event_frame))
        add_button.pack()

    def add_event(self, date, title, description, frame):
        if not title or not description.strip():
            messagebox.showerror("Error", "Title and description cannot be empty.")
            return

        with sqlite3.connect('calendar_app.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO events (title, description, date) VALUES (?, ?, ?)', (title, description, date))
            conn.commit()

        frame.destroy()
        self.show_events_for_date(date)
        self.highlight_event_days()

    def highlight_event_days(self):
        self.calendar.calevent_remove('all')
        now = datetime.datetime.now()
        year, month = now.year, now.month

        with sqlite3.connect('calendar_app.db') as conn:
            c = conn.cursor()
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{datetime.date(year, month, 1).day + 31}"
            c.execute("SELECT DISTINCT date FROM events WHERE date BETWEEN ? AND ?", (start_date, end_date))
            for row in c.fetchall():
                event_date = datetime.datetime.strptime(row[0], '%Y-%m-%d').date()
                if event_date.year == year and event_date.month == month:
                    self.calendar.calevent_create(event_date, 'reminder', 'reminder')

        self.calendar.tag_config('reminder', background='lightblue', foreground='blue')  # Change the foreground color for selected dates
    def initialize_canvas_assignments(self):
        # Fetch and add Canvas assignments to the calendar
        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=30)  # Adjust the end date as needed

        # Fetch assignments from the ICS feed
        ics_feed_url = 'https://canvas.pitt.edu/feeds/calendars/user_ZxzGlAytJfbiJim4fXGL0tKEr0WuHox7PTGbYdYn.ics'
        assignments = self.get_canvas_assignments_from_ics_feed(ics_feed_url)

        for due_date, assignment_name in assignments:
            self.calendar.calevent_create(due_date, 'canvas_assignment', assignment_name)

        self.calendar.tag_config('canvas_assignment', background='yellow', foreground='black')

    def get_canvas_assignments_from_ics_feed(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()

            ics_data = response.text
            assignments = []

            # Use regular expressions to extract event details
            event_pattern = r'BEGIN:VEVENT(.*?)END:VEVENT'
            events = re.findall(event_pattern, ics_data, re.DOTALL)

            for event_entry in events:
                # Extract summary (assignment name) and start date
                summary_match = re.search(r'SUMMARY:(.*?)\n', event_entry)
                if summary_match:
                    assignment_name = summary_match.group(1).strip()
                else:
                    continue  # Skip events without a summary

                dtstart_match = re.search(r'DTSTART:(.*?)\n', event_entry)
                if dtstart_match:
                    start_date = datetime.datetime.strptime(dtstart_match.group(1).strip(), '%Y%m%dT%H%M%SZ').date()
                else:
                    continue  # Skip events without a start date

                # Extract end date if available
                dtend_match = re.search(r'DTEND:(.*?)\n', event_entry)
                if dtend_match:
                    end_date = datetime.datetime.strptime(dtend_match.group(1).strip(), '%Y%m%dT%H%M%SZ').date()
                else:
                    end_date = None

                assignments.append((start_date, assignment_name))  # Adjust the tuple here

            return assignments
        except Exception as e:
            print(f'Error fetching Canvas assignments from ICS feed: {str(e)}')
            return []






if __name__ == "__main__":
    init_db()
    root = ThemedTk()
    app = CalendarApp(root)
    root.mainloop()

