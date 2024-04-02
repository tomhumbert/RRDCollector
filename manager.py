import tkinter as tk
from tkinter import Text, StringVar, OptionMenu
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
import pandas as pd

import sys
import threading
import asyncio
import queue
import time
from scraper import RScraper as scrp



class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.config(state=tk.NORMAL)  # Enable the widget
        self.text_widget.insert(tk.END, message)
        self.text_widget.config(state=tk.DISABLED)  # Disable the widget
        self.text_widget.see(tk.END)  # Scroll to the end of the text

    def flush(self):
        pass  # This method is required but we don't need to do anything

def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()

class GUI:
    def __init__(self):
        self.entries = {}
        self.clicked = None

    def start_button_clicked(self):
        # Create a message for the pop-up
        message = "Contents of the fields:\n\n"
        resume = ""
        # Get the contents of the text fields
        mode = self.clicked.get()

        for key, content in self.entries.items():
            resume += f", {content.get()}"
            message += f"{key}: {content.get()}\n"
        message += "\nDo you want to continue with these parameters?"

        # Display the pop-up message
        response = messagebox.askyesno("Confirmation", message)
        
        # If user confirms, execute the function; otherwise, do nothing
        if response:
            # Add your function execution here
            print(f"Starting collection in {mode} mode with the given parameters")
            loop = get_or_create_eventloop()
            loop.create_task(self.collect_subs(self.entries['Title'].get(),self.entries['Subreddits'].get(), self.entries['Keywords'].get(), mod=mode))
        else:
            pass

    async def collect_authors(self, title):
        authors = pd.read_csv("data/seed_authors.csv", title)
        authorlist = list(authors['authors'])

        # Scraper init
        scraper = RScraper("reddit-credentials.txt")

        data = scraper.get_authors_posts(authorlist)
        print(data.head())
        print(scraper.summary())
        input("Save this collection? Else, abort.")
        scraper.safe_all_to_csv()

    async def collect_subs(self, title, subreddits, kwords, mod='search'):
        scraper = scrp("reddit-credentials.txt", title)
        data = await scraper.collect_posts(subreddits, keywords=kwords, mode=mod)

    def gui_main(self, data=None):
        #============ LEFT PANEL ==============

        # Create the main window
        root = tk.Tk()
        root.title("Collection Manager")
        root.geometry("900x500")  # Set initial size


        # Divide the viewport into two frames
        left_frame = tk.Frame(root, width=250)  # Adjust width as needed
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=3,pady=3)

        right_frame = tk.Frame(root)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3,pady=3)

        # Input fields on the left side
        input_labels = ['Title', 'Subreddits', 'Keywords']
        self.entries =  {'Title': '', 
                    'Subreddits': '', 
                    'Keywords': ''
                    }
        for label_text in input_labels:
            label = tk.Label(left_frame, text=label_text)
            label.pack()
            entry = tk.Entry(left_frame)
            entry.pack()
            self.entries[label_text] = entry

        # Change the label text 
        #label.config(text = clicked.get()) 
        # Dropdown menu options 
        options = [ 
            "top",
            "new",
            "hot"
        ] 
        # datatype of menu text 
        self.clicked = StringVar() 
        # initial menu text 
        self.clicked.set("top") 
        
        # Create Dropdown menu 
        label = tk.Label(left_frame, text="Mode")
        drop = OptionMenu(left_frame , self.clicked , *options) 
        drop.pack() 
        

        # 'Start' button below input fields
        start_button = tk.Button(left_frame, text="Start", command=self.start_button_clicked)
        start_button.pack()

        #============ RIGHT PANEL ==============

        # Create a Frame to contain the table and console
        table_console_frame = tk.Frame(right_frame)
        table_console_frame.pack(fill=tk.BOTH, expand=True)

        #------------ CONSOLE -----------------

        output_text = tk.Text(table_console_frame, wrap=tk.WORD)
        output_text.pack(fill=tk.BOTH, expand=True)
        output_text.config(height=7)
        # Redirect stdout to the Text widget
        sys.stdout = StdoutRedirector(output_text)

        #------------ SEPERATOR -----------------

        separator = ttk.Separator(table_console_frame, orient='horizontal')
        separator.pack(fill='x', padx=5, pady=5)

        #------------ DATA TABLE -----------------

        # GET COL NAMES
        if data == None:
            columns = ('subreddit', 'title', 'content', 'upvotes', 'upvote_ratio', 'n_comments')
            # Insert dummy data into the table
            rows = [
                ('r/python', 'Python is awesome', 'Python is a versatile programming language', 1000, 0.95, 50),
                ('r/machinelearning', 'Introduction to ML', 'Learn the basics of machine learning', 800, 0.90, 30),
                ('r/datascience', 'Data Science career tips', 'How to kickstart your career in Data Science', 1200, 0.92, 60)
            ]
        else:
            columns = data.columns
            rows = data

        tree = ttk.Treeview(table_console_frame, columns=columns, show='headings')
        tree_height = int(root.winfo_reqheight() * 3 / 4)
        tree.config(height=tree_height)

        # Define column headings
        for col in columns:
            tree.heading(col, text=col.title())
        for data in rows:
            tree.insert('', 'end', values=data)

        # Adjust the height of the table to take up 2/3 of the vertical space
        tree_height = int(root.winfo_reqheight() * 3 / 4)
        tree.config(height=tree_height)

        # Pack the table
        tree.pack(fill=tk.BOTH, expand=True)

        # Calculate the maximum width of data in each column
        max_widths = [max([len(str(item)) for item in column]) for column in zip(*rows)]

        # Set the width of each column in the Treeview widget based on the maximum width of data in that column
        for i, width in enumerate(max_widths):
            tree.column(columns[i], width=width + 20)  # Add a little padding to the column width

        # Calculate the total width needed for all columns
        total_width = sum(max_widths) + len(columns) * 20  # Add padding for each column

        # Update the window size to fit the content
        if total_width > 900:
            root.geometry(f"{total_width}x800")

        #------------ Style -----------------
        # Configure the style for dark theme
        style = ttk.Style()
        style.theme_use('clam')  # Choose the dark theme (you can use 'clam', 'alt', or 'default')
        style.configure('Treeview', background='#333', foreground='white', fieldbackground='#333')
        style.configure('Text', background='#333', foreground='white', fieldbackground='#333')
        style.map('Treeview', background=[('selected', '#444')])
        style.map('Text', background=[('selected', '#444')])

        # Run the Tkinter event loop
        root.mainloop()

if __name__ == "__main__":
    gui = GUI()

    # Start the GUI in a separate thread
    gui_thread = threading.Thread(target=gui.gui_main)
    gui_thread.start()