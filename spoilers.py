# -*- coding: utf-8 -*-
import datetime
import requests
import feedparser
import re
import json
#import hashlib

#variables for xml & json
blockname = 'Kaladesh'
setname = 'KLD'
setlongname = 'Kaladesh'
setreleasedate = '2016-09-30'

setjson = setname + '.json'
cardsxml = setname + '.xml'

#for maintaining an html page with changes.
#format is
#line 27: latest card added
#line 29: date of last add
#line 31: time of last add
html = 'index.html'

#static
SPOILER_RSS = 'http://www.mtgsalvation.com/spoilers.rss'
#typically magic.wizards.com/en/content/set-name-with-hyphens-cards
IMAGES = 'http://magic.wizards.com/en/content/' + setlongname.lower().replace(' ','-') + '-cards'
#static
IMAGES2 = 'http://mythicspoiler.com/newspoilers.html'
#magic.wizards.com/en/articles/card-image-gallery/set-name-with-hyphens
IMAGES3 = 'http://magic.wizards.com/en/articles/archive/card-image-gallery/' + setlongname.lower().replace(' ','-')

#scraper pattern for mtgs rss feed
patterns = ['<b>Name:</b> <b>(?P<name>.*?)<',
            'Cost: (?P<cost>\d{0,2}[WUBRGC]*?)<',
            'Type: (?P<type>.*?)<',
            'Pow/Tgh: (?P<pow>.*?)<',
            'Rules Text: (?P<rules>.*?)<br /',
            'Rarity: (?P<rarity>.*?)<',
            'Set Number: #(?P<setnumber>.*?)/'
            ]

related_cards = {}

#fix any cards that have errors, format:
#"card name": {
#  "incorrect key": "correct value"
#}
#can handle multiple incorrect values
#and handles incorrect name
#new keys will be created (loyalty)
card_corrections = {
    "Glint-Sleeved Artisan": {
        "name": "Glint-Sleeve Artisan"
    },
    "Fleetwheel Cruiser": {
        "pow": "5/3",
        "type": "Artifact - Vehicle"
    },
    "Golden Wire Fox": {
        "pow": "2/2"
    },
    "Sky Skiff": {
        "pow": "2/3"
    },
    "Skysovereign, Consul Flagship": {
        "pow": "6/5"
    },
    "Ovalchase Dragster": {
        "pow": "6/1"
    },
    "Saheeli Rai": {
        "loyalty": 3
    }
}

#if you want to add a card manually
#use this template and place the object in the manual_cards array
manual_card_template = [
    {
        "cost": '',
        "cmc": '',
        "img": '',
        "pow": '',
        "name": '',
        "rules": '',
        "type": '',
        "setnumber": '',
        "rarity": '',
    }
]

#array for storing manually entered cards, mtgs can be slow
manual_cards = [
]

def get_cards():
    text = requests.get(SPOILER_RSS).text
    d = feedparser.parse(text)

    cards = []
    for entry in d.items()[5][1]:
        card = dict(cost='',cmc='',img='',pow='',name='',rules='',type='',
                color='', altname='', colorIdentity='', colorArray=[], colorIdentityArray=[], setnumber='', rarity='')
        summary = entry['summary']
        for pattern in patterns:
            match = re.search(pattern, summary, re.MULTILINE|re.DOTALL)
            if match:
                dg = match.groupdict()
                card[dg.items()[0][0]] = dg.items()[0][1]
        cards.append(card)

    for manual_card in manual_cards:
        incards = False
        manual_card['colorArray'] = []
        manual_card['colorIdentityArray'] = []
        manual_card['color'] = ''
        manual_card['colorIdentity'] = ''
        if not manual_card.has_key('rules'):
            manual_card['rules'] = ''
        if not manual_card.has_key('pow'):
            manual_card['pow'] = ''
        if not manual_card.has_key('setnumber'):
            manual_card['setnumber'] = '0'
        if not manual_card.has_key('type'):
            manual_card['type'] = ''
        for card in cards:
            if card['name'] == manual_card['name']:
                incards = True
        if not (incards):
            print 'Inserting manual card: ' + manual_card['name']
            cards.append(manual_card)
    return cards

def correct_cards(cards):
    for card in cards:
        if card['name'] == ' Rashmi, Eterniafter ':
            cards.remove(card)
        elif card['name'] == 'DeputisProtester':
            cards.remove(card)
        card['name'] = card['name'].replace('&#x27;', '\'')
        card['rules'] = card['rules'].replace('&#x27;', '\'') \
            .replace('&lt;i&gt;', '') \
            .replace('&lt;/i&gt;', '') \
            .replace('&quot;', '"') \
            .replace('blkocking', 'blocking').replace('&amp;bull;','*')\
            .replace('comes into the','enters the')
        if card['name'] in card_corrections:
            for correction in card_corrections[card['name']]:
                if correction == 'name':
                    card['rules'] = card['rules'].replace(card['name'],card_corrections[card['name']][correction])
                else:
                    card[correction] = card_corrections[card['name']][correction]

        if 'cost' in card and len(card['cost']) > 0:
            m = re.search('(\d+)', card['cost'].replace('X',''))
            cmc = 0
            if m:
                cmc += int(m.group())
                cmc += len(card['cost']) - 1  # account for colored symbols
            else:
                cmc += len(card['cost'])  # all colored symbols
            card['cmc'] = cmc
        # figure out color
        for c in 'WUBRG':
            if c not in card['colorIdentity']:
                if c in card['cost']:
                    card['color'] += c
                    card['colorIdentity'] += c
                if (c + '}') in card['rules'] or (str.lower(c) + '}') in card['rules']:
                    if not (c in card['colorIdentity']):
                        card['colorIdentity'] += c

    return cards

def add_images(cards):
    text = requests.get(IMAGES).text
    text2 = requests.get(IMAGES2).text
    text3 = requests.get(IMAGES3).text
    wotcpattern = r'<img alt="{}.*?" src="(?P<img>.*?\.png)"'
    mythicspoilerpattern = r' src="' + setname.lower() + '/cards/{}.*?.jpg">'
    for c in cards:
                #check official wotc site first
        match = re.search(wotcpattern.format(c['name'].replace('\'','&rsquo;')), text, re.DOTALL)
        if not c['img']:
            if match:
                c['img'] = match.groupdict()['img']
            else:
                        #check wotc site #2 next
                match3 = re.search(wotcpattern.format(c['name'].replace('\'','&rsquo;')), text3, re.DOTALL)
                if match3:
                    c['img'] = match3.groupdict()['img']
                else:
                            #finally check mythicspoiler
                    match2 = re.search(mythicspoilerpattern.format((c['name']).lower().replace(' ', '').replace('&#x27;', '').replace('-', '').replace('\'','').replace(',', '')), text2, re.DOTALL)
                    if match2:
                        #print match2.group(0).replace(' src="', 'http://mythicspoiler.com/').replace('">', '')
                        c['img'] = match2.group(0).replace(' src="', 'http://mythicspoiler.com/').replace('">', '')
                    else:
                        print('image for {} not found'.format(c['name']))
                        #print('we checked mythic for ' + c['altname'])
                    pass


def make_json(cards, setjson):
    #initialize mtg format json
    cardsjson = {
        "block": blockname,
        "border": "black",
        "code": setname,
        "magicCardsInfoCode": setname.lower(),
        "name": setlongname,
        "releaseDate": setreleasedate,
        "type": "expansion",
        "booster": [
                [
                "rare",
                "mythic rare"
                ],
            "uncommon",
            "uncommon",
            "uncommon",
            "common",
            "common",
            "common",
            "common",
            "common",
            "common",
            "common",
            "common",
            "common",
            "common",
            "land",
            "marketing"
        ],
        "cards": []
    }
    for card in cards:
            #check to see if card is duplicate
        dupe = False
        for dupecheck in cardsjson['cards']:
            if dupecheck['name'] == card['name']:
                dupe = True
        if dupe == True:
            continue
        #if 'draft' in card['rules']:
        #    continue
        for cid in card['colorIdentity']:
            card['colorIdentityArray'].append(cid)
        if 'W' in card['color']:
            card['colorArray'].append('White')
        if 'U' in card['color']:
            card['colorArray'].append('Blue')
        if 'B' in card['color']:
            card['colorArray'].append('Black')
        if 'R' in card['color']:
            card['colorArray'].append('Red')
        if 'G' in card['color']:
            card['colorArray'].append('Green')
        cardpower = ''
        cardtoughness = ''
        if len(card['pow'].split('/')) > 1:
            cardpower = card['pow'].split('/')[0]
            cardtoughness = card['pow'].split('/')[1]
        cardnames = []
        cardnumber = card['setnumber'].lstrip('0')
        if card['name'] in related_cards:
            cardnames.append(card['name'])
            cardnames.append(related_cards[card['name']])
            cardnumber += 'a'
            card['layout'] = 'double-faced'
            card['name']
        for namematch in related_cards:
            if card['name'] == related_cards[namematch]:
                card['layout'] = 'double-faced'
                cardnames.append(namematch)
                if not card['name'] in cardnames:
                    cardnames.append(card['name'])
                    cardnumber += 'b'
        cardtypes = []
        if not '-' in card['type']:
            card['type'] = card['type'].replace('instant','Instant')
            cardtypes.append(card['type'].replace('instant','Instant'))
        else:
            cardtypes = card['type'].replace('Legendary ','').split('-')[0].split(' ')[:-1]
        #print card['name']
        if card['cmc'] == '':
            card['cmc'] = 0
        cardjson = {}
        #cardjson["id"] = hashlib.sha1(setname + card['name'] + str(card['name']).lower()).hexdigest()
        cardjson["cmc"] = card['cmc']
        cardjson["manaCost"] = card['cost']
        cardjson["name"] = card['name']
        cardjson["number"] = cardnumber
        if card['rarity'] not in ['Mythic Rare','Rare','Uncommon','Common','Special']:
            print card['name'] + ' has rarity = ' + card['rarity']
        cardjson["rarity"] = card['rarity']
        cardjson["text"] = card['rules']
        cardjson["type"] = card['type']
        cardjson["url"] = card['img']
        cardjson["types"] = cardtypes
        #optional fields
        if len(card['colorIdentityArray']) > 0:
            cardjson["colorIdentity"] = card['colorIdentityArray']
        if len(card['colorArray']) > 0:
            cardjson["colors"] = card['colorArray']
        if len(cardnames) > 1:
            cardjson["names"] = cardnames
        if cardpower or cardpower == '0':
            cardjson["power"] = cardpower
            cardjson["toughness"] = cardtoughness
        if card.has_key('loyalty'):
            cardjson["loyalty"] = card['loyalty']
        if card.has_key('layout'):
            cardjson["layout"] = card['layout']

        cardsjson['cards'].append(cardjson)
    with open(setjson, 'w') as outfile:
        json.dump(cardsjson, outfile, sort_keys=True, indent=2, separators=(',', ': '))

    return cardsjson

def write_xml(mtgjson, cardsxml):
    cardsxml = open(cardsxml, 'w')
    cardsxml.truncate()
    count = 0
    dfccount = 0
    newest = ''
    related = 0
    cardsxml.write("<?xml version='1.0' encoding='UTF-8'?>\n"
                   "<cockatrice_carddatabase version='3'>\n"
                   "<sets>\n<set>\n<name>"
                   + setname +
                   "</name>\n"
                   "<longname>"
                   + setlongname +
                   "</longname>\n"
                   "<settype>Expansion</settype>\n"
                   "<releasedate>"
                   + setreleasedate +
                   "</releasedate>\n"
                   "</set>\n"
                   "</sets>\n"
                   "<cards>")
    for card in mtgjson["cards"]:
        if count == 0:
            newest = card["name"]
        count += 1
        #print card["name"]
        name = card["name"]
        if card.has_key("manaCost"):
            manacost = card["manaCost"].replace('{', '').replace('}', '')
        else:
            manacost = ""
        if card.has_key("power") or card.has_key("toughness"):
            if card["power"]:
                pt = str(card["power"]) + "/" + str(card["toughness"])
            else:
                pt = 0
        else:
            pt = 0
        if card.has_key("text"):
            text = card["text"]
        else:
            text = ""
        if card.has_key("names"):
            if len(card["names"]) > 1:
                if card["names"][0] == card["name"]:
                    related = card["names"][1]
                    text += '\n\n(Related: ' + card["names"][1] + ')'
                    dfccount += 1
                elif card['names'][1] == card['name']:
                    related = card["names"][0]
                    text += '\n\n(Related: ' + card["names"][0] + ')'

        cardtype = card["type"]
        tablerow = "1"
        if "Land" in cardtype:
            tablerow = "0"
        elif "Sorcery" in cardtype:
            tablerow = "3"
        elif "Instant" in cardtype:
            tablerow = "3"
        elif "Creature" in cardtype:
            tablerow = "2"

        cardsxml.write("<card>\n")
        cardsxml.write("<name>" + name.encode('utf-8') + "</name>\n")
        cardsxml.write('<set rarity="' + card['rarity'] + '" picURL="' + card["url"] + '">' + setname + '</set>\n')
        cardsxml.write("<manacost>" + manacost.encode('utf-8') + "</manacost>\n")
        cardsxml.write("<cmc>" + str(card['cmc']) + "</cmc>")
        if card.has_key('colors'):
            for color in card['colors']:
                cardsxml.write('<color>' + color + '</color>')
        if name == 'Terrarion' or name == 'Cryptolith Fragment':
            cardsxml.write("<cipt>1</cipt>")
        cardsxml.write("<type>" + cardtype.encode('utf-8') + "</type>\n")
        if pt:
            cardsxml.write("<pt>" + pt + "</pt>\n")
        if card.has_key('loyalty'):
            cardsxml.write("<loyalty>" + str(card['loyalty']) + "</loyalty>")
        cardsxml.write("<tablerow>" + tablerow + "</tablerow>\n")
        cardsxml.write("<text>" + text.encode('utf-8') + "</text>\n")
        if related:
            cardsxml.write("<related>" + related.encode('utf-8') + "</related>\n")
            related = ''

        cardsxml.write("</card>\n")

    cardsxml.write("</cards>\n</cockatrice_carddatabase>")

    print 'XML STATS'
    print 'Total cards: ' + str(count)
    if dfccount > 0:
        print 'DFC: ' + str(dfccount)
    print 'Newest: ' + str(newest)
    print 'Time: ' + str(datetime.datetime.today().strftime('%H:%M'))

    return newest

def writehtml(newest):
    f = open(html, 'r')
    lines = f.readlines()
    lines[26] = newest + '\n'
    lines[28] = str(datetime.date.today()) + '\n'
    lines[30] = str(datetime.datetime.today().strftime('%H:%M')) + '\n'
    f.close()

    f = open(html, 'w')
    f.writelines(lines)
    f.close()

if __name__ == '__main__':
    cards = get_cards()
    cards = correct_cards(cards)
    #some unicode cards don't get caught the first time through, no harm going through twice
    cards = correct_cards(cards)
    add_images(cards)
    #prep_xml(cards)
    #make_xml(cards)
    mtgjson = make_json(cards, setjson)
    newest = write_xml(mtgjson, cardsxml)
    writehtml(newest)
