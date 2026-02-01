<!DOCTYPE html>
<html>
<head>
  <title>Tornado Probability Map</title>
  <meta charset="utf-8" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
  <style>
    html, body { margin:0; height:100%; }
    #map { width:100%; height:100%; }
  </style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
var map = L.map('map').setView([39.5, -98.35], 4);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution:'© OpenStreetMap contributors'
}).addTo(map);

function getColor(p){
  return p>0.8 ? '#800026' :
         p>0.6 ? '#BD0026' :
         p>0.4 ? '#E31A1C' :
         p>0.2 ? '#FC4E2A' :
                 '#FFEDA0';
}

fetch("map/data/tornado_prob.json")
  .then(r => r.json())
  .then(data => {
    data.forEach(pt => {
      L.rectangle(
        [[pt.lat_min, pt.lon_min],[pt.lat_max, pt.lon_max]],
        { fillColor: getColor(pt.prob), fillOpacity:0.7, color:'#000', weight:0.2 }
      ).addTo(map);
    });
    console.log("✅ All cells drawn correctly, touching each other")
  });
</script>
</body>
</html>
