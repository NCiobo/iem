"""
 Mine grid point extracted values for our good and the good of the IEM
 Use Unidata's motherlode server :)

"""
import sys
import network
table = network.Table( ['AWOS', 'IA_ASOS'] )
import psycopg2
MOS = psycopg2.connect(database='mos', host='iemdb')
mcursor = MOS.cursor()

import csv
import urllib2
import datetime
import pytz

BASE_URL = "http://thredds.ucar.edu/thredds/ncss/grid/grib/NCEP/"
URLS = { 
 'NAM' : "NAM/CONUS_12km/conduit/files/NAM_CONUS_12km_conduit_%Y%m%d_%H00.grib2",
 'GFS' : "GFS/Global_0p5deg/files/GFS_Global_0p5deg_%Y%m%d_%H00.grib2",
 'RAP' : "RAP/CONUS_13km/files/RR_CONUS_13km_%Y%m%d_%H00.grib2",
}
VLOOKUP = {
 'sbcape': {'NAM': 'Convective_available_potential_energy_surface',
            'GFS': 'Convective_available_potential_energy_surface',
            'RAP': 'Convective_available_potential_energy_surface'},
 'sbcin': {'NAM': 'Convective_inhibition_surface',
           'GFS': 'Convective_inhibition_surface',
           'RAP': 'Convective_inhibition_surface'},
 'pwater': {'NAM': 'Precipitable_water_entire_atmosphere',
            'GFS': 'Precipitable_water_entire_atmosphere',
            'RAP': 'Precipitable_water_entire_atmosphere'},
 'precipcon': {'RAP': 
               'Convective_precipitation_surface_Mixed_intervals_Accumulation',
            'NAM': 'Convective_precipitation_surface_3_Hour_Accumulation',
            'GFS': 
            'Convective_precipitation_surface_Mixed_intervals_Accumulation',
           },
 'precipnon': {'RAP': None,
            'NAM': None,
            'GFS': None
           },
 'precip': {'RAP': 
'Large-scale_precipitation_non-convective_surface_Mixed_intervals_Accumulation',
            'NAM': 'Total_precipitation_surface_3_Hour_Accumulation',
            'GFS': 'Total_precipitation_surface_Mixed_intervals_Accumulation',
           }
}


def run(model, station, lon, lat, ts):
    """
    Ingest the model data for a given Model, stationid and timestamp
    """

    vstring = ""
    for v in VLOOKUP:
        if VLOOKUP[v][model] is not None:
            vstring += "var=%s&" % (VLOOKUP[v][model],)

    url = ("%s%s?%slatitude=%s&longitude=%s&temporal=all&vertCoord="
           +"&accept=csv&point=true") % (BASE_URL, ts.strftime( URLS[model] ), 
                                        vstring, lat, lon)
    try:
        fp = urllib2.urlopen( url , timeout=60)
    except Exception, exp:
        print exp, url
        print 'FAIL ts: %s station: %s model: %s' % (ts.strftime("%Y-%m-%d %H"), 
                                                     station, model)
        return

    table = "model_gridpoint_%s" % (ts.year,)
    sql = """DELETE from """+ table +""" WHERE 
        station = %s and 
          model = %s and runtime = %s """
    args = (station, model, ts)
    mcursor.execute( sql, args )
    if mcursor.rowcount > 0:
        print 'Deleted %s rows for ts: %s station: %s model: %s' % (
                        mcursor.rowcount, ts, station, model)

    count = 0
    r = csv.DictReader( fp )
    for row in r:
        for k in row.keys():
            row[ k[:k.find("[")] ] = row[k]
        sbcape = row[ VLOOKUP['sbcape'][model] ] 
        sbcin = row[ VLOOKUP['sbcin'][model] ] 
        pwater = row[ VLOOKUP['pwater'][model] ] 
        precipcon = row[ VLOOKUP['precipcon'][model] ] 
        if model == "RAP22":
            precip = (float(row[ VLOOKUP['precipcon'][model] ]) + 
                      float(row[ VLOOKUP['precipnon'][model] ]))
        else:
            precip = row[ VLOOKUP['precip'][model] ] 
        if precip < 0:
            precip = None
        if precipcon < 0:
            precipcon = None
        fts = datetime.datetime.strptime(row['date'], '%Y-%m-%dT%H:%M:%SZ')
        fts = fts.replace(tzinfo=pytz.timezone("UTC"))
        sql = """INSERT into """+table+""" (station, model, runtime, 
              ftime, sbcape, sbcin, pwater, precipcon, precip) 
              VALUES (%s, %s , %s,
              %s, %s, %s, %s, %s, %s )"""
        args = ( station, model, ts, fts, sbcape, sbcin, pwater, precipcon, 
                 precip)
        mcursor.execute( sql, args )
        count += 1
    return count

if __name__ == '__main__':
    ''' Go Go gadget '''
    gts = datetime.datetime.utcnow()
    if len(sys.argv) == 5:
        gts = datetime.datetime(int(sys.argv[1]), int(sys.argv[2]), 
                                int(sys.argv[3]), int(sys.argv[4]))
    gts = gts.replace(tzinfo=pytz.timezone("UTC"), minute=0, second=0,
                      microsecond=0)

    if gts.hour % 6 == 0:
        ts = gts - datetime.timedelta(hours=6)
        for sid in table.sts.keys():
            cnt = run("GFS", "K"+sid, table.sts[sid]['lon'], 
                      table.sts[sid]['lat'], ts)
            if cnt == 0:
                print 'No data', "K"+sid, ts, 'GFS'
            cnt = run("NAM", "K"+sid, table.sts[sid]['lon'], 
                      table.sts[sid]['lat'], ts)
            if cnt == 0:
                print 'No data', "K"+sid, ts, 'GFS'
    for sid in table.sts.keys():
        ts = gts - datetime.timedelta(hours=2)
        run("RAP", "K"+sid, table.sts[sid]['lon'], table.sts[sid]['lat'], ts)
    mcursor.close()
    MOS.commit()
    MOS.close()