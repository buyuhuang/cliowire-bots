from MapBot import contentBreakDown
from MapBot import openGeoPulsesFile

#Teest that non GeoPulse raise an Exception when presented a malformed GeoPulse.
try:
    contentBreakDown("DHstudents went to #GeoEntity (Venice https://en.wikipedia.org/wiki/Venice)")
    assert False
except Exception as inst:
    assert True

#Test that contentBreakDown works on a typical geoPulsed string with 1 named entities (that is the geoEntity)
cont, ents, coords = contentBreakDown("#geoCoords(12.3404, 45.4337) DHstudents went to #GeoEntity (Venice https://en.wikipedia.org/wiki/Venice)")
assert ents == ['Venice']
assert cont == "DHstudents went to Venice"
assert coords == [12.3404, 45.4337]

#Test that contentBreakDown works with a geoPulse of 2 named entities.
cont, ents, coords = contentBreakDown("#geoCoords(12.3404, 45.4337) (DHstudents https://dh.epfl.ch) went to #GeoEntity (Venice https://en.wikipedia.org/wiki/Venice)")
assert ents == ['DHstudents', 'Venice']
assert cont == "DHstudents went to Venice"
assert coords == [12.3404, 45.4337]

#Test that contentBreakDown works with pulse of 0 named entities
cont, ents, coords = contentBreakDown("#geoCoords(12.3404, 45.4337) DHstudents went to #GeoEntity Venice")
assert ents == ['Venice']
assert cont == "DHstudents went to Venice"
assert coords == [12.3404, 45.4337]

#Test that contentBreakDown works with the geoEntity is elsewhere
cont, ents, coords = contentBreakDown("#geoCoords(12.3404, 45.4337) #GeoEntity Venice was the place where the DHstudents went")
assert ents == ['Venice']
assert cont == "Venice was the place where the DHstudents went"
assert coords == [12.3404, 45.4337]

#Test that contentBreakDown works with named entities everywhere.
cont, ents, coords = contentBreakDown("#geoCoords(12.3404, 45.4337) (DHstudents https://dh.epfl.ch) (went https://go.com) (to https://go.com) #GeoEntity (Venice https://en.wikipedia.org/wiki/Venice)")
assert ents == ['DHstudents','went', 'to', 'Venice']
assert cont == "DHstudents went to Venice"
assert coords == [12.3404, 45.4337]

#Test another case where the geopulse is the first entity in the list
cont, ents, coords = contentBreakDown("#geoCoords(2.3522, 48.8566) #GeoEntity (Paris https://en.wikipedia.org/wiki/Paris) is a nice city")
assert ents == ['Paris']
assert cont == "Paris is a nice city"
assert coords == [2.3522, 48.8566]
