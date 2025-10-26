import re

def clean_prison_list():
    with open('prisons.txt', 'r') as f:
        content = f.read()
    
    clean_prisons = []
    current_state = ""
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Extract state from headers
        if line.startswith('List of ') and 'state prisons' in line:
            current_state = line.replace('List of ', '').replace(' state prisons', '').title()
            continue
        elif 'Department of Corrections' in line or 'Division of' in line:
            current_state = line.split()[0]
            continue
            
        # Skip department headers and other non-facility lines
        if any(skip in line for skip in ['Department', 'Division', 'Criminal Injuries', 'Emergency Number', 'Office of']):
            continue
            
        # Clean facility names
        if len(line) > 5 and not line.startswith('List'):
            # Remove capacity, dates, operators, and status info
            clean_name = re.sub(r'\s*\([^)]*\)', '', line)  # Remove parentheses content
            clean_name = re.sub(r'\s*,\s*[A-Za-z\s]+$', '', clean_name)  # Remove trailing location
            clean_name = re.sub(r'\s*–\s*', ' - ', clean_name)  # Standardize dashes
            clean_name = clean_name.strip()
            
            # Skip if too short or contains unwanted text
            if len(clean_name) > 5 and not any(skip in clean_name.lower() for skip in ['operated by', 'formerly known', 'including:']):
                clean_prisons.append({
                    'state': current_state,
                    'facility': clean_name
                })
    
    # Write clean list
    with open('clean_prisons.txt', 'w') as f:
        current_state = ""
        for prison in clean_prisons:
            if prison['state'] != current_state:
                f.write(f"\n{prison['state']}:\n")
                current_state = prison['state']
            f.write(f"{prison['facility']}\n")
    
    print(f"Cleaned {len(clean_prisons)} facilities")
    return clean_prisons

if __name__ == "__main__":
    clean_prison_list()