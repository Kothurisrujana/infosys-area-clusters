[out:json][timeout:180];
(
  node["highway"="motorway_junction"](17.30,78.24,17.53,78.44);
  nwr["shop"="mall"](17.33,78.27,17.51,78.42);
  nwr["natural"="water"]["name"](17.33,78.27,17.51,78.42);
  nwr["leisure"="golf_course"](17.33,78.27,17.51,78.42);
  nwr["leisure"="stadium"](17.33,78.27,17.51,78.42);
  nwr["amenity"="university"](17.33,78.27,17.51,78.42);
  nwr["tourism"="hotel"]["stars"~"^[45]"](17.33,78.27,17.51,78.42);
  nwr["tourism"="hotel"]["name"~"Marriott|Hyatt|Westin|Novotel|Sheraton|ITC|Taj|Radisson|Trident|Oakwood|Sheraton|Crowne|Holiday Inn|Le M",i](17.33,78.27,17.51,78.42);
  nwr["leisure"="nature_reserve"]["name"](17.33,78.27,17.51,78.42);
);
out tags center;
