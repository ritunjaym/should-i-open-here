# Restaurant Location Analysis Input

## User Request

```json
{
  "address": "425 W 51st St, New York, NY 10019",
  "day_of_the_week": "Saturday",
  "opening_time": "11:00",
  "closing_time": "23:00",
  "search_term": "pizza restaurant"
}
```

## Hourly Traffic Data

```json
[
  {
    "hour": 11,
    "speed_summary": {
      "Free Flow": 58,
      "Slow Traffic": 14,
      "Moderate Congestion": 6,
      "Heavy Congestion": 2
    }
  },
  {
    "hour": 12,
    "speed_summary": {
      "Free Flow": 49,
      "Slow Traffic": 21,
      "Moderate Congestion": 11,
      "Heavy Congestion": 4
    }
  },
  {
    "hour": 13,
    "speed_summary": {
      "Free Flow": 41,
      "Slow Traffic": 26,
      "Moderate Congestion": 18,
      "Heavy Congestion": 7
    }
  },
  {
    "hour": 14,
    "speed_summary": {
      "Free Flow": 37,
      "Slow Traffic": 28,
      "Moderate Congestion": 21,
      "Heavy Congestion": 9
    }
  },
  {
    "hour": 15,
    "speed_summary": {
      "Free Flow": 33,
      "Slow Traffic": 29,
      "Moderate Congestion": 24,
      "Heavy Congestion": 12
    }
  },
  {
    "hour": 16,
    "speed_summary": {
      "Free Flow": 28,
      "Slow Traffic": 30,
      "Moderate Congestion": 27,
      "Heavy Congestion": 16
    }
  },
  {
    "hour": 17,
    "speed_summary": {
      "Free Flow": 22,
      "Slow Traffic": 27,
      "Moderate Congestion": 31,
      "Heavy Congestion": 21
    }
  },
  {
    "hour": 18,
    "speed_summary": {
      "Free Flow": 19,
      "Slow Traffic": 24,
      "Moderate Congestion": 33,
      "Heavy Congestion": 25
    }
  },
  {
    "hour": 19,
    "speed_summary": {
      "Free Flow": 17,
      "Slow Traffic": 22,
      "Moderate Congestion": 34,
      "Heavy Congestion": 28
    }
  },
  {
    "hour": 20,
    "speed_summary": {
      "Free Flow": 21,
      "Slow Traffic": 25,
      "Moderate Congestion": 30,
      "Heavy Congestion": 22
    }
  },
  {
    "hour": 21,
    "speed_summary": {
      "Free Flow": 29,
      "Slow Traffic": 27,
      "Moderate Congestion": 22,
      "Heavy Congestion": 14
    }
  },
  {
    "hour": 22,
    "speed_summary": {
      "Free Flow": 38,
      "Slow Traffic": 22,
      "Moderate Congestion": 14,
      "Heavy Congestion": 8
    }
  }
]
```

## Nearby Competitors

```json
[
  {
    "rank": 1,
    "title": "Hell's Kitchen Pizza",
    "address": "691 10th Ave, New York, NY 10036",
    "totalScore": 4.6,
    "reviewsCount": 843,
    "categories": ["Pizza", "Italian Restaurant", "Takeout"],
    "openingHours": [
      {"day": "Monday", "hours": "11 AM to 11 PM"},
      {"day": "Tuesday", "hours": "11 AM to 11 PM"},
      {"day": "Wednesday", "hours": "11 AM to 11 PM"},
      {"day": "Thursday", "hours": "11 AM to 11 PM"},
      {"day": "Friday", "hours": "11 AM to 12 AM"},
      {"day": "Saturday", "hours": "11 AM to 12 AM"},
      {"day": "Sunday", "hours": "12 PM to 10 PM"}
    ]
  },
  {
    "rank": 2,
    "title": "Gotham Pizza",
    "address": "527 9th Ave, New York, NY 10018",
    "totalScore": 4.3,
    "reviewsCount": 512,
    "categories": ["Pizza", "Fast Food", "Delivery"],
    "openingHours": [
      {"day": "Monday", "hours": "10 AM to 11 PM"},
      {"day": "Tuesday", "hours": "10 AM to 11 PM"},
      {"day": "Wednesday", "hours": "10 AM to 11 PM"},
      {"day": "Thursday", "hours": "10 AM to 11 PM"},
      {"day": "Friday", "hours": "10 AM to 1 AM"},
      {"day": "Saturday", "hours": "10 AM to 1 AM"},
      {"day": "Sunday", "hours": "11 AM to 11 PM"}
    ]
  },
  {
    "rank": 3,
    "title": "Midtown Slice",
    "address": "350 W 46th St, New York, NY 10036",
    "totalScore": 4.7,
    "reviewsCount": 1204,
    "categories": ["Pizza", "New York Style Pizza", "Restaurant"],
    "openingHours": [
      {"day": "Monday", "hours": "11 AM to 10 PM"},
      {"day": "Tuesday", "hours": "11 AM to 10 PM"},
      {"day": "Wednesday", "hours": "11 AM to 10 PM"},
      {"day": "Thursday", "hours": "11 AM to 10 PM"},
      {"day": "Friday", "hours": "11 AM to 11 PM"},
      {"day": "Saturday", "hours": "12 PM to 11 PM"},
      {"day": "Sunday", "hours": "12 PM to 9 PM"}
    ]
  },
  {
    "rank": 4,
    "title": "Luigi's Trattoria",
    "address": "402 W 44th St, New York, NY 10036",
    "totalScore": 4.4,
    "reviewsCount": 389,
    "categories": ["Italian Restaurant", "Pizza", "Wine Bar"],
    "openingHours": [
      {"day": "Monday", "hours": "5 PM to 11 PM"},
      {"day": "Tuesday", "hours": "5 PM to 11 PM"},
      {"day": "Wednesday", "hours": "5 PM to 11 PM"},
      {"day": "Thursday", "hours": "5 PM to 11 PM"},
      {"day": "Friday", "hours": "5 PM to 12 AM"},
      {"day": "Saturday", "hours": "4 PM to 12 AM"},
      {"day": "Sunday", "hours": "4 PM to 10 PM"}
    ]
  },
  {
    "rank": 5,
    "title": "Joe's Pizza - Midtown",
    "address": "1435 Broadway, New York, NY 10018",
    "totalScore": 4.5,
    "reviewsCount": 2841,
    "categories": ["Pizza", "Fast Food", "Takeout"],
    "openingHours": [
      {"day": "Monday", "hours": "10 AM to 12 AM"},
      {"day": "Tuesday", "hours": "10 AM to 12 AM"},
      {"day": "Wednesday", "hours": "10 AM to 12 AM"},
      {"day": "Thursday", "hours": "10 AM to 12 AM"},
      {"day": "Friday", "hours": "10 AM to 2 AM"},
      {"day": "Saturday", "hours": "10 AM to 2 AM"},
      {"day": "Sunday", "hours": "11 AM to 12 AM"}
    ]
  },
  {
    "rank": 6,
    "title": "Nonna's Neapolitan",
    "address": "555 W 50th St, New York, NY 10019",
    "totalScore": 4.8,
    "reviewsCount": 671,
    "categories": ["Pizza", "Neapolitan Pizza", "Italian Restaurant"],
    "openingHours": [
      {"day": "Monday", "hours": "Closed"},
      {"day": "Tuesday", "hours": "5 PM to 10 PM"},
      {"day": "Wednesday", "hours": "5 PM to 10 PM"},
      {"day": "Thursday", "hours": "5 PM to 10 PM"},
      {"day": "Friday", "hours": "5 PM to 11 PM"},
      {"day": "Saturday", "hours": "1 PM to 11 PM"},
      {"day": "Sunday", "hours": "1 PM to 9 PM"}
    ]
  },
  {
    "rank": 7,
    "title": "Theater District Burgers",
    "address": "315 W 48th St, New York, NY 10036",
    "totalScore": 4.1,
    "reviewsCount": 927,
    "categories": ["Burger Restaurant", "American Restaurant", "Pizza"],
    "openingHours": [
      {"day": "Monday", "hours": "11 AM to 11 PM"},
      {"day": "Tuesday", "hours": "11 AM to 11 PM"},
      {"day": "Wednesday", "hours": "11 AM to 11 PM"},
      {"day": "Thursday", "hours": "11 AM to 11 PM"},
      {"day": "Friday", "hours": "11 AM to 12 AM"},
      {"day": "Saturday", "hours": "11 AM to 12 AM"},
      {"day": "Sunday", "hours": "12 PM to 10 PM"}
    ]
  },
  {
    "rank": 8,
    "title": "Bella Cucina",
    "address": "620 9th Ave, New York, NY 10036",
    "totalScore": 4.2,
    "reviewsCount": 284,
    "categories": ["Italian Restaurant", "Pasta", "Wine Bar"],
    "openingHours": [
      {"day": "Monday", "hours": "Closed"},
      {"day": "Tuesday", "hours": "5 PM to 10 PM"},
      {"day": "Wednesday", "hours": "5 PM to 10 PM"},
      {"day": "Thursday", "hours": "5 PM to 10 PM"},
      {"day": "Friday", "hours": "5 PM to 11 PM"},
      {"day": "Saturday", "hours": "5 PM to 11 PM"},
      {"day": "Sunday", "hours": "4 PM to 9 PM"}
    ]
  },
  {
    "rank": 9,
    "title": "Quick Slice Express",
    "address": "474 9th Ave, New York, NY 10018",
    "totalScore": 3.8,
    "reviewsCount": 156,
    "categories": ["Pizza", "Takeout", "Fast Food"],
    "openingHours": [
      {"day": "Monday", "hours": "9 AM to 10 PM"},
      {"day": "Tuesday", "hours": "9 AM to 10 PM"},
      {"day": "Wednesday", "hours": "9 AM to 10 PM"},
      {"day": "Thursday", "hours": "9 AM to 10 PM"},
      {"day": "Friday", "hours": "9 AM to 11 PM"},
      {"day": "Saturday", "hours": "9 AM to 11 PM"},
      {"day": "Sunday", "hours": "10 AM to 9 PM"}
    ]
  },
  {
    "rank": 10,
    "title": "West Side Tavern",
    "address": "401 W 54th St, New York, NY 10019",
    "totalScore": 4.0,
    "reviewsCount": 612,
    "categories": ["Bar", "American Restaurant", "Pizza"],
    "openingHours": [
      {"day": "Monday", "hours": "4 PM to 2 AM"},
      {"day": "Tuesday", "hours": "4 PM to 2 AM"},
      {"day": "Wednesday", "hours": "4 PM to 2 AM"},
      {"day": "Thursday", "hours": "4 PM to 2 AM"},
      {"day": "Friday", "hours": "12 PM to 4 AM"},
      {"day": "Saturday", "hours": "12 PM to 4 AM"},
      {"day": "Sunday", "hours": "12 PM to 12 AM"}
    ]
  }
]
```
