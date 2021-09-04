import numpy as np
import pandas as pd
import datetime as dt

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func

from flask import Flask, jsonify

# Database Setup
database_path = "./Resources/hawaii.sqlite"
engine = create_engine(f"sqlite:///{database_path}", echo=False)

# reflect an existing database into a new model
Base = automap_base()
# reflect the tables
Base.prepare(engine, reflect=True)

# Save reference to the table
Measurements = Base.classes.measurement
Stations = Base.classes.station

# Flask Setup
app = Flask(__name__)

###########################################################################################
################################## Flask Routes ###########################################
###########################################################################################

@app.route("/")
def welcome():
    """List all available api routes."""
    session = Session(engine)

    latestDate = session.query(Measurements.date).order_by(Measurements.date.desc()).first()
    earliestDate = session.query(Measurements.date).order_by(Measurements.date).first()
   
    session.close()
    
    return (
        f"Available Routes:<br/>"
        f"&emsp;&emsp;/api/v1.0/precipitation<br/>"
        f"&emsp;&emsp;/api/v1.0/stations</br>"
        f"&emsp;&emsp;/api/v1.0/tobs<br/>"
        f"<br/>"
        f"Available Date Search Routes:<br/>"
        f"&emsp;Data Available between:&emsp;{earliestDate[0]}&emsp; to&emsp; {latestDate[0]}<br/>"
        f"&emsp;&emsp;/api/v1.0/startdate<br/>"
        f"&emsp;&emsp;/api/v1.0/startdate/enddate"
    )

###########################################################################################

@app.route("/api/v1.0/precipitation")
def precipitation():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    # Query precipitation data
    
    query_date = dt.date(2017, 8, 23) - dt.timedelta(days=365)
    precipScores = session.query(Measurements.station, Measurements.date, Measurements.prcp).filter(Measurements.date >= query_date).\
    order_by(Measurements.date).all()
    session.close()

    
    prcpScores_df = pd.DataFrame(precipScores, columns=['Stations','Date','Precipitation'])
    prcpSums_df = prcpScores_df.groupby("Date").sum()
    

    # Convert list of tuples into normal list
    prcpData = [prcpSums_df.to_dict()]
    
    return jsonify(prcpData)

###########################################################################################

@app.route("/api/v1.0/stations")
def stations():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    # Query station data 
    activeStations = session.query(Stations.station,Stations.name,func.count(Measurements.station)).\
        filter(Stations.station == Measurements.station).\
        group_by(Measurements.station).\
        order_by(func.count(Measurements.station).desc()).all()    
    
    session.close()
    
    stationList =[]

    for station, name, observations in activeStations:
        station_dict = {}
        station_dict['StationID'] = station
        station_dict['Name'] = name
        station_dict['Observations'] = observations
        stationList.append(station_dict)    
    
    return jsonify(stationList)

###########################################################################################

@app.route("/api/v1.0/tobs")
def temperature():
    # Create our session (link) from Python to the DB
    session = Session(engine)
    
    # Query date
    query_date = dt.date(2017, 8, 23) - dt.timedelta(days=365)

    # Query to find most active station ID
    activeStations =session.query(Stations.station, Stations.name,func.count(Measurements.station)).\
        filter(Stations.station == Measurements.station).\
        group_by(Measurements.station).\
        order_by(func.count(Measurements.station).desc()).all()
    
    topStation =  [result[0] for result in activeStations][0]
    
    # Query most active station data 
    topActive = session.query(Measurements.station, Stations.name, Measurements.date, Measurements.tobs).\
        filter(Stations.station == Measurements.station).\
        filter(Measurements.station == topStation).\
        filter(Measurements.date >= query_date).\
        order_by(Measurements.date).all()
    
    session.close()

    # Create dictionary for temp data of most active station
    topActive_df = pd.DataFrame(topActive, columns=["StationID","Name","Date","Temperature"])
    stationTemp_dict = topActive_df[["Date","Temperature"]].set_index("Date").to_dict()
    stationTemps= stationTemp_dict["Temperature"]
    
    # Strip most active station name and ID
    stationID = [result[0] for result in topActive][1]
    stationName = [result[1] for result in topActive][1]
    
    # Create dictionary for most active station
    activeStation = [{"Name":stationName,
                     "Station ID":stationID,
                     "Temperatures":stationTemps
                    }]
    
    return jsonify(activeStation)

###########################################################################################

@app.route("/api/v1.0/<start>")
def stats_by_start_date(start):
    # Create our session (link) from Python to the DB
    session = Session(engine)
    
    # Format search query date
    search = dt.date.fromisoformat(start)
    
    # Query and date validation
    latestDate = session.query(Measurements.date).order_by(Measurements.date.desc()).first()
    earliestDate = session.query(Measurements.date).order_by(Measurements.date).first()
    upperBounds = dt.date.fromisoformat(latestDate[0])
    lowerBounds = dt.date.fromisoformat(earliestDate[0])
    
    if search>upperBounds or search<lowerBounds: 
        return jsonify({"ERROR": "Choose date within avaliable range."}), 404
    
    # Query for temp data
    stationData = session.query(Measurements.station, Stations.name, Measurements.date, Measurements.tobs).\
        filter(Stations.station == Measurements.station).\
        filter(Measurements.date >= search).\
        order_by(Measurements.date).all()
    
    session.close()

    # Calculate statistics from search
    stationData_df = pd.DataFrame(stationData, columns=["StationID","Name","Date","Temperature"])
    tests = ['min','max','mean']
    stationStats_df = stationData_df.groupby(["StationID","Name"]).agg({"Temperature":tests}).reset_index() 
    
    # Create dictionary data from search
    tempResults = [] 
    
    for x in range(len(stationStats_df)):
        stationStats = {}     
        stationStats["Name"] = stationStats_df.iloc[x,1]
        stationStats["Station ID"] =stationStats_df.iloc[x,0]
        stationStats["Temperatures"] = stationStats_df["Temperature"].iloc[x,:].to_dict()
        tempResults.append(stationStats)
    
    return jsonify(tempResults)

###########################################################################################

@app.route("/api/v1.0/<start>/<end>")
def stats_between_dates(start,end):
    # Create our session (link) from Python to the DB
    session = Session(engine)
    
    # Format search query dates
    searchStart = dt.date.fromisoformat(start)
    searchEnd = dt.date.fromisoformat(end)
    
    # Query and date validation
    dateTest = searchStart <= searchEnd
    
    latestDate = session.query(Measurements.date).order_by(Measurements.date.desc()).first()
    earliestDate = session.query(Measurements.date).order_by(Measurements.date).first()
    upperBounds = dt.date.fromisoformat(latestDate[0])
    lowerBounds = dt.date.fromisoformat(earliestDate[0])
    
    if dateTest == False:
        return jsonify({"ERROR": "End date should be greater than start date."}), 404
    elif ((searchStart or searchEnd)>upperBounds) or ((searchStart or searchEndsearch)<lowerBounds):
        return jsonify({"ERROR": "Choose dates within avaliable range."}), 404
    
    # Query for temp data
    stationData = session.query(Measurements.station, Stations.name, Measurements.date, Measurements.tobs).\
        filter(Stations.station == Measurements.station).\
        filter(Measurements.date >= searchStart).\
        filter(Measurements.date <= searchEnd).\
        order_by(Measurements.date).all()

    # Calculate statistics from search
    stationData_df = pd.DataFrame(stationData, columns=["StationID","Name","Date","Temperature"])
    tests = ['min','max','mean']
    stationStats_df = stationData_df.groupby(["StationID","Name"]).agg({"Temperature":tests}).reset_index() 
    
    # Create dictionary data from search
    tempResults = [] 
    
    for x in range(len(stationStats_df)-1):
        stationStats = {}     
        stationStats["Name"] = stationStats_df.iloc[x,1]
        stationStats["Station ID"] =stationStats_df.iloc[x,0]
        stationStats["Temperatures"] = stationStats_df["Temperature"].iloc[x,:].to_dict()
        tempResults.append(stationStats)
    
    return jsonify(tempResults)

###########################################################################################

if __name__ == '__main__':
    app.run(debug=True)
    
###########################################################################################
###########################################################################################