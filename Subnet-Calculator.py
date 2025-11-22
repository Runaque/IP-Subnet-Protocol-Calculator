import tkinter as tk
from tkinter import messagebox, filedialog, ttk # Added ttk for themed widgets
import ipaddress
import sys
from collections import OrderedDict
import datetime 

# --- Helper Function for IPv4 Class Determination ---

def get_ip_class(ip_address_str):
    """Determines the historical IPv4 class (A, B, C, D, E) based on the first octet."""
    try:
        first_octet = int(ip_address_str.split('.')[0])
        
        if 1 <= first_octet <= 126:
            return "Class A"
        elif 128 <= first_octet <= 191:
            return "Class B"
        elif 192 <= first_octet <= 223:
            return "Class C"
        elif 224 <= first_octet <= 239:
            return "Class D (Multicast)"
        elif 240 <= first_octet <= 255:
            return "Class E (Reserved)"
        else:
            return "Special/Reserved" # e.g., 0.x.x.x or 127.x.x.x
            
    except:
        return "N/A"

# --- Core Calculation Logic ---

def calculate_subnet_details(ip_with_cidr):
    """
    Calculates and returns the detailed subnet information for both IPv4 and IPv6.
    
    Args:
        ip_with_cidr (str): An IP address followed by a CIDR mask (e.g., "192.168.1.50/26" or "2001:db8::1/64").
        
    Returns:
        OrderedDict: A dictionary containing subnet details, or {"Error": ...} if input is invalid.
    """
    try:
        # ipaddress.ip_network automatically detects IPv4 or IPv6
        network = ipaddress.ip_network(ip_with_cidr, strict=False)
        
        details = OrderedDict()
        
        details["Input IP/CIDR"] = ip_with_cidr
        details["IP Version"] = f"IPv{network.version}"
        
        # --- Common Details ---
        details["Network ID"] = str(network.network_address)
        
        if network.version == 4:
            # New field for the calculated class
            ip_class = get_ip_class(str(network.network_address))
            details["Historical Class"] = ip_class

        details["CIDR Prefix"] = f"/{network.prefixlen}"
        
        if network.version == 4:
            # --- IPv4 Specific Details ---
            
            total_hosts = network.num_addresses
            host_bits = 32 - network.prefixlen
            
            # Special handling for /31 (RFC 3021) and /32
            if network.prefixlen == 31:
                usable_hosts = 2 # Both addresses are usable for point-to-point links
                broadcast_address = str(network.network_address + 1)
                host_range = f"{network.network_address} - {broadcast_address} (RFC 3021 P2P)"
            elif network.prefixlen == 32:
                usable_hosts = 1 # Single host address, often used for loopback
                broadcast_address = str(network.network_address) # Same as network ID
                host_range = str(network.network_address)
            else:
                usable_hosts = total_hosts - 2
                broadcast_address = str(network.broadcast_address)
                try:
                    first_host = next(network.hosts())
                    last_host = network.broadcast_address - 1
                    host_range = f"{first_host} - {last_host}"
                except StopIteration:
                    host_range = "None"
            
            details["Subnet Mask"] = str(network.netmask)
            details["Host Bits (h)"] = host_bits
            details["Subnet Bits (s)"] = network.prefixlen % 8 if network.prefixlen > 24 else network.prefixlen
            details["Total IP Addresses"] = total_hosts
            
            # Display usable hosts contextually
            if network.prefixlen == 31:
                details["Usable Host Count"] = f"{usable_hosts} (RFC 3021 P2P)"
            elif network.prefixlen == 32:
                 details["Usable Host Count"] = f"{usable_hosts} (Single Address)"
            else:
                 details["Usable Host Count"] = usable_hosts
                 
            details["Broadcast Address"] = broadcast_address
            details["Usable Host Range"] = host_range

        elif network.version == 6:
            # --- IPv6 Specific Details ---
            
            # IPv6 networks typically use a /64 prefix for subnets.
            host_bits = 128 - network.prefixlen
            
            details["Subnet Mask Concept"] = "Not Applicable (N/A)"
            details["Host Bits"] = host_bits
            
            # Calculate host count expression (2^N)
            # Use string representation as the number is too large to display directly
            if host_bits >= 64:
                 details["Total IP Addresses"] = f"2^{host_bits} (Standard /64 Subnet)"
                 details["Usable Host Count"] = "Effectively infinite"
            else:
                 details["Total IP Addresses"] = f"2^{host_bits}"
                 details["Usable Host Count"] = "2^" + str(host_bits)
            
            details["Broadcast Address Concept"] = "Not Applicable (Uses Multicast)"
            details["Host Range Concept"] = "The entire address space after the prefix."
            
        return details
    
    except ValueError as e:
        # Return the error message to be displayed by the GUI
        return {"Error": f"Invalid input: {e}"}


# --- GUI Implementation ---

class SubnetCalculatorGUI:
    def __init__(self, master):
        """Initializes the main application window and components."""
        self.master = master
        master.title("IP Subnet & Protocol Calculator")
        master.geometry("500x620") # Adjusted size slightly for new field
        master.resizable(False, False)
        
        # Define the primary background color for the smooth look
        self.bg_color = '#f4f4f4'
        master.tk_setPalette(background=self.bg_color, foreground='#333333')
        
        # --- TTK Style setup for buttons ---
        self.style = ttk.Style()
        # Changed button font from bold to regular
        self.style.configure('TButton', font=('Arial', 11), padding=6)
        
        # State Storage
        self.ip_cidr_var = tk.StringVar(master, value="192.168.50.1/8") # Changed default value
        self.last_details = {} # Store the last successful calculation details
        
        # --- Main Frame Layout (Container) ---
        main_frame = tk.Frame(master, padx=15, pady=15, bg=self.bg_color, bd=0, relief=tk.FLAT)
        main_frame.pack(padx=0, pady=0, fill='both', expand=True) 

        # 1. Input Section
        # Changed font from bold to regular
        tk.Label(main_frame, text="Enter IP Address/CIDR:", font=('Arial', 11), bg=self.bg_color).pack(anchor='w', pady=(0, 5))
        
        self.ip_cidr_entry = tk.Entry(main_frame, textvariable=self.ip_cidr_var, width=50, font=('Consolas', 11), relief=tk.GROOVE)
        self.ip_cidr_entry.pack(fill='x', padx=5, pady=(0, 10))
        
        # 2. Button Frame for two buttons (Calculate and Save)
        button_frame = tk.Frame(main_frame, bg=self.bg_color)
        button_frame.pack(fill='x', padx=5, pady=(5, 15))
        
        # Calculate Button uses the regular TButton style
        self.calculate_button = ttk.Button(button_frame, 
                                           text="Calculate Subnet Details", 
                                           command=self.perform_calculation, 
                                           style='TButton') 
        self.calculate_button.pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 5))
        
        # Save Button uses the regular TButton style
        self.save_button = ttk.Button(button_frame, 
                                      text="Save to .txt", 
                                      command=self.save_results_to_file,
                                      state=tk.DISABLED,
                                      style='TButton') 
        self.save_button.pack(side=tk.RIGHT, fill='x', expand=True, padx=(5, 0))
        
        # 3. Results Section
        # Changed font from bold to regular
        tk.Label(main_frame, text="Subnet Details:", font=('Arial', 11), bg=self.bg_color).pack(anchor='w', pady=(0, 10))
        
        self.results_frame = tk.Frame(main_frame, bg='#f0f0f0', bd=1, relief=tk.SUNKEN)
        self.results_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 4. Signature Label
        tk.Label(main_frame, text="Made in Antwerp by Runaque", font=('Arial', 9), 
                 fg='SlateGray', bg=self.bg_color).pack(fill='x', pady=(5, 0))
        
        # Run initial calculation on startup
        self.perform_calculation()


    def clear_results(self):
        """Clears all widgets from the results frame."""
        for widget in self.results_frame.winfo_children():
            widget.destroy()

    def perform_calculation(self):
        """Retrieves input, calculates details, and dynamically updates the GUI."""
        ip_cidr = self.ip_cidr_var.get().strip()
        details = calculate_subnet_details(ip_cidr)
        
        self.clear_results()

        # Check for error
        if "Error" in details:
            messagebox.showerror("Calculation Error", details["Error"])
            self.last_details = {} # Clear state on error
            self.save_button.config(state=tk.DISABLED)
            return

        self.last_details = details # Store successful details
        self.save_button.config(state=tk.NORMAL) # Enable save button

        # Dynamically create and populate labels based on the returned details
        for i, (key, value) in enumerate(details.items()):
            
            # Key Label (fixed) - kept regular as before
            tk.Label(self.results_frame, text=f"{key}:", anchor='w', font=('Arial', 10), bg='#f0f0f0').grid(row=i, column=0, sticky='w', padx=10, pady=4)
            
            # Value Label (to be updated) - kept bold for emphasis on data
            if key == "Historical Class":
                 # Use light grey color for historical context
                 fg_color = 'grey50'
                 font_style = ('Consolas', 10) # Less emphasis
            elif "ID" in key or "Prefix" in key or "Mask" in key or "Version" in key:
                 fg_color = '#0056b3'
                 font_style = ('Consolas', 10, 'bold')
            elif "Broadcast" in key or "Range" in key:
                 fg_color = '#cc0000' # Red for boundary addresses
                 font_style = ('Consolas', 10, 'bold')
            else:
                 fg_color = '#333333'
                 font_style = ('Consolas', 10, 'bold')
                 
            value_label = tk.Label(self.results_frame, text=str(value), anchor='w', font=font_style, bg='#f0f0f0', fg=fg_color)
            value_label.grid(row=i, column=1, sticky='w', padx=10, pady=4)
            
        # Configure grid for results frame
        self.results_frame.grid_columnconfigure(1, weight=1)

    def save_results_to_file(self):
        """Opens a file dialog and saves the last calculated details to a text file."""
        if not self.last_details:
            messagebox.showwarning("Save Error", "No subnet calculation data available to save.")
            return

        # Build the content string
        content = "--- IP Subnet & Protocol Calculation ---\n"
        content += f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += "-" * 40 + "\n"
        
        # Find the maximum length of the keys for alignment
        max_key_len = max(len(key) for key in self.last_details.keys())
        
        for key, value in self.last_details.items():
            content += f"{key.ljust(max_key_len)} : {value}\n"
        
        # Open file dialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"subnet_report_{self.last_details.get('Network ID', 'default').replace('/', '_')}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Subnet Calculation Results"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Results successfully saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SubnetCalculatorGUI(root)
    root.mainloop()