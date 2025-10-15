#!/usr/bin/env python3
"""
Flight Price Tracker - Extracts flight price data from Skyscanner emails and plots trends
"""

import mailbox
import re
import csv
from datetime import datetime
from pathlib import Path


def normalize_italian_date(date_str):
    """Convert Italian date format to English format for consistency"""
    # Mapping of Italian day/month names to English
    italian_to_english = {
        # Days
        'lun': 'Mon',
        'mar': 'Tue',
        'mer': 'Wed',
        'gio': 'Thu',
        'ven': 'Fri',
        'sab': 'Sat',
        'dom': 'Sun',
        # Months
        'gen': 'Jan',
        'feb': 'Feb',
        'mar': 'Mar',
        'apr': 'Apr',
        'mag': 'May',
        'giu': 'Jun',
        'lug': 'Jul',
        'ago': 'Aug',
        'set': 'Sep',
        'ott': 'Oct',
        'nov': 'Nov',
        'dic': 'Dec'
    }
    
    # If it's already in English format (contains comma), return as is
    if ',' in date_str:
        return date_str
    
    # Convert Italian format: "gio 23 ott" -> "Thu, 23 Oct"
    normalized = date_str
    for italian, english in italian_to_english.items():
        normalized = re.sub(r'\b' + italian + r'\b', english, normalized, flags=re.IGNORECASE)
    
    # Add comma after day if not present
    # Pattern: "Thu 23 Oct" -> "Thu, 23 Oct"
    normalized = re.sub(r'^(\w{3})\s+(\d)', r'\1, \2', normalized)
    
    return normalized


def extract_text_from_email(email_message):
    """Extract plain text content from email message"""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    return part.get_payload(decode=True).decode('latin-1', errors='ignore')
    else:
        try:
            return email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            return email_message.get_payload(decode=True).decode('latin-1', errors='ignore')
    return ""


def detect_email_type(text):
    """Detect the type of Skyscanner email"""
    # Check for Italian
    if "Il prezzo dei tuoi voli" in text or "Da Zurigo a Lisbona" in text:
        return "italian_single"
    # Check for English with multiple flights
    elif "Price updates for 2 saved flights" in text:
        return "english_double"
    # Check for English single
    elif "Zurich to Lisbon" in text and "Your" in text and "flights have" in text:
        return "english_single"
    return None


def extract_date_from_email(email_message, text):
    """Extract the email date"""
    # Try to get from email headers
    date_str = email_message.get('Date')
    if date_str:
        try:
            # Parse various date formats
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%a, %d %b %Y")
        except:
            pass
    
    # Try to extract from text
    patterns = [
        r'(\d{1,2}\s+\w+\s+\d{4})',
        r'(\w+,\s+\d{1,2}\s+\w+\s+\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:500])
        if match:
            return match.group(1)
    
    return ""


def clean_price(price_str):
    """Clean and extract numeric price value"""
    # Remove currency symbols and convert to number
    cleaned = re.sub(r'[^\d,.]', '', price_str)
    cleaned = cleaned.replace(',', '.')
    try:
        return cleaned
    except:
        return price_str


def extract_italian_single_flight(text, email_date):
    """Extract data from Italian email with one roundtrip"""
    lines = text.split('\n')
    
    data = {
        'date': email_date,
        'direction1': '',
        'date1': '',
        'time1': '',
        'direction2': '',
        'date2': '',
        'time2': '',
        'price': '',
        'label': ''
    }
    
    # Search for the key information in the text
    # Date pattern: "gio 23 ott"
    date_pattern = r'(\w+\s+\d{1,2}\s+\w+)'
    # Time pattern: "10:40"
    time_pattern = r'(\d{1,2}:\d{2})'
    
    # Find dates (usually appear in order)
    dates = []
    for i, line in enumerate(lines):
        if re.search(date_pattern, line) and 'ott' in line.lower():
            match = re.search(date_pattern, line)
            if match:
                dates.append((i, match.group(1)))
    
    # Find times and airports together - they appear close to each other
    times = []
    airports = []
    
    for i, line in enumerate(lines):
        # Look for time pattern
        time_match = re.search(r'^(\d{1,2}:\d{2})\s*-\s*$', line.strip())
        if time_match:
            times.append((i, time_match.group(1)))
            
            # Airport codes should be 2-3 lines after the time
            for j in range(i+1, min(i+5, len(lines))):
                airport_match = re.search(r'^([A-Z]{3})\s*-\s*$', lines[j].strip())
                if airport_match:
                    # Next line should have the second airport
                    if j+1 < len(lines):
                        next_airport = re.search(r'^([A-Z]{3})', lines[j+1].strip())
                        if next_airport:
                            airports.append((i, f"{airport_match.group(1)}-{next_airport.group(1)}"))
                            break
    
    # Find price (look for the final price)
    price_found = False
    for i, line in enumerate(lines):
        if 'aumentato' in line.lower() or 'diminuito' in line.lower() or 'sceso' in line.lower():
            # Look in nearby lines for the price
            for j in range(max(0, i-5), min(len(lines), i+5)):
                price_match = re.search(r'€\s*(\d+)', lines[j])
                if price_match and not price_found:
                    data['price'] = price_match.group(1)
                    price_found = True
                    break
    
    # Assign data based on order
    if len(dates) >= 2:
        data['date1'] = normalize_italian_date(dates[0][1])
        data['date2'] = normalize_italian_date(dates[1][1])
    
    if len(times) >= 2:
        data['time1'] = times[0][1]
        data['time2'] = times[1][1]
    
    if len(airports) >= 2:
        data['direction1'] = airports[0][1]
        data['direction2'] = airports[1][1]
    
    # Create label
    if data['direction1'] and data['date1'] and data['date2']:
        data['label'] = f"{data['direction1']}:{data['direction2']} {data['date1']} - {data['date2']} :: {data['time1']} - {data['time2']}"
    
    return data


def extract_english_single_flight(text, email_date):
    """Extract data from English email with one roundtrip"""
    lines = text.split('\n')
    
    data = {
        'date': email_date,
        'direction1': '',
        'date1': '',
        'time1': '',
        'direction2': '',
        'date2': '',
        'time2': '',
        'price': '',
        'label': ''
    }
    
    # Find dates (e.g., "Fri, 24 Oct")
    date_pattern = r'(\w+,\s+\d{1,2}\s+\w+)'
    
    dates = []
    times = []
    airports = []
    
    for i, line in enumerate(lines):
        # Find dates
        date_match = re.search(date_pattern, line)
        if date_match and 'Oct' in line:
            dates.append((i, date_match.group(1)))
        
        # Find times and nearby airport codes
        time_match = re.search(r'^(\d{1,2}:\d{2})\s*-\s*$', line.strip())
        if time_match:
            times.append((i, time_match.group(1)))
            
            # Airport codes should be 2-3 lines after the time
            for j in range(i+1, min(i+5, len(lines))):
                airport_match = re.search(r'^([A-Z]{3})\s*-\s*$', lines[j].strip())
                if airport_match:
                    # Next line should have the second airport
                    if j+1 < len(lines):
                        next_airport = re.search(r'^([A-Z]{3})', lines[j+1].strip())
                        if next_airport:
                            airports.append((i, f"{airport_match.group(1)}-{next_airport.group(1)}"))
                            break
    
    # Find price
    for i, line in enumerate(lines):
        if 'gone up' in line.lower() or 'gone down' in line.lower():
            for j in range(max(0, i-5), min(len(lines), i+5)):
                price_match = re.search(r'(\d+)\s*€', lines[j])
                if price_match:
                    data['price'] = price_match.group(1)
                    break
    
    # Assign data
    if len(dates) >= 2:
        data['date1'] = dates[0][1]
        data['date2'] = dates[1][1]
    
    if len(times) >= 2:
        data['time1'] = times[0][1]
        data['time2'] = times[1][1]
    
    if len(airports) >= 2:
        data['direction1'] = airports[0][1]
        data['direction2'] = airports[1][1]
    
    # Create label
    if data['direction1'] and data['date1'] and data['date2']:
        data['label'] = f"{data['direction1']}:{data['direction2']} {data['date1']} - {data['date2']} :: {data['time1']} - {data['time2']}"
    
    return data


def extract_english_double_flight(text, email_date):
    """Extract data from English email with two roundtrips"""
    lines = text.split('\n')
    
    # We'll return a list of two flights
    flights = []
    
    # Pattern matching
    date_pattern = r'(\w+,\s+\d{1,2}\s+\w+)'
    
    dates = []
    times = []
    airports = []
    prices = []
    
    for i, line in enumerate(lines):
        # Find dates
        date_match = re.search(date_pattern, line)
        if date_match and 'Oct' in line:
            dates.append((i, date_match.group(1)))
        
        # Find times and nearby airport codes
        time_match = re.search(r'^(\d{1,2}:\d{2})\s*-\s*$', line.strip())
        if time_match:
            times.append((i, time_match.group(1)))
            
            # Airport codes should be 2-3 lines after the time
            for j in range(i+1, min(i+5, len(lines))):
                airport_match = re.search(r'^([A-Z]{3})\s*-\s*$', lines[j].strip())
                if airport_match:
                    # Next line should have the second airport
                    if j+1 < len(lines):
                        next_airport = re.search(r'^([A-Z]{3})', lines[j+1].strip())
                        if next_airport:
                            airports.append((i, f"{airport_match.group(1)}-{next_airport.group(1)}"))
                            break
        
        # Find prices
        if 'gone up' in line.lower() or 'gone down' in line.lower():
            for j in range(max(0, i-5), min(len(lines), i+5)):
                price_match = re.search(r'(\d+)\s*€', lines[j])
                if price_match:
                    prices.append((i, price_match.group(1)))
                    break
    
    # Split data for two flights based on line numbers
    # First flight data should appear first, second flight data appears later
    
    # Find the midpoint to split flights
    if len(dates) >= 4:
        mid_line = dates[2][0]  # Use the 3rd date as approximate midpoint
    else:
        mid_line = 700  # Default fallback
    
    # Flight 1
    flight1 = {
        'date': email_date,
        'direction1': '',
        'date1': '',
        'time1': '',
        'direction2': '',
        'date2': '',
        'time2': '',
        'price': '',
        'label': ''
    }
    
    # Flight 2
    flight2 = {
        'date': email_date,
        'direction1': '',
        'date1': '',
        'time1': '',
        'direction2': '',
        'date2': '',
        'time2': '',
        'price': '',
        'label': ''
    }
    
    # Filter data for first flight
    dates_1 = [d for d in dates if d[0] < mid_line]
    times_1 = [t for t in times if t[0] < mid_line]
    airports_1 = [a for a in airports if a[0] < mid_line]
    
    # Filter data for second flight
    dates_2 = [d for d in dates if d[0] >= mid_line - 20]  # Small overlap to catch edge cases
    times_2 = [t for t in times if t[0] >= mid_line - 20]
    airports_2 = [a for a in airports if a[0] >= mid_line - 20]
    
    # Assign first flight
    if len(dates_1) >= 2:
        flight1['date1'] = normalize_italian_date(dates_1[0][1])
        flight1['date2'] = normalize_italian_date(dates_1[1][1])
    
    if len(times_1) >= 2:
        flight1['time1'] = times_1[0][1]
        flight1['time2'] = times_1[1][1]
    
    if len(airports_1) >= 2:
        flight1['direction1'] = airports_1[0][1]
        flight1['direction2'] = airports_1[1][1]
    
    if len(prices) >= 1:
        flight1['price'] = prices[0][1]
    
    if flight1['direction1']:
        flight1['label'] = f"{flight1['direction1']}:{flight1['direction2']} {flight1['date1']} - {flight1['date2']} :: {flight1['time1']} - {flight1['time2']}"
    
    # Assign second flight (skip first entries if they belong to flight 1)
    if len(dates_2) >= 2:
        # Take the last two dates
        flight2['date1'] = normalize_italian_date(dates_2[-2][1])
        flight2['date2'] = normalize_italian_date(dates_2[-1][1])
    
    if len(times_2) >= 2:
        # Take the last two times
        flight2['time1'] = times_2[-2][1]
        flight2['time2'] = times_2[-1][1]
    
    if len(airports_2) >= 2:
        # Take the last two airport pairs
        flight2['direction1'] = airports_2[-2][1]
        flight2['direction2'] = airports_2[-1][1]
    
    if len(prices) >= 2:
        flight2['price'] = prices[1][1]
    
    if flight2['direction1']:
        flight2['label'] = f"{flight2['direction1']}:{flight2['direction2']} {flight2['date1']} - {flight2['date2']} :: {flight2['time1']} - {flight2['time2']}"
    
    return [flight1, flight2]


def parse_mbox_file(mbox_path):
    """Parse mbox file and extract flight data"""
    mbox = mailbox.mbox(mbox_path)
    all_flights = []
    
    for message in mbox:
        text = extract_text_from_email(message)
        email_type = detect_email_type(text)
        
        if not email_type:
            continue
        
        email_date = extract_date_from_email(message, text)
        
        if email_type == "italian_single":
            flight_data = extract_italian_single_flight(text, email_date)
            if flight_data['price']:
                all_flights.append(flight_data)
        
        elif email_type == "english_single":
            flight_data = extract_english_single_flight(text, email_date)
            if flight_data['price']:
                all_flights.append(flight_data)
        
        elif email_type == "english_double":
            flights_data = extract_english_double_flight(text, email_date)
            for flight_data in flights_data:
                if flight_data['price']:
                    all_flights.append(flight_data)
    
    return all_flights


def save_to_csv(flights, csv_path):
    """Save flight data to CSV file"""
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['date', 'direction1', 'date1', 'time1', 'direction2', 'date2', 'time2', 'price', 'label']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for flight in flights:
            writer.writerow(flight)
    
    print(f"Data saved to {csv_path}")


def plot_prices(csv_path):
    """Create a plot from the CSV data"""
    import matplotlib.pyplot as plt
    import pandas as pd
    from datetime import datetime
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    if df.empty:
        print("No data to plot")
        return
    
    # Convert price to numeric
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'], format='%a, %d %b %Y', errors='coerce')
    
    # Sort by date
    df = df.sort_values('date')
    
    # Create plot
    plt.figure(figsize=(14, 8))
    
    # Group by label (each unique flight combination)
    for label in df['label'].unique():
        flight_data = df[df['label'] == label]
        plt.plot(flight_data['date'], flight_data['price'], marker='o', label=label, linewidth=2)
    
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price (€)', fontsize=12)
    plt.title('Flight Prices Over Time', fontsize=14, fontweight='bold')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save plot
    plot_path = csv_path.parent / 'flight_prices_plot.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to {plot_path}")
    
    # Show plot
    plt.show()


def main():
    """Main function"""
    # Set paths
    base_path = Path(__file__).parent
    mbox_path = base_path / 'Skyscanner.mbox' / 'mbox'
    csv_path = base_path / 'prices.csv'
    
    print("Parsing mbox file...")
    flights = parse_mbox_file(mbox_path)
    
    print(f"Found {len(flights)} flight records")
    
    if flights:
        print("Saving to CSV...")
        save_to_csv(flights, csv_path)
        
        print("Creating plot...")
        plot_prices(csv_path)
    else:
        print("No flight data found in mbox file")


if __name__ == "__main__":
    main()
