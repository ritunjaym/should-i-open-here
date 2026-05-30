from apify_client import ApifyClient
from geopy.geocoders import Nominatim
import json
from tqdm.notebook import tqdm
from datetime import datetime, time, timedelta
import pytz
from timezonefinder import TimezoneFinder
import os

api_key = os.getenv("APIFY_API_KEY")

if not api_key:
    raise ValueError("APIFY_API_KEY not found. Please set it in your environment variables.")

client = ApifyClient(api_key)

# Sample input
input = {
    "address": "411 15th Ave E, Seattle, WA 98112",
    "day_of_the_week": "Monday",
    "opening_time": "11:00",
    "closing_time": "15:00",
    "search_term": "vegan restaurant"
}

## Google Maps Scraper
# Prepare the Actor input
run_input = {
    "searchStringsArray": [input["search_term"]],
    "locationQuery": input["address"],
    "maxCrawledPlacesPerSearch": 10,
    "skipClosedPlaces": True,
    "reviewsStartDate": "2024-01-01",
}

# Run the Actor and wait for it to finish
run = client.actor("nwua9Gu5YrADL7ZDj").call(run_input=run_input)

# Put all the data in a list of dictionaries
google_maps_data = []
for item in client.dataset(run.default_dataset_id).iterate_items():
    google_maps_data.append(item)

# Filter the dataset to include only the specified keys
keys_to_keep = ['title', 'address', 'totalScore', 'categories', 'reviewsCount', 'openingHours', 'rank']

filtered_google_maps_data = [
    {key: item.get(key) for key in keys_to_keep}
    for item in google_maps_data
]

## Google Maps Traffic Scraper
# Get lat and long of address
geolocator = Nominatim(user_agent="my_app")
location = geolocator.geocode(input["address"])
lat = location.latitude
lon = location.longitude

# Dictionary to store all speed summaries
traffic_data = {}

# 1. Parse start and end hours from input directly in this cell
start_hour = int(input['opening_time'].split(':')[0])
end_hour = int(input['closing_time'].split(':')[0])

# 2. Identify the local timezone based on coordinates
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=lon, lat=lat)
local_tz = pytz.timezone(tz_name)

# 3. Helper to get the start of the current week (Sunday 00:00 UTC)
now_utc = datetime.now(pytz.utc)
days_since_sunday = (now_utc.weekday() + 1) % 7
sunday_start_utc = (now_utc - timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)

print(f"Local Timezone: {tz_name}")
print(f"Reference Sunday Start (UTC): {sunday_start_utc}\n")

# 4. Calculate seconds from Sunday 00:00 UTC for each hour
for hour in range(start_hour, end_hour + 1):
    # Create local time for today at the specific hour
    naive_dt = datetime.combine(datetime.now().date(), time(hour=hour % 24))
    local_dt = local_tz.localize(naive_dt)
    
    # Convert to UTC
    utc_dt = local_dt.astimezone(pytz.utc)
    
    # Calculate difference in seconds from Sunday 00:00 UTC
    delta_seconds = int((utc_dt - sunday_start_utc).total_seconds())
    
    print(f"Local {hour:02d}:00 ({local_dt.strftime('%Z')}) -> {delta_seconds} seconds from Sunday 00:00 UTC")

print("Fetching traffic data for each hour...")
for hour in tqdm(range(start_hour, end_hour + 1), desc="Fetching Traffic Data"):
    # Recalculate delta_seconds for the current hour
    naive_dt = datetime.combine(datetime.now().date(), time(hour=hour % 24))
    local_dt = local_tz.localize(naive_dt)
    utc_dt = local_dt.astimezone(pytz.utc)
    delta_seconds = int((utc_dt - sunday_start_utc).total_seconds())
    
    # Prepare the Actor input
    run_input = {
        "lat": str(lat),
        "lon": str(lon),
        "zoom": 17,
        "radius": 2,
        "seconds": delta_seconds,
    }

    # Run the Actor and wait for it to finish
    run = client.actor("qlLfzCYcQfFM9S5n1").call(run_input=run_input)

    # Fetch and extract 'speed_summary' from the run's dataset
    speed_summaries = []
    for item in client.dataset(run.default_dataset_id).iterate_items():
      if "speed_summary" in item['metadata']:
        speed_summaries.append(item['metadata']['speed_summary'])
            
    # Store the result with a clear label for seconds
    traffic_data[f"{delta_seconds}"] = speed_summaries

print("\nExtraction complete.")

# Aggregate traffic data
aggregated_traffic = {}
categories = ["Free Flow", "Slow Traffic", "Moderate Congestion", "Heavy Congestion"]

for timestamp, summaries in traffic_data.items():
    totals = {cat: 0 for cat in categories}
    for entry in summaries:
        for cat in categories:
            totals[cat] += entry.get(cat, 0)
            
    # Convert timestamp (seconds from Sunday 00:00 UTC) to local datetime string
    dt_utc = sunday_start_utc + timedelta(seconds=int(timestamp))
    dt_local = dt_utc.astimezone(local_tz)
    readable_time = dt_local.strftime('%Y-%m-%d %I:%M %p %Z')
    
    aggregated_traffic[readable_time] = totals

# Combine both datasets into one dictionary
combined_data = {
    "google_maps_places": filtered_google_maps_data,
    "aggregated_traffic": aggregated_traffic
}

# Save to a JSON file
file_path = "exported_data.json"
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(combined_data, f, indent=2, ensure_ascii=False)

print(f"Data successfully exported to {file_path}. You can find it in the folder icon on the left panel!")