[out:json][timeout:90];
(

 node["highway"="traffic_signals"]["name"](17.36,78.29,17.50,78.39);
 node["place"~"neighbourhood|suburb|quarter"]["name"~"Gowlidoddi|Gowlidodi|Financial District|Kokapet|Narsingi|Puppalaguda|Khajaguda|Nanakramguda",i](17.36,78.29,17.50,78.39);
 nwr["shop"~"furniture"]["name"~"IKEA",i](17.36,78.29,17.50,78.39);
 nwr["name"~"My Home Avatar",i](17.36,78.29,17.50,78.39);
 nwr["junction"]["name"](17.36,78.29,17.50,78.39);
 nwr["amenity"="police"]["name"~"Narsingi",i](17.36,78.29,17.50,78.39);
);
out center tags;
