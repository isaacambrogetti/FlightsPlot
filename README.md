# Flight Price Tracker

A Python program that extracts flight price data from Skyscanner email updates and creates visualizations to track price changes over time.

## Features

- Parses Skyscanner price alert emails from an mbox file
- Supports three types of emails:
  - Italian emails with one roundtrip flight
  - English emails with one roundtrip flight
  - English emails with two roundtrip flights
- Extracts flight details: dates, times, airports, and prices
- Generates a CSV file with all extracted data
- Creates a line plot showing price trends over time for each flight route

## Requirements

- Python 3.8+
- matplotlib
- pandas

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

Or if using the virtual environment:
```bash
.venv/bin/pip install -r requirements.txt
```

## Usage

1. Export your Skyscanner price alert emails to an mbox file and place it in the project directory as `Skyscanner.mbox/mbox`

2. Run the program:
```bash
python flight_price_tracker.py
```

Or with virtual environment:
```bash
.venv/bin/python flight_price_tracker.py
```

3. The program will:
   - Parse all emails in the mbox file
   - Extract flight price information
   - Save the data to `prices.csv`
   - Generate a plot saved as `flight_prices_plot.png`
   - Display the plot

## CSV Output Format

The generated CSV file contains the following columns:

- **date**: Email date (when the price was tracked)
- **direction1**: First flight direction (e.g., "ZRH-LIS")
- **date1**: Departure date of first flight
- **time1**: Departure time of first flight
- **direction2**: Return flight direction (e.g., "LIS-ZRH")
- **date2**: Departure date of return flight
- **time2**: Departure time of return flight
- **price**: Total price in EUR
- **label**: Legend label for the plot (e.g., "ZRH-LIS:LIS-ZRH Fri, 24 Oct - Tue, 28 Oct :: 10:45 - 18:45")

## Plot

The generated plot shows:
- X-axis: Date when the price was tracked
- Y-axis: Price in EUR
- Each unique flight combination (same dates and times) is shown as a separate line with a different color
- Legend shows all tracked flight combinations

## Example Files

The repository includes example files for reference:
- `SkyscannerEmail_toTune-1.eml` - Italian email with one roundtrip
- `SkyscannerEmail_toTune-1-en.eml` - English email with one roundtrip
- `SkyscannerEmail_toTune-2-en.eml` - English email with two roundtrips
- `prices_handmade.csv` - Example CSV output

## How It Works

The program:
1. Opens the mbox file and iterates through all emails
2. Detects the email type (Italian/English, single/double flight)
3. Uses regex patterns to extract:
   - Flight dates and times
   - Airport codes (departure and destination)
   - Prices
4. Formats the data according to the CSV schema
5. Creates visualizations using matplotlib

## Troubleshooting

If the program doesn't extract data correctly:
- Verify the mbox file path is correct
- Check that the emails are from Skyscanner price alerts
- Ensure the email format matches one of the three supported types
- Check the console output for parsing errors