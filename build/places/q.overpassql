[out:json][timeout:180];
(
  nwr["railway"="station"](17.30,78.24,17.56,78.46);
  nwr["public_transport"="station"]["subway"="yes"](17.30,78.24,17.56,78.46);
  nwr["station"="subway"](17.30,78.24,17.56,78.46);
  nwr["office"~"^(it|company|software|telecommunication)$"](17.33,78.27,17.51,78.40);
  nwr["building"="office"]["name"](17.33,78.27,17.51,78.40);
  nwr["landuse"="commercial"]["name"~"IT|Tech|SEZ|Park|Campus|Tower|Hub",i](17.33,78.27,17.51,78.40);
  nwr["amenity"~"^(school|college|university)$"](17.33,78.27,17.51,78.40);
  nwr["amenity"~"^(hospital|clinic)$"](17.33,78.27,17.51,78.40);
  nwr["healthcare"="hospital"](17.33,78.27,17.51,78.40);
  nwr["leisure"="park"](17.33,78.27,17.51,78.40);
  nwr["amenity"~"^(restaurant|cafe|fast_food|food_court)$"](17.33,78.27,17.51,78.40);
);
out tags center;
