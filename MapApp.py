import folium

venice_coord = [45.4,12.33]
m = folium.Map(location=venice_coord)
venice = "Venice"

# créer un marker avec lequel une box apparait qui contient une url

doges_location = [45.4337, 12.3404]
url = "<a href=\"https://cliowire.dhlab.epfl.ch/web/statuses/99018727713161107\">"+venice+"</a>"
folium.Marker(doges_location, popup=url).add_to(m)

m.save('MapAppTest.html')
m
