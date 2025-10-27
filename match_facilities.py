import sqlite3
from difflib import SequenceMatcher

def load_prison_list():
    with open('prisons.txt', 'r') as f:
        content = f.read()
    
    prisons = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('List of') and not line.startswith('Department') and line != '':
            # Clean up the line
            prison = line.split('(')[0].strip()  # Remove capacity info
            prison = prison.split(',')[0].strip()  # Remove location info
            if prison and len(prison) > 5:  # Filter out short entries
                prisons.append(prison)
    
    return prisons

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def match_facilities():
    prisons = load_prison_list()
    
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT facility_name FROM jobs WHERE facility_name IS NOT NULL")
    aramark_facilities = [row[0] for row in cursor.fetchall()]
    
    matches = []
    
    for aramark_facility in aramark_facilities:
        best_match = None
        best_score = 0
        
        for prison in prisons:
            score = similarity(aramark_facility, prison)
            if score > best_score and score > 0.6:  # 60% similarity threshold
                best_score = score
                best_match = prison
        
        matches.append({
            'aramark': aramark_facility,
            'matched_prison': best_match,
            'score': best_score
        })
    
    # Display results
    print("=== FACILITY MATCHING RESULTS ===\n")
    
    matched_count = 0
    for match in matches:
        if match['matched_prison']:
            print(f"✓ {match['aramark']}")
            print(f"  → {match['matched_prison']} ({match['score']:.2f})")
            matched_count += 1
        else:
            print(f"✗ {match['aramark']}")
            print(f"  → No match found")
        print()
    
    print(f"Matched: {matched_count}/{len(aramark_facilities)} facilities")
    
    conn.close()

if __name__ == "__main__":
    match_facilities()