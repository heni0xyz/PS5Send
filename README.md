# <img width="48" height="48" alt="PS5Send" src="https://github.com/user-attachments/assets/405004c5-2347-4214-8c24-bd81deb76ac9" /> PS5Send

PS5Send is an open-source python gui payload sender made for injecting PS5 payloads on Windows and macOS.
<img width="256" height="345" alt="Screenshot of PS5Send on macOS" src="https://github.com/user-attachments/assets/49e3fefd-afd4-4a75-a274-f5e715af3d9a" /> <img width="256" height="345" alt="Screenshot of PS5Send on macOS" src="https://github.com/user-attachments/assets/423974f8-1a8f-4be5-a001-5b163a4e62b2" /> <img width="475" height="356" alt="NanoDNS on PS5" src="https://github.com/user-attachments/assets/3e3ea89b-bbd7-411c-9c3c-bc0fd388f6fa" />

# Usage
Place `.elf`, `.jar`, `.js`, `.lua` or other supported files in the same folder as the executable or select them via the combobox. They should show up in the **Payloads** list.  
Sending a payload sends the file to the entered IP and uses an auto-assigned port based on your file:
* `.elf` - 9021
* `.jar` - 9025
* `.js` - 50000
* `.lua` - 9026

# .aelf (Automated Executable and Linkable Format)
This is essentially an autoloader for your `.elf` files.  
`:ms` is a break between sending your next payload.  

**Example usage:**
```text
hello_world.elf
:2000
hello_world.elf
:4000
hello_world.elf
