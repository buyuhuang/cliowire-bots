from MapBot import contentBreakDown
from MapBot import cleanHTTP

#Test that contentBreakDown works on a typical geoPulsed string with 1 named entities
cont, ents, coords = contentBreakDown("DHstudents went to #Venice #geocoding #p12_3404_45_4337")
assert ents == ['Venice']
assert cont == "DHstudents went to #Venice"
assert coords == [12.3404, 45.4337]

#Test that contentBreakDown works with a geoPulse of 2 named entities.
cont, ents, coords = contentBreakDown("#DHstudents went to #Venice #geocoding #p12_3404_45_4337")
assert ents == ['DHstudents', 'Venice']
assert cont == "#DHstudents went to #Venice"
assert coords == [12.3404, 45.4337]

#Test that contentBreakDown works with pulse of 0 named entities
cont, ents, coords = contentBreakDown("DHstudents went to Venice #geocoding #p12_3404_45_4337")
assert ents == []
assert cont == "DHstudents went to Venice"
assert coords == [12.3404, 45.4337]

#Test that contentBreakDown works with named entities everywhere.
cont, ents, coords = contentBreakDown("#DHstudents #went #to #Venice #geocoding #p12_3404_45_4337")
assert ents == ['DHstudents','went', 'to', 'Venice']
assert cont == "#DHstudents #went #to #Venice"
assert coords == [12.3404, 45.4337]

#Test another case
cont, ents, coords = contentBreakDown("#Paris is a nice city #geocoding #p2_3522_48_4337")
assert ents == ['Paris']
assert cont == "#Paris is a nice city"
assert coords == [2.3522, 48.4337]

#Test that hashtags after the ones relating to the geocoding are still there or parsed correctly
cont, ents, coords = contentBreakDown("#Paris is a nice city #geocoding #p2_3522_48_4337 #Mentions #DubiousPulse")
assert ents == ['Paris', 'Mentions', 'DubiousPulse']
assert cont == "#Paris is a nice city #Mentions #DubiousPulse"
assert coords == [2.3522, 48.4337]


#test that an exception is raised when the coordinates are not correctly formated
try:
    _,_,_ = contentBreakDown("#Paris is a nice city #geocoding #p2_3522_48 #Mentions #DubiousPulse")
    assert False
except Exception:
    assert True

#Test that cleanHTTP remove all balises, but keep the url in named entities.
httpStr = "<p><a href=\"https://cliowire.dhlab.epfl.ch/tags/geocoords\" class=\"mention hashtag\" rel=\"tag\">#<span>geoCoords</span></a>(2.3522, 48.8566) <a href=\"https://cliowire.dhlab.epfl.ch/tags/geoentity\" class=\"mention hashtag\" rel=\"tag\">#<span>GeoEntity</span></a> (Paris <a href=\"https://en.wikipedia.org/wiki/Paris\" rel=\"nofollow noopener\" target=\"_blank\"><span class=\"invisible\">https://</span><span class=\"\">en.wikipedia.org/wiki/Paris</span><span class=\"invisible\"></span></a>) is a nice city</p>"
intendedRes = "#geoCoords(2.3522, 48.8566) #GeoEntity (Paris https://en.wikipedia.org/wiki/Paris) is a nice city"
assert cleanHTTP(httpStr) == intendedRes
