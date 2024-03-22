import tkinter as tk
from tkinter import Text
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk

import sys

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

def start_button_clicked():
    # Get the contents of the text fields
    field_contents = [entry.get() for entry in entries]
    
    # Create a message for the pop-up
    message = "Contents of the fields:\n\n"
    resume = ""
    for i, content in enumerate(field_contents, start=1):
        resume += f", {content}"
        message += f"Field {i}: {content}\n"
    message += "\nDo you want to continue with these parameters?"

    # Display the pop-up message
    response = messagebox.askyesno("Confirmation", message)
    
    # If user confirms, execute the function; otherwise, do nothing
    if response:
        # Add your function execution here
        print("Starting collection with the given parameters")
    else:
        pass


# Create the main window
root = tk.Tk()
root.title("Collection Manager")
root.geometry("900x500")  # Set initial size


# Divide the viewport into two frames
left_frame = tk.Frame(root, width=200)  # Adjust width as needed
left_frame.pack(side=tk.LEFT, fill=tk.Y)

right_frame = tk.Frame(root)
right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Input fields on the left side
input_labels = ['Field 1', 'Field 2', 'Field 3', 'Field 4', 'Field 5']
entries = []
for label_text in input_labels:
    label = tk.Label(left_frame, text=label_text)
    label.pack()
    entry = tk.Entry(left_frame)
    entry.pack()
    entries.append(entry)

# 'Start' button below input fields
start_button = tk.Button(left_frame, text="Start", command=start_button_clicked)
start_button.pack()

# Create a Treeview widget for the table
columns = ('subreddit', 'title', 'content', 'upvotes', 'upvote_ratio', 'n_comments')

# Create a Frame to contain the table and console
table_console_frame = tk.Frame(right_frame)
table_console_frame.pack(fill=tk.BOTH, expand=True)

# Create a Text widget for the console
output_text = tk.Text(table_console_frame, wrap=tk.WORD)
output_text.pack(fill=tk.BOTH, expand=True)
output_text.config(height=7)
# Redirect stdout to the Text widget
sys.stdout = StdoutRedirector(output_text)

# Create a separator between the console and the table
separator = ttk.Separator(table_console_frame, orient='horizontal')
separator.pack(fill='x', padx=5, pady=5)

# Create a Treeview widget for the table
tree = ttk.Treeview(table_console_frame, columns=columns, show='headings')

# Define column headings
for col in columns:
    tree.heading(col, text=col.title())

# Insert dummy data into the table
dummy_data = [
    ('r/python', 'Python is awesome', 'Python is a versatile programming language', 1000, 0.95, 50),
    ('r/machinelearning', 'Introduction to ML', 'Learn the basics of machine learning', 800, 0.90, 30),
    ('r/datascience', 'Data Science career tips', 'How to kickstart your career in Data Science', 1200, 0.92, 60)
]

for data in dummy_data:
    tree.insert('', 'end', values=data)

# Adjust the height of the table to take up 2/3 of the vertical space
tree_height = int(root.winfo_reqheight() * 3 / 4)
tree.config(height=tree_height)

# Pack the table
tree.pack(fill=tk.BOTH, expand=True)

# Calculate the maximum width of data in each column
max_widths = [max([len(str(item)) for item in column]) for column in zip(*dummy_data)]

# Set the width of each column in the Treeview widget based on the maximum width of data in that column
for i, width in enumerate(max_widths):
    tree.column(columns[i], width=width + 20)  # Add a little padding to the column width

# Calculate the total width needed for all columns
total_width = sum(max_widths) + len(columns) * 20  # Add padding for each column
print(total_width)

# Update the window size to fit the content
if total_width > 900:
    root.geometry(f"{total_width}x500")


# Configure the style for dark theme
style = ttk.Style()
style.theme_use('clam')  # Choose the dark theme (you can use 'clam', 'alt', or 'default')
style.configure('Treeview', background='#333', foreground='white', fieldbackground='#333')
style.configure('Text', background='#333', foreground='white', fieldbackground='#333')
style.map('Treeview', background=[('selected', '#444')])
style.map('Text', background=[('selected', '#444')])

# Run the Tkinter event loop
root.mainloop()
