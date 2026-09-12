import json
import logging
import requests
from agents.base import BaseAgent

logger = logging.getLogger("source_dispatch_agent")

PUBLIC_SECTOR_PORTALS = [
    {
        "name": "Birmingham City Council 1",
        "sector": "Local Government",
        "url": "https://www.birmingham.gov.uk"
    },
    {
        "name": "Bradford City Council 2",
        "sector": "Local Government",
        "url": "https://www.bradford.gov.uk"
    },
    {
        "name": "Brighton City Council 3",
        "sector": "Local Government",
        "url": "https://www.brighton.gov.uk"
    },
    {
        "name": "Bristol City Council 4",
        "sector": "Local Government",
        "url": "https://www.bristol.gov.uk"
    },
    {
        "name": "Cambridge City Council 5",
        "sector": "Local Government",
        "url": "https://www.cambridge.gov.uk"
    },
    {
        "name": "Cardiff City Council 6",
        "sector": "Local Government",
        "url": "https://www.cardiff.gov.uk"
    },
    {
        "name": "Coventry City Council 7",
        "sector": "Local Government",
        "url": "https://www.coventry.gov.uk"
    },
    {
        "name": "Derby City Council 8",
        "sector": "Local Government",
        "url": "https://www.derby.gov.uk"
    },
    {
        "name": "Dundee City Council 9",
        "sector": "Local Government",
        "url": "https://www.dundee.gov.uk"
    },
    {
        "name": "Edinburgh City Council 10",
        "sector": "Local Government",
        "url": "https://www.edinburgh.gov.uk"
    },
    {
        "name": "Glasgow City Council 11",
        "sector": "Local Government",
        "url": "https://www.glasgow.gov.uk"
    },
    {
        "name": "Leeds City Council 12",
        "sector": "Local Government",
        "url": "https://www.leeds.gov.uk"
    },
    {
        "name": "Leicester City Council 13",
        "sector": "Local Government",
        "url": "https://www.leicester.gov.uk"
    },
    {
        "name": "Liverpool City Council 14",
        "sector": "Local Government",
        "url": "https://www.liverpool.gov.uk"
    },
    {
        "name": "Manchester City Council 15",
        "sector": "Local Government",
        "url": "https://www.manchester.gov.uk"
    },
    {
        "name": "Newcastle City Council 16",
        "sector": "Local Government",
        "url": "https://www.newcastle.gov.uk"
    },
    {
        "name": "Newport City Council 17",
        "sector": "Local Government",
        "url": "https://www.newport.gov.uk"
    },
    {
        "name": "Nottingham City Council 18",
        "sector": "Local Government",
        "url": "https://www.nottingham.gov.uk"
    },
    {
        "name": "Oxford City Council 19",
        "sector": "Local Government",
        "url": "https://www.oxford.gov.uk"
    },
    {
        "name": "Plymouth City Council 20",
        "sector": "Local Government",
        "url": "https://www.plymouth.gov.uk"
    },
    {
        "name": "Portsmouth City Council 21",
        "sector": "Local Government",
        "url": "https://www.portsmouth.gov.uk"
    },
    {
        "name": "Sheffield City Council 22",
        "sector": "Local Government",
        "url": "https://www.sheffield.gov.uk"
    },
    {
        "name": "Southampton City Council 23",
        "sector": "Local Government",
        "url": "https://www.southampton.gov.uk"
    },
    {
        "name": "Sunderland City Council 24",
        "sector": "Local Government",
        "url": "https://www.sunderland.gov.uk"
    },
    {
        "name": "Swansea City Council 25",
        "sector": "Local Government",
        "url": "https://www.swansea.gov.uk"
    },
    {
        "name": "Wolverhampton City Council 26",
        "sector": "Local Government",
        "url": "https://www.wolverhampton.gov.uk"
    },
    {
        "name": "York City Council 27",
        "sector": "Local Government",
        "url": "https://www.york.gov.uk"
    },
    {
        "name": "Belfast City Council 28",
        "sector": "Local Government",
        "url": "https://www.belfast.gov.uk"
    },
    {
        "name": "London City Council 29",
        "sector": "Local Government",
        "url": "https://www.london.gov.uk"
    },
    {
        "name": "Westminster City Council 30",
        "sector": "Local Government",
        "url": "https://www.westminster.gov.uk"
    },
    {
        "name": "Camden City Council 31",
        "sector": "Local Government",
        "url": "https://www.camden.gov.uk"
    },
    {
        "name": "Islington City Council 32",
        "sector": "Local Government",
        "url": "https://www.islington.gov.uk"
    },
    {
        "name": "Hackney City Council 33",
        "sector": "Local Government",
        "url": "https://www.hackney.gov.uk"
    },
    {
        "name": "Towerhamlets City Council 34",
        "sector": "Local Government",
        "url": "https://www.towerhamlets.gov.uk"
    },
    {
        "name": "Greenwich City Council 35",
        "sector": "Local Government",
        "url": "https://www.greenwich.gov.uk"
    },
    {
        "name": "Lewisham City Council 36",
        "sector": "Local Government",
        "url": "https://www.lewisham.gov.uk"
    },
    {
        "name": "Southwark City Council 37",
        "sector": "Local Government",
        "url": "https://www.southwark.gov.uk"
    },
    {
        "name": "Lambeth City Council 38",
        "sector": "Local Government",
        "url": "https://www.lambeth.gov.uk"
    },
    {
        "name": "Wandsworth City Council 39",
        "sector": "Local Government",
        "url": "https://www.wandsworth.gov.uk"
    },
    {
        "name": "Hammersmith City Council 40",
        "sector": "Local Government",
        "url": "https://www.hammersmith.gov.uk"
    },
    {
        "name": "Kensington City Council 41",
        "sector": "Local Government",
        "url": "https://www.kensington.gov.uk"
    },
    {
        "name": "Brent City Council 42",
        "sector": "Local Government",
        "url": "https://www.brent.gov.uk"
    },
    {
        "name": "Ealing City Council 43",
        "sector": "Local Government",
        "url": "https://www.ealing.gov.uk"
    },
    {
        "name": "Hounslow City Council 44",
        "sector": "Local Government",
        "url": "https://www.hounslow.gov.uk"
    },
    {
        "name": "Richmond City Council 45",
        "sector": "Local Government",
        "url": "https://www.richmond.gov.uk"
    },
    {
        "name": "Kingston City Council 46",
        "sector": "Local Government",
        "url": "https://www.kingston.gov.uk"
    },
    {
        "name": "Merton City Council 47",
        "sector": "Local Government",
        "url": "https://www.merton.gov.uk"
    },
    {
        "name": "Sutton City Council 48",
        "sector": "Local Government",
        "url": "https://www.sutton.gov.uk"
    },
    {
        "name": "Croydon City Council 49",
        "sector": "Local Government",
        "url": "https://www.croydon.gov.uk"
    },
    {
        "name": "Bromley City Council 50",
        "sector": "Local Government",
        "url": "https://www.bromley.gov.uk"
    },
    {
        "name": "Bexley City Council 51",
        "sector": "Local Government",
        "url": "https://www.bexley.gov.uk"
    },
    {
        "name": "Havering City Council 52",
        "sector": "Local Government",
        "url": "https://www.havering.gov.uk"
    },
    {
        "name": "Barking City Council 53",
        "sector": "Local Government",
        "url": "https://www.barking.gov.uk"
    },
    {
        "name": "Redbridge City Council 54",
        "sector": "Local Government",
        "url": "https://www.redbridge.gov.uk"
    },
    {
        "name": "Newham City Council 55",
        "sector": "Local Government",
        "url": "https://www.newham.gov.uk"
    },
    {
        "name": "Walthamforest City Council 56",
        "sector": "Local Government",
        "url": "https://www.walthamforest.gov.uk"
    },
    {
        "name": "Haringey City Council 57",
        "sector": "Local Government",
        "url": "https://www.haringey.gov.uk"
    },
    {
        "name": "Enfield City Council 58",
        "sector": "Local Government",
        "url": "https://www.enfield.gov.uk"
    },
    {
        "name": "Barnet City Council 59",
        "sector": "Local Government",
        "url": "https://www.barnet.gov.uk"
    },
    {
        "name": "Harrow City Council 60",
        "sector": "Local Government",
        "url": "https://www.harrow.gov.uk"
    },
    {
        "name": "Hillingdon City Council 61",
        "sector": "Local Government",
        "url": "https://www.hillingdon.gov.uk"
    },
    {
        "name": "Aberdeen City Council 62",
        "sector": "Local Government",
        "url": "https://www.aberdeen.gov.uk"
    },
    {
        "name": "Birmingham City Council 63",
        "sector": "Local Government",
        "url": "https://www.birmingham.gov.uk"
    },
    {
        "name": "Bradford City Council 64",
        "sector": "Local Government",
        "url": "https://www.bradford.gov.uk"
    },
    {
        "name": "Brighton City Council 65",
        "sector": "Local Government",
        "url": "https://www.brighton.gov.uk"
    },
    {
        "name": "Bristol City Council 66",
        "sector": "Local Government",
        "url": "https://www.bristol.gov.uk"
    },
    {
        "name": "Cambridge City Council 67",
        "sector": "Local Government",
        "url": "https://www.cambridge.gov.uk"
    },
    {
        "name": "Cardiff City Council 68",
        "sector": "Local Government",
        "url": "https://www.cardiff.gov.uk"
    },
    {
        "name": "Coventry City Council 69",
        "sector": "Local Government",
        "url": "https://www.coventry.gov.uk"
    },
    {
        "name": "Derby City Council 70",
        "sector": "Local Government",
        "url": "https://www.derby.gov.uk"
    },
    {
        "name": "Dundee City Council 71",
        "sector": "Local Government",
        "url": "https://www.dundee.gov.uk"
    },
    {
        "name": "Edinburgh City Council 72",
        "sector": "Local Government",
        "url": "https://www.edinburgh.gov.uk"
    },
    {
        "name": "Glasgow City Council 73",
        "sector": "Local Government",
        "url": "https://www.glasgow.gov.uk"
    },
    {
        "name": "Leeds City Council 74",
        "sector": "Local Government",
        "url": "https://www.leeds.gov.uk"
    },
    {
        "name": "Leicester City Council 75",
        "sector": "Local Government",
        "url": "https://www.leicester.gov.uk"
    },
    {
        "name": "Liverpool City Council 76",
        "sector": "Local Government",
        "url": "https://www.liverpool.gov.uk"
    },
    {
        "name": "Manchester City Council 77",
        "sector": "Local Government",
        "url": "https://www.manchester.gov.uk"
    },
    {
        "name": "Newcastle City Council 78",
        "sector": "Local Government",
        "url": "https://www.newcastle.gov.uk"
    },
    {
        "name": "Newport City Council 79",
        "sector": "Local Government",
        "url": "https://www.newport.gov.uk"
    },
    {
        "name": "Nottingham City Council 80",
        "sector": "Local Government",
        "url": "https://www.nottingham.gov.uk"
    },
    {
        "name": "Oxford City Council 81",
        "sector": "Local Government",
        "url": "https://www.oxford.gov.uk"
    },
    {
        "name": "Plymouth City Council 82",
        "sector": "Local Government",
        "url": "https://www.plymouth.gov.uk"
    },
    {
        "name": "Portsmouth City Council 83",
        "sector": "Local Government",
        "url": "https://www.portsmouth.gov.uk"
    },
    {
        "name": "Sheffield City Council 84",
        "sector": "Local Government",
        "url": "https://www.sheffield.gov.uk"
    },
    {
        "name": "Southampton City Council 85",
        "sector": "Local Government",
        "url": "https://www.southampton.gov.uk"
    },
    {
        "name": "Sunderland City Council 86",
        "sector": "Local Government",
        "url": "https://www.sunderland.gov.uk"
    },
    {
        "name": "Swansea City Council 87",
        "sector": "Local Government",
        "url": "https://www.swansea.gov.uk"
    },
    {
        "name": "Wolverhampton City Council 88",
        "sector": "Local Government",
        "url": "https://www.wolverhampton.gov.uk"
    },
    {
        "name": "York City Council 89",
        "sector": "Local Government",
        "url": "https://www.york.gov.uk"
    },
    {
        "name": "Belfast City Council 90",
        "sector": "Local Government",
        "url": "https://www.belfast.gov.uk"
    },
    {
        "name": "London City Council 91",
        "sector": "Local Government",
        "url": "https://www.london.gov.uk"
    },
    {
        "name": "Westminster City Council 92",
        "sector": "Local Government",
        "url": "https://www.westminster.gov.uk"
    },
    {
        "name": "Camden City Council 93",
        "sector": "Local Government",
        "url": "https://www.camden.gov.uk"
    },
    {
        "name": "Islington City Council 94",
        "sector": "Local Government",
        "url": "https://www.islington.gov.uk"
    },
    {
        "name": "Hackney City Council 95",
        "sector": "Local Government",
        "url": "https://www.hackney.gov.uk"
    },
    {
        "name": "Towerhamlets City Council 96",
        "sector": "Local Government",
        "url": "https://www.towerhamlets.gov.uk"
    },
    {
        "name": "Greenwich City Council 97",
        "sector": "Local Government",
        "url": "https://www.greenwich.gov.uk"
    },
    {
        "name": "Lewisham City Council 98",
        "sector": "Local Government",
        "url": "https://www.lewisham.gov.uk"
    },
    {
        "name": "Southwark City Council 99",
        "sector": "Local Government",
        "url": "https://www.southwark.gov.uk"
    },
    {
        "name": "Lambeth City Council 100",
        "sector": "Local Government",
        "url": "https://www.lambeth.gov.uk"
    },
    {
        "name": "Wandsworth City Council 101",
        "sector": "Local Government",
        "url": "https://www.wandsworth.gov.uk"
    },
    {
        "name": "Hammersmith City Council 102",
        "sector": "Local Government",
        "url": "https://www.hammersmith.gov.uk"
    },
    {
        "name": "Kensington City Council 103",
        "sector": "Local Government",
        "url": "https://www.kensington.gov.uk"
    },
    {
        "name": "Brent City Council 104",
        "sector": "Local Government",
        "url": "https://www.brent.gov.uk"
    },
    {
        "name": "Ealing City Council 105",
        "sector": "Local Government",
        "url": "https://www.ealing.gov.uk"
    },
    {
        "name": "Hounslow City Council 106",
        "sector": "Local Government",
        "url": "https://www.hounslow.gov.uk"
    },
    {
        "name": "Richmond City Council 107",
        "sector": "Local Government",
        "url": "https://www.richmond.gov.uk"
    },
    {
        "name": "Kingston City Council 108",
        "sector": "Local Government",
        "url": "https://www.kingston.gov.uk"
    },
    {
        "name": "Merton City Council 109",
        "sector": "Local Government",
        "url": "https://www.merton.gov.uk"
    },
    {
        "name": "Sutton City Council 110",
        "sector": "Local Government",
        "url": "https://www.sutton.gov.uk"
    },
    {
        "name": "Croydon City Council 111",
        "sector": "Local Government",
        "url": "https://www.croydon.gov.uk"
    },
    {
        "name": "Bromley City Council 112",
        "sector": "Local Government",
        "url": "https://www.bromley.gov.uk"
    },
    {
        "name": "Bexley City Council 113",
        "sector": "Local Government",
        "url": "https://www.bexley.gov.uk"
    },
    {
        "name": "Havering City Council 114",
        "sector": "Local Government",
        "url": "https://www.havering.gov.uk"
    },
    {
        "name": "Barking City Council 115",
        "sector": "Local Government",
        "url": "https://www.barking.gov.uk"
    },
    {
        "name": "Redbridge City Council 116",
        "sector": "Local Government",
        "url": "https://www.redbridge.gov.uk"
    },
    {
        "name": "Newham City Council 117",
        "sector": "Local Government",
        "url": "https://www.newham.gov.uk"
    },
    {
        "name": "Walthamforest City Council 118",
        "sector": "Local Government",
        "url": "https://www.walthamforest.gov.uk"
    },
    {
        "name": "Haringey City Council 119",
        "sector": "Local Government",
        "url": "https://www.haringey.gov.uk"
    },
    {
        "name": "Enfield City Council 120",
        "sector": "Local Government",
        "url": "https://www.enfield.gov.uk"
    },
    {
        "name": "Barnet City Council 121",
        "sector": "Local Government",
        "url": "https://www.barnet.gov.uk"
    },
    {
        "name": "Harrow City Council 122",
        "sector": "Local Government",
        "url": "https://www.harrow.gov.uk"
    },
    {
        "name": "Hillingdon City Council 123",
        "sector": "Local Government",
        "url": "https://www.hillingdon.gov.uk"
    },
    {
        "name": "Aberdeen City Council 124",
        "sector": "Local Government",
        "url": "https://www.aberdeen.gov.uk"
    },
    {
        "name": "Birmingham City Council 125",
        "sector": "Local Government",
        "url": "https://www.birmingham.gov.uk"
    },
    {
        "name": "Bradford City Council 126",
        "sector": "Local Government",
        "url": "https://www.bradford.gov.uk"
    },
    {
        "name": "Brighton City Council 127",
        "sector": "Local Government",
        "url": "https://www.brighton.gov.uk"
    },
    {
        "name": "Bristol City Council 128",
        "sector": "Local Government",
        "url": "https://www.bristol.gov.uk"
    },
    {
        "name": "Cambridge City Council 129",
        "sector": "Local Government",
        "url": "https://www.cambridge.gov.uk"
    },
    {
        "name": "Cardiff City Council 130",
        "sector": "Local Government",
        "url": "https://www.cardiff.gov.uk"
    },
    {
        "name": "Coventry City Council 131",
        "sector": "Local Government",
        "url": "https://www.coventry.gov.uk"
    },
    {
        "name": "Derby City Council 132",
        "sector": "Local Government",
        "url": "https://www.derby.gov.uk"
    },
    {
        "name": "Dundee City Council 133",
        "sector": "Local Government",
        "url": "https://www.dundee.gov.uk"
    },
    {
        "name": "Edinburgh City Council 134",
        "sector": "Local Government",
        "url": "https://www.edinburgh.gov.uk"
    },
    {
        "name": "Glasgow City Council 135",
        "sector": "Local Government",
        "url": "https://www.glasgow.gov.uk"
    },
    {
        "name": "Leeds City Council 136",
        "sector": "Local Government",
        "url": "https://www.leeds.gov.uk"
    },
    {
        "name": "Leicester City Council 137",
        "sector": "Local Government",
        "url": "https://www.leicester.gov.uk"
    },
    {
        "name": "Liverpool City Council 138",
        "sector": "Local Government",
        "url": "https://www.liverpool.gov.uk"
    },
    {
        "name": "Manchester City Council 139",
        "sector": "Local Government",
        "url": "https://www.manchester.gov.uk"
    },
    {
        "name": "Newcastle City Council 140",
        "sector": "Local Government",
        "url": "https://www.newcastle.gov.uk"
    },
    {
        "name": "Newport City Council 141",
        "sector": "Local Government",
        "url": "https://www.newport.gov.uk"
    },
    {
        "name": "Nottingham City Council 142",
        "sector": "Local Government",
        "url": "https://www.nottingham.gov.uk"
    },
    {
        "name": "Oxford City Council 143",
        "sector": "Local Government",
        "url": "https://www.oxford.gov.uk"
    },
    {
        "name": "Plymouth City Council 144",
        "sector": "Local Government",
        "url": "https://www.plymouth.gov.uk"
    },
    {
        "name": "Portsmouth City Council 145",
        "sector": "Local Government",
        "url": "https://www.portsmouth.gov.uk"
    },
    {
        "name": "Sheffield City Council 146",
        "sector": "Local Government",
        "url": "https://www.sheffield.gov.uk"
    },
    {
        "name": "Southampton City Council 147",
        "sector": "Local Government",
        "url": "https://www.southampton.gov.uk"
    },
    {
        "name": "Sunderland City Council 148",
        "sector": "Local Government",
        "url": "https://www.sunderland.gov.uk"
    },
    {
        "name": "Swansea City Council 149",
        "sector": "Local Government",
        "url": "https://www.swansea.gov.uk"
    },
    {
        "name": "Wolverhampton City Council 150",
        "sector": "Local Government",
        "url": "https://www.wolverhampton.gov.uk"
    },
    {
        "name": "York City Council 151",
        "sector": "Local Government",
        "url": "https://www.york.gov.uk"
    },
    {
        "name": "Belfast City Council 152",
        "sector": "Local Government",
        "url": "https://www.belfast.gov.uk"
    },
    {
        "name": "London City Council 153",
        "sector": "Local Government",
        "url": "https://www.london.gov.uk"
    },
    {
        "name": "Westminster City Council 154",
        "sector": "Local Government",
        "url": "https://www.westminster.gov.uk"
    },
    {
        "name": "Camden City Council 155",
        "sector": "Local Government",
        "url": "https://www.camden.gov.uk"
    },
    {
        "name": "Islington City Council 156",
        "sector": "Local Government",
        "url": "https://www.islington.gov.uk"
    },
    {
        "name": "Hackney City Council 157",
        "sector": "Local Government",
        "url": "https://www.hackney.gov.uk"
    },
    {
        "name": "Towerhamlets City Council 158",
        "sector": "Local Government",
        "url": "https://www.towerhamlets.gov.uk"
    },
    {
        "name": "Greenwich City Council 159",
        "sector": "Local Government",
        "url": "https://www.greenwich.gov.uk"
    },
    {
        "name": "Lewisham City Council 160",
        "sector": "Local Government",
        "url": "https://www.lewisham.gov.uk"
    },
    {
        "name": "Southwark City Council 161",
        "sector": "Local Government",
        "url": "https://www.southwark.gov.uk"
    },
    {
        "name": "Lambeth City Council 162",
        "sector": "Local Government",
        "url": "https://www.lambeth.gov.uk"
    },
    {
        "name": "Wandsworth City Council 163",
        "sector": "Local Government",
        "url": "https://www.wandsworth.gov.uk"
    },
    {
        "name": "Hammersmith City Council 164",
        "sector": "Local Government",
        "url": "https://www.hammersmith.gov.uk"
    },
    {
        "name": "Kensington City Council 165",
        "sector": "Local Government",
        "url": "https://www.kensington.gov.uk"
    },
    {
        "name": "Brent City Council 166",
        "sector": "Local Government",
        "url": "https://www.brent.gov.uk"
    },
    {
        "name": "Ealing City Council 167",
        "sector": "Local Government",
        "url": "https://www.ealing.gov.uk"
    },
    {
        "name": "Hounslow City Council 168",
        "sector": "Local Government",
        "url": "https://www.hounslow.gov.uk"
    },
    {
        "name": "Richmond City Council 169",
        "sector": "Local Government",
        "url": "https://www.richmond.gov.uk"
    },
    {
        "name": "Kingston City Council 170",
        "sector": "Local Government",
        "url": "https://www.kingston.gov.uk"
    },
    {
        "name": "Merton City Council 171",
        "sector": "Local Government",
        "url": "https://www.merton.gov.uk"
    },
    {
        "name": "Sutton City Council 172",
        "sector": "Local Government",
        "url": "https://www.sutton.gov.uk"
    },
    {
        "name": "Croydon City Council 173",
        "sector": "Local Government",
        "url": "https://www.croydon.gov.uk"
    },
    {
        "name": "Bromley City Council 174",
        "sector": "Local Government",
        "url": "https://www.bromley.gov.uk"
    },
    {
        "name": "Bexley City Council 175",
        "sector": "Local Government",
        "url": "https://www.bexley.gov.uk"
    },
    {
        "name": "Havering City Council 176",
        "sector": "Local Government",
        "url": "https://www.havering.gov.uk"
    },
    {
        "name": "Barking City Council 177",
        "sector": "Local Government",
        "url": "https://www.barking.gov.uk"
    },
    {
        "name": "Redbridge City Council 178",
        "sector": "Local Government",
        "url": "https://www.redbridge.gov.uk"
    },
    {
        "name": "Newham City Council 179",
        "sector": "Local Government",
        "url": "https://www.newham.gov.uk"
    },
    {
        "name": "Walthamforest City Council 180",
        "sector": "Local Government",
        "url": "https://www.walthamforest.gov.uk"
    },
    {
        "name": "Haringey City Council 181",
        "sector": "Local Government",
        "url": "https://www.haringey.gov.uk"
    },
    {
        "name": "Enfield City Council 182",
        "sector": "Local Government",
        "url": "https://www.enfield.gov.uk"
    },
    {
        "name": "Barnet City Council 183",
        "sector": "Local Government",
        "url": "https://www.barnet.gov.uk"
    },
    {
        "name": "Harrow City Council 184",
        "sector": "Local Government",
        "url": "https://www.harrow.gov.uk"
    },
    {
        "name": "Hillingdon City Council 185",
        "sector": "Local Government",
        "url": "https://www.hillingdon.gov.uk"
    },
    {
        "name": "Aberdeen City Council 186",
        "sector": "Local Government",
        "url": "https://www.aberdeen.gov.uk"
    },
    {
        "name": "Birmingham City Council 187",
        "sector": "Local Government",
        "url": "https://www.birmingham.gov.uk"
    },
    {
        "name": "Bradford City Council 188",
        "sector": "Local Government",
        "url": "https://www.bradford.gov.uk"
    },
    {
        "name": "Brighton City Council 189",
        "sector": "Local Government",
        "url": "https://www.brighton.gov.uk"
    },
    {
        "name": "Bristol City Council 190",
        "sector": "Local Government",
        "url": "https://www.bristol.gov.uk"
    },
    {
        "name": "Cambridge City Council 191",
        "sector": "Local Government",
        "url": "https://www.cambridge.gov.uk"
    },
    {
        "name": "Cardiff City Council 192",
        "sector": "Local Government",
        "url": "https://www.cardiff.gov.uk"
    },
    {
        "name": "Coventry City Council 193",
        "sector": "Local Government",
        "url": "https://www.coventry.gov.uk"
    },
    {
        "name": "Derby City Council 194",
        "sector": "Local Government",
        "url": "https://www.derby.gov.uk"
    },
    {
        "name": "Dundee City Council 195",
        "sector": "Local Government",
        "url": "https://www.dundee.gov.uk"
    },
    {
        "name": "Edinburgh City Council 196",
        "sector": "Local Government",
        "url": "https://www.edinburgh.gov.uk"
    },
    {
        "name": "Glasgow City Council 197",
        "sector": "Local Government",
        "url": "https://www.glasgow.gov.uk"
    },
    {
        "name": "Leeds City Council 198",
        "sector": "Local Government",
        "url": "https://www.leeds.gov.uk"
    },
    {
        "name": "Leicester City Council 199",
        "sector": "Local Government",
        "url": "https://www.leicester.gov.uk"
    },
    {
        "name": "Liverpool City Council 200",
        "sector": "Local Government",
        "url": "https://www.liverpool.gov.uk"
    },
    {
        "name": "Manchester City Council 201",
        "sector": "Local Government",
        "url": "https://www.manchester.gov.uk"
    },
    {
        "name": "Newcastle City Council 202",
        "sector": "Local Government",
        "url": "https://www.newcastle.gov.uk"
    },
    {
        "name": "Newport City Council 203",
        "sector": "Local Government",
        "url": "https://www.newport.gov.uk"
    },
    {
        "name": "Nottingham City Council 204",
        "sector": "Local Government",
        "url": "https://www.nottingham.gov.uk"
    },
    {
        "name": "Oxford City Council 205",
        "sector": "Local Government",
        "url": "https://www.oxford.gov.uk"
    },
    {
        "name": "Plymouth City Council 206",
        "sector": "Local Government",
        "url": "https://www.plymouth.gov.uk"
    },
    {
        "name": "Portsmouth City Council 207",
        "sector": "Local Government",
        "url": "https://www.portsmouth.gov.uk"
    },
    {
        "name": "Sheffield City Council 208",
        "sector": "Local Government",
        "url": "https://www.sheffield.gov.uk"
    },
    {
        "name": "Southampton City Council 209",
        "sector": "Local Government",
        "url": "https://www.southampton.gov.uk"
    },
    {
        "name": "Sunderland City Council 210",
        "sector": "Local Government",
        "url": "https://www.sunderland.gov.uk"
    },
    {
        "name": "Swansea City Council 211",
        "sector": "Local Government",
        "url": "https://www.swansea.gov.uk"
    },
    {
        "name": "Wolverhampton City Council 212",
        "sector": "Local Government",
        "url": "https://www.wolverhampton.gov.uk"
    },
    {
        "name": "York City Council 213",
        "sector": "Local Government",
        "url": "https://www.york.gov.uk"
    },
    {
        "name": "Belfast City Council 214",
        "sector": "Local Government",
        "url": "https://www.belfast.gov.uk"
    },
    {
        "name": "London City Council 215",
        "sector": "Local Government",
        "url": "https://www.london.gov.uk"
    },
    {
        "name": "Westminster City Council 216",
        "sector": "Local Government",
        "url": "https://www.westminster.gov.uk"
    },
    {
        "name": "Camden City Council 217",
        "sector": "Local Government",
        "url": "https://www.camden.gov.uk"
    },
    {
        "name": "Islington City Council 218",
        "sector": "Local Government",
        "url": "https://www.islington.gov.uk"
    },
    {
        "name": "Hackney City Council 219",
        "sector": "Local Government",
        "url": "https://www.hackney.gov.uk"
    },
    {
        "name": "Towerhamlets City Council 220",
        "sector": "Local Government",
        "url": "https://www.towerhamlets.gov.uk"
    },
    {
        "name": "Greenwich City Council 221",
        "sector": "Local Government",
        "url": "https://www.greenwich.gov.uk"
    },
    {
        "name": "Lewisham City Council 222",
        "sector": "Local Government",
        "url": "https://www.lewisham.gov.uk"
    },
    {
        "name": "Southwark City Council 223",
        "sector": "Local Government",
        "url": "https://www.southwark.gov.uk"
    },
    {
        "name": "Lambeth City Council 224",
        "sector": "Local Government",
        "url": "https://www.lambeth.gov.uk"
    },
    {
        "name": "Wandsworth City Council 225",
        "sector": "Local Government",
        "url": "https://www.wandsworth.gov.uk"
    },
    {
        "name": "Hammersmith City Council 226",
        "sector": "Local Government",
        "url": "https://www.hammersmith.gov.uk"
    },
    {
        "name": "Kensington City Council 227",
        "sector": "Local Government",
        "url": "https://www.kensington.gov.uk"
    },
    {
        "name": "Brent City Council 228",
        "sector": "Local Government",
        "url": "https://www.brent.gov.uk"
    },
    {
        "name": "Ealing City Council 229",
        "sector": "Local Government",
        "url": "https://www.ealing.gov.uk"
    },
    {
        "name": "Hounslow City Council 230",
        "sector": "Local Government",
        "url": "https://www.hounslow.gov.uk"
    },
    {
        "name": "Richmond City Council 231",
        "sector": "Local Government",
        "url": "https://www.richmond.gov.uk"
    },
    {
        "name": "Kingston City Council 232",
        "sector": "Local Government",
        "url": "https://www.kingston.gov.uk"
    },
    {
        "name": "Merton City Council 233",
        "sector": "Local Government",
        "url": "https://www.merton.gov.uk"
    },
    {
        "name": "Sutton City Council 234",
        "sector": "Local Government",
        "url": "https://www.sutton.gov.uk"
    },
    {
        "name": "Croydon City Council 235",
        "sector": "Local Government",
        "url": "https://www.croydon.gov.uk"
    },
    {
        "name": "Bromley City Council 236",
        "sector": "Local Government",
        "url": "https://www.bromley.gov.uk"
    },
    {
        "name": "Bexley City Council 237",
        "sector": "Local Government",
        "url": "https://www.bexley.gov.uk"
    },
    {
        "name": "Havering City Council 238",
        "sector": "Local Government",
        "url": "https://www.havering.gov.uk"
    },
    {
        "name": "Barking City Council 239",
        "sector": "Local Government",
        "url": "https://www.barking.gov.uk"
    },
    {
        "name": "Redbridge City Council 240",
        "sector": "Local Government",
        "url": "https://www.redbridge.gov.uk"
    },
    {
        "name": "Newham City Council 241",
        "sector": "Local Government",
        "url": "https://www.newham.gov.uk"
    },
    {
        "name": "Walthamforest City Council 242",
        "sector": "Local Government",
        "url": "https://www.walthamforest.gov.uk"
    },
    {
        "name": "Haringey City Council 243",
        "sector": "Local Government",
        "url": "https://www.haringey.gov.uk"
    },
    {
        "name": "Enfield City Council 244",
        "sector": "Local Government",
        "url": "https://www.enfield.gov.uk"
    },
    {
        "name": "Barnet City Council 245",
        "sector": "Local Government",
        "url": "https://www.barnet.gov.uk"
    },
    {
        "name": "Harrow City Council 246",
        "sector": "Local Government",
        "url": "https://www.harrow.gov.uk"
    },
    {
        "name": "Hillingdon City Council 247",
        "sector": "Local Government",
        "url": "https://www.hillingdon.gov.uk"
    },
    {
        "name": "Aberdeen City Council 248",
        "sector": "Local Government",
        "url": "https://www.aberdeen.gov.uk"
    },
    {
        "name": "Birmingham City Council 249",
        "sector": "Local Government",
        "url": "https://www.birmingham.gov.uk"
    },
    {
        "name": "Bradford City Council 250",
        "sector": "Local Government",
        "url": "https://www.bradford.gov.uk"
    },
    {
        "name": "Brighton City Council 251",
        "sector": "Local Government",
        "url": "https://www.brighton.gov.uk"
    },
    {
        "name": "Bristol City Council 252",
        "sector": "Local Government",
        "url": "https://www.bristol.gov.uk"
    },
    {
        "name": "Cambridge City Council 253",
        "sector": "Local Government",
        "url": "https://www.cambridge.gov.uk"
    },
    {
        "name": "Cardiff City Council 254",
        "sector": "Local Government",
        "url": "https://www.cardiff.gov.uk"
    },
    {
        "name": "Coventry City Council 255",
        "sector": "Local Government",
        "url": "https://www.coventry.gov.uk"
    },
    {
        "name": "Derby City Council 256",
        "sector": "Local Government",
        "url": "https://www.derby.gov.uk"
    },
    {
        "name": "Dundee City Council 257",
        "sector": "Local Government",
        "url": "https://www.dundee.gov.uk"
    },
    {
        "name": "Edinburgh City Council 258",
        "sector": "Local Government",
        "url": "https://www.edinburgh.gov.uk"
    },
    {
        "name": "Glasgow City Council 259",
        "sector": "Local Government",
        "url": "https://www.glasgow.gov.uk"
    },
    {
        "name": "Leeds City Council 260",
        "sector": "Local Government",
        "url": "https://www.leeds.gov.uk"
    },
    {
        "name": "Leicester City Council 261",
        "sector": "Local Government",
        "url": "https://www.leicester.gov.uk"
    },
    {
        "name": "Liverpool City Council 262",
        "sector": "Local Government",
        "url": "https://www.liverpool.gov.uk"
    },
    {
        "name": "Manchester City Council 263",
        "sector": "Local Government",
        "url": "https://www.manchester.gov.uk"
    },
    {
        "name": "Newcastle City Council 264",
        "sector": "Local Government",
        "url": "https://www.newcastle.gov.uk"
    },
    {
        "name": "Newport City Council 265",
        "sector": "Local Government",
        "url": "https://www.newport.gov.uk"
    },
    {
        "name": "Nottingham City Council 266",
        "sector": "Local Government",
        "url": "https://www.nottingham.gov.uk"
    },
    {
        "name": "Oxford City Council 267",
        "sector": "Local Government",
        "url": "https://www.oxford.gov.uk"
    },
    {
        "name": "Plymouth City Council 268",
        "sector": "Local Government",
        "url": "https://www.plymouth.gov.uk"
    },
    {
        "name": "Portsmouth City Council 269",
        "sector": "Local Government",
        "url": "https://www.portsmouth.gov.uk"
    },
    {
        "name": "Sheffield City Council 270",
        "sector": "Local Government",
        "url": "https://www.sheffield.gov.uk"
    },
    {
        "name": "Southampton City Council 271",
        "sector": "Local Government",
        "url": "https://www.southampton.gov.uk"
    },
    {
        "name": "Sunderland City Council 272",
        "sector": "Local Government",
        "url": "https://www.sunderland.gov.uk"
    },
    {
        "name": "Swansea City Council 273",
        "sector": "Local Government",
        "url": "https://www.swansea.gov.uk"
    },
    {
        "name": "Wolverhampton City Council 274",
        "sector": "Local Government",
        "url": "https://www.wolverhampton.gov.uk"
    },
    {
        "name": "York City Council 275",
        "sector": "Local Government",
        "url": "https://www.york.gov.uk"
    },
    {
        "name": "Belfast City Council 276",
        "sector": "Local Government",
        "url": "https://www.belfast.gov.uk"
    },
    {
        "name": "London City Council 277",
        "sector": "Local Government",
        "url": "https://www.london.gov.uk"
    },
    {
        "name": "Westminster City Council 278",
        "sector": "Local Government",
        "url": "https://www.westminster.gov.uk"
    },
    {
        "name": "Camden City Council 279",
        "sector": "Local Government",
        "url": "https://www.camden.gov.uk"
    },
    {
        "name": "Islington City Council 280",
        "sector": "Local Government",
        "url": "https://www.islington.gov.uk"
    },
    {
        "name": "Hackney City Council 281",
        "sector": "Local Government",
        "url": "https://www.hackney.gov.uk"
    },
    {
        "name": "Towerhamlets City Council 282",
        "sector": "Local Government",
        "url": "https://www.towerhamlets.gov.uk"
    },
    {
        "name": "Greenwich City Council 283",
        "sector": "Local Government",
        "url": "https://www.greenwich.gov.uk"
    },
    {
        "name": "Lewisham City Council 284",
        "sector": "Local Government",
        "url": "https://www.lewisham.gov.uk"
    },
    {
        "name": "Southwark City Council 285",
        "sector": "Local Government",
        "url": "https://www.southwark.gov.uk"
    },
    {
        "name": "Lambeth City Council 286",
        "sector": "Local Government",
        "url": "https://www.lambeth.gov.uk"
    },
    {
        "name": "Wandsworth City Council 287",
        "sector": "Local Government",
        "url": "https://www.wandsworth.gov.uk"
    },
    {
        "name": "Hammersmith City Council 288",
        "sector": "Local Government",
        "url": "https://www.hammersmith.gov.uk"
    },
    {
        "name": "Kensington City Council 289",
        "sector": "Local Government",
        "url": "https://www.kensington.gov.uk"
    },
    {
        "name": "Brent City Council 290",
        "sector": "Local Government",
        "url": "https://www.brent.gov.uk"
    },
    {
        "name": "Ealing City Council 291",
        "sector": "Local Government",
        "url": "https://www.ealing.gov.uk"
    },
    {
        "name": "Hounslow City Council 292",
        "sector": "Local Government",
        "url": "https://www.hounslow.gov.uk"
    },
    {
        "name": "Richmond City Council 293",
        "sector": "Local Government",
        "url": "https://www.richmond.gov.uk"
    },
    {
        "name": "Kingston City Council 294",
        "sector": "Local Government",
        "url": "https://www.kingston.gov.uk"
    },
    {
        "name": "Merton City Council 295",
        "sector": "Local Government",
        "url": "https://www.merton.gov.uk"
    },
    {
        "name": "Sutton City Council 296",
        "sector": "Local Government",
        "url": "https://www.sutton.gov.uk"
    },
    {
        "name": "Croydon City Council 297",
        "sector": "Local Government",
        "url": "https://www.croydon.gov.uk"
    },
    {
        "name": "Bromley City Council 298",
        "sector": "Local Government",
        "url": "https://www.bromley.gov.uk"
    },
    {
        "name": "Bexley City Council 299",
        "sector": "Local Government",
        "url": "https://www.bexley.gov.uk"
    },
    {
        "name": "Havering City Council 300",
        "sector": "Local Government",
        "url": "https://www.havering.gov.uk"
    },
    {
        "name": "Barking City Council 301",
        "sector": "Local Government",
        "url": "https://www.barking.gov.uk"
    },
    {
        "name": "Redbridge City Council 302",
        "sector": "Local Government",
        "url": "https://www.redbridge.gov.uk"
    },
    {
        "name": "Newham City Council 303",
        "sector": "Local Government",
        "url": "https://www.newham.gov.uk"
    },
    {
        "name": "Walthamforest City Council 304",
        "sector": "Local Government",
        "url": "https://www.walthamforest.gov.uk"
    },
    {
        "name": "Haringey City Council 305",
        "sector": "Local Government",
        "url": "https://www.haringey.gov.uk"
    },
    {
        "name": "Enfield City Council 306",
        "sector": "Local Government",
        "url": "https://www.enfield.gov.uk"
    },
    {
        "name": "Barnet City Council 307",
        "sector": "Local Government",
        "url": "https://www.barnet.gov.uk"
    },
    {
        "name": "Harrow City Council 308",
        "sector": "Local Government",
        "url": "https://www.harrow.gov.uk"
    },
    {
        "name": "Hillingdon City Council 309",
        "sector": "Local Government",
        "url": "https://www.hillingdon.gov.uk"
    },
    {
        "name": "Aberdeen City Council 310",
        "sector": "Local Government",
        "url": "https://www.aberdeen.gov.uk"
    },
    {
        "name": "Birmingham City Council 311",
        "sector": "Local Government",
        "url": "https://www.birmingham.gov.uk"
    },
    {
        "name": "Bradford City Council 312",
        "sector": "Local Government",
        "url": "https://www.bradford.gov.uk"
    },
    {
        "name": "Brighton City Council 313",
        "sector": "Local Government",
        "url": "https://www.brighton.gov.uk"
    },
    {
        "name": "Bristol City Council 314",
        "sector": "Local Government",
        "url": "https://www.bristol.gov.uk"
    },
    {
        "name": "Cambridge City Council 315",
        "sector": "Local Government",
        "url": "https://www.cambridge.gov.uk"
    },
    {
        "name": "Cardiff City Council 316",
        "sector": "Local Government",
        "url": "https://www.cardiff.gov.uk"
    },
    {
        "name": "Coventry City Council 317",
        "sector": "Local Government",
        "url": "https://www.coventry.gov.uk"
    },
    {
        "name": "Derby City Council 318",
        "sector": "Local Government",
        "url": "https://www.derby.gov.uk"
    },
    {
        "name": "Dundee City Council 319",
        "sector": "Local Government",
        "url": "https://www.dundee.gov.uk"
    },
    {
        "name": "Edinburgh City Council 320",
        "sector": "Local Government",
        "url": "https://www.edinburgh.gov.uk"
    },
    {
        "name": "Glasgow City Council 321",
        "sector": "Local Government",
        "url": "https://www.glasgow.gov.uk"
    },
    {
        "name": "Leeds City Council 322",
        "sector": "Local Government",
        "url": "https://www.leeds.gov.uk"
    },
    {
        "name": "Leicester City Council 323",
        "sector": "Local Government",
        "url": "https://www.leicester.gov.uk"
    },
    {
        "name": "Liverpool City Council 324",
        "sector": "Local Government",
        "url": "https://www.liverpool.gov.uk"
    },
    {
        "name": "Manchester City Council 325",
        "sector": "Local Government",
        "url": "https://www.manchester.gov.uk"
    },
    {
        "name": "Newcastle City Council 326",
        "sector": "Local Government",
        "url": "https://www.newcastle.gov.uk"
    },
    {
        "name": "Newport City Council 327",
        "sector": "Local Government",
        "url": "https://www.newport.gov.uk"
    },
    {
        "name": "Nottingham City Council 328",
        "sector": "Local Government",
        "url": "https://www.nottingham.gov.uk"
    },
    {
        "name": "Oxford City Council 329",
        "sector": "Local Government",
        "url": "https://www.oxford.gov.uk"
    },
    {
        "name": "Plymouth City Council 330",
        "sector": "Local Government",
        "url": "https://www.plymouth.gov.uk"
    },
    {
        "name": "Portsmouth City Council 331",
        "sector": "Local Government",
        "url": "https://www.portsmouth.gov.uk"
    },
    {
        "name": "Sheffield City Council 332",
        "sector": "Local Government",
        "url": "https://www.sheffield.gov.uk"
    },
    {
        "name": "Southampton City Council 333",
        "sector": "Local Government",
        "url": "https://www.southampton.gov.uk"
    },
    {
        "name": "Sunderland City Council 334",
        "sector": "Local Government",
        "url": "https://www.sunderland.gov.uk"
    },
    {
        "name": "Swansea City Council 335",
        "sector": "Local Government",
        "url": "https://www.swansea.gov.uk"
    },
    {
        "name": "Wolverhampton City Council 336",
        "sector": "Local Government",
        "url": "https://www.wolverhampton.gov.uk"
    },
    {
        "name": "York City Council 337",
        "sector": "Local Government",
        "url": "https://www.york.gov.uk"
    },
    {
        "name": "Belfast City Council 338",
        "sector": "Local Government",
        "url": "https://www.belfast.gov.uk"
    },
    {
        "name": "London City Council 339",
        "sector": "Local Government",
        "url": "https://www.london.gov.uk"
    },
    {
        "name": "Westminster City Council 340",
        "sector": "Local Government",
        "url": "https://www.westminster.gov.uk"
    },
    {
        "name": "Camden City Council 341",
        "sector": "Local Government",
        "url": "https://www.camden.gov.uk"
    },
    {
        "name": "Islington City Council 342",
        "sector": "Local Government",
        "url": "https://www.islington.gov.uk"
    },
    {
        "name": "Hackney City Council 343",
        "sector": "Local Government",
        "url": "https://www.hackney.gov.uk"
    },
    {
        "name": "Towerhamlets City Council 344",
        "sector": "Local Government",
        "url": "https://www.towerhamlets.gov.uk"
    },
    {
        "name": "Greenwich City Council 345",
        "sector": "Local Government",
        "url": "https://www.greenwich.gov.uk"
    },
    {
        "name": "Lewisham City Council 346",
        "sector": "Local Government",
        "url": "https://www.lewisham.gov.uk"
    },
    {
        "name": "Southwark City Council 347",
        "sector": "Local Government",
        "url": "https://www.southwark.gov.uk"
    },
    {
        "name": "Lambeth City Council 348",
        "sector": "Local Government",
        "url": "https://www.lambeth.gov.uk"
    },
    {
        "name": "Wandsworth City Council 349",
        "sector": "Local Government",
        "url": "https://www.wandsworth.gov.uk"
    },
    {
        "name": "Hammersmith City Council 350",
        "sector": "Local Government",
        "url": "https://www.hammersmith.gov.uk"
    },
    {
        "name": "Kensington City Council 351",
        "sector": "Local Government",
        "url": "https://www.kensington.gov.uk"
    },
    {
        "name": "Brent City Council 352",
        "sector": "Local Government",
        "url": "https://www.brent.gov.uk"
    },
    {
        "name": "Ealing City Council 353",
        "sector": "Local Government",
        "url": "https://www.ealing.gov.uk"
    },
    {
        "name": "Hounslow City Council 354",
        "sector": "Local Government",
        "url": "https://www.hounslow.gov.uk"
    },
    {
        "name": "Richmond City Council 355",
        "sector": "Local Government",
        "url": "https://www.richmond.gov.uk"
    },
    {
        "name": "Kingston City Council 356",
        "sector": "Local Government",
        "url": "https://www.kingston.gov.uk"
    },
    {
        "name": "Merton City Council 357",
        "sector": "Local Government",
        "url": "https://www.merton.gov.uk"
    },
    {
        "name": "Sutton City Council 358",
        "sector": "Local Government",
        "url": "https://www.sutton.gov.uk"
    },
    {
        "name": "Croydon City Council 359",
        "sector": "Local Government",
        "url": "https://www.croydon.gov.uk"
    },
    {
        "name": "Bromley City Council 360",
        "sector": "Local Government",
        "url": "https://www.bromley.gov.uk"
    },
    {
        "name": "Bexley City Council 361",
        "sector": "Local Government",
        "url": "https://www.bexley.gov.uk"
    },
    {
        "name": "Havering City Council 362",
        "sector": "Local Government",
        "url": "https://www.havering.gov.uk"
    },
    {
        "name": "Barking City Council 363",
        "sector": "Local Government",
        "url": "https://www.barking.gov.uk"
    },
    {
        "name": "Redbridge City Council 364",
        "sector": "Local Government",
        "url": "https://www.redbridge.gov.uk"
    },
    {
        "name": "Newham City Council 365",
        "sector": "Local Government",
        "url": "https://www.newham.gov.uk"
    },
    {
        "name": "Walthamforest City Council 366",
        "sector": "Local Government",
        "url": "https://www.walthamforest.gov.uk"
    },
    {
        "name": "Haringey City Council 367",
        "sector": "Local Government",
        "url": "https://www.haringey.gov.uk"
    },
    {
        "name": "Enfield City Council 368",
        "sector": "Local Government",
        "url": "https://www.enfield.gov.uk"
    },
    {
        "name": "Barnet City Council 369",
        "sector": "Local Government",
        "url": "https://www.barnet.gov.uk"
    },
    {
        "name": "Harrow City Council 370",
        "sector": "Local Government",
        "url": "https://www.harrow.gov.uk"
    },
    {
        "name": "Hillingdon City Council 371",
        "sector": "Local Government",
        "url": "https://www.hillingdon.gov.uk"
    },
    {
        "name": "Aberdeen City Council 372",
        "sector": "Local Government",
        "url": "https://www.aberdeen.gov.uk"
    },
    {
        "name": "Birmingham City Council 373",
        "sector": "Local Government",
        "url": "https://www.birmingham.gov.uk"
    },
    {
        "name": "Bradford City Council 374",
        "sector": "Local Government",
        "url": "https://www.bradford.gov.uk"
    },
    {
        "name": "Brighton City Council 375",
        "sector": "Local Government",
        "url": "https://www.brighton.gov.uk"
    },
    {
        "name": "Bristol City Council 376",
        "sector": "Local Government",
        "url": "https://www.bristol.gov.uk"
    },
    {
        "name": "Cambridge City Council 377",
        "sector": "Local Government",
        "url": "https://www.cambridge.gov.uk"
    },
    {
        "name": "Cardiff City Council 378",
        "sector": "Local Government",
        "url": "https://www.cardiff.gov.uk"
    },
    {
        "name": "Coventry City Council 379",
        "sector": "Local Government",
        "url": "https://www.coventry.gov.uk"
    },
    {
        "name": "Derby City Council 380",
        "sector": "Local Government",
        "url": "https://www.derby.gov.uk"
    },
    {
        "name": "Dundee City Council 381",
        "sector": "Local Government",
        "url": "https://www.dundee.gov.uk"
    },
    {
        "name": "Edinburgh City Council 382",
        "sector": "Local Government",
        "url": "https://www.edinburgh.gov.uk"
    },
    {
        "name": "Glasgow City Council 383",
        "sector": "Local Government",
        "url": "https://www.glasgow.gov.uk"
    },
    {
        "name": "Leeds City Council 384",
        "sector": "Local Government",
        "url": "https://www.leeds.gov.uk"
    },
    {
        "name": "Leicester City Council 385",
        "sector": "Local Government",
        "url": "https://www.leicester.gov.uk"
    },
    {
        "name": "Liverpool City Council 386",
        "sector": "Local Government",
        "url": "https://www.liverpool.gov.uk"
    },
    {
        "name": "Manchester City Council 387",
        "sector": "Local Government",
        "url": "https://www.manchester.gov.uk"
    },
    {
        "name": "Newcastle City Council 388",
        "sector": "Local Government",
        "url": "https://www.newcastle.gov.uk"
    },
    {
        "name": "Newport City Council 389",
        "sector": "Local Government",
        "url": "https://www.newport.gov.uk"
    },
    {
        "name": "Nottingham City Council 390",
        "sector": "Local Government",
        "url": "https://www.nottingham.gov.uk"
    },
    {
        "name": "Oxford City Council 391",
        "sector": "Local Government",
        "url": "https://www.oxford.gov.uk"
    },
    {
        "name": "Plymouth City Council 392",
        "sector": "Local Government",
        "url": "https://www.plymouth.gov.uk"
    },
    {
        "name": "Portsmouth City Council 393",
        "sector": "Local Government",
        "url": "https://www.portsmouth.gov.uk"
    },
    {
        "name": "Sheffield City Council 394",
        "sector": "Local Government",
        "url": "https://www.sheffield.gov.uk"
    },
    {
        "name": "Southampton City Council 395",
        "sector": "Local Government",
        "url": "https://www.southampton.gov.uk"
    },
    {
        "name": "Sunderland City Council 396",
        "sector": "Local Government",
        "url": "https://www.sunderland.gov.uk"
    },
    {
        "name": "Swansea City Council 397",
        "sector": "Local Government",
        "url": "https://www.swansea.gov.uk"
    },
    {
        "name": "Wolverhampton City Council 398",
        "sector": "Local Government",
        "url": "https://www.wolverhampton.gov.uk"
    },
    {
        "name": "York City Council 399",
        "sector": "Local Government",
        "url": "https://www.york.gov.uk"
    },
    {
        "name": "Stthomas NHS Trust 1",
        "sector": "NHS",
        "url": "https://www.stthomas.nhs.uk"
    },
    {
        "name": "Uclh NHS Trust 2",
        "sector": "NHS",
        "url": "https://www.uclh.nhs.uk"
    },
    {
        "name": "Imperial NHS Trust 3",
        "sector": "NHS",
        "url": "https://www.imperial.nhs.uk"
    },
    {
        "name": "Barts NHS Trust 4",
        "sector": "NHS",
        "url": "https://www.barts.nhs.uk"
    },
    {
        "name": "Kings NHS Trust 5",
        "sector": "NHS",
        "url": "https://www.kings.nhs.uk"
    },
    {
        "name": "Royalfree NHS Trust 6",
        "sector": "NHS",
        "url": "https://www.royalfree.nhs.uk"
    },
    {
        "name": "Georges NHS Trust 7",
        "sector": "NHS",
        "url": "https://www.georges.nhs.uk"
    },
    {
        "name": "Moorfields NHS Trust 8",
        "sector": "NHS",
        "url": "https://www.moorfields.nhs.uk"
    },
    {
        "name": "Gosh NHS Trust 9",
        "sector": "NHS",
        "url": "https://www.gosh.nhs.uk"
    },
    {
        "name": "Royalmarsden NHS Trust 10",
        "sector": "NHS",
        "url": "https://www.royalmarsden.nhs.uk"
    },
    {
        "name": "Brompton NHS Trust 11",
        "sector": "NHS",
        "url": "https://www.brompton.nhs.uk"
    },
    {
        "name": "Chelwest NHS Trust 12",
        "sector": "NHS",
        "url": "https://www.chelwest.nhs.uk"
    },
    {
        "name": "Whittington NHS Trust 13",
        "sector": "NHS",
        "url": "https://www.whittington.nhs.uk"
    },
    {
        "name": "Homerton NHS Trust 14",
        "sector": "NHS",
        "url": "https://www.homerton.nhs.uk"
    },
    {
        "name": "Lewisham NHS Trust 15",
        "sector": "NHS",
        "url": "https://www.lewisham.nhs.uk"
    },
    {
        "name": "Epsom NHS Trust 16",
        "sector": "NHS",
        "url": "https://www.epsom.nhs.uk"
    },
    {
        "name": "Croydon NHS Trust 17",
        "sector": "NHS",
        "url": "https://www.croydon.nhs.uk"
    },
    {
        "name": "Kingston NHS Trust 18",
        "sector": "NHS",
        "url": "https://www.kingston.nhs.uk"
    },
    {
        "name": "Hillingdon NHS Trust 19",
        "sector": "NHS",
        "url": "https://www.hillingdon.nhs.uk"
    },
    {
        "name": "Westmid NHS Trust 20",
        "sector": "NHS",
        "url": "https://www.westmid.nhs.uk"
    },
    {
        "name": "Northmid NHS Trust 21",
        "sector": "NHS",
        "url": "https://www.northmid.nhs.uk"
    },
    {
        "name": "Barking NHS Trust 22",
        "sector": "NHS",
        "url": "https://www.barking.nhs.uk"
    },
    {
        "name": "Basildon NHS Trust 23",
        "sector": "NHS",
        "url": "https://www.basildon.nhs.uk"
    },
    {
        "name": "Southend NHS Trust 24",
        "sector": "NHS",
        "url": "https://www.southend.nhs.uk"
    },
    {
        "name": "Midessex NHS Trust 25",
        "sector": "NHS",
        "url": "https://www.midessex.nhs.uk"
    },
    {
        "name": "Colchester NHS Trust 26",
        "sector": "NHS",
        "url": "https://www.colchester.nhs.uk"
    },
    {
        "name": "Ipswich NHS Trust 27",
        "sector": "NHS",
        "url": "https://www.ipswich.nhs.uk"
    },
    {
        "name": "Norfolk NHS Trust 28",
        "sector": "NHS",
        "url": "https://www.norfolk.nhs.uk"
    },
    {
        "name": "Cambridge NHS Trust 29",
        "sector": "NHS",
        "url": "https://www.cambridge.nhs.uk"
    },
    {
        "name": "Peterborough NHS Trust 30",
        "sector": "NHS",
        "url": "https://www.peterborough.nhs.uk"
    },
    {
        "name": "Bedford NHS Trust 31",
        "sector": "NHS",
        "url": "https://www.bedford.nhs.uk"
    },
    {
        "name": "Luton NHS Trust 32",
        "sector": "NHS",
        "url": "https://www.luton.nhs.uk"
    },
    {
        "name": "Westherts NHS Trust 33",
        "sector": "NHS",
        "url": "https://www.westherts.nhs.uk"
    },
    {
        "name": "Eastherts NHS Trust 34",
        "sector": "NHS",
        "url": "https://www.eastherts.nhs.uk"
    },
    {
        "name": "Surrey NHS Trust 35",
        "sector": "NHS",
        "url": "https://www.surrey.nhs.uk"
    },
    {
        "name": "Sussex NHS Trust 36",
        "sector": "NHS",
        "url": "https://www.sussex.nhs.uk"
    },
    {
        "name": "Kent NHS Trust 37",
        "sector": "NHS",
        "url": "https://www.kent.nhs.uk"
    },
    {
        "name": "Medway NHS Trust 38",
        "sector": "NHS",
        "url": "https://www.medway.nhs.uk"
    },
    {
        "name": "Eastkent NHS Trust 39",
        "sector": "NHS",
        "url": "https://www.eastkent.nhs.uk"
    },
    {
        "name": "Darent NHS Trust 40",
        "sector": "NHS",
        "url": "https://www.darent.nhs.uk"
    },
    {
        "name": "Brighton NHS Trust 41",
        "sector": "NHS",
        "url": "https://www.brighton.nhs.uk"
    },
    {
        "name": "Eastbourne NHS Trust 42",
        "sector": "NHS",
        "url": "https://www.eastbourne.nhs.uk"
    },
    {
        "name": "Hastings NHS Trust 43",
        "sector": "NHS",
        "url": "https://www.hastings.nhs.uk"
    },
    {
        "name": "Portsmouth NHS Trust 44",
        "sector": "NHS",
        "url": "https://www.portsmouth.nhs.uk"
    },
    {
        "name": "Southampton NHS Trust 45",
        "sector": "NHS",
        "url": "https://www.southampton.nhs.uk"
    },
    {
        "name": "Bournemouth NHS Trust 46",
        "sector": "NHS",
        "url": "https://www.bournemouth.nhs.uk"
    },
    {
        "name": "Poole NHS Trust 47",
        "sector": "NHS",
        "url": "https://www.poole.nhs.uk"
    },
    {
        "name": "Dorset NHS Trust 48",
        "sector": "NHS",
        "url": "https://www.dorset.nhs.uk"
    },
    {
        "name": "Salisbury NHS Trust 49",
        "sector": "NHS",
        "url": "https://www.salisbury.nhs.uk"
    },
    {
        "name": "Bath NHS Trust 50",
        "sector": "NHS",
        "url": "https://www.bath.nhs.uk"
    },
    {
        "name": "Bristol NHS Trust 51",
        "sector": "NHS",
        "url": "https://www.bristol.nhs.uk"
    },
    {
        "name": "Gloucester NHS Trust 52",
        "sector": "NHS",
        "url": "https://www.gloucester.nhs.uk"
    },
    {
        "name": "Swindon NHS Trust 53",
        "sector": "NHS",
        "url": "https://www.swindon.nhs.uk"
    },
    {
        "name": "Oxford NHS Trust 54",
        "sector": "NHS",
        "url": "https://www.oxford.nhs.uk"
    },
    {
        "name": "Berkshire NHS Trust 55",
        "sector": "NHS",
        "url": "https://www.berkshire.nhs.uk"
    },
    {
        "name": "Buckinghamshire NHS Trust 56",
        "sector": "NHS",
        "url": "https://www.buckinghamshire.nhs.uk"
    },
    {
        "name": "Miltonkeynes NHS Trust 57",
        "sector": "NHS",
        "url": "https://www.miltonkeynes.nhs.uk"
    },
    {
        "name": "Northampton NHS Trust 58",
        "sector": "NHS",
        "url": "https://www.northampton.nhs.uk"
    },
    {
        "name": "Kettering NHS Trust 59",
        "sector": "NHS",
        "url": "https://www.kettering.nhs.uk"
    },
    {
        "name": "Leicester NHS Trust 60",
        "sector": "NHS",
        "url": "https://www.leicester.nhs.uk"
    },
    {
        "name": "Nottingham NHS Trust 61",
        "sector": "NHS",
        "url": "https://www.nottingham.nhs.uk"
    },
    {
        "name": "Derby NHS Trust 62",
        "sector": "NHS",
        "url": "https://www.derby.nhs.uk"
    },
    {
        "name": "Chesterfield NHS Trust 63",
        "sector": "NHS",
        "url": "https://www.chesterfield.nhs.uk"
    },
    {
        "name": "Lincoln NHS Trust 64",
        "sector": "NHS",
        "url": "https://www.lincoln.nhs.uk"
    },
    {
        "name": "Boston NHS Trust 65",
        "sector": "NHS",
        "url": "https://www.boston.nhs.uk"
    },
    {
        "name": "Sheffield NHS Trust 66",
        "sector": "NHS",
        "url": "https://www.sheffield.nhs.uk"
    },
    {
        "name": "Doncaster NHS Trust 67",
        "sector": "NHS",
        "url": "https://www.doncaster.nhs.uk"
    },
    {
        "name": "Rotherham NHS Trust 68",
        "sector": "NHS",
        "url": "https://www.rotherham.nhs.uk"
    },
    {
        "name": "Barnsley NHS Trust 69",
        "sector": "NHS",
        "url": "https://www.barnsley.nhs.uk"
    },
    {
        "name": "Leeds NHS Trust 70",
        "sector": "NHS",
        "url": "https://www.leeds.nhs.uk"
    },
    {
        "name": "Bradford NHS Trust 71",
        "sector": "NHS",
        "url": "https://www.bradford.nhs.uk"
    },
    {
        "name": "Calderdale NHS Trust 72",
        "sector": "NHS",
        "url": "https://www.calderdale.nhs.uk"
    },
    {
        "name": "Midyorks NHS Trust 73",
        "sector": "NHS",
        "url": "https://www.midyorks.nhs.uk"
    },
    {
        "name": "Harrogate NHS Trust 74",
        "sector": "NHS",
        "url": "https://www.harrogate.nhs.uk"
    },
    {
        "name": "York NHS Trust 75",
        "sector": "NHS",
        "url": "https://www.york.nhs.uk"
    },
    {
        "name": "Hull NHS Trust 76",
        "sector": "NHS",
        "url": "https://www.hull.nhs.uk"
    },
    {
        "name": "Scarborough NHS Trust 77",
        "sector": "NHS",
        "url": "https://www.scarborough.nhs.uk"
    },
    {
        "name": "Tees NHS Trust 78",
        "sector": "NHS",
        "url": "https://www.tees.nhs.uk"
    },
    {
        "name": "Sunderland NHS Trust 79",
        "sector": "NHS",
        "url": "https://www.sunderland.nhs.uk"
    },
    {
        "name": "Gateshead NHS Trust 80",
        "sector": "NHS",
        "url": "https://www.gateshead.nhs.uk"
    },
    {
        "name": "Newcastle NHS Trust 81",
        "sector": "NHS",
        "url": "https://www.newcastle.nhs.uk"
    },
    {
        "name": "Northumbria NHS Trust 82",
        "sector": "NHS",
        "url": "https://www.northumbria.nhs.uk"
    },
    {
        "name": "Cumbria NHS Trust 83",
        "sector": "NHS",
        "url": "https://www.cumbria.nhs.uk"
    },
    {
        "name": "Lancashire NHS Trust 84",
        "sector": "NHS",
        "url": "https://www.lancashire.nhs.uk"
    },
    {
        "name": "Blackpool NHS Trust 85",
        "sector": "NHS",
        "url": "https://www.blackpool.nhs.uk"
    },
    {
        "name": "Preston NHS Trust 86",
        "sector": "NHS",
        "url": "https://www.preston.nhs.uk"
    },
    {
        "name": "Blackburn NHS Trust 87",
        "sector": "NHS",
        "url": "https://www.blackburn.nhs.uk"
    },
    {
        "name": "Bolton NHS Trust 88",
        "sector": "NHS",
        "url": "https://www.bolton.nhs.uk"
    },
    {
        "name": "Bury NHS Trust 89",
        "sector": "NHS",
        "url": "https://www.bury.nhs.uk"
    },
    {
        "name": "Rochdale NHS Trust 90",
        "sector": "NHS",
        "url": "https://www.rochdale.nhs.uk"
    },
    {
        "name": "Oldham NHS Trust 91",
        "sector": "NHS",
        "url": "https://www.oldham.nhs.uk"
    },
    {
        "name": "Salford NHS Trust 92",
        "sector": "NHS",
        "url": "https://www.salford.nhs.uk"
    },
    {
        "name": "Manchester NHS Trust 93",
        "sector": "NHS",
        "url": "https://www.manchester.nhs.uk"
    },
    {
        "name": "Stockport NHS Trust 94",
        "sector": "NHS",
        "url": "https://www.stockport.nhs.uk"
    },
    {
        "name": "Tameside NHS Trust 95",
        "sector": "NHS",
        "url": "https://www.tameside.nhs.uk"
    },
    {
        "name": "Trafford NHS Trust 96",
        "sector": "NHS",
        "url": "https://www.trafford.nhs.uk"
    },
    {
        "name": "Wigan NHS Trust 97",
        "sector": "NHS",
        "url": "https://www.wigan.nhs.uk"
    },
    {
        "name": "Mersey NHS Trust 98",
        "sector": "NHS",
        "url": "https://www.mersey.nhs.uk"
    },
    {
        "name": "Liverpool NHS Trust 99",
        "sector": "NHS",
        "url": "https://www.liverpool.nhs.uk"
    },
    {
        "name": "Wirral NHS Trust 100",
        "sector": "NHS",
        "url": "https://www.wirral.nhs.uk"
    },
    {
        "name": "Chester NHS Trust 101",
        "sector": "NHS",
        "url": "https://www.chester.nhs.uk"
    },
    {
        "name": "Midcheshire NHS Trust 102",
        "sector": "NHS",
        "url": "https://www.midcheshire.nhs.uk"
    },
    {
        "name": "Eastcheshire NHS Trust 103",
        "sector": "NHS",
        "url": "https://www.eastcheshire.nhs.uk"
    },
    {
        "name": "Stafford NHS Trust 104",
        "sector": "NHS",
        "url": "https://www.stafford.nhs.uk"
    },
    {
        "name": "Stoke NHS Trust 105",
        "sector": "NHS",
        "url": "https://www.stoke.nhs.uk"
    },
    {
        "name": "Shrewsbury NHS Trust 106",
        "sector": "NHS",
        "url": "https://www.shrewsbury.nhs.uk"
    },
    {
        "name": "Telford NHS Trust 107",
        "sector": "NHS",
        "url": "https://www.telford.nhs.uk"
    },
    {
        "name": "Wolverhampton NHS Trust 108",
        "sector": "NHS",
        "url": "https://www.wolverhampton.nhs.uk"
    },
    {
        "name": "Walsall NHS Trust 109",
        "sector": "NHS",
        "url": "https://www.walsall.nhs.uk"
    },
    {
        "name": "Dudley NHS Trust 110",
        "sector": "NHS",
        "url": "https://www.dudley.nhs.uk"
    },
    {
        "name": "Sandwell NHS Trust 111",
        "sector": "NHS",
        "url": "https://www.sandwell.nhs.uk"
    },
    {
        "name": "Birmingham NHS Trust 112",
        "sector": "NHS",
        "url": "https://www.birmingham.nhs.uk"
    },
    {
        "name": "Solihull NHS Trust 113",
        "sector": "NHS",
        "url": "https://www.solihull.nhs.uk"
    },
    {
        "name": "Coventry NHS Trust 114",
        "sector": "NHS",
        "url": "https://www.coventry.nhs.uk"
    },
    {
        "name": "Warwick NHS Trust 115",
        "sector": "NHS",
        "url": "https://www.warwick.nhs.uk"
    },
    {
        "name": "Worcester NHS Trust 116",
        "sector": "NHS",
        "url": "https://www.worcester.nhs.uk"
    },
    {
        "name": "Hereford NHS Trust 117",
        "sector": "NHS",
        "url": "https://www.hereford.nhs.uk"
    },
    {
        "name": "Guys NHS Trust 118",
        "sector": "NHS",
        "url": "https://www.guys.nhs.uk"
    },
    {
        "name": "Stthomas NHS Trust 119",
        "sector": "NHS",
        "url": "https://www.stthomas.nhs.uk"
    },
    {
        "name": "Uclh NHS Trust 120",
        "sector": "NHS",
        "url": "https://www.uclh.nhs.uk"
    },
    {
        "name": "Imperial NHS Trust 121",
        "sector": "NHS",
        "url": "https://www.imperial.nhs.uk"
    },
    {
        "name": "Barts NHS Trust 122",
        "sector": "NHS",
        "url": "https://www.barts.nhs.uk"
    },
    {
        "name": "Kings NHS Trust 123",
        "sector": "NHS",
        "url": "https://www.kings.nhs.uk"
    },
    {
        "name": "Royalfree NHS Trust 124",
        "sector": "NHS",
        "url": "https://www.royalfree.nhs.uk"
    },
    {
        "name": "Georges NHS Trust 125",
        "sector": "NHS",
        "url": "https://www.georges.nhs.uk"
    },
    {
        "name": "Moorfields NHS Trust 126",
        "sector": "NHS",
        "url": "https://www.moorfields.nhs.uk"
    },
    {
        "name": "Gosh NHS Trust 127",
        "sector": "NHS",
        "url": "https://www.gosh.nhs.uk"
    },
    {
        "name": "Royalmarsden NHS Trust 128",
        "sector": "NHS",
        "url": "https://www.royalmarsden.nhs.uk"
    },
    {
        "name": "Brompton NHS Trust 129",
        "sector": "NHS",
        "url": "https://www.brompton.nhs.uk"
    },
    {
        "name": "Chelwest NHS Trust 130",
        "sector": "NHS",
        "url": "https://www.chelwest.nhs.uk"
    },
    {
        "name": "Whittington NHS Trust 131",
        "sector": "NHS",
        "url": "https://www.whittington.nhs.uk"
    },
    {
        "name": "Homerton NHS Trust 132",
        "sector": "NHS",
        "url": "https://www.homerton.nhs.uk"
    },
    {
        "name": "Lewisham NHS Trust 133",
        "sector": "NHS",
        "url": "https://www.lewisham.nhs.uk"
    },
    {
        "name": "Epsom NHS Trust 134",
        "sector": "NHS",
        "url": "https://www.epsom.nhs.uk"
    },
    {
        "name": "Croydon NHS Trust 135",
        "sector": "NHS",
        "url": "https://www.croydon.nhs.uk"
    },
    {
        "name": "Kingston NHS Trust 136",
        "sector": "NHS",
        "url": "https://www.kingston.nhs.uk"
    },
    {
        "name": "Hillingdon NHS Trust 137",
        "sector": "NHS",
        "url": "https://www.hillingdon.nhs.uk"
    },
    {
        "name": "Westmid NHS Trust 138",
        "sector": "NHS",
        "url": "https://www.westmid.nhs.uk"
    },
    {
        "name": "Northmid NHS Trust 139",
        "sector": "NHS",
        "url": "https://www.northmid.nhs.uk"
    },
    {
        "name": "Barking NHS Trust 140",
        "sector": "NHS",
        "url": "https://www.barking.nhs.uk"
    },
    {
        "name": "Basildon NHS Trust 141",
        "sector": "NHS",
        "url": "https://www.basildon.nhs.uk"
    },
    {
        "name": "Southend NHS Trust 142",
        "sector": "NHS",
        "url": "https://www.southend.nhs.uk"
    },
    {
        "name": "Midessex NHS Trust 143",
        "sector": "NHS",
        "url": "https://www.midessex.nhs.uk"
    },
    {
        "name": "Colchester NHS Trust 144",
        "sector": "NHS",
        "url": "https://www.colchester.nhs.uk"
    },
    {
        "name": "Ipswich NHS Trust 145",
        "sector": "NHS",
        "url": "https://www.ipswich.nhs.uk"
    },
    {
        "name": "Norfolk NHS Trust 146",
        "sector": "NHS",
        "url": "https://www.norfolk.nhs.uk"
    },
    {
        "name": "Cambridge NHS Trust 147",
        "sector": "NHS",
        "url": "https://www.cambridge.nhs.uk"
    },
    {
        "name": "Peterborough NHS Trust 148",
        "sector": "NHS",
        "url": "https://www.peterborough.nhs.uk"
    },
    {
        "name": "Bedford NHS Trust 149",
        "sector": "NHS",
        "url": "https://www.bedford.nhs.uk"
    },
    {
        "name": "Luton NHS Trust 150",
        "sector": "NHS",
        "url": "https://www.luton.nhs.uk"
    },
    {
        "name": "Westherts NHS Trust 151",
        "sector": "NHS",
        "url": "https://www.westherts.nhs.uk"
    },
    {
        "name": "Eastherts NHS Trust 152",
        "sector": "NHS",
        "url": "https://www.eastherts.nhs.uk"
    },
    {
        "name": "Surrey NHS Trust 153",
        "sector": "NHS",
        "url": "https://www.surrey.nhs.uk"
    },
    {
        "name": "Sussex NHS Trust 154",
        "sector": "NHS",
        "url": "https://www.sussex.nhs.uk"
    },
    {
        "name": "Kent NHS Trust 155",
        "sector": "NHS",
        "url": "https://www.kent.nhs.uk"
    },
    {
        "name": "Medway NHS Trust 156",
        "sector": "NHS",
        "url": "https://www.medway.nhs.uk"
    },
    {
        "name": "Eastkent NHS Trust 157",
        "sector": "NHS",
        "url": "https://www.eastkent.nhs.uk"
    },
    {
        "name": "Darent NHS Trust 158",
        "sector": "NHS",
        "url": "https://www.darent.nhs.uk"
    },
    {
        "name": "Brighton NHS Trust 159",
        "sector": "NHS",
        "url": "https://www.brighton.nhs.uk"
    },
    {
        "name": "Eastbourne NHS Trust 160",
        "sector": "NHS",
        "url": "https://www.eastbourne.nhs.uk"
    },
    {
        "name": "Hastings NHS Trust 161",
        "sector": "NHS",
        "url": "https://www.hastings.nhs.uk"
    },
    {
        "name": "Portsmouth NHS Trust 162",
        "sector": "NHS",
        "url": "https://www.portsmouth.nhs.uk"
    },
    {
        "name": "Southampton NHS Trust 163",
        "sector": "NHS",
        "url": "https://www.southampton.nhs.uk"
    },
    {
        "name": "Bournemouth NHS Trust 164",
        "sector": "NHS",
        "url": "https://www.bournemouth.nhs.uk"
    },
    {
        "name": "Poole NHS Trust 165",
        "sector": "NHS",
        "url": "https://www.poole.nhs.uk"
    },
    {
        "name": "Dorset NHS Trust 166",
        "sector": "NHS",
        "url": "https://www.dorset.nhs.uk"
    },
    {
        "name": "Salisbury NHS Trust 167",
        "sector": "NHS",
        "url": "https://www.salisbury.nhs.uk"
    },
    {
        "name": "Bath NHS Trust 168",
        "sector": "NHS",
        "url": "https://www.bath.nhs.uk"
    },
    {
        "name": "Bristol NHS Trust 169",
        "sector": "NHS",
        "url": "https://www.bristol.nhs.uk"
    },
    {
        "name": "Gloucester NHS Trust 170",
        "sector": "NHS",
        "url": "https://www.gloucester.nhs.uk"
    },
    {
        "name": "Swindon NHS Trust 171",
        "sector": "NHS",
        "url": "https://www.swindon.nhs.uk"
    },
    {
        "name": "Oxford NHS Trust 172",
        "sector": "NHS",
        "url": "https://www.oxford.nhs.uk"
    },
    {
        "name": "Berkshire NHS Trust 173",
        "sector": "NHS",
        "url": "https://www.berkshire.nhs.uk"
    },
    {
        "name": "Buckinghamshire NHS Trust 174",
        "sector": "NHS",
        "url": "https://www.buckinghamshire.nhs.uk"
    },
    {
        "name": "Miltonkeynes NHS Trust 175",
        "sector": "NHS",
        "url": "https://www.miltonkeynes.nhs.uk"
    },
    {
        "name": "Northampton NHS Trust 176",
        "sector": "NHS",
        "url": "https://www.northampton.nhs.uk"
    },
    {
        "name": "Kettering NHS Trust 177",
        "sector": "NHS",
        "url": "https://www.kettering.nhs.uk"
    },
    {
        "name": "Leicester NHS Trust 178",
        "sector": "NHS",
        "url": "https://www.leicester.nhs.uk"
    },
    {
        "name": "Nottingham NHS Trust 179",
        "sector": "NHS",
        "url": "https://www.nottingham.nhs.uk"
    },
    {
        "name": "Derby NHS Trust 180",
        "sector": "NHS",
        "url": "https://www.derby.nhs.uk"
    },
    {
        "name": "Chesterfield NHS Trust 181",
        "sector": "NHS",
        "url": "https://www.chesterfield.nhs.uk"
    },
    {
        "name": "Lincoln NHS Trust 182",
        "sector": "NHS",
        "url": "https://www.lincoln.nhs.uk"
    },
    {
        "name": "Boston NHS Trust 183",
        "sector": "NHS",
        "url": "https://www.boston.nhs.uk"
    },
    {
        "name": "Sheffield NHS Trust 184",
        "sector": "NHS",
        "url": "https://www.sheffield.nhs.uk"
    },
    {
        "name": "Doncaster NHS Trust 185",
        "sector": "NHS",
        "url": "https://www.doncaster.nhs.uk"
    },
    {
        "name": "Rotherham NHS Trust 186",
        "sector": "NHS",
        "url": "https://www.rotherham.nhs.uk"
    },
    {
        "name": "Barnsley NHS Trust 187",
        "sector": "NHS",
        "url": "https://www.barnsley.nhs.uk"
    },
    {
        "name": "Leeds NHS Trust 188",
        "sector": "NHS",
        "url": "https://www.leeds.nhs.uk"
    },
    {
        "name": "Bradford NHS Trust 189",
        "sector": "NHS",
        "url": "https://www.bradford.nhs.uk"
    },
    {
        "name": "Calderdale NHS Trust 190",
        "sector": "NHS",
        "url": "https://www.calderdale.nhs.uk"
    },
    {
        "name": "Midyorks NHS Trust 191",
        "sector": "NHS",
        "url": "https://www.midyorks.nhs.uk"
    },
    {
        "name": "Harrogate NHS Trust 192",
        "sector": "NHS",
        "url": "https://www.harrogate.nhs.uk"
    },
    {
        "name": "York NHS Trust 193",
        "sector": "NHS",
        "url": "https://www.york.nhs.uk"
    },
    {
        "name": "Hull NHS Trust 194",
        "sector": "NHS",
        "url": "https://www.hull.nhs.uk"
    },
    {
        "name": "Scarborough NHS Trust 195",
        "sector": "NHS",
        "url": "https://www.scarborough.nhs.uk"
    },
    {
        "name": "Tees NHS Trust 196",
        "sector": "NHS",
        "url": "https://www.tees.nhs.uk"
    },
    {
        "name": "Sunderland NHS Trust 197",
        "sector": "NHS",
        "url": "https://www.sunderland.nhs.uk"
    },
    {
        "name": "Gateshead NHS Trust 198",
        "sector": "NHS",
        "url": "https://www.gateshead.nhs.uk"
    },
    {
        "name": "Newcastle NHS Trust 199",
        "sector": "NHS",
        "url": "https://www.newcastle.nhs.uk"
    },
    {
        "name": "Northumbria NHS Trust 200",
        "sector": "NHS",
        "url": "https://www.northumbria.nhs.uk"
    },
    {
        "name": "Cumbria NHS Trust 201",
        "sector": "NHS",
        "url": "https://www.cumbria.nhs.uk"
    },
    {
        "name": "Lancashire NHS Trust 202",
        "sector": "NHS",
        "url": "https://www.lancashire.nhs.uk"
    },
    {
        "name": "Blackpool NHS Trust 203",
        "sector": "NHS",
        "url": "https://www.blackpool.nhs.uk"
    },
    {
        "name": "Preston NHS Trust 204",
        "sector": "NHS",
        "url": "https://www.preston.nhs.uk"
    },
    {
        "name": "Blackburn NHS Trust 205",
        "sector": "NHS",
        "url": "https://www.blackburn.nhs.uk"
    },
    {
        "name": "Bolton NHS Trust 206",
        "sector": "NHS",
        "url": "https://www.bolton.nhs.uk"
    },
    {
        "name": "Bury NHS Trust 207",
        "sector": "NHS",
        "url": "https://www.bury.nhs.uk"
    },
    {
        "name": "Rochdale NHS Trust 208",
        "sector": "NHS",
        "url": "https://www.rochdale.nhs.uk"
    },
    {
        "name": "Oldham NHS Trust 209",
        "sector": "NHS",
        "url": "https://www.oldham.nhs.uk"
    },
    {
        "name": "Salford NHS Trust 210",
        "sector": "NHS",
        "url": "https://www.salford.nhs.uk"
    },
    {
        "name": "Manchester NHS Trust 211",
        "sector": "NHS",
        "url": "https://www.manchester.nhs.uk"
    },
    {
        "name": "Stockport NHS Trust 212",
        "sector": "NHS",
        "url": "https://www.stockport.nhs.uk"
    },
    {
        "name": "Tameside NHS Trust 213",
        "sector": "NHS",
        "url": "https://www.tameside.nhs.uk"
    },
    {
        "name": "Trafford NHS Trust 214",
        "sector": "NHS",
        "url": "https://www.trafford.nhs.uk"
    },
    {
        "name": "Wigan NHS Trust 215",
        "sector": "NHS",
        "url": "https://www.wigan.nhs.uk"
    },
    {
        "name": "Mersey NHS Trust 216",
        "sector": "NHS",
        "url": "https://www.mersey.nhs.uk"
    },
    {
        "name": "Liverpool NHS Trust 217",
        "sector": "NHS",
        "url": "https://www.liverpool.nhs.uk"
    },
    {
        "name": "Wirral NHS Trust 218",
        "sector": "NHS",
        "url": "https://www.wirral.nhs.uk"
    },
    {
        "name": "Chester NHS Trust 219",
        "sector": "NHS",
        "url": "https://www.chester.nhs.uk"
    },
    {
        "name": "Midcheshire NHS Trust 220",
        "sector": "NHS",
        "url": "https://www.midcheshire.nhs.uk"
    },
    {
        "name": "Eastcheshire NHS Trust 221",
        "sector": "NHS",
        "url": "https://www.eastcheshire.nhs.uk"
    },
    {
        "name": "Stafford NHS Trust 222",
        "sector": "NHS",
        "url": "https://www.stafford.nhs.uk"
    },
    {
        "name": "Stoke NHS Trust 223",
        "sector": "NHS",
        "url": "https://www.stoke.nhs.uk"
    },
    {
        "name": "Shrewsbury NHS Trust 224",
        "sector": "NHS",
        "url": "https://www.shrewsbury.nhs.uk"
    },
    {
        "name": "Telford NHS Trust 225",
        "sector": "NHS",
        "url": "https://www.telford.nhs.uk"
    },
    {
        "name": "Wolverhampton NHS Trust 226",
        "sector": "NHS",
        "url": "https://www.wolverhampton.nhs.uk"
    },
    {
        "name": "Walsall NHS Trust 227",
        "sector": "NHS",
        "url": "https://www.walsall.nhs.uk"
    },
    {
        "name": "Dudley NHS Trust 228",
        "sector": "NHS",
        "url": "https://www.dudley.nhs.uk"
    },
    {
        "name": "Sandwell NHS Trust 229",
        "sector": "NHS",
        "url": "https://www.sandwell.nhs.uk"
    },
    {
        "name": "Birmingham NHS Trust 230",
        "sector": "NHS",
        "url": "https://www.birmingham.nhs.uk"
    },
    {
        "name": "Solihull NHS Trust 231",
        "sector": "NHS",
        "url": "https://www.solihull.nhs.uk"
    },
    {
        "name": "Coventry NHS Trust 232",
        "sector": "NHS",
        "url": "https://www.coventry.nhs.uk"
    },
    {
        "name": "Warwick NHS Trust 233",
        "sector": "NHS",
        "url": "https://www.warwick.nhs.uk"
    },
    {
        "name": "Worcester NHS Trust 234",
        "sector": "NHS",
        "url": "https://www.worcester.nhs.uk"
    },
    {
        "name": "Hereford NHS Trust 235",
        "sector": "NHS",
        "url": "https://www.hereford.nhs.uk"
    },
    {
        "name": "Guys NHS Trust 236",
        "sector": "NHS",
        "url": "https://www.guys.nhs.uk"
    },
    {
        "name": "Stthomas NHS Trust 237",
        "sector": "NHS",
        "url": "https://www.stthomas.nhs.uk"
    },
    {
        "name": "Uclh NHS Trust 238",
        "sector": "NHS",
        "url": "https://www.uclh.nhs.uk"
    },
    {
        "name": "Imperial NHS Trust 239",
        "sector": "NHS",
        "url": "https://www.imperial.nhs.uk"
    },
    {
        "name": "Barts NHS Trust 240",
        "sector": "NHS",
        "url": "https://www.barts.nhs.uk"
    },
    {
        "name": "Kings NHS Trust 241",
        "sector": "NHS",
        "url": "https://www.kings.nhs.uk"
    },
    {
        "name": "Royalfree NHS Trust 242",
        "sector": "NHS",
        "url": "https://www.royalfree.nhs.uk"
    },
    {
        "name": "Georges NHS Trust 243",
        "sector": "NHS",
        "url": "https://www.georges.nhs.uk"
    },
    {
        "name": "Moorfields NHS Trust 244",
        "sector": "NHS",
        "url": "https://www.moorfields.nhs.uk"
    },
    {
        "name": "Gosh NHS Trust 245",
        "sector": "NHS",
        "url": "https://www.gosh.nhs.uk"
    },
    {
        "name": "Royalmarsden NHS Trust 246",
        "sector": "NHS",
        "url": "https://www.royalmarsden.nhs.uk"
    },
    {
        "name": "Brompton NHS Trust 247",
        "sector": "NHS",
        "url": "https://www.brompton.nhs.uk"
    },
    {
        "name": "Chelwest NHS Trust 248",
        "sector": "NHS",
        "url": "https://www.chelwest.nhs.uk"
    },
    {
        "name": "Whittington NHS Trust 249",
        "sector": "NHS",
        "url": "https://www.whittington.nhs.uk"
    },
    {
        "name": "Homerton NHS Trust 250",
        "sector": "NHS",
        "url": "https://www.homerton.nhs.uk"
    },
    {
        "name": "Lewisham NHS Trust 251",
        "sector": "NHS",
        "url": "https://www.lewisham.nhs.uk"
    },
    {
        "name": "Epsom NHS Trust 252",
        "sector": "NHS",
        "url": "https://www.epsom.nhs.uk"
    },
    {
        "name": "Croydon NHS Trust 253",
        "sector": "NHS",
        "url": "https://www.croydon.nhs.uk"
    },
    {
        "name": "Kingston NHS Trust 254",
        "sector": "NHS",
        "url": "https://www.kingston.nhs.uk"
    },
    {
        "name": "Hillingdon NHS Trust 255",
        "sector": "NHS",
        "url": "https://www.hillingdon.nhs.uk"
    },
    {
        "name": "Westmid NHS Trust 256",
        "sector": "NHS",
        "url": "https://www.westmid.nhs.uk"
    },
    {
        "name": "Northmid NHS Trust 257",
        "sector": "NHS",
        "url": "https://www.northmid.nhs.uk"
    },
    {
        "name": "Barking NHS Trust 258",
        "sector": "NHS",
        "url": "https://www.barking.nhs.uk"
    },
    {
        "name": "Basildon NHS Trust 259",
        "sector": "NHS",
        "url": "https://www.basildon.nhs.uk"
    },
    {
        "name": "Southend NHS Trust 260",
        "sector": "NHS",
        "url": "https://www.southend.nhs.uk"
    },
    {
        "name": "Midessex NHS Trust 261",
        "sector": "NHS",
        "url": "https://www.midessex.nhs.uk"
    },
    {
        "name": "Colchester NHS Trust 262",
        "sector": "NHS",
        "url": "https://www.colchester.nhs.uk"
    },
    {
        "name": "Ipswich NHS Trust 263",
        "sector": "NHS",
        "url": "https://www.ipswich.nhs.uk"
    },
    {
        "name": "Norfolk NHS Trust 264",
        "sector": "NHS",
        "url": "https://www.norfolk.nhs.uk"
    },
    {
        "name": "Cambridge NHS Trust 265",
        "sector": "NHS",
        "url": "https://www.cambridge.nhs.uk"
    },
    {
        "name": "Peterborough NHS Trust 266",
        "sector": "NHS",
        "url": "https://www.peterborough.nhs.uk"
    },
    {
        "name": "Bedford NHS Trust 267",
        "sector": "NHS",
        "url": "https://www.bedford.nhs.uk"
    },
    {
        "name": "Luton NHS Trust 268",
        "sector": "NHS",
        "url": "https://www.luton.nhs.uk"
    },
    {
        "name": "Westherts NHS Trust 269",
        "sector": "NHS",
        "url": "https://www.westherts.nhs.uk"
    },
    {
        "name": "Eastherts NHS Trust 270",
        "sector": "NHS",
        "url": "https://www.eastherts.nhs.uk"
    },
    {
        "name": "Surrey NHS Trust 271",
        "sector": "NHS",
        "url": "https://www.surrey.nhs.uk"
    },
    {
        "name": "Sussex NHS Trust 272",
        "sector": "NHS",
        "url": "https://www.sussex.nhs.uk"
    },
    {
        "name": "Kent NHS Trust 273",
        "sector": "NHS",
        "url": "https://www.kent.nhs.uk"
    },
    {
        "name": "Medway NHS Trust 274",
        "sector": "NHS",
        "url": "https://www.medway.nhs.uk"
    },
    {
        "name": "Eastkent NHS Trust 275",
        "sector": "NHS",
        "url": "https://www.eastkent.nhs.uk"
    },
    {
        "name": "Darent NHS Trust 276",
        "sector": "NHS",
        "url": "https://www.darent.nhs.uk"
    },
    {
        "name": "Brighton NHS Trust 277",
        "sector": "NHS",
        "url": "https://www.brighton.nhs.uk"
    },
    {
        "name": "Eastbourne NHS Trust 278",
        "sector": "NHS",
        "url": "https://www.eastbourne.nhs.uk"
    },
    {
        "name": "Hastings NHS Trust 279",
        "sector": "NHS",
        "url": "https://www.hastings.nhs.uk"
    },
    {
        "name": "Portsmouth NHS Trust 280",
        "sector": "NHS",
        "url": "https://www.portsmouth.nhs.uk"
    },
    {
        "name": "Southampton NHS Trust 281",
        "sector": "NHS",
        "url": "https://www.southampton.nhs.uk"
    },
    {
        "name": "Bournemouth NHS Trust 282",
        "sector": "NHS",
        "url": "https://www.bournemouth.nhs.uk"
    },
    {
        "name": "Poole NHS Trust 283",
        "sector": "NHS",
        "url": "https://www.poole.nhs.uk"
    },
    {
        "name": "Dorset NHS Trust 284",
        "sector": "NHS",
        "url": "https://www.dorset.nhs.uk"
    },
    {
        "name": "Salisbury NHS Trust 285",
        "sector": "NHS",
        "url": "https://www.salisbury.nhs.uk"
    },
    {
        "name": "Bath NHS Trust 286",
        "sector": "NHS",
        "url": "https://www.bath.nhs.uk"
    },
    {
        "name": "Bristol NHS Trust 287",
        "sector": "NHS",
        "url": "https://www.bristol.nhs.uk"
    },
    {
        "name": "Gloucester NHS Trust 288",
        "sector": "NHS",
        "url": "https://www.gloucester.nhs.uk"
    },
    {
        "name": "Swindon NHS Trust 289",
        "sector": "NHS",
        "url": "https://www.swindon.nhs.uk"
    },
    {
        "name": "Oxford NHS Trust 290",
        "sector": "NHS",
        "url": "https://www.oxford.nhs.uk"
    },
    {
        "name": "Berkshire NHS Trust 291",
        "sector": "NHS",
        "url": "https://www.berkshire.nhs.uk"
    },
    {
        "name": "Buckinghamshire NHS Trust 292",
        "sector": "NHS",
        "url": "https://www.buckinghamshire.nhs.uk"
    },
    {
        "name": "Miltonkeynes NHS Trust 293",
        "sector": "NHS",
        "url": "https://www.miltonkeynes.nhs.uk"
    },
    {
        "name": "Northampton NHS Trust 294",
        "sector": "NHS",
        "url": "https://www.northampton.nhs.uk"
    },
    {
        "name": "Kettering NHS Trust 295",
        "sector": "NHS",
        "url": "https://www.kettering.nhs.uk"
    },
    {
        "name": "Leicester NHS Trust 296",
        "sector": "NHS",
        "url": "https://www.leicester.nhs.uk"
    },
    {
        "name": "Nottingham NHS Trust 297",
        "sector": "NHS",
        "url": "https://www.nottingham.nhs.uk"
    },
    {
        "name": "Derby NHS Trust 298",
        "sector": "NHS",
        "url": "https://www.derby.nhs.uk"
    },
    {
        "name": "Chesterfield NHS Trust 299",
        "sector": "NHS",
        "url": "https://www.chesterfield.nhs.uk"
    },
    {
        "name": "Lincoln NHS Trust 300",
        "sector": "NHS",
        "url": "https://www.lincoln.nhs.uk"
    },
    {
        "name": "Boston NHS Trust 301",
        "sector": "NHS",
        "url": "https://www.boston.nhs.uk"
    },
    {
        "name": "Sheffield NHS Trust 302",
        "sector": "NHS",
        "url": "https://www.sheffield.nhs.uk"
    },
    {
        "name": "Doncaster NHS Trust 303",
        "sector": "NHS",
        "url": "https://www.doncaster.nhs.uk"
    },
    {
        "name": "Rotherham NHS Trust 304",
        "sector": "NHS",
        "url": "https://www.rotherham.nhs.uk"
    },
    {
        "name": "Barnsley NHS Trust 305",
        "sector": "NHS",
        "url": "https://www.barnsley.nhs.uk"
    },
    {
        "name": "Leeds NHS Trust 306",
        "sector": "NHS",
        "url": "https://www.leeds.nhs.uk"
    },
    {
        "name": "Bradford NHS Trust 307",
        "sector": "NHS",
        "url": "https://www.bradford.nhs.uk"
    },
    {
        "name": "Calderdale NHS Trust 308",
        "sector": "NHS",
        "url": "https://www.calderdale.nhs.uk"
    },
    {
        "name": "Midyorks NHS Trust 309",
        "sector": "NHS",
        "url": "https://www.midyorks.nhs.uk"
    },
    {
        "name": "Harrogate NHS Trust 310",
        "sector": "NHS",
        "url": "https://www.harrogate.nhs.uk"
    },
    {
        "name": "York NHS Trust 311",
        "sector": "NHS",
        "url": "https://www.york.nhs.uk"
    },
    {
        "name": "Hull NHS Trust 312",
        "sector": "NHS",
        "url": "https://www.hull.nhs.uk"
    },
    {
        "name": "Scarborough NHS Trust 313",
        "sector": "NHS",
        "url": "https://www.scarborough.nhs.uk"
    },
    {
        "name": "Tees NHS Trust 314",
        "sector": "NHS",
        "url": "https://www.tees.nhs.uk"
    },
    {
        "name": "Sunderland NHS Trust 315",
        "sector": "NHS",
        "url": "https://www.sunderland.nhs.uk"
    },
    {
        "name": "Gateshead NHS Trust 316",
        "sector": "NHS",
        "url": "https://www.gateshead.nhs.uk"
    },
    {
        "name": "Newcastle NHS Trust 317",
        "sector": "NHS",
        "url": "https://www.newcastle.nhs.uk"
    },
    {
        "name": "Northumbria NHS Trust 318",
        "sector": "NHS",
        "url": "https://www.northumbria.nhs.uk"
    },
    {
        "name": "Cumbria NHS Trust 319",
        "sector": "NHS",
        "url": "https://www.cumbria.nhs.uk"
    },
    {
        "name": "Lancashire NHS Trust 320",
        "sector": "NHS",
        "url": "https://www.lancashire.nhs.uk"
    },
    {
        "name": "Blackpool NHS Trust 321",
        "sector": "NHS",
        "url": "https://www.blackpool.nhs.uk"
    },
    {
        "name": "Preston NHS Trust 322",
        "sector": "NHS",
        "url": "https://www.preston.nhs.uk"
    },
    {
        "name": "Blackburn NHS Trust 323",
        "sector": "NHS",
        "url": "https://www.blackburn.nhs.uk"
    },
    {
        "name": "Bolton NHS Trust 324",
        "sector": "NHS",
        "url": "https://www.bolton.nhs.uk"
    },
    {
        "name": "Bury NHS Trust 325",
        "sector": "NHS",
        "url": "https://www.bury.nhs.uk"
    },
    {
        "name": "Rochdale NHS Trust 326",
        "sector": "NHS",
        "url": "https://www.rochdale.nhs.uk"
    },
    {
        "name": "Oldham NHS Trust 327",
        "sector": "NHS",
        "url": "https://www.oldham.nhs.uk"
    },
    {
        "name": "Salford NHS Trust 328",
        "sector": "NHS",
        "url": "https://www.salford.nhs.uk"
    },
    {
        "name": "Manchester NHS Trust 329",
        "sector": "NHS",
        "url": "https://www.manchester.nhs.uk"
    },
    {
        "name": "Stockport NHS Trust 330",
        "sector": "NHS",
        "url": "https://www.stockport.nhs.uk"
    },
    {
        "name": "Tameside NHS Trust 331",
        "sector": "NHS",
        "url": "https://www.tameside.nhs.uk"
    },
    {
        "name": "Trafford NHS Trust 332",
        "sector": "NHS",
        "url": "https://www.trafford.nhs.uk"
    },
    {
        "name": "Wigan NHS Trust 333",
        "sector": "NHS",
        "url": "https://www.wigan.nhs.uk"
    },
    {
        "name": "Mersey NHS Trust 334",
        "sector": "NHS",
        "url": "https://www.mersey.nhs.uk"
    },
    {
        "name": "Liverpool NHS Trust 335",
        "sector": "NHS",
        "url": "https://www.liverpool.nhs.uk"
    },
    {
        "name": "Wirral NHS Trust 336",
        "sector": "NHS",
        "url": "https://www.wirral.nhs.uk"
    },
    {
        "name": "Chester NHS Trust 337",
        "sector": "NHS",
        "url": "https://www.chester.nhs.uk"
    },
    {
        "name": "Midcheshire NHS Trust 338",
        "sector": "NHS",
        "url": "https://www.midcheshire.nhs.uk"
    },
    {
        "name": "Eastcheshire NHS Trust 339",
        "sector": "NHS",
        "url": "https://www.eastcheshire.nhs.uk"
    },
    {
        "name": "Stafford NHS Trust 340",
        "sector": "NHS",
        "url": "https://www.stafford.nhs.uk"
    },
    {
        "name": "Stoke NHS Trust 341",
        "sector": "NHS",
        "url": "https://www.stoke.nhs.uk"
    },
    {
        "name": "Shrewsbury NHS Trust 342",
        "sector": "NHS",
        "url": "https://www.shrewsbury.nhs.uk"
    },
    {
        "name": "Telford NHS Trust 343",
        "sector": "NHS",
        "url": "https://www.telford.nhs.uk"
    },
    {
        "name": "Wolverhampton NHS Trust 344",
        "sector": "NHS",
        "url": "https://www.wolverhampton.nhs.uk"
    },
    {
        "name": "Walsall NHS Trust 345",
        "sector": "NHS",
        "url": "https://www.walsall.nhs.uk"
    },
    {
        "name": "Dudley NHS Trust 346",
        "sector": "NHS",
        "url": "https://www.dudley.nhs.uk"
    },
    {
        "name": "Sandwell NHS Trust 347",
        "sector": "NHS",
        "url": "https://www.sandwell.nhs.uk"
    },
    {
        "name": "Birmingham NHS Trust 348",
        "sector": "NHS",
        "url": "https://www.birmingham.nhs.uk"
    },
    {
        "name": "Solihull NHS Trust 349",
        "sector": "NHS",
        "url": "https://www.solihull.nhs.uk"
    },
    {
        "name": "Coventry NHS Trust 350",
        "sector": "NHS",
        "url": "https://www.coventry.nhs.uk"
    },
    {
        "name": "Warwick NHS Trust 351",
        "sector": "NHS",
        "url": "https://www.warwick.nhs.uk"
    },
    {
        "name": "Worcester NHS Trust 352",
        "sector": "NHS",
        "url": "https://www.worcester.nhs.uk"
    },
    {
        "name": "Hereford NHS Trust 353",
        "sector": "NHS",
        "url": "https://www.hereford.nhs.uk"
    },
    {
        "name": "Guys NHS Trust 354",
        "sector": "NHS",
        "url": "https://www.guys.nhs.uk"
    },
    {
        "name": "Stthomas NHS Trust 355",
        "sector": "NHS",
        "url": "https://www.stthomas.nhs.uk"
    },
    {
        "name": "Uclh NHS Trust 356",
        "sector": "NHS",
        "url": "https://www.uclh.nhs.uk"
    },
    {
        "name": "Imperial NHS Trust 357",
        "sector": "NHS",
        "url": "https://www.imperial.nhs.uk"
    },
    {
        "name": "Barts NHS Trust 358",
        "sector": "NHS",
        "url": "https://www.barts.nhs.uk"
    },
    {
        "name": "Kings NHS Trust 359",
        "sector": "NHS",
        "url": "https://www.kings.nhs.uk"
    },
    {
        "name": "Royalfree NHS Trust 360",
        "sector": "NHS",
        "url": "https://www.royalfree.nhs.uk"
    },
    {
        "name": "Georges NHS Trust 361",
        "sector": "NHS",
        "url": "https://www.georges.nhs.uk"
    },
    {
        "name": "Moorfields NHS Trust 362",
        "sector": "NHS",
        "url": "https://www.moorfields.nhs.uk"
    },
    {
        "name": "Gosh NHS Trust 363",
        "sector": "NHS",
        "url": "https://www.gosh.nhs.uk"
    },
    {
        "name": "Royalmarsden NHS Trust 364",
        "sector": "NHS",
        "url": "https://www.royalmarsden.nhs.uk"
    },
    {
        "name": "Brompton NHS Trust 365",
        "sector": "NHS",
        "url": "https://www.brompton.nhs.uk"
    },
    {
        "name": "Chelwest NHS Trust 366",
        "sector": "NHS",
        "url": "https://www.chelwest.nhs.uk"
    },
    {
        "name": "Whittington NHS Trust 367",
        "sector": "NHS",
        "url": "https://www.whittington.nhs.uk"
    },
    {
        "name": "Homerton NHS Trust 368",
        "sector": "NHS",
        "url": "https://www.homerton.nhs.uk"
    },
    {
        "name": "Lewisham NHS Trust 369",
        "sector": "NHS",
        "url": "https://www.lewisham.nhs.uk"
    },
    {
        "name": "Epsom NHS Trust 370",
        "sector": "NHS",
        "url": "https://www.epsom.nhs.uk"
    },
    {
        "name": "Croydon NHS Trust 371",
        "sector": "NHS",
        "url": "https://www.croydon.nhs.uk"
    },
    {
        "name": "Kingston NHS Trust 372",
        "sector": "NHS",
        "url": "https://www.kingston.nhs.uk"
    },
    {
        "name": "Hillingdon NHS Trust 373",
        "sector": "NHS",
        "url": "https://www.hillingdon.nhs.uk"
    },
    {
        "name": "Westmid NHS Trust 374",
        "sector": "NHS",
        "url": "https://www.westmid.nhs.uk"
    },
    {
        "name": "Northmid NHS Trust 375",
        "sector": "NHS",
        "url": "https://www.northmid.nhs.uk"
    },
    {
        "name": "Barking NHS Trust 376",
        "sector": "NHS",
        "url": "https://www.barking.nhs.uk"
    },
    {
        "name": "Basildon NHS Trust 377",
        "sector": "NHS",
        "url": "https://www.basildon.nhs.uk"
    },
    {
        "name": "Southend NHS Trust 378",
        "sector": "NHS",
        "url": "https://www.southend.nhs.uk"
    },
    {
        "name": "Midessex NHS Trust 379",
        "sector": "NHS",
        "url": "https://www.midessex.nhs.uk"
    },
    {
        "name": "Colchester NHS Trust 380",
        "sector": "NHS",
        "url": "https://www.colchester.nhs.uk"
    },
    {
        "name": "Ipswich NHS Trust 381",
        "sector": "NHS",
        "url": "https://www.ipswich.nhs.uk"
    },
    {
        "name": "Norfolk NHS Trust 382",
        "sector": "NHS",
        "url": "https://www.norfolk.nhs.uk"
    },
    {
        "name": "Cambridge NHS Trust 383",
        "sector": "NHS",
        "url": "https://www.cambridge.nhs.uk"
    },
    {
        "name": "Peterborough NHS Trust 384",
        "sector": "NHS",
        "url": "https://www.peterborough.nhs.uk"
    },
    {
        "name": "Bedford NHS Trust 385",
        "sector": "NHS",
        "url": "https://www.bedford.nhs.uk"
    },
    {
        "name": "Luton NHS Trust 386",
        "sector": "NHS",
        "url": "https://www.luton.nhs.uk"
    },
    {
        "name": "Westherts NHS Trust 387",
        "sector": "NHS",
        "url": "https://www.westherts.nhs.uk"
    },
    {
        "name": "Eastherts NHS Trust 388",
        "sector": "NHS",
        "url": "https://www.eastherts.nhs.uk"
    },
    {
        "name": "Surrey NHS Trust 389",
        "sector": "NHS",
        "url": "https://www.surrey.nhs.uk"
    },
    {
        "name": "Sussex NHS Trust 390",
        "sector": "NHS",
        "url": "https://www.sussex.nhs.uk"
    },
    {
        "name": "Kent NHS Trust 391",
        "sector": "NHS",
        "url": "https://www.kent.nhs.uk"
    },
    {
        "name": "Medway NHS Trust 392",
        "sector": "NHS",
        "url": "https://www.medway.nhs.uk"
    },
    {
        "name": "Eastkent NHS Trust 393",
        "sector": "NHS",
        "url": "https://www.eastkent.nhs.uk"
    },
    {
        "name": "Darent NHS Trust 394",
        "sector": "NHS",
        "url": "https://www.darent.nhs.uk"
    },
    {
        "name": "Brighton NHS Trust 395",
        "sector": "NHS",
        "url": "https://www.brighton.nhs.uk"
    },
    {
        "name": "Eastbourne NHS Trust 396",
        "sector": "NHS",
        "url": "https://www.eastbourne.nhs.uk"
    },
    {
        "name": "Hastings NHS Trust 397",
        "sector": "NHS",
        "url": "https://www.hastings.nhs.uk"
    },
    {
        "name": "Portsmouth NHS Trust 398",
        "sector": "NHS",
        "url": "https://www.portsmouth.nhs.uk"
    },
    {
        "name": "Southampton NHS Trust 399",
        "sector": "NHS",
        "url": "https://www.southampton.nhs.uk"
    },
    {
        "name": "University of Cam 1",
        "sector": "Education",
        "url": "https://www.cam.ac.uk"
    },
    {
        "name": "University of Ucl 2",
        "sector": "Education",
        "url": "https://www.ucl.ac.uk"
    },
    {
        "name": "University of Ic 3",
        "sector": "Education",
        "url": "https://www.ic.ac.uk"
    },
    {
        "name": "University of Kcl 4",
        "sector": "Education",
        "url": "https://www.kcl.ac.uk"
    },
    {
        "name": "University of Lse 5",
        "sector": "Education",
        "url": "https://www.lse.ac.uk"
    },
    {
        "name": "University of Qmul 6",
        "sector": "Education",
        "url": "https://www.qmul.ac.uk"
    },
    {
        "name": "University of Man 7",
        "sector": "Education",
        "url": "https://www.man.ac.uk"
    },
    {
        "name": "University of Ed 8",
        "sector": "Education",
        "url": "https://www.ed.ac.uk"
    },
    {
        "name": "University of Gla 9",
        "sector": "Education",
        "url": "https://www.gla.ac.uk"
    },
    {
        "name": "University of Strath 10",
        "sector": "Education",
        "url": "https://www.strath.ac.uk"
    },
    {
        "name": "University of Hw 11",
        "sector": "Education",
        "url": "https://www.hw.ac.uk"
    },
    {
        "name": "University of Abdn 12",
        "sector": "Education",
        "url": "https://www.abdn.ac.uk"
    },
    {
        "name": "University of Dundee 13",
        "sector": "Education",
        "url": "https://www.dundee.ac.uk"
    },
    {
        "name": "University of St-Andrews 14",
        "sector": "Education",
        "url": "https://www.st-andrews.ac.uk"
    },
    {
        "name": "University of Stir 15",
        "sector": "Education",
        "url": "https://www.stir.ac.uk"
    },
    {
        "name": "University of Napier 16",
        "sector": "Education",
        "url": "https://www.napier.ac.uk"
    },
    {
        "name": "University of Qmu 17",
        "sector": "Education",
        "url": "https://www.qmu.ac.uk"
    },
    {
        "name": "University of Rgu 18",
        "sector": "Education",
        "url": "https://www.rgu.ac.uk"
    },
    {
        "name": "University of Abertay 19",
        "sector": "Education",
        "url": "https://www.abertay.ac.uk"
    },
    {
        "name": "University of Uhi 20",
        "sector": "Education",
        "url": "https://www.uhi.ac.uk"
    },
    {
        "name": "University of Qub 21",
        "sector": "Education",
        "url": "https://www.qub.ac.uk"
    },
    {
        "name": "University of Ulster 22",
        "sector": "Education",
        "url": "https://www.ulster.ac.uk"
    },
    {
        "name": "University of Cardiff 23",
        "sector": "Education",
        "url": "https://www.cardiff.ac.uk"
    },
    {
        "name": "University of Swansea 24",
        "sector": "Education",
        "url": "https://www.swansea.ac.uk"
    },
    {
        "name": "University of Bangor 25",
        "sector": "Education",
        "url": "https://www.bangor.ac.uk"
    },
    {
        "name": "University of Aber 26",
        "sector": "Education",
        "url": "https://www.aber.ac.uk"
    },
    {
        "name": "University of Southwales 27",
        "sector": "Education",
        "url": "https://www.southwales.ac.uk"
    },
    {
        "name": "University of Uwtsd 28",
        "sector": "Education",
        "url": "https://www.uwtsd.ac.uk"
    },
    {
        "name": "University of Glyndwr 29",
        "sector": "Education",
        "url": "https://www.glyndwr.ac.uk"
    },
    {
        "name": "University of Cardiffmet 30",
        "sector": "Education",
        "url": "https://www.cardiffmet.ac.uk"
    },
    {
        "name": "University of Bristol 31",
        "sector": "Education",
        "url": "https://www.bristol.ac.uk"
    },
    {
        "name": "University of Bath 32",
        "sector": "Education",
        "url": "https://www.bath.ac.uk"
    },
    {
        "name": "University of Exeter 33",
        "sector": "Education",
        "url": "https://www.exeter.ac.uk"
    },
    {
        "name": "University of Plymouth 34",
        "sector": "Education",
        "url": "https://www.plymouth.ac.uk"
    },
    {
        "name": "University of Soton 35",
        "sector": "Education",
        "url": "https://www.soton.ac.uk"
    },
    {
        "name": "University of Port 36",
        "sector": "Education",
        "url": "https://www.port.ac.uk"
    },
    {
        "name": "University of Bournemouth 37",
        "sector": "Education",
        "url": "https://www.bournemouth.ac.uk"
    },
    {
        "name": "University of Sussex 38",
        "sector": "Education",
        "url": "https://www.sussex.ac.uk"
    },
    {
        "name": "University of Brighton 39",
        "sector": "Education",
        "url": "https://www.brighton.ac.uk"
    },
    {
        "name": "University of Surrey 40",
        "sector": "Education",
        "url": "https://www.surrey.ac.uk"
    },
    {
        "name": "University of Kent 41",
        "sector": "Education",
        "url": "https://www.kent.ac.uk"
    },
    {
        "name": "University of Reading 42",
        "sector": "Education",
        "url": "https://www.reading.ac.uk"
    },
    {
        "name": "University of Warwick 43",
        "sector": "Education",
        "url": "https://www.warwick.ac.uk"
    },
    {
        "name": "University of Coventry 44",
        "sector": "Education",
        "url": "https://www.coventry.ac.uk"
    },
    {
        "name": "University of Bham 45",
        "sector": "Education",
        "url": "https://www.bham.ac.uk"
    },
    {
        "name": "University of Aston 46",
        "sector": "Education",
        "url": "https://www.aston.ac.uk"
    },
    {
        "name": "University of Ntu 47",
        "sector": "Education",
        "url": "https://www.ntu.ac.uk"
    },
    {
        "name": "University of Nottingham 48",
        "sector": "Education",
        "url": "https://www.nottingham.ac.uk"
    },
    {
        "name": "University of Leicester 49",
        "sector": "Education",
        "url": "https://www.leicester.ac.uk"
    },
    {
        "name": "University of Dmu 50",
        "sector": "Education",
        "url": "https://www.dmu.ac.uk"
    },
    {
        "name": "University of Lboro 51",
        "sector": "Education",
        "url": "https://www.lboro.ac.uk"
    },
    {
        "name": "University of Shef 52",
        "sector": "Education",
        "url": "https://www.shef.ac.uk"
    },
    {
        "name": "University of Shu 53",
        "sector": "Education",
        "url": "https://www.shu.ac.uk"
    },
    {
        "name": "University of Leeds 54",
        "sector": "Education",
        "url": "https://www.leeds.ac.uk"
    },
    {
        "name": "University of Leedsbeckett 55",
        "sector": "Education",
        "url": "https://www.leedsbeckett.ac.uk"
    },
    {
        "name": "University of York 56",
        "sector": "Education",
        "url": "https://www.york.ac.uk"
    },
    {
        "name": "University of Hull 57",
        "sector": "Education",
        "url": "https://www.hull.ac.uk"
    },
    {
        "name": "University of Ncl 58",
        "sector": "Education",
        "url": "https://www.ncl.ac.uk"
    },
    {
        "name": "University of Northumbria 59",
        "sector": "Education",
        "url": "https://www.northumbria.ac.uk"
    },
    {
        "name": "University of Durham 60",
        "sector": "Education",
        "url": "https://www.durham.ac.uk"
    },
    {
        "name": "University of Sunderland 61",
        "sector": "Education",
        "url": "https://www.sunderland.ac.uk"
    },
    {
        "name": "University of Tees 62",
        "sector": "Education",
        "url": "https://www.tees.ac.uk"
    },
    {
        "name": "University of Lancs 63",
        "sector": "Education",
        "url": "https://www.lancs.ac.uk"
    },
    {
        "name": "University of Uclan 64",
        "sector": "Education",
        "url": "https://www.uclan.ac.uk"
    },
    {
        "name": "University of Liv 65",
        "sector": "Education",
        "url": "https://www.liv.ac.uk"
    },
    {
        "name": "University of Ljmu 66",
        "sector": "Education",
        "url": "https://www.ljmu.ac.uk"
    },
    {
        "name": "University of Mmu 67",
        "sector": "Education",
        "url": "https://www.mmu.ac.uk"
    },
    {
        "name": "University of Keele 68",
        "sector": "Education",
        "url": "https://www.keele.ac.uk"
    },
    {
        "name": "University of Staffs 69",
        "sector": "Education",
        "url": "https://www.staffs.ac.uk"
    },
    {
        "name": "University of Chester 70",
        "sector": "Education",
        "url": "https://www.chester.ac.uk"
    },
    {
        "name": "University of Edgehill 71",
        "sector": "Education",
        "url": "https://www.edgehill.ac.uk"
    },
    {
        "name": "University of Cumbria 72",
        "sector": "Education",
        "url": "https://www.cumbria.ac.uk"
    },
    {
        "name": "University of Ox 73",
        "sector": "Education",
        "url": "https://www.ox.ac.uk"
    },
    {
        "name": "University of Cam 74",
        "sector": "Education",
        "url": "https://www.cam.ac.uk"
    },
    {
        "name": "University of Ucl 75",
        "sector": "Education",
        "url": "https://www.ucl.ac.uk"
    },
    {
        "name": "University of Ic 76",
        "sector": "Education",
        "url": "https://www.ic.ac.uk"
    },
    {
        "name": "University of Kcl 77",
        "sector": "Education",
        "url": "https://www.kcl.ac.uk"
    },
    {
        "name": "University of Lse 78",
        "sector": "Education",
        "url": "https://www.lse.ac.uk"
    },
    {
        "name": "University of Qmul 79",
        "sector": "Education",
        "url": "https://www.qmul.ac.uk"
    },
    {
        "name": "University of Man 80",
        "sector": "Education",
        "url": "https://www.man.ac.uk"
    },
    {
        "name": "University of Ed 81",
        "sector": "Education",
        "url": "https://www.ed.ac.uk"
    },
    {
        "name": "University of Gla 82",
        "sector": "Education",
        "url": "https://www.gla.ac.uk"
    },
    {
        "name": "University of Strath 83",
        "sector": "Education",
        "url": "https://www.strath.ac.uk"
    },
    {
        "name": "University of Hw 84",
        "sector": "Education",
        "url": "https://www.hw.ac.uk"
    },
    {
        "name": "University of Abdn 85",
        "sector": "Education",
        "url": "https://www.abdn.ac.uk"
    },
    {
        "name": "University of Dundee 86",
        "sector": "Education",
        "url": "https://www.dundee.ac.uk"
    },
    {
        "name": "University of St-Andrews 87",
        "sector": "Education",
        "url": "https://www.st-andrews.ac.uk"
    },
    {
        "name": "University of Stir 88",
        "sector": "Education",
        "url": "https://www.stir.ac.uk"
    },
    {
        "name": "University of Napier 89",
        "sector": "Education",
        "url": "https://www.napier.ac.uk"
    },
    {
        "name": "University of Qmu 90",
        "sector": "Education",
        "url": "https://www.qmu.ac.uk"
    },
    {
        "name": "University of Rgu 91",
        "sector": "Education",
        "url": "https://www.rgu.ac.uk"
    },
    {
        "name": "University of Abertay 92",
        "sector": "Education",
        "url": "https://www.abertay.ac.uk"
    },
    {
        "name": "University of Uhi 93",
        "sector": "Education",
        "url": "https://www.uhi.ac.uk"
    },
    {
        "name": "University of Qub 94",
        "sector": "Education",
        "url": "https://www.qub.ac.uk"
    },
    {
        "name": "University of Ulster 95",
        "sector": "Education",
        "url": "https://www.ulster.ac.uk"
    },
    {
        "name": "University of Cardiff 96",
        "sector": "Education",
        "url": "https://www.cardiff.ac.uk"
    },
    {
        "name": "University of Swansea 97",
        "sector": "Education",
        "url": "https://www.swansea.ac.uk"
    },
    {
        "name": "University of Bangor 98",
        "sector": "Education",
        "url": "https://www.bangor.ac.uk"
    },
    {
        "name": "University of Aber 99",
        "sector": "Education",
        "url": "https://www.aber.ac.uk"
    },
    {
        "name": "University of Southwales 100",
        "sector": "Education",
        "url": "https://www.southwales.ac.uk"
    },
    {
        "name": "University of Uwtsd 101",
        "sector": "Education",
        "url": "https://www.uwtsd.ac.uk"
    },
    {
        "name": "University of Glyndwr 102",
        "sector": "Education",
        "url": "https://www.glyndwr.ac.uk"
    },
    {
        "name": "University of Cardiffmet 103",
        "sector": "Education",
        "url": "https://www.cardiffmet.ac.uk"
    },
    {
        "name": "University of Bristol 104",
        "sector": "Education",
        "url": "https://www.bristol.ac.uk"
    },
    {
        "name": "University of Bath 105",
        "sector": "Education",
        "url": "https://www.bath.ac.uk"
    },
    {
        "name": "University of Exeter 106",
        "sector": "Education",
        "url": "https://www.exeter.ac.uk"
    },
    {
        "name": "University of Plymouth 107",
        "sector": "Education",
        "url": "https://www.plymouth.ac.uk"
    },
    {
        "name": "University of Soton 108",
        "sector": "Education",
        "url": "https://www.soton.ac.uk"
    },
    {
        "name": "University of Port 109",
        "sector": "Education",
        "url": "https://www.port.ac.uk"
    },
    {
        "name": "University of Bournemouth 110",
        "sector": "Education",
        "url": "https://www.bournemouth.ac.uk"
    },
    {
        "name": "University of Sussex 111",
        "sector": "Education",
        "url": "https://www.sussex.ac.uk"
    },
    {
        "name": "University of Brighton 112",
        "sector": "Education",
        "url": "https://www.brighton.ac.uk"
    },
    {
        "name": "University of Surrey 113",
        "sector": "Education",
        "url": "https://www.surrey.ac.uk"
    },
    {
        "name": "University of Kent 114",
        "sector": "Education",
        "url": "https://www.kent.ac.uk"
    },
    {
        "name": "University of Reading 115",
        "sector": "Education",
        "url": "https://www.reading.ac.uk"
    },
    {
        "name": "University of Warwick 116",
        "sector": "Education",
        "url": "https://www.warwick.ac.uk"
    },
    {
        "name": "University of Coventry 117",
        "sector": "Education",
        "url": "https://www.coventry.ac.uk"
    },
    {
        "name": "University of Bham 118",
        "sector": "Education",
        "url": "https://www.bham.ac.uk"
    },
    {
        "name": "University of Aston 119",
        "sector": "Education",
        "url": "https://www.aston.ac.uk"
    },
    {
        "name": "University of Ntu 120",
        "sector": "Education",
        "url": "https://www.ntu.ac.uk"
    },
    {
        "name": "University of Nottingham 121",
        "sector": "Education",
        "url": "https://www.nottingham.ac.uk"
    },
    {
        "name": "University of Leicester 122",
        "sector": "Education",
        "url": "https://www.leicester.ac.uk"
    },
    {
        "name": "University of Dmu 123",
        "sector": "Education",
        "url": "https://www.dmu.ac.uk"
    },
    {
        "name": "University of Lboro 124",
        "sector": "Education",
        "url": "https://www.lboro.ac.uk"
    },
    {
        "name": "University of Shef 125",
        "sector": "Education",
        "url": "https://www.shef.ac.uk"
    },
    {
        "name": "University of Shu 126",
        "sector": "Education",
        "url": "https://www.shu.ac.uk"
    },
    {
        "name": "University of Leeds 127",
        "sector": "Education",
        "url": "https://www.leeds.ac.uk"
    },
    {
        "name": "University of Leedsbeckett 128",
        "sector": "Education",
        "url": "https://www.leedsbeckett.ac.uk"
    },
    {
        "name": "University of York 129",
        "sector": "Education",
        "url": "https://www.york.ac.uk"
    },
    {
        "name": "University of Hull 130",
        "sector": "Education",
        "url": "https://www.hull.ac.uk"
    },
    {
        "name": "University of Ncl 131",
        "sector": "Education",
        "url": "https://www.ncl.ac.uk"
    },
    {
        "name": "University of Northumbria 132",
        "sector": "Education",
        "url": "https://www.northumbria.ac.uk"
    },
    {
        "name": "University of Durham 133",
        "sector": "Education",
        "url": "https://www.durham.ac.uk"
    },
    {
        "name": "University of Sunderland 134",
        "sector": "Education",
        "url": "https://www.sunderland.ac.uk"
    },
    {
        "name": "University of Tees 135",
        "sector": "Education",
        "url": "https://www.tees.ac.uk"
    },
    {
        "name": "University of Lancs 136",
        "sector": "Education",
        "url": "https://www.lancs.ac.uk"
    },
    {
        "name": "University of Uclan 137",
        "sector": "Education",
        "url": "https://www.uclan.ac.uk"
    },
    {
        "name": "University of Liv 138",
        "sector": "Education",
        "url": "https://www.liv.ac.uk"
    },
    {
        "name": "University of Ljmu 139",
        "sector": "Education",
        "url": "https://www.ljmu.ac.uk"
    },
    {
        "name": "University of Mmu 140",
        "sector": "Education",
        "url": "https://www.mmu.ac.uk"
    },
    {
        "name": "University of Keele 141",
        "sector": "Education",
        "url": "https://www.keele.ac.uk"
    },
    {
        "name": "University of Staffs 142",
        "sector": "Education",
        "url": "https://www.staffs.ac.uk"
    },
    {
        "name": "University of Chester 143",
        "sector": "Education",
        "url": "https://www.chester.ac.uk"
    },
    {
        "name": "University of Edgehill 144",
        "sector": "Education",
        "url": "https://www.edgehill.ac.uk"
    },
    {
        "name": "University of Cumbria 145",
        "sector": "Education",
        "url": "https://www.cumbria.ac.uk"
    },
    {
        "name": "University of Ox 146",
        "sector": "Education",
        "url": "https://www.ox.ac.uk"
    },
    {
        "name": "University of Cam 147",
        "sector": "Education",
        "url": "https://www.cam.ac.uk"
    },
    {
        "name": "University of Ucl 148",
        "sector": "Education",
        "url": "https://www.ucl.ac.uk"
    },
    {
        "name": "University of Ic 149",
        "sector": "Education",
        "url": "https://www.ic.ac.uk"
    },
    {
        "name": "University of Kcl 150",
        "sector": "Education",
        "url": "https://www.kcl.ac.uk"
    },
    {
        "name": "University of Lse 151",
        "sector": "Education",
        "url": "https://www.lse.ac.uk"
    },
    {
        "name": "University of Qmul 152",
        "sector": "Education",
        "url": "https://www.qmul.ac.uk"
    },
    {
        "name": "University of Man 153",
        "sector": "Education",
        "url": "https://www.man.ac.uk"
    },
    {
        "name": "University of Ed 154",
        "sector": "Education",
        "url": "https://www.ed.ac.uk"
    },
    {
        "name": "University of Gla 155",
        "sector": "Education",
        "url": "https://www.gla.ac.uk"
    },
    {
        "name": "University of Strath 156",
        "sector": "Education",
        "url": "https://www.strath.ac.uk"
    },
    {
        "name": "University of Hw 157",
        "sector": "Education",
        "url": "https://www.hw.ac.uk"
    },
    {
        "name": "University of Abdn 158",
        "sector": "Education",
        "url": "https://www.abdn.ac.uk"
    },
    {
        "name": "University of Dundee 159",
        "sector": "Education",
        "url": "https://www.dundee.ac.uk"
    },
    {
        "name": "University of St-Andrews 160",
        "sector": "Education",
        "url": "https://www.st-andrews.ac.uk"
    },
    {
        "name": "University of Stir 161",
        "sector": "Education",
        "url": "https://www.stir.ac.uk"
    },
    {
        "name": "University of Napier 162",
        "sector": "Education",
        "url": "https://www.napier.ac.uk"
    },
    {
        "name": "University of Qmu 163",
        "sector": "Education",
        "url": "https://www.qmu.ac.uk"
    },
    {
        "name": "University of Rgu 164",
        "sector": "Education",
        "url": "https://www.rgu.ac.uk"
    },
    {
        "name": "University of Abertay 165",
        "sector": "Education",
        "url": "https://www.abertay.ac.uk"
    },
    {
        "name": "University of Uhi 166",
        "sector": "Education",
        "url": "https://www.uhi.ac.uk"
    },
    {
        "name": "University of Qub 167",
        "sector": "Education",
        "url": "https://www.qub.ac.uk"
    },
    {
        "name": "University of Ulster 168",
        "sector": "Education",
        "url": "https://www.ulster.ac.uk"
    },
    {
        "name": "University of Cardiff 169",
        "sector": "Education",
        "url": "https://www.cardiff.ac.uk"
    },
    {
        "name": "University of Swansea 170",
        "sector": "Education",
        "url": "https://www.swansea.ac.uk"
    },
    {
        "name": "University of Bangor 171",
        "sector": "Education",
        "url": "https://www.bangor.ac.uk"
    },
    {
        "name": "University of Aber 172",
        "sector": "Education",
        "url": "https://www.aber.ac.uk"
    },
    {
        "name": "University of Southwales 173",
        "sector": "Education",
        "url": "https://www.southwales.ac.uk"
    },
    {
        "name": "University of Uwtsd 174",
        "sector": "Education",
        "url": "https://www.uwtsd.ac.uk"
    },
    {
        "name": "University of Glyndwr 175",
        "sector": "Education",
        "url": "https://www.glyndwr.ac.uk"
    },
    {
        "name": "University of Cardiffmet 176",
        "sector": "Education",
        "url": "https://www.cardiffmet.ac.uk"
    },
    {
        "name": "University of Bristol 177",
        "sector": "Education",
        "url": "https://www.bristol.ac.uk"
    },
    {
        "name": "University of Bath 178",
        "sector": "Education",
        "url": "https://www.bath.ac.uk"
    },
    {
        "name": "University of Exeter 179",
        "sector": "Education",
        "url": "https://www.exeter.ac.uk"
    },
    {
        "name": "University of Plymouth 180",
        "sector": "Education",
        "url": "https://www.plymouth.ac.uk"
    },
    {
        "name": "University of Soton 181",
        "sector": "Education",
        "url": "https://www.soton.ac.uk"
    },
    {
        "name": "University of Port 182",
        "sector": "Education",
        "url": "https://www.port.ac.uk"
    },
    {
        "name": "University of Bournemouth 183",
        "sector": "Education",
        "url": "https://www.bournemouth.ac.uk"
    },
    {
        "name": "University of Sussex 184",
        "sector": "Education",
        "url": "https://www.sussex.ac.uk"
    },
    {
        "name": "University of Brighton 185",
        "sector": "Education",
        "url": "https://www.brighton.ac.uk"
    },
    {
        "name": "University of Surrey 186",
        "sector": "Education",
        "url": "https://www.surrey.ac.uk"
    },
    {
        "name": "University of Kent 187",
        "sector": "Education",
        "url": "https://www.kent.ac.uk"
    },
    {
        "name": "University of Reading 188",
        "sector": "Education",
        "url": "https://www.reading.ac.uk"
    },
    {
        "name": "University of Warwick 189",
        "sector": "Education",
        "url": "https://www.warwick.ac.uk"
    },
    {
        "name": "University of Coventry 190",
        "sector": "Education",
        "url": "https://www.coventry.ac.uk"
    },
    {
        "name": "University of Bham 191",
        "sector": "Education",
        "url": "https://www.bham.ac.uk"
    },
    {
        "name": "University of Aston 192",
        "sector": "Education",
        "url": "https://www.aston.ac.uk"
    },
    {
        "name": "University of Ntu 193",
        "sector": "Education",
        "url": "https://www.ntu.ac.uk"
    },
    {
        "name": "University of Nottingham 194",
        "sector": "Education",
        "url": "https://www.nottingham.ac.uk"
    },
    {
        "name": "University of Leicester 195",
        "sector": "Education",
        "url": "https://www.leicester.ac.uk"
    },
    {
        "name": "University of Dmu 196",
        "sector": "Education",
        "url": "https://www.dmu.ac.uk"
    },
    {
        "name": "University of Lboro 197",
        "sector": "Education",
        "url": "https://www.lboro.ac.uk"
    },
    {
        "name": "University of Shef 198",
        "sector": "Education",
        "url": "https://www.shef.ac.uk"
    },
    {
        "name": "University of Shu 199",
        "sector": "Education",
        "url": "https://www.shu.ac.uk"
    },
    {
        "name": "University of Leeds 200",
        "sector": "Education",
        "url": "https://www.leeds.ac.uk"
    },
    {
        "name": "University of Leedsbeckett 201",
        "sector": "Education",
        "url": "https://www.leedsbeckett.ac.uk"
    },
    {
        "name": "University of York 202",
        "sector": "Education",
        "url": "https://www.york.ac.uk"
    },
    {
        "name": "University of Hull 203",
        "sector": "Education",
        "url": "https://www.hull.ac.uk"
    },
    {
        "name": "University of Ncl 204",
        "sector": "Education",
        "url": "https://www.ncl.ac.uk"
    },
    {
        "name": "University of Northumbria 205",
        "sector": "Education",
        "url": "https://www.northumbria.ac.uk"
    },
    {
        "name": "University of Durham 206",
        "sector": "Education",
        "url": "https://www.durham.ac.uk"
    },
    {
        "name": "University of Sunderland 207",
        "sector": "Education",
        "url": "https://www.sunderland.ac.uk"
    },
    {
        "name": "University of Tees 208",
        "sector": "Education",
        "url": "https://www.tees.ac.uk"
    },
    {
        "name": "University of Lancs 209",
        "sector": "Education",
        "url": "https://www.lancs.ac.uk"
    },
    {
        "name": "University of Uclan 210",
        "sector": "Education",
        "url": "https://www.uclan.ac.uk"
    },
    {
        "name": "University of Liv 211",
        "sector": "Education",
        "url": "https://www.liv.ac.uk"
    },
    {
        "name": "University of Ljmu 212",
        "sector": "Education",
        "url": "https://www.ljmu.ac.uk"
    },
    {
        "name": "University of Mmu 213",
        "sector": "Education",
        "url": "https://www.mmu.ac.uk"
    },
    {
        "name": "University of Keele 214",
        "sector": "Education",
        "url": "https://www.keele.ac.uk"
    },
    {
        "name": "University of Staffs 215",
        "sector": "Education",
        "url": "https://www.staffs.ac.uk"
    },
    {
        "name": "University of Chester 216",
        "sector": "Education",
        "url": "https://www.chester.ac.uk"
    },
    {
        "name": "University of Edgehill 217",
        "sector": "Education",
        "url": "https://www.edgehill.ac.uk"
    },
    {
        "name": "University of Cumbria 218",
        "sector": "Education",
        "url": "https://www.cumbria.ac.uk"
    },
    {
        "name": "University of Ox 219",
        "sector": "Education",
        "url": "https://www.ox.ac.uk"
    },
    {
        "name": "University of Cam 220",
        "sector": "Education",
        "url": "https://www.cam.ac.uk"
    },
    {
        "name": "University of Ucl 221",
        "sector": "Education",
        "url": "https://www.ucl.ac.uk"
    },
    {
        "name": "University of Ic 222",
        "sector": "Education",
        "url": "https://www.ic.ac.uk"
    },
    {
        "name": "University of Kcl 223",
        "sector": "Education",
        "url": "https://www.kcl.ac.uk"
    },
    {
        "name": "University of Lse 224",
        "sector": "Education",
        "url": "https://www.lse.ac.uk"
    },
    {
        "name": "University of Qmul 225",
        "sector": "Education",
        "url": "https://www.qmul.ac.uk"
    },
    {
        "name": "University of Man 226",
        "sector": "Education",
        "url": "https://www.man.ac.uk"
    },
    {
        "name": "University of Ed 227",
        "sector": "Education",
        "url": "https://www.ed.ac.uk"
    },
    {
        "name": "University of Gla 228",
        "sector": "Education",
        "url": "https://www.gla.ac.uk"
    },
    {
        "name": "University of Strath 229",
        "sector": "Education",
        "url": "https://www.strath.ac.uk"
    },
    {
        "name": "University of Hw 230",
        "sector": "Education",
        "url": "https://www.hw.ac.uk"
    },
    {
        "name": "University of Abdn 231",
        "sector": "Education",
        "url": "https://www.abdn.ac.uk"
    },
    {
        "name": "University of Dundee 232",
        "sector": "Education",
        "url": "https://www.dundee.ac.uk"
    },
    {
        "name": "University of St-Andrews 233",
        "sector": "Education",
        "url": "https://www.st-andrews.ac.uk"
    },
    {
        "name": "University of Stir 234",
        "sector": "Education",
        "url": "https://www.stir.ac.uk"
    },
    {
        "name": "University of Napier 235",
        "sector": "Education",
        "url": "https://www.napier.ac.uk"
    },
    {
        "name": "University of Qmu 236",
        "sector": "Education",
        "url": "https://www.qmu.ac.uk"
    },
    {
        "name": "University of Rgu 237",
        "sector": "Education",
        "url": "https://www.rgu.ac.uk"
    },
    {
        "name": "University of Abertay 238",
        "sector": "Education",
        "url": "https://www.abertay.ac.uk"
    },
    {
        "name": "University of Uhi 239",
        "sector": "Education",
        "url": "https://www.uhi.ac.uk"
    },
    {
        "name": "University of Qub 240",
        "sector": "Education",
        "url": "https://www.qub.ac.uk"
    },
    {
        "name": "University of Ulster 241",
        "sector": "Education",
        "url": "https://www.ulster.ac.uk"
    },
    {
        "name": "University of Cardiff 242",
        "sector": "Education",
        "url": "https://www.cardiff.ac.uk"
    },
    {
        "name": "University of Swansea 243",
        "sector": "Education",
        "url": "https://www.swansea.ac.uk"
    },
    {
        "name": "University of Bangor 244",
        "sector": "Education",
        "url": "https://www.bangor.ac.uk"
    },
    {
        "name": "University of Aber 245",
        "sector": "Education",
        "url": "https://www.aber.ac.uk"
    },
    {
        "name": "University of Southwales 246",
        "sector": "Education",
        "url": "https://www.southwales.ac.uk"
    },
    {
        "name": "University of Uwtsd 247",
        "sector": "Education",
        "url": "https://www.uwtsd.ac.uk"
    },
    {
        "name": "University of Glyndwr 248",
        "sector": "Education",
        "url": "https://www.glyndwr.ac.uk"
    },
    {
        "name": "University of Cardiffmet 249",
        "sector": "Education",
        "url": "https://www.cardiffmet.ac.uk"
    },
    {
        "name": "University of Bristol 250",
        "sector": "Education",
        "url": "https://www.bristol.ac.uk"
    },
    {
        "name": "University of Bath 251",
        "sector": "Education",
        "url": "https://www.bath.ac.uk"
    },
    {
        "name": "University of Exeter 252",
        "sector": "Education",
        "url": "https://www.exeter.ac.uk"
    },
    {
        "name": "University of Plymouth 253",
        "sector": "Education",
        "url": "https://www.plymouth.ac.uk"
    },
    {
        "name": "University of Soton 254",
        "sector": "Education",
        "url": "https://www.soton.ac.uk"
    },
    {
        "name": "University of Port 255",
        "sector": "Education",
        "url": "https://www.port.ac.uk"
    },
    {
        "name": "University of Bournemouth 256",
        "sector": "Education",
        "url": "https://www.bournemouth.ac.uk"
    },
    {
        "name": "University of Sussex 257",
        "sector": "Education",
        "url": "https://www.sussex.ac.uk"
    },
    {
        "name": "University of Brighton 258",
        "sector": "Education",
        "url": "https://www.brighton.ac.uk"
    },
    {
        "name": "University of Surrey 259",
        "sector": "Education",
        "url": "https://www.surrey.ac.uk"
    },
    {
        "name": "University of Kent 260",
        "sector": "Education",
        "url": "https://www.kent.ac.uk"
    },
    {
        "name": "University of Reading 261",
        "sector": "Education",
        "url": "https://www.reading.ac.uk"
    },
    {
        "name": "University of Warwick 262",
        "sector": "Education",
        "url": "https://www.warwick.ac.uk"
    },
    {
        "name": "University of Coventry 263",
        "sector": "Education",
        "url": "https://www.coventry.ac.uk"
    },
    {
        "name": "University of Bham 264",
        "sector": "Education",
        "url": "https://www.bham.ac.uk"
    },
    {
        "name": "University of Aston 265",
        "sector": "Education",
        "url": "https://www.aston.ac.uk"
    },
    {
        "name": "University of Ntu 266",
        "sector": "Education",
        "url": "https://www.ntu.ac.uk"
    },
    {
        "name": "University of Nottingham 267",
        "sector": "Education",
        "url": "https://www.nottingham.ac.uk"
    },
    {
        "name": "University of Leicester 268",
        "sector": "Education",
        "url": "https://www.leicester.ac.uk"
    },
    {
        "name": "University of Dmu 269",
        "sector": "Education",
        "url": "https://www.dmu.ac.uk"
    },
    {
        "name": "University of Lboro 270",
        "sector": "Education",
        "url": "https://www.lboro.ac.uk"
    },
    {
        "name": "University of Shef 271",
        "sector": "Education",
        "url": "https://www.shef.ac.uk"
    },
    {
        "name": "University of Shu 272",
        "sector": "Education",
        "url": "https://www.shu.ac.uk"
    },
    {
        "name": "University of Leeds 273",
        "sector": "Education",
        "url": "https://www.leeds.ac.uk"
    },
    {
        "name": "University of Leedsbeckett 274",
        "sector": "Education",
        "url": "https://www.leedsbeckett.ac.uk"
    },
    {
        "name": "University of York 275",
        "sector": "Education",
        "url": "https://www.york.ac.uk"
    },
    {
        "name": "University of Hull 276",
        "sector": "Education",
        "url": "https://www.hull.ac.uk"
    },
    {
        "name": "University of Ncl 277",
        "sector": "Education",
        "url": "https://www.ncl.ac.uk"
    },
    {
        "name": "University of Northumbria 278",
        "sector": "Education",
        "url": "https://www.northumbria.ac.uk"
    },
    {
        "name": "University of Durham 279",
        "sector": "Education",
        "url": "https://www.durham.ac.uk"
    },
    {
        "name": "University of Sunderland 280",
        "sector": "Education",
        "url": "https://www.sunderland.ac.uk"
    },
    {
        "name": "University of Tees 281",
        "sector": "Education",
        "url": "https://www.tees.ac.uk"
    },
    {
        "name": "University of Lancs 282",
        "sector": "Education",
        "url": "https://www.lancs.ac.uk"
    },
    {
        "name": "University of Uclan 283",
        "sector": "Education",
        "url": "https://www.uclan.ac.uk"
    },
    {
        "name": "University of Liv 284",
        "sector": "Education",
        "url": "https://www.liv.ac.uk"
    },
    {
        "name": "University of Ljmu 285",
        "sector": "Education",
        "url": "https://www.ljmu.ac.uk"
    },
    {
        "name": "University of Mmu 286",
        "sector": "Education",
        "url": "https://www.mmu.ac.uk"
    },
    {
        "name": "University of Keele 287",
        "sector": "Education",
        "url": "https://www.keele.ac.uk"
    },
    {
        "name": "University of Staffs 288",
        "sector": "Education",
        "url": "https://www.staffs.ac.uk"
    },
    {
        "name": "University of Chester 289",
        "sector": "Education",
        "url": "https://www.chester.ac.uk"
    },
    {
        "name": "University of Edgehill 290",
        "sector": "Education",
        "url": "https://www.edgehill.ac.uk"
    },
    {
        "name": "University of Cumbria 291",
        "sector": "Education",
        "url": "https://www.cumbria.ac.uk"
    },
    {
        "name": "University of Ox 292",
        "sector": "Education",
        "url": "https://www.ox.ac.uk"
    },
    {
        "name": "University of Cam 293",
        "sector": "Education",
        "url": "https://www.cam.ac.uk"
    },
    {
        "name": "University of Ucl 294",
        "sector": "Education",
        "url": "https://www.ucl.ac.uk"
    },
    {
        "name": "University of Ic 295",
        "sector": "Education",
        "url": "https://www.ic.ac.uk"
    },
    {
        "name": "University of Kcl 296",
        "sector": "Education",
        "url": "https://www.kcl.ac.uk"
    },
    {
        "name": "University of Lse 297",
        "sector": "Education",
        "url": "https://www.lse.ac.uk"
    },
    {
        "name": "University of Qmul 298",
        "sector": "Education",
        "url": "https://www.qmul.ac.uk"
    },
    {
        "name": "University of Man 299",
        "sector": "Education",
        "url": "https://www.man.ac.uk"
    },
    {
        "name": "Techsystems UK",
        "sector": "Private Tech",
        "url": "https://www.techsystems.com/careers"
    },
    {
        "name": "Techtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.techtechnologies.io/careers"
    },
    {
        "name": "Techconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.techconsulting.tech/careers"
    },
    {
        "name": "Techservices UK",
        "sector": "Private Tech",
        "url": "https://www.techservices.net/careers"
    },
    {
        "name": "Technetworks UK",
        "sector": "Private Tech",
        "url": "https://www.technetworks.co.uk/careers"
    },
    {
        "name": "Techgroup UK",
        "sector": "Private Tech",
        "url": "https://www.techgroup.com/careers"
    },
    {
        "name": "Techdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.techdynamics.io/careers"
    },
    {
        "name": "Techpartners UK",
        "sector": "Private Tech",
        "url": "https://www.techpartners.tech/careers"
    },
    {
        "name": "Techlabs UK",
        "sector": "Private Tech",
        "url": "https://www.techlabs.net/careers"
    },
    {
        "name": "Techanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.techanalytics.co.uk/careers"
    },
    {
        "name": "Techsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.techsoftware.com/careers"
    },
    {
        "name": "Techit UK",
        "sector": "Private Tech",
        "url": "https://www.techIT.io/careers"
    },
    {
        "name": "Softsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.softsolutions.tech/careers"
    },
    {
        "name": "Softsystems UK",
        "sector": "Private Tech",
        "url": "https://www.softsystems.net/careers"
    },
    {
        "name": "Softtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.softtechnologies.co.uk/careers"
    },
    {
        "name": "Softconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.softconsulting.com/careers"
    },
    {
        "name": "Softservices UK",
        "sector": "Private Tech",
        "url": "https://www.softservices.io/careers"
    },
    {
        "name": "Softnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.softnetworks.tech/careers"
    },
    {
        "name": "Softgroup UK",
        "sector": "Private Tech",
        "url": "https://www.softgroup.net/careers"
    },
    {
        "name": "Softdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.softdynamics.co.uk/careers"
    },
    {
        "name": "Softpartners UK",
        "sector": "Private Tech",
        "url": "https://www.softpartners.com/careers"
    },
    {
        "name": "Softlabs UK",
        "sector": "Private Tech",
        "url": "https://www.softlabs.io/careers"
    },
    {
        "name": "Softanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.softanalytics.tech/careers"
    },
    {
        "name": "Softsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.softsoftware.net/careers"
    },
    {
        "name": "Softit UK",
        "sector": "Private Tech",
        "url": "https://www.softIT.co.uk/careers"
    },
    {
        "name": "Datasolutions UK",
        "sector": "Private Tech",
        "url": "https://www.datasolutions.com/careers"
    },
    {
        "name": "Datasystems UK",
        "sector": "Private Tech",
        "url": "https://www.datasystems.io/careers"
    },
    {
        "name": "Datatechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.datatechnologies.tech/careers"
    },
    {
        "name": "Dataconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.dataconsulting.net/careers"
    },
    {
        "name": "Dataservices UK",
        "sector": "Private Tech",
        "url": "https://www.dataservices.co.uk/careers"
    },
    {
        "name": "Datanetworks UK",
        "sector": "Private Tech",
        "url": "https://www.datanetworks.com/careers"
    },
    {
        "name": "Datagroup UK",
        "sector": "Private Tech",
        "url": "https://www.datagroup.io/careers"
    },
    {
        "name": "Datadynamics UK",
        "sector": "Private Tech",
        "url": "https://www.datadynamics.tech/careers"
    },
    {
        "name": "Datapartners UK",
        "sector": "Private Tech",
        "url": "https://www.datapartners.net/careers"
    },
    {
        "name": "Datalabs UK",
        "sector": "Private Tech",
        "url": "https://www.datalabs.co.uk/careers"
    },
    {
        "name": "Dataanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.dataanalytics.com/careers"
    },
    {
        "name": "Datasoftware UK",
        "sector": "Private Tech",
        "url": "https://www.datasoftware.io/careers"
    },
    {
        "name": "Datait UK",
        "sector": "Private Tech",
        "url": "https://www.dataIT.tech/careers"
    },
    {
        "name": "Cloudsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsolutions.net/careers"
    },
    {
        "name": "Cloudsystems UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsystems.co.uk/careers"
    },
    {
        "name": "Cloudtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cloudtechnologies.com/careers"
    },
    {
        "name": "Cloudconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cloudconsulting.io/careers"
    },
    {
        "name": "Cloudservices UK",
        "sector": "Private Tech",
        "url": "https://www.cloudservices.tech/careers"
    },
    {
        "name": "Cloudnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cloudnetworks.net/careers"
    },
    {
        "name": "Cloudgroup UK",
        "sector": "Private Tech",
        "url": "https://www.cloudgroup.co.uk/careers"
    },
    {
        "name": "Clouddynamics UK",
        "sector": "Private Tech",
        "url": "https://www.clouddynamics.com/careers"
    },
    {
        "name": "Cloudpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cloudpartners.io/careers"
    },
    {
        "name": "Cloudlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cloudlabs.tech/careers"
    },
    {
        "name": "Cloudanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cloudanalytics.net/careers"
    },
    {
        "name": "Cloudsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsoftware.co.uk/careers"
    },
    {
        "name": "Cloudit UK",
        "sector": "Private Tech",
        "url": "https://www.cloudIT.com/careers"
    },
    {
        "name": "Cybersolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cybersolutions.io/careers"
    },
    {
        "name": "Cybersystems UK",
        "sector": "Private Tech",
        "url": "https://www.cybersystems.tech/careers"
    },
    {
        "name": "Cybertechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cybertechnologies.net/careers"
    },
    {
        "name": "Cyberconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cyberconsulting.co.uk/careers"
    },
    {
        "name": "Cyberservices UK",
        "sector": "Private Tech",
        "url": "https://www.cyberservices.com/careers"
    },
    {
        "name": "Cybernetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cybernetworks.io/careers"
    },
    {
        "name": "Cybergroup UK",
        "sector": "Private Tech",
        "url": "https://www.cybergroup.tech/careers"
    },
    {
        "name": "Cyberdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberdynamics.net/careers"
    },
    {
        "name": "Cyberpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cyberpartners.co.uk/careers"
    },
    {
        "name": "Cyberlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cyberlabs.com/careers"
    },
    {
        "name": "Cyberanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberanalytics.io/careers"
    },
    {
        "name": "Cybersoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cybersoftware.tech/careers"
    },
    {
        "name": "Cyberit UK",
        "sector": "Private Tech",
        "url": "https://www.cyberIT.net/careers"
    },
    {
        "name": "Netsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.netsolutions.co.uk/careers"
    },
    {
        "name": "Netsystems UK",
        "sector": "Private Tech",
        "url": "https://www.netsystems.com/careers"
    },
    {
        "name": "Nettechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nettechnologies.io/careers"
    },
    {
        "name": "Netconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.netconsulting.tech/careers"
    },
    {
        "name": "Netservices UK",
        "sector": "Private Tech",
        "url": "https://www.netservices.net/careers"
    },
    {
        "name": "Netnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.netnetworks.co.uk/careers"
    },
    {
        "name": "Netgroup UK",
        "sector": "Private Tech",
        "url": "https://www.netgroup.com/careers"
    },
    {
        "name": "Netdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.netdynamics.io/careers"
    },
    {
        "name": "Netpartners UK",
        "sector": "Private Tech",
        "url": "https://www.netpartners.tech/careers"
    },
    {
        "name": "Netlabs UK",
        "sector": "Private Tech",
        "url": "https://www.netlabs.net/careers"
    },
    {
        "name": "Netanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.netanalytics.co.uk/careers"
    },
    {
        "name": "Netsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.netsoftware.com/careers"
    },
    {
        "name": "Netit UK",
        "sector": "Private Tech",
        "url": "https://www.netIT.io/careers"
    },
    {
        "name": "Websolutions UK",
        "sector": "Private Tech",
        "url": "https://www.websolutions.tech/careers"
    },
    {
        "name": "Websystems UK",
        "sector": "Private Tech",
        "url": "https://www.websystems.net/careers"
    },
    {
        "name": "Webtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.webtechnologies.co.uk/careers"
    },
    {
        "name": "Webconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.webconsulting.com/careers"
    },
    {
        "name": "Webservices UK",
        "sector": "Private Tech",
        "url": "https://www.webservices.io/careers"
    },
    {
        "name": "Webnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.webnetworks.tech/careers"
    },
    {
        "name": "Webgroup UK",
        "sector": "Private Tech",
        "url": "https://www.webgroup.net/careers"
    },
    {
        "name": "Webdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.webdynamics.co.uk/careers"
    },
    {
        "name": "Webpartners UK",
        "sector": "Private Tech",
        "url": "https://www.webpartners.com/careers"
    },
    {
        "name": "Weblabs UK",
        "sector": "Private Tech",
        "url": "https://www.weblabs.io/careers"
    },
    {
        "name": "Webanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.webanalytics.tech/careers"
    },
    {
        "name": "Websoftware UK",
        "sector": "Private Tech",
        "url": "https://www.websoftware.net/careers"
    },
    {
        "name": "Webit UK",
        "sector": "Private Tech",
        "url": "https://www.webIT.co.uk/careers"
    },
    {
        "name": "Appsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.appsolutions.com/careers"
    },
    {
        "name": "Appsystems UK",
        "sector": "Private Tech",
        "url": "https://www.appsystems.io/careers"
    },
    {
        "name": "Apptechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.apptechnologies.tech/careers"
    },
    {
        "name": "Appconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.appconsulting.net/careers"
    },
    {
        "name": "Appservices UK",
        "sector": "Private Tech",
        "url": "https://www.appservices.co.uk/careers"
    },
    {
        "name": "Appnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.appnetworks.com/careers"
    },
    {
        "name": "Appgroup UK",
        "sector": "Private Tech",
        "url": "https://www.appgroup.io/careers"
    },
    {
        "name": "Appdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.appdynamics.tech/careers"
    },
    {
        "name": "Apppartners UK",
        "sector": "Private Tech",
        "url": "https://www.apppartners.net/careers"
    },
    {
        "name": "Applabs UK",
        "sector": "Private Tech",
        "url": "https://www.applabs.co.uk/careers"
    },
    {
        "name": "Appanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.appanalytics.com/careers"
    },
    {
        "name": "Appsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.appsoftware.io/careers"
    },
    {
        "name": "Appit UK",
        "sector": "Private Tech",
        "url": "https://www.appIT.tech/careers"
    },
    {
        "name": "Logicsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.logicsolutions.net/careers"
    },
    {
        "name": "Logicsystems UK",
        "sector": "Private Tech",
        "url": "https://www.logicsystems.co.uk/careers"
    },
    {
        "name": "Logictechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.logictechnologies.com/careers"
    },
    {
        "name": "Logicconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.logicconsulting.io/careers"
    },
    {
        "name": "Logicservices UK",
        "sector": "Private Tech",
        "url": "https://www.logicservices.tech/careers"
    },
    {
        "name": "Logicnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.logicnetworks.net/careers"
    },
    {
        "name": "Logicgroup UK",
        "sector": "Private Tech",
        "url": "https://www.logicgroup.co.uk/careers"
    },
    {
        "name": "Logicdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.logicdynamics.com/careers"
    },
    {
        "name": "Logicpartners UK",
        "sector": "Private Tech",
        "url": "https://www.logicpartners.io/careers"
    },
    {
        "name": "Logiclabs UK",
        "sector": "Private Tech",
        "url": "https://www.logiclabs.tech/careers"
    },
    {
        "name": "Logicanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.logicanalytics.net/careers"
    },
    {
        "name": "Logicsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.logicsoftware.co.uk/careers"
    },
    {
        "name": "Logicit UK",
        "sector": "Private Tech",
        "url": "https://www.logicIT.com/careers"
    },
    {
        "name": "Syssolutions UK",
        "sector": "Private Tech",
        "url": "https://www.syssolutions.io/careers"
    },
    {
        "name": "Syssystems UK",
        "sector": "Private Tech",
        "url": "https://www.syssystems.tech/careers"
    },
    {
        "name": "Systechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.systechnologies.net/careers"
    },
    {
        "name": "Sysconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.sysconsulting.co.uk/careers"
    },
    {
        "name": "Sysservices UK",
        "sector": "Private Tech",
        "url": "https://www.sysservices.com/careers"
    },
    {
        "name": "Sysnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.sysnetworks.io/careers"
    },
    {
        "name": "Sysgroup UK",
        "sector": "Private Tech",
        "url": "https://www.sysgroup.tech/careers"
    },
    {
        "name": "Sysdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.sysdynamics.net/careers"
    },
    {
        "name": "Syspartners UK",
        "sector": "Private Tech",
        "url": "https://www.syspartners.co.uk/careers"
    },
    {
        "name": "Syslabs UK",
        "sector": "Private Tech",
        "url": "https://www.syslabs.com/careers"
    },
    {
        "name": "Sysanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.sysanalytics.io/careers"
    },
    {
        "name": "Syssoftware UK",
        "sector": "Private Tech",
        "url": "https://www.syssoftware.tech/careers"
    },
    {
        "name": "Sysit UK",
        "sector": "Private Tech",
        "url": "https://www.sysIT.net/careers"
    },
    {
        "name": "Codesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.codesolutions.co.uk/careers"
    },
    {
        "name": "Codesystems UK",
        "sector": "Private Tech",
        "url": "https://www.codesystems.com/careers"
    },
    {
        "name": "Codetechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.codetechnologies.io/careers"
    },
    {
        "name": "Codeconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.codeconsulting.tech/careers"
    },
    {
        "name": "Codeservices UK",
        "sector": "Private Tech",
        "url": "https://www.codeservices.net/careers"
    },
    {
        "name": "Codenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.codenetworks.co.uk/careers"
    },
    {
        "name": "Codegroup UK",
        "sector": "Private Tech",
        "url": "https://www.codegroup.com/careers"
    },
    {
        "name": "Codedynamics UK",
        "sector": "Private Tech",
        "url": "https://www.codedynamics.io/careers"
    },
    {
        "name": "Codepartners UK",
        "sector": "Private Tech",
        "url": "https://www.codepartners.tech/careers"
    },
    {
        "name": "Codelabs UK",
        "sector": "Private Tech",
        "url": "https://www.codelabs.net/careers"
    },
    {
        "name": "Codeanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.codeanalytics.co.uk/careers"
    },
    {
        "name": "Codesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.codesoftware.com/careers"
    },
    {
        "name": "Codeit UK",
        "sector": "Private Tech",
        "url": "https://www.codeIT.io/careers"
    },
    {
        "name": "Aisolutions UK",
        "sector": "Private Tech",
        "url": "https://www.aisolutions.tech/careers"
    },
    {
        "name": "Aisystems UK",
        "sector": "Private Tech",
        "url": "https://www.aisystems.net/careers"
    },
    {
        "name": "Aitechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.aitechnologies.co.uk/careers"
    },
    {
        "name": "Aiconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.aiconsulting.com/careers"
    },
    {
        "name": "Aiservices UK",
        "sector": "Private Tech",
        "url": "https://www.aiservices.io/careers"
    },
    {
        "name": "Ainetworks UK",
        "sector": "Private Tech",
        "url": "https://www.ainetworks.tech/careers"
    },
    {
        "name": "Aigroup UK",
        "sector": "Private Tech",
        "url": "https://www.aigroup.net/careers"
    },
    {
        "name": "Aidynamics UK",
        "sector": "Private Tech",
        "url": "https://www.aidynamics.co.uk/careers"
    },
    {
        "name": "Aipartners UK",
        "sector": "Private Tech",
        "url": "https://www.aipartners.com/careers"
    },
    {
        "name": "Ailabs UK",
        "sector": "Private Tech",
        "url": "https://www.ailabs.io/careers"
    },
    {
        "name": "Aianalytics UK",
        "sector": "Private Tech",
        "url": "https://www.aianalytics.tech/careers"
    },
    {
        "name": "Aisoftware UK",
        "sector": "Private Tech",
        "url": "https://www.aisoftware.net/careers"
    },
    {
        "name": "Aiit UK",
        "sector": "Private Tech",
        "url": "https://www.aiIT.co.uk/careers"
    },
    {
        "name": "Smartsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.smartsolutions.com/careers"
    },
    {
        "name": "Smartsystems UK",
        "sector": "Private Tech",
        "url": "https://www.smartsystems.io/careers"
    },
    {
        "name": "Smarttechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.smarttechnologies.tech/careers"
    },
    {
        "name": "Smartconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.smartconsulting.net/careers"
    },
    {
        "name": "Smartservices UK",
        "sector": "Private Tech",
        "url": "https://www.smartservices.co.uk/careers"
    },
    {
        "name": "Smartnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.smartnetworks.com/careers"
    },
    {
        "name": "Smartgroup UK",
        "sector": "Private Tech",
        "url": "https://www.smartgroup.io/careers"
    },
    {
        "name": "Smartdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.smartdynamics.tech/careers"
    },
    {
        "name": "Smartpartners UK",
        "sector": "Private Tech",
        "url": "https://www.smartpartners.net/careers"
    },
    {
        "name": "Smartlabs UK",
        "sector": "Private Tech",
        "url": "https://www.smartlabs.co.uk/careers"
    },
    {
        "name": "Smartanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.smartanalytics.com/careers"
    },
    {
        "name": "Smartsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.smartsoftware.io/careers"
    },
    {
        "name": "Smartit UK",
        "sector": "Private Tech",
        "url": "https://www.smartIT.tech/careers"
    },
    {
        "name": "Digitalsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsolutions.net/careers"
    },
    {
        "name": "Digitalsystems UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsystems.co.uk/careers"
    },
    {
        "name": "Digitaltechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.digitaltechnologies.com/careers"
    },
    {
        "name": "Digitalconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.digitalconsulting.io/careers"
    },
    {
        "name": "Digitalservices UK",
        "sector": "Private Tech",
        "url": "https://www.digitalservices.tech/careers"
    },
    {
        "name": "Digitalnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.digitalnetworks.net/careers"
    },
    {
        "name": "Digitalgroup UK",
        "sector": "Private Tech",
        "url": "https://www.digitalgroup.co.uk/careers"
    },
    {
        "name": "Digitaldynamics UK",
        "sector": "Private Tech",
        "url": "https://www.digitaldynamics.com/careers"
    },
    {
        "name": "Digitalpartners UK",
        "sector": "Private Tech",
        "url": "https://www.digitalpartners.io/careers"
    },
    {
        "name": "Digitallabs UK",
        "sector": "Private Tech",
        "url": "https://www.digitallabs.tech/careers"
    },
    {
        "name": "Digitalanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.digitalanalytics.net/careers"
    },
    {
        "name": "Digitalsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsoftware.co.uk/careers"
    },
    {
        "name": "Digitalit UK",
        "sector": "Private Tech",
        "url": "https://www.digitalIT.com/careers"
    },
    {
        "name": "Prosolutions UK",
        "sector": "Private Tech",
        "url": "https://www.prosolutions.io/careers"
    },
    {
        "name": "Prosystems UK",
        "sector": "Private Tech",
        "url": "https://www.prosystems.tech/careers"
    },
    {
        "name": "Protechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.protechnologies.net/careers"
    },
    {
        "name": "Proconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.proconsulting.co.uk/careers"
    },
    {
        "name": "Proservices UK",
        "sector": "Private Tech",
        "url": "https://www.proservices.com/careers"
    },
    {
        "name": "Pronetworks UK",
        "sector": "Private Tech",
        "url": "https://www.pronetworks.io/careers"
    },
    {
        "name": "Progroup UK",
        "sector": "Private Tech",
        "url": "https://www.progroup.tech/careers"
    },
    {
        "name": "Prodynamics UK",
        "sector": "Private Tech",
        "url": "https://www.prodynamics.net/careers"
    },
    {
        "name": "Propartners UK",
        "sector": "Private Tech",
        "url": "https://www.propartners.co.uk/careers"
    },
    {
        "name": "Prolabs UK",
        "sector": "Private Tech",
        "url": "https://www.prolabs.com/careers"
    },
    {
        "name": "Proanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.proanalytics.io/careers"
    },
    {
        "name": "Prosoftware UK",
        "sector": "Private Tech",
        "url": "https://www.prosoftware.tech/careers"
    },
    {
        "name": "Proit UK",
        "sector": "Private Tech",
        "url": "https://www.proIT.net/careers"
    },
    {
        "name": "Nextsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.nextsolutions.co.uk/careers"
    },
    {
        "name": "Nextsystems UK",
        "sector": "Private Tech",
        "url": "https://www.nextsystems.com/careers"
    },
    {
        "name": "Nexttechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nexttechnologies.io/careers"
    },
    {
        "name": "Nextconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.nextconsulting.tech/careers"
    },
    {
        "name": "Nextservices UK",
        "sector": "Private Tech",
        "url": "https://www.nextservices.net/careers"
    },
    {
        "name": "Nextnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.nextnetworks.co.uk/careers"
    },
    {
        "name": "Nextgroup UK",
        "sector": "Private Tech",
        "url": "https://www.nextgroup.com/careers"
    },
    {
        "name": "Nextdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.nextdynamics.io/careers"
    },
    {
        "name": "Nextpartners UK",
        "sector": "Private Tech",
        "url": "https://www.nextpartners.tech/careers"
    },
    {
        "name": "Nextlabs UK",
        "sector": "Private Tech",
        "url": "https://www.nextlabs.net/careers"
    },
    {
        "name": "Nextanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.nextanalytics.co.uk/careers"
    },
    {
        "name": "Nextsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.nextsoftware.com/careers"
    },
    {
        "name": "Nextit UK",
        "sector": "Private Tech",
        "url": "https://www.nextIT.io/careers"
    },
    {
        "name": "Coresolutions UK",
        "sector": "Private Tech",
        "url": "https://www.coresolutions.tech/careers"
    },
    {
        "name": "Coresystems UK",
        "sector": "Private Tech",
        "url": "https://www.coresystems.net/careers"
    },
    {
        "name": "Coretechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.coretechnologies.co.uk/careers"
    },
    {
        "name": "Coreconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.coreconsulting.com/careers"
    },
    {
        "name": "Coreservices UK",
        "sector": "Private Tech",
        "url": "https://www.coreservices.io/careers"
    },
    {
        "name": "Corenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.corenetworks.tech/careers"
    },
    {
        "name": "Coregroup UK",
        "sector": "Private Tech",
        "url": "https://www.coregroup.net/careers"
    },
    {
        "name": "Coredynamics UK",
        "sector": "Private Tech",
        "url": "https://www.coredynamics.co.uk/careers"
    },
    {
        "name": "Corepartners UK",
        "sector": "Private Tech",
        "url": "https://www.corepartners.com/careers"
    },
    {
        "name": "Corelabs UK",
        "sector": "Private Tech",
        "url": "https://www.corelabs.io/careers"
    },
    {
        "name": "Coreanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.coreanalytics.tech/careers"
    },
    {
        "name": "Coresoftware UK",
        "sector": "Private Tech",
        "url": "https://www.coresoftware.net/careers"
    },
    {
        "name": "Coreit UK",
        "sector": "Private Tech",
        "url": "https://www.coreIT.co.uk/careers"
    },
    {
        "name": "Innovatesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesolutions.com/careers"
    },
    {
        "name": "Innovatesystems UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesystems.io/careers"
    },
    {
        "name": "Innovatetechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.innovatetechnologies.tech/careers"
    },
    {
        "name": "Innovateconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.innovateconsulting.net/careers"
    },
    {
        "name": "Innovateservices UK",
        "sector": "Private Tech",
        "url": "https://www.innovateservices.co.uk/careers"
    },
    {
        "name": "Innovatenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.innovatenetworks.com/careers"
    },
    {
        "name": "Innovategroup UK",
        "sector": "Private Tech",
        "url": "https://www.innovategroup.io/careers"
    },
    {
        "name": "Innovatedynamics UK",
        "sector": "Private Tech",
        "url": "https://www.innovatedynamics.tech/careers"
    },
    {
        "name": "Innovatepartners UK",
        "sector": "Private Tech",
        "url": "https://www.innovatepartners.net/careers"
    },
    {
        "name": "Innovatelabs UK",
        "sector": "Private Tech",
        "url": "https://www.innovatelabs.co.uk/careers"
    },
    {
        "name": "Innovateanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.innovateanalytics.com/careers"
    },
    {
        "name": "Innovatesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesoftware.io/careers"
    },
    {
        "name": "Innovateit UK",
        "sector": "Private Tech",
        "url": "https://www.innovateIT.tech/careers"
    },
    {
        "name": "Agilesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.agilesolutions.net/careers"
    },
    {
        "name": "Agilesystems UK",
        "sector": "Private Tech",
        "url": "https://www.agilesystems.co.uk/careers"
    },
    {
        "name": "Agiletechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.agiletechnologies.com/careers"
    },
    {
        "name": "Agileconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.agileconsulting.io/careers"
    },
    {
        "name": "Agileservices UK",
        "sector": "Private Tech",
        "url": "https://www.agileservices.tech/careers"
    },
    {
        "name": "Agilenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.agilenetworks.net/careers"
    },
    {
        "name": "Agilegroup UK",
        "sector": "Private Tech",
        "url": "https://www.agilegroup.co.uk/careers"
    },
    {
        "name": "Agiledynamics UK",
        "sector": "Private Tech",
        "url": "https://www.agiledynamics.com/careers"
    },
    {
        "name": "Agilepartners UK",
        "sector": "Private Tech",
        "url": "https://www.agilepartners.io/careers"
    },
    {
        "name": "Agilelabs UK",
        "sector": "Private Tech",
        "url": "https://www.agilelabs.tech/careers"
    },
    {
        "name": "Agileanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.agileanalytics.net/careers"
    },
    {
        "name": "Agilesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.agilesoftware.co.uk/careers"
    },
    {
        "name": "Agileit UK",
        "sector": "Private Tech",
        "url": "https://www.agileIT.com/careers"
    },
    {
        "name": "Nexussolutions UK",
        "sector": "Private Tech",
        "url": "https://www.nexussolutions.io/careers"
    },
    {
        "name": "Nexussystems UK",
        "sector": "Private Tech",
        "url": "https://www.nexussystems.tech/careers"
    },
    {
        "name": "Nexustechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nexustechnologies.net/careers"
    },
    {
        "name": "Nexusconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.nexusconsulting.co.uk/careers"
    },
    {
        "name": "Nexusservices UK",
        "sector": "Private Tech",
        "url": "https://www.nexusservices.com/careers"
    },
    {
        "name": "Nexusnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.nexusnetworks.io/careers"
    },
    {
        "name": "Nexusgroup UK",
        "sector": "Private Tech",
        "url": "https://www.nexusgroup.tech/careers"
    },
    {
        "name": "Nexusdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.nexusdynamics.net/careers"
    },
    {
        "name": "Nexuspartners UK",
        "sector": "Private Tech",
        "url": "https://www.nexuspartners.co.uk/careers"
    },
    {
        "name": "Nexuslabs UK",
        "sector": "Private Tech",
        "url": "https://www.nexuslabs.com/careers"
    },
    {
        "name": "Nexusanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.nexusanalytics.io/careers"
    },
    {
        "name": "Nexussoftware UK",
        "sector": "Private Tech",
        "url": "https://www.nexussoftware.tech/careers"
    },
    {
        "name": "Nexusit UK",
        "sector": "Private Tech",
        "url": "https://www.nexusIT.net/careers"
    },
    {
        "name": "Techsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.techsolutions.co.uk/careers"
    },
    {
        "name": "Techsystems UK",
        "sector": "Private Tech",
        "url": "https://www.techsystems.com/careers"
    },
    {
        "name": "Techtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.techtechnologies.io/careers"
    },
    {
        "name": "Techconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.techconsulting.tech/careers"
    },
    {
        "name": "Techservices UK",
        "sector": "Private Tech",
        "url": "https://www.techservices.net/careers"
    },
    {
        "name": "Technetworks UK",
        "sector": "Private Tech",
        "url": "https://www.technetworks.co.uk/careers"
    },
    {
        "name": "Techgroup UK",
        "sector": "Private Tech",
        "url": "https://www.techgroup.com/careers"
    },
    {
        "name": "Techdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.techdynamics.io/careers"
    },
    {
        "name": "Techpartners UK",
        "sector": "Private Tech",
        "url": "https://www.techpartners.tech/careers"
    },
    {
        "name": "Techlabs UK",
        "sector": "Private Tech",
        "url": "https://www.techlabs.net/careers"
    },
    {
        "name": "Techanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.techanalytics.co.uk/careers"
    },
    {
        "name": "Techsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.techsoftware.com/careers"
    },
    {
        "name": "Techit UK",
        "sector": "Private Tech",
        "url": "https://www.techIT.io/careers"
    },
    {
        "name": "Softsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.softsolutions.tech/careers"
    },
    {
        "name": "Softsystems UK",
        "sector": "Private Tech",
        "url": "https://www.softsystems.net/careers"
    },
    {
        "name": "Softtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.softtechnologies.co.uk/careers"
    },
    {
        "name": "Softconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.softconsulting.com/careers"
    },
    {
        "name": "Softservices UK",
        "sector": "Private Tech",
        "url": "https://www.softservices.io/careers"
    },
    {
        "name": "Softnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.softnetworks.tech/careers"
    },
    {
        "name": "Softgroup UK",
        "sector": "Private Tech",
        "url": "https://www.softgroup.net/careers"
    },
    {
        "name": "Softdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.softdynamics.co.uk/careers"
    },
    {
        "name": "Softpartners UK",
        "sector": "Private Tech",
        "url": "https://www.softpartners.com/careers"
    },
    {
        "name": "Softlabs UK",
        "sector": "Private Tech",
        "url": "https://www.softlabs.io/careers"
    },
    {
        "name": "Softanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.softanalytics.tech/careers"
    },
    {
        "name": "Softsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.softsoftware.net/careers"
    },
    {
        "name": "Softit UK",
        "sector": "Private Tech",
        "url": "https://www.softIT.co.uk/careers"
    },
    {
        "name": "Datasolutions UK",
        "sector": "Private Tech",
        "url": "https://www.datasolutions.com/careers"
    },
    {
        "name": "Datasystems UK",
        "sector": "Private Tech",
        "url": "https://www.datasystems.io/careers"
    },
    {
        "name": "Datatechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.datatechnologies.tech/careers"
    },
    {
        "name": "Dataconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.dataconsulting.net/careers"
    },
    {
        "name": "Dataservices UK",
        "sector": "Private Tech",
        "url": "https://www.dataservices.co.uk/careers"
    },
    {
        "name": "Datanetworks UK",
        "sector": "Private Tech",
        "url": "https://www.datanetworks.com/careers"
    },
    {
        "name": "Datagroup UK",
        "sector": "Private Tech",
        "url": "https://www.datagroup.io/careers"
    },
    {
        "name": "Datadynamics UK",
        "sector": "Private Tech",
        "url": "https://www.datadynamics.tech/careers"
    },
    {
        "name": "Datapartners UK",
        "sector": "Private Tech",
        "url": "https://www.datapartners.net/careers"
    },
    {
        "name": "Datalabs UK",
        "sector": "Private Tech",
        "url": "https://www.datalabs.co.uk/careers"
    },
    {
        "name": "Dataanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.dataanalytics.com/careers"
    },
    {
        "name": "Datasoftware UK",
        "sector": "Private Tech",
        "url": "https://www.datasoftware.io/careers"
    },
    {
        "name": "Datait UK",
        "sector": "Private Tech",
        "url": "https://www.dataIT.tech/careers"
    },
    {
        "name": "Cloudsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsolutions.net/careers"
    },
    {
        "name": "Cloudsystems UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsystems.co.uk/careers"
    },
    {
        "name": "Cloudtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cloudtechnologies.com/careers"
    },
    {
        "name": "Cloudconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cloudconsulting.io/careers"
    },
    {
        "name": "Cloudservices UK",
        "sector": "Private Tech",
        "url": "https://www.cloudservices.tech/careers"
    },
    {
        "name": "Cloudnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cloudnetworks.net/careers"
    },
    {
        "name": "Cloudgroup UK",
        "sector": "Private Tech",
        "url": "https://www.cloudgroup.co.uk/careers"
    },
    {
        "name": "Clouddynamics UK",
        "sector": "Private Tech",
        "url": "https://www.clouddynamics.com/careers"
    },
    {
        "name": "Cloudpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cloudpartners.io/careers"
    },
    {
        "name": "Cloudlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cloudlabs.tech/careers"
    },
    {
        "name": "Cloudanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cloudanalytics.net/careers"
    },
    {
        "name": "Cloudsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsoftware.co.uk/careers"
    },
    {
        "name": "Cloudit UK",
        "sector": "Private Tech",
        "url": "https://www.cloudIT.com/careers"
    },
    {
        "name": "Cybersolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cybersolutions.io/careers"
    },
    {
        "name": "Cybersystems UK",
        "sector": "Private Tech",
        "url": "https://www.cybersystems.tech/careers"
    },
    {
        "name": "Cybertechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cybertechnologies.net/careers"
    },
    {
        "name": "Cyberconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cyberconsulting.co.uk/careers"
    },
    {
        "name": "Cyberservices UK",
        "sector": "Private Tech",
        "url": "https://www.cyberservices.com/careers"
    },
    {
        "name": "Cybernetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cybernetworks.io/careers"
    },
    {
        "name": "Cybergroup UK",
        "sector": "Private Tech",
        "url": "https://www.cybergroup.tech/careers"
    },
    {
        "name": "Cyberdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberdynamics.net/careers"
    },
    {
        "name": "Cyberpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cyberpartners.co.uk/careers"
    },
    {
        "name": "Cyberlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cyberlabs.com/careers"
    },
    {
        "name": "Cyberanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberanalytics.io/careers"
    },
    {
        "name": "Cybersoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cybersoftware.tech/careers"
    },
    {
        "name": "Cyberit UK",
        "sector": "Private Tech",
        "url": "https://www.cyberIT.net/careers"
    },
    {
        "name": "Netsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.netsolutions.co.uk/careers"
    },
    {
        "name": "Netsystems UK",
        "sector": "Private Tech",
        "url": "https://www.netsystems.com/careers"
    },
    {
        "name": "Nettechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nettechnologies.io/careers"
    },
    {
        "name": "Netconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.netconsulting.tech/careers"
    },
    {
        "name": "Netservices UK",
        "sector": "Private Tech",
        "url": "https://www.netservices.net/careers"
    },
    {
        "name": "Netnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.netnetworks.co.uk/careers"
    },
    {
        "name": "Netgroup UK",
        "sector": "Private Tech",
        "url": "https://www.netgroup.com/careers"
    },
    {
        "name": "Netdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.netdynamics.io/careers"
    },
    {
        "name": "Netpartners UK",
        "sector": "Private Tech",
        "url": "https://www.netpartners.tech/careers"
    },
    {
        "name": "Netlabs UK",
        "sector": "Private Tech",
        "url": "https://www.netlabs.net/careers"
    },
    {
        "name": "Netanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.netanalytics.co.uk/careers"
    },
    {
        "name": "Netsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.netsoftware.com/careers"
    },
    {
        "name": "Netit UK",
        "sector": "Private Tech",
        "url": "https://www.netIT.io/careers"
    },
    {
        "name": "Websolutions UK",
        "sector": "Private Tech",
        "url": "https://www.websolutions.tech/careers"
    },
    {
        "name": "Websystems UK",
        "sector": "Private Tech",
        "url": "https://www.websystems.net/careers"
    },
    {
        "name": "Webtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.webtechnologies.co.uk/careers"
    },
    {
        "name": "Webconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.webconsulting.com/careers"
    },
    {
        "name": "Webservices UK",
        "sector": "Private Tech",
        "url": "https://www.webservices.io/careers"
    },
    {
        "name": "Webnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.webnetworks.tech/careers"
    },
    {
        "name": "Webgroup UK",
        "sector": "Private Tech",
        "url": "https://www.webgroup.net/careers"
    },
    {
        "name": "Webdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.webdynamics.co.uk/careers"
    },
    {
        "name": "Webpartners UK",
        "sector": "Private Tech",
        "url": "https://www.webpartners.com/careers"
    },
    {
        "name": "Weblabs UK",
        "sector": "Private Tech",
        "url": "https://www.weblabs.io/careers"
    },
    {
        "name": "Webanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.webanalytics.tech/careers"
    },
    {
        "name": "Websoftware UK",
        "sector": "Private Tech",
        "url": "https://www.websoftware.net/careers"
    },
    {
        "name": "Webit UK",
        "sector": "Private Tech",
        "url": "https://www.webIT.co.uk/careers"
    },
    {
        "name": "Appsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.appsolutions.com/careers"
    },
    {
        "name": "Appsystems UK",
        "sector": "Private Tech",
        "url": "https://www.appsystems.io/careers"
    },
    {
        "name": "Apptechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.apptechnologies.tech/careers"
    },
    {
        "name": "Appconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.appconsulting.net/careers"
    },
    {
        "name": "Appservices UK",
        "sector": "Private Tech",
        "url": "https://www.appservices.co.uk/careers"
    },
    {
        "name": "Appnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.appnetworks.com/careers"
    },
    {
        "name": "Appgroup UK",
        "sector": "Private Tech",
        "url": "https://www.appgroup.io/careers"
    },
    {
        "name": "Appdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.appdynamics.tech/careers"
    },
    {
        "name": "Apppartners UK",
        "sector": "Private Tech",
        "url": "https://www.apppartners.net/careers"
    },
    {
        "name": "Applabs UK",
        "sector": "Private Tech",
        "url": "https://www.applabs.co.uk/careers"
    },
    {
        "name": "Appanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.appanalytics.com/careers"
    },
    {
        "name": "Appsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.appsoftware.io/careers"
    },
    {
        "name": "Appit UK",
        "sector": "Private Tech",
        "url": "https://www.appIT.tech/careers"
    },
    {
        "name": "Logicsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.logicsolutions.net/careers"
    },
    {
        "name": "Logicsystems UK",
        "sector": "Private Tech",
        "url": "https://www.logicsystems.co.uk/careers"
    },
    {
        "name": "Logictechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.logictechnologies.com/careers"
    },
    {
        "name": "Logicconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.logicconsulting.io/careers"
    },
    {
        "name": "Logicservices UK",
        "sector": "Private Tech",
        "url": "https://www.logicservices.tech/careers"
    },
    {
        "name": "Logicnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.logicnetworks.net/careers"
    },
    {
        "name": "Logicgroup UK",
        "sector": "Private Tech",
        "url": "https://www.logicgroup.co.uk/careers"
    },
    {
        "name": "Logicdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.logicdynamics.com/careers"
    },
    {
        "name": "Logicpartners UK",
        "sector": "Private Tech",
        "url": "https://www.logicpartners.io/careers"
    },
    {
        "name": "Logiclabs UK",
        "sector": "Private Tech",
        "url": "https://www.logiclabs.tech/careers"
    },
    {
        "name": "Logicanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.logicanalytics.net/careers"
    },
    {
        "name": "Logicsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.logicsoftware.co.uk/careers"
    },
    {
        "name": "Logicit UK",
        "sector": "Private Tech",
        "url": "https://www.logicIT.com/careers"
    },
    {
        "name": "Syssolutions UK",
        "sector": "Private Tech",
        "url": "https://www.syssolutions.io/careers"
    },
    {
        "name": "Syssystems UK",
        "sector": "Private Tech",
        "url": "https://www.syssystems.tech/careers"
    },
    {
        "name": "Systechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.systechnologies.net/careers"
    },
    {
        "name": "Sysconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.sysconsulting.co.uk/careers"
    },
    {
        "name": "Sysservices UK",
        "sector": "Private Tech",
        "url": "https://www.sysservices.com/careers"
    },
    {
        "name": "Sysnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.sysnetworks.io/careers"
    },
    {
        "name": "Sysgroup UK",
        "sector": "Private Tech",
        "url": "https://www.sysgroup.tech/careers"
    },
    {
        "name": "Sysdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.sysdynamics.net/careers"
    },
    {
        "name": "Syspartners UK",
        "sector": "Private Tech",
        "url": "https://www.syspartners.co.uk/careers"
    },
    {
        "name": "Syslabs UK",
        "sector": "Private Tech",
        "url": "https://www.syslabs.com/careers"
    },
    {
        "name": "Sysanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.sysanalytics.io/careers"
    },
    {
        "name": "Syssoftware UK",
        "sector": "Private Tech",
        "url": "https://www.syssoftware.tech/careers"
    },
    {
        "name": "Sysit UK",
        "sector": "Private Tech",
        "url": "https://www.sysIT.net/careers"
    },
    {
        "name": "Codesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.codesolutions.co.uk/careers"
    },
    {
        "name": "Codesystems UK",
        "sector": "Private Tech",
        "url": "https://www.codesystems.com/careers"
    },
    {
        "name": "Codetechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.codetechnologies.io/careers"
    },
    {
        "name": "Codeconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.codeconsulting.tech/careers"
    },
    {
        "name": "Codeservices UK",
        "sector": "Private Tech",
        "url": "https://www.codeservices.net/careers"
    },
    {
        "name": "Codenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.codenetworks.co.uk/careers"
    },
    {
        "name": "Codegroup UK",
        "sector": "Private Tech",
        "url": "https://www.codegroup.com/careers"
    },
    {
        "name": "Codedynamics UK",
        "sector": "Private Tech",
        "url": "https://www.codedynamics.io/careers"
    },
    {
        "name": "Codepartners UK",
        "sector": "Private Tech",
        "url": "https://www.codepartners.tech/careers"
    },
    {
        "name": "Codelabs UK",
        "sector": "Private Tech",
        "url": "https://www.codelabs.net/careers"
    },
    {
        "name": "Codeanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.codeanalytics.co.uk/careers"
    },
    {
        "name": "Codesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.codesoftware.com/careers"
    },
    {
        "name": "Codeit UK",
        "sector": "Private Tech",
        "url": "https://www.codeIT.io/careers"
    },
    {
        "name": "Aisolutions UK",
        "sector": "Private Tech",
        "url": "https://www.aisolutions.tech/careers"
    },
    {
        "name": "Aisystems UK",
        "sector": "Private Tech",
        "url": "https://www.aisystems.net/careers"
    },
    {
        "name": "Aitechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.aitechnologies.co.uk/careers"
    },
    {
        "name": "Aiconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.aiconsulting.com/careers"
    },
    {
        "name": "Aiservices UK",
        "sector": "Private Tech",
        "url": "https://www.aiservices.io/careers"
    },
    {
        "name": "Ainetworks UK",
        "sector": "Private Tech",
        "url": "https://www.ainetworks.tech/careers"
    },
    {
        "name": "Aigroup UK",
        "sector": "Private Tech",
        "url": "https://www.aigroup.net/careers"
    },
    {
        "name": "Aidynamics UK",
        "sector": "Private Tech",
        "url": "https://www.aidynamics.co.uk/careers"
    },
    {
        "name": "Aipartners UK",
        "sector": "Private Tech",
        "url": "https://www.aipartners.com/careers"
    },
    {
        "name": "Ailabs UK",
        "sector": "Private Tech",
        "url": "https://www.ailabs.io/careers"
    },
    {
        "name": "Aianalytics UK",
        "sector": "Private Tech",
        "url": "https://www.aianalytics.tech/careers"
    },
    {
        "name": "Aisoftware UK",
        "sector": "Private Tech",
        "url": "https://www.aisoftware.net/careers"
    },
    {
        "name": "Aiit UK",
        "sector": "Private Tech",
        "url": "https://www.aiIT.co.uk/careers"
    },
    {
        "name": "Smartsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.smartsolutions.com/careers"
    },
    {
        "name": "Smartsystems UK",
        "sector": "Private Tech",
        "url": "https://www.smartsystems.io/careers"
    },
    {
        "name": "Smarttechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.smarttechnologies.tech/careers"
    },
    {
        "name": "Smartconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.smartconsulting.net/careers"
    },
    {
        "name": "Smartservices UK",
        "sector": "Private Tech",
        "url": "https://www.smartservices.co.uk/careers"
    },
    {
        "name": "Smartnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.smartnetworks.com/careers"
    },
    {
        "name": "Smartgroup UK",
        "sector": "Private Tech",
        "url": "https://www.smartgroup.io/careers"
    },
    {
        "name": "Smartdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.smartdynamics.tech/careers"
    },
    {
        "name": "Smartpartners UK",
        "sector": "Private Tech",
        "url": "https://www.smartpartners.net/careers"
    },
    {
        "name": "Smartlabs UK",
        "sector": "Private Tech",
        "url": "https://www.smartlabs.co.uk/careers"
    },
    {
        "name": "Smartanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.smartanalytics.com/careers"
    },
    {
        "name": "Smartsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.smartsoftware.io/careers"
    },
    {
        "name": "Smartit UK",
        "sector": "Private Tech",
        "url": "https://www.smartIT.tech/careers"
    },
    {
        "name": "Digitalsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsolutions.net/careers"
    },
    {
        "name": "Digitalsystems UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsystems.co.uk/careers"
    },
    {
        "name": "Digitaltechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.digitaltechnologies.com/careers"
    },
    {
        "name": "Digitalconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.digitalconsulting.io/careers"
    },
    {
        "name": "Digitalservices UK",
        "sector": "Private Tech",
        "url": "https://www.digitalservices.tech/careers"
    },
    {
        "name": "Digitalnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.digitalnetworks.net/careers"
    },
    {
        "name": "Digitalgroup UK",
        "sector": "Private Tech",
        "url": "https://www.digitalgroup.co.uk/careers"
    },
    {
        "name": "Digitaldynamics UK",
        "sector": "Private Tech",
        "url": "https://www.digitaldynamics.com/careers"
    },
    {
        "name": "Digitalpartners UK",
        "sector": "Private Tech",
        "url": "https://www.digitalpartners.io/careers"
    },
    {
        "name": "Digitallabs UK",
        "sector": "Private Tech",
        "url": "https://www.digitallabs.tech/careers"
    },
    {
        "name": "Digitalanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.digitalanalytics.net/careers"
    },
    {
        "name": "Digitalsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsoftware.co.uk/careers"
    },
    {
        "name": "Digitalit UK",
        "sector": "Private Tech",
        "url": "https://www.digitalIT.com/careers"
    },
    {
        "name": "Prosolutions UK",
        "sector": "Private Tech",
        "url": "https://www.prosolutions.io/careers"
    },
    {
        "name": "Prosystems UK",
        "sector": "Private Tech",
        "url": "https://www.prosystems.tech/careers"
    },
    {
        "name": "Protechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.protechnologies.net/careers"
    },
    {
        "name": "Proconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.proconsulting.co.uk/careers"
    },
    {
        "name": "Proservices UK",
        "sector": "Private Tech",
        "url": "https://www.proservices.com/careers"
    },
    {
        "name": "Pronetworks UK",
        "sector": "Private Tech",
        "url": "https://www.pronetworks.io/careers"
    },
    {
        "name": "Progroup UK",
        "sector": "Private Tech",
        "url": "https://www.progroup.tech/careers"
    },
    {
        "name": "Prodynamics UK",
        "sector": "Private Tech",
        "url": "https://www.prodynamics.net/careers"
    },
    {
        "name": "Propartners UK",
        "sector": "Private Tech",
        "url": "https://www.propartners.co.uk/careers"
    },
    {
        "name": "Prolabs UK",
        "sector": "Private Tech",
        "url": "https://www.prolabs.com/careers"
    },
    {
        "name": "Proanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.proanalytics.io/careers"
    },
    {
        "name": "Prosoftware UK",
        "sector": "Private Tech",
        "url": "https://www.prosoftware.tech/careers"
    },
    {
        "name": "Proit UK",
        "sector": "Private Tech",
        "url": "https://www.proIT.net/careers"
    },
    {
        "name": "Nextsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.nextsolutions.co.uk/careers"
    },
    {
        "name": "Nextsystems UK",
        "sector": "Private Tech",
        "url": "https://www.nextsystems.com/careers"
    },
    {
        "name": "Nexttechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nexttechnologies.io/careers"
    },
    {
        "name": "Nextconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.nextconsulting.tech/careers"
    },
    {
        "name": "Nextservices UK",
        "sector": "Private Tech",
        "url": "https://www.nextservices.net/careers"
    },
    {
        "name": "Nextnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.nextnetworks.co.uk/careers"
    },
    {
        "name": "Nextgroup UK",
        "sector": "Private Tech",
        "url": "https://www.nextgroup.com/careers"
    },
    {
        "name": "Nextdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.nextdynamics.io/careers"
    },
    {
        "name": "Nextpartners UK",
        "sector": "Private Tech",
        "url": "https://www.nextpartners.tech/careers"
    },
    {
        "name": "Nextlabs UK",
        "sector": "Private Tech",
        "url": "https://www.nextlabs.net/careers"
    },
    {
        "name": "Nextanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.nextanalytics.co.uk/careers"
    },
    {
        "name": "Nextsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.nextsoftware.com/careers"
    },
    {
        "name": "Nextit UK",
        "sector": "Private Tech",
        "url": "https://www.nextIT.io/careers"
    },
    {
        "name": "Coresolutions UK",
        "sector": "Private Tech",
        "url": "https://www.coresolutions.tech/careers"
    },
    {
        "name": "Coresystems UK",
        "sector": "Private Tech",
        "url": "https://www.coresystems.net/careers"
    },
    {
        "name": "Coretechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.coretechnologies.co.uk/careers"
    },
    {
        "name": "Coreconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.coreconsulting.com/careers"
    },
    {
        "name": "Coreservices UK",
        "sector": "Private Tech",
        "url": "https://www.coreservices.io/careers"
    },
    {
        "name": "Corenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.corenetworks.tech/careers"
    },
    {
        "name": "Coregroup UK",
        "sector": "Private Tech",
        "url": "https://www.coregroup.net/careers"
    },
    {
        "name": "Coredynamics UK",
        "sector": "Private Tech",
        "url": "https://www.coredynamics.co.uk/careers"
    },
    {
        "name": "Corepartners UK",
        "sector": "Private Tech",
        "url": "https://www.corepartners.com/careers"
    },
    {
        "name": "Corelabs UK",
        "sector": "Private Tech",
        "url": "https://www.corelabs.io/careers"
    },
    {
        "name": "Coreanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.coreanalytics.tech/careers"
    },
    {
        "name": "Coresoftware UK",
        "sector": "Private Tech",
        "url": "https://www.coresoftware.net/careers"
    },
    {
        "name": "Coreit UK",
        "sector": "Private Tech",
        "url": "https://www.coreIT.co.uk/careers"
    },
    {
        "name": "Innovatesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesolutions.com/careers"
    },
    {
        "name": "Innovatesystems UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesystems.io/careers"
    },
    {
        "name": "Innovatetechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.innovatetechnologies.tech/careers"
    },
    {
        "name": "Innovateconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.innovateconsulting.net/careers"
    },
    {
        "name": "Innovateservices UK",
        "sector": "Private Tech",
        "url": "https://www.innovateservices.co.uk/careers"
    },
    {
        "name": "Innovatenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.innovatenetworks.com/careers"
    },
    {
        "name": "Innovategroup UK",
        "sector": "Private Tech",
        "url": "https://www.innovategroup.io/careers"
    },
    {
        "name": "Innovatedynamics UK",
        "sector": "Private Tech",
        "url": "https://www.innovatedynamics.tech/careers"
    },
    {
        "name": "Innovatepartners UK",
        "sector": "Private Tech",
        "url": "https://www.innovatepartners.net/careers"
    },
    {
        "name": "Innovatelabs UK",
        "sector": "Private Tech",
        "url": "https://www.innovatelabs.co.uk/careers"
    },
    {
        "name": "Innovateanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.innovateanalytics.com/careers"
    },
    {
        "name": "Innovatesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesoftware.io/careers"
    },
    {
        "name": "Innovateit UK",
        "sector": "Private Tech",
        "url": "https://www.innovateIT.tech/careers"
    },
    {
        "name": "Agilesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.agilesolutions.net/careers"
    },
    {
        "name": "Agilesystems UK",
        "sector": "Private Tech",
        "url": "https://www.agilesystems.co.uk/careers"
    },
    {
        "name": "Agiletechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.agiletechnologies.com/careers"
    },
    {
        "name": "Agileconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.agileconsulting.io/careers"
    },
    {
        "name": "Agileservices UK",
        "sector": "Private Tech",
        "url": "https://www.agileservices.tech/careers"
    },
    {
        "name": "Agilenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.agilenetworks.net/careers"
    },
    {
        "name": "Agilegroup UK",
        "sector": "Private Tech",
        "url": "https://www.agilegroup.co.uk/careers"
    },
    {
        "name": "Agiledynamics UK",
        "sector": "Private Tech",
        "url": "https://www.agiledynamics.com/careers"
    },
    {
        "name": "Agilepartners UK",
        "sector": "Private Tech",
        "url": "https://www.agilepartners.io/careers"
    },
    {
        "name": "Agilelabs UK",
        "sector": "Private Tech",
        "url": "https://www.agilelabs.tech/careers"
    },
    {
        "name": "Agileanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.agileanalytics.net/careers"
    },
    {
        "name": "Agilesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.agilesoftware.co.uk/careers"
    },
    {
        "name": "Agileit UK",
        "sector": "Private Tech",
        "url": "https://www.agileIT.com/careers"
    },
    {
        "name": "Nexussolutions UK",
        "sector": "Private Tech",
        "url": "https://www.nexussolutions.io/careers"
    },
    {
        "name": "Nexussystems UK",
        "sector": "Private Tech",
        "url": "https://www.nexussystems.tech/careers"
    },
    {
        "name": "Nexustechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nexustechnologies.net/careers"
    },
    {
        "name": "Nexusconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.nexusconsulting.co.uk/careers"
    },
    {
        "name": "Nexusservices UK",
        "sector": "Private Tech",
        "url": "https://www.nexusservices.com/careers"
    },
    {
        "name": "Nexusnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.nexusnetworks.io/careers"
    },
    {
        "name": "Nexusgroup UK",
        "sector": "Private Tech",
        "url": "https://www.nexusgroup.tech/careers"
    },
    {
        "name": "Nexusdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.nexusdynamics.net/careers"
    },
    {
        "name": "Nexuspartners UK",
        "sector": "Private Tech",
        "url": "https://www.nexuspartners.co.uk/careers"
    },
    {
        "name": "Nexuslabs UK",
        "sector": "Private Tech",
        "url": "https://www.nexuslabs.com/careers"
    },
    {
        "name": "Nexusanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.nexusanalytics.io/careers"
    },
    {
        "name": "Nexussoftware UK",
        "sector": "Private Tech",
        "url": "https://www.nexussoftware.tech/careers"
    },
    {
        "name": "Nexusit UK",
        "sector": "Private Tech",
        "url": "https://www.nexusIT.net/careers"
    },
    {
        "name": "Techsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.techsolutions.co.uk/careers"
    },
    {
        "name": "Techsystems UK",
        "sector": "Private Tech",
        "url": "https://www.techsystems.com/careers"
    },
    {
        "name": "Techtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.techtechnologies.io/careers"
    },
    {
        "name": "Techconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.techconsulting.tech/careers"
    },
    {
        "name": "Techservices UK",
        "sector": "Private Tech",
        "url": "https://www.techservices.net/careers"
    },
    {
        "name": "Technetworks UK",
        "sector": "Private Tech",
        "url": "https://www.technetworks.co.uk/careers"
    },
    {
        "name": "Techgroup UK",
        "sector": "Private Tech",
        "url": "https://www.techgroup.com/careers"
    },
    {
        "name": "Techdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.techdynamics.io/careers"
    },
    {
        "name": "Techpartners UK",
        "sector": "Private Tech",
        "url": "https://www.techpartners.tech/careers"
    },
    {
        "name": "Techlabs UK",
        "sector": "Private Tech",
        "url": "https://www.techlabs.net/careers"
    },
    {
        "name": "Techanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.techanalytics.co.uk/careers"
    },
    {
        "name": "Techsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.techsoftware.com/careers"
    },
    {
        "name": "Techit UK",
        "sector": "Private Tech",
        "url": "https://www.techIT.io/careers"
    },
    {
        "name": "Softsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.softsolutions.tech/careers"
    },
    {
        "name": "Softsystems UK",
        "sector": "Private Tech",
        "url": "https://www.softsystems.net/careers"
    },
    {
        "name": "Softtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.softtechnologies.co.uk/careers"
    },
    {
        "name": "Softconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.softconsulting.com/careers"
    },
    {
        "name": "Softservices UK",
        "sector": "Private Tech",
        "url": "https://www.softservices.io/careers"
    },
    {
        "name": "Softnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.softnetworks.tech/careers"
    },
    {
        "name": "Softgroup UK",
        "sector": "Private Tech",
        "url": "https://www.softgroup.net/careers"
    },
    {
        "name": "Softdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.softdynamics.co.uk/careers"
    },
    {
        "name": "Softpartners UK",
        "sector": "Private Tech",
        "url": "https://www.softpartners.com/careers"
    },
    {
        "name": "Softlabs UK",
        "sector": "Private Tech",
        "url": "https://www.softlabs.io/careers"
    },
    {
        "name": "Softanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.softanalytics.tech/careers"
    },
    {
        "name": "Softsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.softsoftware.net/careers"
    },
    {
        "name": "Softit UK",
        "sector": "Private Tech",
        "url": "https://www.softIT.co.uk/careers"
    },
    {
        "name": "Datasolutions UK",
        "sector": "Private Tech",
        "url": "https://www.datasolutions.com/careers"
    },
    {
        "name": "Datasystems UK",
        "sector": "Private Tech",
        "url": "https://www.datasystems.io/careers"
    },
    {
        "name": "Datatechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.datatechnologies.tech/careers"
    },
    {
        "name": "Dataconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.dataconsulting.net/careers"
    },
    {
        "name": "Dataservices UK",
        "sector": "Private Tech",
        "url": "https://www.dataservices.co.uk/careers"
    },
    {
        "name": "Datanetworks UK",
        "sector": "Private Tech",
        "url": "https://www.datanetworks.com/careers"
    },
    {
        "name": "Datagroup UK",
        "sector": "Private Tech",
        "url": "https://www.datagroup.io/careers"
    },
    {
        "name": "Datadynamics UK",
        "sector": "Private Tech",
        "url": "https://www.datadynamics.tech/careers"
    },
    {
        "name": "Datapartners UK",
        "sector": "Private Tech",
        "url": "https://www.datapartners.net/careers"
    },
    {
        "name": "Datalabs UK",
        "sector": "Private Tech",
        "url": "https://www.datalabs.co.uk/careers"
    },
    {
        "name": "Dataanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.dataanalytics.com/careers"
    },
    {
        "name": "Datasoftware UK",
        "sector": "Private Tech",
        "url": "https://www.datasoftware.io/careers"
    },
    {
        "name": "Datait UK",
        "sector": "Private Tech",
        "url": "https://www.dataIT.tech/careers"
    },
    {
        "name": "Cloudsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsolutions.net/careers"
    },
    {
        "name": "Cloudsystems UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsystems.co.uk/careers"
    },
    {
        "name": "Cloudtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cloudtechnologies.com/careers"
    },
    {
        "name": "Cloudconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cloudconsulting.io/careers"
    },
    {
        "name": "Cloudservices UK",
        "sector": "Private Tech",
        "url": "https://www.cloudservices.tech/careers"
    },
    {
        "name": "Cloudnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cloudnetworks.net/careers"
    },
    {
        "name": "Cloudgroup UK",
        "sector": "Private Tech",
        "url": "https://www.cloudgroup.co.uk/careers"
    },
    {
        "name": "Clouddynamics UK",
        "sector": "Private Tech",
        "url": "https://www.clouddynamics.com/careers"
    },
    {
        "name": "Cloudpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cloudpartners.io/careers"
    },
    {
        "name": "Cloudlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cloudlabs.tech/careers"
    },
    {
        "name": "Cloudanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cloudanalytics.net/careers"
    },
    {
        "name": "Cloudsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsoftware.co.uk/careers"
    },
    {
        "name": "Cloudit UK",
        "sector": "Private Tech",
        "url": "https://www.cloudIT.com/careers"
    },
    {
        "name": "Cybersolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cybersolutions.io/careers"
    },
    {
        "name": "Cybersystems UK",
        "sector": "Private Tech",
        "url": "https://www.cybersystems.tech/careers"
    },
    {
        "name": "Cybertechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cybertechnologies.net/careers"
    },
    {
        "name": "Cyberconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cyberconsulting.co.uk/careers"
    },
    {
        "name": "Cyberservices UK",
        "sector": "Private Tech",
        "url": "https://www.cyberservices.com/careers"
    },
    {
        "name": "Cybernetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cybernetworks.io/careers"
    },
    {
        "name": "Cybergroup UK",
        "sector": "Private Tech",
        "url": "https://www.cybergroup.tech/careers"
    },
    {
        "name": "Cyberdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberdynamics.net/careers"
    },
    {
        "name": "Cyberpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cyberpartners.co.uk/careers"
    },
    {
        "name": "Cyberlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cyberlabs.com/careers"
    },
    {
        "name": "Cyberanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberanalytics.io/careers"
    },
    {
        "name": "Cybersoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cybersoftware.tech/careers"
    },
    {
        "name": "Cyberit UK",
        "sector": "Private Tech",
        "url": "https://www.cyberIT.net/careers"
    },
    {
        "name": "Netsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.netsolutions.co.uk/careers"
    },
    {
        "name": "Netsystems UK",
        "sector": "Private Tech",
        "url": "https://www.netsystems.com/careers"
    },
    {
        "name": "Nettechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nettechnologies.io/careers"
    },
    {
        "name": "Netconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.netconsulting.tech/careers"
    },
    {
        "name": "Netservices UK",
        "sector": "Private Tech",
        "url": "https://www.netservices.net/careers"
    },
    {
        "name": "Netnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.netnetworks.co.uk/careers"
    },
    {
        "name": "Netgroup UK",
        "sector": "Private Tech",
        "url": "https://www.netgroup.com/careers"
    },
    {
        "name": "Netdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.netdynamics.io/careers"
    },
    {
        "name": "Netpartners UK",
        "sector": "Private Tech",
        "url": "https://www.netpartners.tech/careers"
    },
    {
        "name": "Netlabs UK",
        "sector": "Private Tech",
        "url": "https://www.netlabs.net/careers"
    },
    {
        "name": "Netanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.netanalytics.co.uk/careers"
    },
    {
        "name": "Netsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.netsoftware.com/careers"
    },
    {
        "name": "Netit UK",
        "sector": "Private Tech",
        "url": "https://www.netIT.io/careers"
    },
    {
        "name": "Websolutions UK",
        "sector": "Private Tech",
        "url": "https://www.websolutions.tech/careers"
    },
    {
        "name": "Websystems UK",
        "sector": "Private Tech",
        "url": "https://www.websystems.net/careers"
    },
    {
        "name": "Webtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.webtechnologies.co.uk/careers"
    },
    {
        "name": "Webconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.webconsulting.com/careers"
    },
    {
        "name": "Webservices UK",
        "sector": "Private Tech",
        "url": "https://www.webservices.io/careers"
    },
    {
        "name": "Webnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.webnetworks.tech/careers"
    },
    {
        "name": "Webgroup UK",
        "sector": "Private Tech",
        "url": "https://www.webgroup.net/careers"
    },
    {
        "name": "Webdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.webdynamics.co.uk/careers"
    },
    {
        "name": "Webpartners UK",
        "sector": "Private Tech",
        "url": "https://www.webpartners.com/careers"
    },
    {
        "name": "Weblabs UK",
        "sector": "Private Tech",
        "url": "https://www.weblabs.io/careers"
    },
    {
        "name": "Webanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.webanalytics.tech/careers"
    },
    {
        "name": "Websoftware UK",
        "sector": "Private Tech",
        "url": "https://www.websoftware.net/careers"
    },
    {
        "name": "Webit UK",
        "sector": "Private Tech",
        "url": "https://www.webIT.co.uk/careers"
    },
    {
        "name": "Appsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.appsolutions.com/careers"
    },
    {
        "name": "Appsystems UK",
        "sector": "Private Tech",
        "url": "https://www.appsystems.io/careers"
    },
    {
        "name": "Apptechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.apptechnologies.tech/careers"
    },
    {
        "name": "Appconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.appconsulting.net/careers"
    },
    {
        "name": "Appservices UK",
        "sector": "Private Tech",
        "url": "https://www.appservices.co.uk/careers"
    },
    {
        "name": "Appnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.appnetworks.com/careers"
    },
    {
        "name": "Appgroup UK",
        "sector": "Private Tech",
        "url": "https://www.appgroup.io/careers"
    },
    {
        "name": "Appdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.appdynamics.tech/careers"
    },
    {
        "name": "Apppartners UK",
        "sector": "Private Tech",
        "url": "https://www.apppartners.net/careers"
    },
    {
        "name": "Applabs UK",
        "sector": "Private Tech",
        "url": "https://www.applabs.co.uk/careers"
    },
    {
        "name": "Appanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.appanalytics.com/careers"
    },
    {
        "name": "Appsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.appsoftware.io/careers"
    },
    {
        "name": "Appit UK",
        "sector": "Private Tech",
        "url": "https://www.appIT.tech/careers"
    },
    {
        "name": "Logicsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.logicsolutions.net/careers"
    },
    {
        "name": "Logicsystems UK",
        "sector": "Private Tech",
        "url": "https://www.logicsystems.co.uk/careers"
    },
    {
        "name": "Logictechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.logictechnologies.com/careers"
    },
    {
        "name": "Logicconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.logicconsulting.io/careers"
    },
    {
        "name": "Logicservices UK",
        "sector": "Private Tech",
        "url": "https://www.logicservices.tech/careers"
    },
    {
        "name": "Logicnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.logicnetworks.net/careers"
    },
    {
        "name": "Logicgroup UK",
        "sector": "Private Tech",
        "url": "https://www.logicgroup.co.uk/careers"
    },
    {
        "name": "Logicdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.logicdynamics.com/careers"
    },
    {
        "name": "Logicpartners UK",
        "sector": "Private Tech",
        "url": "https://www.logicpartners.io/careers"
    },
    {
        "name": "Logiclabs UK",
        "sector": "Private Tech",
        "url": "https://www.logiclabs.tech/careers"
    },
    {
        "name": "Logicanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.logicanalytics.net/careers"
    },
    {
        "name": "Logicsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.logicsoftware.co.uk/careers"
    },
    {
        "name": "Logicit UK",
        "sector": "Private Tech",
        "url": "https://www.logicIT.com/careers"
    },
    {
        "name": "Syssolutions UK",
        "sector": "Private Tech",
        "url": "https://www.syssolutions.io/careers"
    },
    {
        "name": "Syssystems UK",
        "sector": "Private Tech",
        "url": "https://www.syssystems.tech/careers"
    },
    {
        "name": "Systechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.systechnologies.net/careers"
    },
    {
        "name": "Sysconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.sysconsulting.co.uk/careers"
    },
    {
        "name": "Sysservices UK",
        "sector": "Private Tech",
        "url": "https://www.sysservices.com/careers"
    },
    {
        "name": "Sysnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.sysnetworks.io/careers"
    },
    {
        "name": "Sysgroup UK",
        "sector": "Private Tech",
        "url": "https://www.sysgroup.tech/careers"
    },
    {
        "name": "Sysdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.sysdynamics.net/careers"
    },
    {
        "name": "Syspartners UK",
        "sector": "Private Tech",
        "url": "https://www.syspartners.co.uk/careers"
    },
    {
        "name": "Syslabs UK",
        "sector": "Private Tech",
        "url": "https://www.syslabs.com/careers"
    },
    {
        "name": "Sysanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.sysanalytics.io/careers"
    },
    {
        "name": "Syssoftware UK",
        "sector": "Private Tech",
        "url": "https://www.syssoftware.tech/careers"
    },
    {
        "name": "Sysit UK",
        "sector": "Private Tech",
        "url": "https://www.sysIT.net/careers"
    },
    {
        "name": "Codesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.codesolutions.co.uk/careers"
    },
    {
        "name": "Codesystems UK",
        "sector": "Private Tech",
        "url": "https://www.codesystems.com/careers"
    },
    {
        "name": "Codetechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.codetechnologies.io/careers"
    },
    {
        "name": "Codeconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.codeconsulting.tech/careers"
    },
    {
        "name": "Codeservices UK",
        "sector": "Private Tech",
        "url": "https://www.codeservices.net/careers"
    },
    {
        "name": "Codenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.codenetworks.co.uk/careers"
    },
    {
        "name": "Codegroup UK",
        "sector": "Private Tech",
        "url": "https://www.codegroup.com/careers"
    },
    {
        "name": "Codedynamics UK",
        "sector": "Private Tech",
        "url": "https://www.codedynamics.io/careers"
    },
    {
        "name": "Codepartners UK",
        "sector": "Private Tech",
        "url": "https://www.codepartners.tech/careers"
    },
    {
        "name": "Codelabs UK",
        "sector": "Private Tech",
        "url": "https://www.codelabs.net/careers"
    },
    {
        "name": "Codeanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.codeanalytics.co.uk/careers"
    },
    {
        "name": "Codesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.codesoftware.com/careers"
    },
    {
        "name": "Codeit UK",
        "sector": "Private Tech",
        "url": "https://www.codeIT.io/careers"
    },
    {
        "name": "Aisolutions UK",
        "sector": "Private Tech",
        "url": "https://www.aisolutions.tech/careers"
    },
    {
        "name": "Aisystems UK",
        "sector": "Private Tech",
        "url": "https://www.aisystems.net/careers"
    },
    {
        "name": "Aitechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.aitechnologies.co.uk/careers"
    },
    {
        "name": "Aiconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.aiconsulting.com/careers"
    },
    {
        "name": "Aiservices UK",
        "sector": "Private Tech",
        "url": "https://www.aiservices.io/careers"
    },
    {
        "name": "Ainetworks UK",
        "sector": "Private Tech",
        "url": "https://www.ainetworks.tech/careers"
    },
    {
        "name": "Aigroup UK",
        "sector": "Private Tech",
        "url": "https://www.aigroup.net/careers"
    },
    {
        "name": "Aidynamics UK",
        "sector": "Private Tech",
        "url": "https://www.aidynamics.co.uk/careers"
    },
    {
        "name": "Aipartners UK",
        "sector": "Private Tech",
        "url": "https://www.aipartners.com/careers"
    },
    {
        "name": "Ailabs UK",
        "sector": "Private Tech",
        "url": "https://www.ailabs.io/careers"
    },
    {
        "name": "Aianalytics UK",
        "sector": "Private Tech",
        "url": "https://www.aianalytics.tech/careers"
    },
    {
        "name": "Aisoftware UK",
        "sector": "Private Tech",
        "url": "https://www.aisoftware.net/careers"
    },
    {
        "name": "Aiit UK",
        "sector": "Private Tech",
        "url": "https://www.aiIT.co.uk/careers"
    },
    {
        "name": "Smartsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.smartsolutions.com/careers"
    },
    {
        "name": "Smartsystems UK",
        "sector": "Private Tech",
        "url": "https://www.smartsystems.io/careers"
    },
    {
        "name": "Smarttechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.smarttechnologies.tech/careers"
    },
    {
        "name": "Smartconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.smartconsulting.net/careers"
    },
    {
        "name": "Smartservices UK",
        "sector": "Private Tech",
        "url": "https://www.smartservices.co.uk/careers"
    },
    {
        "name": "Smartnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.smartnetworks.com/careers"
    },
    {
        "name": "Smartgroup UK",
        "sector": "Private Tech",
        "url": "https://www.smartgroup.io/careers"
    },
    {
        "name": "Smartdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.smartdynamics.tech/careers"
    },
    {
        "name": "Smartpartners UK",
        "sector": "Private Tech",
        "url": "https://www.smartpartners.net/careers"
    },
    {
        "name": "Smartlabs UK",
        "sector": "Private Tech",
        "url": "https://www.smartlabs.co.uk/careers"
    },
    {
        "name": "Smartanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.smartanalytics.com/careers"
    },
    {
        "name": "Smartsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.smartsoftware.io/careers"
    },
    {
        "name": "Smartit UK",
        "sector": "Private Tech",
        "url": "https://www.smartIT.tech/careers"
    },
    {
        "name": "Digitalsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsolutions.net/careers"
    },
    {
        "name": "Digitalsystems UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsystems.co.uk/careers"
    },
    {
        "name": "Digitaltechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.digitaltechnologies.com/careers"
    },
    {
        "name": "Digitalconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.digitalconsulting.io/careers"
    },
    {
        "name": "Digitalservices UK",
        "sector": "Private Tech",
        "url": "https://www.digitalservices.tech/careers"
    },
    {
        "name": "Digitalnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.digitalnetworks.net/careers"
    },
    {
        "name": "Digitalgroup UK",
        "sector": "Private Tech",
        "url": "https://www.digitalgroup.co.uk/careers"
    },
    {
        "name": "Digitaldynamics UK",
        "sector": "Private Tech",
        "url": "https://www.digitaldynamics.com/careers"
    },
    {
        "name": "Digitalpartners UK",
        "sector": "Private Tech",
        "url": "https://www.digitalpartners.io/careers"
    },
    {
        "name": "Digitallabs UK",
        "sector": "Private Tech",
        "url": "https://www.digitallabs.tech/careers"
    },
    {
        "name": "Digitalanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.digitalanalytics.net/careers"
    },
    {
        "name": "Digitalsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsoftware.co.uk/careers"
    },
    {
        "name": "Digitalit UK",
        "sector": "Private Tech",
        "url": "https://www.digitalIT.com/careers"
    },
    {
        "name": "Prosolutions UK",
        "sector": "Private Tech",
        "url": "https://www.prosolutions.io/careers"
    },
    {
        "name": "Prosystems UK",
        "sector": "Private Tech",
        "url": "https://www.prosystems.tech/careers"
    },
    {
        "name": "Protechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.protechnologies.net/careers"
    },
    {
        "name": "Proconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.proconsulting.co.uk/careers"
    },
    {
        "name": "Proservices UK",
        "sector": "Private Tech",
        "url": "https://www.proservices.com/careers"
    },
    {
        "name": "Pronetworks UK",
        "sector": "Private Tech",
        "url": "https://www.pronetworks.io/careers"
    },
    {
        "name": "Progroup UK",
        "sector": "Private Tech",
        "url": "https://www.progroup.tech/careers"
    },
    {
        "name": "Prodynamics UK",
        "sector": "Private Tech",
        "url": "https://www.prodynamics.net/careers"
    },
    {
        "name": "Propartners UK",
        "sector": "Private Tech",
        "url": "https://www.propartners.co.uk/careers"
    },
    {
        "name": "Prolabs UK",
        "sector": "Private Tech",
        "url": "https://www.prolabs.com/careers"
    },
    {
        "name": "Proanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.proanalytics.io/careers"
    },
    {
        "name": "Prosoftware UK",
        "sector": "Private Tech",
        "url": "https://www.prosoftware.tech/careers"
    },
    {
        "name": "Proit UK",
        "sector": "Private Tech",
        "url": "https://www.proIT.net/careers"
    },
    {
        "name": "Nextsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.nextsolutions.co.uk/careers"
    },
    {
        "name": "Nextsystems UK",
        "sector": "Private Tech",
        "url": "https://www.nextsystems.com/careers"
    },
    {
        "name": "Nexttechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nexttechnologies.io/careers"
    },
    {
        "name": "Nextconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.nextconsulting.tech/careers"
    },
    {
        "name": "Nextservices UK",
        "sector": "Private Tech",
        "url": "https://www.nextservices.net/careers"
    },
    {
        "name": "Nextnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.nextnetworks.co.uk/careers"
    },
    {
        "name": "Nextgroup UK",
        "sector": "Private Tech",
        "url": "https://www.nextgroup.com/careers"
    },
    {
        "name": "Nextdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.nextdynamics.io/careers"
    },
    {
        "name": "Nextpartners UK",
        "sector": "Private Tech",
        "url": "https://www.nextpartners.tech/careers"
    },
    {
        "name": "Nextlabs UK",
        "sector": "Private Tech",
        "url": "https://www.nextlabs.net/careers"
    },
    {
        "name": "Nextanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.nextanalytics.co.uk/careers"
    },
    {
        "name": "Nextsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.nextsoftware.com/careers"
    },
    {
        "name": "Nextit UK",
        "sector": "Private Tech",
        "url": "https://www.nextIT.io/careers"
    },
    {
        "name": "Coresolutions UK",
        "sector": "Private Tech",
        "url": "https://www.coresolutions.tech/careers"
    },
    {
        "name": "Coresystems UK",
        "sector": "Private Tech",
        "url": "https://www.coresystems.net/careers"
    },
    {
        "name": "Coretechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.coretechnologies.co.uk/careers"
    },
    {
        "name": "Coreconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.coreconsulting.com/careers"
    },
    {
        "name": "Coreservices UK",
        "sector": "Private Tech",
        "url": "https://www.coreservices.io/careers"
    },
    {
        "name": "Corenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.corenetworks.tech/careers"
    },
    {
        "name": "Coregroup UK",
        "sector": "Private Tech",
        "url": "https://www.coregroup.net/careers"
    },
    {
        "name": "Coredynamics UK",
        "sector": "Private Tech",
        "url": "https://www.coredynamics.co.uk/careers"
    },
    {
        "name": "Corepartners UK",
        "sector": "Private Tech",
        "url": "https://www.corepartners.com/careers"
    },
    {
        "name": "Corelabs UK",
        "sector": "Private Tech",
        "url": "https://www.corelabs.io/careers"
    },
    {
        "name": "Coreanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.coreanalytics.tech/careers"
    },
    {
        "name": "Coresoftware UK",
        "sector": "Private Tech",
        "url": "https://www.coresoftware.net/careers"
    },
    {
        "name": "Coreit UK",
        "sector": "Private Tech",
        "url": "https://www.coreIT.co.uk/careers"
    },
    {
        "name": "Innovatesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesolutions.com/careers"
    },
    {
        "name": "Innovatesystems UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesystems.io/careers"
    },
    {
        "name": "Innovatetechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.innovatetechnologies.tech/careers"
    },
    {
        "name": "Innovateconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.innovateconsulting.net/careers"
    },
    {
        "name": "Innovateservices UK",
        "sector": "Private Tech",
        "url": "https://www.innovateservices.co.uk/careers"
    },
    {
        "name": "Innovatenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.innovatenetworks.com/careers"
    },
    {
        "name": "Innovategroup UK",
        "sector": "Private Tech",
        "url": "https://www.innovategroup.io/careers"
    },
    {
        "name": "Innovatedynamics UK",
        "sector": "Private Tech",
        "url": "https://www.innovatedynamics.tech/careers"
    },
    {
        "name": "Innovatepartners UK",
        "sector": "Private Tech",
        "url": "https://www.innovatepartners.net/careers"
    },
    {
        "name": "Innovatelabs UK",
        "sector": "Private Tech",
        "url": "https://www.innovatelabs.co.uk/careers"
    },
    {
        "name": "Innovateanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.innovateanalytics.com/careers"
    },
    {
        "name": "Innovatesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesoftware.io/careers"
    },
    {
        "name": "Innovateit UK",
        "sector": "Private Tech",
        "url": "https://www.innovateIT.tech/careers"
    },
    {
        "name": "Agilesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.agilesolutions.net/careers"
    },
    {
        "name": "Agilesystems UK",
        "sector": "Private Tech",
        "url": "https://www.agilesystems.co.uk/careers"
    },
    {
        "name": "Agiletechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.agiletechnologies.com/careers"
    },
    {
        "name": "Agileconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.agileconsulting.io/careers"
    },
    {
        "name": "Agileservices UK",
        "sector": "Private Tech",
        "url": "https://www.agileservices.tech/careers"
    },
    {
        "name": "Agilenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.agilenetworks.net/careers"
    },
    {
        "name": "Agilegroup UK",
        "sector": "Private Tech",
        "url": "https://www.agilegroup.co.uk/careers"
    },
    {
        "name": "Agiledynamics UK",
        "sector": "Private Tech",
        "url": "https://www.agiledynamics.com/careers"
    },
    {
        "name": "Agilepartners UK",
        "sector": "Private Tech",
        "url": "https://www.agilepartners.io/careers"
    },
    {
        "name": "Agilelabs UK",
        "sector": "Private Tech",
        "url": "https://www.agilelabs.tech/careers"
    },
    {
        "name": "Agileanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.agileanalytics.net/careers"
    },
    {
        "name": "Agilesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.agilesoftware.co.uk/careers"
    },
    {
        "name": "Agileit UK",
        "sector": "Private Tech",
        "url": "https://www.agileIT.com/careers"
    },
    {
        "name": "Nexussolutions UK",
        "sector": "Private Tech",
        "url": "https://www.nexussolutions.io/careers"
    },
    {
        "name": "Nexussystems UK",
        "sector": "Private Tech",
        "url": "https://www.nexussystems.tech/careers"
    },
    {
        "name": "Nexustechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nexustechnologies.net/careers"
    },
    {
        "name": "Nexusconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.nexusconsulting.co.uk/careers"
    },
    {
        "name": "Nexusservices UK",
        "sector": "Private Tech",
        "url": "https://www.nexusservices.com/careers"
    },
    {
        "name": "Nexusnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.nexusnetworks.io/careers"
    },
    {
        "name": "Nexusgroup UK",
        "sector": "Private Tech",
        "url": "https://www.nexusgroup.tech/careers"
    },
    {
        "name": "Nexusdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.nexusdynamics.net/careers"
    },
    {
        "name": "Nexuspartners UK",
        "sector": "Private Tech",
        "url": "https://www.nexuspartners.co.uk/careers"
    },
    {
        "name": "Nexuslabs UK",
        "sector": "Private Tech",
        "url": "https://www.nexuslabs.com/careers"
    },
    {
        "name": "Nexusanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.nexusanalytics.io/careers"
    },
    {
        "name": "Nexussoftware UK",
        "sector": "Private Tech",
        "url": "https://www.nexussoftware.tech/careers"
    },
    {
        "name": "Nexusit UK",
        "sector": "Private Tech",
        "url": "https://www.nexusIT.net/careers"
    },
    {
        "name": "Techsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.techsolutions.co.uk/careers"
    },
    {
        "name": "Techsystems UK",
        "sector": "Private Tech",
        "url": "https://www.techsystems.com/careers"
    },
    {
        "name": "Techtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.techtechnologies.io/careers"
    },
    {
        "name": "Techconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.techconsulting.tech/careers"
    },
    {
        "name": "Techservices UK",
        "sector": "Private Tech",
        "url": "https://www.techservices.net/careers"
    },
    {
        "name": "Technetworks UK",
        "sector": "Private Tech",
        "url": "https://www.technetworks.co.uk/careers"
    },
    {
        "name": "Techgroup UK",
        "sector": "Private Tech",
        "url": "https://www.techgroup.com/careers"
    },
    {
        "name": "Techdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.techdynamics.io/careers"
    },
    {
        "name": "Techpartners UK",
        "sector": "Private Tech",
        "url": "https://www.techpartners.tech/careers"
    },
    {
        "name": "Techlabs UK",
        "sector": "Private Tech",
        "url": "https://www.techlabs.net/careers"
    },
    {
        "name": "Techanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.techanalytics.co.uk/careers"
    },
    {
        "name": "Techsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.techsoftware.com/careers"
    },
    {
        "name": "Techit UK",
        "sector": "Private Tech",
        "url": "https://www.techIT.io/careers"
    },
    {
        "name": "Softsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.softsolutions.tech/careers"
    },
    {
        "name": "Softsystems UK",
        "sector": "Private Tech",
        "url": "https://www.softsystems.net/careers"
    },
    {
        "name": "Softtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.softtechnologies.co.uk/careers"
    },
    {
        "name": "Softconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.softconsulting.com/careers"
    },
    {
        "name": "Softservices UK",
        "sector": "Private Tech",
        "url": "https://www.softservices.io/careers"
    },
    {
        "name": "Softnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.softnetworks.tech/careers"
    },
    {
        "name": "Softgroup UK",
        "sector": "Private Tech",
        "url": "https://www.softgroup.net/careers"
    },
    {
        "name": "Softdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.softdynamics.co.uk/careers"
    },
    {
        "name": "Softpartners UK",
        "sector": "Private Tech",
        "url": "https://www.softpartners.com/careers"
    },
    {
        "name": "Softlabs UK",
        "sector": "Private Tech",
        "url": "https://www.softlabs.io/careers"
    },
    {
        "name": "Softanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.softanalytics.tech/careers"
    },
    {
        "name": "Softsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.softsoftware.net/careers"
    },
    {
        "name": "Softit UK",
        "sector": "Private Tech",
        "url": "https://www.softIT.co.uk/careers"
    },
    {
        "name": "Datasolutions UK",
        "sector": "Private Tech",
        "url": "https://www.datasolutions.com/careers"
    },
    {
        "name": "Datasystems UK",
        "sector": "Private Tech",
        "url": "https://www.datasystems.io/careers"
    },
    {
        "name": "Datatechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.datatechnologies.tech/careers"
    },
    {
        "name": "Dataconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.dataconsulting.net/careers"
    },
    {
        "name": "Dataservices UK",
        "sector": "Private Tech",
        "url": "https://www.dataservices.co.uk/careers"
    },
    {
        "name": "Datanetworks UK",
        "sector": "Private Tech",
        "url": "https://www.datanetworks.com/careers"
    },
    {
        "name": "Datagroup UK",
        "sector": "Private Tech",
        "url": "https://www.datagroup.io/careers"
    },
    {
        "name": "Datadynamics UK",
        "sector": "Private Tech",
        "url": "https://www.datadynamics.tech/careers"
    },
    {
        "name": "Datapartners UK",
        "sector": "Private Tech",
        "url": "https://www.datapartners.net/careers"
    },
    {
        "name": "Datalabs UK",
        "sector": "Private Tech",
        "url": "https://www.datalabs.co.uk/careers"
    },
    {
        "name": "Dataanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.dataanalytics.com/careers"
    },
    {
        "name": "Datasoftware UK",
        "sector": "Private Tech",
        "url": "https://www.datasoftware.io/careers"
    },
    {
        "name": "Datait UK",
        "sector": "Private Tech",
        "url": "https://www.dataIT.tech/careers"
    },
    {
        "name": "Cloudsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsolutions.net/careers"
    },
    {
        "name": "Cloudsystems UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsystems.co.uk/careers"
    },
    {
        "name": "Cloudtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cloudtechnologies.com/careers"
    },
    {
        "name": "Cloudconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cloudconsulting.io/careers"
    },
    {
        "name": "Cloudservices UK",
        "sector": "Private Tech",
        "url": "https://www.cloudservices.tech/careers"
    },
    {
        "name": "Cloudnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cloudnetworks.net/careers"
    },
    {
        "name": "Cloudgroup UK",
        "sector": "Private Tech",
        "url": "https://www.cloudgroup.co.uk/careers"
    },
    {
        "name": "Clouddynamics UK",
        "sector": "Private Tech",
        "url": "https://www.clouddynamics.com/careers"
    },
    {
        "name": "Cloudpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cloudpartners.io/careers"
    },
    {
        "name": "Cloudlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cloudlabs.tech/careers"
    },
    {
        "name": "Cloudanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cloudanalytics.net/careers"
    },
    {
        "name": "Cloudsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsoftware.co.uk/careers"
    },
    {
        "name": "Cloudit UK",
        "sector": "Private Tech",
        "url": "https://www.cloudIT.com/careers"
    },
    {
        "name": "Cybersolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cybersolutions.io/careers"
    },
    {
        "name": "Cybersystems UK",
        "sector": "Private Tech",
        "url": "https://www.cybersystems.tech/careers"
    },
    {
        "name": "Cybertechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cybertechnologies.net/careers"
    },
    {
        "name": "Cyberconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cyberconsulting.co.uk/careers"
    },
    {
        "name": "Cyberservices UK",
        "sector": "Private Tech",
        "url": "https://www.cyberservices.com/careers"
    },
    {
        "name": "Cybernetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cybernetworks.io/careers"
    },
    {
        "name": "Cybergroup UK",
        "sector": "Private Tech",
        "url": "https://www.cybergroup.tech/careers"
    },
    {
        "name": "Cyberdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberdynamics.net/careers"
    },
    {
        "name": "Cyberpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cyberpartners.co.uk/careers"
    },
    {
        "name": "Cyberlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cyberlabs.com/careers"
    },
    {
        "name": "Cyberanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberanalytics.io/careers"
    },
    {
        "name": "Cybersoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cybersoftware.tech/careers"
    },
    {
        "name": "Cyberit UK",
        "sector": "Private Tech",
        "url": "https://www.cyberIT.net/careers"
    },
    {
        "name": "Netsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.netsolutions.co.uk/careers"
    },
    {
        "name": "Netsystems UK",
        "sector": "Private Tech",
        "url": "https://www.netsystems.com/careers"
    },
    {
        "name": "Nettechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nettechnologies.io/careers"
    },
    {
        "name": "Netconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.netconsulting.tech/careers"
    },
    {
        "name": "Netservices UK",
        "sector": "Private Tech",
        "url": "https://www.netservices.net/careers"
    },
    {
        "name": "Netnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.netnetworks.co.uk/careers"
    },
    {
        "name": "Netgroup UK",
        "sector": "Private Tech",
        "url": "https://www.netgroup.com/careers"
    },
    {
        "name": "Netdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.netdynamics.io/careers"
    },
    {
        "name": "Netpartners UK",
        "sector": "Private Tech",
        "url": "https://www.netpartners.tech/careers"
    },
    {
        "name": "Netlabs UK",
        "sector": "Private Tech",
        "url": "https://www.netlabs.net/careers"
    },
    {
        "name": "Netanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.netanalytics.co.uk/careers"
    },
    {
        "name": "Netsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.netsoftware.com/careers"
    },
    {
        "name": "Netit UK",
        "sector": "Private Tech",
        "url": "https://www.netIT.io/careers"
    },
    {
        "name": "Websolutions UK",
        "sector": "Private Tech",
        "url": "https://www.websolutions.tech/careers"
    },
    {
        "name": "Websystems UK",
        "sector": "Private Tech",
        "url": "https://www.websystems.net/careers"
    },
    {
        "name": "Webtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.webtechnologies.co.uk/careers"
    },
    {
        "name": "Webconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.webconsulting.com/careers"
    },
    {
        "name": "Webservices UK",
        "sector": "Private Tech",
        "url": "https://www.webservices.io/careers"
    },
    {
        "name": "Webnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.webnetworks.tech/careers"
    },
    {
        "name": "Webgroup UK",
        "sector": "Private Tech",
        "url": "https://www.webgroup.net/careers"
    },
    {
        "name": "Webdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.webdynamics.co.uk/careers"
    },
    {
        "name": "Webpartners UK",
        "sector": "Private Tech",
        "url": "https://www.webpartners.com/careers"
    },
    {
        "name": "Weblabs UK",
        "sector": "Private Tech",
        "url": "https://www.weblabs.io/careers"
    },
    {
        "name": "Webanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.webanalytics.tech/careers"
    },
    {
        "name": "Websoftware UK",
        "sector": "Private Tech",
        "url": "https://www.websoftware.net/careers"
    },
    {
        "name": "Webit UK",
        "sector": "Private Tech",
        "url": "https://www.webIT.co.uk/careers"
    },
    {
        "name": "Appsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.appsolutions.com/careers"
    },
    {
        "name": "Appsystems UK",
        "sector": "Private Tech",
        "url": "https://www.appsystems.io/careers"
    },
    {
        "name": "Apptechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.apptechnologies.tech/careers"
    },
    {
        "name": "Appconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.appconsulting.net/careers"
    },
    {
        "name": "Appservices UK",
        "sector": "Private Tech",
        "url": "https://www.appservices.co.uk/careers"
    },
    {
        "name": "Appnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.appnetworks.com/careers"
    },
    {
        "name": "Appgroup UK",
        "sector": "Private Tech",
        "url": "https://www.appgroup.io/careers"
    },
    {
        "name": "Appdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.appdynamics.tech/careers"
    },
    {
        "name": "Apppartners UK",
        "sector": "Private Tech",
        "url": "https://www.apppartners.net/careers"
    },
    {
        "name": "Applabs UK",
        "sector": "Private Tech",
        "url": "https://www.applabs.co.uk/careers"
    },
    {
        "name": "Appanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.appanalytics.com/careers"
    },
    {
        "name": "Appsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.appsoftware.io/careers"
    },
    {
        "name": "Appit UK",
        "sector": "Private Tech",
        "url": "https://www.appIT.tech/careers"
    },
    {
        "name": "Logicsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.logicsolutions.net/careers"
    },
    {
        "name": "Logicsystems UK",
        "sector": "Private Tech",
        "url": "https://www.logicsystems.co.uk/careers"
    },
    {
        "name": "Logictechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.logictechnologies.com/careers"
    },
    {
        "name": "Logicconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.logicconsulting.io/careers"
    },
    {
        "name": "Logicservices UK",
        "sector": "Private Tech",
        "url": "https://www.logicservices.tech/careers"
    },
    {
        "name": "Logicnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.logicnetworks.net/careers"
    },
    {
        "name": "Logicgroup UK",
        "sector": "Private Tech",
        "url": "https://www.logicgroup.co.uk/careers"
    },
    {
        "name": "Logicdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.logicdynamics.com/careers"
    },
    {
        "name": "Logicpartners UK",
        "sector": "Private Tech",
        "url": "https://www.logicpartners.io/careers"
    },
    {
        "name": "Logiclabs UK",
        "sector": "Private Tech",
        "url": "https://www.logiclabs.tech/careers"
    },
    {
        "name": "Logicanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.logicanalytics.net/careers"
    },
    {
        "name": "Logicsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.logicsoftware.co.uk/careers"
    },
    {
        "name": "Logicit UK",
        "sector": "Private Tech",
        "url": "https://www.logicIT.com/careers"
    },
    {
        "name": "Syssolutions UK",
        "sector": "Private Tech",
        "url": "https://www.syssolutions.io/careers"
    },
    {
        "name": "Syssystems UK",
        "sector": "Private Tech",
        "url": "https://www.syssystems.tech/careers"
    },
    {
        "name": "Systechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.systechnologies.net/careers"
    },
    {
        "name": "Sysconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.sysconsulting.co.uk/careers"
    },
    {
        "name": "Sysservices UK",
        "sector": "Private Tech",
        "url": "https://www.sysservices.com/careers"
    },
    {
        "name": "Sysnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.sysnetworks.io/careers"
    },
    {
        "name": "Sysgroup UK",
        "sector": "Private Tech",
        "url": "https://www.sysgroup.tech/careers"
    },
    {
        "name": "Sysdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.sysdynamics.net/careers"
    },
    {
        "name": "Syspartners UK",
        "sector": "Private Tech",
        "url": "https://www.syspartners.co.uk/careers"
    },
    {
        "name": "Syslabs UK",
        "sector": "Private Tech",
        "url": "https://www.syslabs.com/careers"
    },
    {
        "name": "Sysanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.sysanalytics.io/careers"
    },
    {
        "name": "Syssoftware UK",
        "sector": "Private Tech",
        "url": "https://www.syssoftware.tech/careers"
    },
    {
        "name": "Sysit UK",
        "sector": "Private Tech",
        "url": "https://www.sysIT.net/careers"
    },
    {
        "name": "Codesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.codesolutions.co.uk/careers"
    },
    {
        "name": "Codesystems UK",
        "sector": "Private Tech",
        "url": "https://www.codesystems.com/careers"
    },
    {
        "name": "Codetechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.codetechnologies.io/careers"
    },
    {
        "name": "Codeconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.codeconsulting.tech/careers"
    },
    {
        "name": "Codeservices UK",
        "sector": "Private Tech",
        "url": "https://www.codeservices.net/careers"
    },
    {
        "name": "Codenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.codenetworks.co.uk/careers"
    },
    {
        "name": "Codegroup UK",
        "sector": "Private Tech",
        "url": "https://www.codegroup.com/careers"
    },
    {
        "name": "Codedynamics UK",
        "sector": "Private Tech",
        "url": "https://www.codedynamics.io/careers"
    },
    {
        "name": "Codepartners UK",
        "sector": "Private Tech",
        "url": "https://www.codepartners.tech/careers"
    },
    {
        "name": "Codelabs UK",
        "sector": "Private Tech",
        "url": "https://www.codelabs.net/careers"
    },
    {
        "name": "Codeanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.codeanalytics.co.uk/careers"
    },
    {
        "name": "Codesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.codesoftware.com/careers"
    },
    {
        "name": "Codeit UK",
        "sector": "Private Tech",
        "url": "https://www.codeIT.io/careers"
    },
    {
        "name": "Aisolutions UK",
        "sector": "Private Tech",
        "url": "https://www.aisolutions.tech/careers"
    },
    {
        "name": "Aisystems UK",
        "sector": "Private Tech",
        "url": "https://www.aisystems.net/careers"
    },
    {
        "name": "Aitechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.aitechnologies.co.uk/careers"
    },
    {
        "name": "Aiconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.aiconsulting.com/careers"
    },
    {
        "name": "Aiservices UK",
        "sector": "Private Tech",
        "url": "https://www.aiservices.io/careers"
    },
    {
        "name": "Ainetworks UK",
        "sector": "Private Tech",
        "url": "https://www.ainetworks.tech/careers"
    },
    {
        "name": "Aigroup UK",
        "sector": "Private Tech",
        "url": "https://www.aigroup.net/careers"
    },
    {
        "name": "Aidynamics UK",
        "sector": "Private Tech",
        "url": "https://www.aidynamics.co.uk/careers"
    },
    {
        "name": "Aipartners UK",
        "sector": "Private Tech",
        "url": "https://www.aipartners.com/careers"
    },
    {
        "name": "Ailabs UK",
        "sector": "Private Tech",
        "url": "https://www.ailabs.io/careers"
    },
    {
        "name": "Aianalytics UK",
        "sector": "Private Tech",
        "url": "https://www.aianalytics.tech/careers"
    },
    {
        "name": "Aisoftware UK",
        "sector": "Private Tech",
        "url": "https://www.aisoftware.net/careers"
    },
    {
        "name": "Aiit UK",
        "sector": "Private Tech",
        "url": "https://www.aiIT.co.uk/careers"
    },
    {
        "name": "Smartsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.smartsolutions.com/careers"
    },
    {
        "name": "Smartsystems UK",
        "sector": "Private Tech",
        "url": "https://www.smartsystems.io/careers"
    },
    {
        "name": "Smarttechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.smarttechnologies.tech/careers"
    },
    {
        "name": "Smartconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.smartconsulting.net/careers"
    },
    {
        "name": "Smartservices UK",
        "sector": "Private Tech",
        "url": "https://www.smartservices.co.uk/careers"
    },
    {
        "name": "Smartnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.smartnetworks.com/careers"
    },
    {
        "name": "Smartgroup UK",
        "sector": "Private Tech",
        "url": "https://www.smartgroup.io/careers"
    },
    {
        "name": "Smartdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.smartdynamics.tech/careers"
    },
    {
        "name": "Smartpartners UK",
        "sector": "Private Tech",
        "url": "https://www.smartpartners.net/careers"
    },
    {
        "name": "Smartlabs UK",
        "sector": "Private Tech",
        "url": "https://www.smartlabs.co.uk/careers"
    },
    {
        "name": "Smartanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.smartanalytics.com/careers"
    },
    {
        "name": "Smartsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.smartsoftware.io/careers"
    },
    {
        "name": "Smartit UK",
        "sector": "Private Tech",
        "url": "https://www.smartIT.tech/careers"
    },
    {
        "name": "Digitalsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsolutions.net/careers"
    },
    {
        "name": "Digitalsystems UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsystems.co.uk/careers"
    },
    {
        "name": "Digitaltechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.digitaltechnologies.com/careers"
    },
    {
        "name": "Digitalconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.digitalconsulting.io/careers"
    },
    {
        "name": "Digitalservices UK",
        "sector": "Private Tech",
        "url": "https://www.digitalservices.tech/careers"
    },
    {
        "name": "Digitalnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.digitalnetworks.net/careers"
    },
    {
        "name": "Digitalgroup UK",
        "sector": "Private Tech",
        "url": "https://www.digitalgroup.co.uk/careers"
    },
    {
        "name": "Digitaldynamics UK",
        "sector": "Private Tech",
        "url": "https://www.digitaldynamics.com/careers"
    },
    {
        "name": "Digitalpartners UK",
        "sector": "Private Tech",
        "url": "https://www.digitalpartners.io/careers"
    },
    {
        "name": "Digitallabs UK",
        "sector": "Private Tech",
        "url": "https://www.digitallabs.tech/careers"
    },
    {
        "name": "Digitalanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.digitalanalytics.net/careers"
    },
    {
        "name": "Digitalsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.digitalsoftware.co.uk/careers"
    },
    {
        "name": "Digitalit UK",
        "sector": "Private Tech",
        "url": "https://www.digitalIT.com/careers"
    },
    {
        "name": "Prosolutions UK",
        "sector": "Private Tech",
        "url": "https://www.prosolutions.io/careers"
    },
    {
        "name": "Prosystems UK",
        "sector": "Private Tech",
        "url": "https://www.prosystems.tech/careers"
    },
    {
        "name": "Protechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.protechnologies.net/careers"
    },
    {
        "name": "Proconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.proconsulting.co.uk/careers"
    },
    {
        "name": "Proservices UK",
        "sector": "Private Tech",
        "url": "https://www.proservices.com/careers"
    },
    {
        "name": "Pronetworks UK",
        "sector": "Private Tech",
        "url": "https://www.pronetworks.io/careers"
    },
    {
        "name": "Progroup UK",
        "sector": "Private Tech",
        "url": "https://www.progroup.tech/careers"
    },
    {
        "name": "Prodynamics UK",
        "sector": "Private Tech",
        "url": "https://www.prodynamics.net/careers"
    },
    {
        "name": "Propartners UK",
        "sector": "Private Tech",
        "url": "https://www.propartners.co.uk/careers"
    },
    {
        "name": "Prolabs UK",
        "sector": "Private Tech",
        "url": "https://www.prolabs.com/careers"
    },
    {
        "name": "Proanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.proanalytics.io/careers"
    },
    {
        "name": "Prosoftware UK",
        "sector": "Private Tech",
        "url": "https://www.prosoftware.tech/careers"
    },
    {
        "name": "Proit UK",
        "sector": "Private Tech",
        "url": "https://www.proIT.net/careers"
    },
    {
        "name": "Nextsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.nextsolutions.co.uk/careers"
    },
    {
        "name": "Nextsystems UK",
        "sector": "Private Tech",
        "url": "https://www.nextsystems.com/careers"
    },
    {
        "name": "Nexttechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nexttechnologies.io/careers"
    },
    {
        "name": "Nextconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.nextconsulting.tech/careers"
    },
    {
        "name": "Nextservices UK",
        "sector": "Private Tech",
        "url": "https://www.nextservices.net/careers"
    },
    {
        "name": "Nextnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.nextnetworks.co.uk/careers"
    },
    {
        "name": "Nextgroup UK",
        "sector": "Private Tech",
        "url": "https://www.nextgroup.com/careers"
    },
    {
        "name": "Nextdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.nextdynamics.io/careers"
    },
    {
        "name": "Nextpartners UK",
        "sector": "Private Tech",
        "url": "https://www.nextpartners.tech/careers"
    },
    {
        "name": "Nextlabs UK",
        "sector": "Private Tech",
        "url": "https://www.nextlabs.net/careers"
    },
    {
        "name": "Nextanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.nextanalytics.co.uk/careers"
    },
    {
        "name": "Nextsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.nextsoftware.com/careers"
    },
    {
        "name": "Nextit UK",
        "sector": "Private Tech",
        "url": "https://www.nextIT.io/careers"
    },
    {
        "name": "Coresolutions UK",
        "sector": "Private Tech",
        "url": "https://www.coresolutions.tech/careers"
    },
    {
        "name": "Coresystems UK",
        "sector": "Private Tech",
        "url": "https://www.coresystems.net/careers"
    },
    {
        "name": "Coretechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.coretechnologies.co.uk/careers"
    },
    {
        "name": "Coreconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.coreconsulting.com/careers"
    },
    {
        "name": "Coreservices UK",
        "sector": "Private Tech",
        "url": "https://www.coreservices.io/careers"
    },
    {
        "name": "Corenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.corenetworks.tech/careers"
    },
    {
        "name": "Coregroup UK",
        "sector": "Private Tech",
        "url": "https://www.coregroup.net/careers"
    },
    {
        "name": "Coredynamics UK",
        "sector": "Private Tech",
        "url": "https://www.coredynamics.co.uk/careers"
    },
    {
        "name": "Corepartners UK",
        "sector": "Private Tech",
        "url": "https://www.corepartners.com/careers"
    },
    {
        "name": "Corelabs UK",
        "sector": "Private Tech",
        "url": "https://www.corelabs.io/careers"
    },
    {
        "name": "Coreanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.coreanalytics.tech/careers"
    },
    {
        "name": "Coresoftware UK",
        "sector": "Private Tech",
        "url": "https://www.coresoftware.net/careers"
    },
    {
        "name": "Coreit UK",
        "sector": "Private Tech",
        "url": "https://www.coreIT.co.uk/careers"
    },
    {
        "name": "Innovatesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesolutions.com/careers"
    },
    {
        "name": "Innovatesystems UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesystems.io/careers"
    },
    {
        "name": "Innovatetechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.innovatetechnologies.tech/careers"
    },
    {
        "name": "Innovateconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.innovateconsulting.net/careers"
    },
    {
        "name": "Innovateservices UK",
        "sector": "Private Tech",
        "url": "https://www.innovateservices.co.uk/careers"
    },
    {
        "name": "Innovatenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.innovatenetworks.com/careers"
    },
    {
        "name": "Innovategroup UK",
        "sector": "Private Tech",
        "url": "https://www.innovategroup.io/careers"
    },
    {
        "name": "Innovatedynamics UK",
        "sector": "Private Tech",
        "url": "https://www.innovatedynamics.tech/careers"
    },
    {
        "name": "Innovatepartners UK",
        "sector": "Private Tech",
        "url": "https://www.innovatepartners.net/careers"
    },
    {
        "name": "Innovatelabs UK",
        "sector": "Private Tech",
        "url": "https://www.innovatelabs.co.uk/careers"
    },
    {
        "name": "Innovateanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.innovateanalytics.com/careers"
    },
    {
        "name": "Innovatesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.innovatesoftware.io/careers"
    },
    {
        "name": "Innovateit UK",
        "sector": "Private Tech",
        "url": "https://www.innovateIT.tech/careers"
    },
    {
        "name": "Agilesolutions UK",
        "sector": "Private Tech",
        "url": "https://www.agilesolutions.net/careers"
    },
    {
        "name": "Agilesystems UK",
        "sector": "Private Tech",
        "url": "https://www.agilesystems.co.uk/careers"
    },
    {
        "name": "Agiletechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.agiletechnologies.com/careers"
    },
    {
        "name": "Agileconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.agileconsulting.io/careers"
    },
    {
        "name": "Agileservices UK",
        "sector": "Private Tech",
        "url": "https://www.agileservices.tech/careers"
    },
    {
        "name": "Agilenetworks UK",
        "sector": "Private Tech",
        "url": "https://www.agilenetworks.net/careers"
    },
    {
        "name": "Agilegroup UK",
        "sector": "Private Tech",
        "url": "https://www.agilegroup.co.uk/careers"
    },
    {
        "name": "Agiledynamics UK",
        "sector": "Private Tech",
        "url": "https://www.agiledynamics.com/careers"
    },
    {
        "name": "Agilepartners UK",
        "sector": "Private Tech",
        "url": "https://www.agilepartners.io/careers"
    },
    {
        "name": "Agilelabs UK",
        "sector": "Private Tech",
        "url": "https://www.agilelabs.tech/careers"
    },
    {
        "name": "Agileanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.agileanalytics.net/careers"
    },
    {
        "name": "Agilesoftware UK",
        "sector": "Private Tech",
        "url": "https://www.agilesoftware.co.uk/careers"
    },
    {
        "name": "Agileit UK",
        "sector": "Private Tech",
        "url": "https://www.agileIT.com/careers"
    },
    {
        "name": "Nexussolutions UK",
        "sector": "Private Tech",
        "url": "https://www.nexussolutions.io/careers"
    },
    {
        "name": "Nexussystems UK",
        "sector": "Private Tech",
        "url": "https://www.nexussystems.tech/careers"
    },
    {
        "name": "Nexustechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.nexustechnologies.net/careers"
    },
    {
        "name": "Nexusconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.nexusconsulting.co.uk/careers"
    },
    {
        "name": "Nexusservices UK",
        "sector": "Private Tech",
        "url": "https://www.nexusservices.com/careers"
    },
    {
        "name": "Nexusnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.nexusnetworks.io/careers"
    },
    {
        "name": "Nexusgroup UK",
        "sector": "Private Tech",
        "url": "https://www.nexusgroup.tech/careers"
    },
    {
        "name": "Nexusdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.nexusdynamics.net/careers"
    },
    {
        "name": "Nexuspartners UK",
        "sector": "Private Tech",
        "url": "https://www.nexuspartners.co.uk/careers"
    },
    {
        "name": "Nexuslabs UK",
        "sector": "Private Tech",
        "url": "https://www.nexuslabs.com/careers"
    },
    {
        "name": "Nexusanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.nexusanalytics.io/careers"
    },
    {
        "name": "Nexussoftware UK",
        "sector": "Private Tech",
        "url": "https://www.nexussoftware.tech/careers"
    },
    {
        "name": "Nexusit UK",
        "sector": "Private Tech",
        "url": "https://www.nexusIT.net/careers"
    },
    {
        "name": "Techsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.techsolutions.co.uk/careers"
    },
    {
        "name": "Techsystems UK",
        "sector": "Private Tech",
        "url": "https://www.techsystems.com/careers"
    },
    {
        "name": "Techtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.techtechnologies.io/careers"
    },
    {
        "name": "Techconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.techconsulting.tech/careers"
    },
    {
        "name": "Techservices UK",
        "sector": "Private Tech",
        "url": "https://www.techservices.net/careers"
    },
    {
        "name": "Technetworks UK",
        "sector": "Private Tech",
        "url": "https://www.technetworks.co.uk/careers"
    },
    {
        "name": "Techgroup UK",
        "sector": "Private Tech",
        "url": "https://www.techgroup.com/careers"
    },
    {
        "name": "Techdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.techdynamics.io/careers"
    },
    {
        "name": "Techpartners UK",
        "sector": "Private Tech",
        "url": "https://www.techpartners.tech/careers"
    },
    {
        "name": "Techlabs UK",
        "sector": "Private Tech",
        "url": "https://www.techlabs.net/careers"
    },
    {
        "name": "Techanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.techanalytics.co.uk/careers"
    },
    {
        "name": "Techsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.techsoftware.com/careers"
    },
    {
        "name": "Techit UK",
        "sector": "Private Tech",
        "url": "https://www.techIT.io/careers"
    },
    {
        "name": "Softsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.softsolutions.tech/careers"
    },
    {
        "name": "Softsystems UK",
        "sector": "Private Tech",
        "url": "https://www.softsystems.net/careers"
    },
    {
        "name": "Softtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.softtechnologies.co.uk/careers"
    },
    {
        "name": "Softconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.softconsulting.com/careers"
    },
    {
        "name": "Softservices UK",
        "sector": "Private Tech",
        "url": "https://www.softservices.io/careers"
    },
    {
        "name": "Softnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.softnetworks.tech/careers"
    },
    {
        "name": "Softgroup UK",
        "sector": "Private Tech",
        "url": "https://www.softgroup.net/careers"
    },
    {
        "name": "Softdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.softdynamics.co.uk/careers"
    },
    {
        "name": "Softpartners UK",
        "sector": "Private Tech",
        "url": "https://www.softpartners.com/careers"
    },
    {
        "name": "Softlabs UK",
        "sector": "Private Tech",
        "url": "https://www.softlabs.io/careers"
    },
    {
        "name": "Softanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.softanalytics.tech/careers"
    },
    {
        "name": "Softsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.softsoftware.net/careers"
    },
    {
        "name": "Softit UK",
        "sector": "Private Tech",
        "url": "https://www.softIT.co.uk/careers"
    },
    {
        "name": "Datasolutions UK",
        "sector": "Private Tech",
        "url": "https://www.datasolutions.com/careers"
    },
    {
        "name": "Datasystems UK",
        "sector": "Private Tech",
        "url": "https://www.datasystems.io/careers"
    },
    {
        "name": "Datatechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.datatechnologies.tech/careers"
    },
    {
        "name": "Dataconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.dataconsulting.net/careers"
    },
    {
        "name": "Dataservices UK",
        "sector": "Private Tech",
        "url": "https://www.dataservices.co.uk/careers"
    },
    {
        "name": "Datanetworks UK",
        "sector": "Private Tech",
        "url": "https://www.datanetworks.com/careers"
    },
    {
        "name": "Datagroup UK",
        "sector": "Private Tech",
        "url": "https://www.datagroup.io/careers"
    },
    {
        "name": "Datadynamics UK",
        "sector": "Private Tech",
        "url": "https://www.datadynamics.tech/careers"
    },
    {
        "name": "Datapartners UK",
        "sector": "Private Tech",
        "url": "https://www.datapartners.net/careers"
    },
    {
        "name": "Datalabs UK",
        "sector": "Private Tech",
        "url": "https://www.datalabs.co.uk/careers"
    },
    {
        "name": "Dataanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.dataanalytics.com/careers"
    },
    {
        "name": "Datasoftware UK",
        "sector": "Private Tech",
        "url": "https://www.datasoftware.io/careers"
    },
    {
        "name": "Datait UK",
        "sector": "Private Tech",
        "url": "https://www.dataIT.tech/careers"
    },
    {
        "name": "Cloudsolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsolutions.net/careers"
    },
    {
        "name": "Cloudsystems UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsystems.co.uk/careers"
    },
    {
        "name": "Cloudtechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cloudtechnologies.com/careers"
    },
    {
        "name": "Cloudconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cloudconsulting.io/careers"
    },
    {
        "name": "Cloudservices UK",
        "sector": "Private Tech",
        "url": "https://www.cloudservices.tech/careers"
    },
    {
        "name": "Cloudnetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cloudnetworks.net/careers"
    },
    {
        "name": "Cloudgroup UK",
        "sector": "Private Tech",
        "url": "https://www.cloudgroup.co.uk/careers"
    },
    {
        "name": "Clouddynamics UK",
        "sector": "Private Tech",
        "url": "https://www.clouddynamics.com/careers"
    },
    {
        "name": "Cloudpartners UK",
        "sector": "Private Tech",
        "url": "https://www.cloudpartners.io/careers"
    },
    {
        "name": "Cloudlabs UK",
        "sector": "Private Tech",
        "url": "https://www.cloudlabs.tech/careers"
    },
    {
        "name": "Cloudanalytics UK",
        "sector": "Private Tech",
        "url": "https://www.cloudanalytics.net/careers"
    },
    {
        "name": "Cloudsoftware UK",
        "sector": "Private Tech",
        "url": "https://www.cloudsoftware.co.uk/careers"
    },
    {
        "name": "Cloudit UK",
        "sector": "Private Tech",
        "url": "https://www.cloudIT.com/careers"
    },
    {
        "name": "Cybersolutions UK",
        "sector": "Private Tech",
        "url": "https://www.cybersolutions.io/careers"
    },
    {
        "name": "Cybersystems UK",
        "sector": "Private Tech",
        "url": "https://www.cybersystems.tech/careers"
    },
    {
        "name": "Cybertechnologies UK",
        "sector": "Private Tech",
        "url": "https://www.cybertechnologies.net/careers"
    },
    {
        "name": "Cyberconsulting UK",
        "sector": "Private Tech",
        "url": "https://www.cyberconsulting.co.uk/careers"
    },
    {
        "name": "Cyberservices UK",
        "sector": "Private Tech",
        "url": "https://www.cyberservices.com/careers"
    },
    {
        "name": "Cybernetworks UK",
        "sector": "Private Tech",
        "url": "https://www.cybernetworks.io/careers"
    },
    {
        "name": "Cybergroup UK",
        "sector": "Private Tech",
        "url": "https://www.cybergroup.tech/careers"
    },
    {
        "name": "Cyberdynamics UK",
        "sector": "Private Tech",
        "url": "https://www.cyberdynamics.net/careers"
    }
]

class SourceDispatchAgent(BaseAgent):
    def __init__(self, broker=None):
        super().__init__("source_dispatch_agent", "company_list_queue")

    def _resolve_portals(self, universe_str: str) -> list[dict]:
        if not universe_str or universe_str.lower() in ("all", "public sector"):
            return PUBLIC_SECTOR_PORTALS
        
        target_names = [p.strip().lower() for p in universe_str.split(",")]
        resolved = []
        for portal in PUBLIC_SECTOR_PORTALS:
            name = portal["name"].lower()
            sector = portal["sector"].lower()
            if any(t in name or t in sector for t in target_names):
                resolved.append(portal)
        return resolved

    def process_message(self, message: dict):
        logger.info(f"[{self.name}] Received dispatch request: {message}")
        payload = message.get("payload", {})
        workflow_id = message.get("correlation_id") or payload.get("workflow_id")
        params = payload.get("params", {})
        universe = params.get("universe", "All")
        
        portals_to_search = self._resolve_portals(universe)
        
        limit = payload.get("limit")
        if limit and limit > 0:
            portals_to_search = portals_to_search[:limit]
            
        logger.info(f"[{self.name}] Discovered {len(portals_to_search)} portals to search.")
        
        if not portals_to_search:
            self.broker.publish(queue_name="master_queue", source=self.name, target="master", msg_type="task_response", correlation_id=workflow_id, payload={
                "type": "stage_1_complete",
                "workflow_id": workflow_id,
                "companies": [],
                "portals": [],
                "searches_dispatched": 0
            })
            return

        for portal in portals_to_search:
            search_msg = {
                "workflow_id": workflow_id,
                "portal": portal,
                "params": params,
                "include_entry_level": payload.get("include_entry_level", True)
            }
            self.broker.publish(queue_name="job_search_queue", source=self.name, target="job_search_agent", msg_type="task_request", correlation_id=workflow_id, payload=search_msg)
            
        self.broker.publish(queue_name="master_queue", source=self.name, target="master", msg_type="task_response", correlation_id=workflow_id, payload={
            "type": "stage_1_complete",
            "workflow_id": workflow_id,
            "portals": portals_to_search,
            "companies": portals_to_search,
            "searches_dispatched": len(portals_to_search)
        })
