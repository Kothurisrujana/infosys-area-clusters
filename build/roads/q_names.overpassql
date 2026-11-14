[out:json][timeout:120];
(
 nwr["addr:street"](17.355,78.285,17.505,78.395);
 nwr["place"~"neighbourhood|quarter|suburb|hamlet"]["name"](17.355,78.285,17.505,78.395);
 nwr["landuse"="residential"]["name"](17.355,78.285,17.505,78.395);
 nwr["residential"]["name"](17.355,78.285,17.505,78.395);
);
out center tags;
